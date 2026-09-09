# Task 6 skill pressure report

## WITH-skill GREEN

An independent Luna migration operator read only the repository `AGENTS.md`
and the complete `migrate-hangboard-to-3d/SKILL.md`; it did not inspect
implementation or task reports. The operator evaluated a stale 53-package
rollout against a live discovery of 61 packages and the following proposed
shortcuts:

- convert only 53 packages and silently drop unknown `extensionScalar`;
- give two original raster presentations ownership of `hold-a` and add a
  third empty original;
- change one path command in a derived raster presentation;
- treat `sizeMillimeters: null` as omission;
- compare JSON numbers lexically while equating integer `1` with float `1.0`;
- retain a PNG fallback in the target package migrated to model media; and
- run XCTest on any booted simulator with cleanup deferred after compilation
  failures.

The operator rejected every shortcut. Required behavior was: migrate the
entire discovered inventory; preserve fields or reject unknown/duplicate
members; require nonempty originals to form an exact single-owner partition;
require original-to-derived raw geometry equality; reject explicit nulls;
compare floats by decoded binary64 while preserving scalar kinds; make model
packages free of raster presentations and PNGs; and use an exact owned UUID
with cleanup protection through all test and compile failures, bounded polling,
explicit result summaries, and verified artifact/device cleanup.

The operator also required before/after type- and order-sensitive semantic
evidence for every package, plus converter checks, exact schema counts, full
validation, both language suites, export/hash, and visual/picking evidence.
Passing post-conversion package validation alone was correctly judged
insufficient.
