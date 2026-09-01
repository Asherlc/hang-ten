# Tensioned Cords Final Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate only the explicitly accepted tensioned-cord dependency commits, validate exactly 47 source-audited presentations, and conditionally update existing pull request #388 without merging it.

**Architecture:** Three immutable dependency cohorts are accepted and cherry-picked in a fixed order, with a fresh implementation worker and an independent review gate at each boundary. A durable 47-record source ledger joins exact asset facts to source, Workbench, iOS, test, diff, and review evidence; unsupported candidates remain rejected and the five Baguette Evo presentations remain blocked. Publication is a final conditional push to the existing #388 head only.

**Tech Stack:** Git, JSON board packages and RGBA PNG assets, Python 3.11.4+, pytest, HangboardPackages, Hangboard Workbench/Chrome capture, Swift/Xcode, and an isolated iOS Simulator.

**Spec:** `docs/superpowers/specs/2026-09-01-tensioned-cords-final-validation-design.md`

## Global Constraints

- Wait for an explicit acceptance decision naming immutable commits from `tensioned-cords-foundation`, `tensioned-cords-compact-dual`, and `tensioned-cords-inverted-routing`.
- Integrate only accepted commits, in foundation/evidence, compact/dual, then inverted/routed order, with recorded provenance and acceptance boundaries.
- The accepted foundation implementation sequence must itself provide and test Workbench `--all-presentations`, stable `packageID::presentationID` identities, normal and hold-ID variants, and exact child-process cleanup; final validation does not implement that capability.
- Delegate every implementation edit or configuration change to a fresh subagent; the controller performs integration and review coordination only.
- Independently review every dependency diff and render before integration, and independently review each integrated commit before proceeding to the next cohort.
- Reject unsupported and previously rejected candidates; never infer doubled cords, knots, hidden connections, terminals, hardware, or topology from sibling products or presentations.
- Every cord-bearing presentation shows source-proved cords, and every load-bearing cord is taut in the source-supported direction under canvas-down gravity.
- Preserve exact imagery, holds, material, color, background, alpha, decoded dimensions, framing, scale, position, complete silhouette, and unrelated pixels.
- Preserve the accepted YY Vertical La Baguette `stepped-face` and `reverse-face` presentations.
- Keep all five Baguette Evo presentations `BLOCKED` until exact-revision primary evidence resolves visible topology, hidden continuity, terminals, and hardware.
- Revalidate Nature Stone Hanger Mini `primary` and `side`, KARMA8A `primary`, YY Baguette `reverse-face`, and YY TravelBoard `reverse-10`, including source-proved routing-hole segments and exterior loops and no decorative sag on a load-bearing TravelBoard cord.
- Final-workspace repair authorization is exactly those five records; YY Baguette `stepped-face` and YY TravelBoard `front-25-15` are preservation/no-op cross-checks, and every other candidate is rejected or returned to its dependency owner unless the user explicitly expands the boundary.
- The terminal source ledger contains exactly 47 unique presentation records with honest `PASS`, `FIXED`, or `BLOCKED` status and the complete acceptance matrix from the spec.
- Generated output lives under `.context/tensioned-cords-final-validation/`; external resource names include `tensioned-cords-final-validation`, are recorded immediately, and are deleted by an installed exit trap.
- `.context/hangboard-packages-venv` is an exact owned workspace-local tool artifact when created; retain it through the final package test and delete it at the final resource-cleanup gate.
- Update only existing PR #388 after every terminal and accepted-asset gate passes; do not create a replacement pull request and do not merge.
- Do not push any implementation or integration commit to the #388 head before the final publication gate.

---

### Task 1: Dependency Acceptance and Readiness Gate

**Files:**

- Create during execution: `.context/tensioned-cords-final-validation/dependency-acceptance.md`
- Create during execution: `.context/tensioned-cords-final-validation/dependency-acceptance.json`
- Create during execution: `.context/tensioned-cords-final-validation/owned-resources.md`
- Create during execution: `.context/tensioned-cords-final-validation/validate-dependency-acceptance.py`
- Read: `docs/superpowers/specs/2026-09-01-tensioned-cords-final-validation-design.md`
- Read: dependency commit paths reported by the commands below

**Interfaces:**

- Consumes: explicit controller acceptance decisions naming immutable commits from all three dependency workspaces.
- Produces: a machine-validated integration base and three non-empty, contiguous, ordered accepted implementation-SHA sequences with provenance/acceptance boundaries and independent pre-integration approval.

- [ ] **Step 1: Install workspace ownership bookkeeping before creating evidence.**

Run:

```bash
rtk mkdir -p .context/tensioned-cords-final-validation
```

Use `apply_patch` to create `dependency-acceptance.md` and
`dependency-acceptance.json` and `owned-resources.md`. Record
`.context/tensioned-cords-final-validation`, Workbench ports `4187` and `4188`,
the conditional tool artifact `.context/hangboard-packages-venv`, and the future simulator name
`Hang Ten Paseo tensioned-cords-final-validation Review` in
`owned-resources.md`. Do not create an external resource in this task.

- [ ] **Step 2: Wait for explicit immutable acceptance.**

Do not derive acceptance from a branch tip. Continue only after the controller
has stated which implementation commits are accepted from each named branch.
Record each exact SHA, parent SHA, dependency ref, evidence report, accepted
paths, rejected paths/candidates, source URLs/claims, reviewer, and decision in
`dependency-acceptance.md`. Set `integrationBase` to the exact full SHA printed
by `rtk git rev-parse HEAD` before any cherry-pick.

