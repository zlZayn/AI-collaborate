import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copy
import json
import threading
from datetime import datetime

import lib.client
import lib.constants
import lib.dispatcher
import lib.log
import lib.planner
import lib.safe_name
import lib.summarizer
from lib.context import read_file, build_context


class WebRunner:
    def __init__(self, config, broadcaster):
        self.cfg = config
        self.bc = broadcaster
        self.client = lib.client.LLMClient(
            config["connection"]["api_key"], config["connection"]["base_url"]
        )
        self.goal = config["goal"]
        self.model_ids = [m["model"] for m in config["model_pool"]]
        self.pipeline = config["pipeline"]
        self.plan_model = self.pipeline["plan"]["model"]
        self.plan_temperature = self.pipeline["plan"].get("temperature")

        self.plan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.folder = f"output/{lib.safe_name.safe_name(self.goal)}_{self.plan_id}"
        os.makedirs(self.folder, exist_ok=True)

        self.state_path = os.path.join(self.folder, "state.json")
        self.state = {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "plan": [],
            "runs": [],
        }
        self._lock = threading.Lock()

        self.dispatcher = lib.dispatcher.Dispatcher(
            self.client,
            self.state,
            self.folder,
            self._save_state,
            on_all_done=self._do_summary,
            agent_rules=config.get("agent_rules", ""),
            broadcaster=broadcaster,
        )

    def _save_state(self):
        with self._lock:
            state_copy = copy.deepcopy(self.state)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state_copy, f, ensure_ascii=False, indent=2)
        self.bc.emit("state_update", {"plan_id": self.plan_id})

    def _enrich_plan(self, plan, stage_offset=0, agent_offset=0):
        agent_id = agent_offset
        for i, stage in enumerate(plan):
            stage["stage_id"] = f"S{i + 1 + stage_offset}"
            stage.setdefault("description", "")
            for agent in stage["agents"]:
                agent_id += 1
                agent["agent_id"] = f"A{agent_id}"

    def run(self):
        self.bc.emit(
            "run_start",
            {
                "plan_id": self.plan_id,
                "goal": self.goal,
                "folder": self.folder,
            },
        )

        model_desc = "\n".join(
            f"- {m['model']}: {m['desc']}" for m in self.cfg["model_pool"]
        )
        prompt = self.pipeline["plan"]["prompt"].replace("{model_pool}", model_desc)

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": self.goal},
        ]

        plan = None
        for attempt in range(3):
            try:
                raw = self.client.chat(
                    messages, self.plan_model, temperature=self.plan_temperature
                )
            except Exception as e:
                if attempt == 2:
                    self.bc.emit("error", {"message": f"plan exception: {e}"})
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
            self.bc.emit("error", {"message": "plan failed after 3 retries"})
            return

        self._enrich_plan(plan)
        self.state["plan"] = plan
        self._save_state()

        self.bc.emit(
            "plan_ready",
            {
                "plan": plan,
                "folder": self.folder,
            },
        )

        try:
            self.dispatcher.launch_all(
                self.state["plan"], bridge_callback=self._build_bridge
            )
        except Exception as e:
            self.bc.emit("error", {"message": f"dispatch exception: {e}"})

        self.bc.emit("run_done", {"plan_id": self.plan_id})

    def run_continue(self, question):
        safe_q = lib.safe_name.safe_name(question)
        continue_idx = len(self.state.get("continues", [])) + 1
        result_path = os.path.join(
            self.folder, f"continue{continue_idx}_{safe_q}_result.md"
        )
        thinking_path = os.path.join(
            self.folder, f"continue{continue_idx}_{safe_q}_thinking.md"
        )

        ctx = build_context(self.goal, self.state["plan"], self.state["runs"])
        system = self.pipeline["chat"]["prompt"].replace("{context}", ctx)

        self.client.stream_to_file(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            self.pipeline["chat"]["model"],
            result_path,
            thinking_path,
            temperature=self.pipeline["chat"].get("temperature"),
            on_chunk=lambda t, text: self.bc.emit(
                "chunk",
                {
                    "agent_id": f"__continue{continue_idx}__",
                    "run_id": f"continue{continue_idx}",
                    "type": t,
                    "text": text,
                },
            ),
        )

        self.state.setdefault("continues", []).append(
            {
                "index": continue_idx,
                "question": question,
                "result_path": result_path,
                "thinking_path": thinking_path,
            }
        )
        self._save_state()
        self.bc.emit(
            "continue_done",
            {
                "index": continue_idx,
                "question": question,
            },
        )

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

    def _do_summary(self):
        prompt_tpl = self.pipeline["summary"]["prompt"]
        model = self.pipeline["summary"]["model"]
        temperature = self.pipeline["summary"].get("temperature")
        filename = f"summary_{lib.safe_name.safe_name(self.goal)}_result.md"
        self.bc.emit("summary_start", {"plan_id": self.plan_id})
        lib.summarizer.run_summary(
            self.client,
            self.state["runs"],
            self.folder,
            model,
            prompt_tpl,
            temperature,
            filename,
            on_chunk=lambda chunk_type, text: self.bc.emit(
                "chunk",
                {
                    "agent_id": "__summary__",
                    "run_id": "__summary__",
                    "type": chunk_type,
                    "text": text,
                },
            ),
        )
        self.bc.emit("summary_done", {"plan_id": self.plan_id})


def load_base_config(path=None):
    if path is None:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config_orchestrator.json",
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)
