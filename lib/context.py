import lib.constants


def build_context(goal, plan, tasks):
    model_of = {}
    for stage in plan:
        for agent in stage["agents"]:
            model_of[agent["agent_id"]] = agent["model"]

    done = [t for t in tasks if t["status"] == lib.constants.STATUS_DONE]
    running = [t for t in tasks if t["status"] == lib.constants.STATUS_RUNNING]

    ctx = f"## 目标\n{goal}\n\n"

    if done:
        ctx += "## 已完成\n\n"
        for t in done:
            ctx += (
                f"### {t['task_id']} [{t['role']}] {t['description']}\n"
                f"model: {model_of.get(t['agent_id'], '?')}\n\n{t['result']}\n\n---\n\n"
            )

    if running:
        ctx += f"## 进行中 ({len(running)})\n"
        for t in running:
            ctx += f"- {t['task_id']} [{t['role']}] {t['description']}\n"

    return ctx