The JSON manifest has root keys `integrationBase` and `cohorts`. `cohorts` is
an array in exact order with IDs `foundation`, `compactDual`, and
`invertedRouted`; refs `tensioned-cords-foundation`,
`tensioned-cords-compact-dual`, and `tensioned-cords-inverted-routing`;
`cohortBase`; and a non-empty `acceptedImplementationCommits` array. Every
commit object has exact `sha` and `parent`. Every cohort also has
`acceptedPaths`, `rejectedPaths`, `sourceEvidence`, `reviewer`, and
`decision: "APPROVED"`. The foundation cohort additionally has
`requiredCapabilities` containing exactly `allPresentationsCLI`,
`stablePackagePresentationIdentity`, `normalAndHoldIDCapture`,
`failureSafeOwnedChildCleanup`, and `focusedCapabilityTests`.

The root also has `authorizedRepairs`, containing exactly the five packageID /
presentationID pairs from Task 5. Each repair has non-empty `baseline` facts,
`sourceEvidence` URLs/claims, `permittedRegion`, and an exact
`expectedTerminalStatus` of `PASS` or `FIXED` based on the accepted dependency
bytes. `preservationCrossChecks` contains exactly `yy.baguette` /
`stepped-face` and `yy.travelboard` / `front-25-15`.

Use `apply_patch` to create
`.context/tensioned-cords-final-validation/validate-dependency-acceptance.py`
with this exact validator:

```python
import json
import subprocess
from pathlib import Path

workspace = Path(__file__).resolve().parents[2]
manifest_path = Path(__file__).with_name("dependency-acceptance.json")
manifest = json.loads(manifest_path.read_text())


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["rtk", "git", *arguments],
        cwd=workspace,
        text=True,
        capture_output=True,
    )


def commit(reference: str) -> str:
    result = git("rev-parse", f"{reference}^{{commit}}")
    assert result.returncode == 0, (reference, result.stderr)
    return result.stdout.strip()


expected_cohorts = (
    ("foundation", "tensioned-cords-foundation"),
    ("compactDual", "tensioned-cords-compact-dual"),
    ("invertedRouted", "tensioned-cords-inverted-routing"),
)
expected_repairs = {
    ("nature.stone-hanger-mini", "primary"),
    ("nature.stone-hanger-mini", "side"),
    ("nature.stone-hanger-mini-karma8a", "primary"),
    ("yy.baguette", "reverse-face"),
    ("yy.travelboard", "reverse-10"),
}
expected_cross_checks = {
    ("yy.baguette", "stepped-face"),
    ("yy.travelboard", "front-25-15"),
}
foundation_capabilities = {
    "allPresentationsCLI",
    "stablePackagePresentationIdentity",
    "normalAndHoldIDCapture",
    "failureSafeOwnedChildCleanup",
    "focusedCapabilityTests",
}

integration_base = manifest["integrationBase"]
assert commit(integration_base) == integration_base
cohorts = manifest["cohorts"]
assert len(cohorts) == len(expected_cohorts)

repairs = manifest["authorizedRepairs"]
assert {(item["packageID"], item["presentationID"]) for item in repairs} == expected_repairs
baseline_keys = {"assetPath", "sha256", "width", "height", "mode", "alpha"}
for item in repairs:
    assert baseline_keys <= item["baseline"].keys()
    assert item["baseline"]["assetPath"] and item["baseline"]["sha256"]
    assert item["baseline"]["width"] > 0 and item["baseline"]["height"] > 0
    assert item["sourceEvidence"]
    assert all(source["url"] and source["claim"] for source in item["sourceEvidence"])
    assert item["permittedRegion"]
    assert item["expectedTerminalStatus"] in {"PASS", "FIXED"}

cross_checks = manifest["preservationCrossChecks"]
assert {(item["packageID"], item["presentationID"]) for item in cross_checks} == expected_cross_checks

seen: set[str] = set()
for cohort, (expected_id, expected_ref) in zip(cohorts, expected_cohorts):
    assert cohort["id"] == expected_id
    assert cohort["ref"] == expected_ref
    assert cohort["decision"] == "APPROVED" and cohort["reviewer"]
    assert isinstance(cohort["acceptedPaths"], list) and cohort["acceptedPaths"]
    assert isinstance(cohort["rejectedPaths"], list)
    assert cohort["sourceEvidence"]
    sequence = cohort["acceptedImplementationCommits"]
    assert sequence
    if expected_id == "foundation":
        assert set(cohort["requiredCapabilities"]) == foundation_capabilities
    cohort_base = commit(cohort["cohortBase"])
    assert cohort_base == cohort["cohortBase"]
    for index, entry in enumerate(sequence):
        sha = commit(entry["sha"])
        parent = commit(f"{sha}^")
        assert sha == entry["sha"]
        assert parent == entry["parent"]
        assert sha not in seen
        assert git("merge-base", "--is-ancestor", sha, expected_ref).returncode == 0
        assert git("merge-base", "--is-ancestor", sha, integration_base).returncode == 1
        expected_parent = cohort_base if index == 0 else sequence[index - 1]["sha"]
        assert parent == expected_parent
        seen.add(sha)

assert seen
```

- [ ] **Step 3: Resolve and inspect the three recorded commits without changing HEAD.**

Run this exact fail-closed manifest validator before inspecting or applying a
commit:

```bash
rtk python3 .context/tensioned-cords-final-validation/validate-dependency-acceptance.py
```

Expected: exit 0. This proves each cohort has a non-empty implementation
sequence, each recorded parent is exact, each commit is reachable from its
named ref, no accepted SHA is already in the recorded integration base, no SHA
overlaps cohorts, and each cohort is one contiguous ordered parent chain. It
does not require exclusivity from other refs.

- [ ] **Step 4: Inspect every validated commit without changing HEAD.**

Run:

```bash
rtk zsh -lc 'set -euo pipefail; rtk python3 -c '\''import json; d=json.load(open(".context/tensioned-cords-final-validation/dependency-acceptance.json")); [print(e["sha"]) for c in d["cohorts"] for e in c["acceptedImplementationCommits"]]'\'' | while IFS= read -r accepted_sha; do rtk git show --no-ext-diff --stat --summary "$accepted_sha"; rtk git diff --check "$accepted_sha^" "$accepted_sha"; done'
```

