# Model-routing skill update

**Behavioral follow-up:** [`task-8-skill-routing-follow-up-report.md`](task-8-skill-routing-follow-up-report.md) records the full-skill `gpt-5.6-luna` verification and matched RED/GREEN pressure campaign.

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

## Follow-up behavioral validation

The review-requested matched pressure test is recorded in
[`task-8-skill-pressure-report.md`](task-8-skill-pressure-report.md). It
preserves the full common prompt, fresh-context identities, and essential
baseline/guidance decisions. The no-guidance baseline allowed Astra to start
before retained evidence and allowed fixture duplication under deadline
pressure; the matched guidance control required the evidence gate and one
shared declarative cross-parser matrix while retaining focused tests. The
configured ChatGPT account rejected `gpt-6-luna` and `gpt-5`; both runs used
the only accepted `gpt-6-astra` model. A private full-skill subprocess was
blocked by the approval boundary, so the report explicitly labels the GREEN
as an extracted-guidance control rather than overclaiming a full-file run.

## Validation

```text
.context/hangboard-packages-venv/bin/python -B \
  /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .codex/skills/migrate-hangboard-to-3d
Skill is valid!

git diff --check
passed with no output
```
