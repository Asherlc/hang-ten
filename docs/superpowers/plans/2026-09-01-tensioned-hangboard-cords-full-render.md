# Tensioned Hangboard Cords Full-Render Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every cord-equipped hangboard presentation with an evidence-grounded, whole-object board-and-cord render on genuine transparency, with mechanically correct tension and one highlighted in-app proof screenshot for each presentation.

**Architecture:** A closed-schema cord-render audit owns the 20-package/49-presentation/48-asset cohort and records immutable evidence, generation calls, acceptance decisions, promoted hashes, geometry reviews, and screenshots. Product agents work only in owner-named `.context` packets; independent reviewers approve packets; one serial integration agent promotes reviewed bytes and manually authored geometry. A backward-compatible `geometryRotationAnchor` projects canonical paths for inverted aliases around the physical board rather than the cord-inclusive canvas center.

**Tech Stack:** Python 3.11+ and Pillow for package/audit/image gates; Swift, SwiftUI, XCTest, and iOS Simulator for app decoding/rendering/capture; TypeScript, React, and pytest for Hangboard Workbench; the built-in image generation tool for complete raster synthesis; JSON board packages and source-audit ledgers.

**Spec:** `docs/superpowers/specs/2026-09-01-tensioned-hangboard-cords-full-render-design.md`

## Global Constraints

- Read the complete spec before each implementation or review assignment. Product workers must also read the `imagegen` and `add-hangboard` skills; simulator workers must read `validate-hang-ten-ios`, `docs/IOS_SIMULATOR_VALIDATION.md`, and `docs/IOS_RUNTIME_SERVICES.md`.
- Execute this approved plan with `superpowers:subagent-driven-development`: a fresh implementation agent performs each code, configuration, catalog, audit, asset, or screenshot mutation, followed by a fresh spec-compliance reviewer and then a fresh quality/visual reviewer. Reviewers do not edit; rejected work returns to another fresh implementation agent.
- The controller never edits shared files. It may run read-only checks, dispatch agents, and own exact external-resource identifiers. Every implementation commit is pushed immediately to `origin/feature/hangboard-cord-tension`.
- Prefix every shell command with `rtk`. Use `apply_patch` for text changes. Copying a reviewer-hashed generated PNG is a mechanical binary promotion; verify the source and destination SHA-256 before and after the exact copy.
- Never have more than three product workers plus the controller active. Product workers write only beneath the formal path pattern `.context/joyful-donkey-cords-{slug}-run-{number}/`, with `{slug}` taken from the closed matrix. Only one integration agent may write `Hangboards/`, `docs/source-audits/`, or `docs/pr-screenshots/` at a time.
- Record ownership before creating a local or external resource. Every resource name contains `joyful-donkey`; record exact image-job handles and simulator UUIDs, install an exit/archive cleanup trap, delete only those exact owned resources, and verify absence before completion. Leave shared, standard, unknown, and pre-existing resources alone.
- Every accepted PNG is generated as one complete new scene: board body, cords, knots, hardware, relief, and material together. Do not edit the existing raster, overlay cords, composite candidates, crop, resize, rotate, register, align, warp, paint, sharpen, blur, color-grade, relight, or patch an output. Deterministic chroma removal and its bounded edge decontamination are the only output processing.
- Every official manufacturer photograph found for the exact revision is actual referenced-image input to every generation call. URLs or prompt descriptions do not count. When more than five photographs exist, use at most five verified lossless atlas pages; no panel may be cropped, resampled, warped, rotated, recolored, retouched, or recompressed.
- Generate exactly two initial candidates for each unique PNG. Permit one targeted third only after both initial candidates have concrete recorded rejection reasons. If the third fails, block the asset; never continue aesthetic retries.
- Gravity is normalized canvas down, `(0, +1)`. Every depicted board remains below its suspension/support while the climber loads it downward from below. Every force-bearing cord or strap branch leaves the board taut upward toward overhead support, and no load-bearing cord, tail, knot, or hardware appears below the board. The Mini Bar retains its documented exterior-body sling attachment routing without a below-board load path; Rock Rings and Penta retain independent overhead suspensions. Do not transfer routing between products.
- Rotate the physical board, not gravity. Concave recesses remain concave. Source/alias bodies retain identical scale, normalized position, aspect ratio, silhouette, and relief. Reject generator drift instead of compensating with per-hold offsets.
- Hold geometry is authored and reviewed manually. Do not use detection, segmentation, masks, contours, image registration/alignment, vectorization, automatic path simplification, automatic cropping, or proposal/refine/promote geometry workflows. The saved canonical path remains the only rendering, highlighting, and hit-testing source.
- Do not modify or rebaseline `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json` or its narrative. Their starting hashes are respectively `72d1d68bdb1e802a9c83b3312c18d5ee88878b94d0ddbef59085dbcaa4d839ff` and `3dc4fb20b089b2f900477c0d42dcb3edb71df124f9ccaca9f2e326e7a5be685a`.
- Package roots contain exactly `board.json` and `assets/`; every file below `assets/` is declared by a presentation and every declared asset exists. Sources, atlases, prompts, candidates, conversion intermediates, reviews, and temporary captures never enter package roots.
- Final acceptance is exactly 20 scoped packages, 49 presentation records, 48 unique declared PNG paths, and 49 selected-hold app screenshots. The Port-A-Board shared path explains the one-record difference.

## File and Interface Map

### Existing files to modify

- `Tools/HangboardPackages/src/hangboard_packages/board_geometry_schema.py`: strict normalized point type for `geometryRotationAnchor`.
- `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`: Python package decoding and alias/anchor/aspect/projected-bounds validation.
- `Tools/HangboardPackages/src/hangboard_packages/cli.py`: cord asset, audit, and capture command entry points.
- `Tools/HangboardPackages/pyproject.toml`: make the already-tested Pillow dependency available to the runtime image commands.
- `scripts/hangboard-packages.sh`: expose the new cord commands through the repository wrapper.
- `HangTen/Models/TrainingModels.swift`: `BoardGeometryRotationAnchor`, the `BoardPresentation` field, and the shared projection helper used by shapes and markers.
- `HangTen/Models/BoardPackageStore.swift`: strict anchor decode, alias rules, equal-aspect rule, and projected-bounds validation.
- `HangTen/Models/BoardPackageWriter.swift`: editor decode/validation/canonical encoding and round-trip preservation.
- `HangTen/Views/BoardMapView.swift`: use one projected shape for normal/active visuals, interaction/accessibility shapes, and number markers; remove center-based `rotationEffect`.
- `Tools/HangboardWorkbench/board_package.py`: strict anchor parsing and alias preview projection in image coordinates.
- `Tools/HangboardWorkbench/server.py`, `Tools/HangboardWorkbench/src/types.ts`, and `Tools/HangboardWorkbench/src/workbench-client.ts`: expose and validate inversion/anchor metadata while continuing to render the server-projected canonical paths.
- `HangTen/Views/TrainView.swift`: DEBUG-only exact board/presentation/hold review route.
- `docs/IOS_SIMULATOR_VALIDATION.md`: document that exact capture route and its release-build exclusion.

### New focused files

- `Tools/HangboardPackages/src/hangboard_packages/cord_render_assets.py`: byte/pixel hashing, immutable source lock, deterministic lossless atlas build/round-trip proof, chroma removal, and focused transparency inspection.
- `Tools/HangboardPackages/src/hangboard_packages/cord_render_audit.py`: closed-schema lifecycle parser and cross-checker for evidence, candidates, promoted assets, geometry reviews, and screenshots.
- `Tools/HangboardPackages/src/hangboard_packages/cord_render_capture.py`: explicit-owned-simulator capture runner that writes an untracked screenshot index and never edits the audit.
- `Tools/HangboardPackages/tests/test_cord_render_assets.py`, `test_cord_render_audit.py`, and `test_cord_render_capture.py`: focused unit coverage.
- `Tools/HangboardPackages/tests/test_cord_render_catalog_audit.py`: production cohort/count/historical-hash regression test.
- `docs/source-audits/2026-09-01-tensioned-hangboard-cords.json`: machine ledger with 49 presentation and 48 deduplicated asset records.
- `docs/source-audits/2026-09-01-tensioned-hangboard-cords.md`: human narrative, supersession statement, blockers, review decisions, and final gate results.
- `docs/pr-screenshots/2026-09-01-tensioned-hangboard-cords/{slug}/{presentation-id}-highlighted.png`: 49 actual app captures, with both variables taken from the closed matrix/live package record.

### Test files to extend

- `Tools/HangboardPackages/tests/test_board_geometry_schema.py`
- `Tools/HangboardPackages/tests/test_board_catalog.py`
- `Tools/HangboardPackages/tests/test_cli.py`
- `HangTenTests/BoardPackageStoreTests.swift`
- `HangTenTests/BoardPackageWriterTests.swift`
- `HangTenTests/BoardSourceBoundaryTests.swift`
- `Tools/HangboardWorkbench/tests/test_board_package.py`
- `Tools/HangboardWorkbench/tests/test_server.py`
- `Tools/HangboardWorkbench/tests/workbench-modules.test.ts`

## Closed Cohort and Batch Matrix

The presentation IDs and paths below are the checked-in starting inventory. A presentation rename, path split, or path merge changes the 49/48 contract and requires a separately approved design decision.

