# AI Collaborate — 维护索引

## 全局规则（项目特有）
- 架构“为什么” → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 模块手册 → [lib/README.md](lib/README.md) · [web/README.md](web/README.md) · [tests/README.md](tests/README.md)
- 决策记录 → [.agents/notes/](.agents/notes/)
- 双语文档对译：README.md ↔ README_zh.md 同步更新
- 配置两套结构：orchestrator.json 与 mini_panel.json 不同构，改配置先看对应示例

## 常用命令（活文档·可执行）
- `uv run python orchestrator.py` 编排 CLI（plan → dispatch → loop）
- `uv run python orchestrator.py -n "目标"` 单次执行
- `uv run python mini_panel.py` 精简链路
- `uv run python run_web.py` Web 界面（http://localhost:8080）

## 验证快照（2026-08-24 实际跑过）
- pytest: no tests ran（0 collected / 0 errors，收集干净；dev 组 pytest 9.1.1）
- web: GET / 200 · GET /api/runs 200

## 待办
- [ ] 为 lib/ 核心逻辑补真 pytest 用例（当前 0 collected）
- [ ] 决定是否从 .gitignore 恢复 tests/（新文件现需 git add -f 纳入）

## 活跃坑
- tests/ 目录整体被忽略（新文件需 git add -f）；proposal/、config/*.json 保持忽略不提交
- lib/log.py 遮蔽标准库 logging，import 必须写全 `lib.log`
- run_web.py 常驻阻塞终端，会绑定 0.0.0.0:8080（web_port 可配）