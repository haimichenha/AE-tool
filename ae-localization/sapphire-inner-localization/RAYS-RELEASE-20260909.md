> 历史版本记录；当前多效果状态和核心消费者请先读[当前状态](CURRENT-STATUS-20260913.md)，不要直接重放旧部署。

# 正式 S_射线入口（2026-09-09）

用户反馈副本“看着已经汉化完成”，随后明确授权替换原效果。此记录仅表示可见界面反馈，不覆盖未测试功能。

## 已部署

- 正式文件：`C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore\Sapphire Plug-ins\Sapphire Lighting\S_Rays.aex`。
- 中文显示名：`S_射线`；内部匹配名始终为 `S_Rays`。
- AEX SHA256：`914F931DC9517863D5CB9012474938C1AC8FCACF06B6E2F7A0F80D1FAEA289E1`。
- Rays核心：`D:\tmp\saprt\rays09\lib64\sapphire_ae.dll`，SHA256 `54DB5D9C542AE758C0E9F3803FBA60F830A6B572B5DF1B439605EE2DF8B71BBE`。
- 继承的Mocha启动依赖仍为 `D:\tmp\saprt\l3dao`。两个runtime目录均不可清理。
- 共享入口同时影响 AE 与 Premiere；本次未改其他效果或厂商原件。
- 构建仅改正式AEX的核心根目录与PE校验和，保持全部PiPL属性和机器码。备份输入的第二次构建逐字节一致。
- 正式入口的启动、旧工程加载、关键帧、保存重开、渲染与Mocha调用仍需运行验收。

## 测试入口与回退

`R_Rays.aex` 已从 AE 的 `Sapphire Patch Lab` 目录移除；备份保留在 `D:\tmp\rays-release-20260909\backup\R_Rays.test.aex`。

**用过 R_Rays 的测试工程不会自动改为 S_Rays**：需要重新添加正式 `S_射线`，或临时恢复测试入口。不要把测试匹配名更改造成的缺失误判为正式 S_Rays 兼容性结论。

正式入口旧文件：`D:\tmp\rays-release-20260909\backup\S_Rays.previous.aex`，SHA256 `7040173BBD4D2C15AA42E4CB97E6246A0131AB3B651140F51CE29F701D481274`。

退出 AE/PR/Mocha 后，以管理员权限仅将这个备份复制回上述正式路径，再核对哈希。需要恢复测试工程时仅将 `R_Rays.test.aex` 恢复到原 Patch Lab 路径并命名 `R_Rays.aex`。不要批量回滚 Light3D、Mocha 或 RG。

## 重建

```powershell
python ./scripts/build_rays_native_titles.py --source '<匹配的已验收核心>' --mapping ./maps/Rays-zh-CN.json --output '<新目录>/sapphire_ae.dll'
# 按 RAYS-GROK-WORKFLOW-20260909.md 准备独立runtime，核对核心哈希。
python ./scripts/build_rays_chinese_entry.py --source '<匹配的旧S_Rays.aex>' --output '<新目录>/S_Rays.aex' --runtime 'D:/tmp/saprt/rays09'
```

脚本只构建，不提权、不自动部署；部署记录在 `observations/rays-formal-deployment-20260909.json`。普通权限首次复制被系统拒绝，随后使用正常 Windows UAC 管理员授权完成；没有修改ACL。