| Wave | Mechanical family | Package slug | Presentation IDs | Presentations | Unique PNGs | Evidence/review focus |
| --- | --- | --- | --- | ---: | ---: | --- |
| O1 | overhead | `aelith-cyclops-011` | `primary` | 1 | 1 | Exact revision, visible attachment traversal, knot, and taut overhead branch |
| O1 | overhead | `captain-fingerfood-dual` | `primary`, `reverse` | 2 | 2 | Both usable faces and face-specific concavity/routing |
| O1 | overhead | `captain-fingerfood-pocket` | `primary` | 1 | 1 | Pocket relief remains recessive; exact support arrangement |
| O2 | overhead | `captain-fingerfood-unlevel` | `primary`, `reverse` | 2 | 2 | Both usable faces and asymmetrical level/attachment identity |
| O2 | overhead aliases | `crimptonite-helium-mobile` | `primary`, `front-inverted`, `reverse`, `reverse-inverted` | 4 | 4 | Atomic source/alias pairs, same body placement, no generic bottom wrap |
| O2 | overhead | `metolius-light-rail-2` | `20mm-side`, `15mm-side` | 2 | 2 | Preserve transparent framing while restoring exact cords to both sides |
| O3 | overhead | `nature-stone-hanger-mini` | `primary`, `side` | 2 | 2 | Exact stone/material identity and surface-specific routing |
| O3 | overhead | `nature-stone-hanger-mini-karma8a` | `primary` | 1 | 1 | Exact collaboration revision and attachment details |
| O3 | overhead | `yy-baguette` | `stepped-face`, `reverse-face` | 2 | 2 | Both faces, recess/edge relief, and taut support |
| O4 | overhead | `yy-baguette-evo` | `paired-25-20-15-10`, `paired-12-8-6`, `central-30-25`, `central-20-6`, `rounded-tray` | 5 | 5 | Five named contact configurations without blending surfaces |
| O4 | overhead | `yy-travelboard` | `front-25-15`, `reverse-10` | 2 | 2 | Replace current partial/slack loops with evidence-backed taut routing |
| O4 | overhead aliases | `tension-flash-board` | `three-edge-upright`, `three-edge-inverted`, `two-edge-upright`, `two-edge-inverted` | 4 | 4 | Preserve concavity, complete both source/alias pairs, prove pilot provenance |
| N | evidence-selected overhead routing | `frictitious-nug` | `primary`, `reverse` | 2 | 2 | Establish exact attachment topology independently for each presentation; loaded branches resolve upward |
| L | straps-up lifting edge | `lattice-mxedge-lift-large` | `primary`, `large-medium-edge-position`, `mono-position` | 3 | 3 | Every force-bearing strap points canvas up; exact large-size revision and positions |
| L | straps-up lifting edge | `lattice-mxedge-lift-small` | `primary`, `large-medium-edge-position`, `mono-position` | 3 | 3 | Every force-bearing strap points canvas up; exact small-size revision and positions |
| L | straps-up lifting edge | `plateau-lifting-edge` | `primary` | 1 | 1 | Board below support; every force-bearing strap points canvas up |
| S | exterior sling | `lattice-mini-bar` | `edge-10`, `edge-20`, `ergonomic-jug`, `mini-pinch` | 4 | 4 | Preserve manufacturer-documented lower/outer body sling contact while every loaded return branch runs upward |
| I | independent units | `metolius-rock-rings-3d` | `front-pair` | 1 | 1 | Each ring has its own suspension; no unsupported bridge |
| I | independent units | `yy-penta-evo` | `front-pair` | 1 | 1 | Each unit has its own suspension and identical exact-revision pair identity |
| P | optional portable | `frictitious-port-a-board` | `primary`, `front-inverted`, `cord-option-4-20mm-incut`, `back`, `back-inverted`, `side` | 6 | 5 | Portable cord mode only; option 4 starts evidence-blocked and shares `assets/front-inverted.png` |
| **Total** |  | **20 packages** |  | **49** | **48** |  |

Wave totals are O1 `4/4`, O2 `8/8`, O3 `5/5`, O4 `11/11`, N `2/2`, L `7/7`, S `4/4`, I `2/2`, and P `6/5` for presentation/PNG counts.

## Ownership and Product Packet Contract

Every product worker produces this exact untracked shape and never writes a tracked path:

```text
.context/joyful-donkey-cords-{slug}-run-1/
  OWNERSHIP.json
  sources/index.json
  sources/original/{source-id}.{original-extension}
  atlases/index.json
  atlases/page-01.png ... page-05.png
  contracts/{presentation-id}.json
  prompts/{asset-key}/candidate-01.txt
  prompts/{asset-key}/candidate-02.txt
  prompts/{asset-key}/candidate-03.txt        # present only after two recorded rejections
  candidates/{asset-key}/candidate-01-raw.png
  candidates/{asset-key}/candidate-01-rgba.png
  candidates/{asset-key}/candidate-01-report.json
  reviews/owner.json
  reviews/independent.json
  packet.json
```

`OWNERSHIP.json` records `owner: "joyful-donkey"`, package slug, absolute directory, creator task, created time, exact external handles, cleanup command, and cleanup verification. `packet.json` is closed-schema and records the package ID, all presentation IDs, all unique asset paths, SHA-256 for every file, ordered reference list for every call, candidate dispositions, and the independent reviewer decision.

Each `contracts/{presentation-id}.json` is manually authored after reviewing all evidence and contains: exact revision; usable surface; material; gravity `[0, 1]`; mechanical family; loaded object; downward climber-load direction; overhead support direction; each visible attachment point; ordered hole/body traversal; supported knots, bights, crossings, independent strands, and short tails; taut segments; forbidden topology; silhouette/contact inventory; and relief constraints. Every contract keeps the board below support, every force-bearing branch upward, and every cord, tail, knot, and hardware component out of the area below the board. An unknown fact is a named evidence blocker, not an inferred value.

## Task 0: Establish the Owned Baseline and Known-Red Historical Preflight

**Files:**
- Create only under ignored context: `.context/joyful-donkey-cords-execution/OWNERSHIP.json`
- Read: all 20 `Hangboards/{slug}/board.json` files in the matrix, substituting each literal matrix slug
- Read and hash only: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Read and hash only: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Produces: a controller-owned execution directory, exact baseline commit, exact historical hashes, current package validation output, and the owned simulator/resource manifest used by later tasks.
- Does not produce a tracked change or commit.

- [ ] **Step 1: Dispatch a fresh setup agent and record ownership before creating anything else.** Derive the owner from the final worktree component and require it to equal `joyful-donkey`. Create the one exact execution directory with `apply_patch`; record the current branch/commit and the literal cleanup target. Install an exit/archive trap that invokes `PASEO_WORKTREE_PATH=/Users/asherlc/.paseo/worktrees/0h78jp9r/joyful-donkey scripts/paseo-resource-cleanup.sh archive` and removes only resources listed in this ownership file.

- [ ] **Step 2: Verify the branch and clean tracked baseline.**

```bash
rtk git status --short --branch
rtk git rev-parse HEAD
rtk git rev-parse origin/feature/hangboard-cord-tension
```

Expected: the branch is `feature/hangboard-cord-tension`, local and remote both start at the approved design commit or its reviewed successor, and no tracked file is dirty.

- [ ] **Step 3: Capture the current green package baseline.**

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
rtk npm --prefix Tools/HangboardWorkbench test
rtk env SRCROOT=/Users/asherlc/.paseo/worktrees/0h78jp9r/joyful-donkey scripts/verify-board-source-boundary-manifest.sh
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
```

Expected: current repository gates pass. Record any unrelated baseline failure verbatim before continuing; do not silently normalize it.

- [ ] **Step 4: Confirm the historical audit is immutable and record its known stale-hash result.**

```bash
rtk shasum -a 256 docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json --phase2-final
```

Expected: hashes equal the two constants in Global Constraints. The historical final audit may fail on stale current asset hashes; record that as the pre-existing result and do not edit either historical file.

- [ ] **Step 5: Reconcile the closed cohort from live JSON.** Use a read-only `rtk jq` query to assert the matrix yields 20 distinct slugs, 49 presentation records, and 48 distinct `(slug, assetPath)` values. Assert the only within-package shared path is Port-A-Board `assets/front-inverted.png`, used by `front-inverted` and `cord-option-4-20mm-incut`.

- [ ] **Step 6: Create and immediately register one exact owned simulator.** Before creation, record the intended name, device type, and runtime in `OWNERSHIP.json` and the pending-resource manifest. Create `Hang Ten Paseo joyful-donkey Cord Render Review` with the installed `com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro` and `com.apple.CoreSimulator.SimRuntime.iOS-26-5`. Validate the returned UUID, add it to `.context/paseo-owned-simulators`, write it as `simulatorUUID` in `OWNERSHIP.json` using `apply_patch`, then clear only its pending record.

```bash
rtk xcrun simctl create 'Hang Ten Paseo joyful-donkey Cord Render Review' com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5
```

Expected: one UUID is returned and `rtk xcrun simctl list devices` shows that exact UUID/name. Later commands read this UUID from the ownership file and never use `booted`.

- [ ] **Step 7: Have a fresh reviewer compare the baseline record to the spec.** The reviewer confirms exact counts, exact historical hashes, no tracked mutation, exact simulator ownership, and trap installation. A mismatch stops Task 1.

## Task 1: Add Strict Python Alias-Anchor Schema Validation

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_geometry_schema.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`
- Modify: `Tools/HangboardPackages/tests/test_board_geometry_schema.py`
- Modify: `Tools/HangboardPackages/tests/test_board_catalog.py`

**Interfaces:**
- Produces: `NormalizedPoint.from_json(value, label)` and `BoardPresentation.geometry_rotation_anchor: NormalizedPoint | None`.
- Validation contract: `geometryRotationAnchor` is exactly `{x, y}` with finite normalized values; it is legal only with `sourcePresentationID` and `isInverted: true`; source and alias aspect ratios match; projected source-owned frames remain inside `[0, 1]`.
- Projection formula: `project_normalized_point(point, anchor) -> (2 * anchor.x - point.x, 2 * anchor.y - point.y)`; omission uses the existing center behavior and stores `None`.

