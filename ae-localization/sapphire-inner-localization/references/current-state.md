> 历史版本记录；当前多效果状态和核心消费者请先读[当前状态](../CURRENT-STATUS-20260913.md)，不要直接重放旧部署。

# 当前状态与正式入口（2026-09-08）

## 用户验收与技术边界

用户反馈：“已经完全汉化了，剩下的对使用没有影响”。据此记录为**用户当前实际使用范围验收通过**；并不意味着自动扫描到的全部字符串都已替换，也不代表所有未使用模块完成验证。

- Light3D 核心：`410C69A61BEC964322550ECC8662D60E454C1984175E2850B4244B02C31A7B91`。
- 用户认可的 Mocha UI：`9141D09D02DD2E303E2BDB6F5BAB21844A441201562A5CE85790489FD0020030`。
- Mocha 映射覆盖 517 个 context/source 组合、588 个文字地址调用点，另保留一个旧版定长标题。
- `observations/mocha-ui-user-acceptance-20260908.json` 是后续用户反馈；较早文件中的 `pending` 是当时历史状态，不应改写抹除。

## 正式 Light3D 入口

在用户接受“共用入口替换、移除 O 测试入口”的范围后：

- 正式文件：`C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore\Sapphire Plug-ins\Sapphire Lighting\S_Light3D.aex`。
- 显示名称：`S_3D灯光`；分组：`S_蓝宝石 光照效果`。
- 内部匹配名：`S_Light3D`，未翻译。
- 新 AEX：`A569D6B564F75A59185C0F2E1A25A3CBA08BD6F8A2435EEB3FE2FE1CD4C3F985`。
- 依赖根目录：`D:\tmp\saprt\l3dao`，不得作为垃圾删除。重启后仍需此路径。
- 此正式入口同时供 AE 与 Premiere 扫描。其他蓝宝石效果未改。
- `O_Light3D.aex` 已移出 AE 插件扫描范围并备份；引用 `O_Light3D` 的测试工程需要重新添加正式效果或恢复测试入口，不能自动视作 `S_Light3D`。
- 目前只有静态部署与身份验证，**替换正式入口后的启动、旧工程加载以及 Premiere 功能仍待单独验收**。

## 重建正式中文 AEX

```powershell
python .\scripts\build_light3d_chinese_entry.py `
  --source '<匹配基线的 S_Light3D.aex>' `
  --output '<新隔离目录>\S_Light3D.aex' `
  --runtime-root 'D:\tmp\saprt\l3dao'
```

支持的源指纹：
- 厂商目录原件：`888BB1C868D1DE4488FABDCF33CCB320400659329DC80F16FBB463B6B8F26D4C`。
- 本机原有中文列表入口：`B65193F4D46F0911D1DCBB0B56583E185D10F70B2A65A7747C1394999E6B97AA`。

构建只改 PiPL 显示名、分组、核心根目录字段与 PE 校验和；保留匹配名及其他字节。构建命令不部署、不删除旧文件。

## 本机回退材料

`D:\tmp\light3d-release-backup-20260908`：
- `S_Light3D.previous.aex`：旧共享入口，SHA-256 为 `B65193F4D46F0911D1DCBB0B56583E185D10F70B2A65A7747C1394999E6B97AA`。
- `O_Light3D.test.aex`：旧测试入口，SHA-256 为 `C5ABE5E85504E80A51C96A895D2C07DAEBF4AC966766F5233CB86913981FCFFD`。
- 退出 AE、PR、Mocha 后按部署记录中的原路径恢复；恢复 Program Files 需要管理员权限。恢复前后验证哈希，不批量回滚其他效果。

这些备份在本机，不随 Git 上传。原 `C:\Program Files\BorisFX` 目录内的核心、UI、厂商 AEX 未改动。
