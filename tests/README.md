# tests/ — 测试与手工验证脚本

- 职责：验证与演示脚本；现状不是标准 pytest 套件

文件索引：
- test_think.py：手工脚本（非 pytest 用例）。import 即调用真实 API，结果写 tests/thinking_output.md；配置读 config/orchestrator.json
- thinking_output.md：test_think.py 上次运行的产物（模型输出）

已知问题（2026-08-24 实测）：
- `uv run pytest` 在收集 test_think.py 时直接调 API，key 无效 → 401 collection error，0 用例
- 改 lib/ 或 web/ 后的回归验证：目前无可用自动测试

变更影响路由：新增/修改测试 → 同步根 [AGENTS.md](../AGENTS.md) 的验证快照。
工作约束 → 见 [AGENTS.md](AGENTS.md)。