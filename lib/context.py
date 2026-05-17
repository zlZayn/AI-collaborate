import os

import lib.constants


def read_file(path):
    try:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
    except (OSError, IOError):
        pass
    return ""


def build_context(goal, plan, runs):
    model_of = {}
    for stage in plan:
        for agent in stage["agents"]:
            model_of[agent["agent_id"]] = agent["model"]

    done = [run for run in runs if run["status"] == lib.constants.STATUS_DONE]
    running = [run for run in runs if run["status"] == lib.constants.STATUS_RUNNING]

    ctx = f"## 目标\n{goal}\n\n"

    if done:
        ctx += "## 已完成\n\n"
        for run in done:
            content = read_file(run.get("result_path", ""))
            if not content:
                content = run.get("error", "[结果不可用]")
            ctx += (
                f"### {run['run_id']} [{run['role']}] {run['stage_description']}\n"
                f"model: {model_of.get(run['agent_id'], '?')}\n\n{content}\n\n---\n\n"
            )

    if running:
        ctx += f"## 进行中 ({len(running)})\n"
        for run in running:
            ctx += f"- {run['run_id']} [{run['role']}] {run['stage_description']}\n"

    return ctx
