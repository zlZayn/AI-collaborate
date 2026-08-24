# lib/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

lib/ 特有约束：
- 新模块必须被 orchestrator.py 或 web/runner.py 显式 import，无自动发现机制
- 状态字符串一律引自 [constants.py](constants.py)，禁止散落字面量
- 文件职责与导出 → [README.md](README.md)