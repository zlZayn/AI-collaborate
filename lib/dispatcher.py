import os
import threading


class Dispatcher:
    def __init__(
        self, client, state, folder, save_callback, on_all_done=None, rules=""
    ):
        self._client = client
        self._state = state
        self._folder = folder
        self._save = save_callback
        self._on_all_done = on_all_done
        self._rules = rules

    def launch_all(self, plan):
        task_id = 0
        for item in plan:
            for a in item["agents"]:
                task_id += 1
                self._state["tasks"].append(
                    {
                        "id": f"T{task_id}",
                        "task": item["task"],
                        "label": a["label"],
                        "model": a["model"],
                        "prompt": a["prompt"],
                        "temperature": a.get("temperature"),
                        "status": "running",
                        "result_file": "",
                        "result": None,
                    }
                )

        self._save()
        total = len(self._state["tasks"])
        print(f"[dispatch] {total} agents")

        for task in self._state["tasks"]:
            path = os.path.join(self._folder, f"{task['id']}_{task['label']}.md")
            task["result_file"] = path
            t = threading.Thread(target=self._run_one, args=(task, path))
            t.start()

    def _run_one(self, task, path):
        system = task["prompt"]
        if self._rules:
            system += f"\n\n{self._rules}"
        self._client.stream_to_file(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": task["task"]},
            ],
            task["model"],
            path,
            temperature=task.get("temperature"),
        )

        with open(path, encoding="utf-8") as f:
            task["result"] = f.read()

        task["status"] = "done"
        self._save()

        print(f"  {os.path.basename(path)}  done")

        if self._on_all_done and all(
            t["status"] == "done" for t in self._state["tasks"]
        ):
            self._on_all_done()
