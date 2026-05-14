import json
import sys
from openai import OpenAI

# IPython/Jupyter 的 stdout 是自定义 OutStream，没有 reconfigure 方法
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

cfg = json.load(open("config_orchestrator.json", encoding="utf-8"))
client = OpenAI(
    api_key=cfg["connection"]["api_key"], base_url=cfg["connection"]["base_url"]
)

model = cfg["model_pool"][0]["model"]
print(f"model: {model}\n")

stream = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "数据采集领域，什么是混叠？"}],
    stream=True,
)

thinking = ""
content = ""

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta:
        d = chunk.choices[0].delta
        if d.reasoning_content:
            thinking += d.reasoning_content
        if d.content:
            content += d.content

output_path = "thinking_output.md"
with open(output_path, "w", encoding="utf-8") as f:
    if thinking:
        f.write(f"# thinking\n\n{thinking}\n\n")
    f.write(f"# output\n\n{content}\n")

print(f"saved to {output_path}")
