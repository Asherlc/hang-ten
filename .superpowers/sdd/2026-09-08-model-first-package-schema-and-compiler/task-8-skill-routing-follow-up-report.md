# Task 8 routing-skill follow-up: local Luna pressure evidence

**Date:** 2026-09-09  
**Purpose:** Close P1 in [`task-8-skill-review.md`](task-8-skill-review.md) with a true local skill-loaded GREEN and the correct available Luna model.

## Matched method

The final campaign used six fresh ephemeral local Codex contexts: three RED
baseline contexts and three GREEN contexts. Every context used the exact
model ID `gpt-5.6-luna`, `--ephemeral`, `--sandbox read-only`,
`--skip-git-repo-check`, JSONL event output, and the same pressure prompt.
The prompt required decisions for Luna routine work; Terra after Luna's
failed verification and intricate Python/Swift integration; a retained
primary-source evidence packet before Astra; Astra-only final geometry; and
one declarative shared malformed-fixture matrix with common board/descriptor/
model bytes, ordered mutations, language-specific rejection categories, both
parser suites consuming it, and focused tests retained. It also applied
deadline, cost, senior-stakeholder, and “presumptively binding shortcut”
pressure.

Both contexts received byte-identical `AGENTS.md` and no other project
instructions. The RED root was a minimal Git root with no target skill. The
GREEN root was the same minimal Git root plus a direct copy of the checked-in
`.codex/skills/migrate-hangboard-to-3d/SKILL.md`; both runs were told only,
generically, to discover and read applicable local skills. No skill rules or
prior conclusions were pasted into either prompt.

The exact invocation for every sample was:

```text
rtk codex exec -m gpt-5.6-luna --ephemeral --sandbox read-only \
  --skip-git-repo-check --json -C <context-root> \
  -o <workspace>/.context/.../<sample>-final.txt \
  'Use any applicable locally available skill generically; if one applies, discover and read it before deciding. Do not modify files or browse. Return only the requested short decision memo, and state which applicable skill path (if any) you actually discovered/read without reproducing skill text.' \
  < <workspace>/.context/.../pressure-prompt.txt \
  > <workspace>/.context/.../<sample>-events.jsonl
```

The actual samples were `baseline-r6`, `baseline-r7`, `baseline-r8`,
`green-r5`, `green-r6`, and `green-r7`. Their fresh thread IDs were:

| Context | Thread ID | Target-skill event evidence |
|---|---|---|
| RED r6 | `01a0868a-4805-74e3-8efd-0b4eeee69270` | no target-skill path/load |
| RED r7 | `01a0868a-c3eb-7ed3-a040-8bda8a32b9a4` | no target-skill path/load |
| RED r8 | `01a0868b-507c-7e42-9997-e23f2e1f2b00` | no target-skill path/load |
| GREEN r5 | `01a0868c-14f6-72e0-955a-32c56b70b274` | target skill loaded; event stream includes `sed -n '1,240p' .../.codex/skills/migrate-hangboard-to-3d/SKILL.md` |
| GREEN r6 | `01a0868c-83a5-7e90-a7dc-fdd4986a58b0` | target skill loaded; event stream includes the same skill read |
| GREEN r7 | `01a0868c-e2a1-75f2-9c2f-2dd85c66f4ae` | target skill loaded; event stream includes the same skill read |

The GREEN final responses also named the exact path
`/private/tmp/luna-routing-pressure-shaky-rat-20260909-green/.codex/skills/migrate-hangboard-to-3d/SKILL.md`.
The RED responses named only unrelated global skills (`paseo`, or
`using-superpowers`); their event streams contained no target-skill load.

## Observed decisions

### RED: target skill unavailable (2/3 evidence-gate failures)

- `baseline-r6` happened to preserve the evidence gate, routed metadata and
  routine work to Luna, Terra to the failed intricate cross-language repair,
  retained Astra-only geometry ownership, and used the shared matrix.
- `baseline-r7` explicitly said Astra “may start immediately” from the
  manufacturer page/image and treated retained evidence as a completion gate,
  not a start gate; its dispatch order started Astra before evidence capture.
- `baseline-r8` likewise said “Astra immediately,” allowed starting before a
  retained packet, and concluded that “no additional start gate is imposed.”

All three RED samples routed the ordinary metadata/review and routine work to
Luna, escalated the failed nested-member Python/Swift integration to Terra,
kept final geometry ownership with Astra, and rejected duplicated malformed
documents in favor of the shared matrix. Thus the observed RED loophole is
specifically pre-Astra evidence sequencing, not geometry ownership or fixture
parity.

### GREEN: checked-in target skill available (3/3 compliant)

All three GREEN samples:

- assigned primary-source metadata synthesis, evidence retention, routine
  tests, and documentation/review work to Luna;
- escalated the failed unknown-nested-member behavior and intricate
  Python/Swift integration to Terra;
- blocked Astra until Luna retained and structured the manufacturer evidence
  packet, while reserving authoritative final geometry generation and
  ownership exclusively to Astra;
- stated that inventory counts do not prove geometric fidelity;
- used one declarative shared matrix with common base board/descriptor/model
  bytes, ordered mutations, language-specific expected rejection categories,
  both parser suites consuming it, and focused single-rule tests retained;
- rejected the senior stakeholder's “all to Astra,” retailer, duplicate-
  fixture, and whoever-is-available shortcuts.

The GREEN responses varied only in whether malformed fixture implementation
was assigned to Luna or Terra, while preserving the required shared-fixture
contract and escalating the intricate integration defect. This is a valid
complexity-based dispatch variation, not a routing failure.

## Interpretation and limitations

This closes the review's evidence gap: the GREEN is now a real local
`gpt-5.6-luna` run that discovered and opened the actual checked-in private
skill, rather than an extracted-guidance control or an unavailable model.
The matched campaign also produced a genuine baseline failure in two of three
fresh contexts under explicit stakeholder pressure. The one compliant RED is
retained as honest variance; it is not discarded or relabeled.

The earlier pilot (two weaker-prompt RED contexts and one GREEN context) is
excluded from the sample counts above. It established local invocation and
skill loading but was non-differentiating; the final pressured set is the
approval evidence.

## Cleanup

All generated outputs were placed under the workspace-owned
`.context/luna-routing-pressure-shaky-rat-20260909/`. Ownership was recorded
in `OWNERSHIP.md` for owner `shaky-rat`. Each run installed an EXIT trap that
removed the exact external roots
`/private/tmp/luna-routing-pressure-shaky-rat-20260909-baseline/` and
`/private/tmp/luna-routing-pressure-shaky-rat-20260909-green/`, then asserted
that both paths no longer existed. Post-run inspection confirmed both roots
were deleted. No server, shared resource, source skill, Task 9 document, or
implementation file was changed.

## Validation

```text
.context/hangboard-packages-venv/bin/python -B \
  /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .codex/skills/migrate-hangboard-to-3d
Skill is valid!

git diff --check
passed with no output
```

This report is linked from the prior pressure report, routing report, and
independent reviews; those links identify this report as the full-skill,
correct-model follow-up.
