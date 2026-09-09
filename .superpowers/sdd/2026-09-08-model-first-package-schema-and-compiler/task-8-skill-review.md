# Independent review: cross-parser fixture skill update

**Range:** `766174ef^..766174ef` (`docs: codify cross-parser fixture parity`)

**Verdict:** **REQUEST CHANGES — one Important process finding.** The
cross-parser fixture rule is technically sound and non-duplicative, and the
Task 8 implementation/review evidence is consistent. The model-routing
follow-up is candid about its limitation, but that limitation leaves the
required full-skill GREEN/model-tier evidence incomplete.

## Findings by severity

### Critical

None.

### Important

#### P1 — The GREEN does not test the updated skill or exercise model-tier routing

The follow-up says the no-guidance and guidance contexts were matched, but its
guidance-control preamble manually supplies extracted rules rather than making
the private `.codex/skills/migrate-hangboard-to-3d/SKILL.md` available. It also
explicitly records that the full-skill subprocess was blocked
([`task-8-skill-pressure-report.md:93-102`](task-8-skill-pressure-report.md#L93)).
Therefore the observed GREEN demonstrates that the extracted wording changes
an Astra response; it does not demonstrate that a fresh agent discovers,
loads, and follows the committed skill.

Both evaluators also ran as `gpt-6-astra` because `gpt-6-luna` and `gpt-5` were
unavailable ([`task-8-skill-pressure-report.md:12-18`](task-8-skill-pressure-report.md#L12)).
The outputs name Luna/Terra/Astra as dispatch choices, but no Luna or Terra
run occurred, so this is not evidence of actual tier routing or of the
complexity/failed-verification escalation being enacted between model tiers.
The baseline/control preambles necessarily differ by more than skill
availability: the baseline tells the evaluator to honor shortcuts and avoid
the skill, while the control injects the new rules. That is a useful wording
control and is reported honestly, but it does not satisfy the stronger
same-prompt/full-skill GREEN requested by the prior routing review.

Run the matched scenario in an evaluator that can access the private skill,
or otherwise obtain an approved local skill-loaded run; retain the same task
body and record actual model identities/dispatches. Until then, keep the
follow-up labeled as extracted-guidance evidence rather than approval evidence.

## Content and implementation review

- The new rule at
  `.codex/skills/migrate-hangboard-to-3d/SKILL.md:38` is accurate and durable:
  one declarative matrix carries common board/descriptor documents and model
  bytes, ordered mutations, and language-specific rejection categories; both
  suites consume it while focused single-rule tests remain.
- The Task 8 implementation uses exactly that contract. The Python and Swift
  runners read the same `model` board/descriptor and base64 bytes, apply the
  same ordered mutation operations, and validate through production parsers.
  The matrix contains the eleven required malformed cases and declares the
  Python `ValueError` and Swift category for each.
- Focused tests remain present for the individual SHA, inventory, descriptor,
  tagged-media, camera, and derivation rules. No equivalent malformed fixture
  documents were independently added in the two languages, and the skill rule
  does not conflict with neighboring raw-JSON/parsing guidance.
- The earlier Task 8 review's implementation findings remain supported by the
  source and report. The earlier model-routing review's P1 is only partially
  addressed: the follow-up adds real matched RED observations and preserves
  the prompt/session limitation, but cannot close the full-skill/model-tier
  evidence gap described above.

## Verification

- Read `AGENTS.md`, the complete `skill-creator` and
  `superpowers:writing-skills` guidance, its required TDD background, the
  migration skill, Task 8 implementation/report/review artifacts, and the
  prior model-routing review.
- Fresh quick validation passed:
  `.context/hangboard-packages-venv/bin/python -B /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/skills/migrate-hangboard-to-3d`
  → `Skill is valid!`.
- `git diff --check 766174ef^ 766174ef` passed with no output.
- `python3 -m json.tool HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
  passed.
- Focused Python suite passed: `42 passed in 0.18s`.
- Review scope excludes the pre-existing working-tree change in
  `Tools/HangboardModels/README.md`; no Task 9 files were edited.
