# Grok skills

- `grok-task-execution/` — 通用持续执行入口：任务卡、分阶段验收、断点续跑、证据账本，适用于代码/文档/研究/数据/运维，不限汉化。
- `grok-software-execution/` — 推荐适配器依赖的共享 CLI 传输函数，以及非默认的历史软件执行器。
- `selftest/` — 历史联网验收工具，可能消耗模型额度，不是离线单元测试。
- `archives/` — 历史脚本对照，不作为当前默认入口。

将两个技能文件夹相邻安装到宿主的 skills 目录；通用账本仅需 Python 标准库。可选 Grok 网络调用还需 PowerShell 7、Claude CLI 及用户本机的端点/凭据配置；仓库不包含凭据。

调用示例：`$grok-task-execution 指导 Grok 持续完成当前任务，按任务卡逐项执行、独立验收并保存断点。`

这是宿主监督的持续工作流，不是关闭宿主后仍运行的后台服务，也不保证所有领域都能无人值守。

## 与 SS 的关系

有用，但不是完整的软件开发 skills：SS 管规划、代码学习与产品验收；这里管已获准的 Grok 委派。无需复制 SS 或修改原 AS。工具发现、单一项目状态和旧 runner 的限制见 [接入说明](grok-task-execution/references/software-stack-integration.md)。

推荐从 `grok-task-execution/scripts/invoke-grok-step.ps1` 开始，不自动运行三个旧软件 runner。它们的历史默认模型/预算逻辑仍需专门迁移。

本轮改动与实际测试范围见 [2026-10-22 审阅记录](review-20261022.md)。

从仓库根运行离线测试（不会调用模型）：

```powershell
python -B -m unittest discover -s grok-skills/grok-task-execution/tests -v
```
