# AI Collaborate 架构说明

## 设计哲学
- 编排即状态机：进度与结果全部落盘 `state.json`，CLI/Web 只读写该文件，刷新与重启可恢复
- 模块化复用：CLI 与 Web 共用 lib/ 执行链，web/ 只是换成 SSE 推送到浏览器的界面层
- 最小依赖：运行时仅 openai；HTTP 服务器用标准库 http.server，前端静态资源本地化
- 人性化措辞：任务内以“同事”相称，不暴露发送方是模型（agent_rules 约束输出风格）

## 关键决策
- 分阶段分派：同 stage 并发、stage 间串行，后序 stage 只见前序输出，天然承载依赖
- 桥接上下文：stage 间用轻量 LLM 调用压缩前序输出（bridge_S{n}_context.md）；无 bridge 配置时回退逐段 500 字截断
- 规划重试：planner 输出按严格 JSON 解析并校验（字段/模型池/取值范围），错误回喂修正，最多 3 次
- 错误隔离：单 agent 失败标 error，不污染桥接与汇总；某 stage 全部失败则流水线停止
- 状态生命周期：run 四态 pending → running → done / error；summary 独立状态（idle → running → done）
- 产物命名：output/{safe_name(goal)}_{plan_id}/，run 文件 R{n}_{role}_result|_thinking.md，plan_id 为时间戳

## 数据流
- 输入：config/*.json（connection / model_pool / pipeline / agent_rules / web_port）→ orchestrator.py 或 run_web.py
- 规划：goal + 规划 prompt → LLM → plan JSON → 解析校验补修 → state.plan
- 执行：Dispatcher 逐 stage 起线程，输出写 *_result.md / *_thinking.md，状态写 state.runs
- 桥接：stage 间生成 bridge_S{n}_context.md 作为下一 stage 的系统上下文
- 汇总：全部 done 后 summarizer 读各 run 结果文件，合成 summary_*_result.md
- 持续：交互循环与 followup 追加 continue{n}_*_result.md，全部记入 state.json

## 契约
- state.json 字段：plan_id、goal、folder、status、summary_status、plan、runs、bridges、continues
- run 字段：run_id(R{n})、stage_id(S{n})、agent_id(A{n})、role、stage_description、status、result_path、thinking_path、error
- 配置接口：orchestrator.json 用 connection.model_pool.pipeline（多智能体编排）；mini_panel.json 用 api_key.base_url.question.panel（单轮并行面板）——两套不同构
- HTTP 接口（web/server.py）：GET /、/api/state、/api/runs、/api/runs/<id>、/api/runs/<id>/summary、/static/*、SSE /api/stream；POST /api/run、/api/reset
- 端口：默认 8080，由 orchestrator.json 的 web_port 指定

## 防错清单
- 改 state.json 字段即前后端契约变更，必须同步 web/index.html 与 README
- 新增 lib 模块必须被 orchestrator.py 或 web/runner.py 显式 import，无自动发现
- lib.log 遮蔽标准库 logging 名，引用一律写 `lib.log`，禁止裸 `import log`
- 产物路径一律经 lib/safe_name.safe_name() 生成，避免非法文件名字符