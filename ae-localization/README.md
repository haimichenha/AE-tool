# AE 汉化材料

- [Sapphire／Mocha 汉化技能](sapphire-inner-localization/SKILL.md)：Light3D 参数、多级菜单、中文效果名、版本锁重建和回退。
- [当前验收与正式入口](sapphire-inner-localization/references/current-state.md)：最新状态，区分用户验收与尚未完成的正式入口启动验证。
- `adobe-host/`：已有 AE/PR 宿主辅助脚本。
- `red-giant-universe/`：已有 RG/Universe 界面与恢复脚本。
- `legacy-jsx/`：历史 JSX 工具，独立保存；不是当前原生 DLL 汉化方案。

脚本可能使用本机路径，运行前核对版本和路径，不自动迁移到其他版本。
Sapphire 的历史重建步骤见 [REPRODUCE.md](sapphire-inner-localization/REPRODUCE.md)，基线工件指纹见 [artifacts.manifest.json](sapphire-inner-localization/artifacts.manifest.json)。当前菜单扩展和入口替换指纹见最新状态文档及对应 observations。

保留失败试验和历史观察以追溯原因，不将它们作为当前推荐部署方案。
仓库保存文本源、映射、测试及证据；厂商二进制、账号凭据和本机回退备份不在 Git 内。
