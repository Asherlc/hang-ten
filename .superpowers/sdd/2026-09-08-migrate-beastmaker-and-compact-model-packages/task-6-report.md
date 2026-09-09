# Task 6 — staging, build, and source-boundary verification

Date: 2026-09-09

## Changes

- Added one data-driven staging characterization for the two promoted live
  model packages. It parses the staged inventory, requires exactly
  `primary.usdz` and `primary.model.json`, compares source and staged bytes for
  both assets, and verifies the staged descriptor hash against the staged USDZ.
- Migrated the three stale `BoardSourceBoundaryTests` invariants to schema-v2
  typed media. Raster packages still require their package image URL; model
  packages use their package asset URL and no image URL. The boundary now
  requires exact declared-versus-actual assets, keeps model packages model-only,
  rejects PNG fallback, and rejects legacy `geometry`/`presentationID` hold
  sentinels for Beastmaker 1000 and Compact II.
- Updated `Tools/HangboardPackages/README.md` to record the current inventory:
  59 raster v2 packages and two model-only v2 packages.

## Verification

- `.context/hangboard-packages-venv/bin/python -B -m pytest Tools/HangboardPackages/tests/test_board_package_staging.py Tools/HangboardPackages/tests/test_model_first_packages.py -q`
  — **PASS: 52 passed**. The new staging test would fail on dropped or renamed
  USDZ/descriptor bytes, extra or missing assets, or a descriptor hash not
  bound to the staged USDZ.
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  — **PASS: 61 complete packages, 0 drafts**.
- `SRCROOT="$PWD" scripts/verify-board-source-boundary-manifest.sh` — **PASS**.
- `xcrun swiftc -frontend -parse HangTenTests/BoardSourceBoundaryTests.swift`
  — **PASS** (Swift syntax parse).
- `git diff --check` — **PASS**.

## Build limitation

The requested unsigned simulator `xcodebuild ... build-for-testing` was
attempted twice. The first attempt stopped while fetching Swift packages due
to unavailable DNS/network access. The second used workspace-owned copies of
the exact resolved checkouts, repositories, artifacts, and workspace state,
with automatic resolution and updates disabled; Xcode then stopped before
compilation with `Missing package product 'AmplitudeSwift'` and `Missing
package product 'Sentry'`. CoreSimulatorService was unavailable throughout.
No simulator was created. All Task 6-owned DerivedData and package-cache
directories were removed after each attempt.

The existing staging implementation was not changed: its validated recursive
copy behavior is covered by the new live-package characterization.
