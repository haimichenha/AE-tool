# 任务卡、模型请求与宿主回执

## 任务卡

将下例的根目录、模型和端点替换成当前获准值。任务卡不存凭据。任务标准应覆盖交付物、实际使用及回归要求；不是只检查文件存在。

```json
{
  "objective": "整理已提供数据并生成可核对的统计报告",
  "model": "<明确选择的 Grok 模型>",
  "endpoint_origin": "https://<获准主机>:<端口>",
  "authorization": "用户允许处理该目录的数据；外传仅限脱敏汇总；不发布报告",
  "roots": ["D:/approved-project"],
  "limits": {"max_steps": 12, "max_work_attempts": 2, "max_verify_attempts": 2, "max_seconds": 1800},
  "tasks": [
    {"id": "data", "mode": "ReadOnly", "goal": "核对输入字段、缺失值与总数", "depends_on": [], "criteria": {"A1": "与原始行数及字段读回一致"}},
    {"id": "report", "mode": "Implement", "goal": "在输出目录生成报告", "depends_on": ["data"], "criteria": {"A1": "统计数字可重算", "A2": "报告渲染检查没有遮挡和缺页"}}
  ]
}
```

```powershell
python ./scripts/task_state.py --state D:/approved-state/state.json init --card D:/approved-state/card.json
python ./scripts/task_state.py --state D:/approved-state/state.json next
python ./scripts/task_state.py --state D:/approved-state/state.json begin --task data --phase work
```

状态路径必须在允许写入区域。账本不是权限沙箱：roots/authorization 供宿主约束工具与数据外传，脚本自身只读写账本和证据。不能把设置了 roots 当成阻止外部进程访问其他路径的技术保证。

## 单次模型请求

```json
{
  "task_id": "data",
  "phase": "work",
  "goal": "检查给定汇总是否存在不一致；未提供的原始数据不能声称已读",
  "criteria": {"A1": "指出总行数与各类数量是否一致"},
  "evidence": [{"id": "E1", "source": "host readback", "text": "已脱敏的实际证据摘要"}],
  "feedback": "首次调用；无历史输出"
}
```

```powershell
./scripts/invoke-grok-step.ps1 -RequestFile D:/approved-state/request.json `
  -OutputDirectory D:/approved-state/call-001 -Model '<指定模型>' `
  -ExpectedOrigin 'https://<获准主机>:<端口>' -TimeoutSeconds 240 -MaxBudgetUsd 0.50
```

`ExpectedOrigin` 与本机配置的 scheme/host/port 必须一致。使用该适配器即会将 request JSON 发给该端点；调用前审核整个 JSON。不传未经授权的私人文件、完整仓库或凭据。`contract_valid` 仅检查响应身份和阶段，不等于验收。

遇到格式不合格或传输错误，保留结果并由账本管理有界重试。空输出不是“已完成”。verify 请求换成动作后的新证据，不重发写操作。

## 宿主回执

先执行本地检查并保存输出，计算证据 SHA256，再写以下回执。**不得直接把模型 JSON 当作回执**。

```json
{
  "task_id": "data",
  "phase": "work",
  "attempt": 1,
  "reviewer": "host",
  "outcome": "ready_for_verify",
  "note": "宿主实际读取了获准文件并保存统计结果；未修改输入",
  "evidence": [{"id": "E1", "path": "D:/approved-state/readback.json", "sha256": "<实际SHA256>"}]
}
```

```powershell
python ./scripts/task_state.py --state D:/approved-state/state.json record --receipt D:/approved-state/receipt.json
python ./scripts/task_state.py --state D:/approved-state/state.json next
```

work 可返回 `ready_for_verify`、`retry`、`blocked`。
verify 可返回 `passed`、`retry`、`rework`、`blocked`。
retry 还必须给 `safe_to_retry: true`，并在 note/evidence 中记录为何确定没有未知副作用。

verify 通过回执增加：

```json
{
  "outcome": "passed",
  "acceptance": {"A1": {"verdict": "passed", "evidence_ids": ["E1"]}},
  "remaining_work": []
}
```

上述字段并入完整回执，保留 task_id/phase/attempt/reviewer/note/evidence。每个 criterion 都要有通过证据。证据日志应保存在不会被下一步覆盖的位置；将产物哈希、命令、退出码写入日志，不能只引用稍后必然变化的工作文件。

账本能校验引用和哈希，不能证明人工审核诚实或语义正确；宿主仍需阅读证据。预算、中断、拒绝均不允许伪造 passed。

## Version 2：每一步的有效进展

新建账本采用version=2；旧账本保留原版恢复语义，不在续跑时暗改验收标准。
`ready_for_verify`、`passed` 和 `rework` 回执必须额外包含：

```json
"progress": {
  "kind": "evidence_added",
  "summary": "对应A1：实际读取输入并发现缺失行，下一步需要修正汇总",
  "evidence_ids": ["E1"]
}
```

kind可选artifact_changed、evidence_added、validation_run、blocker_isolated。verify实际执行验证通常用validation_run。retry回执还需retry_reason说明条件变化或有界瞬时故障依据。只有模型解释、换了命令字符串或改了日志时间戳不能证明有效进展；宿主要核对结果与目标的联系。
