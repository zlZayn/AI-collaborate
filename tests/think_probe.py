import os
import sys

from openai import OpenAI

# IPython/Jupyter 的 stdout 是自定义 OutStream，没有 reconfigure 方法
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
model = os.environ.get("OPENAI_MODEL")

if not api_key:
    print("OPENAI_API_KEY 未设置：跳过真实 API 探测（本脚本为手工探测器，非 pytest 用例）")
    sys.exit(0)

if not model:
    print("OPENAI_MODEL 未设置：跳过真实 API 探测")
    sys.exit(0)

client = OpenAI(api_key=api_key, base_url=base_url)
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

output_path = "tests/thinking_output.md"
with open(output_path, "w", encoding="utf-8") as f:
    if thinking:
        f.write(f"# thinking\n\n{thinking}\n\n")
    f.write(f"# output\n\n{content}\n")

print(f"saved to {output_path}")