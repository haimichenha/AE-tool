---
name: grok-software-execution
description: 维护或明确使用 Grok 软件专用旧执行器及共享 Claude CLI 传输层时使用。普通的 Grok 委派走相邻 grok-task-execution；不接管未要求外部模型的软件开发任务。
---

# Grok Software Execution

跨领域持续任务（代码、文档、数据、研究、运维）优先使用相邻的 [grok-task-execution](../grok-task-execution/SKILL.md)。本技能保留软件专用执行器及公共传输依赖；旧 manifest runner 的 ACTION/VERIFY 共用重试计数，不能把最后一次 ACTION 成功但缺少 VERIFY 当作已验收。

普通软件协作默认使用 `grok-task-execution/scripts/invoke-grok-step.ps1`，只发送已审阅的证据包，由宿主执行和验收。不要自动运行本目录的旧 direct/manifest/supervisor 脚本：它们仍含历史默认模型、自动增额逻辑或宽范围读取/执行能力，与推荐适配器的限制不同。

仅当用户明确选择旧执行器，并核对模型、端点、数据范围、工具权限和总预算后才考虑使用。限制和迁移方式见 [接入说明](../grok-task-execution/references/software-stack-integration.md)。本轮共享分类修复不等于旧执行器全面改造完成。

## Required inputs

- Specify one or more existing target roots.
- State acceptance criteria as observable outcomes.
- Begin in `ReadOnly` mode for unfamiliar software, binaries, installers, or external plug-ins.
- Use `Implement` only for authorized, reversible workspace changes.

## Legacy workflow (only after explicit selection and review)

1. Let the runner create a bounded evidence packet from the target roots.
2. Let the same configured Grok model receive only the task card, evidence packet, and acceptance criteria through `claude --bare`.
3. Require JSON evidence IDs, action records, acceptance results, remaining work, and a next action.
4. Treat directory enumeration as phase-one evidence only. Require a concrete content fact from every named script, reference, state, configuration, and text artifact before cross-file conclusions.
5. Reject output that cites unknown evidence IDs, summarizes a file with no matching read record, marks criteria passed without verification, or declares completion while remaining work is non-empty.
6. Only retry with new diagnostic evidence within the approved budget and count limits. Model/permission/quota/budget failures stop the route; the old automatic budget ladder is not authorization to spend more.
7. Report completion only when every criterion is passed; otherwise report the exact blocked or missing-evidence state.

## Anti-fabrication

Listing a path is not reading it. A glob, `ls`, or directory enumeration yields paths only — it yields no frontmatter, no field names, no content summary, no file-type characterization beyond the extension.

Never describe what a file contains without a read record for that exact path. When a claim about content has no read behind it, say the file was listed but not opened, then open it.

## Continuation contract

One criterion passing is not the end of the task. After each verified criterion, move to the next one in the same turn without waiting for a new instruction.

Stop only on: every criterion passed; a denied permission; or a blocker with concrete evidence. Never stop on "the first phase looks complete", on a summary, or on an A/B/C menu offered in place of the work.

When one criterion is blocked, finish every other criterion in full, then report exactly what was left out and why. Narrowing scope is the user's decision, not the runner's.

Do not claim a file, test, backup, or completed action without a matching evidence ID. Do not substitute another model.
