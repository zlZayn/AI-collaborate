# tests/ — 测试与手工验证脚本

- 职责：验证与演示脚本；现状不是标准 pytest 套件

文件索引：
- think_probe.py：手工 API 探测器（非 pytest 用例，文件名无 test_ 前缀不被收集）。凭据走环境变量：OPENAI_API_KEY（必填）、OPENAI_BASE_URL（默认 https://api.deepseek.com/v1）、OPENAI_MODEL（必填）；缺 key/model 时打印提示并退出，不触发真实请求。结果写 tests/thinking_output.md
- thinking_output.md：think_probe.py 上次运行的产物（模型输出）

已知问题（2026-08-24 实测）：
- `uv run pytest -q`：no tests ran（0 collected / 0 errors，收集干净）
- 改 lib/ 或 web/ 后的回归验证：目前无可用自动测试（见根 AGENTS.md 待办）

变更影响路由：新增/修改测试 → 同步根 [AGENTS.md](../AGENTS.md) 的验证快照。
工作约束 → 见 [AGENTS.md](AGENTS.md)。