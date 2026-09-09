# Runtime Task 1 skill review — simulator identity and SwiftPM recovery

**Review target:** `5bf3a1aa79c634c0a7de442401e3685b15b21d08` (`docs: codify isolated SwiftPM test recovery`)

**Scope:** the two additions at `.codex/skills/migrate-hangboard-to-3d/SKILL.md:80-82`. This review does not modify the skill, `HangTenTests/BoardModelTests.swift`, Task 9, or implementation files.

## Verdict

**REVISE/RETEST before treating the complete edit as behaviorally approved.** The exact simulator-name rule is technically correct and has a valid real-worker RED antecedent. The SwiftPM rule is technically accurate, but the supplied RED campaign shows that this recovery was already intuitive; it has no observed pre-edit violation and should be reverted unless a real failing baseline is collected. The GREEN evidence is candid and useful, but 3/4 target-skill discovery (3/3 only after conditioning on a successful load) does not satisfy a strict writing-skills deployment gate by itself.

## Findings by severity

### Critical

None.

### Important

#### P1 — SwiftPM recovery addition has no demonstrated RED failure

The matched pre-edit pressure campaign explicitly reports 0/3 RED: every fresh
Luna context chose workspace-local verified pinned checkouts, locked/offline
resolution, no shared-cache mutation/fetch, no test skipping, and cleanup
(`task-1-skill-baseline-report.md:14-19`; the follow-up repeats this at
`task-1-skill-runtime-recovery-report.md:18-23`). The actual Task 1 fix worker
also independently selected the same safe workaround and recorded the exact
Xcode flags and local paths (`task-1-fix-1-report.md:39-53`). Thus this addition
did not close an observed agent rationalization.

This matters under `superpowers:writing-skills` and its required TDD
methodology: RED must show the agent failing before the wording is written,
and GREEN must be the same behavior corrected by that wording. `skill-creator`
also cautions against turning a single operational example or preference into a
universal rule. The paragraph is a good compact runbook, but the evidence
supports “already intuitive/no wording needed,” not a tested discipline fix.

**Disposition: REVERT the SwiftPM addition at `SKILL.md:82`.** If the team
wants to retain it, first run a fresh no-skill scenario that actually produces a
shared-cache mutation, arbitrary fetch, or skipped XCTest under pressure; then
run the same scenario with the checked-in skill and retain the observed
rationalization plus at least the writing-skills-required repeated micro-test
evidence. Do not relabel the existing 0/3 baseline as RED.

#### P1 — GREEN discovery/iteration evidence is not a complete deployment gate

The four-context follow-up records three true target-skill loads and one
discovery miss. Runs r1, r2, and r4 opened the checked-in skill and complied;
r3 did not load it and produced the malformed duplicate name
`Hang Ten Paseo Paseo shaky-rat Review` (`task-1-skill-runtime-recovery-report.md:40-65`).
That is correctly reported as 3/4 true-skill loads, not 4/4. However, the
missed run is not a GREEN compliance result, so “3/3 compliant” is only
conditional on successful discovery. The writing-skills checklist requires
running scenarios with the skill and, for behavior-shaping wording, repeated
micro-tests against a no-guidance control; no five-plus micro-test set for
these two additions is retained.

The later 3+3 routing campaign is strong evidence for the pre-existing model
routing rule: its RED failures concern pre-Astra evidence sequencing and its
GREEN runs load the complete skill (`task-8-skill-routing-follow-up-report.md:58-111`).
It does not test simulator identity or SwiftPM recovery, so it cannot repair
this edit’s missing evidence.

**Disposition: REVISE/RETEST the validation record.** Keep the honest 3/4
accounting, do not call r3 a skill-compliant GREEN, and obtain repeated
skill-loaded runs targeted at these additions before declaring the whole edit
behaviorally approved. This finding does not by itself require changing the
wording; r3 never read it.

### Minor

#### P2 — The added wording is technically sound and appropriately narrow

The simulator rule at `SKILL.md:80` exactly matches the approved plan’s
creation identity (`docs/superpowers/plans/2026-09-08-package-driven-3d-runtime-and-tools.md:26-28`)
and the validation skill’s prescribed `Hang Ten Paseo <workspace_name> Review`
workflow. Its explicit rejection of a task suffix, booted state, or apparent
equivalence directly addresses the historical worker variance: the successful
Task 1 fix used `Hang Ten Paseo shaky-rat Task1Fix1` rather than `… Review`
(`task-1-fix-1-review.md:86-92`). That is a genuine pre-edit lifecycle
deviation against the exact plan/validation identity, even though the earlier
review softened it as satisfying the ownership prefix. It is therefore a
valid real-world RED antecedent for this narrow rule; the 0/3 synthetic
baseline remains a separate honest result.

The rule’s “exact name” language governs simulator creation/use identity and
does not conflict with the validation cleanup fallback, which only checks the
workspace ownership prefix after an exact UUID lookup. Recording the UUID
before XCTest is also directly aligned with the plan and validation skill.

The SwiftPM paragraph is likewise technically correct as a procedure: its
exact-object precondition, workspace-local SourcePackages/package-cache
paths, no arbitrary fetch or shared-cache mutation, resolved-file/update
posture, and cleanup/evidence retention all match the successful isolated
retry (`task-1-fix-1-report.md:47-53,75-81`). It is concise for a fragile
Xcode failure mode; the problem is evidentiary justification, not technical
content.

**Disposition:** APPROVE retaining the exact-name addition at `SKILL.md:80`;
REVERT the unproven SwiftPM addition as specified in P1. If retained after a
new RED/GREEN cycle, no further technical rewrite is required.

## Verification

- `quick_validate.py .codex/skills/migrate-hangboard-to-3d` → `Skill is valid!`.
- `git diff --check 5bf3a1aa^ 5bf3a1aa` → clean.
- Current worktree `git diff --check` → clean; the pre-existing
  `HangTenTests/BoardModelTests.swift` modification was not touched.

