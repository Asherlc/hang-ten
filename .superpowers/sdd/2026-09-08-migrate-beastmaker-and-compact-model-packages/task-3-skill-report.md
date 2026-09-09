# Task 3 migration-skill evidence-gate report

Reviewed 2026-09-09 against `AGENTS.md`, the full migration skill,
`skill-creator`, `writing-skills`, `test-driven-development`, the Stage 0
evidence reviews, and the runtime Task 1 skill review.

## Change

The migration skill now requires a per-board multi-angle visual evidence gate
before Astra geometry. Each exact-revision set must contain at least two
materially distinct retained visual snapshots with actual bytes, SHA-256
hashes, source URL/publisher, and view labels. The rule asks for manufacturer
front plus oblique/side/back/profile evidence when available, requires
manufacturer-first sourcing, and permits an authorized retailer/distributor
only as clearly tiered, documented missing-angle evidence. It records what
each view does and does not support, requires human approval of the exact set,
and sends every approved image to Astra. It rejects duplicate crops/variants,
profile-less diagrams, search thumbnails, generated renders, legacy raster
assets/paths, and ambiguous revisions; missing trustworthy second views stop
the gate and ask the human.

The approved exact simulator-name rule remains unchanged. The unsupported
SwiftPM recovery paragraph was removed after the runtime review found an
honest 0/3 no-skill RED baseline for that behavior; no unproven recovery
requirement remains in this skill.

## RED evidence

The triggering RED observation is the actual prior migration event supplied by
the task: only one straight-on Beastmaker image was handed to Astra and
geometry began before the need for a second, materially different view was
recognized. This is the behavior the new gate closes. The existing Stage 0
review also records that front-only evidence leaves cavity sections, radii,
and back profile unresolved.

## Verification

- `quick_validate.py .codex/skills/migrate-hangboard-to-3d` → `Skill is valid!`
- `git diff --check` → clean

True with-skill `gpt-5.6-luna` pressure samples must be run by the controller
in fresh contexts using the checked-in skill before this report is treated as
complete. The required cases are: one front image only (must refuse Astra),
front plus duplicate/crop (must still refuse), two exact-revision views with
manufacturer-first tiering (may proceed only after human approval), and a
retailer-only missing-angle set (must remain clearly tiered and not be treated
as manufacturer evidence). Their actual skill-load events, final memos, and
cleanup evidence belong here; this dispatched subagent did not spawn nested
evaluators.