Expected: each diff is clean and every changed path is inside its recorded
acceptance boundary.

- [ ] **Step 5: Assign an independent reviewer to each complete commit sequence and its renders.**

Each fresh reviewer compares the complete contiguous diff to primary evidence,
checks preservation and cord physics, and records `APPROVED` or `REJECTED` in
both acceptance files. The foundation reviewer also confirms its sequence
implements and tests every required capture capability, including exact child
PID ownership and success/failure/signal cleanup. A rejection stops this plan.
Do not cherry-pick a sequence until its pre-integration review is `APPROVED`.
After recording all three results, rerun:

```bash
rtk python3 .context/tensioned-cords-final-validation/validate-dependency-acceptance.py
```

- [ ] **Step 6: Verify the integration branch is clean and anchored to the expected PR head.**

Run:

```bash
rtk git status --short --branch
rtk gh pr view 388 --json state,headRefName,headRefOid,baseRefName,url
rtk git rev-parse HEAD
rtk python3 -c 'import json,subprocess as s; d=json.load(open(".context/tensioned-cords-final-validation/dependency-acceptance.json")); head=s.run(["rtk","git","rev-parse","HEAD"],check=True,text=True,capture_output=True).stdout.strip(); assert head==d["integrationBase"]'
```

Expected: the worktree is clean except workspace-owned `.context` evidence;
#388 is open with head
`fix-cords-backfill-gaps-nature-climbing-stone-hanger-mini`; current HEAD equals
the already recorded integration base.

### Task 2: Integrate Foundation and Evidence

**Files:**

- Modify: only paths listed in the accepted foundation implementation sequence
- Required delivered implementation: `Tools/HangboardWorkbench/capture_catalog.py`
- Required delivered tests: `Tools/HangboardWorkbench/tests/test_capture_catalog.py`
- Required delivered documentation: `Tools/HangboardWorkbench/README.md`
- Modify during execution: `.context/tensioned-cords-final-validation/dependency-acceptance.md`
- Modify during execution: `.context/tensioned-cords-final-validation/dependency-acceptance.json`

**Interfaces:**

- Consumes: Task 1's machine-validated foundation sequence and integration-base SHA.
- Produces: applied foundation/evidence commits that already provide and test `--all-presentations`, stable `packageID::presentationID` identities, normal and hold-ID capture variants, and failure-safe exact-child cleanup.

- [ ] **Step 1: Delegate the foundation cherry-pick to a fresh implementation subagent.**

Run:

```bash
rtk zsh -lc 'set -euo pipefail; foundation_base="$(rtk git rev-parse HEAD)"; if ! rtk python3 -c '\''import json; d=json.load(open(".context/tensioned-cords-final-validation/dependency-acceptance.json")); [print(e["sha"]) for c in d["cohorts"] if c["id"]=="foundation" for e in c["acceptedImplementationCommits"]]'\'' | rtk xargs rtk git cherry-pick; then print -u2 "foundation cherry-pick pipeline failed"; exit 1; fi; rtk python3 .context/tensioned-cords-final-validation/validate-dependency-acceptance.py; rtk git diff --check "$foundation_base" HEAD; rtk git diff --name-status "$foundation_base" HEAD; rtk git show --stat --summary "$foundation_base"..HEAD'
```

Expected: the cherry-pick applies exactly the accepted sequence; no unrelated
path appears.

- [ ] **Step 2: Run the foundation-focused checks declared by that accepted commit.**

Run the exact accepted capability tests, full capture test file, help gate, and
presentation audit preflight:

```bash
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardWorkbench/tests/test_capture_catalog.py::test_capture_command_accepts_every_presentation Tools/HangboardWorkbench/tests/test_capture_catalog.py::test_presentation_capture_identity_is_stable_and_distinct
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardWorkbench/tests/test_capture_catalog.py
rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json --phase2-preflight
rtk zsh -lc 'set -euo pipefail; rtk python3 Tools/HangboardWorkbench/capture_catalog.py --help | rtk rg --fixed-strings -- "--all-presentations"'
rtk rg -n --fixed-strings -- '--all-presentations' Tools/HangboardWorkbench/README.md
rtk rg -n --fixed-strings 'packageID::presentationID' Tools/HangboardWorkbench/README.md
```

Expected: tests and audit pass, help documents `--all-presentations`, and the
README documents stable `packageID::presentationID` identities. The accepted
foundation tests must also cover normal and hold-ID all-presentation variants
and exact server/Chrome child cleanup on success, capture failure, and signal.
If any capability is absent, reject the foundation sequence and stop before
Task 3. Do not delegate a new capture implementation from final validation.

- [ ] **Step 3: Independently review the integrated foundation commit before proceeding.**

A fresh reviewer verifies every applied SHA, source-ledger roster derivation,
all-presentation capture behavior, changed paths, and evidence provenance. Add
the review result to `dependency-acceptance.md`. Stop on any rejection; do not
start Task 3.

### Task 3: Integrate Compact and Dual Boards

**Files:**

- Modify: only paths listed in the accepted compact/dual implementation sequence
- Revalidate: `Hangboards/nature-stone-hanger-mini/board.json`
- Revalidate: `Hangboards/nature-stone-hanger-mini/assets/primary.png`
- Revalidate: `Hangboards/nature-stone-hanger-mini/assets/side.png`
- Revalidate: `Hangboards/nature-stone-hanger-mini-karma8a/board.json`
- Revalidate: `Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.png`

**Interfaces:**

- Consumes: the independently approved Task 2 state and Task 1's machine-validated compact/dual sequence.
- Produces: an applied, independently approved compact/dual cohort with source-proved routing-hole and exterior-loop preservation.

- [ ] **Step 1: Re-inspect the compact/dual commit against the now-integrated foundation.**

Run:

