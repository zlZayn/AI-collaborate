# 决策：文档结构标准化（2026-08-24）

已实施

## 问题
- 项目无根 AGENTS.md、docs/ARCHITECTURE.md、.agents/notes/，子目录无双件
- README.md 与 README_zh.md 核对后与代码一致，缺的是结构层而非内容层

## 决策
- 按 maintenance-flow 技能落地三档结构：根 AGENTS.md 仪表盘 + docs/ARCHITECTURE.md + lib/、web/、tests/ 双件
- 架构文档统一放 docs/ARCHITECTURE.md，根目录不放独立 ARCHITECTURE.md
- 决策记录统一放 .agents/notes/，不建索引文件
- output/、proposal/ 等数据/产物目录不建双件

## 替代方案（强制）
- 保持现状不补文档：Agent 无上下文注入，违背可维护目标 → 拒绝
- 根目录平铺 ARCHITECTURE.md：违反统一规则（根只留指针，架构正文下钻 docs/）→ 拒绝
- 全部子目录建双件：output/（运行时产物）与 proposal/（提案）文档价值低，只为核心源码目录建 → 拒绝

## 影响
- 新建 9 个文档文件，0 行功能代码改动
- README.md / README_zh.md 核对后确认一致，未改动
- 遗留：tests/test_think.py 非 pytest 用例、tests/ 与 proposal/ 被 gitignore（见根 AGENTS.md 待办）