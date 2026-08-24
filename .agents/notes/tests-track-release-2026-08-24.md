# 决策：tests/ 放开 gitignore 跟踪（2026-08-24）

已实施

## 问题
- tests/ 曾整目录忽略，双件与探针脚本需逐文件 -f 强加，入库状态与目录忽略规则互相矛盾

## 决策
- 从 .gitignore 删除 tests/ 条目，tests/ 下全部文件正常入库
- thinking_output.md（探针产物）一并入库，接受其随探针运行产生 diff 的噪声

## 替代方案（强制）
- 保持整目录忽略 + 逐文件 -f：每个新测试文件都需记住 -f，规则与事实长期矛盾 → 拒绝
- 只恢复源码、忽略产物：需新增细粒度 .gitignore 规则，维护成本与收益不成比例 → 拒绝

## 影响
- tests/ 新文件直接 git add 即可
- 探针产物 thinking_output.md 入库后每次运行产生 diff（已记入根 AGENTS.md 活跃坑）