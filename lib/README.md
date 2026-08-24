# lib/ — 核心执行链库

- 职责：LLM 客户端、规划解析、分派执行、上下文、汇总、事件总线
- 被 orchestrator.py、web/runner.py、mini_panel.py 依赖

文件索引（职责 / 关键导出 / 被谁依赖 / 改后必测）：
- client.py：OpenAI 封装（chat / stream_to_file / stream_print）；改后必测 CLI 与 Web 流式输出
- planner.py：parse_plan（JSON 容错解析）+ validate_plan（字段/模型池/范围校验）；被 orchestrator 与 WebRunner 共用
- dispatcher.py：分阶段并发分派、run 状态与产物路径生成；被 orchestrator 与 WebRunner 共用
- context.py：build_context / read_file；被 orchestrator、summarizer 依赖
- summarizer.py：run_summary 汇总，输出 summary_*_result.md；被 orchestrator 与 WebRunner 依赖
- broadcaster.py：SSE 事件总线（subscribe / emit）；被 web/server.py 使用
- constants.py：STATUS_DONE/RUNNING/PENDING/ERROR；被多方依赖
- log.py：线程安全日志缓冲（phase / task_done / task_error / flush）
- safe_name.py：文件名安全化（去空格、去非法字符、截断 40 字符）

变更影响路由：改 lib/ 对外接口 → 同步根 [AGENTS.md](../AGENTS.md) 待办/坑 + 架构影响写 [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)。
工作约束 → 见 [AGENTS.md](AGENTS.md)。