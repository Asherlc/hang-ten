# Mini Bar Rope Contact Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether Bullet can settle the Mini Bar's exterior cord loops against the actual USDZ mesh in all four grip poses without authored contact coordinates.

**Architecture:** An offline Python adapter verifies and exports the hash-bound board triangles and suspension inputs. A small C++ Bullet executable simulates two rope chains against the rigid board for each pose, then a Python evaluator measures contact and renders review views. The experiment leaves the app, CAD, USDZ, descriptor, and suspension sidecar unchanged.

**Tech Stack:** Python 3, `numpy`, `usd-core==26.8`, `pytest`, `matplotlib`, Bullet tag `3.25` C++, `nlohmann/json` tag `v3.12.0`, CMake, macOS command-line tools.

**Spec:** [Mini Bar rope contact prototype design](../specs/2026-09-27-mini-bar-rope-contact-prototype-design.md)

## Global Constraints

- Use `Hangboards/lattice-mini-bar/assets/primary.usdz` only after its SHA-256 matches `primary.model.json` and the `suspension.json` hash.
- Use body triangles and importer transforms; no image-derived geometry, CAD edits, baked cord, or per-pose route points.
- Keep source for the reproducible experiment in `Tools/HangboardRopePrototype/`; keep dependencies, builds, logs, and images in `.context/frantic-kiwi/`.
- The outside wrap side and two strand locations define topology; simulation derives every intermediate contact point.
- Test the existing 0.75 m per-loop display estimate and a separately labeled derived taut length. Record radius, collision margin, damping, friction, solver steps, and iterations.
- Acceptance for each of four poses: underside tube-to-board gap at expected contact samples at most 1 mm, penetration at most 0.5 mm, correct exterior topology, separate loops, shared pull point, and repeatable fresh runs.
- No iOS deployment-target change or RealityKit runtime integration in this prototype.

## Review Focus

1. A stale USDZ or sidecar hash must stop before simulation. Task 1 tests both mismatches.
2. Imported transform or unit errors must not produce a plausible-looking, wrong-sized collider. Task 1 tests bounds against the descriptor.
3. A seed that crosses the board or swaps the exterior side must fail topology validation. Task 2 tests a synthetic obstacle and Task 3 tests all Mini Bar poses.
4. A 0.75 m slack loop must not be reported as taut contact. Task 3 tests both length conditions independently.
5. A render that hides penetration, unstable settling, or inter-loop overlap must fail numerical review. Task 4 tests distances and repeatability before producing the report.

---

### Task 1: Export a validated Mini Bar case

**Files:**
- Create: `Tools/HangboardRopePrototype/case.py`
- Create: `Tools/HangboardRopePrototype/tests/test_case.py`
- Create: `Tools/HangboardRopePrototype/requirements.txt`

**Interfaces:**
- Produces: `load_case(package: Path) -> RopeCase`; `RopeCase` contains body vertices and triangular faces in model metres, four pose quaternions/translations, shared anchor, two loop guide pairs, cord radius, and the original per-loop rest length.
- Produces: `write_case(case: RopeCase, path: Path) -> None`, a versioned JSON fixture for the C++ solver.

- [ ] **Step 1: Write failing tests** for exact descriptor/sidecar hash matching, missing body node, nontriangle/nonfinite geometry, importer transform and descriptor bounds matching, anchor computed as bounds midpoint X/Z plus offset and maximum Y plus offset, and all four pose IDs.
- [ ] **Step 2: Run** `python3 -m pytest Tools/HangboardRopePrototype/tests/test_case.py -q`; expect failures from missing API.
- [ ] **Step 3: Implement** `load_case` using USD `UsdGeom.XformCache`, the descriptor body node ID, and the same anchor calculation as `BoardPackageStore.swift:2101`. Extract triangle indices and transform positions; exclude selectable contact meshes. Implement `write_case` with stable ordering and source hashes. Pin `numpy`, `usd-core==26.8`, and `pytest` in the prototype requirements; create the virtual environment under `.context/frantic-kiwi/`.
- [ ] **Step 4: Run** the focused test and `python3 Tools/HangboardRopePrototype/case.py Hangboards/lattice-mini-bar .context/frantic-kiwi/rope-case.json`; expect a matching SHA-256, nonempty triangles, and four poses.
- [ ] **Step 5: Commit** the exporter, requirements, and tests.

### Task 2: Establish Bullet rope contact on a synthetic obstacle

**Files:**
- Create: `Tools/HangboardRopePrototype/CMakeLists.txt`
- Create: `Tools/HangboardRopePrototype/rope_solver.cpp`
- Create: `Tools/HangboardRopePrototype/tests/test_solver.py`

