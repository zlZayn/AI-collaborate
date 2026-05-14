import lib.constants


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
            ctx += (
                f"### {r['run_id']} [{r['role']}] {r['stage_description']}\n"
                f"model: {model_of.get(r['agent_id'], '?')}\n\n{r['result']}\n\n---\n\n"
            )

    if running:
        ctx += f"## 进行中 ({len(running)})\n"
        for r in running:
            ctx += f"- {r['run_id']} [{r['role']}] {r['stage_description']}\n"

    return ctx
