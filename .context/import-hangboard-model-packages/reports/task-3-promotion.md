# Task 3 promotion report

Date: 2026-09-10  
Owner: `gray-horse`

## Promoted package inventory

- `Hangboards/yy-baguette-evo/board.json`
- `Hangboards/yy-baguette-evo/assets/primary.usdz`
- `Hangboards/yy-baguette-evo/assets/primary.model.json`
- `Hangboards/nature-stone-hanger/board.json`
- `Hangboards/nature-stone-hanger/assets/primary.usdz`
- `Hangboards/nature-stone-hanger/assets/primary.model.json`

Both package roots contain exactly `board.json` and `assets/`; both asset
directories contain exactly the declared USDZ and descriptor. Neither board
contains `holdGeometry`, raster media, or a PNG fallback.

## Exact promoted hashes

| Asset | SHA-256 |
| --- | --- |
| Baguette Evo USDZ | `e006aad2dfac8e5a3911d1e3e0944830056856d45d757fc76c360e339c76f91b` |
| Baguette Evo descriptor | `e73f56e2f9ae903583896f88067f03f9f3d9bb1065b8febddd825fcd98b4532c` |
| Nature Stone Hanger USDZ | `366e6833403d8877b62b2403ce98683e4c27f9ce76c1d9e9abaa24e50ba382e4` |
| Nature Stone Hanger descriptor | `eb2a83c035d1a80e172f196c68210b4b0556a897f367ebd3ddcd27b196237fa8` |

All four promoted files compare byte-for-byte equal to the committed Task 2
outputs under `.context/import-hangboard-model-packages/converted`.

## Validation results

- Type- and order-sensitive Baguette comparison: PASS. `git show HEAD:... |
  jq 'del(.presentations)'` is identical to the promoted board after deleting
  only `presentations`; all pre-existing logical metadata and hold order remain.
- Installed package validator: PASS, 62 complete direct-child packages and no
  drafts. Command:
  `.context/import-hangboard-model-packages/gray-horse-hangboard-packages-venv/bin/hangboard-packages validate --root Hangboards --final-inventory`.
- Package status discovery: PASS, includes `nature.stone-hanger` and
  `yy.baguette-evo`, no drafts.
- Blender-free committed report checks: PASS, 12 tests.
- Focused importer tests: PASS, 19 tests.
- `git diff --check` on Task 3 paths: PASS.
- The documented `scripts/hangboard-packages.sh` wrapper could not bootstrap a
  fresh environment because restricted network access prevented pip from
  retrieving `setuptools>=84.0.0`. This is an environment bootstrap limitation,
  not a package validation failure; the already-owned environment ran the same
  installed validator successfully.

## Non-promoted candidates

- Metolius: blocked because actual reimport reports a body mesh without an
  image material.
- Training Tiles: blocked because four existing logical IDs have no explicit
  source-mesh mapping.

Their existing board package paths were not modified.
