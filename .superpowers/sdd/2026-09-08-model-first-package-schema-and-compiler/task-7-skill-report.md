# Task 7 skill report

## Scope and ruling

Updated only `.codex/skills/migrate-hangboard-to-3d/SKILL.md` and this report.
No app code, production staging code, board package, schema, generated asset,
server, or simulator was changed.

The migration skill now directs operators to inspect staging first. When the
existing stager already recursively copies the parser-approved regular-file
package tree, production staging remains unchanged and the model behavior is
covered by a characterization fixture/test.

## Durable staging contract

- A v2 model fixture proves staged USDZ and generated descriptor bytes are
  identical to their source bytes.
- Staged assets must exactly match the parser-declared inventory.
- Staging never synthesizes, renames, replaces, or app-side substitutes model
  resources.
- Generated staging directories and resources are recorded and cleaned.

These rules are integrated beside the existing package validation, staging,
sync, and Workbench guidance; no task counts, commit history, or fixture
trivia were added to the skill.

## Review and validation basis

The Task 7 final review confirmed that the existing staging implementation
discovers parser-approved packages and recursively copies regular files with
byte-preserving semantics, and that its characterization test checks exact
USDZ/descriptor bytes and the complete staged inventory. The skill records
that behavior as a reusable rule without introducing model-specific staging
logic.

```text
.context/hangboard-packages-venv/bin/python -B \
  /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .codex/skills/migrate-hangboard-to-3d
Skill is valid!

rtk git diff --check
exit 0
```

No runtime suite was needed for this documentation-only update; the focused
staging/model-first suites and final inventory remain covered by the reviewed
Task 7 characterization evidence.

## Resource lifecycle

This update created no persistent resource, HTTP server, tunnel, simulator, or
generated staging directory. No cleanup was required beyond the normal
workspace diff.
