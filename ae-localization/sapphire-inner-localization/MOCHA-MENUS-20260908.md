# Mocha 多级菜单扩展（2026-09-08，运行验收待完成）

## 与旧版区别

旧版 `new_mocha_menu_batch_trial.py` 只有 24 个定长字符串替换；它并非完整 Mocha 汉化。
新候选版本仍直接改造本机 DLL，不使用 JSX，不注入跟踪或渲染算法：

1. `mocha_ui_catalog.py` 从精确版本的 `.text` 提取 `lea r8,[rip+disp32]`；沿短直线路径验证它传给两个经本机反汇编追踪的翻译入口（RVA `0x25B78B0`、`0x25DD700`）。
2. 按异常目录完整长度读取函数范围，并从函数起点解码验证指令边界，防止在指令中间误匹配；不能只依赖 PE 库默认截断的异常记录列表。
3. 词表按 `context + source` 精确匹配，不全局替换相同英文，不修改 objectName、内部参数键、文件后缀或快捷键绑定。
4. 中文 UTF-8 字符串追加至新的只读 `.mcn` 节。仅改被选中的文字地址操作数，原先 `&File` 等短字段不再限制中文长度。保留原助记符（如 `文件(&F)`）。
5. 一个旧版已验证标题 `View controls` 暂保留其定长替换；扫描器尚未覆盖它的构造路径。它单独列在 `legacy_fixed`，不能笼统宣称原文字池完全未改。
6. 每次构建逆向还原所有允许变更的字节，与原文件逐字节比较；另检查调用指令及重定向后的 UTF-8 内容。

Qt 官方说明：翻译使用上下文、源文和消歧信息进行查找；同一英文不能自动认为在所有上下文中具有相同作用。参见 [QTranslator](https://doc.qt.io/qt-6/qtranslator.html)。本项目两个入口地址是特定本机 DLL 的静态追踪结果，不是 Qt 跨版本 ABI 保证。

## 当前范围与边界

- 映射：517 个上下文/源文组合、588 个直接调用点，另保留一个旧版定长标题。
- 主菜单、View 的通道/蒙版/切线/代理等子菜单、布局子菜单、图层右键菜单、基础面板、图层属性、边缘属性、时间轴和关闭项目弹窗已纳入本轮词表。
- 提取器共发现 3615 个直接文字引用，不等于 3615 个可见菜单项，也不证明遍历了全部菜单。
- 尚有首选项、跟踪详细面板、导入/导出窗口、颜色窗口及未知动态构造路径等未覆盖。Sapphire 分发文件也包含 Mocha Pro 其他模块文本，不能认为全部都可从 Sapphire 进入。
- Light3D 的核心、AEX、内部参数和数值未在本轮修改。旧 54 项标题也不能代表其按钮、下拉项、提示已全部汉化。
- 运行时稳定性、中文显示、截断和所有可达界面的覆盖度均待实测，不能把哈希一致或语法检查写成“功能全部正常”。

## 重建

要求 Windows x64、Python 3.13 和匹配 SHA-256 的原始 Mocha UI。输出必须为新文件，且不与原始 DLL 同目录。

```powershell
python -m pip install -r .\scripts\requirements-mocha-ui.txt
python .\scripts\mocha_ui_catalog.py --source '<原始 mocha4bcc.dll>' --output '<新目录>\catalog.json'
python .\scripts\build_mocha_ui_relocated.py --source '<原始 mocha4bcc.dll>' --mapping .\maps\Mocha-context-menu-zh-CN.json --output '<新隔离目录>\mocha4bcc.dll'
python -m unittest discover -s .\tests -v
```

原始输入 SHA-256：`969E1724C74FB4A661043E626FE92E8C29F062038C8D1BF647C99051F23DC029`。
本轮候选 SHA-256：`9141D09D02DD2E303E2BDB6F5BAB21844A441201562A5CE85790489FD0020030`。
重建两次哈希一致；5 个防护测试通过。这些只证明构建及静态检查，不代替运行验收。

## 部署与回退原则

只在 AE 与 Mocha 关闭时替换 `D:\tmp\saprt\l3dao` 内的 UI 副本。部署前验证旧版为 `F5B853EFBEA11AAFB1FBD0226275301CD3758F21FA8A9FC25AA4BB3C0EF50FD1` 并保留独立备份；部署后重新核对候选哈希。原始 BorisFX 安装不变。
回退时先退出 AE/Mocha，再恢复已校验的旧版备份；不卸载、不清缓存、不改效果标识。

## 必须执行的运行验收

使用可丢弃的测试工程，不覆盖用户素材和原工程。

- 展开 File/Edit/Track/View/Movie/Tools/Help 每个菜单；所有有箭头的项继续展开到叶节点，记录完整菜单路径，不只看第一层。
- 检查 View → Channels/Mattes/Layers/Spline tangents/Proxies、Layout 和 Toolbars 分支；记录缺字、英文、布局截断及错误助记符。
- 检查图层列表右键、关键帧右键、导入/导出与首选项弹窗、颜色选择器及悬停提示。未进入/未捕获的页面记为“未验收”，不记为通过。
- 新建样条并进行短帧跟踪，保存返回 AE；对比蒙版/跟踪结果、撤销重做、关键帧及保存重开行为。数据/渲染对比没有完成前，不推广到其他效果。
- Light3D 完整性还需检查加载/保存预设、Edit Mocha 按钮、分组、下拉项、帮助入口、参数关键帧与表达式兼容性。

收集下一批漏译时记录“窗口/菜单路径 → 英文原文 → 截图/实际加载的 DLL 指纹”，再补充对应上下文，而非仅按英文关键字批量替换。