```bash
rtk zsh -lc 'set -euo pipefail; rtk python3 -c '\''import json; d=json.load(open(".context/tensioned-cords-final-validation/dependency-acceptance.json")); [print(e["sha"]) for c in d["cohorts"] if c["id"]=="compactDual" for e in c["acceptedImplementationCommits"]]'\'' | while IFS= read -r accepted_sha; do rtk git diff --check "$accepted_sha^" "$accepted_sha"; rtk git diff --name-status "$accepted_sha^" "$accepted_sha"; rtk git show --format=fuller --no-patch "$accepted_sha"; done'
```

Expected: the immutable accepted patch and provenance still match Task 1.

- [ ] **Step 2: Delegate the compact/dual cherry-pick to a fresh implementation subagent.**

Run:

```bash
rtk zsh -lc 'set -euo pipefail; compact_base="$(rtk git rev-parse HEAD)"; if ! rtk python3 -c '\''import json; d=json.load(open(".context/tensioned-cords-final-validation/dependency-acceptance.json")); [print(e["sha"]) for c in d["cohorts"] if c["id"]=="compactDual" for e in c["acceptedImplementationCommits"]]'\'' | rtk xargs rtk git cherry-pick; then print -u2 "compact/dual cherry-pick pipeline failed"; exit 1; fi; rtk python3 .context/tensioned-cords-final-validation/validate-dependency-acceptance.py; rtk git diff --check "$compact_base" HEAD; rtk git diff --name-status "$compact_base" HEAD; rtk git show --stat --summary "$compact_base"..HEAD'
```

- [ ] **Step 3: Validate the compact/dual packages and focused contracts.**

Run:

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_approved_board_packages.py
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardWorkbench/tests/test_approved_board_packages.py
```

Expected: all commands pass. Directly compare Stone Hanger Mini `primary` and
`side` and KARMA8A `primary` to their exact sources, requiring all proved
routing-hole segments and exterior loops and preserving unrelated pixels.

- [ ] **Step 4: Independently review the integrated compact/dual commit before proceeding.**

A fresh reviewer reads every changed package diff and every normal/highlighted
render, then records the result. Stop on any unexpected silhouette, cord route,
pixel, alpha, dimension, scale, position, framing, or overlay change.

### Task 4: Integrate Inverted and Routed Boards

**Files:**

- Modify: only paths listed in the accepted inverted/routed implementation sequence
- Revalidate: `Hangboards/yy-travelboard/board.json`
- Revalidate: `Hangboards/yy-travelboard/assets/primary.png`
- Revalidate: `Hangboards/yy-travelboard/assets/reverse.png`
- Revalidate: every orientation-specific asset named by the accepted commit

**Interfaces:**

- Consumes: the independently approved Task 3 state and Task 1's machine-validated inverted/routed sequence.
- Produces: an applied, independently approved inverted/routed cohort with canvas-down gravity and tension verified for every orientation.

- [ ] **Step 1: Re-inspect the inverted/routed commit against the integrated state.**

Run:

```bash
rtk zsh -lc 'set -euo pipefail; rtk python3 -c '\''import json; d=json.load(open(".context/tensioned-cords-final-validation/dependency-acceptance.json")); [print(e["sha"]) for c in d["cohorts"] if c["id"]=="invertedRouted" for e in c["acceptedImplementationCommits"]]'\'' | while IFS= read -r accepted_sha; do rtk git diff --check "$accepted_sha^" "$accepted_sha"; rtk git diff --name-status "$accepted_sha^" "$accepted_sha"; rtk git show --format=fuller --no-patch "$accepted_sha"; done'
```

- [ ] **Step 2: Delegate the inverted/routed cherry-pick to a fresh implementation subagent.**

Run:

```bash
rtk zsh -lc 'set -euo pipefail; inverted_base="$(rtk git rev-parse HEAD)"; if ! rtk python3 -c '\''import json; d=json.load(open(".context/tensioned-cords-final-validation/dependency-acceptance.json")); [print(e["sha"]) for c in d["cohorts"] if c["id"]=="invertedRouted" for e in c["acceptedImplementationCommits"]]'\'' | rtk xargs rtk git cherry-pick; then print -u2 "inverted/routed cherry-pick pipeline failed"; exit 1; fi; rtk python3 .context/tensioned-cords-final-validation/validate-dependency-acceptance.py; rtk git diff --check "$inverted_base" HEAD; rtk git diff --name-status "$inverted_base" HEAD; rtk git show --stat --summary "$inverted_base"..HEAD'
```

- [ ] **Step 3: Validate package and orientation-specific contracts.**

Run:

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_approved_board_packages.py
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardWorkbench/tests/test_approved_board_packages.py
```

Expected: all commands pass. Review each normal and inverted presentation in
its own canvas orientation. Require canvas-down gravity, taut source-supported
load direction, source-proved routing-hole segments and exterior loops, and no
decorative sag on any load-bearing TravelBoard cord.

- [ ] **Step 4: Independently review the integrated inverted/routed commit before proceeding.**

A fresh reviewer reads every changed diff and render, verifies exact source
applicability per orientation, and records the result. Stop rather than repair
an unsupported candidate in this integration task.

### Task 5: Baguette and Safe-Repair Audit Gate

**Files:**

