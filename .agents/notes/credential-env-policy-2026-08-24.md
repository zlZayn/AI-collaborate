# 决策：密钥环境变量化——探针凭据改造（2026-08-24）

已实施

## 问题
- tests/test_think.py 曾从 config/orchestrator.json 读 key（无效 key 导致 pytest 收集期 401）
- config/orchestrator.json 与 mini_panel.json 含真实 key，只能靠 gitignore 保护，无法机器校验

## 决策
- 探针脚本改名 tests/think_probe.py 且凭据改环境变量：OPENAI_API_KEY 必填、OPENAI_BASE_URL / OPENAI_MODEL 可配（commit 00a92d5）
- config/ 真实 json 永不入库：gitignore + [config/AGENTS.md](../../config/AGENTS.md) 规则双保险

## 替代方案（强制）
- 继续从 gitignore 的 config 读 key：key 有效性无机器校验，改配置即破，无法在 CI/收集期复现 → 拒绝
- 硬编码 key 进脚本：密钥一旦入历史无法清除 → 拒绝
- 引入 .env + python-dotenv：多一个运行时依赖，与最小依赖约束冲突 → 暂不采用，环境变量已满足探针需求

## 影响
- 探针脚本零密钥、零配置依赖，pytest 收集不再触网
- 运行时入口（orchestrator.py / mini_panel.py / web）仍读 config json 真实 key，属现状；迁移为环境变量是可选后续，未实施
- 真实 key 仍存于 gitignored config/*.json，勿外传