- [ ] **Step 1: Write failing normalized-point tests.** Add cases that accept `{ "x": 0.5, "y": 0.68 }` and reject missing/unknown keys, booleans, NaN/infinity, and values outside `[0, 1]`.

```python
def test_normalized_point_requires_finite_unit_coordinates() -> None:
    assert NormalizedPoint.from_json({"x": 0.5, "y": 0.68}, "anchor") == NormalizedPoint(0.5, 0.68)
    with pytest.raises(ValueError, match="at most 1"):
        NormalizedPoint.from_json({"x": 1.01, "y": 0.5}, "anchor")
```

- [ ] **Step 2: Write failing board-catalog tests.** Use `write_multi_presentation_board_package` fixtures for default-center compatibility, a valid non-center anchor, anchor on a canonical presentation, anchor on a non-inverted alias, invalid aspect ratio, and an anchor that projects a source hold outside the target canvas. Assert the parsed dataclass preserves the custom anchor.

- [ ] **Step 3: Run the focused tests and verify red failures.**

```bash
rtk uv run --with pytest python -m pytest -q Tools/HangboardPackages/tests/test_board_geometry_schema.py Tools/HangboardPackages/tests/test_board_catalog.py -k 'normalized_point or rotation_anchor'
```

Expected: failures show the field/type and validation are absent; no unrelated test fails.

- [ ] **Step 4: Implement the minimum closed-schema behavior.** Add `NormalizedPoint` using the module's `_mapping`, `_closed`, and `_float` helpers. Extend `BoardPresentation.from_json` optional keys with `geometryRotationAnchor`. After all presentations and holds are parsed, validate alias legality, source/target aspect equality, and the projected min/max of every source-owned piece frame. Do not add affine matrices, per-hold offsets, or geometry overrides.

- [ ] **Step 5: Run focused and complete Python package tests.**

```bash
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_board_geometry_schema.py Tools/HangboardPackages/tests/test_board_catalog.py
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
```

Expected: all pass, and all existing packages still decode with omitted anchors.

- [ ] **Step 6: Run two fresh review gates.** The spec reviewer checks the exact alias-only contract and center compatibility. The quality reviewer checks finite-number handling, source lookup, aspect comparison, projected bounds, and regression tests. A rejection returns to a new implementation agent.

- [ ] **Step 7: Commit and push only this task.**

```bash
rtk git add Tools/HangboardPackages/src/hangboard_packages/board_geometry_schema.py Tools/HangboardPackages/src/hangboard_packages/board_catalog.py Tools/HangboardPackages/tests/test_board_geometry_schema.py Tools/HangboardPackages/tests/test_board_catalog.py
rtk git commit -m "Validate hangboard alias rotation anchors"
rtk git push origin feature/hangboard-cord-tension
```

## Task 2: Decode, Validate, and Round-Trip Alias Anchors in Swift

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Models/BoardPackageStore.swift`
- Modify: `HangTen/Models/BoardPackageWriter.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/BoardPackageWriterTests.swift`

**Interfaces:**
- Produces: `BoardGeometryRotationAnchor(x:y:)`, `.center`, and `BoardPresentation.geometryRotationAnchor: BoardGeometryRotationAnchor?`.
- Store and writer enforce the same legality, equal-aspect, finite/range, and projected-frame rules as Task 1.
- Writer emits `geometryRotationAnchor` after `isInverted` in canonical presentation JSON and omits it when absent.

- [ ] **Step 1: Add failing store fixture tests.** Extend a multi-presentation fixture with an inverted alias anchored at `(0.5, 0.68)`. Assert the runtime model preserves it. Add separate rejection tests for a source-owned anchor, a non-inverted alias anchor, `1e999`, a coordinate above one, source/target aspect mismatch, and out-of-canvas projected geometry.

- [ ] **Step 2: Add failing writer tests.** Construct `BoardEditablePresentation` with and without an anchor. Assert decode/encode/decode equality, stable canonical output, field omission for the default behavior, and the same invalid combinations as the store.

- [ ] **Step 3: Run a compile-only red gate.**

```bash
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardPackageWriterTests
```

Expected: compilation fails because the new types/properties do not exist.

- [ ] **Step 4: Implement the model and store.** Define the normalized anchor as a small `Hashable` value in `TrainingModels.swift`. Extend the strict `BoardPackagePresentationDocument` coding keys and `trainingPresentation`. After `validateHolds`, validate projected piece-frame corners against the target canvas. Keep an omitted anchor as `nil`, not a serialized center value.

- [ ] **Step 5: Implement editor decode/validation/encoding.** Extend `BoardEditablePresentation` and its strict unknown-key list, validate before serialization, and add a canonical object for `{ "x": ..., "y": ... }`. Use the same error reasons for semantically identical store/writer failures.

- [ ] **Step 6: Run focused tests on the explicit owned simulator UUID from Task 0.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$(rtk jq -r '.simulatorUUID' .context/joyful-donkey-cords-execution/OWNERSHIP.json)" -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardPackageWriterTests
```

Expected: both suites pass. The literal UUID is the exact recorded Task 0 resource; never substitute `booted` or a shared name.

- [ ] **Step 7: Run two fresh review gates.** The spec reviewer compares every validation rule with Task 1. The quality reviewer checks strict decoding, writer ordering, equality, error messages, and real-package round trips.

- [ ] **Step 8: Commit and push only this task.**

```bash
rtk git add HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift HangTen/Models/BoardPackageWriter.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/BoardPackageWriterTests.swift
rtk git commit -m "Round trip hangboard alias rotation anchors"
rtk git push origin feature/hangboard-cord-tension
```

## Task 3: Use One Projection for SwiftUI Paths, Highlights, Markers, and Hit Tests

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Views/BoardMapView.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift`

**Interfaces:**
- Produces: `BoardPresentationGeometryProjection(presentation:)`, `project(_ point: CGPoint, in rect: CGRect) -> CGPoint`, and `project(_ path: Path, in rect: CGRect) -> Path`.
- `BoardHoldPathShape` accepts a projection, builds the canonical path once, and returns the projected path.
- `PhysicalHoldVisual` receives the same projection used by `BoardDetailMapView` marker centers; no `rotationEffect` remains.

- [ ] **Step 1: Add failing pure projection tests.** Cover identity, center inversion, non-center `(0.5, 0.68)`, a multi-piece path, and a marker center. For a rectangular fixture, assert both `shape.path(in:).contains(projectedCenter)` and the marker point equal the same projection result.

```swift
let projection = BoardPresentationGeometryProjection(
    isInverted: true,
    rotationAnchor: .init(x: 0.5, y: 0.68)
)
XCTAssertEqual(
    projection.project(CGPoint(x: 20, y: 30), in: CGRect(x: 0, y: 0, width: 100, height: 100)),
    CGPoint(x: 80, y: 106)
)
```

- [ ] **Step 2: Strengthen the source-boundary regression test.** Require `BoardMapView.swift` to construct one projected `BoardHoldPathShape`, use it for `.fill`, `.stroke`, `.contentShape(.interaction, ...)`, and `.contentShape(.accessibility, ...)`, and not contain the old inverted `rotationEffect` expression.

- [ ] **Step 3: Run the focused build and verify red.**

```bash
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardSourceBoundaryTests
```

Expected: the new projection tests or compile references fail.

- [ ] **Step 4: Implement the shared projection.** Transform around the normalized anchor in the actual board rect. Build `BoardHoldPathShape` from the canonical pieces, then apply that transform to the `Path`. Pass the same projection into every `PhysicalHoldVisual`; compute number-marker centers with `projection.project`. Remove `isInverted`-only frame rotations so visual and interaction geometry cannot diverge.

- [ ] **Step 5: Run focused XCTest and a generic build.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$(rtk jq -r '.simulatorUUID' .context/joyful-donkey-cords-execution/OWNERSHIP.json)" -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardSourceBoundaryTests
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
```

Expected: tests and build pass; default-center packages render as before.

- [ ] **Step 6: Perform a fresh interaction review.** On one center alias and a temporary non-center fixture, inspect normal, all-active, selected, marker, VoiceOver/accessibility target, and taps at path edges. The reviewer records that the exact same path drives each state.

- [ ] **Step 7: Commit and push only this task.**

```bash
rtk git add HangTen/Models/TrainingModels.swift HangTen/Views/BoardMapView.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/BoardSourceBoundaryTests.swift
rtk git commit -m "Project inverted hangboard interaction geometry"
rtk git push origin feature/hangboard-cord-tension
```

## Task 4: Apply the Identical Anchor Projection in Hangboard Workbench

**Files:**
- Modify: `Tools/HangboardWorkbench/board_package.py`
- Modify: `Tools/HangboardWorkbench/server.py`
- Modify: `Tools/HangboardWorkbench/src/types.ts`
- Modify: `Tools/HangboardWorkbench/src/workbench-client.ts`
- Modify: `Tools/HangboardWorkbench/tests/test_board_package.py`
- Modify: `Tools/HangboardWorkbench/tests/test_server.py`
- Modify: `Tools/HangboardWorkbench/tests/workbench-modules.test.ts`

**Interfaces:**
- Extends `BoardPresentation` with `geometry_rotation_anchor: tuple[float, float] | None`.
- Changes `_inverted_display_path(path, width, height, anchor, label=...)` to project each x/y pair around `(anchor.x * width, anchor.y * height)`.
- Browser API exposes optional `isInverted: true` and `geometryRotationAnchor: {x, y}` for alias metadata; `EditorDocument.regions[].displayPath` remains the authoritative already-projected preview/interaction path.

- [ ] **Step 1: Write failing Python Workbench tests.** Add strict parse cases matching Tasks 1–2. Change the inverted alias fixture to `(0.5, 0.68)` and assert path extrema use `2 * anchorPixel - sourceCoordinate`. Assert alias saves remain prohibited and source geometry remains unchanged.