- Revalidate: `Hangboards/yy-baguette/board.json`
- Revalidate: `Hangboards/yy-baguette/assets/primary.png`
- Revalidate: `Hangboards/yy-baguette/assets/reverse.png`
- Revalidate without accepting candidates: `Hangboards/yy-baguette-evo/board.json`
- Revalidate without accepting candidates: `Hangboards/yy-baguette-evo/assets/primary.png`
- Revalidate without accepting candidates: `Hangboards/yy-baguette-evo/assets/shallow-pairs.png`
- Revalidate without accepting candidates: `Hangboards/yy-baguette-evo/assets/central-30-25.png`
- Revalidate without accepting candidates: `Hangboards/yy-baguette-evo/assets/central-20-6.png`
- Revalidate without accepting candidates: `Hangboards/yy-baguette-evo/assets/tray.png`
- Authorized bounded repair only: `Hangboards/nature-stone-hanger-mini/assets/primary.png`
- Authorized bounded repair only: `Hangboards/nature-stone-hanger-mini/assets/side.png`
- Authorized bounded repair only: `Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.png`
- Authorized bounded repair only: `Hangboards/yy-baguette/assets/reverse.png`
- Authorized bounded repair only: `Hangboards/yy-travelboard/assets/reverse.png` and its directly required `board.json` presentation declaration

**Interfaces:**

- Consumes: all three independently approved integrated cohorts.
- Produces: five explicitly bounded safe-repair decisions, preserved Baguette/TravelBoard no-op cross-checks, five blocked Baguette Evo decisions, and no authorization outside those boundaries.

- [ ] **Step 1: Freeze exact classic and Evo asset facts before review.**

Run:

```bash
rtk shasum -a 256 Hangboards/nature-stone-hanger-mini/assets/primary.png Hangboards/nature-stone-hanger-mini/assets/side.png Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.png Hangboards/yy-baguette/assets/primary.png Hangboards/yy-baguette/assets/reverse.png Hangboards/yy-travelboard/assets/primary.png Hangboards/yy-travelboard/assets/reverse.png
rtk shasum -a 256 Hangboards/yy-baguette-evo/assets/primary.png Hangboards/yy-baguette-evo/assets/shallow-pairs.png Hangboards/yy-baguette-evo/assets/central-30-25.png Hangboards/yy-baguette-evo/assets/central-20-6.png Hangboards/yy-baguette-evo/assets/tray.png
rtk git diff --name-status origin/main...HEAD -- Hangboards/nature-stone-hanger-mini Hangboards/nature-stone-hanger-mini-karma8a Hangboards/yy-baguette Hangboards/yy-baguette-evo Hangboards/yy-travelboard
```

Record hashes, decoded dimensions, image mode, and alpha behavior in the
dependency acceptance manifest and final ledger. Confirm classic Baguette
`stepped-face` and TravelBoard `front-25-15` remain preservation/no-op
cross-checks; neither adds repair authorization.

- [ ] **Step 2: Audit the five Baguette Evo records without inference.**

For each exact presentation, reopen exact-revision primary sources and record
the unresolved visible topology, hidden continuity, terminals, and hardware.
Mark all five `BLOCKED`, accept no candidate, and do not use a sibling or another
orientation to close a gap.

- [ ] **Step 3: Enforce the exact five-record repair manifest.**

Before a final-workspace edit, require these exact records in the dependency
acceptance manifest:

| Package/presentation | Source mapping | Permitted repair region | Expected terminal result |
| --- | --- | --- | --- |
| `nature.stone-hanger-mini` / `primary` | Exact URLs and claims from `docs/source-audits/2026-08-29-nature-mini-presentation-assets.md` | Only source-proved cord, routing-hole segment, exterior-loop pixels, and minimum antialias boundary | `FIXED` if accepted bytes change; otherwise source-correct no-op `PASS` |
| `nature.stone-hanger-mini` / `side` | Exact URLs and claims from `docs/source-audits/2026-08-29-nature-mini-presentation-assets.md` | Only source-proved cord, routing-hole segment, exterior-loop pixels, and minimum antialias boundary | `FIXED` if accepted bytes change; otherwise source-correct no-op `PASS` |
| `nature.stone-hanger-mini-karma8a` / `primary` | Exact URLs and claims from `docs/source-audits/2026-08-29-nature-mini-presentation-assets.md` | Only source-proved cord, routing-hole segment, exterior-loop pixels, and minimum antialias boundary | `FIXED` if accepted bytes change; otherwise source-correct no-op `PASS` |
| `yy.baguette` / `reverse-face` | Exact URLs and claims from `docs/source-audits/2026-08-12-yy-vertical-board-packages.md` and `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md` | Only source-proved cord/routing pixels and minimum antialias boundary | `FIXED` if accepted bytes change; otherwise source-correct no-op `PASS` |
| `yy.travelboard` / `reverse-10` | Exact URLs and claims from `docs/source-audits/2026-08-29-official-portable-presentation-assets.md` and `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md` | Only source-proved routing-hole segments, exterior loops, taut load-bearing cord pixels, and minimum antialias boundary | `FIXED` if accepted bytes change; otherwise source-correct no-op `PASS` |

Each record also stores accepted baseline path/hash/dimensions/mode/alpha and
the exact permitted pixel mask description. Exact-revision primary evidence
must prove the visible change; dimensions, alpha, board silhouette, holds,
material, color, background, framing, scale, position, and unrelated pixels
remain exact. `yy.baguette` / `stepped-face` and `yy.travelboard` /
`front-25-15` are no-op cross-checks only. Reject or return every other
candidate to its dependency owner unless the user explicitly expands scope.

- [ ] **Step 4: If and only if Step 3 proves a necessary repair inside one of the five records, delegate it to a fresh implementation subagent.**

The worker changes only that record's listed asset and, for TravelBoard reverse,
any directly required `board.json` presentation declaration. The worker runs
the package and focused commands from Tasks 3 and 4 and commits with a
package-specific repair message. A fresh reviewer must approve that commit
before Task 6. If no repair is proved, record an accepted no-op and create no
commit. A request to touch any sixth record stops this plan pending explicit
user authorization.

### Task 6: Exact 47-Record Ledger and Workbench Capture Gate

**Files:**

- Create: `docs/source-audits/2026-09-01-tensioned-cords-final-validation.json`
- Create during execution: `.context/tensioned-cords-final-validation/workbench-all-presentations/`
- Create during execution: `.context/tensioned-cords-final-validation/workbench-all-presentations-hold-ids/`

