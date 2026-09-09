# Model-routing skill update

## Scope

Updated only `.codex/skills/migrate-hangboard-to-3d/SKILL.md` and this report.
No Task 8 tests, review artifacts, app code, package data, geometry, or
generated resources were changed.

## Baseline pressure case (RED)

The pre-edit routing sentence said only to default bounded work to Luna and
use Sol or Terra for more involved non-geometry work. Under a deadline prompt
that supplied manufacturer links but no retained evidence packet, that
wording left these unsafe choices open: invoke Astra before structuring
evidence, send routine research/tests/reviews/docs to a higher-cost model,
escalate by preference rather than a complexity or failed-verification
predicate, and let a lower-cost worker own final geometry generation.

## Updated behavior (GREEN)

The routing guidance now requires:

- Luna for routine primary-source research synthesis, straightforward tests,
  reviews, and documentation;
- Terra for intricate schema/tooling/integration work, or when a Luna attempt
  fails verification and the unresolved issue is no longer routine;
- lower-cost evidence gathering and structuring before any Astra invocation,
  with manufacturer evidence first and authorized retailer gaps clearly
  tiered;
- Astra as the sole owner of authoritative final 3D geometry generation and
  difficult geometry judgment.

The existing primary-source hierarchy, Astra-only geometry boundary, and
human visual-review requirements remain intact.

## Validation

```text
.context/hangboard-packages-venv/bin/python -B \
  /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .codex/skills/migrate-hangboard-to-3d
Skill is valid!

git diff --check
passed with no output
```
