# AE-tool

Two self-contained source areas:

- `ae-localization/` — Adobe host, Red Giant Universe, and Sapphire localization research/scripts.
- `grok-skills/` — General Grok task-continuation skill, software adapters, tests, and archived script lineage.

## Skill entry

Start at [skills/SKILL.md](skills/SKILL.md). For multi-effect Sapphire localization, use the [specialist skill](ae-localization/sapphire-inner-localization/SKILL.md), its single current-state ledger, and configuration-driven regression tools.

## Distribution boundary

This repository contains only text source, mappings, deployment records, and observations. It deliberately excludes vendor DLL/AEX/EXE files, installation packages, license material, and credentials. Use only with software you are entitled to use and make a backup before applying any script.

## Layout

- `ae-localization/adobe-host/`: AE/PR host automation and localization helpers.
- `ae-localization/red-giant-universe/`: RG/Universe panel and restoration scripts.
- `ae-localization/sapphire-inner-localization/`: Sapphire Lighting multi-effect localization, Light3D/Mocha mappings, regression tools, and scoped observed outcomes. `trials/` binaries are intentionally not published.
- `ae-localization/legacy-jsx/`: Existing JSX helpers, retained separately from direct-DLL work.
- `grok-skills/grok-task-execution/`: General host-supervised Grok work/verify/resume workflow for code, documents, research, data, and operations.
- `grok-skills/grok-software-execution/`: Shared CLI transport dependency and legacy, non-default software runners.
- `grok-skills/selftest/`: Historical online harness (may incur model charges), not the offline test suite.
- `grok-skills/archives/`: Earlier saved script versions for comparison.

No prebuilt plugin, DLL, AEX, executable, or key is required to inspect the repository.

For software-development planning and learning, use an optional SS skill alongside the bounded Grok executor; this repository does not yet publish the separate SS package. See [Grok skills and SS integration](grok-skills/grok-task-execution/references/software-stack-integration.md). No AS repository, model configuration, or installed skill is changed just by inspecting this repository.
