# 版本锁定的构建配方（仅候选，不安装）

在技能目录执行；以下源文件由操作者提供，不随仓库分发。CLI 输出到新隔离目录；先阅读工作流程中的身份、消费者和验收门槛。

## 16 效果标题 → 按钮 → 布局 → 空参数保护

```powershell
python -X utf8 scripts/build_lighting_remaining_titles.py --source BASE_410C.dll --mapping maps/Lighting-remaining16-zh-CN.candidate.json --output stage/01/sapphire_ae.dll
python -X utf8 scripts/build_preset_button_captions.py --source stage/01/sapphire_ae.dll --output stage/02/sapphire_ae.dll
python -X utf8 scripts/build_lightleak_layout.py --source stage/02/sapphire_ae.dll --output stage/03/sapphire_ae.dll
python -X utf8 scripts/build_empty_args_guard.py --version rem16 --source stage/03/sapphire_ae.dll --output stage/04/sapphire_ae.dll
```

各层精确输入锁由脚本执行，不能混用版本或调换顺序：

| 层 | 对应指纹前缀／范围 |
|---|---|
| 已验收 Light3D/Mocha 基础 | `410C69A6…`，并非纯厂商代码 |
| 剩余16效果、26定义、1093标题 | `5141659F…` |
| 两个右侧预设按钮 | `23425CFF…`，识别字符串不变 |
| 漏光真实布局与语义修正 | `28523507…` |
| 空启动参数保护 | `F80B250E…` |

基础核心已经包含 CP936 标题处理及 Mocha 启动改动，不能将整个产物称作“只有文字”。核心的具体消费者由安装机决定；构建16项不表示发布16项。

眩光使用 `build_glare_native_titles.py` 与 `maps/Glare-zh-CN.candidate.json`，再加右侧按钮及 `--version glare01` 保护。六个早期效果使用 `build_lighting_batch_titles.py` 和对应 batch01 词表；另四效果的中间候选由 `build_lighting_batch02_titles.py` 保留。不要把重叠候选叠加到已经包含这些定义的核心上。

## 生成正式入口

```powershell
python -X utf8 scripts/build_lighting_canonical_entry.py --effect S_LensFlare --source ORIGINAL_S_LensFlare.aex --runtime-root D:/runtime/rem16 --output stage/entry/S_LensFlare.aex
```

此工具对23个已记录源版本保留整个活跃 PiPL、内部 S_* 名称和可执行节，只改变短 ASCII 根路径及校验和。使用准确的原始备份；不拿当前已重定向 AEX 当源。Light3D/Rays 使用各自历史专用入口构建器，不在这23项源锁中。

`build_lighting_remaining_aex.py` 生成的是 R_ 测试副本，**不是正式入口替换工具**。不能将其输出改文件名后覆盖 S_*。

入口指向的 runtime 必须事先具备所需完整依赖，并在安装前核对核心/manifest/其他消费者。生成器不自动复制依赖、安装或移除副本；所有生成结果都保持 `installed=false`。

基础核心的 Mocha 启动根参数仍依赖既有 l3dao 运行库，不会自动跟随新 AEX 根目录。跨机器或改根需使用专用 Mocha 根参数重定位方案并重新验收，不能只改文件夹名称或全局替换启动格式串。
