# Task 6 incremental skill-maintenance review

## Verdict

**Needs one follow-up.** The skill text is concise, durable, and technically
aligned with the approved Task 6 contract. The update lacks the required
forward behavioral verification for a skill edit.

## Critical findings

None.

## Important findings

### 1. The edited skill was not forward-tested with the skill present

The validation record contains only `quick_validate` and a working-tree diff
check (`.superpowers/sdd/2026-09-08-model-first-package-schema-and-compiler/task-6-skill-report.md:32`).
The prior Task 6 review counterexamples are useful RED evidence, but the report
does not show a fresh agent applying the same realistic scenarios WITH the
updated skill. `superpowers:writing-skills` requires that GREEN verification
for edits, and `skill-creator` calls for independent forward-testing when a
skill update is sufficiently complex or risky.

Consequence: the syntactic validator cannot demonstrate that a future agent
will correctly distinguish catalog-wide raster schema migration from the
migrated target's model-only contract, or correctly apply the subtle raw JSON
number and XCTest lifecycle rules. Run a scoped, fresh-context behavioral
evaluation against the updated skill and record the observable result before
approving deployment. No simulator is needed for that evaluation.

## Minor findings

None.

## Content review

- `.codex/skills/migrate-hangboard-to-3d/SKILL.md:18` makes live discovery,
  deterministic/idempotent conversion, preserve-or-reject behavior, and
  duplicate/unknown-member rejection explicit without embedding a catalog
  count or commit detail.
- `.codex/skills/migrate-hangboard-to-3d/SKILL.md:20` gives a concise,
  package-wide before/after semantic-audit contract and names the required
  follow-up checks without duplicating their implementation.
- `.codex/skills/migrate-hangboard-to-3d/SKILL.md:24` retains the model-only
  rule for a migrated target; the conditional raster rules at line 26 govern
  raster packages and do not require raster media in that target.
- `.codex/skills/migrate-hangboard-to-3d/SKILL.md:26` requires nonempty,
  exact-one original ownership, original-to-derived references, and raw
  source equality with member order and scalar kind/value preserved.
- `.codex/skills/migrate-hangboard-to-3d/SKILL.md:30` correctly states the
  closed-schema omission-only rule for optional members and cross-language
  rejection of explicit `null`.
- `.codex/skills/migrate-hangboard-to-3d/SKILL.md:36` correctly specifies
  ordered object/list equality, arbitrary exact integers with Python-equivalent
  zero normalization, finite decoded-binary64 float equality, and distinct
  integer/float kinds.
- `.codex/skills/migrate-hangboard-to-3d/SKILL.md:76` captures the approved
  XCTest ownership, cleanup, bounded-polling, xcresult, and artifact lifecycle
  without task-specific history.

No added rule contradicts the existing 3D-only migration contract, repeats a
neighboring rule unnecessarily, or carries transient package counts, commit
IDs, or changelog prose.

## Verification

- Read the complete migration skill, `skill-creator`,
  `superpowers:writing-skills`, its required
  `superpowers:test-driven-development` background, the Task 6 final review,
  and the skill brief/report.
- Fresh `quick_validate.py .codex/skills/migrate-hangboard-to-3d` passed.
- `git diff --check fac1f56f^ fac1f56f` passed.
- Commit scope is limited to the migration skill and its report.
- No simulator was created or used.
