# tests/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

tests/ 特有约束：
- 新测试必须是真 pytest 函数，禁止在 import/收集期调用真实 API
- 目录被 .gitignore 忽略，不随 git 提交（是否恢复跟踪见根 AGENTS.md 待办）
- 文件职责 → [README.md](README.md)