- [ ] **Step 2: Write failing server/client tests.** Assert the board API returns `isInverted` and the anchor only when declared, and the TypeScript client rejects malformed coordinates, unknown anchor keys, and an anchor on a non-inverted/source presentation response.

- [ ] **Step 3: Run focused red tests.**

```bash
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py -k 'anchor or inverted_alias'
rtk npm --prefix Tools/HangboardWorkbench run test:modules
```

Expected: the new anchor assertions fail.

- [ ] **Step 4: Implement strict parsing and projection.** Extend `_parse_board_presentations`, the dataclass, package construction, server payload, TypeScript types, and client guards. Keep all alias regions read-only. Do not infer anchors from pixels or add client-side fitting.

- [ ] **Step 5: Run all Workbench gates.**

```bash
rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
rtk npm --prefix Tools/HangboardWorkbench test
rtk npm --prefix Tools/HangboardWorkbench run check:bundle
```

Expected: Python, TypeScript, React, typecheck, and bundle checks pass.

- [ ] **Step 6: Perform a fresh Workbench visual/interaction review.** Load the non-center fixture, compare source and alias side by side, click each piece and its boundary, and confirm displayed path, selection outline, and pointer target coincide while editing remains disabled.

- [ ] **Step 7: Commit and push only this task.**

```bash
rtk git add Tools/HangboardWorkbench/board_package.py Tools/HangboardWorkbench/server.py Tools/HangboardWorkbench/src/types.ts Tools/HangboardWorkbench/src/workbench-client.ts Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py Tools/HangboardWorkbench/tests/workbench-modules.test.ts
rtk git commit -m "Project Workbench aliases around board anchors"
rtk git push origin feature/hangboard-cord-tension
```

## Task 5: Build Deterministic Evidence, Atlas, Chroma, and Transparency Tools

**Files:**
- Create: `Tools/HangboardPackages/src/hangboard_packages/cord_render_assets.py`
- Create: `Tools/HangboardPackages/tests/test_cord_render_assets.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `Tools/HangboardPackages/tests/test_cli.py`
- Modify: `Tools/HangboardPackages/pyproject.toml`
- Modify: `scripts/hangboard-packages.sh`

**Interfaces:**
- `lock_source(path: Path, *, source_id: str, url: str, publisher: str, role: str, revision: str, reviewed_at: date) -> LockedSource`
- `decoded_pixel_sha256(path: Path) -> str`: hashes mode, dimensions, and decoded pixel bytes, independent of PNG/JPEG container metadata.
- `build_lossless_atlases(sources: Sequence[LockedSource], output_dir: Path, *, max_pages: int = 5) -> AtlasIndex`: deterministic source order, neutral padding/labels outside panels, no source transform.
- `verify_atlas_round_trip(index: AtlasIndex) -> AtlasVerification`: crops only the atlas panel rectangle for verification and proves mode, dimensions, and decoded pixels match each frozen source exactly.
- `remove_chroma(input_path: Path, output_path: Path, config: ChromaConfig) -> TransparencyReport`: preserves dimensions and non-key pixels; supports a recorded alternative key when the product itself conflicts with green.
- `inspect_transparency(path: Path, expected_width: int, expected_height: int, key_rgb: tuple[int, int, int]) -> TransparencyReport`.
- CLI: `hangboard-packages cord-assets lock|atlas|key|inspect` writes reports only to caller-provided `.context/joyful-donkey-*` paths.

**Publication transaction contract:** All supported `cord_render_assets`
writers for one owner context serialize with a process-local reentrant lock and
a cross-process `flock`, held through commit and cleanup. Normal external
changes at observable boundaries remain detected and preserved. Arbitrary
same-UID direct mutation during an exact name-based `unlink` or `rmdir` is
outside the supported concurrency contract because macOS/POSIX has no
inode-conditional delete operation. Created output-parent directories are
monotonic and never destructively rolled back. One all-output final precommit
verification precedes an explicit `COMMITTED` state. Precommit errors roll
back; postcommit cleanup errors never roll back, leave every output
consistently committed, and raise with `publication committed; cleanup state is
unproven`. Register every generated old- or new-output quarantine name before
its syscall, then reconcile it or disclose it.

- [ ] **Step 1: Write failing source-lock and decoded-pixel tests.** Use two images with identical decoded pixels but different container metadata to assert equal pixel hashes and unequal byte hashes. Reject symlinks, mutable/missing source metadata, duplicate source IDs, non-image files, and output paths outside an owner-named context directory.

- [ ] **Step 2: Write failing atlas tests.** Build an atlas from six differently sized lossless fixtures. Assert one to five pages, deterministic byte hashes across runs, unchanged sources, non-overlapping panel rectangles, exact panel mode/dimensions/pixels, and failure when a supplied index is tampered. Assert no resize/crop/rotate parameters exist in the interface.

- [ ] **Step 3: Write failing chroma/alpha tests.** Cover an RGB chroma candidate, antialiased key-edge pixels, existing alpha, a green product pixel isolated from the boundary, transparent corners, opaque/off-white background flood, chroma fringe, wrong dimensions, and an all-opaque RGBA file. Assert output dimensions and fully non-key opaque pixels are byte-identical.

- [ ] **Step 4: Run the new tests and verify red.**

```bash
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardPackages/tests/test_cord_render_assets.py Tools/HangboardPackages/tests/test_cli.py -k 'cord_assets or atlas or chroma or transparency'
```

Expected: imports and CLI commands are absent.

- [ ] **Step 5: Implement the deterministic tools.** Use Pillow without EXIF autorotation. Atlas pages place original decoded panels without resampling and save losslessly; labels/padding never overlap panels. Chroma conversion uses the exact recorded key and bounded thresholds from `ChromaConfig`; decontamination is applied only to partially keyed boundary-connected pixels. The report records config, input/output hashes, dimensions, alpha extrema, corner alpha, transparent fraction, boundary-connected opaque-flood count, and remaining key-fringe count.

- [ ] **Step 6: Expose commands without broadening package validation.** Add Pillow as a runtime dependency for this tool package, nested `cord-assets` parsers, and wrapper allow-list/help entries. Commands refuse a sixth atlas page and refuse in-place keying.

- [ ] **Step 7: Run focused and complete gates.**

```bash
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_cord_render_assets.py Tools/HangboardPackages/tests/test_cli.py
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Expected: all pass; generic validation still permits legacy opaque packages while the focused cord command rejects them.

- [ ] **Step 8: Run two fresh review gates.** The spec reviewer checks that atlas work is input-only and chroma removal is the sole output transform. The quality reviewer inspects hashing determinism, symlink/path confinement, pixel preservation, fringe/flood detection, and CLI errors.

- [ ] **Step 9: Commit and push only this task.**

```bash
rtk git add Tools/HangboardPackages/src/hangboard_packages/cord_render_assets.py Tools/HangboardPackages/tests/test_cord_render_assets.py Tools/HangboardPackages/src/hangboard_packages/cli.py Tools/HangboardPackages/tests/test_cli.py Tools/HangboardPackages/pyproject.toml scripts/hangboard-packages.sh
rtk git commit -m "Add cord render evidence and transparency gates"
rtk git push origin feature/hangboard-cord-tension
```

## Task 6: Add the Closed Cord-Render Audit and Lifecycle Validator

