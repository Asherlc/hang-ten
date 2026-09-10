# Task 7 fix round 1 independent review

**Range:** `cc70618b..ebfffd03`
**Verdict:** **APPROVED**

The prior P1 README contradiction is resolved. The full README no longer says
that all boards are flat PNG/path packages or that all packages contain
`assets/primary.png`.

The revised opening accurately distinguishes schema-v2 raster-only media
(PNG plus `media.holdGeometry`) from model-only media (USDZ plus a generated,
hash-bound `.model.json` descriptor). The runtime paragraph accurately limits
canonical geometry to raster media, states that model packages use a USDZ and
descriptor, and preserves the logical-holds-without-spatial-fields rule. The
detailed staging section remains intact and continues to state the declared
asset, byte-identity, and no-substitution contract. The Workbench text now
correctly differentiates editable raster geometry from read-only model
geometry. These locations serve distinct overview, runtime, staging, and
editing concerns; their terminology is consistent rather than contradictory.

The reviewed commit changes only `README.md` and its ignored fix report; no
staging script, tests, board package, or runtime code is touched.

## Fresh checks

```text
rtk rg -n -i "flat package|presentation PNG|assets/primary\\.png|canonical hold paths|every supported board|each supported board" README.md
No stale universal PNG/path claim found; the sole match is the new typed-media
opening declaration.

rtk git diff --check cc70618b ebfffd03
exit 0

rtk git diff --exit-code cc70618b ebfffd03 -- \
  scripts/stage-board-packages.py \
  Tools/HangboardPackages/tests/test_board_package_staging.py \
  Hangboards HangTen
exit 0

rtk git diff --name-status cc70618b ebfffd03
A  .superpowers/sdd/2026-09-08-model-first-package-schema-and-compiler/task-7-fix-1-report.md
M  README.md
```
