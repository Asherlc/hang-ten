# CI runner audit

Audited all 17 jobs with an assigned runner in `.github/workflows` on
2026-10-05. Eleven use Ubuntu; six require an Apple toolchain. Counts exclude
matrix expansion and the two call sites for the reusable runtime workflow.

| Workflow / job | Runner | Requirement |
| --- | --- | --- |
| CI / changes | Ubuntu | Git diff and path classification |
| CI / metadata | macOS | `xcodebuild -showBuildSettings` resolves Debug and Release settings; `sips` checks icons |
| CI / board-assets | Reusable Ubuntu pipeline | Calls `runtime-assets.yml`; counted through its two runner jobs below |
| CI / python | Ubuntu | Package validation, staging, source contracts and pytest |
| CI / transgression-native | Ubuntu 24.04 | Native FreeCAD and OpenUSD; no Apple SDK required |
| CI / workflow-lint | Ubuntu | actionlint |
| CI / build-required | Ubuntu | Required-check aggregation |
| CI / build-release-device | macOS | `xcodebuild` with the iPhoneOS SDK |
| CI / test-unit | macOS | XCTest on iOS Simulator |
| CI / test-ui-paywall | macOS | Two UI shards: custom planner; purchase, settings and workouts |
| CI / test-ui-map | Apple runner (`xcode-27`) | Three UI shards with Xcode 27, Metal compiler and iOS Simulator |
| CI / test-ui | Ubuntu | Required UI-check aggregation |
| Dependabot / discover-pr | Ubuntu | GitHub API and jq |
| Dependabot / enable-auto-merge | Ubuntu | GitHub CLI |
| Runtime assets / boards | Ubuntu 24.04 | Eight cached FreeCAD/OpenUSD board shards |
| Runtime assets / assemble | Ubuntu 24.04 | Blender hand export and strict runtime catalog validation |
| Release / compile-manual-assets | Reusable Ubuntu pipeline | Calls `runtime-assets.yml` for manually selected sources |
| Release / board-assets | Ubuntu | Selects and validates the exact runtime catalog tested by CI |
| Release / release | macOS | Xcode archive/export, Apple keychain signing, codesign and Mach-O verification |

The UI matrices separate custom planner scenarios, purchase/settings/workout
flows, model/picker interaction, board layouts, and grip/weight flows. Each
shard keeps one simulator and runs each selected test once. Keep these groups
separate: the one-hour test phase runs inside a 70-minute Actions job that also
includes asset restoration, simulator startup and compilation. Combining the
planner and workout suites can exhaust that job limit before every test runs.
The `xcode-27` runner pool can be scarce, so keep grip diagnostics in the
existing grip/weight shard. Configure each workout fixture before opening its
URL, terminate any app process left by an earlier test, and call
`XCUIApplication.open(URL)` once. An unused launch in diagnostic setup cost
about 20–27 seconds per test on the slow hosted run; launching Train before the
URL repeated startup and orientation work. These cold routes start on Train, so
they avoid the Settings navigation transition that previously dropped warm
deep links. Disable spoken cues for visual, weight, and timer tests that do not
assert speech: the workout can begin its countdown without waiting for audio
preparation. Keep one speaker-toggle check in the published visual journey and
combine assertions that share the same Manual weight setup journey.
The purchase/workout shard also checks the third-workout paywall and its
dismissal in one launch. Its free-workout entry and empty-log assertions share
one launch, and the duplicate minimal-log case is gone. The discard/resume
case ends once it verifies that an unfinished session cannot unlock Last;
the separate completed-set case verifies that a real finish does unlock Last.
Free-workout cases disable spoken cues because they assert controls, set
state, and history rather than audio playback.
`test_ci_xctest_contract.py` verifies that every UI test method is selected
exactly once across both required UI jobs; the required UI gate waits for all
matrix shards.