**Files:**
- Create: `Tools/HangboardPackages/src/hangboard_packages/cord_render_audit.py`
- Create: `Tools/HangboardPackages/tests/test_cord_render_audit.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `Tools/HangboardPackages/tests/test_cli.py`
- Modify: `scripts/hangboard-packages.sh`

**Interfaces:**
- `load_cord_render_audit(path: Path) -> CordRenderAudit`
- `validate_cord_render_audit(audit, inventory, *, root: Path, mode: AuditMode, packet_roots: Sequence[Path] = (), selected_package_ids: frozenset[str] = frozenset()) -> CordRenderReport`
- `AuditMode` values: `INITIAL`, `PACKET`, `PARTIAL`, `FINAL`.
- CLI: `hangboard-packages audit-cord-renders --root Hangboards --audit docs/source-audits/2026-09-01-tensioned-hangboard-cords.json --mode initial|packet|partial|final`; packet/partial calls additionally accept the exact owner path and literal matrix package ID.

The root JSON has exactly `schemaVersion`, `reviewDate`, `cohort`, `historicalBaseline`, `presentationRecords`, and `assetRecords`. `schemaVersion` is integer `1`. `cohort` has exact package/presentation/asset counts and sorted package IDs/slugs. `historicalBaseline` records both immutable paths and starting SHA-256 values.

Every presentation record has a stable key `{packageID}:{presentationID}`, package ID/slug, presentation ID/name, asset path, source presentation ID, inversion flag, aspect ratio, physical revision, material, mechanical family, gravity `[0,1]`, usable surface, load-path contract, relief constraints, official and corroborating sources, atlas/call references, lifecycle state, geometry review, optional alias-anchor review, reviewer decision, and screenshot record. Every asset record has `{slug}:{assetPath}`, all consuming presentation keys, candidate records, selected candidate, raw/keyed/promoted hashes and dimensions, transparency report, processing declaration exactly `chromaRemoval`, package validation result, and reviewer decision.

Legal lifecycle states are `pendingEvidence`, `blockedEvidence`, `readyToGenerate`, `candidateReview`, `accepted`, and `rejected`. `INITIAL` requires complete 20/49/48 coverage and permits pending/blocked records. `PACKET` additionally validates transient source, atlas, candidate, and report files against hashes. `PARTIAL` validates promoted accepted records while permitting explicitly reported blockers. `FINAL` requires every record accepted, all 48 current package hashes/transparency reports valid, and all 49 tracked screenshot hashes valid.

- [ ] **Step 1: Write a minimal valid unit fixture and closed-schema failures.** The fixture contains one package, two presentations sharing one asset, two complete candidate dispositions, one selected candidate, and two screenshot records. Reject missing/unknown keys, wrong scalar types, duplicate keys, unsorted cohort IDs, and illegal lifecycle transitions.

- [ ] **Step 2: Write cross-record/count tests.** Reject a presentation absent from live `board.json`, an undeclared asset, incorrect source alias/aspect/inversion, asset consumer mismatch, duplicate screenshot path, candidate 3 without two rejections, more than three candidates, accepted output without exactly two initial candidates, and any processing declaration besides `chromaRemoval`.

- [ ] **Step 3: Write evidence/reference tests.** Reject an official source omitted from a candidate's ordered reference set, an unverified atlas, more than five reference images, mismatched byte/pixel hashes, mixed revisions, a missing manually authored contract, and a source URL listed without supplied pixels. In packet mode, mutate each transient file and assert hash failure.

- [ ] **Step 4: Write final-mode tests.** Reject pending/blocked records, a non-RGBA/opaque/fringed promoted asset, wrong dimensions/aspect, missing geometry or independent review, missing/non-highlighted screenshot declaration, wrong screenshot hash, historical baseline hash drift, and counts other than `20/49/48/49` for the production cohort.

- [ ] **Step 5: Run focused red tests.**

```bash
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardPackages/tests/test_cord_render_audit.py Tools/HangboardPackages/tests/test_cli.py -k 'cord_render'
```

Expected: module and command are absent.

- [ ] **Step 6: Implement strict dataclasses/parser/validator.** Reuse `cord_render_assets` hashes and transparency inspection. Resolve current package declarations from `BoardInventory`; never import or mutate the historical remediation validator. Make error messages identify the exact record and first failed invariant.

- [ ] **Step 7: Add CLI and wrapper support.** Packet roots must be explicit, owner-named, non-symlink directories. `FINAL` rejects packet roots/transient files. `--package-id` is legal in packet/partial modes only and never weakens full root count reconciliation.

- [ ] **Step 8: Run all audit/package tests.**

```bash
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_cord_render_audit.py Tools/HangboardPackages/tests/test_cli.py
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
```

Expected: all pass.

- [ ] **Step 9: Run two fresh review gates, commit, and push.**

```bash
rtk git add Tools/HangboardPackages/src/hangboard_packages/cord_render_audit.py Tools/HangboardPackages/tests/test_cord_render_audit.py Tools/HangboardPackages/src/hangboard_packages/cli.py Tools/HangboardPackages/tests/test_cli.py scripts/hangboard-packages.sh
rtk git commit -m "Add tensioned cord render provenance audit"
rtk git push origin feature/hangboard-cord-tension
```

The spec reviewer checks every required field and lifecycle. The quality reviewer checks closed-schema behavior, count reconciliation, transient/final separation, hash verification, and historical-manifest immutability.

## Task 7: Add Exact DEBUG Presentation Routing and Owned Screenshot Capture

**Files:**
- Modify: `HangTen/Views/TrainView.swift`
- Modify: `HangTen/Views/BoardMapView.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Create: `Tools/HangboardPackages/src/hangboard_packages/cord_render_capture.py`
- Create: `Tools/HangboardPackages/tests/test_cord_render_capture.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `Tools/HangboardPackages/tests/test_cli.py`
- Modify: `scripts/hangboard-packages.sh`
- Modify: `docs/IOS_SIMULATOR_VALIDATION.md`

**Interfaces:**
- DEBUG environment: `HANGTEN_REVIEW_BOARD_DETAIL=1`, `HANGTEN_REVIEW_BOARD_ID`, `HANGTEN_REVIEW_PRESENTATION_ID`, and `HANGTEN_REVIEW_HOLD_ID`.
- `BoardDetailView(board:initialPresentationID:initialHoldID:)` and `BoardDetailMapView(..., initialPresentationID:)` select the exact presentation and real source-owned hold before first render.
- Release builds ignore all four values.
- CLI: `capture-cord-screenshots --audit docs/source-audits/2026-09-01-tensioned-hangboard-cords.json --package-id {literal-matrix-id} --simulator-uuid {owned-UUID} --app-path .context/joyful-donkey-cords-execution/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app --output-root .context/joyful-donkey-cords-{wave}-captures`; it writes screenshots plus `screenshot-index.json` under context and never edits tracked audit files.

- [ ] **Step 1: Write failing route tests.** Test a valid exact tuple, unknown board/presentation/hold, an alias using a hold owned by its canonical source, a hold from another surface, missing values, and release exclusion. Assert the resolved initial selection visibly highlights the requested hold.

- [ ] **Step 2: Write failing capture-runner tests with an injected subprocess runner.** Require an exact UUID, simulator name prefix `Hang Ten Paseo joyful-donkey `, existing app path, owner-named output root, accepted audit record, and one selected hold. Assert each launch uses the four `SIMCTL_CHILD_` values, terminates/launches only `com.hangten.training`, captures one PNG, hashes it, and writes one index record. Reject `booted`, a foreign UUID/name, duplicate path, and screenshot command failure.

- [ ] **Step 3: Run red gates.**

```bash
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator' -only-testing:HangTenTests/BoardPackageStoreTests
rtk uv run --with pytest python -m pytest -q Tools/HangboardPackages/tests/test_cord_render_capture.py Tools/HangboardPackages/tests/test_cli.py -k 'capture_cord'
```

Expected: route and command are absent.

- [ ] **Step 4: Implement the exact DEBUG route.** Resolve the tuple against `BoardCatalog.packageStore`; for an alias, allow only a hold whose `presentationID` equals the alias's `sourcePresentationID`. Initialize both selected presentation and selected hold without UI tapping. Do not change normal navigation or persisted selected-board state.

- [ ] **Step 5: Implement bounded capture.** The command verifies ownership from `xcrun simctl list devices`, launches one package at a time, waits only the documented short render interval, uses `xcrun simctl io {owned-UUID} screenshot`, validates PNG dimensions, and writes the untracked index. The controller invokes one wave/package per call so it can report progress inside 60 seconds.

- [ ] **Step 6: Document exact usage and cleanup.** Add the four environment variables to the DEBUG table and a cord-capture example with explicit UUID, Derived Data, app path, output path, and archive cleanup. State that a screenshot is valid only when the exact presentation is visible and one real hold is selected/highlighted.

- [ ] **Step 7: Run focused and complete gates.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$(rtk jq -r '.simulatorUUID' .context/joyful-donkey-cords-execution/OWNERSHIP.json)" -only-testing:HangTenTests/BoardPackageStoreTests
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_cord_render_capture.py Tools/HangboardPackages/tests/test_cli.py
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
```

Expected: all pass.

- [ ] **Step 8: Perform a fresh real-simulator smoke review.** Capture one canonical and one alias fixture on the exact owned simulator. Inspect both images and confirm board, presentation picker, selected-hold card, marker, and active path agree.

- [ ] **Step 9: Commit and push only this task.**

```bash
rtk git add HangTen/Views/TrainView.swift HangTen/Views/BoardMapView.swift HangTenTests/BoardPackageStoreTests.swift Tools/HangboardPackages/src/hangboard_packages/cord_render_capture.py Tools/HangboardPackages/tests/test_cord_render_capture.py Tools/HangboardPackages/src/hangboard_packages/cli.py Tools/HangboardPackages/tests/test_cli.py scripts/hangboard-packages.sh docs/IOS_SIMULATOR_VALIDATION.md
rtk git commit -m "Add exact hangboard presentation capture route"
rtk git push origin feature/hangboard-cord-tension
```

## Task 8: Seed the Exact 20/49/48 Audit Before Generation

**Files:**
- Create: `docs/source-audits/2026-09-01-tensioned-hangboard-cords.json`
- Create: `docs/source-audits/2026-09-01-tensioned-hangboard-cords.md`
- Create: `Tools/HangboardPackages/tests/test_cord_render_catalog_audit.py`

**Interfaces:**
- Produces: a complete initial-state ledger accepted by `AuditMode.INITIAL`, with every live presentation/asset represented before any tracked asset replacement.
- Port-A-Board option 4 begins as `blockedEvidence`; other not-yet-researched records begin `pendingEvidence`. These are explicit lifecycle states, not invented physical claims.

- [ ] **Step 1: Write the failing production audit test.** Assert the exact sorted package IDs/slugs in the matrix, 49 unique presentation keys, 48 asset keys, four Flash records, six Port-A records, and the one Port shared asset consumer pair. Assert Mammut is absent. Assert the historical paths/hashes match Global Constraints.

- [ ] **Step 2: Run the test and verify red.**

```bash
rtk uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardPackages/tests/test_cord_render_catalog_audit.py
```

Expected: the production audit file is absent.

- [ ] **Step 3: Author the machine ledger from live package declarations.** Use `apply_patch`; do not generate or infer mechanics from image pixels. Populate package/presentation identity, aliases, aspect ratios, asset consumers, gravity, and mechanical family only from the approved spec/live JSON. Leave evidence-dependent fields absent under their legal initial lifecycle state. Set Port option 4's exact block reason: current first-party evidence does not establish the named routing, and the shared raster path is not proof of physical equivalence.

- [ ] **Step 4: Author the companion narrative.** State that this lineage supersedes cord-only pixel preservation and the old off-white-background rule for this cohort; state that the 2026-08-30 manifest/narrative remain immutable historical records; explain the 20/49/48 count, Flash production obligation, Mammut exclusion, Port inclusion/blocker, bounded generation policy, and human-review requirements.

- [ ] **Step 5: Validate initial mode and historical immutability.**

```bash
rtk scripts/hangboard-packages.sh audit-cord-renders --root Hangboards --audit docs/source-audits/2026-09-01-tensioned-hangboard-cords.json --mode initial
rtk shasum -a 256 docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_cord_render_catalog_audit.py
```

