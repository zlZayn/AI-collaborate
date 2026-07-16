import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from openai import OpenAI

from lib.safe_name import safe_name

CONFIG = json.load(open("config/mini_panel.json", encoding="utf-8"))


def stream_write(client, messages, model, path):
    stream = client.chat.completions.create(model=model, messages=messages, stream=True)
    with open(path, "w", encoding="utf-8") as f:
        for chunk in stream:
            if (
                chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                f.write(chunk.choices[0].delta.content)
                f.flush()


def main():
    client = OpenAI(api_key=CONFIG["api_key"], base_url=CONFIG["base_url"])
    question = CONFIG["question"]
    panel = CONFIG["panel"]
    summary_model = CONFIG["summary_model"]
    summary_prompt = CONFIG["summary_prompt"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"output/{safe_name(question)}_{ts}"
    os.makedirs(folder, exist_ok=True)
    print(f"\n  {folder}/\n")

    paths = {}
    with ThreadPoolExecutor() as pool:
        print(f"  {'  '.join(p['label'] for p in panel)}  running...")

        futures = {}
        for p in panel:
            path = os.path.join(folder, f"{p['label']}_{p['model']}.md")
            paths[p["label"]] = path
            msgs = [
                {"role": "system", "content": p["prompt"]},
                {"role": "user", "content": question},
            ]
            futures[pool.submit(stream_write, client, msgs, p["model"], path)] = p

        for f, p in futures.items():
            f.result()
            print(f"    {os.path.basename(paths[p['label']])}")

    print()

    body = "\n\n---\n\n".join(
        f"[{p['label']}]\n{open(paths[p['label']], encoding='utf-8').read()}"
        for p in panel
    )

    summary_path = os.path.join(folder, f"summary_{summary_model}.md")
    print("  summary  running...")
    stream_write(
        client,
        [{"role": "user", "content": summary_prompt.format(body=body)}],
        summary_model,
        summary_path,
    )
    print(f"    {os.path.basename(summary_path)}")


if __name__ == "__main__":
    main()
