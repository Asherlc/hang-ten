# Task 8 integration report — Helium model inventory and ODR registration

## Scope and ownership

This deterministic integration slice changes only the Batch-04 source-audit
handoff assertion, static model inventory, orientation-audit package entry, and
Xcode ODR registration. Helium geometry, package assets, cord-audit records,
and board-specific approval tests remain owned by the concurrent Task 8
authoring work and were neither edited nor staged here.

## TDD record

Before the integration changes, this exact focused command was RED:

```text
rtk proxy .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_batch04_source_audit.py::test_batch04_supersedes_historical_audits_without_opening_the_cord_manifest \
  Tools/HangboardPackages/tests/test_model_orientation_inventory.py::test_discovered_model_inventory_matches_current_packages \
  Tools/HangboardPackages/tests/test_board_package_staging.py::test_xcode_assigns_each_live_model_to_its_own_safe_odr_tag -q
```

It failed on all three intended seams: the superseded `Batch 04 remains
outside` assertion, missing `crimptonite.helium-mobile` from the static model
inventory, and missing `HangTenModelODR/crimptonite-helium-mobile/Hangboards`
with its safe ODR tag.

The inventory-file GREEN run first exposed the missing orientation-audit
package entry (`42 passed, 1 failed`). That entry is now limited to the live
package facts: the single canonical `primary` position, its six ordered contact
IDs, and the absence of orientation/pivot metadata. It makes no new geometry,
orientation, or physical claim.

## Delivered integration

- The source-audit test now asserts the current `Unpromoted Batch 04 packages
  remain outside this closed machine-readable` handoff.
- `MODEL_PACKAGE_IDS` includes `crimptonite.helium-mobile`.
- `HangTen.xcodeproj` has one conventional ODR registration using unique IDs
  `D10000000000000000000022` and `D20000000000000000000022`: a build file,
  folder reference to `$(DERIVED_FILE_DIR)/HangTenModelODR/crimptonite-helium-mobile/Hangboards`,
  On-Demand Model Resources group child, and HangTen Resources-phase entry,
  all using `hang-ten-model-crimptonite-helium-mobile`.

## Verification

- Focused integration seam command: `3 passed in 3.12s`.
- Combined relevant package tests (`test_batch04_source_audit`,
  `test_model_orientation_inventory`, `test_board_package_staging`,
  `test_approved_board_packages`, and `test_cord_audit`): `138 passed in
  5.71s`.
- `rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` passed with no drafts.
- `rtk proxy scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json` passed with 9 represented and 25 excluded decisions.
- `rtk plutil -lint HangTen.xcodeproj/project.pbxproj` passed.
- A top-level PBX object-definition scan found 390 unique identifiers; the
  Helium build-file and file-reference identifiers each occur exactly once.
- `rtk git diff --check` passed.

`xcodebuild -list -project HangTen.xcodeproj` parsed the project and reached
Swift package resolution, but could not continue because this sandbox cannot
reach CoreSimulator services or write Xcode's shared DerivedData/SourcePackages
locations. Its exact temporary result bundle was removed and its absence was
verified. The project lint and Python ODR staging test provide the completed
non-native project/staging checks for this slice.