Expected: initial audit and test pass; historical hashes are unchanged.

- [ ] **Step 6: Run two fresh review gates.** The spec reviewer reconciles every row with live JSON and the spec. The quality reviewer checks closed-schema formatting, lifecycle legality, deterministic ordering, no unsupported mechanics, and no historical diff.

- [ ] **Step 7: Commit and push only this task.**

```bash
rtk git add docs/source-audits/2026-09-01-tensioned-hangboard-cords.json docs/source-audits/2026-09-01-tensioned-hangboard-cords.md Tools/HangboardPackages/tests/test_cord_render_catalog_audit.py
rtk git commit -m "Seed tensioned cord render source audit"
rtk git push origin feature/hangboard-cord-tension
```

## Mandatory Product-Batch Protocol

Tasks 9–17 supply exact product assignments and tracked paths to this protocol. The controller executes one wave at a time. Within a wave, up to three product workers may run concurrently because they write disjoint owner directories. Product review begins after generation; one fresh integration agent then performs all shared writes serially.

- [ ] **P1 — Create and register each product workspace.** A fresh product worker creates the exact `.context/joyful-donkey-cords-{assigned-matrix-slug}-run-1/` path, writes `OWNERSHIP.json` with `apply_patch`, starts its exact cleanup guard, and records any image-generation handle before using it. It verifies `rtk git status --short` is unchanged.

- [ ] **P2 — Freeze the complete evidence set.** Search current official manufacturer pages/catalogues for the exact physical revision. Download every official manufacturer photograph for that revision into `sources/original/`, without browser or EXIF autorotation. Record direct URL, publisher, review date, revision applicability, role, original byte hash, decoded-pixel hash, dimensions, mode, and local owner path. Resolve revision conflicts before proceeding. Independent sources may corroborate depth/mechanics but never replace an official photo. Existing Hang Ten assets are non-authoritative composition references only and may use a reference slot only after all official pixels fit.

- [ ] **P3 — Build and verify referenced-image inputs.** Run the source-lock and atlas commands from Task 5. If the official set is five images or fewer and each file is accepted directly by image generation, pass all originals. Otherwise build up to five lossless atlas pages. Require a passing pixel-for-pixel panel round trip, then record the exact ordered source/atlas hashes. If all official sources cannot be supplied within five references without changing pixels, set `blockedEvidence` and stop that product.

```bash
rtk scripts/hangboard-packages.sh cord-assets lock --manifest .context/joyful-donkey-cords-aelith-cyclops-011-run-1/sources/index.json
rtk scripts/hangboard-packages.sh cord-assets atlas --manifest .context/joyful-donkey-cords-aelith-cyclops-011-run-1/sources/index.json --output-root .context/joyful-donkey-cords-aelith-cyclops-011-run-1/atlases
```

- [ ] **P4 — Manually author every presentation contract.** Write the fields in Ownership and Product Packet Contract from primary evidence. Trace every attachment, loaded segment, knot/bight/crossing, surface, and concavity claim to an exact source ID. Apply the presentation invariant explicitly: gravity canvas-down, board below overhead support, climber loading downward from below, all force-bearing branches taut upward, and no cord, tail, knot, or hardware below the board. Never derive topology from the current asset, presentation name, another product, or model intuition. A contract with unresolved attachment routing blocks generation for that presentation.

- [ ] **P5 — Generate exactly two whole-image candidates per unique PNG.** Use the built-in image generation tool in new-image mode. Every call's `referenced_image_paths` is the exact complete ordered official input set from P3. The prompt names the exact revision, usable surface, manually authored attachment routing, canvas-down gravity, board below overhead support, downward climber load from below, every force-bearing branch taut upward, no cord/tail/knot/hardware below the board, required aspect/composition, identity/relief constraints, flat chroma key, and forbidden topology/background. It explicitly requests a new complete board-and-cord render and forbids cord overlay or source-image editing. Save raw outputs and record full prompt, exposed model/tool version, time, ordered reference hashes, output hash, and dimensions.

- [ ] **P6 — Apply only deterministic chroma removal.** Run `cord-assets key` to a new RGBA path and `cord-assets inspect` on it. Do not change dimensions or any other pixels. If the product contains the default green, choose and record a flat alternative key before generation; never key away product material.

```bash
rtk scripts/hangboard-packages.sh cord-assets key --input .context/joyful-donkey-cords-aelith-cyclops-011-run-1/candidates/assets-primary-png/candidate-01-raw.png --output .context/joyful-donkey-cords-aelith-cyclops-011-run-1/candidates/assets-primary-png/candidate-01-rgba.png --config .context/joyful-donkey-cords-aelith-cyclops-011-run-1/chroma-config.json --report .context/joyful-donkey-cords-aelith-cyclops-011-run-1/candidates/assets-primary-png/candidate-01-report.json
rtk scripts/hangboard-packages.sh cord-assets inspect --image .context/joyful-donkey-cords-aelith-cyclops-011-run-1/candidates/assets-primary-png/candidate-01-rgba.png --expected-from Hangboards/aelith-cyclops-011/board.json:primary --config .context/joyful-donkey-cords-aelith-cyclops-011-run-1/chroma-config.json --report .context/joyful-donkey-cords-aelith-cyclops-011-run-1/candidates/assets-primary-png/candidate-01-inspection.json
```

- [ ] **P7 — Perform the owner review against all evidence.** For both candidates, record acceptance or a concrete rejection for exact revision, silhouette, material, contacts, holes, cord inventory, routing/crossing/knot, force direction/tension, relief, scale/position, background/alpha, and missing components. For a source/alias pair, compare equal body scale, normalized position, perspective, aspect ratio, and concavity. Aesthetics alone never accepts a candidate.

- [ ] **P8 — Permit at most one targeted third.** Only when both initial candidates are rejected, write one new prompt addressing their named failures and make one third call with the same complete official references. If it fails, mark the asset blocked and stop; do not issue another call.

- [ ] **P9 — Validate and seal the packet.** Populate `packet.json`, include all rejected and selected hashes, run packet-mode validation, and make the packet read-only for review. It must account for every presentation and unique asset assigned to that product.

```bash
rtk scripts/hangboard-packages.sh audit-cord-renders --root Hangboards --audit docs/source-audits/2026-09-01-tensioned-hangboard-cords.json --mode packet --package-id aelith.cyclops-011 --packet-root .context/joyful-donkey-cords-aelith-cyclops-011-run-1
```

- [ ] **P10 — Obtain an independent evidence/mechanics/visual decision.** A fresh reviewer opens every official input, contract, raw candidate, RGBA candidate, and report. It checks every rejection criterion in the spec and writes `reviews/independent.json`. The reviewer does not edit the candidate. A rejection returns to a new product worker only if the bounded candidate budget remains; otherwise it blocks.

- [ ] **P11 — Promote accepted bytes through one integration agent.** After all wave reviewers finish, dispatch one fresh integration agent. It verifies packet and selected hashes, checks a clean HEAD, mechanically copies only selected RGBA bytes into the exact declared asset paths, and verifies destination hashes. Promote all members of each source/alias pair together. The agent uses `apply_patch` for `board.json` and audit text/JSON changes.

- [ ] **P12 — Manually review canonical geometry and aliases.** In Workbench, inspect normal, all-active, each hold/piece, selected highlight, marker/selection target, and hit test for every presentation. Deliberately redraw canonical paths when the accepted composition requires it; mirror only verified symmetry and choose a constraint only from operator-reviewed evidence. For an alias whose body pivot is not canvas center, manually choose one `geometryRotationAnchor`; never fit it from pixels. If one anchor cannot align every contact, reject/regenerate the pair.

