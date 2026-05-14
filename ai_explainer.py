import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from openai import OpenAI

CONFIG = json.load(open("config.json", encoding="utf-8"))


def safe_name(s):
    s = s.strip().replace(" ", "_")
    s = re.sub(r"[^\w一-鿿\-]", "", s)
    return s[:40]


def stream_to_file(client, messages, model, path):
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
        names = "  ".join(p["label"] for p in panel)
        print(f"  {names}  running...")

        futures = {}
        for p in panel:
            path = os.path.join(folder, f"{p['label']}_{p['model']}.md")
            paths[p["label"]] = path
            futures[
                pool.submit(
                    stream_to_file,
                    client,
                    [
                        {"role": "system", "content": p["prompt"]},
                        {"role": "user", "content": question},
                    ],
                    p["model"],
                    path,
                )
            ] = p

        for f, p in futures.items():
            f.result()
            print(f"    {os.path.basename(paths[p['label']])}")

    print()

    body = ""
    for p in panel:
        with open(paths[p["label"]], encoding="utf-8") as fp:
            body += f"[{p['label']}]\n{fp.read()}\n\n---\n\n"
    body = body.rstrip("\n---\n")

    summary_path = os.path.join(folder, f"summary_{summary_model}.md")
    print("  summary  running...")
    stream_to_file(
        client,
        [
            {"role": "user", "content": summary_prompt.format(body=body)},
        ],
        summary_model,
        summary_path,
    )
    print(f"    {os.path.basename(summary_path)}")


if __name__ == "__main__":
    main()
