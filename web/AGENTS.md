# web/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

web/ 特有约束：
- server.py 只允许标准库，禁止新增第三方运行时依赖（前端依赖已本地化）
- index.html 与 server.py 的路由、state 字段是前后端契约，改一处必须同步另一处
- 新静态资源放 [static/](static/)，用相对路径引用