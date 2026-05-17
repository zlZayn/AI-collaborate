import os

import lib.constants
import lib.log
from lib.context import read_file


def run_summary(
    client, runs, folder, model, prompt_template=None, temperature=None, filename=None
):
    done = [run for run in runs if run["status"] == lib.constants.STATUS_DONE]
    if not done:
        lib.log.phase("summary", "no completed runs")
        return

    body = "\n\n---\n\n".join(
        f"[{run['role']}] {run['stage_description']}\n{read_file(run.get('result_path', ''))}"
        for run in done
    )

    if prompt_template:
        prompt = prompt_template.replace("{body}", body)
    else:
        prompt = f"去冗余，整合提炼为一个精炼的总结：\n\n{body}"

    fname = filename if filename else f"summary_{model}.md"
    path = os.path.join(folder, fname)
    thinking_path = path.replace(".md", "_thinking.md")
    lib.log.phase("summary", f"{model} running...")

    client.stream_to_file(
        [{"role": "user", "content": prompt}],
        model,
        path,
        thinking_path,
        temperature=temperature,
    )

    lib.log.task_done(os.path.basename(path))
