import copy
import importlib
import json
import os
import sys
import threading
from datetime import datetime

import lib.client
import lib.constants
import lib.context
import lib.dispatcher
import lib.log
import lib.planner
import lib.safe_name
import lib.summarizer
from lib.context import read_file


class Harness:
    def __init__(self, config):
        self.cfg = config
        self.client = lib.client.LLMClient(
            config["connection"]["api_key"], config["connection"]["base_url"]
        )
        self.goal = config["goal"]
        self.model_ids = [m["model"] for m in config["model_pool"]]
        self.pipeline = config["pipeline"]
        self.plan_model = self.pipeline["plan"]["model"]
        self.plan_temperature = self.pipeline["plan"].get("temperature")
        self.chat_model = self.pipeline["chat"]["model"]
        self.chat_temperature = self.pipeline["chat"].get("temperature")

        self.plan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.folder = f"output/{lib.safe_name.safe_name(self.goal)}_{self.plan_id}"
        os.makedirs(self.folder, exist_ok=True)

        self.state_path = os.path.join(self.folder, "state.json")
        self.state = {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "folder": self.folder,
            "status": "planning",
            "summary_status": "idle",
            "plan": [],
            "runs": [],
            "bridges": [],
            "continues": [],
        }
        self._lock = threading.Lock()

        self.dispatcher = lib.dispatcher.Dispatcher(
            self.client,
            self.state,
            self.folder,
            self._save_state,
            on_all_done=self._do_summary,
            agent_rules=config.get("agent_rules", ""),
        )

    def _save_state(self):
        with self._lock:
            state_copy = copy.deepcopy(self.state)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state_copy, f, ensure_ascii=False, indent=2)

    def _enrich_plan(self, plan, stage_offset=0, agent_offset=0):
        agent_id = agent_offset
        for i, stage in enumerate(plan):
            stage["stage_id"] = f"S{i + 1 + stage_offset}"
            stage.setdefault("description", "")
            for agent in stage["agents"]:
                agent_id += 1
                agent["agent_id"] = f"A{agent_id}"

    # -- plan ---------------------------------------------------------

    def plan(self):
        print("  Creating directory...", end="", flush=True)
        print(f"\r[dir] {os.path.abspath(self.folder)}\\")

        model_desc = "\n".join(
            f"- {m['model']}: {m['desc']}" for m in self.cfg["model_pool"]
        )
        prompt = self.pipeline["plan"]["prompt"].replace("{model_pool}", model_desc)

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": self.goal},
        ]

        print("  Planning...", end="", flush=True)
        plan = None
        for attempt in range(3):
            try:
                raw = self.client.chat(
                    messages, self.plan_model, temperature=self.plan_temperature
                )
            except Exception as e:
                if attempt == 2:
                    print(f"\r[plan] 异常: {e}")
                    return
                continue
            plan = lib.planner.parse_plan(raw, self.model_ids)

            if plan is None:
                if attempt < 2:
                    messages += [
                        {"role": "assistant", "content": raw},
                        {
                            "role": "user",
                            "content": "上条输出不是合法 JSON，请按格式重新输出纯 JSON。",
                        },
                    ]
                continue

            errors = lib.planner.validate_plan(plan, self.model_ids)
            if not errors:
                break

            if attempt < 2:
                err = "上条 JSON 有以下问题，请修正后重新输出完整 JSON：\n" + "\n".join(
                    f"- {e}" for e in errors
                )
                messages += [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": err},
                ]
            plan = None

        if plan is None:
            print("\r[plan] 规划失败，已重试 3 次")
            return

        self._enrich_plan(plan)
        self.state["plan"] = plan
        self._save_state()

        total = sum(len(item["agents"]) for item in plan)
        print(f"\r[plan] {len(plan)} stages, {total} agents")

        for i, item in enumerate(plan):
            task_prefix = "└── " if i == len(plan) - 1 else "├── "
            indent = "    " if i == len(plan) - 1 else "│   "
            print(f"  {task_prefix}{item['description']}")
            agents = item["agents"]
            for j, a in enumerate(agents):
                agent_prefix = "└── " if j == len(agents) - 1 else "├── "
                print(f"  {indent}{agent_prefix}{a['role']}")

    # -- dispatch -----------------------------------------------------

    def dispatch(self):
        if not self.state["plan"]:
            return
        try:
            self.dispatcher.launch_all(
                self.state["plan"], bridge_callback=self._build_bridge
            )
        except Exception:
            pass

    # -- loop ---------------------------------------------------------

    def loop(self):
        while True:
            self._flush_logs()
            try:
                cmd = input(
                    "\n[*] /1:status  /2:summarize  /0:quit  |  输入文字即对话\n> "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not cmd:
                continue
            if cmd in ("/0", "/quit"):
                break
            if cmd in ("/1", "/status"):
                self._show_status()
                continue
            if cmd in ("/2", "/summarize"):
                self._do_summary()
                continue

            safe_q = lib.safe_name.safe_name(cmd)
            continue_idx = len(self.state.get("continues", [])) + 1
            result_path = os.path.join(
                self.folder, f"continue{continue_idx}_{safe_q}_result.md"
            )
            thinking_path = os.path.join(
                self.folder, f"continue{continue_idx}_{safe_q}_thinking.md"
            )

            ctx = lib.context.build_context(
                self.goal, self.state["plan"], self.state["runs"]
            )
            system = self.pipeline["chat"]["prompt"].replace("{context}", ctx)

            print(f"\n[continue{continue_idx}] writing to {result_path}")
            self.client.stream_to_file(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": cmd},
                ],
                self.chat_model,
                result_path,
                thinking_path,
                temperature=self.chat_temperature,
            )
            print(f"[continue{continue_idx}] done")

            self.state.setdefault("continues", []).append(
                {
                    "index": continue_idx,
                    "question": cmd,
                    "status": "done",
                    "result_path": result_path,
                    "thinking_path": thinking_path,
                }
            )
            self._save_state()

    # -- flush --------------------------------------------------------

    def _flush_logs(self):
        for line in lib.log.flush():
            print(line)

    # -- status -------------------------------------------------------

    def _show_status(self):
        self._flush_logs()

        done_n = sum(
            1 for r in self.state["runs"] if r["status"] == lib.constants.STATUS_DONE
        )
        total = len(self.state["runs"])

        status_map = {r["agent_id"]: r["status"] for r in self.state["runs"]}
        bridge_map = {}
        for b in self.state.get("bridges", []):
            bridge_map[b["to_stage"]] = b

        # flat list: legend -> stage -> bridge -> stage -> ... -> summary
        items = [("[status] [+] done  [-] running  [!] error  [ ] pending", [])]
        stages = self.state["plan"]
        for stage in stages:
            children = []
            stage_statuses = []
            for a in stage["agents"]:
                s = status_map.get(a["agent_id"], lib.constants.STATUS_PENDING)
                mark = {"done": "+", "running": "-", "error": "!"}.get(s, " ")
                children.append(f"[{mark}] {a['role']}")
                stage_statuses.append(s)
            if all(s == "done" for s in stage_statuses):
                smark = "+"
            elif any(s == "running" for s in stage_statuses):
                smark = "-"
            elif any(s == "error" for s in stage_statuses):
                smark = "!"
            else:
                smark = " "
            items.append((f"[{smark}] {stage['description']}", children))
            # bridge only between multiple stages
            if len(stages) > 1:
                sid = stage["stage_id"]
                if sid in bridge_map:
                    src = ",".join(bridge_map[sid]["from_stages"])
                    items.append((f"[+] bridge {src}->{sid}", []))

        # summary only after all stages done
        if done_n == total and total > 0:
            summary_files = [
                f
                for f in os.listdir(self.folder)
                if f.startswith("summary_") and not f.endswith("_thinking.md")
            ]
            if summary_files:
                items.append(("[+] summary", []))

        # continues
        for c in self.state.get("continues", []):
            items.append(
                (
                    f"[+] continue{c['index']}: {c['question']}",
                    [],
                )
            )

        # render tree: legend first, then rest
        legend, rest = items[0], items[1:]
        print(legend[0])
        print("  │")
        for i, (label, children) in enumerate(rest):
            is_last = i == len(rest) - 1
            prefix = "└── " if is_last else "├── "
            indent = "    " if is_last else "│   "
            print(f"  {prefix}{label}")
            for j, child in enumerate(children):
                is_last_c = j == len(children) - 1
                cp = "└── " if is_last_c else "├── "
                print(f"  {indent}{cp}{child}")

    # -- bridge -------------------------------------------------------

    def _build_bridge(self, next_stage, completed_runs):
        bridge_cfg = self.pipeline.get("bridge")
        if not bridge_cfg:
            return self._fallback_context(completed_runs)

        done = [r for r in completed_runs if r["status"] == lib.constants.STATUS_DONE]
        if not done:
            return ""

        prev_outputs = "\n\n---\n\n".join(
            f"[{r['stage_id']}] {r['role']}: {r['stage_description']}\n{read_file(r.get('result_path', ''))}"
            for r in done
        )

        prompt = bridge_cfg["prompt"].replace("{next_stage}", next_stage["description"])
        prompt = prompt.replace("{prev_outputs}", prev_outputs)

        bridge_text = self.client.chat(
            [{"role": "user", "content": prompt}],
            bridge_cfg["model"],
            temperature=bridge_cfg.get("temperature"),
        )

        bridge_filename = f"bridge_{next_stage['stage_id']}_context.md"
        bridge_path = os.path.join(self.folder, bridge_filename)
        with open(bridge_path, "w", encoding="utf-8") as f:
            f.write(bridge_text)

        from_stages = list(dict.fromkeys(r["stage_id"] for r in done))
        if "bridges" not in self.state:
            self.state["bridges"] = []
        self.state["bridges"].append(
            {
                "bridge_id": f"B{len(self.state['bridges']) + 1}",
                "to_stage": next_stage["stage_id"],
                "from_stages": from_stages,
                "path": bridge_filename,
                "model": bridge_cfg["model"],
            }
        )
        self._save_state()

        return bridge_text

    def _fallback_context(self, completed_runs):
        parts = []
        for r in completed_runs:
            if r["status"] != lib.constants.STATUS_DONE:
                continue
            content = read_file(r.get("result_path", ""))
            snippet = content[:500]
            if len(content) > 500:
                snippet += "..."
            parts.append(
                f"### [{r['stage_id']}] {r['role']}: {r['stage_description']}\n\n{snippet}"
            )
        return "## 前序阶段输出\n\n" + "\n\n---\n\n".join(parts) if parts else ""

    # -- summary ------------------------------------------------------

    def _do_summary(self):
        prompt_tpl = self.pipeline["summary"]["prompt"]
        model = self.pipeline["summary"]["model"]
        temperature = self.pipeline["summary"].get("temperature")
        filename = f"summary_{lib.safe_name.safe_name(self.goal)}_result.md"
        lib.summarizer.run_summary(
            self.client,
            self.state["runs"],
            self.folder,
            model,
            prompt_tpl,
            temperature,
            filename,
        )


def main():
    for mod in (
        lib.client,
        lib.constants,
        lib.context,
        lib.dispatcher,
        lib.log,
        lib.planner,
        lib.safe_name,
        lib.summarizer,
    ):
        importlib.reload(mod)
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config_orchestrator.json"
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    h = Harness(config)
    h.plan()
    if not h.state["plan"]:
        return
    dispatch_thread = threading.Thread(target=h.dispatch, daemon=True)
    dispatch_thread.start()
    h.loop()


if __name__ == "__main__":
    main()
