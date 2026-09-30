# YY VerticalBoards CAD delivery validation — 2026-09-29

Migrated `yy-verticalboard-first`, `yy-verticalboard-light`, and `yy-verticalboard-one` after checking all local worktrees, fetched remote branches, native-source history, and open pull requests. None was already being migrated. Trango Natural (PR #521) and Tension Whetstone (another active worktree) were excluded.

The operator approved six retained manufacturer photographs before authoring. Board-specific evidence, exact dimensions, source conflicts, and explicitly estimated display geometry are documented in the three adjacent dated source audits. All 49 original contact records and factual board metadata are preserved.

## Verification

The results below record the original migration acceptance. Main commit `65efe7b77` subsequently retired the delivery lock and reproducible-export command; these historical checks are retained as evidence, not current release requirements. Current package validation checks descriptor/model integrity and generated CAD metadata. See the CI audit for later integration and renderer verification.

- Pinned FreeCAD 1.1.3 / OpenUSD 26.08 `verify_reproducible.py --package yy-verticalboard-first --package yy-verticalboard-light --package yy-verticalboard-one`: all three sources rebuild the USDZ and descriptor byte-identically. Receipt: `.context/supreme-zebra-cad-validation/reproducibility.log`.
- Retained `test_verticalboards_native.py`: 3 passed with the native toolchain enabled. Tests reopen/recompute native sources, check constrained sketches, envelopes and actual depths, reject capped mouths and frozen geometry, and save/reopen a real depth edit while checking unrelated contacts remain fixed.
- Complete Python suites under `Tools/HangboardCAD/tests`, `Tools/HangboardModels`, and `Tools/HangboardPackages`: 489 passed, 14 skipped, 24 subtests. Native tests skipped by this invocation were run separately above.
- iOS simulator build-for-testing succeeded. Complete `HangTenTests` suite: 1,234 tests, 3 skipped, zero failures. The new RealityKit test loads all three actual USDZs and verifies every contact has its model, collision, and input-target components.
- Android and iOS release staging passed; generated manifests match between platforms. Android stages USDZs, iOS delivery uses ODR, and neither platform stages CAD sources or removed rasters. Receipt: `.context/supreme-zebra-cad-validation/staging-parity.json`.
- Independent review verified all 49 contact records and factual metadata, actual source/descriptor/model hashes, material-free USDZs, ODR integration and delivery lock; 47 staging/backdrop tests passed.

## Visual evidence

Front/side/top comparisons against the prior committed front raster were presented before acceptance. Prior side/top geometry was unavailable and is labeled accordingly:

- `.context/supreme-zebra-first-cad/comparison.png`
- `.context/supreme-zebra-light-cad/comparison.png`
- `.context/supreme-zebra-one-cad/comparison.png`

The models are analytical display approximations from approved manufacturer evidence, not manufacturing drawings. Published envelopes and grip depths are exact; undocumented aperture sizes, offsets, radii and rear profiles remain documented estimates.

Isolated iOS 26.5 simulator review verified actual loaded models and correct highlights for 16 representative contacts: First and Light jugs, side slopers, outer edges and center edge; One jug, sloper, two-finger pocket, 18 mm edge, inclined edge and center handle. Captures are `.context/supreme-zebra-cad-validation/ios-final-<board>-<contact>.png`; review sheets are `ios-review-<board>.png` in that directory. These are simulator checks; no physical-device visual validation is claimed.

A physical simulator tap directly on First’s lower center cavity changed selection from the outer 45 mm edge to the center 24 mm edge/notch and highlighted that recessed surface. Capture: `.context/supreme-zebra-cad-validation/ios-direct-picking.png`.

Both exact workspace-owned simulator UUIDs were shut down/deleted and absence was verified; ownership manifests were consumed, DerivedData and the copied review app were removed. Receipt: `.context/supreme-zebra-cad-validation/resource-cleanup.json`. No development HTTP server was started.
