# AI Collaborate — 维护索引

## 全局规则（项目特有）
- 架构“为什么” → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 模块手册 → [lib/README.md](lib/README.md) · [web/README.md](web/README.md) · [tests/README.md](tests/README.md)
- 决策记录 → [.agents/notes/](.agents/notes/)
- 双语文档对译：README.md ↔ README_zh.md 同步更新
- 配置两套结构：orchestrator.json 与 mini_panel.json 不同构，改配置先看对应示例
- 双件分离：AGENTS.md 只写规则，README.md 只写是什么/怎么改

## 常用命令（活文档·可执行）

- 本地钩子：`pre-commit install`（每个 clone 一次；本体 `uv tool install pre-commit`）——提交前自动 `ruff check --fix` + `ruff format`；CI 只读跑同一组检查
- `uv run python orchestrator.py` 编排 CLI（plan → dispatch → loop）
- `uv run python orchestrator.py -n "目标"` 单次执行
- `uv run python mini_panel.py` 精简链路
- `uv run python run_web.py` Web 界面（http://localhost:8080）
- `uv run ruff check .` Lint（ruff 默认规则集，列宽默认 88）
- `uv run ruff format .` 格式化（`--check` 只看不改）

## 验证快照（2026-09-27 实测）
- pytest: no tests ran（0 collected / 0 errors，收集干净；dev 组 pytest 9.1.1）
- Ruff: `check` 0 发现；`format --check` 全绿（全量格式化已落地）
- 引入 Ruff 后复验：`validate_plan` 用 25 例畸形输入对旧实现做差分，输出逐例相同；lib/ 与三个入口 compileall 通过
- web: GET / 200 · GET /api/runs 200

## 待办
- [ ] 为 lib/ 核心逻辑补真 pytest 用例（当前 0 collected）

## 活跃坑
- proposal/、config/*.json 保持忽略不提交；tests/ 已放开跟踪，探针产物 thinking_output.md 随探针运行变动
- lib/log.py 遮蔽标准库 logging，import 必须写全 `lib.log`
- run_web.py 常驻阻塞终端，会绑定 0.0.0.0:8080（web_port 可配）