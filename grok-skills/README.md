# Grok skills

- `grok-task-execution/` — 通用持续执行入口：任务卡、分阶段验收、断点续跑、证据账本，适用于代码/文档/研究/数据/运维，不限汉化。
- `grok-software-execution/` — 已有软件专用执行器与共享 CLI 传输函数。
- `selftest/` — 旧执行器验收工具。
- `archives/` — 历史脚本对照，不作为当前默认入口。

将两个技能文件夹相邻安装到宿主的 skills 目录；通用账本仅需 Python 标准库。可选 Grok 网络调用还需 PowerShell 7、Claude CLI 及用户本机的端点/凭据配置；仓库不包含凭据。

调用示例：`$grok-task-execution 指导 Grok 持续完成当前任务，按任务卡逐项执行、独立验收并保存断点。`

这是宿主监督的持续工作流，不是关闭宿主后仍运行的后台服务，也不保证所有领域都能无人值守。
