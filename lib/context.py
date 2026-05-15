import os

import lib.constants


def _read_file(path):
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

    done = [r for r in runs if r["status"] == lib.constants.STATUS_DONE]
    running = [r for r in runs if r["status"] == lib.constants.STATUS_RUNNING]

    ctx = f"## 目标\n{goal}\n\n"

    if done:
        ctx += "## 已完成\n\n"
        for r in done:
            content = _read_file(r.get("result_path", ""))
            if not content:
                content = r.get("error", "[结果不可用]")
            ctx += (
                f"### {r['run_id']} [{r['role']}] {r['stage_description']}\n"
                f"model: {model_of.get(r['agent_id'], '?')}\n\n{content}\n\n---\n\n"
            )

    if running:
        ctx += f"## 进行中 ({len(running)})\n"
        for r in running:
            ctx += f"- {r['run_id']} [{r['role']}] {r['stage_description']}\n"

    return ctx