- [ ] **P13 — Run package/app gates and capture every wave presentation.** Run package validation/status, focused audit partial mode, relevant Python/Workbench tests, source-boundary verification, a signed Debug build to the exact owned simulator, and the capture command from Task 7. Copy each reviewer-approved capture to its exact tracked `docs/pr-screenshots/2026-09-01-tensioned-hangboard-cords/{slug}/` path and verify the copied hash.

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk env SRCROOT=/Users/asherlc/.paseo/worktrees/0h78jp9r/joyful-donkey scripts/verify-board-source-boundary-manifest.sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=$(rtk jq -r '.simulatorUUID' .context/joyful-donkey-cords-execution/OWNERSHIP.json)" -derivedDataPath .context/joyful-donkey-cords-execution/DerivedData build
rtk scripts/hangboard-packages.sh capture-cord-screenshots --audit docs/source-audits/2026-09-01-tensioned-hangboard-cords.json --package-id aelith.cyclops-011 --simulator-uuid "$(rtk jq -r '.simulatorUUID' .context/joyful-donkey-cords-execution/OWNERSHIP.json)" --app-path .context/joyful-donkey-cords-execution/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app --output-root .context/joyful-donkey-cords-wave-o1-captures
```

- [ ] **P14 — Review actual app screenshots and finalize wave audit records.** A fresh visual reviewer opens every capture, confirms the exact named presentation, transparent render, correct gravity/mechanics/relief, one real selected highlighted hold, marker, and path alignment, and records the decision. The integration agent then updates screenshot paths/hashes and changes only fully accepted records to `accepted`. Run partial audit again.

- [ ] **P15 — Commit, push, and clean exact owned resources.** The integration agent verifies the diff contains only that wave's declared packages, audit files, and screenshots; commits and pushes. After the remote contains the commit and every provenance hash is tracked, each product owner shuts down/deletes recorded external handles and removes only its exact packet directory. Verify each exact resource/path is absent; retain a blocked packet only while its evidence escalation is active and registered.

## Task 9: Generate and Integrate Overhead Wave O1

**Files:**
- Replace: `Hangboards/aelith-cyclops-011/assets/primary.png`
- Replace: `Hangboards/captain-fingerfood-dual/assets/primary.png`, `assets/reverse.png`
- Replace: `Hangboards/captain-fingerfood-pocket/assets/primary.png`
- Modify only if manual geometry review requires it: the three corresponding `board.json` files
- Modify: the new cord audit JSON/narrative
- Create: four screenshots under the matching three dated screenshot subdirectories

**Interfaces:** Four presentations and four unique PNGs; eight mandatory initial candidate records and at most four targeted-third records.

- [ ] **Step 1: Dispatch exactly three fresh product workers.** Assign Aelith, Captain Dual, and Captain Pocket one per worker. Execute P1–P9 for each, including complete official photo inputs on every call.
- [ ] **Step 2: Dispatch fresh independent reviewers.** Execute P10 separately for all three packets. Pocket relief must remain concave; neither Captain face may borrow routing from the other without exact evidence.
- [ ] **Step 3: Dispatch one serial integration agent.** Execute P11–P14 for these exact packages and four presentations. The geometry operator reviews all canonical holds manually.
- [ ] **Step 4: Run the wave audit.**

```bash
rtk scripts/hangboard-packages.sh audit-cord-renders --root Hangboards --audit docs/source-audits/2026-09-01-tensioned-hangboard-cords.json --mode partial --package-id aelith.cyclops-011 --package-id captain-fingerfood.dual --package-id captain-fingerfood.pocket
```

Expected: these four records are accepted with four screenshots; every other record remains explicitly pending or blocked.

- [ ] **Step 5: Commit, push, and clean via P15.** Use commit message `Render tensioned cords for overhead wave O1`.

## Task 10: Generate and Integrate Overhead Wave O2

**Files:**
- Replace: `Hangboards/captain-fingerfood-unlevel/assets/primary.png`, `assets/reverse.png`
- Replace: all four PNGs in `Hangboards/crimptonite-helium-mobile/assets/`
- Replace: `Hangboards/metolius-light-rail-2/assets/primary.png`, `assets/15mm-surface.png`
- Modify as manually required: those three `board.json` files
- Modify: cord audit JSON/narrative
- Create: eight corresponding highlighted screenshots

**Interfaces:** Eight presentations/assets; 16 mandatory initial candidate records, at most eight targeted thirds. Crimptonite has atomic pairs `primary`/`front-inverted` and `reverse`/`reverse-inverted`.

- [ ] **Step 1: Dispatch three fresh product workers.** Assign Unlevel, Crimptonite, and Light Rail. Execute P1–P9. Existing transparent Light Rail images remain non-authoritative references and do not waive whole-image regeneration.
- [ ] **Step 2: Dispatch fresh reviewers.** Execute P10. Crimptonite reviewers require same body scale/position and concavity across each alias pair and reject bottom wrapping unsupported by first-party evidence.
- [ ] **Step 3: Dispatch one serial integration/geometry agent.** Execute P11–P14. Add a non-center anchor only if manual full-contact review demonstrates it is necessary.
- [ ] **Step 4: Run partial audit for the three exact package IDs.** Expected: eight new accepted records and eight tracked screenshots.
- [ ] **Step 5: Commit, push, and clean via P15.** Use commit message `Render tensioned cords for overhead wave O2`.

## Task 11: Generate and Integrate Overhead Wave O3

**Files:**
- Replace: `Hangboards/nature-stone-hanger-mini/assets/primary.png`, `assets/side.png`
- Replace: `Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.png`
- Replace: `Hangboards/yy-baguette/assets/primary.png`, `assets/reverse.png`
- Modify as manually required: those three `board.json` files
- Modify: cord audit JSON/narrative
- Create: five corresponding highlighted screenshots

**Interfaces:** Five presentations/assets; ten mandatory initial candidate records, at most five targeted thirds.

- [ ] **Step 1: Dispatch three fresh product workers.** Assign Nature Mini, Karma8a, and YY Baguette. Execute P1–P9; the Karma8a worker resolves the exact collaboration revision instead of blending it with the standard Mini.
- [ ] **Step 2: Dispatch fresh reviewers and one serial integrator.** Execute P10–P14. Review stone/wood identity and surface-specific recess depth, not merely cord plausibility.
- [ ] **Step 3: Run partial audit for `nature.stone-hanger-mini`, `nature.stone-hanger-mini-karma8a`, and `yy.baguette`.** Expected: five new accepted records/screenshots.
- [ ] **Step 4: Commit, push, and clean via P15.** Use commit message `Render tensioned cords for overhead wave O3`.

## Task 12: Generate and Integrate Overhead Wave O4

**Files:**
- Replace: all five declared PNGs in `Hangboards/yy-baguette-evo/assets/`
- Replace: `Hangboards/yy-travelboard/assets/primary.png`, `assets/reverse.png`
- Replace: `Hangboards/tension-flash-board/assets/primary.png`, `assets/three-edge-inverted.png`, `assets/two-edge-surface.png`, `assets/two-edge-inverted.png`
- Modify as manually required: those three `board.json` files
- Modify: cord audit JSON/narrative
- Create: 11 corresponding highlighted screenshots

**Interfaces:** Eleven presentations/assets; 22 mandatory initial candidate records, at most 11 targeted thirds. Flash has atomic three-edge and two-edge source/alias pairs.

- [ ] **Step 1: Dispatch three fresh workers.** Assign Baguette Evo, TravelBoard, and Flash. Execute P1–P9. The Baguette worker authors five distinct surface contracts; TravelBoard does not preserve current slack merely because it exists in the catalog.
- [ ] **Step 2: Reconcile the Flash pilot without weakening provenance.** The Flash worker may reuse a pilot candidate only if raw/keyed hashes, exactly two initial dispositions, full prompt, complete official referenced-image inputs, atlas proof, chroma-only processing, and cleanup ownership are all recoverable and pass packet validation. Otherwise regenerate that asset within the normal two-plus-one budget. Complete both two-edge views regardless.
- [ ] **Step 3: Dispatch fresh reviewers and one serial integrator.** Execute P10–P14. Flash reviewers explicitly reject convex-looking recesses and cords wrapped under the body without exact evidence.
- [ ] **Step 4: Run partial audit for `yy.baguette-evo`, `yy.travelboard`, and `tension.flash-board`.** Expected: 11 accepted records/screenshots and all four Flash views accounted for.
- [ ] **Step 5: Commit, push, and clean via P15.** Use commit message `Complete overhead cord render cohort`.

## Task 13: Resolve and Integrate the Frictitious NUG Modes

**Files:**
- Replace: `Hangboards/frictitious-nug/assets/primary.png`, `assets/reverse.png`
- Modify if manually required: `Hangboards/frictitious-nug/board.json`
- Modify: cord audit JSON/narrative
- Create: two corresponding highlighted screenshots

**Interfaces:** Two presentations/assets; four mandatory initial candidates, at most two targeted thirds. Mechanical family is selected from evidence per presentation, never defaulted catalog-wide.

- [ ] **Step 1: Dispatch one fresh evidence/product worker.** Before a generation call, establish each exact presentation's manufacturer-supported attachment topology while applying the shared straps-up composition: board below overhead support, downward climber load from below, and all force-bearing branches upward. If first-party evidence cannot establish the attachment routing, mark that presentation `blockedEvidence` and issue no call.
- [ ] **Step 2: For evidence-complete presentations, execute P1–P9 and obtain a fresh P10 review.** The reviewer checks force direction independently for `primary` and `reverse`.
- [ ] **Step 3: Dispatch one serial integration agent for P11–P14.** Do not promote one face as a substitute for an unresolved other face.
- [ ] **Step 4: Run partial audit for `frictitious.nug`.** Expected: two accepted records or an explicit evidence block that prevents final completion; no inferred routing.
- [ ] **Step 5: Commit accepted/audited work, push, and clean via P15.** Use commit message `Render evidence-selected NUG cord modes` only when both records are accepted; otherwise use `Record NUG cord evidence blocker` and report the blocker to the user before final acceptance.

## Task 14: Generate and Integrate Straps-Up Lifting-Edge Wave L

**Files:**
- Replace: `Hangboards/lattice-mxedge-lift-large/assets/primary.png`, `assets/large-medium.png`, `assets/mono.png`
- Replace: `Hangboards/lattice-mxedge-lift-small/assets/primary.png`, `assets/large-medium.png`, `assets/mono.png`
- Replace: `Hangboards/plateau-lifting-edge/assets/primary.png`
- Modify as manually required: those three `board.json` files
- Modify: cord audit JSON/narrative
- Create: seven corresponding highlighted screenshots

**Interfaces:** Seven presentations/assets; 14 mandatory initial candidates, at most seven targeted thirds. Every board is below overhead support while the climber loads downward from below; all force-bearing cord/strap branches point canvas up.

- [ ] **Step 1: Dispatch exactly three fresh product workers.** Assign MXEdge Large, MXEdge Small, and Plateau. Execute P1–P9. Large and small revisions remain separate evidence sets.
- [ ] **Step 2: Dispatch fresh reviewers.** Execute P10. Reject any force-bearing branch that points downward, any cord/tail/knot/hardware below the board, any unsupported generic bridle, or any missing evidence-backed attachment branch.
- [ ] **Step 3: Dispatch one serial integration/geometry agent for P11–P14.** Manually review the geometry of every named edge/mono position.
- [ ] **Step 4: Run partial audit for the three straps-up lifting-edge package IDs.** Expected: seven accepted records/screenshots.
- [ ] **Step 5: Commit, push, and clean via P15.** Use commit message `Render straps-up lifting-edge cords`.

## Task 15: Generate and Integrate Exterior-Sling Wave S

**Files:**
- Replace: all four declared PNGs in `Hangboards/lattice-mini-bar/assets/`
- Modify if manually required: `Hangboards/lattice-mini-bar/board.json`
- Modify: cord audit JSON/narrative
- Create: four corresponding highlighted screenshots

**Interfaces:** Four presentations/assets; eight mandatory initial candidates, at most four targeted thirds. Documented exterior-body sling contact is required product mechanics, but every force-bearing return branch leaves upward and nothing hangs below the board.

- [ ] **Step 1: Dispatch one fresh Mini Bar worker for P1–P9.** Author a separate load/relief contract for `edge-10`, `edge-20`, `ergonomic-jug`, and `mini-pinch` from exact official evidence.
- [ ] **Step 2: Dispatch a fresh specialist reviewer.** Execute P10 and explicitly retain evidence-backed exterior body slings while rejecting unsupported knot/hole changes.
- [ ] **Step 3: Dispatch one serial integration/geometry agent for P11–P14.** Preserve the evidence-backed exterior-body sling contact while enforcing the same no-cord/tail/knot/hardware-below-board invariant as every other package.
- [ ] **Step 4: Run partial audit for `lattice.mini-bar`.** Expected: four accepted records/screenshots.
- [ ] **Step 5: Commit, push, and clean via P15.** Use commit message `Render Mini Bar exterior cord slings`.

## Task 16: Generate and Integrate Independent-Unit Wave I

**Files:**
- Replace: `Hangboards/metolius-rock-rings-3d/assets/primary.png`
- Replace: `Hangboards/yy-penta-evo/assets/primary.png`
- Modify if manually required: both `board.json` files
- Modify: cord audit JSON/narrative
- Create: two corresponding highlighted screenshots

**Interfaces:** Two presentations/assets; four mandatory initial candidates, at most two targeted thirds. Each rendered unit has its own complete documented suspension.

- [ ] **Step 1: Dispatch two fresh product workers.** Assign Rock Rings and Penta separately and execute P1–P9.
- [ ] **Step 2: Dispatch fresh reviewers.** Execute P10. Reject a shared unsupported bridge, one unit hanging from the other, a missing strand, or a mixed-revision pair.
- [ ] **Step 3: Dispatch one serial integration/geometry agent for P11–P14.** Review each unit's holds/pieces and both suspensions in the actual app.
- [ ] **Step 4: Run partial audit for `metolius.rock-rings-3d` and `yy.penta-evo`.** Expected: two accepted records/screenshots.
- [ ] **Step 5: Commit, push, and clean via P15.** Use commit message `Render independent hangboard suspensions`.

## Task 17: Resolve and Integrate Optional Port-A-Board Wave P

**Files:**
- Replace only after evidence resolution: `Hangboards/frictitious-port-a-board/assets/primary.png`, `assets/front-inverted.png`, `assets/back.png`, `assets/back-inverted.png`, `assets/side.png`
- Modify if manually required: `Hangboards/frictitious-port-a-board/board.json`
- Modify: cord audit JSON/narrative
- Create only after all records resolve: six corresponding highlighted screenshots

**Interfaces:** Six presentation records, five unique PNGs, ten mandatory initial candidate records, at most five targeted thirds. `front-inverted` and `cord-option-4-20mm-incut` both consume `assets/front-inverted.png`.

- [ ] **Step 1: Dispatch one fresh evidence-only worker first.** Freeze all exact-revision official evidence and determine the named option-4 routing. The presentation name, shared current asset, another Port-A configuration, or model intuition is not evidence.
- [ ] **Step 2: Enforce the shared-path decision gate.** If first-party evidence proves `front-inverted` and option 4 can truthfully share one complete render, document both contracts and continue. If it proves different visible topology, stop and request a separately approved scope/count change; do not silently split the asset and invalidate 48. If evidence remains absent, preserve `blockedEvidence`, make no option-4 call, and report that final cohort acceptance is blocked.
- [ ] **Step 3: After successful resolution, execute P1–P10.** Generate five unique assets with every official photo supplied to every call. Review the `primary`/`front-inverted`/option-4 group and `back`/`back-inverted` pair atomically; `side` remains its own presentation.
- [ ] **Step 4: Dispatch one serial integration/geometry agent for P11–P14.** Preserve portable cord mode; do not add a cord to a wall-mounted scene. Require one screenshot for each of the six records even though two records share one PNG.
- [ ] **Step 5: Run partial audit for `frictitious.port-a-board`.** Expected after evidence resolution: six accepted records, five asset records, six screenshot hashes. Before resolution: exact blocker remains and final mode fails by design.
- [ ] **Step 6: Commit, push, and clean via P15.** Use commit message `Render portable Port-A-Board cord options` only after all six records pass. A blocker-only audit commit uses `Record Port-A-Board option routing blocker` and is not feature completion.

## Task 18: Complete the 49-Screenshot, 48-Asset Final Audit and Cleanup

**Files:**
- Modify final state only: `docs/source-audits/2026-09-01-tensioned-hangboard-cords.json`
- Modify final results only: `docs/source-audits/2026-09-01-tensioned-hangboard-cords.md`
- Verify: all scoped `Hangboards/{literal-matrix-slug}/board.json` files and 48 declared assets
- Verify: all 49 dated screenshots
- Verify byte-for-byte unchanged: both 2026-08-30 historical audit files

**Interfaces:** Produces a final-mode report with exactly 20 packages, 49 accepted presentation records, 48 accepted asset records, and 49 unique accepted screenshot records; produces no live `.context` or external resources owned by this execution.

- [ ] **Step 1: Stop if any evidence or candidate blocker remains.** Final mode is not a mechanism for waiving NUG, Port option 4, a third-candidate failure, missing official inputs, alias drift, geometry mismatch, or screenshot failure. Report the exact record and request the necessary evidence/product decision.

- [ ] **Step 2: Dispatch a fresh final audit agent.** Recompute live presentation/asset keys from all 20 package JSON files. Recompute every promoted asset and screenshot hash. Re-run focused transparency inspection on all 48 assets. Assert every call supplied all official source/atlas hashes and declared only chroma removal.

- [ ] **Step 3: Re-review all geometry and screenshots, not a montage surrogate.** A fresh visual reviewer opens each of the 49 individual app screenshots and cross-checks its audit record, accepted asset, and selected hold. A second geometry reviewer inspects each canonical path/piece and each alias in Workbench and app for path/highlight/marker/hit-test agreement, same-scale source/alias bodies, and preserved concavity.

- [ ] **Step 4: Run the final machine audit and count queries.**

```bash
rtk scripts/hangboard-packages.sh audit-cord-renders --root Hangboards --audit docs/source-audits/2026-09-01-tensioned-hangboard-cords.json --mode final
rtk jq '[.presentationRecords | length, .assetRecords | length, ([.presentationRecords[].screenshot.path] | unique | length)]' docs/source-audits/2026-09-01-tensioned-hangboard-cords.json
rtk shasum -a 256 docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
```

Expected: final audit exits zero; counts print `[49,48,49]`; historical hashes equal Global Constraints.

- [ ] **Step 5: Run every repository gate.**

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
rtk npm --prefix Tools/HangboardWorkbench test
rtk npm --prefix Tools/HangboardWorkbench run check:bundle
rtk env SRCROOT=/Users/asherlc/.paseo/worktrees/0h78jp9r/joyful-donkey scripts/verify-board-source-boundary-manifest.sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$(rtk jq -r '.simulatorUUID' .context/joyful-donkey-cords-execution/OWNERSHIP.json)" -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardPackageWriterTests -only-testing:HangTenTests/BoardSourceBoundaryTests
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
```

