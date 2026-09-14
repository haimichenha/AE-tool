---
name: ae-tool
description: 在 AE-tool 仓库中开展 After Effects／Premiere 原生插件汉化、验证、回退及技能维护时使用。先按目标插件选择专项技能，不把历史试验当作当前安装状态。
---

# AE-tool 项目入口

- **Sapphire 光照效果、多轮汉化、Light3D／Mocha**：进入 [Sapphire 专项技能](../ae-localization/sapphire-inner-localization/SKILL.md)，不要默认只处理 Light3D 或只修改效果列表名称。
- **Adobe 宿主或 Red Giant／Universe**：先查阅 `ae-localization/adobe-host/` 或 `ae-localization/red-giant-universe/` 中对应材料；Sapphire 的版本指纹、偏移和依赖不适用这些模块。
- **Grok 任务执行技能**：位于 `grok-skills/`，与插件运行库分开维护。

当前状态只由专项技能指定的一份状态文档管理。历史文件保留当时结论，不通过不断插入“最新”段落覆盖彼此。

用户要求继续时，读取已有验收和明确范围后推进可做工作；不要重复索取已给出的确认。构建、验证、安装、提交分别说明结果。某项安装受阻，不应停止不受阻的词表整理、离线构建或证据分析，也不能换命令绕过拒绝。

发布仅包含相关源码、词表、测试和适量脱敏记录。排除厂商二进制、用户工程、素材、转储和凭据；未提交的其他模块不混入本次提交。
