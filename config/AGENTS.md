# config/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

config/ 特有约束（安全敏感目录）：
- config/*.json（真实配置）严禁 git add / commit，含 `-f`；文件含真实 API key
- 密钥只进环境变量，不入代码与文档；新代码用 `os.environ.get()`
- 改任一配置字段结构 → 必须同步 [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 契约节
- 文件职责 → [README.md](README.md)