**Interfaces:**
- Consumes: Task 1's versioned JSON schema.
- Produces: `rope_solver --case <json> --pose <id> --length-mode original|taut --output <json>`; output includes ordered centerline samples for both loops, step/iteration counts, convergence residual, collision settings, and status.

- [ ] **Step 1: Write a failing integration test** with a triangulated round-ended synthetic bar: each rope begins in its declared exterior winding, stays outside the mesh, wraps under it, and ends at the shared anchor. Add a deliberately crossed seed that must return a topology failure.
- [ ] **Step 2: Run** `python3 -m pytest Tools/HangboardRopePrototype/tests/test_solver.py -q`; expect failure because the executable does not exist.
- [ ] **Step 3: Build Bullet tag `3.25` in `.context/frantic-kiwi/bullet3-3.25`**, record its resolved commit and license in the result log, and use only `BulletSoftBody`, `BulletDynamics`, `BulletCollision`, and `LinearMath`. Fetch `nlohmann/json` tag `v3.12.0` beneath the same workspace-owned directory for the versioned fixture and result format. CMake builds a local command-line executable without app linkage.
- [ ] **Step 4: Implement** the CLI: parse and validate the case, construct a rigid triangle-mesh collider, place it with the selected pose, construct each rope as an ordered Bullet soft-body chain pinned at both ends to the anchor, seed it around the declared exterior side using the guide pair, and step at a fixed time step until stable or a fixed iteration cap. Keep collision margins explicit and output the settled centerlines. Reject invalid topology and nonconvergence.
- [ ] **Step 5: Run** the synthetic integration test twice from fresh states; expect the same accepted topology and bounded position difference. Commit solver, CMake file, and test.

### Task 3: Run all Mini Bar poses and both length conditions

**Files:**
- Create: `Tools/HangboardRopePrototype/run_case.py`
- Create: `Tools/HangboardRopePrototype/tests/test_run_case.py`

**Interfaces:**
- Consumes: Task 1 fixture and Task 2 CLI.
- Produces: `.context/frantic-kiwi/rope-results/<pose>/<length-mode>.json` plus a manifest of source hashes, Bullet revision, display parameters, and pass/fail reason.

- [ ] **Step 1: Write a failing test** asserting exactly eight independent runs (four named poses times `original` and `taut`), fresh simulation state for each, complete provenance, and an explicit failure when a long rope settles slack without expected contact.
- [ ] **Step 2: Run** `python3 -m pytest Tools/HangboardRopePrototype/tests/test_run_case.py -q`; expect failure from missing runner.
- [ ] **Step 3: Implement** `run_case.py` to invoke the solver separately for each condition. Use the collision-free exterior seed at cord-radius offset to derive its full anchor-to-anchor length as the taut display estimate, record it beside the unchanged 0.75 m estimate, and never write the derived value to package metadata. Preserve failed solver output and reason for diagnosis.
- [ ] **Step 4: Run** the focused test and all eight real Mini Bar cases; expect complete result files or an explicit solver limitation, never a silently omitted pose. Commit the runner and test.

### Task 4: Measure, render, and decide

**Files:**
- Create: `Tools/HangboardRopePrototype/evaluate.py`
- Create: `Tools/HangboardRopePrototype/tests/test_evaluate.py`
- Create: `Tools/HangboardRopePrototype/README.md`

**Interfaces:**
- Consumes: Task 1 body triangles and Task 3 centerlines.
- Produces: `.context/frantic-kiwi/rope-results/report.json`, a concise Markdown findings report, and front/oblique/end-on PNGs for every pose and length condition.

- [ ] **Step 1: Write failing geometry tests** for a tube tangent to a known triangle, a 0.5 mm allowed penetration versus a 0.6 mm rejected penetration, a greater-than-1 mm gap, two overlapping loops, and repeat runs with divergent positions.
- [ ] **Step 2: Run** `python3 -m pytest Tools/HangboardRopePrototype/tests/test_evaluate.py -q`; expect failure from missing evaluator.
- [ ] **Step 3: Implement** segment-to-triangle distance and inside/outside classification against the exact body triangles, subtracting cord radius for surface gap; measure the underside contact region, inter-loop clearance, topology, convergence, and repeatability. Render the same board triangles with the transient tube centerlines in three camera views using Matplotlib. Mark each condition pass/fail, including slack and nonconvergence.
- [ ] **Step 4: Run** all prototype tests and the real-case evaluator. Review every generated side view and record whether the four-pose acceptance criteria hold. If Bullet fails, report the measured reason and keep product code unchanged; do not tune pose-specific routes or relax acceptance thresholds.
- [ ] **Step 5: Document** setup, exact run commands, source hashes, Bullet revision, parameters, timing, and findings in `README.md` and the workspace-owned report. Commit the evaluator, tests, and README; push commits to the branch. Clean exact owned external processes/resources and verify the worktree is clean.
