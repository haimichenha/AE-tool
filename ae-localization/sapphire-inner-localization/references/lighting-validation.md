# 可复用的离线与宿主验证

以下命令在技能目录执行。工具不会安装插件、启动 AE、修改首选项或访问账号；AE 脚本由操作者在确认宿主范围后单独运行。

## Python 检查

```powershell
python -X utf8 -m pip install -r scripts/requirements-lighting.txt
python -X utf8 -m unittest discover -s tests -v
```

Python 3.10+；可选 Node.js 宿主模型测试覆盖菜单重复命令和用户切换工程，没有启动 Adobe。无厂商二进制也可运行离线测试；真实 DLL 重建另需准确版本。依赖版本是本次验证版本，不是对所有未来版本的承诺。

## 配置式原生菜单诊断

创建 JSON 配置，使用自己的素材和专用诊断目录：

```json
{
  "media_path": "D:/fixtures/source.mp4",
  "work_dir": "D:/validation/session-01",
  "tag": "before",
  "time_seconds": 1,
  "cases": [
    {"name": "Solo", "effects": ["S_LensFlare"]},
    {"name": "AB", "effects": ["S_LightLeak", "S_LensFlare"]},
    {"name": "BA", "effects": ["S_LensFlare", "S_LightLeak"]}
  ]
}
```

```powershell
python -X utf8 scripts/prepare_lighting_probe.py --config probe.json --output before.jsx
```

生成器仅输出 JSX，拒绝覆盖已有文件。宿主脚本要求空且未保存的项目，首次存盘后固定项目路径；操作前再验证，用户切换项目时停止并取消自动退出。名称通过 JSON 编码注入，不拼接脚本字符串。

脚本在首次添加前缓存菜单 ID；添加后检查效果数量和 matchName；叠加完成后再读取所有实例。记录使用 `REPAIR_BEGIN/END` 及最后的 `ALL_ADDED` 标记。没有最后标记就是未完成，不以已有 AEP 文件存在判定成功。

每个实例标签为 `案例名__序号__内部效果名`，支持同一效果重复叠加。生成 after 项目时换 tag，不覆盖 before。配置的 span_frames 是时间跨度，不保证宿主恰好输出该数量文件。

## 比较参数与帧

```powershell
python -X utf8 scripts/lighting_regression.py `
  --before-project before.aep --after-project after.aep `
  --expected-instances 5 `
  --allow-name-change Solo__1__S_LensFlare `
  --allow-name-change AB__2__S_LensFlare `
  --allow-name-change BA__1__S_LensFlare `
  --before-frames before-frames --after-frames after-frames `
  --expected-frames 6 --output comparison.json
```

实例和帧的预期数来自本次已核验的完整基线，不直接照抄示例。工具检查完整标记、唯一实例、连续参数索引、字段一致及允许改变名称的实例；不默认允许所有名称变化。

帧必须集合相同、格式／尺寸／类型相同，使用整数 TIFF 精确比较。任意像素差异都会返回失败并保留报告，不设置静默容差。需要进一步控制或解释时另外记录，不把结果改成通过。

进行核心／入口对照时，使用同一个已保存的 before 工程渲染，保留前一组文件后才生成后一组。确保宿主真正结束和文件到齐，必要时核对输出时间及哈希。不要让 renderer 覆盖唯一证据。

## 还需要人或 UI 测试的部分

原生菜单自动化不是鼠标操作的完全替代。预设浏览器、眩光／光晕样式编辑器、Mocha、旧项目引用、关键帧／表达式和 Premiere 分别验收。以实际反馈归档，不因为主面板中文或无损帧一致就标记全部完成。