The native CAD job previously used macOS solely to install a DMG. The shared
`scripts/install-freecad.sh` now verifies the pinned official Linux x86_64
Python 3.11 AppImage and extracts its SquashFS payload at the ELF boundary with
`unsquashfs`. Its workspace-owned wrapper supplies the bundled Python home and
FreeCAD library directory and invokes the CLI directly. The job installs the
headless system libraries first, then creates and records its owned toolchain
inside the same shell that installs dependencies and runs the regressions.
An exit trap deletes that toolchain and verifies deletion; the always-run
cleanup validates recorded ownership before removing any remaining directory.
The native job also restores the generated Linux board catalog. Its existing
FreeCAD/OpenUSD pins, test selection, path gates, timeout, and required-check
dependencies are retained. No FUSE mount or AppImage launcher is required.

All runtime board compilation, hand export, catalog assembly, and native CAD
regressions use Linux. macOS allocations are reserved for the Apple toolchain
jobs listed above. Releases reuse the precise successfully tested catalog;
automatic releases do not compile the assets again.

Primary toolchain sources:

- [FreeCAD 1.1.3 release and binary assets](https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.3)
- [Release asset digests](https://api.github.com/repos/FreeCAD/FreeCAD/releases/tags/1.1.3)
- [FreeCAD Linux AppRun launcher](https://github.com/FreeCAD/FreeCAD-Bundle/blob/main/conda/linux/AppDir/AppRun)

The release job also performs API calls and uploads, and the unit-test job
runs a Ruby release-version contract check. Those steps share jobs that already
need macOS; separating them would not eliminate a macOS runner allocation.
Metadata validation stays on macOS because replacing resolved Xcode settings
with source-text matching would weaken the current validation.

Linux verification exposed a platform-dependent redundant midpoint in the
Clavellium cached cord route. Its regression now compares both ordered curves
at every vertex's normalized arc-length station, with a 2 nm tolerance for
nine-decimal-meter cache rounding. It still checks endpoints, total length,
height, branch identities, native-solid clearance and the prescribed sling
length. Dedicated cases reject new bends, reversed direction and backtracking.
No CAD, model, suspension cache or rendered geometry changes are involved.

## XCTest time budgets

`scripts/ci-run-xctest.sh` applies `XCTEST_RUN_TIMEOUT_SECONDS` independently
to `build-for-testing` and `test-without-building`. Simulator startup and a
cold compile do not shorten the time allowed to execute the selected suite.
Each phase still collects diagnostics and terminates its process group on
timeout, and the first failure stops the runner without retrying. The Actions
job timeout bounds the entire job, including setup and both Xcode phases.
Required UI selectors and check aggregation apply regardless of cache warmth.

## Upstream verification

The separate runner audit merged in main `68861ede3` (PR #552) recorded:

- Full native job on Ubuntu 24.04 x86_64 with FreeCAD 1.1.3, Python 3.11
  and the workflow's pinned dependencies: **53 passed**, including all native
  source edits, cord checks and the route-comparison negative cases.
- CI XCTest selection contract: **79 passed**.
- actionlint: clean with the existing unrecognized `xcode-27` label warning
  excluded; unfiltered lint reports that warning.
- `git diff --check`: clean.
- The disposable workspace-owned Docker container and CAD toolchain were
  deleted and deletion was verified.

That Docker verification unpacked the verified AppImage with `unsquashfs` at
its ELF boundary because x86 emulation rejected the AppImage launcher and the
archive has case-sensitive filenames. The combined workflow uses the shared
installer's same payload extraction method. It has already passed hosted
Ubuntu compilation for all 66 boards and the native CAD lane: see the
[cold runtime build](https://github.com/Asherlc/hang-ten/actions/runs/37355190847)
and the [native regression run](https://github.com/Asherlc/hang-ten/actions/runs/37373530929/attempts/2).
Those runs precede this main integration and are retained as historical evidence.

## Combined merge verification

Integration of main `68861ede3` passes all eight Clavellium native tests with
native execution required, using the current Linux-generated catalog and the
installed macOS FreeCAD CLI. The 133 workflow, catalog, and release-selection
regressions also pass. Workflow lint, shell syntax, and source-boundary checks
pass. The compiler cache key is unchanged, as are all 159 app/test Swift and
canonical JSON source hashes and all 156 Linux-generated asset hashes from the
previously validated chooser build. No iOS source or geometry changed in this
merge.
