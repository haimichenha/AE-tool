# S_Rays 原生副本：Grok受控任务（2026-09-09）

> 本文记录词表及副本试验阶段。用户随后授权的正式替换见 [RAYS-RELEASE-20260909.md](RAYS-RELEASE-20260909.md)；历史副本路径不代表当前扫描入口。

## 当时状态

- 首轮47项词表已生成，但包含“缩放/不透明度”等译义问题，不能直接验收。
- 第二轮Grok前两次输出操作封装JSON不合格，第三次成功写出完整纠正词表。
- 已独立核验全部47个内部键、CP936字节长度、Mocha名称及关键译义。本机确定性构建器已生成原生DLL和AEX，不使用JSX。
- 独立只读VERIFY任务 `rays-native-verify-20260909-c` 已在第1次调用通过：仅验收47项词表及提供的本机构建静态证据，明确DLL由本机构建器生成；不是AE运行验收。见 `observations/rays-grok-verify-20260909.json`。
- **AE运行显示、渲染及完整汉化尚待用户实测。** 标题插入不等于按钮、分组、下拉项目和动态UI都已汉化。

## 隔离产物

- 可见名称：`S_射线副本`；测试匹配名：`R_Rays`。
- 测试入口：AE 2025 `Support Files/Plug-ins/Effects/Sapphire Patch Lab/R_Rays.aex`。
- 依赖根目录：`D:\tmp\saprt\rays09`，不能作为垃圾删除。
- AEX SHA-256：`92F35C21BF36E5A794AF344A61C9641A4F04C28C801AD33B53CD0E3ECDFD0210`。
- DLL SHA-256：`54DB5D9C542AE758C0E9F3803FBA60F830A6B572B5DF1B439605EE2DF8B71BBE`。
- 核心在已验收Light3D/Mocha核心的隔离副本上仅插入Rays标题并重定向一个定义指针；现有机器码未变。
- 继承的Mocha启动根目录仍指向已验收 `D:\tmp\saprt\l3dao`，因此这两个runtime目录均需保留。rays09里的Mocha UI也复制了同一验收版本，但实际启动路径不能只凭文件存在推断。
- 正式S_Rays、Light3D、Mocha以及AE宿主未在本次任务改动。

## 可复现路径

1. 读取 `maps/Rays-zh-CN.json` 和对应 observations，核对源核心指纹。
2. `scripts/build_rays_native_titles.py --source <已验证核心> --mapping maps/Rays-zh-CN.json --output <新目录>/sapphire_ae.dll`。
3. 用 `New-IsolatedSapphireRuntime.ps1` 创建新runtime；其输入为原始安装资源和候选核心，禁止覆盖现存目录。
4. `build_rays_test_aex.py --source <匹配版本的正式S_Rays.aex> --runtime <独立runtime> --output <新R_Rays.aex>`，依赖pefile。
5. 关闭AE后仅安装新的R_Rays.aex；原效果不删。实际比较原/副本的参数、画面、关键帧、保存重开、Mocha调用。

## 连续执行器的实际问题

已有runner将ACTION重试次数和VERIFY共用一个计数。若ACTION恰在最后一轮成功，循环没有下一轮做VERIFY，却留下“moving to VERIFY”的记录并最终失败。必须接一次独立ReadOnly验收，不能重新执行ACTION，也不能把旧超时错误当作最终行为结论。

任务记录位于 `D:\tmp\grok-rays-native-20260908`（首次）与 `D:\tmp\grok-rays-native-20260909`（续跑）。模型原始失败输出保留。中途修复封装并人工复核的候选为过渡版本；当前测试部署已使用Grok最后一轮实际写出的合格词表，不混淆来源。

用户此前指定移除的 `S_射线_复制中文控制.jsx` 在已检查的本机标准脚本及CodexSkills目录中未找到。没有据此声称已删除，也没有删除3D灯光的其他脚本或工程内控件。
