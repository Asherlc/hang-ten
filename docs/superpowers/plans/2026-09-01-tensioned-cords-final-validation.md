# Tensioned Cords Final Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate only the explicitly accepted tensioned-cord dependency commits, validate exactly 47 source-audited presentations, and conditionally update existing pull request #388 without merging it.

**Architecture:** Three immutable dependency cohorts are accepted and cherry-picked in a fixed order, with a fresh implementation worker and an independent review gate at each boundary. A durable 47-record source ledger joins exact asset facts to source, Workbench, iOS, test, diff, and review evidence; unsupported candidates remain rejected and the five Baguette Evo presentations remain blocked. Publication is a final conditional push to the existing #388 head only.

**Tech Stack:** Git, JSON board packages and RGBA PNG assets, Python 3.11.4+, pytest, HangboardPackages, Hangboard Workbench/Chrome capture, Swift/Xcode, and an isolated iOS Simulator.

**Spec:** `docs/superpowers/specs/2026-09-01-tensioned-cords-final-validation-design.md`

## Global Constraints

- Wait for an explicit acceptance decision naming immutable commits from `tensioned-cords-foundation`, `tensioned-cords-compact-dual`, and `tensioned-cords-inverted-routing`.
- Integrate only accepted commits, in foundation/evidence, compact/dual, then inverted/routed order, with recorded provenance and acceptance boundaries.
- Delegate every implementation edit or configuration change to a fresh subagent; the controller performs integration and review coordination only.
- Independently review every dependency diff and render before integration, and independently review each integrated commit before proceeding to the next cohort.
- Reject unsupported and previously rejected candidates; never infer doubled cords, knots, hidden connections, terminals, hardware, or topology from sibling products or presentations.
- Every cord-bearing presentation shows source-proved cords, and every load-bearing cord is taut in the source-supported direction under canvas-down gravity.
- Preserve exact imagery, holds, material, color, background, alpha, decoded dimensions, framing, scale, position, complete silhouette, and unrelated pixels.
- Preserve the accepted YY Vertical La Baguette `stepped-face` and `reverse-face` presentations.
- Keep all five Baguette Evo presentations `BLOCKED` until exact-revision primary evidence resolves visible topology, hidden continuity, terminals, and hardware.
- Revalidate Nature Stone Hanger Mini `primary` and `side`, KARMA8A `primary`, YY Baguette `reverse-face`, and YY TravelBoard `reverse-10`, including source-proved routing-hole segments and exterior loops and no decorative sag on a load-bearing TravelBoard cord.
- The terminal source ledger contains exactly 47 unique presentation records with honest `PASS`, `FIXED`, or `BLOCKED` status and the complete acceptance matrix from the spec.
- Generated output lives under `.context/tensioned-cords-final-validation/`; external resource names include `tensioned-cords-final-validation`, are recorded immediately, and are deleted by an installed exit trap.
- Update only existing PR #388 after every terminal and accepted-asset gate passes; do not create a replacement pull request and do not merge.
- Do not push any implementation or integration commit to the #388 head before the final publication gate.

---

### Task 1: Dependency Acceptance and Readiness Gate

**Files:**

- Create during execution: `.context/tensioned-cords-final-validation/dependency-acceptance.md`
- Read: `docs/superpowers/specs/2026-09-01-tensioned-cords-final-validation-design.md`
- Read: dependency commit paths reported by the commands below

**Interfaces:**

- Consumes: explicit controller acceptance decisions naming immutable commits from all three dependency workspaces.
- Produces: three ordered accepted-SHA sequences, their provenance/acceptance boundaries, and an independent pre-integration approval for each cohort.

- [ ] **Step 1: Install workspace ownership bookkeeping before creating evidence.**

Run:

```bash
rtk mkdir -p .context/tensioned-cords-final-validation
```

Use `apply_patch` to create `dependency-acceptance.md` and
`owned-resources.md`. Record `.context/tensioned-cords-final-validation`,
Workbench ports `4187` and `4188`, and the future simulator name
`Hang Ten Paseo tensioned-cords-final-validation Review` in
`owned-resources.md`. Do not create an external resource in this task.

- [ ] **Step 2: Wait for explicit immutable acceptance.**

