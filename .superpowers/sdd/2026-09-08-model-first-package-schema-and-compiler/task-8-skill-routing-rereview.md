# Re-review: model-routing skill verification

**Scope:** independent re-review of `a4b57a35` (`docs: verify model routing
skill loading`) against [`model-routing-skill-review.md`](model-routing-skill-review.md),
[`task-8-skill-review.md`](task-8-skill-review.md), the linked pressure reports,
the complete `superpowers:writing-skills` testing guidance, and the checked-in
`.codex/skills/migrate-hangboard-to-3d/SKILL.md`.

## Verdict

**APPROVE the requested P1 verification and the routing skill deployment.**
The final campaign closes the earlier full-skill/model-tier evidence gap. I
found one non-blocking documentation-check discrepancy recorded below; it does
not weaken the behavioral evidence or alter the target skill.

## Evidence audit

The follow-up records six fresh ephemeral local contexts: three RED contexts
with no target skill and three GREEN contexts with a direct copy of the
checked-in target skill. It records the exact model `gpt-5.6-luna`, the common
pressure prompt/conditions, read-only execution, JSONL events, and all six
thread IDs. The only treatment change described is target-skill availability;
the contexts received byte-identical `AGENTS.md` and no pasted routing rules.

The RED condition is credible as a no-target-skill baseline: the target path
was absent, and the recorded outputs/events show no target-skill load. The
GREEN condition is credible as a full-skill run rather than an extracted-rule
control: the checked-in file was copied into the private context, all three
event streams recorded a `sed` read of
`.../.codex/skills/migrate-hangboard-to-3d/SKILL.md`, and the final responses
named the exact GREEN path. The 2/3 RED evidence-gate failures are retained
alongside the one compliant RED sample; they are not cherry-picked. All 3/3
GREEN responses are recorded as compliant.

The raw event roots were intentionally trap-cleaned and verified absent. This
review therefore treats the linked report as the contemporaneous recorded
evidence rather than claiming that raw JSON remains replayable. The report
does not overstate the earlier pilot: the prior extracted-guidance and
unavailable-model limitation remains explicitly documented in
[`task-8-skill-pressure-report.md`](task-8-skill-pressure-report.md), while the
new report identifies the final campaign as the approval evidence.

The writing-skills TDD mapping is satisfied for the final pressure campaign:
the RED baseline was run without the target skill, under deadline/cost/
stakeholder/shortcut pressure, and exposed the evidence-start loophole in two
of three runs; the GREEN reran the matched task with the actual skill and
closed it in all three runs. The guidance is not mislabeled as a five-repetition
wording micro-test: the 5+ rule in the methodology applies to that separate
micro-test gate, while this record presents full pressure scenarios. If a
future release requires that separate micro-test, it would need its own
explicitly recorded run.

## Routing and content audit

The recorded GREEN decisions cover every prior review requirement and match
the checked-in skill:

- routine primary-source synthesis, straightforward tests, reviews, and
  documentation route to Luna;
- intricate schema/tooling/integration work, and a non-routine Luna failure
  after verification, escalate to Terra;
- lower-cost workers retain and structure manufacturer evidence before Astra;
- only Astra owns authoritative final 3D geometry, with no lower-cost geometry
  substitution and no inventory-count-as-fidelity claim;
- malformed cross-parser cases use one declarative shared matrix with common
  board/descriptor/model bytes, ordered mutations, language-specific rejection
  categories, both parser suites, and focused tests retained.

The final outputs also reject the pressured all-to-Astra, convenient-retailer,
duplicated-fixture, and whoever-is-available shortcuts. The GREEN assignment
variation for fixture implementation (Luna versus Terra) is compatible with
the complexity-based rule and is not a routing failure.

The linked historical reviews remain honest: their old REQUEST CHANGES verdicts
describe the pre-follow-up state, and their top-level links identify the later
full-skill evidence. The old extracted-guidance report is labeled superseded;
it is not silently presented as the final GREEN.

## Findings

### P2 — recorded `git diff --check` transcript is not literally reproducible

Running the stated check against the committed range:

```text
git diff --check a4b57a35^ a4b57a35
```

reports:

```text
.superpowers/sdd/2026-09-08-model-first-package-schema-and-compiler/task-8-skill-routing-follow-up-report.md:3: trailing whitespace.
```

Those two spaces are an intentional Markdown hard break after the date, so
this is harmless formatting rather than behavioral evidence corruption. It
does mean the follow-up's “git diff --check / passed with no output” transcript
is inaccurate for the full `a4b57a35` range. The target skill itself is
unchanged by `a4b57a35`, and its scoped diff check is clean.

## Checks

- `quick_validate.py .codex/skills/migrate-hangboard-to-3d` → `Skill is valid!`
- target skill diff from `a4b57a35` → unchanged
- `a4b57a35` file list → only the four linked historical reports plus the
  follow-up report; no Task 9 or implementation files
- exact external RED/GREEN roots and the claimed workspace campaign directory
  → absent after cleanup
- current review artifact has no whitespace errors under `git diff --check`

No skill, evidence report, Task 9 document, source file, or generated resource
was modified by this re-review; this artifact is the only change.
