# config/ — 运行配置（两套结构，含密钥）

- 职责：CLI 与 Web 的运行时配置；example 模板入库，真实文件含密钥被 gitignore

文件索引：
- orchestrator_example.json：编排器配置模板（已跟踪，只放占位符）
- mini_panel_example.json：mini_panel 配置模板（已跟踪，只放占位符）
- orchestrator.json：编排器真实配置（含 key，gitignored，永不入库）
- mini_panel.json：mini_panel 真实配置（含 key，gitignored，永不入库）

两套结构对照：
- orchestrator（被 orchestrator.py、web/runner.py 读取）：connection（api_key/base_url）、model_pool、pipeline（plan/bridge/chat/summary）、agent_rules、web_port（可选，默认 8080）
- mini_panel（被 mini_panel.py 读取）：api_key、base_url、question、panel（label/model/prompt 数组）、summary_model、summary_prompt
- 两套结构不同构，改配置先看对应 _example 模板

密钥管理规则：
- 配置内 key 永不提交：orchestrator.json / mini_panel.json 在 .gitignore 中，任何 add（含 -f）都禁止
- 新代码优先读环境变量（OPENAI_API_KEY 等），参考 tests/think_probe.py
- 带 _example 后缀的模板只放占位符，不放真实 key

架构关系：字段契约见 [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 契约节；改配置字段必须同步该节。
工作约束 → 见 [AGENTS.md](AGENTS.md)。