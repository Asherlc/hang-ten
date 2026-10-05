# CI runner audit

Audited all 14 jobs in `.github/workflows` on 2026-10-05. Eight use Ubuntu;
six require an Apple toolchain. Job counts exclude matrix expansion.

| Workflow / job | Runner | Requirement |
| --- | --- | --- |
| CI / changes | Ubuntu | Git diff and path classification |
| CI / metadata | macOS | `xcodebuild -showBuildSettings` resolves Debug and Release settings; `sips` checks icons |
| CI / python | Ubuntu | Package validation, staging, source contracts and pytest |
| CI / transgression-native | Ubuntu 24.04 | Native FreeCAD and OpenUSD; no Apple SDK required |
| CI / workflow-lint | Ubuntu | actionlint |
| CI / build-required | Ubuntu | Required-check aggregation |
| CI / build-release-device | macOS | `xcodebuild` with the iPhoneOS SDK |
| CI / test-unit | macOS | XCTest on iOS Simulator |
| CI / test-ui-paywall | macOS | XCTest UI automation on iOS Simulator |
| CI / test-ui-map | Apple runner (`xcode-27`) | Xcode 27, Metal compiler and iOS Simulator |
| CI / test-ui | Ubuntu | Required UI-check aggregation |
| Dependabot / discover-pr | Ubuntu | GitHub API and jq |
| Dependabot / enable-auto-merge | Ubuntu | GitHub CLI |
| Release / release | macOS | Xcode archive/export, Apple keychain signing, codesign and Mach-O verification |

The native CAD job previously used macOS solely to install a DMG. It now
extracts the official Linux x86_64 Python 3.11 AppImage, verifies its pinned
SHA-256, and invokes `AppRun freecadcmd` through a workspace-owned wrapper.
AppRun supplies the bundled Python home and FreeCAD library directory. The
FreeCAD version, dependency pins, test selection, job identity, path gates,
timeout and required-check dependencies are preserved. Extraction needs no
FUSE mount, and the always-run cleanup deletes the exact owned toolchain.

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

## Verification

- Full native job on Ubuntu 24.04 x86_64 with FreeCAD 1.1.3, Python 3.11
  and the workflow's pinned dependencies: **53 passed**, including all native
  source edits, cord checks and the route-comparison negative cases.
- CI XCTest selection contract: **79 passed**.
- actionlint: clean with the existing unrecognized `xcode-27` label warning
  excluded; unfiltered lint reports that warning.
- `git diff --check`: clean.
- The disposable workspace-owned Docker container and CAD toolchain were
  deleted and deletion was verified.

Local Docker verification on this Mac required unpacking the verified AppImage
with `unsquashfs` at its ELF boundary on the container filesystem. Docker's
x86 emulation rejected the AppImage launcher, and the archive has case-sensitive
filenames. The committed workflow uses official `--appimage-extract` on a
native x86_64 Ubuntu runner; that launcher path awaits hosted CI validation.