Do not derive acceptance from a branch tip. Continue only after the controller
has stated which commit is accepted from each named branch. Record each exact
SHA, parent SHA, dependency workspace, evidence report, accepted paths,
rejected paths/candidates, reviewer, and decision in
`dependency-acceptance.md`.

- [ ] **Step 3: Resolve and inspect the three recorded commits without changing HEAD.**

Run the following after copying each ordered accepted-SHA sequence from the
recorded decisions into zsh arrays named `foundation_shas`, `compact_shas`, and
`inverted_shas`:

```bash
for accepted_sha in "${foundation_shas[@]}" "${compact_shas[@]}" "${inverted_shas[@]}"; do rtk git cat-file -e "$accepted_sha^{commit}"; done
for accepted_sha in "${foundation_shas[@]}" "${compact_shas[@]}" "${inverted_shas[@]}"; do rtk git show --no-ext-diff --stat --summary "$accepted_sha"; done
for accepted_sha in "${foundation_shas[@]}" "${compact_shas[@]}" "${inverted_shas[@]}"; do rtk git diff --check "$accepted_sha^" "$accepted_sha"; done
```

Expected: all commits exist, each diff is clean, and every changed path is
inside its recorded acceptance boundary.

- [ ] **Step 4: Assign an independent reviewer to each complete commit diff and its renders.**

Each fresh reviewer compares the diff to primary evidence, checks preservation
and cord physics, and records `APPROVED` or `REJECTED` in
`dependency-acceptance.md`. A rejection stops this plan. Do not cherry-pick a
commit until its pre-integration review is `APPROVED`.

- [ ] **Step 5: Verify the integration branch is clean and anchored to the expected PR head.**

Run:

```bash
rtk git status --short --branch
rtk gh pr view 388 --json state,headRefName,headRefOid,baseRefName,url
rtk git rev-parse HEAD
```

Expected: the worktree is clean except workspace-owned `.context` evidence;
#388 is open with head
`fix-cords-backfill-gaps-nature-climbing-stone-hanger-mini`; record its head SHA
as the integration base.

### Task 2: Integrate Foundation and Evidence

**Files:**

- Modify: only paths listed in the accepted foundation commit
- Modify during execution: `.context/tensioned-cords-final-validation/dependency-acceptance.md`

**Interfaces:**

- Consumes: Task 1's approved ordered `foundation_shas` and integration-base SHA.
- Produces: the applied foundation/evidence commits and independently approved all-presentation capture/source-ledger foundation.

- [ ] **Step 1: Delegate the foundation cherry-pick to a fresh implementation subagent.**

Run:

```bash
foundation_base="$(rtk git rev-parse HEAD)"
rtk git cherry-pick "${foundation_shas[@]}"
rtk git diff --check "$foundation_base" HEAD
rtk git diff --name-status "$foundation_base" HEAD
rtk git show --stat --summary "$foundation_base"..HEAD
```

Expected: the cherry-pick applies exactly the accepted commit; no unrelated
path appears.

- [ ] **Step 2: Run the foundation-focused checks declared by that accepted commit.**

At minimum, run the repository's existing all-presentation capture tests and
presentation audit preflight:

```bash
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardWorkbench/tests/test_capture_catalog.py
rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json --phase2-preflight
rtk python3 Tools/HangboardWorkbench/capture_catalog.py --help
```

Expected: tests and audit pass, and help documents `--all-presentations`.

- [ ] **Step 3: Independently review the integrated foundation commit before proceeding.**

A fresh reviewer verifies the applied SHA, source-ledger roster derivation,
all-presentation capture behavior, changed paths, and evidence provenance. Add
the review result to `dependency-acceptance.md`. Stop on any rejection; do not
start Task 3.

### Task 3: Integrate Compact and Dual Boards

**Files:**

- Modify: only paths listed in the accepted compact/dual commit
- Revalidate: `Hangboards/nature-stone-hanger-mini/board.json`
- Revalidate: `Hangboards/nature-stone-hanger-mini/assets/primary.png`
- Revalidate: `Hangboards/nature-stone-hanger-mini/assets/side.png`
- Revalidate: `Hangboards/nature-stone-hanger-mini-karma8a/board.json`
- Revalidate: `Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.png`

**Interfaces:**

