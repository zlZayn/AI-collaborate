import json
import os
import re
import threading
from datetime import datetime

from lib.client import LLMClient
from lib.planner import parse_plan, validate_plan
from lib.dispatcher import Dispatcher
from lib.summarizer import run_summary
from lib.context import build_context


def safe_name(s):
    s = s.strip().replace(" ", "_")
    s = re.sub(r"[^\w一-鰿\-]", "", s)
    return s[:40]


class Harness:
    def __init__(self, config):
        self.cfg = config
        self.client = LLMClient(
            config["connection"]["api_key"], config["connection"]["base_url"]
        )
        self.goal = config["task"]["goal"]
        self.model_ids = [m["model"] for m in config["model_pool"]]
        self.pipeline = config["pipeline"]
        self.plan_model = self.pipeline["plan"]["model"]
        self.chat_model = self.pipeline["chat"]["model"]

        self.ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.folder = f"output/{safe_name(self.goal)}_{self.ts}"
        os.makedirs(self.folder, exist_ok=True)

        self.state_path = os.path.join(self.folder, "state.json")
        self.state = {"goal": self.goal, "plan": [], "tasks": []}
        self._lock = threading.Lock()

        self.dispatcher = Dispatcher(
            self.client,
            self.state,
            self.folder,
            self._save_state,
            on_all_done=self._on_all_tasks_done,
            agent_rules=config["task"].get("agent_rules", ""),
        )

    def _save_state(self):
        with self._lock:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)

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
            raw = self.client.chat(messages, self.plan_model)
            plan = parse_plan(raw, self.model_ids)

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

            errors = validate_plan(plan, self.model_ids)
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

        self.state["plan"] = plan
        self._save_state()

        total = sum(len(item["agents"]) for item in plan)
        print(f"\r[plan] {len(plan)} tasks, {total} agents")

        for i, item in enumerate(plan):
            task_prefix = "└── " if i == len(plan) - 1 else "├── "
            indent = "    " if i == len(plan) - 1 else "│   "
            print(f"  {task_prefix}{item['task']}")
            agents = item["agents"]
            for j, a in enumerate(agents):
                agent_prefix = "└── " if j == len(agents) - 1 else "├── "
                print(f"  {indent}{agent_prefix}{a['label']}")

    # -- dispatch -----------------------------------------------------

    def dispatch(self):
        if not self.state["plan"]:
            return
        print("  Dispatching...", end="", flush=True)
        self.dispatcher.launch_all(self.state["plan"])
        total = len(self.state["tasks"])
        print(f"\r[dispatch] {total} agents")

    # -- loop ---------------------------------------------------------

    def loop(self):
        print("[*] /status  /summarize  /quit")

        while True:
            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not cmd:
                continue
            if cmd == "/quit":
                break
            if cmd == "/status":
                self._show_status()
                continue
            if cmd == "/summarize":
                self._do_summary()
                continue

            ctx = build_context(self.goal, self.state["tasks"])
            system = self.pipeline["chat"]["prompt"].replace("{context}", ctx)

            print()
            self.client.stream_print(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": cmd},
                ],
                self.chat_model,
            )
            print()

    # -- status -------------------------------------------------------

    def _show_status(self):
        done_n = sum(1 for t in self.state["tasks"] if t["status"] == "done")
        run_n = sum(1 for t in self.state["tasks"] if t["status"] == "running")
        total = len(self.state["tasks"])
        print(f"[status] {done_n} done, {run_n} running, {total} total")

        status_map = {(t["task"], t["label"]): t["status"] for t in self.state["tasks"]}

        for i, item in enumerate(self.state["plan"]):
            task_prefix = "└── " if i == len(self.state["plan"]) - 1 else "├── "
            indent = "    " if i == len(self.state["plan"]) - 1 else "│   "
            print(f"  {task_prefix}{item['task']}")
            agents = item["agents"]
            for j, a in enumerate(agents):
                agent_prefix = "└── " if j == len(agents) - 1 else "├── "
                s = status_map.get((item["task"], a["label"]), "pending")
                mark = "+" if s == "done" else ("-" if s == "running" else " ")
                print(f"  {indent}{agent_prefix}[{mark}] {a['label']}")

    def _on_all_tasks_done(self):
        self._do_summary()

    # -- summary ------------------------------------------------------

    def _do_summary(self):
        prompt_tpl = self.pipeline["summary"]["prompt"]
        model = self.pipeline["summary"]["model"]
        temperature = self.pipeline["summary"].get("temperature")
        filename = f"summary_{safe_name(self.goal)}.md"
        print("  Summarizing...", end="", flush=True)
        run_summary(
            self.client,
            self.state["tasks"],
            self.folder,
            model,
            prompt_tpl,
            temperature,
            filename,
        )


def main():
    config = json.load(open("config_orchestrator.json", encoding="utf-8"))
    h = Harness(config)
    h.plan()
    h.dispatch()
    h.loop()


if __name__ == "__main__":
    main()
