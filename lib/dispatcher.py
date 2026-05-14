import os
import threading
from datetime import datetime

import lib.constants


class Dispatcher:
    def __init__(
        self, client, state, folder, save_callback, on_all_done=None, agent_rules=""
    ):
        self._client = client
        self._state = state
        self._folder = folder
        self._save = save_callback
        self._on_all_done = on_all_done
        self._agent_rules = agent_rules

    def launch_all(self, plan):
        plan_id = self._state["plan_id"]
        task_id = 0
        for stage in plan:
            for agent in stage["agents"]:
                task_id += 1
                self._state["tasks"].append(
                    {
                        "task_id": f"T{task_id}",
                        "plan_id": plan_id,
                        "stage_id": stage["stage_id"],
                        "agent_id": agent["agent_id"],
                        "role": agent["role"],
                        "description": stage.get("description", stage.get("task", "")),
                        "status": lib.constants.STATUS_RUNNING,
                        "started_at": datetime.now().isoformat(),
                        "finished_at": "",
                        "result_path": "",
                        "thinking": "",
                        "result": "",
                    }
                )

        self._save()

        for task in self._state["tasks"]:
            path = os.path.abspath(
                os.path.join(self._folder, f"{task['task_id']}_{task['role']}.md")
            )
            task["result_path"] = path
            t = threading.Thread(target=self._run_one, args=(task, path))
            t.start()

    def _find_agent(self, agent_id):
        for stage in self._state["plan"]:
            for agent in stage["agents"]:
                if agent["agent_id"] == agent_id:
                    return agent, stage
        return None, None

    def _run_one(self, task, path):
        agent, _ = self._find_agent(task["agent_id"])
        if agent is None:
            task["status"] = lib.constants.STATUS_DONE
            task["result"] = f"[错误] 未找到 agent: {task['agent_id']}"
            self._save()
            return
        system = agent["prompt"]
        if self._agent_rules:
            system += f"\n\n{self._agent_rules}"
        thinking = self._client.stream_to_file(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": task["description"]},
            ],
            agent["model"],
            path,
            temperature=agent.get("temperature"),
        )

        with open(path, encoding="utf-8") as f:
            task["result"] = f.read()

        task["thinking"] = thinking
        task["finished_at"] = datetime.now().isoformat()
        task["status"] = lib.constants.STATUS_DONE
        self._save()

        print(f"  {os.path.basename(path)}  done")

        if self._on_all_done and all(
            t["status"] == lib.constants.STATUS_DONE for t in self._state["tasks"]
        ):
            self._on_all_done()