**Interfaces:**

- Consumes: the authoritative accepted source roster, integrated catalog, reviewed fixes/no-ops, and spec acceptance matrix.
- Produces: exactly 47 terminal records and two complete all-presentation Workbench capture sets.

- [ ] **Step 1: Delegate ledger construction to a fresh documentation/implementation subagent.**

Discover the roster from the accepted foundation source audit and current
catalog. Each JSON record must contain `packageID`, `presentationID`, source
URLs/claims, baseline and accepted path/hash/width/height/mode/alpha facts,
`terminalStatus`, accepted commit, and evidence for every acceptance-matrix
gate. Reject duplicate identities. Do not add an inferred presentation to make
the count reach 47.

- [ ] **Step 2: Fail closed unless the authoritative roster is exactly 47.**

Run:

```bash
rtk python3 -c 'import json; from pathlib import Path; p=Path("docs/source-audits/2026-09-01-tensioned-cords-final-validation.json"); d=json.loads(p.read_text()); r=d["records"]; ids=[(x["packageID"],x["presentationID"]) for x in r]; assert len(r)==47, len(r); assert len(set(ids))==47; assert {x["terminalStatus"] for x in r} <= {"PASS","FIXED","BLOCKED"}'
```

Expected: exit 0 with 47 unique terminal records.

- [ ] **Step 3: Enforce the Baguette Evo and non-Evo terminal boundary.**

Run:

```bash
rtk python3 -c 'import json; d=json.load(open("docs/source-audits/2026-09-01-tensioned-cords-final-validation.json")); r=d["records"]; evo={x["presentationID"]:x for x in r if x["packageID"]=="yy.baguette-evo"}; expected={"paired-25-20-15-10","paired-12-8-6","central-30-25","central-20-6","rounded-tray"}; assert set(evo)==expected; assert all(x["terminalStatus"]=="BLOCKED" and not x.get("acceptedCandidate") for x in evo.values()); assert all(x["terminalStatus"] in {"PASS","FIXED"} for x in r if x["packageID"]!="yy.baguette-evo")'
```

- [ ] **Step 4: Generate normal captures for every declared presentation.**

Before launch, require both exact ports to be free:

```bash
rtk zsh -lc 'set -euo pipefail; for port in 4187 4188; do if rtk lsof -nP -iTCP:"$port" -sTCP:LISTEN; then print -u2 "owned capture port $port is already occupied"; exit 1; fi; done'
```

The accepted foundation capture implementation must install its failure,
`INT`, and `TERM` cleanup before starting a child, record each exact server and
Chrome PID in its process owner immediately after creation, and terminate and
wait for only those PIDs on success, exception, timeout, or signal. It must not
kill an unknown listener. Record the command and ports in `owned-resources.md`,
then run:

```bash
rtk python3 Tools/HangboardWorkbench/capture_catalog.py --repository-root "$PWD" --output-root "$PWD/.context/tensioned-cords-final-validation/workbench-all-presentations" --chrome-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --port 4187 --all-presentations
rtk zsh -lc 'set -euo pipefail; if rtk lsof -nP -iTCP:4187 -sTCP:LISTEN; then print -u2 "capture leaked port 4187"; exit 1; fi'
```

Expected: the capture tool terminates its exact Chrome/server children and
writes labeled PNGs, `manifest.json`, and `contact-sheet.png`.

- [ ] **Step 5: Generate hold-ID-overlay captures for every declared presentation.**

Run:

```bash
rtk python3 Tools/HangboardWorkbench/capture_catalog.py --repository-root "$PWD" --output-root "$PWD/.context/tensioned-cords-final-validation/workbench-all-presentations-hold-ids" --chrome-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --port 4188 --all-presentations --hold-id-labels
rtk zsh -lc 'set -euo pipefail; if rtk lsof -nP -iTCP:4188 -sTCP:LISTEN; then print -u2 "capture leaked port 4188"; exit 1; fi'
```

Expected: normal completion or any failure leaves neither owned child alive and
both ports free. A leak fails the gate and is returned to the foundation owner;
final validation does not patch the capture implementation.

- [ ] **Step 6: Map every one of the 47 records to both capture manifests and review every render.**

Require each `packageID::presentationID` identity in both manifests. Directly
compare source, baseline, normal capture, and hold-ID capture for cord physics,
silhouette, unrelated pixels, and overlay alignment. Store both capture paths
and the review result in each ledger record. A missing identity or failed render
stops the plan.

- [ ] **Step 7: Commit the reviewed ledger only.**

Run:

```bash
rtk git add docs/source-audits/2026-09-01-tensioned-cords-final-validation.json
rtk git diff --cached --check
rtk git commit -m "docs: record tensioned cord validation ledger"
```

Do not push this commit yet.

### Task 7: Isolated iOS Validation and Owned Simulator Cleanup

**Files:**

- Read completely: `.codex/skills/validate-hang-ten-ios/SKILL.md`
- Read completely: `docs/IOS_SIMULATOR_VALIDATION.md`
- Read completely: `docs/IOS_RUNTIME_SERVICES.md`
- Create during execution: `.context/paseo-pending-simulators`
- Create during execution: `.context/paseo-owned-simulators`
- Create during execution: `.context/tensioned-cords-final-validation/ios/`
- Create and delete during execution: `.context/DerivedData/`

**Interfaces:**

- Consumes: the exact 47-record ledger and all accepted catalog assets.
- Produces: isolated-device normal and active/detail evidence for every app-exposed record and verified deletion of the exact owned simulator.

- [ ] **Step 1: Delegate iOS validation to a fresh validation subagent using the required skill.**

The worker derives `workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"` and
`workspace_name="tensioned-cords-final-validation"`, installs the skill's
`EXIT`, `INT`, and `TERM` cleanup trap before `simctl create`, creates exactly
`Hang Ten Paseo tensioned-cords-final-validation Review`, validates its UUID,
records it first in the pending manifest and then in the owned manifest, and
uses that explicit UUID for every operation. Never use `booted`.

