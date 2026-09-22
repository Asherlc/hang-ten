# Task 9 integration report — Light Rail model inventory and ODR registration

## Scope and ownership

This deterministic integration slice changed the static model inventory, the
3-D orientation audit, Xcode ODR registration, and one newly discovered
source-tier compatibility seam, plus this report. Light Rail geometry/package
assets, approved-board assertions, and the Astra-owned cord-audit test/manifest
files remain owned by the concurrent Task 9 authoring work and were not
edited, staged, committed, or pushed here.

## Delivered integration

- `MODEL_PACKAGE_IDS` now includes `metolius.light-rail-2`.
- The orientation audit records one v1 model presentation for one physical
  reversible unit, positions `20mm-side` and `15mm-side`, all four ordered
  contacts, identity upright plus physical 180-degree front/view-axis
  inversion, and authored-display-estimate pose/contact guides.
- The same audit entry restricts `pairedLeadCord` to the two evidenced exterior
  entry regions and explicitly excludes an underside mouth and hidden vertical
  bore.
- `HangTen.xcodeproj/project.pbxproj` now has the dedicated
  `HangTenModelODR/metolius-light-rail-2/Hangboards` folder reference, ODR group
  child, Resources-phase build file, and
  `hang-ten-model-metolius-light-rail-2` tag using fresh IDs
  `D10000000000000000000023` and `D20000000000000000000023`.
- The additive cord-audit source-tier parser seam now accepts the exact
  retained-evidence tier `independent` while continuing to reject the nearby
  unknown value `independent-field`; the new regression lives in
  `test_cord_audit_source_tiers.py`.

## Verification

- Orientation-audit assertion: `1 passed`.
- Existing recently-migrated ODR provisioning assertion: `1 passed`.
- Strict TDD source-tier RED: `1 failed, 1 passed` before the parser change.
- Source-tier GREEN plus Light Rail retained-evidence parser regression:
  `3 passed`.
- `plutil -lint HangTen.xcodeproj/project.pbxproj`: passed.
- `git diff --check`: passed.
- PBX object-definition scan: `391` definitions, `391` unique; no duplicate
  IDs. The new build-file ID occurs twice (definition/reference) and the new
  file-reference ID three times (definition/group/build-file references), as
  expected for this project format.
- The Light Rail package is now present, and its board-specific approval lane
  passes (`3 passed, 35 deselected`). The exact static-inventory and safe-ODR
  discovery lanes currently fail in package-owned suspension validation because
  the new descriptor's paired-lead attachment points lie outside its declared
  model bounds. This is disjoint from the inventory/PBX edits here and must be
  corrected by the package owner before those discovery tests can run green.

No HTTP server or external resource was started.
