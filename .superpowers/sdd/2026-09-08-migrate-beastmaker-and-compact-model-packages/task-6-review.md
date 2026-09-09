# Task 6 review checkpoint

Reviewed commits: `2e9b67b2..2f661fc4`, then fix round
`2f661fc4..c43ebadc`.

## Original review finding

**Moderate — raster source-boundary coverage was weakened.** The first Task 6
revision changed the legacy per-hold geometry invariant to require only that
the default raster media mapping was non-empty. A raster package missing one or
more logical hold owners could therefore pass this boundary test. This did not
meet the Task 6 requirement to make the source-boundary test schema-v2 aware
without weakening raster package guarantees.

## Fix evidence

`c43ebadc` restores the raster check in
`HangTenTests/BoardSourceBoundaryTests.swift` by:

- collecting ownership across all original raster presentations;
- rejecting overlapping original owners;
- requiring the original-owner union to equal the full logical hold-ID set;
- requiring every declared raster geometry list to contain at least one piece.

The model-only branch remains unchanged: only the two migrated boards may use
model media; their declared assets must be exactly the USDZ and descriptor;
PNG fallback and legacy `geometry`/`presentationID` sentinels remain rejected.
Production staging is unchanged from `2f661fc4`; the live-package staging
characterization continues to prove the two declared assets stage
byte-for-byte and that each staged descriptor hashes its staged USDZ.

Fresh focused verification after the fix:

- `.context/hangboard-packages-venv/bin/python -B -m pytest Tools/HangboardPackages/tests/test_board_package_staging.py Tools/HangboardPackages/tests/test_model_first_packages.py -q` — 52 passed.
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` — 61 complete packages and 0 drafts.
- `SRCROOT="$PWD" scripts/verify-board-source-boundary-manifest.sh` — passed.
- `xcrun swiftc -frontend -parse HangTenTests/BoardSourceBoundaryTests.swift` — passed.
- `git diff --check` — passed.

## Verdict

**SPEC: PASS.** The corrected source-boundary test preserves both the raster
single-owner/non-empty geometry contract and the model-only migration
contract.

**QUALITY: PASS.** The focused tests are proportionate: the staging suite
exercises the production recursive copier with both promoted packages, and the
model-first suite covers the relevant model-media rejection paths.

## Pending native gate

Native build and simulator validation remain pending, separately from this
review result. The requested `xcodebuild build-for-testing` could not reach
compilation because the offline environment lacks the `AmplitudeSwift` and
`Sentry` package products; CoreSimulatorService was also unavailable. The
Swift parse check proves syntax only, not a successful type-check, link, or
XCTest execution.
