import os


def run_summary(
    client, tasks, folder, model, prompt_template=None, temperature=None, filename=None
):
    done = [t for t in tasks if t["status"] == "done"]
    if not done:
        print("\r[summary] no completed tasks")
        return

    body = "\n\n---\n\n".join(
        f"[{t['label']}] {t['task']}\n{t['result']}" for t in done
    )

    if prompt_template:
        prompt = prompt_template.replace("{body}", body)
    else:
        prompt = f"去冗余，整合提炼为一个精炼的总结：\n\n{body}"

    fname = filename if filename else f"summary_{model}.md"
    path = os.path.join(folder, fname)
    print(f"\r[summary] {model}  running...")

    client.stream_to_file(
        [{"role": "user", "content": prompt}],
        model,
        path,
        temperature=temperature,
    )

    print(f"  {os.path.basename(path)}  done")
