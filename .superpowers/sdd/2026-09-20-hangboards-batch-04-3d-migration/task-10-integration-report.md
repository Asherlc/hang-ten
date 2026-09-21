# Task 10 integration report — Rock Rings model inventory and ODR registration

## Scope and ownership

This deterministic integration slice owns the static model inventory, the 3-D
orientation audit, Xcode ODR registration, the native camera/instance
regression, reusable-instance cord-topology discovery, and this report. Rock
Rings geometry/package assets, approved-board assertions, canonical cord-audit
data, and other concurrent authoring files remain outside this slice.

## Delivered integration

- `MODEL_PACKAGE_IDS` now includes `metolius.rock-rings-3d`, with a focused
  contract test for the v2 slot maps, identical identity/unreflected units,
  and independent paired-lead suspension documents.
- The orientation audit records one canonical physical unit instantiated twice
  as `left-ring` and `right-ring`, exact slot mappings, identity orientation,
  visible roof/lateral attachment evidence, and the explicit no-through-bore
  ruling.
- `HangTen.xcodeproj/project.pbxproj` registers the dedicated
  `HangTenModelODR/metolius-rock-rings-3d/Hangboards` folder and
  `hang-ten-model-metolius-rock-rings-3d` tag using fresh IDs
  `D10000000000000000000024` and `D20000000000000000000024`.
- `BoardModelTests` now asserts that the selected primary position resolves
  both reusable units from their per-instance canonical translations, keeps
  their world bounds separated, and frames the union of both units and cords.
  Missing/wrong topology is a hard failure; bounds and projected points must be
  finite.
- `cord_audit.py` now discovers topology from every reusable instance and fails
  closed for media-plus-instance declarations, partial suspension, mixed known
  topologies, and unsupported topology objects. Legacy media-level suspension
  remains unchanged. The new disjoint regression file covers the real Rock
  Rings package and synthetic failure fixtures.

## Verification

- `plutil -lint HangTen.xcodeproj/project.pbxproj`: passed.
- PBX object-definition scan: `397` definitions, `397` unique; no duplicate
  IDs. `git diff --check`: passed.
- `pytest -q Tools/HangboardPackages/tests/test_model_orientation_inventory.py`:
  `44 passed`.
- `pytest -q Tools/HangboardPackages/tests/test_board_package_staging.py -k
  'live_model or staging_phase or recently_migrated'`: `4 passed`.
- `pytest -q Tools/HangboardPackages/tests/test_approved_board_packages.py -k
  rock_rings`: `3 passed`.
- `pytest -q Tools/HangboardPackages/tests/test_cord_audit_reusable_instances.py`:
  `4 passed` (RED before the fix, GREEN after it).
- `pytest -q Tools/HangboardPackages/tests/test_cord_audit.py
  test_cord_audit_reusable_instances.py`: `41 passed, 1 failed`; the concurrent
  existing count assertion still expects `represented: 10`, while the added
  Rock Rings model correctly makes the report `represented: 11`. The geometry
  owner subsequently updated this expectation; the final combined focused
  package/orientation/cord lane passed all 126 tests and the full package suite
  passed all 666 tests. No audit failure remains.
- Focused native lane on the booted iPhone 17 Pro iOS 26.5 simulator:
  `1 passed, 0 failed, 0 skipped`. Xcode emitted four existing warnings; no
  infrastructure limitation occurred.
- The complete focused XcodeBuildMCP text log is retained verbatim at
  `.context/learned-giraffe-task10-evidence/native-primary-separation.log`
  (SHA-256 `17c921378615b9bd7ca8d0c0810c50ee1f4df6237798906518e8d357ef275780`).
- `plutil -lint HangTen.xcodeproj/project.pbxproj`: passed.
- PBX object-definition scan: `397` definitions, `397` unique; no duplicate
  IDs. `git diff --check`: passed. This slice remained unstaged until combined
  independent review and the controller's atomic-commit release.
- Cleanup completed for the two exact Task 10-owned XcodeBuildMCP artifacts:
  the focused `.xctestproducts` and `.xcresult` paths under the
  `learned-giraffe-2e050651c814` workspace. Both paths were verified absent;
  deletion is not recoverable from this workspace. Shared DerivedData and
  simulator resources were left untouched.
- Fresh independent Astra review of the complete Task 10 diff: PASS, no
  findings. The controller released the combined commit and automatic push.
