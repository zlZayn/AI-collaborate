# web/ — HTTP + SSE 服务器与单页 UI

- 职责：Web 界面层（run_web.py → server.main），复用 lib/ 执行链
- 被 run_web.py 依赖；读取 output/ 与 config/orchestrator.json

文件索引：
- server.py：ThreadingHTTPServer + SSE 流、API 路由（见下）
- runner.py：WebRunner（状态机与 orchestrator.Harness 同构）+ load_base_config
- index.html：单页 UI（统一卡片系统、marked.js/KaTeX 渲染）
- static/：marked.min.js、katex.min.js、fonts（本地资源，无 CDN）

HTTP 接口（server.py）：
- GET / · /api/state · /api/runs · /api/runs/<id> · /api/runs/<id>/summary · /static/*
- GET /api/stream（SSE 事件流）；POST /api/run（启动新 run 或 followup）· /api/reset
- 端口默认 8080，由 config/orchestrator.json 的 web_port 指定

变更影响路由：改路由或 state 字段 → 同步 [index.html](index.html) 与根 [AGENTS.md](../AGENTS.md)。
工作约束 → 见 [AGENTS.md](AGENTS.md)。