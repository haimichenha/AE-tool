---
name: sapphire-inner-localization
description: 汉化 After Effects 的 Sapphire Light3D／Rays 参数面板及内置 Mocha 界面，重建版本锁定的 DLL 补丁，处理多级菜单遗漏、中文 PiPL 名称和隔离验证。用于原生插件显示层汉化，不使用 JSX，不默认推广到其他插件版本。
---

# Sapphire／Mocha 原生显示层汉化

## 先选择工作路径

- **S_Rays 原生汉化与正式入口**：读 [Rays 发布记录](RAYS-RELEASE-20260909.md) 与 [Grok 词表构建过程](RAYS-GROK-WORKFLOW-20260909.md)，使用版本锁定的 `build_rays_native_titles.py` / `build_rays_chinese_entry.py`；不能使用 Light3D 偏移。

- **检查当前已验收版本、部署或回退**：先读 [当前状态与入口替换](references/current-state.md)。
- **Light3D 参数标题重建**：读 [REPRODUCE.md](REPRODUCE.md)，依序使用 `scripts/new_light3d_bulk_trial.py` 与 `scripts/new_mocha_root_thunk_trial.py`。该历史构建链使用固定 `D:\tmp` 路径，输出拒绝覆盖。
- **Mocha 漏译／多级菜单扩展**：读 [菜单方案](MOCHA-MENUS-20260908.md)，使用 `scripts/mocha_ui_catalog.py`、`maps/Mocha-context-menu-zh-CN.json`、`scripts/build_mocha_ui_relocated.py`。安装 `scripts/requirements-mocha-ui.txt` 中固定依赖。
- **中文效果名及替换旧入口**：用 `scripts/build_light3d_chinese_entry.py` 生成候选；部署前按当前状态文档检查共享宿主范围和测试工程兼容性。

## 必须保留的区分

1. **显示名不是内部标识**：PiPL `eman` 为可见名称，`ANMe` 为匹配名。正式入口保持 `S_Light3D`；中文显示名为 `S_3D灯光`。不能把匹配名或 DSL 参数键翻成中文。
2. **两套编码不能混用**：已验证环境 Light3D title / PiPL 使用 CP936；Mocha 界面使用 UTF-8。其他系统区域设置须重测。
3. **Mocha 不从测试 DLL 目录自然继承路径**：当前核心通过保留 `%s\lib64\mocha-wrapper.exe` 格式、重定向根目录参数来启动隔离运行时。历史直接替换整个格式串的尝试失败，`new_mocha_wrapper_redirect_trial.py` 不是有效构建步骤。
4. **Mocha 短文字不必压缩译文**：优先按 context/source 定位到已验证翻译调用，把 UTF-8 放入只读新节，只改变文字地址。不要全局替换同名英文、快捷键或内部 objectName。
5. **版本锁**：只对脚本支持的输入 SHA-256 执行补丁，版本不符停止并重新定位，不能移除哈希检查继续。

## 执行与证据

- 先记录当前输入、部署副本、Git 状态与宿主进程，保留已可用版本。
- 补充词表时记录菜单完整路径与上下文。箭头子菜单继续展开到叶节点；参数面板、右键菜单、弹窗和悬停提示分别验收。
- 在新目录构建，核对输入/输出哈希、占位符、助记符和允许修改的字节范围。`tests/` 用于防护检查；真实重建还需版本匹配的本机二进制。
- 模块 `.text` 里的文字寻址操作数可变化，不得笼统宣称“未改代码”。检查动作调用目标、其他指令和原数据保持不变。
- 静态检查、重复构建、用户实测分别记录，不把其中一项写成全部功能已证明。
- 部署只处理用户指定效果；对 Program Files 的修改需管理员权限。共享 MediaCore 会影响 AE 与 Premiere，替换范围需先说明。先退出相关宿主并验证备份，再替换；不强制结束有未保存工作的进程。
- “移除旧入口”优先移出插件扫描目录并保留哈希校验过的备份，而不是销毁唯一回退副本。隔离 runtime 被正式入口引用后是必需依赖，不是临时垃圾。

## 复用边界

当前用户已接受 Light3D／Mocha 的日常使用汉化效果；DLL 内仍存在未映射或不可达的其他上下文。正式 `S_Light3D` 入口替换需单独启动验收。迁移到其他蓝宝石效果前重新核对 DSL 定义、参数键、指针引用、下拉项、预设、表达式与渲染结果，不能仅复制本例偏移。

## 仓库保存范围

本仓库保存技能、脚本、词表、测试与观察记录。当前 `.gitignore` 不纳入 DLL/AEX、账号、凭据或运行日志；不把 Git 文本归档当成二进制备份。上传前只暂存本任务明确文件，保留 Grok 目录与其他工作不变。
