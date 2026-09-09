# Independent review: low-cost model routing

**P1 follow-up:** [`task-8-skill-routing-follow-up-report.md`](task-8-skill-routing-follow-up-report.md) closes the missing local full-skill/model-tier evidence with fresh matched Luna contexts.

**Range:** `7f89109a^..7f89109a`

**Verdict:** **REQUEST CHANGES** for the validation record. The routing text
itself is approved; the commit does not provide credible behavioral GREEN
evidence for a skill edit.

## Findings by severity

### Critical

None.

### Important

#### P1 — The report does not substantiate its RED/GREEN pressure test

The report labels a baseline pressure case RED and the new behavior GREEN, but
only summarizes hypothetical choices. It does not preserve the pressure prompt,
fresh-context setup, agent/model identity, observed baseline output, observed
with-skill output, or the rationalizations that were actually recorded
([model-routing-skill-report.md:9-34](model-routing-skill-report.md#L9-L34)).
Its only reproducible validation is structural (`quick_validate.py` and
`git diff --check`) ([model-routing-skill-report.md:36-46](model-routing-skill-report.md#L36-L46)).

This is insufficient under `superpowers:writing-skills`: the edited skill must
be behaviorally tested, including a no-skill baseline and the same scenario with
the skill present; behavior-shaping wording also calls for repeated micro-tests
against a no-guidance control. Without those observations, the report cannot
establish that an agent under deadline/cost pressure will follow the routing
boundary rather than merely echo it. Record matched fresh-context runs and the
actual outputs/rationalizations, then update the report before approving
deployment. The follow-up should cover: routine Luna research/tests/reviews/docs;
intricate or failed-verification Terra escalation; manufacturer-first retained
evidence before Astra; and Astra-only final geometry ownership.

## Routing/content audit

The changed guidance is otherwise aligned with the requested policy:

- **Luna default:** line 48 explicitly names routine primary-source research
  synthesis, straightforward tests, reviews, and documentation.
- **Terra escalation:** line 48 keys escalation to intricate schema/tooling/
  integration work or a Luna verification failure whose issue is no longer
  routine. It removes the former preference-based `Sol or Terra` escape hatch.
- **Astra boundary and sequencing:** line 46 makes Astra the only owner of
  authoritative final 3D geometry generation and difficult geometry judgment;
  line 48 requires lower-cost workers to structure the primary-source evidence
  packet before invoking Astra.
- **No geometry weakening:** line 48 keeps schema/tooling/material-export/
  integration defects with lower-cost workers and routes geometry/fidelity
  defects back to Astra. This preserves the surrounding direct-authoring and
  human-review constraints at lines 50-54 and 74.
- **No conflict or harmful duplication:** the existing source hierarchy and
  evidence-packet requirements at lines 12 and 16 are strengthened by an
  explicit pre-Astra sequencing rule, not contradicted. The target skill has no
  remaining `Sol` routing mention.

## Fresh checks

```text
.context/hangboard-packages-venv/bin/python -B \
  /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .codex/skills/migrate-hangboard-to-3d
Skill is valid!

git diff --check 7f89109a^ 7f89109a
passed with no output
```

The review artifact is the only new file in this follow-up; the migration skill
and the original routing report are unchanged.