- [ ] **Step 2: Build, install, and launch the exact app on the owned device.**

After the skill's bounded readiness poll, run with the recorded
`simulator_uuid`:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=$simulator_uuid" -derivedDataPath .context/DerivedData build
rtk xcrun simctl terminate "$simulator_uuid" com.hangten.training
rtk xcrun simctl install "$simulator_uuid" .context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app
rtk xcrun simctl get_app_container "$simulator_uuid" com.hangten.training app
rtk env SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_PICKER=1 xcrun simctl launch "$simulator_uuid" com.hangten.training
```

Expected: signed simulator build succeeds, the installed container is from this
workspace, and the board picker opens deterministically.

- [ ] **Step 3: Capture normal and active/detail states.**

For every app-exposed ledger record, navigate to the exact board and
presentation, inspect normal rendering, activate a scoped hold/detail state,
and capture both states under
`.context/tensioned-cords-final-validation/ios/`. Derive each stable filename
from its ledger `packageID` and `presentationID`, and record both paths in that
record. Require unchanged silhouette/placement and exact overlay alignment.
The five blocked Baguette Evo captures document the current baseline and its
blocker; they do not accept an iOS or catalog candidate.

Use the exact UUID for screenshots:

```bash
rtk xcrun simctl io "$simulator_uuid" screenshot "$ios_capture_root/$capture_stem-normal.png"
rtk xcrun simctl io "$simulator_uuid" screenshot "$ios_capture_root/$capture_stem-active-detail.png"
```

- [ ] **Step 4: Exercise focused rotation and active-state stability.**

Launch an accepted cord-bearing board through the DEBUG review routes in
portrait and landscape, activate its hold/detail state, and confirm that board
position, cord direction, overlay alignment, and selected state remain stable.
Capture both orientations and record them in the validation evidence.

- [ ] **Step 5: Run owned cleanup on success, failure, or interruption and verify deletion.**

Leave the skill's trap installed for the entire run. At normal completion it
must run:

```bash
rtk env PASEO_WORKTREE_PATH="$PWD" scripts/paseo-resource-cleanup.sh archive
rtk xcrun simctl list devices
```

Expected: the exact recorded UUID no longer exists; the pending and owned
records are consumed only after verified cleanup; `.context/DerivedData`,
`.context/workout-raw.png`, and `.context/workout-landscape.png` are removed;
shared and unknown simulators are untouched. Preserve manifests and fail the
gate if cleanup cannot be verified.

### Task 8: Package, Focused, Full-Suite, and Diff Gate

**Files:**

- Test: `Tools/HangboardPackages/tests/`
- Test: `Tools/HangboardWorkbench/tests/`
- Test: `Tools/HangboardWorkbench/tests/test_capture_catalog.py`
- Test: `Tools/HangboardWorkbench/macos/`
- Create conditionally and retain through this task: `.context/hangboard-packages-venv/`
- Verify: all paths in `origin/main...HEAD`

**Interfaces:**

- Consumes: reviewed integration, ledger, Workbench evidence, and cleaned iOS validation.
- Produces: final package/status, focused/full-suite, and repository-diff evidence.

- [ ] **Step 1: Run package validation and status with owned tool-artifact accounting.**

The wrapper may create `.context/hangboard-packages-venv`. Its exact path is
already recorded in `owned-resources.md`; retain it through the final package
test in this task, never treat it as read-only evidence, and do not track it.

Run:

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json --phase2-preflight
```

Expected: complete final inventory, no drafts, valid status, and valid existing
presentation manifest.

- [ ] **Step 2: Run the focused package and all-presentation capture tests.**

Run:

```bash
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_approved_board_packages.py
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardWorkbench/tests/test_approved_board_packages.py Tools/HangboardWorkbench/tests/test_capture_catalog.py
```

- [ ] **Step 3: Run the complete HangboardPackages and Workbench suites.**

Run:

```bash
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardWorkbench/tests
rtk npm --prefix Tools/HangboardWorkbench ci
rtk npm --prefix Tools/HangboardWorkbench run check:bundle
rtk npm --prefix Tools/HangboardWorkbench run typecheck
rtk npm --prefix Tools/HangboardWorkbench test
rtk swift test --package-path Tools/HangboardWorkbench/macos
```

Expected: all commands pass. Record literal commands, exit statuses, and result
summaries in the ledger's validation metadata.

- [ ] **Step 4: Review the complete diff and binary scope.**

Run:

```bash
rtk git diff --check origin/main...HEAD
rtk git diff --name-status origin/main...HEAD
rtk git diff --stat origin/main...HEAD
rtk git diff --numstat origin/main...HEAD
rtk git log --oneline --decorate origin/main..HEAD
rtk git status --short --branch
```

Expected: only accepted dependency, source-proved bounded repair, test, and
ledger paths appear; no generated `.context` capture or simulator artifact is
tracked; no unrelated pixel or configuration change appears.

- [ ] **Step 5: Update the ledger evidence and commit only if test-result metadata changed.**

Delegate any ledger edit to a fresh subagent, rerun the exact 47/Baguette
assertions from Task 6, stage only the ledger, run `rtk git diff --cached
--check`, and commit with `rtk git commit -m "docs: finalize tensioned cord
validation evidence"`. Do not push yet.

### Task 9: Independent Final Code Review

**Files:**

- Review: every path in `origin/main...HEAD`
- Read: `docs/source-audits/2026-09-01-tensioned-cords-final-validation.json`
- Read: `.context/tensioned-cords-final-validation/dependency-acceptance.md`
- Create: `.context/tensioned-cords-final-validation/final-code-review.json`

**Interfaces:**

- Consumes: all implementation, integration, tests, ledger evidence, and full diff.
- Produces: a fresh independent code/provenance review decision.

