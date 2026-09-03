---
name: grok-software-execution
description: Run evidence-gated software investigation, implementation, and verification through the configured Grok model without switching models. Use when a Claude Code task must keep progressing through inspect, act, verify, and acceptance; when Grok previously stopped after a summary, ignored the target directory, or gave unsupported conclusions.
---

# Grok Software Execution

Run `scripts/run-grok-direct-task.ps1` for normal software tasks: Grok directly reads files, runs permitted commands, edits authorized target roots, then verifies. Use `run-grok-software-task.ps1` only when direct tools are unavailable and a constrained manifest fallback is required.

## Required inputs

- Specify one or more existing target roots.
- State acceptance criteria as observable outcomes.
- Begin in `ReadOnly` mode for unfamiliar software, binaries, installers, or external plug-ins.
- Use `Implement` only for authorized, reversible workspace changes.

## Workflow

1. Let the runner create a bounded evidence packet from the target roots.
2. Let the same configured Grok model receive only the task card, evidence packet, and acceptance criteria through `claude --bare`.
3. Require JSON evidence IDs, action records, acceptance results, remaining work, and a next action.
4. Treat directory enumeration as phase-one evidence only. Require a concrete content fact from every named script, reference, state, configuration, and text artifact before cross-file conclusions.
5. Reject output that cites unknown evidence IDs, summarizes a file with no matching read record, marks criteria passed without verification, or declares completion while remaining work is non-empty.
6. Re-run the same Grok model with the validation failure as feedback, up to the configured retry limit.
7. Report completion only when every criterion is passed; otherwise report the exact blocked or missing-evidence state.

## Anti-fabrication

Listing a path is not reading it. A glob, `ls`, or directory enumeration yields paths only — it yields no frontmatter, no field names, no content summary, no file-type characterization beyond the extension.

Never describe what a file contains without a read record for that exact path. When a claim about content has no read behind it, say the file was listed but not opened, then open it.

## Continuation contract

One criterion passing is not the end of the task. After each verified criterion, move to the next one in the same turn without waiting for a new instruction.

Stop only on: every criterion passed; a denied permission; or a blocker with concrete evidence. Never stop on "the first phase looks complete", on a summary, or on an A/B/C menu offered in place of the work.

When one criterion is blocked, finish every other criterion in full, then report exactly what was left out and why. Narrowing scope is the user's decision, not the runner's.

Do not claim a file, test, backup, or completed action without a matching evidence ID. Do not substitute another model.
