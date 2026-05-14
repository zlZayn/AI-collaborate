import os
import threading
from datetime import datetime

import lib.constants
import lib.log


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

    def launch_all(self, plan, bridge_callback=None):
        plan_id = self._state["plan_id"]
        run_id = 0
        for stage in plan:
            for agent in stage["agents"]:
                run_id += 1
                self._state["runs"].append(
                    {
                        "run_id": f"R{run_id}",
                        "plan_id": plan_id,
                        "stage_id": stage["stage_id"],
                        "agent_id": agent["agent_id"],
                        "role": agent["role"],
                        "stage_description": stage.get("description", ""),
                        "status": lib.constants.STATUS_PENDING,
                        "started_at": "",
                        "finished_at": "",
                        "result_path": "",
                        "thinking": "",
                        "result": "",
                    }
                )

        self._save()

        for stage in plan:
            stage_runs = [
                r for r in self._state["runs"] if r["stage_id"] == stage["stage_id"]
            ]
            prev_context = self._build_prev_context(stage["stage_id"], bridge_callback)

            threads = []
            for run in stage_runs:
                path = os.path.abspath(
                    os.path.join(self._folder, f"{run['run_id']}_{run['role']}.md")
                )
                run["result_path"] = path
                t = threading.Thread(
                    target=self._run_one, args=(run, path, prev_context)
                )
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            done_n = sum(
                1 for r in stage_runs if r["status"] == lib.constants.STATUS_DONE
            )
            err_n = sum(
                1 for r in stage_runs if r["status"] == lib.constants.STATUS_ERROR
            )
            if err_n and not done_n:
                lib.log.phase(
                    "stage",
                    f"{stage['stage_id']} {stage['description']} ALL ERROR - stopping",
                )
                return
            suffix = f" ({err_n} error)" if err_n else ""
            lib.log.phase(
                "stage", f"{stage['stage_id']} {stage['description']} done{suffix}"
            )

        if self._on_all_done:
            self._on_all_done()

    def _find_agent(self, agent_id):
        for stage in self._state["plan"]:
            for agent in stage["agents"]:
                if agent["agent_id"] == agent_id:
                    return agent, stage
        return None, None

    def _build_prev_context(self, current_stage_id, bridge_callback=None):
        current_idx = int(current_stage_id[1:]) - 1
        if current_idx == 0:
            return ""

        completed = [
            r
            for r in self._state["runs"]
            if r["status"] == lib.constants.STATUS_DONE
            and int(r["stage_id"][1:]) - 1 < current_idx
        ]
        if not completed:
            return ""

        if bridge_callback:
            for stage in self._state["plan"]:
                if stage["stage_id"] == current_stage_id:
                    return bridge_callback(stage, completed)
            return ""

        parts = []
        for r in completed:
            snippet = r["result"][:500]
            if len(r["result"]) > 500:
                snippet += "..."
            parts.append(
                f"### [{r['stage_id']}] {r['role']}: {r['stage_description']}\n\n{snippet}"
            )

        return "## 前序阶段输出\n\n" + "\n\n---\n\n".join(parts) if parts else ""

    def _run_one(self, run, path, prev_context=""):
        run["started_at"] = datetime.now().isoformat()
        run["status"] = lib.constants.STATUS_RUNNING
        agent, _ = self._find_agent(run["agent_id"])
        if agent is None:
            run["status"] = lib.constants.STATUS_ERROR
            run["result"] = f"[错误] 未找到 agent: {run['agent_id']}"
            self._save()
            return
        system = agent["prompt"]
        if self._agent_rules:
            system += f"\n\n{self._agent_rules}"
        if prev_context:
            system += f"\n\n{prev_context}"
        try:
            thinking = self._client.stream_to_file(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": run["stage_description"]},
                ],
                agent["model"],
                path,
                temperature=agent["temperature"],
            )

            with open(path, encoding="utf-8") as f:
                run["result"] = f.read()

            run["thinking"] = thinking
            run["finished_at"] = datetime.now().isoformat()
            run["status"] = lib.constants.STATUS_DONE
            self._save()
        except Exception as e:
            run["status"] = lib.constants.STATUS_ERROR
            run["result"] = f"[错误] {e}"
            run["finished_at"] = datetime.now().isoformat()
            self._save()
            lib.log.task_error(os.path.basename(path), str(e))
            return

        lib.log.task_done(os.path.basename(path))
