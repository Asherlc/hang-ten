# Task 6 fix round 1 re-review

## Original finding dispositions

### 1. Exact raster ownership and derived/source equality — ADDRESSED, with new parity issues

Both parsers now count ownership only across original raster presentations and
require every logical hold's count to equal one. Derived presentations remain
valid only when they reference an original raster, so ordinary
original-to-derived packages still load while derived-to-derived chains remain
rejected. Both parsers also compare the derived `holdGeometry` with its declared
source before constructing the final board.

Python's recursive comparator correctly distinguishes boolean, integer, and
floating types, preserves object-member and array order, and compares decoded
string values. Swift's new raw reader preserves order, rejects duplicate decoded
member names (including escaped-name aliases), delegates string/unicode escape
validation to `JSONDecoder`, distinguishes booleans from both numeric kinds, and
has a 128-level recursion bound. The cited duplicate-owner, derived-only-owner,
path/piece/member-order, scalar-value, and integer-versus-floating cases are
covered. Two new cross-language gaps remain below.

### 2. Explicit null versus omission — ADDRESSED

Swift now uses `contains` plus concrete `decode` for all fields named in the
finding: `dimensions`, `sloper`, `sizeMillimeters`, `depthRangeMillimeters`,
`gripType`, `fingerCapacity`, `handCapacity`, `features`, and
`equipmentObjectID`. A present `null` therefore fails decoding, while an absent
field retains nil or the `primary` default. The explicit-null matrix exercises
every field and the omission control verifies every resulting runtime value.
`HangTen/Models/BoardPackageStore.swift:1425`,
`HangTen/Models/BoardPackageStore.swift:1598`

### 3. Converter unknown-member data loss — ADDRESSED

Legacy presentations now have an explicit closed allowlist and required-key
set. `extensionScalar` and any other unknown member are rejected before
conversion, and the previously dead preservation dictionary is gone. The
converter's fixed canonical return therefore serializes only fields it has
already proved are accepted v1 fields; it no longer silently loses an accepted
member. `Tools/HangboardPackages/scripts/migrate_to_schema_v2.py:96`,
`Tools/HangboardPackages/scripts/migrate_to_schema_v2.py:236`

## New issues

### Critical

None.

### Important

1. **Swift accepts an empty raster presentation that Python rejects.** Python
   retains the per-presentation `holdGeometry` nonempty guard before exact-one
   ownership counting. Swift removed that guard: an empty key set is a subset
   of the logical hold set, its geometry loop is skipped, and the package-wide
   counts still pass when other original presentations partition every hold.
   A package with two valid disjoint originals plus a third original with
   `holdGeometry: {}` is therefore accepted by the native loader but rejected
   by the canonical parser. The new Swift derived-only fixture does not catch
   this because it empties the only original, so the later exact-one check
   rejects all missing holds; the existing incomplete-geometry fixture uses a
   nonempty map whose piece array is empty and reaches a different validator.
   Restore the nonempty guard in Swift and add the redundant-empty-presentation
   counterexample so validation ordering is proven. This is a fail-closed
   Python/Swift parity regression in the first finding's fix.
   `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:1061`,
   `HangTen/Models/BoardPackageStore.swift:718`,
   `HangTenTests/BoardPackageStoreTests.swift:205`,
   `HangTenTests/BoardPackageStoreTests.swift:408`

2. **Swift and Python assign different equality semantics to high-precision
   floating tokens.** Python compares standard `json.loads` values, so
   `0.100000000000000005` and `0.100000000000000006` both become the same
   `float` (`0.1`) and compare equal with the same floating type. Swift parses
   those tokens into distinct `Decimal` values and rejects the otherwise
   identical derived geometry. Thus the current native loader can reject an
   original-to-derived package accepted by the canonical Python parser even
   though object order and the JSON numeric type agree. The numeric regression
   only covers `0.0` versus integer `0`; add same-type values around a Double
   rounding boundary and give both implementations one declared numeric-value
   normalization rule. This violates the fix's claimed cross-language semantic
   equality rather than merely comparing different JSON spellings.
   `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:863`,
   `HangTen/Models/BoardPackageStore.swift:1204`,
   `HangTenTests/BoardPackageStoreTests.swift:281`

### Minor

None.

## Verification

- The complete Python package suite passes: `465 passed in 38.91s`.
- The converter idempotence check reports `checked 61 schema-v2 board
  packages`; final-inventory validation reports 61 complete packages and zero
  drafts.
- `git diff --name-only 5835a518..45b2db51 -- Hangboards` is empty, confirming
  the fix changed no board package data.
- `git diff --check 5835a518 45b2db51` passes.
- The numeric counterexample was checked directly: Python decodes both tokens
  above as equal `float` values, while Foundation `Decimal` preserves them as
  unequal values. The temporary Swift module cache was deleted and verified
  absent.
- No simulator was created or used for this re-review. The implementation
  report's final Swift result records 98 passed, but this review relies on code,
  fixture, and read-only/non-simulator verification as required.

## Verdict

**Needs another fix round.** The three original defects are substantively
corrected, but two Important Python/Swift parity gaps remain in the new raster
enforcement.