- Consumes: the independently approved Task 2 state and Task 1's approved ordered `compact_shas`.
- Produces: an applied, independently approved compact/dual cohort with source-proved routing-hole and exterior-loop preservation.

- [ ] **Step 1: Re-inspect the compact/dual commit against the now-integrated foundation.**

Run:

```bash
for accepted_sha in "${compact_shas[@]}"; do rtk git diff --check "$accepted_sha^" "$accepted_sha"; done
for accepted_sha in "${compact_shas[@]}"; do rtk git diff --name-status "$accepted_sha^" "$accepted_sha"; done
for accepted_sha in "${compact_shas[@]}"; do rtk git show --format=fuller --no-patch "$accepted_sha"; done
```

Expected: the immutable accepted patch and provenance still match Task 1.

- [ ] **Step 2: Delegate the compact/dual cherry-pick to a fresh implementation subagent.**

Run:

```bash
compact_base="$(rtk git rev-parse HEAD)"
rtk git cherry-pick "${compact_shas[@]}"
rtk git diff --check "$compact_base" HEAD
rtk git diff --name-status "$compact_base" HEAD
rtk git show --stat --summary "$compact_base"..HEAD
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

- Modify: only paths listed in the accepted inverted/routed commit
- Revalidate: `Hangboards/yy-travelboard/board.json`
- Revalidate: `Hangboards/yy-travelboard/assets/primary.png`
- Revalidate: `Hangboards/yy-travelboard/assets/reverse.png`
- Revalidate: every orientation-specific asset named by the accepted commit

**Interfaces:**

- Consumes: the independently approved Task 3 state and Task 1's approved ordered `inverted_shas`.
- Produces: an applied, independently approved inverted/routed cohort with canvas-down gravity and tension verified for every orientation.

- [ ] **Step 1: Re-inspect the inverted/routed commit against the integrated state.**

Run:

```bash
for accepted_sha in "${inverted_shas[@]}"; do rtk git diff --check "$accepted_sha^" "$accepted_sha"; done
for accepted_sha in "${inverted_shas[@]}"; do rtk git diff --name-status "$accepted_sha^" "$accepted_sha"; done
for accepted_sha in "${inverted_shas[@]}"; do rtk git show --format=fuller --no-patch "$accepted_sha"; done
```

- [ ] **Step 2: Delegate the inverted/routed cherry-pick to a fresh implementation subagent.**

Run:

```bash
inverted_base="$(rtk git rev-parse HEAD)"
rtk git cherry-pick "${inverted_shas[@]}"
rtk git diff --check "$inverted_base" HEAD
rtk git diff --name-status "$inverted_base" HEAD
rtk git show --stat --summary "$inverted_base"..HEAD
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
- Modify only if source proves a bounded repair: the affected package asset and its `board.json`

**Interfaces:**

- Consumes: all three independently approved integrated cohorts.
- Produces: preserved classic Baguette presentations, five blocked Baguette Evo decisions, and any independently approved source-proved bounded repair.

- [ ] **Step 1: Freeze exact classic and Evo asset facts before review.**

Run:

```bash
rtk shasum -a 256 Hangboards/yy-baguette/assets/primary.png Hangboards/yy-baguette/assets/reverse.png
rtk shasum -a 256 Hangboards/yy-baguette-evo/assets/primary.png Hangboards/yy-baguette-evo/assets/shallow-pairs.png Hangboards/yy-baguette-evo/assets/central-30-25.png Hangboards/yy-baguette-evo/assets/central-20-6.png Hangboards/yy-baguette-evo/assets/tray.png
rtk git diff --name-status origin/main...HEAD -- Hangboards/yy-baguette Hangboards/yy-baguette-evo
```

Record hashes, decoded dimensions, image mode, and alpha behavior in the final
ledger. Confirm classic `stepped-face` and `reverse-face` both remain declared.

- [ ] **Step 2: Audit the five Baguette Evo records without inference.**

For each exact presentation, reopen exact-revision primary sources and record
the unresolved visible topology, hidden continuity, terminals, and hardware.
Mark all five `BLOCKED`, accept no candidate, and do not use a sibling or another
orientation to close a gap.

- [ ] **Step 3: Audit all other candidate changes against the safe-repair rule.**

