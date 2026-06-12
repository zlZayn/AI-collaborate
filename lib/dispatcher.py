import os
import threading
from datetime import datetime

import lib.constants
import lib.log
import lib.safe_name


class Dispatcher:
    def __init__(
        self, client, state, folder, save_callback, on_all_done=None, agent_rules="",
        broadcaster=None,
    ):
        self._client = client
        self._state = state
        self._folder = folder
        self._save = save_callback
        self._on_all_done = on_all_done
        self._agent_rules = agent_rules
        self._bc = broadcaster

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
                        "thinking_path": "",
                        "error": "",
                    }
                )

        self._save()

        for stage in plan:
            stage_runs = [
                run
                for run in self._state["runs"]
                if run["stage_id"] == stage["stage_id"]
            ]
            prev_context = self._build_prev_context(stage["stage_id"], bridge_callback)

            threads = []
            for run in stage_runs:
                safe_role = lib.safe_name.safe_name(run['role'])
                result_path = os.path.abspath(
                    os.path.join(
                        self._folder, f"{run['run_id']}_{safe_role}_result.md"
                    )
                )
                thinking_path = os.path.abspath(
                    os.path.join(
                        self._folder, f"{run['run_id']}_{safe_role}_thinking.md"
                    )
                )
                run["result_path"] = result_path
                run["thinking_path"] = thinking_path
                t = threading.Thread(
                    target=self._run_one,
                    args=(run, thinking_path, result_path, prev_context),
                )
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            done_n = sum(
                1 for run in stage_runs if run["status"] == lib.constants.STATUS_DONE
            )
            err_n = sum(
                1 for run in stage_runs if run["status"] == lib.constants.STATUS_ERROR
            )
            if err_n and not done_n:
                return

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
            run
            for run in self._state["runs"]
            if run["status"] == lib.constants.STATUS_DONE
            and int(run["stage_id"][1:]) - 1 < current_idx
        ]
        if not completed:
            return ""

        if not bridge_callback:
            return ""

        for stage in self._state["plan"]:
            if stage["stage_id"] == current_stage_id:
                return bridge_callback(stage, completed)
        return ""

    def _run_one(self, run, thinking_path, result_path, prev_context=""):
        run["started_at"] = datetime.now().isoformat()
        run["status"] = lib.constants.STATUS_RUNNING
        if self._bc:
            self._bc.emit("status_change", {
                "agent_id": run["agent_id"], "status": "running",
                "run_id": run["run_id"],
            })
        agent, _ = self._find_agent(run["agent_id"])
        if agent is None:
            run["status"] = lib.constants.STATUS_ERROR
            run["error"] = f"[错误] 未找到 agent: {run['agent_id']}"
            self._save()
            return
        system = agent["prompt"]
        if self._agent_rules:
            system += f"\n\n{self._agent_rules}"
        if prev_context:
            system += f"\n\n{prev_context}"
        def _on_chunk(chunk_type, text):
            if self._bc:
                self._bc.emit("chunk", {
                    "agent_id": run["agent_id"], "run_id": run["run_id"],
                    "type": chunk_type, "text": text,
                })

        try:
            self._client.stream_to_file(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": run["stage_description"]},
                ],
                agent["model"],
                result_path,
                thinking_path,
                temperature=agent["temperature"],
                on_chunk=_on_chunk if self._bc else None,
            )

            run["finished_at"] = datetime.now().isoformat()
            run["status"] = lib.constants.STATUS_DONE
            self._save()
            if self._bc:
                self._bc.emit("status_change", {
                    "agent_id": run["agent_id"], "status": "done",
                    "run_id": run["run_id"],
                })
        except Exception as e:
            run["status"] = lib.constants.STATUS_ERROR
            run["result_path"] = ""
            run["error"] = f"[错误] {e}"
            run["finished_at"] = datetime.now().isoformat()
            self._save()
            if self._bc:
                self._bc.emit("status_change", {
                    "agent_id": run["agent_id"], "status": "error",
                    "run_id": run["run_id"], "error": str(e),
                })
            return