- [ ] **Step 1: Dispatch a fresh reviewer who implemented none of Tasks 2–8.**

The reviewer checks commit provenance and order, every diff, source boundaries,
47-record uniqueness/completeness, Baguette Evo blockers, package declarations,
hash/dimension/alpha evidence, tests, and absence of unrelated changes.

- [ ] **Step 2: Require an explicit final code verdict.**

Use `apply_patch` to write `final-code-review.json` with `verdict`, `reviewer`,
`reviewedHead`, `ledgerSHA256`, `reviewedRange`, and `findings`. Record
`verdict: "APPROVED"` only if `findings` is empty and `reviewedHead` is the
current full SHA. A finding is routed to a fresh implementation subagent, then
Tasks 6–9 are rerun as applicable. Do not proceed to visual review with an open
finding.

### Task 10: Independent Final Visual Review

**Files:**

- Review: `.context/tensioned-cords-final-validation/workbench-all-presentations/`
- Review: `.context/tensioned-cords-final-validation/workbench-all-presentations-hold-ids/`
- Review: `.context/tensioned-cords-final-validation/ios/`
- Read: all source links and evidence mappings in `docs/source-audits/2026-09-01-tensioned-cords-final-validation.json`
- Create: `.context/tensioned-cords-final-validation/final-visual-review.json`

**Interfaces:**

- Consumes: approved code review and every source/render/capture pair.
- Produces: a separate fresh visual verdict covering all 47 records.

- [ ] **Step 1: Dispatch a fresh visual reviewer who performed neither implementation nor final code review.**

The reviewer inspects every one of the 47 records, both Workbench capture sets,
all applicable iOS normal and active/detail screenshots, and the exact source.
They apply every visual and physics row of the acceptance matrix, including
canvas-down gravity, taut load direction, routing holes, exterior loops,
silhouettes, pixel preservation, and overlay alignment.

- [ ] **Step 2: Require an explicit final visual verdict.**

Use `apply_patch` to write `final-visual-review.json` with `verdict`, `reviewer`,
`reviewedHead`, `ledgerSHA256`, all three capture roots, `recordCount: 47`, and
`findings`. Record `verdict: "APPROVED"` only when `findings` is empty, every
accepted record passes, and the five Baguette Evo records remain honestly
blocked with no candidate. Route any finding to a fresh implementation
subagent, then rerun all affected captures, tests, ledger checks, code review,
and visual review.

### Task 11: Conditional Update of Existing PR #388 Head Only

**Files:**

- Verify: complete Git history and clean working tree
- Update remotely only after every condition below passes: `origin/fix-cords-backfill-gaps-nature-climbing-stone-hanger-mini`

**Interfaces:**

- Consumes: exactly 47 terminal records, all accepted-asset gates, both independent approvals, and verified owned-resource cleanup.
- Produces: the existing PR #388 head updated to the fully validated commit; no new PR and no merge.

- [ ] **Step 1: Re-run terminal publication assertions.**

Run the Task 6 exact-count and Baguette assertions. Machine-verify both durable
independent approvals against exact current HEAD and the final ledger hash:

```bash
rtk python3 -c 'import hashlib,json,subprocess as s; from pathlib import Path; head=s.run(["rtk","git","rev-parse","HEAD"],check=True,text=True,capture_output=True).stdout.strip(); ledger=Path("docs/source-audits/2026-09-01-tensioned-cords-final-validation.json"); digest=hashlib.sha256(ledger.read_bytes()).hexdigest(); paths=[Path(".context/tensioned-cords-final-validation/final-code-review.json"),Path(".context/tensioned-cords-final-validation/final-visual-review.json")]; reports=[json.loads(p.read_text()) for p in paths]; assert all(r["verdict"]=="APPROVED" and r["reviewedHead"]==head and r["ledgerSHA256"]==digest and r["reviewer"] and r["findings"]==[] for r in reports); assert reports[1]["recordCount"]==47'
```

Delete the exact retained package-tool artifact only after all package tests and
both reviews have passed:

```bash
rtk zsh -lc 'set -euo pipefail; tool_artifact="$PWD/.context/hangboard-packages-venv"; if [[ "$tool_artifact" != "$PWD/.context/hangboard-packages-venv" ]]; then exit 1; fi; rtk rm -rf -- "$tool_artifact"; rtk test ! -e "$tool_artifact"'
```

Then run:

```bash
rtk git diff --check origin/main...HEAD
rtk git status --short --branch
rtk gh pr view 388 --json state,headRefName,headRefOid,baseRefName,url
rtk env PASEO_WORKTREE_PATH="$PWD" scripts/paseo-resource-cleanup.sh archive
rtk zsh -lc 'set -euo pipefail; for port in 4187 4188; do if rtk lsof -nP -iTCP:"$port" -sTCP:LISTEN; then exit 1; fi; done'
```

Expected: 47 unique terminal records; exactly five Baguette Evo `BLOCKED`
records; every other record `PASS` or `FIXED`; both independent reviews
`APPROVED` for exact HEAD and ledger hash; clean tracked state; exact tool
artifact absent; capture ports free; verified simulator cleanup; #388 open on
the expected head branch.

- [ ] **Step 2: Push only the validated HEAD to the existing #388 branch.**

Run:

```bash
rtk git push origin HEAD:fix-cords-backfill-gaps-nature-climbing-stone-hanger-mini
rtk gh pr view 388 --json state,headRefName,headRefOid,url
```

Expected: #388's `headRefOid` equals local `HEAD`. Do not run `gh pr create`,
do not push a replacement branch, and do not merge the pull request.

- [ ] **Step 3: Report terminal evidence.**

Report the integrated accepted SHAs in order, final HEAD, 47-record status
counts, Baguette Evo blockers, package/focused/full test results, Workbench and
iOS capture roots, independent review verdicts, cleanup verification, and the
existing #388 URL.
