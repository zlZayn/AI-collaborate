import os
import threading


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
        task_id = 0
        for item in plan:
            for a in item["agents"]:
                task_id += 1
                self._state["tasks"].append(
                    {
                        "task_id": f"T{task_id}",
                        "description": item["task"],
                        "role": a["role"],
                        "model": a["model"],
                        "prompt": a["prompt"],
                        "temperature": a.get("temperature"),
                        "status": "running",
                        "result_path": "",
                        "thinking": "",
                        "result": "",
                    }
                )

        self._save()

        for task in self._state["tasks"]:
            path = os.path.abspath(os.path.join(self._folder, f"{task['task_id']}_{task['role']}.md"))
            task["result_path"] = path
            t = threading.Thread(target=self._run_one, args=(task, path))
            t.start()

    def _run_one(self, task, path):
        system = task["prompt"]
        if self._agent_rules:
            system += f"\n\n{self._agent_rules}"
        thinking = self._client.stream_to_file(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": task["description"]},
            ],
            task["model"],
            path,
            temperature=task.get("temperature"),
        )

        with open(path, encoding="utf-8") as f:
            task["result"] = f.read()

        task["thinking"] = thinking
        task["status"] = "done"
        self._save()

        print(f"  {os.path.basename(path)}  done")

        if self._on_all_done and all(
            t["status"] == "done" for t in self._state["tasks"]
        ):
            self._on_all_done()
