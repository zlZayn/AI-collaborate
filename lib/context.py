def build_context(goal, tasks):
    done = [t for t in tasks if t["status"] == "done"]
    running = [t for t in tasks if t["status"] == "running"]

    ctx = f"## 目标\n{goal}\n\n"

    if done:
        ctx += "## 已完成\n\n"
        for t in done:
            ctx += (
                f"### {t['id']} [{t['label']}] {t['task']}\n"
                f"model: {t['model']}\n\n{t['result']}\n\n---\n\n"
            )

    if running:
        ctx += f"## 进行中 ({len(running)})\n"
        for t in running:
            ctx += f"- {t['id']} [{t['label']}] {t['task']}\n"

    return ctx
