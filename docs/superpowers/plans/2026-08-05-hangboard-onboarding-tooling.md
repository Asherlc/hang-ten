# Hangboard Onboarding Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the proven staged hangboard-onboarding pipeline and accepted Metolius parity fixture to Hang Ten as repository-local developer tooling.

**Architecture:** Vendor the standalone Python package under `Tools/HangboardOnboarding`, keep generated working runs under ignored `.context/`, and expose its commands through one repository wrapper. The Swift app consumes only manually audited normalized geometry, so the pipeline cannot introduce a raster/highlight drift at runtime.

**Tech Stack:** Python 3.11+, Pillow, NumPy, OpenCV, pytest, Bash, SwiftUI documentation.

## Global Constraints

- Do not change runtime Swift behavior or Xcode target membership.
- Preserve the 19 accepted Metolius logical grip regions and replay hashes.
- Model responses provide compact semantics only; deterministic local processing owns pixel and vector geometry.
- Generated environments, caches, and onboarding runs live under `.context/`.

---

### Task 1: Vendor the tested onboarding package

**Files:**
- Create: `Tools/HangboardOnboarding/README.md`
- Create: `Tools/HangboardOnboarding/pyproject.toml`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/**`
- Create: `Tools/HangboardOnboarding/tests/**`
- Create: `Tools/HangboardOnboarding/docs/**`
- Create: `Tools/HangboardOnboarding/reference/metolius-compact-ii/**`

**Interfaces:**
- Produces: `hangboard-onboard`, `hangboard-semantic-benchmark`, and `hangboard-to-svg` console scripts.

- [x] Copy the tracked package, self-contained tests, and operator documentation from the proven vectorizer commit; omit legacy tests coupled to mutable external work directories.
- [x] Copy the accepted Metolius run byte-for-byte as the cache-only parity fixture.
- [x] Record source commit and fixture purpose in `UPSTREAM.md`.
- [x] Run the focused Metolius semantic benchmark and require exact parity with zero model calls.

### Task 2: Add a repository-local command wrapper

**Files:**
- Create: `scripts/hangboard-tools.sh`

**Interfaces:**
- Consumes: the vendored `pyproject.toml` and its three console scripts.
- Produces: `scripts/hangboard-tools.sh <onboard|benchmark|convert> [arguments...]`.

- [x] Add strict shell argument validation and Python 3.11 detection.
- [x] Bootstrap an editable install in `.context/hangboard-onboarding-venv` when absent.
- [x] Dispatch the requested tool without changing the caller's working directory.
- [x] Verify `scripts/hangboard-tools.sh onboard --help` succeeds.

### Task 3: Connect the tooling to Hang Ten's board workflow

**Files:**
- Modify: `README.md`
- Modify: `docs/ADDING_A_BOARD.md`

**Interfaces:**
- Consumes: staged review images, Stage 3 normalized vector regions, and the Stage 4 selectable artifact.
- Produces: an explicit translation workflow into `TrainingBoard` metadata and `BoardDesign` geometry.

- [x] Document installation-free wrapper commands and the accepted replay check.
- [x] Document which image is reviewed at each stage and where work products belong.
- [x] Reaffirm that generated artwork is calibration evidence and that one Swift path drives rendering, highlighting, and interaction.
- [x] Run the self-contained vendored Python suite, exact accepted-run benchmark, and the existing Hang Ten simulator build.