Accept a repair only when exact-revision primary evidence proves the visible
cord/routing change and the diff preserves dimensions, alpha, board silhouette,
holds, material, color, background, framing, scale, position, and every unrelated
pixel. Reject all others and keep the accepted baseline.

- [ ] **Step 4: If and only if Step 3 proves a necessary repair, delegate it to a fresh implementation subagent.**

The worker changes only the exact package asset and any directly required
presentation declaration, runs the package and focused commands from Tasks 3
and 4, and commits with a package-specific repair message. A fresh reviewer
must approve that commit before Task 6. If no repair is proved, record an
accepted no-op and create no commit.

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

Run:

```bash
rtk python3 Tools/HangboardWorkbench/capture_catalog.py --repository-root "$PWD" --output-root "$PWD/.context/tensioned-cords-final-validation/workbench-all-presentations" --chrome-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --port 4187 --all-presentations
```

Expected: the capture tool terminates its exact Chrome/server children and
writes labeled PNGs, `manifest.json`, and `contact-sheet.png`.

- [ ] **Step 5: Generate hold-ID-overlay captures for every declared presentation.**

Run:

```bash
rtk python3 Tools/HangboardWorkbench/capture_catalog.py --repository-root "$PWD" --output-root "$PWD/.context/tensioned-cords-final-validation/workbench-all-presentations-hold-ids" --chrome-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --port 4188 --all-presentations --hold-id-labels
```

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
- Verify: all paths in `origin/main...HEAD`

**Interfaces:**

- Consumes: reviewed integration, ledger, Workbench evidence, and cleaned iOS validation.
- Produces: final package/status, focused/full-suite, and repository-diff evidence.

- [ ] **Step 1: Run read-only package validation and status.**

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

**Interfaces:**

- Consumes: all implementation, integration, tests, ledger evidence, and full diff.
- Produces: a fresh independent code/provenance review decision.

- [ ] **Step 1: Dispatch a fresh reviewer who implemented none of Tasks 2–8.**

The reviewer checks commit provenance and order, every diff, source boundaries,
47-record uniqueness/completeness, Baguette Evo blockers, package declarations,
hash/dimension/alpha evidence, tests, and absence of unrelated changes.

- [ ] **Step 2: Require an explicit final code verdict.**

Record `APPROVED` only if no finding remains. A finding is routed to a fresh
implementation subagent, then Tasks 6–9 are rerun as applicable. Do not proceed
to visual review with an open finding.

### Task 10: Independent Final Visual Review

**Files:**

- Review: `.context/tensioned-cords-final-validation/workbench-all-presentations/`
- Review: `.context/tensioned-cords-final-validation/workbench-all-presentations-hold-ids/`
- Review: `.context/tensioned-cords-final-validation/ios/`
- Read: all source links and evidence mappings in `docs/source-audits/2026-09-01-tensioned-cords-final-validation.json`

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

Record `APPROVED` only when every accepted record passes and the five Baguette
Evo records remain honestly blocked with no candidate. Route any finding to a
fresh implementation subagent, then rerun all affected captures, tests, ledger
checks, code review, and visual review.

### Task 11: Conditional Update of Existing PR #388 Head Only

**Files:**

- Verify: complete Git history and clean working tree
- Update remotely only after every condition below passes: `origin/fix-cords-backfill-gaps-nature-climbing-stone-hanger-mini`

**Interfaces:**

- Consumes: exactly 47 terminal records, all accepted-asset gates, both independent approvals, and verified owned-resource cleanup.
- Produces: the existing PR #388 head updated to the fully validated commit; no new PR and no merge.

- [ ] **Step 1: Re-run terminal publication assertions.**

Run the Task 6 exact-count and Baguette assertions, then:

```bash
rtk git diff --check origin/main...HEAD
rtk git status --short --branch
rtk gh pr view 388 --json state,headRefName,headRefOid,baseRefName,url
rtk env PASEO_WORKTREE_PATH="$PWD" scripts/paseo-resource-cleanup.sh archive
```

Expected: 47 unique terminal records; exactly five Baguette Evo `BLOCKED`
records; every other record `PASS` or `FIXED`; both independent reviews
`APPROVED`; clean tracked state; verified cleanup; #388 open on the expected
head branch.

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
