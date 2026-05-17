import json


def parse_plan(raw, model_ids):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("\n```", 1)[0]

    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(items, list):
        items = [items]

    plan = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item = {k.strip(): v for k, v in item.items()}
        if "description" not in item:
            continue
        agents = item.get("agents", [])
        if not isinstance(agents, list):
            continue
        cleaned = []
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            agent = {k.strip(): v for k, v in agent.items()}
            cleaned.append(agent)
        item["agents"] = cleaned
        plan.append(item)

    return plan if plan else None


def validate_plan(plan, model_ids):
    errors = []

    if not isinstance(plan, list):
        return [f"整体应为数组，当前为 {type(plan).__name__}"]

    if not plan:
        return ["至少需要 1 个子任务"]

    for i, item in enumerate(plan):
        p = f"items[{i}]"
        desc = item.get("description")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f"{p}.description 缺失或为空")

        agents = item.get("agents")
        if not isinstance(agents, list):
            errors.append(f"{p}.agents 应为数组")
            continue
        if not agents:
            errors.append(f"{p}.agents 至少 1 人")
        for j, agent in enumerate(agents):
            ap = f"{p}.agents[{j}]"
            if not isinstance(agent, dict):
                errors.append(f"{ap} 应为对象")
                continue
            for field in ["role", "model", "prompt"]:
                val = agent.get(field)
                if not isinstance(val, str) or not val.strip():
                    errors.append(f"{ap}.{field} 缺失或为空")
            if (
                "model" in agent
                and isinstance(agent["model"], str)
                and agent["model"].strip()
            ):
                if agent["model"] not in model_ids:
                    errors.append(
                        f'{ap}.model "{agent["model"]}" 不在人选列表 {model_ids} 中'
                    )
            temp = agent.get("temperature")
            if "temperature" not in agent:
                errors.append(f"{ap}.temperature 缺失")
            elif not isinstance(temp, (int, float)):
                errors.append(
                    f"{ap}.temperature 应为数字，实际为 {type(temp).__name__}"
                )
            elif temp < 0 or temp > 1:
                errors.append(f"{ap}.temperature 值 {temp} 超出 0.0-1.0")

    return errors