Expected: every command passes. A generic package pass does not override a visual/evidence failure.

- [ ] **Step 6: Verify package/source boundaries and change scope.** Assert each scoped package contains only `board.json` and declared assets; no sources, atlases, prompts, raw candidates, review notes, or screenshots are under `Hangboards/`. Run `rtk git diff --check` and inspect `rtk git status --short` plus `rtk git diff --name-status origin/main...HEAD`. Investigate every path outside the files named in this plan.

- [ ] **Step 7: Update only final audit results.** With `apply_patch`, record final command results, reviewer identities/times, completion state, and cleanup status in the new audit/narrative. Do not change sourced product contracts during this reporting step.

- [ ] **Step 8: Obtain two final fresh reviews.** The spec-compliance reviewer maps every acceptance criterion to a passing record/gate. The quality reviewer checks implementation, tests, audit determinism, all 49 images, all 49 screenshots, and historical immutability. Corrections go to a new implementation agent and repeat final gates.

- [ ] **Step 9: Commit and push the final report.**

```bash
rtk git add docs/source-audits/2026-09-01-tensioned-hangboard-cords.json docs/source-audits/2026-09-01-tensioned-hangboard-cords.md
rtk git commit -m "Certify tensioned hangboard cord renders"
rtk git push origin feature/hangboard-cord-tension
rtk git status --short --branch
```

Expected: remote push succeeds and tracked worktree is clean.

- [ ] **Step 10: Clean exact owned resources and verify deletion.** Archive the exact recorded simulator UUID, delete only external image jobs that expose a deletable owned handle, then remove execution-owned source caches, atlases, rejected/raw candidates, keyed intermediates, Derived Data, and temporary captures. Do not remove a pre-existing directory unless its ownership was positively established and its necessary artifacts were promoted/audited.

```bash
rtk env PASEO_WORKTREE_PATH=/Users/asherlc/.paseo/worktrees/0h78jp9r/joyful-donkey scripts/paseo-resource-cleanup.sh archive
rtk xcrun simctl list devices
rtk git status --short --branch
```

Expected: each exact owned UUID/handle/path is absent, ownership manifests contain no unresolved resource, shared resources remain, and the branch remains clean and pushed.

## Completion Handoff

Report the remote branch and final commit, the exact `20/49/48/49` counts, all passing gate families, any anchors introduced and why, the immutable historical hashes, and verified resource cleanup. Link the new audit narrative and screenshot root. Do not call the feature complete while any presentation is blocked or any required screenshot is missing.
