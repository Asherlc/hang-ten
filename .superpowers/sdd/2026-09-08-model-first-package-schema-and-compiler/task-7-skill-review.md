# Task 7 skill update independent review

**Range:** `4b0532d7..1ead9138`  
**Verdict:** **REQUEST CHANGES**

## Finding

### P1 — Required behavioral skill validation is not recorded

`writing-skills` explicitly applies RED/GREEN validation to edits of an
existing skill: it requires a no-skill baseline and a WITH-skill behavioral
test. The update report records only structural `quick_validate` and a diff
check, then says no runtime suite was needed. Neither proves that a future
agent will follow the new conditional staging rule. This is process guidance,
so a unit/runtime suite is not the relevant missing evidence; the missing
evidence is behavioral application of the skill.

Run and record this concrete scenario in an isolated temporary workspace:

> Migrate a board to schema-v2 model media. The current
> `scripts/stage-board-packages.py` calls parser discovery and recursively
> copies the package's regular-file tree. The request pressures the agent to
> "make model staging work quickly" and to create a failing test first.

The WITH-skill result must inspect the existing stager first, leave it
unchanged, and add only a parser-valid v2 model characterization fixture that
uses the Xcode staging environment and production entry point. It must assert
exact source/staged USDZ bytes, exact source/staged descriptor bytes, and the
complete parser-declared staged inventory; it must neither manufacture a
missing-helper/RED failure nor synthesize, rename, replace, or app-side
substitute model resources, and it must clean the generated staging output.
Per `writing-skills`, run the same scenario without this added skill guidance
first and record the observed baseline behavior. This review does not run that
test because the task expressly forbids subagents.

## Content review

The one-sentence replacement in
`.codex/skills/migrate-hangboard-to-3d/SKILL.md` is otherwise approved:

- It is concise, durable, and placed with existing validation/staging/sync
  guidance rather than task-history narrative.
- It clearly requires inspection before a staging change and makes the
  characterization path conditional on the existing stager copying the
  parser-approved regular-file tree.
- It requires exact source/staged USDZ and generated-descriptor bytes plus the
  exact parser-declared staged inventory, forbids substitution, and requires
  generated-resource cleanup.
- It does not prescribe or imply a manufactured RED. The characterization is
  correctly the response to already-existing staging behavior.
- It does not contradict the surrounding model-only, hash/inventory, or
  read-only Workbench requirements, and adds no unrelated production change.

## Fresh checks

```text
rtk proxy .context/hangboard-packages-venv/bin/python -B \
  /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .codex/skills/migrate-hangboard-to-3d
Skill is valid!

rtk git diff --check 4b0532d7 1ead9138
exit 0

rtk git diff --name-status 4b0532d7 1ead9138
M  .codex/skills/migrate-hangboard-to-3d/SKILL.md
A  .superpowers/sdd/2026-09-08-model-first-package-schema-and-compiler/task-7-skill-report.md
```
