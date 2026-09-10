# Task 6 code/spec review

## Verdict

**Needs fixes.** The committed 61-package conversion is semantically faithful,
Task 5's transitional loader and its reviewed fixes precede Task 6, both parsers
reject v1, and the Python suite passes. Three Important fail-closed/preservation
gaps remain in the reusable migration and final v2 parser contract.

## Critical

None.

## Important

1. **Raster ownership is checked as a union, not as the required exact
   partition, and derived media is not checked against its canonical source.**
   The Python parser updates one set with every raster presentation and only
   compares the final union with the logical hold set; Swift performs the same
   `formUnion`. Neither side detects a logical hold owned by two unrelated
   original presentations. Their derivation checks only prove raster-to-raster
   typing, so a derived presentation may also bind a different path to a hold
   than its declared source. Independent counterexamples based on
   `captain-fingerfood-dual` (copy one front hold into the other original media)
   and `crimptonite-helium-mobile` (swap two derived hold paths) are both
   accepted by the Python production parser. The Swift code has the same set
   and relationship predicates. This loses the legacy one-owner invariant,
   makes position membership ambiguous, and permits an allegedly derived view
   to change canonical hit-testing geometry. Track ownership across original
   presentations and reject a second owner; require each derived raster
   `holdGeometry` to be exactly its source's geometry, including IDs, pieces,
   scalars, and order. `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:835`,
   `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:1029`,
   `HangTen/Models/BoardPackageStore.swift:664`,
   `HangTen/Models/BoardPackageStore.swift:701`

2. **Swift still treats explicit `null` as omission for optional v2 metadata,
   contrary to the strict Python parser.** Task 6 corrected
   `equipmentObjectID`, but `dimensions`, `sloper`, `sizeMillimeters`,
   `depthRangeMillimeters`, `gripType`, `fingerCapacity`, `handCapacity`, and
   `features` still use `decodeIfPresent`, which returns `nil` for either a
   missing key or JSON `null`. Python branches on key presence and invokes the
   concrete string/number/list parser, rejecting `null`. For example,
   `"sizeMillimeters": null` and `"dimensions": null` are accepted by the app
   but rejected by the canonical package validator. Consequently the claimed
   strict Python/Swift acceptance parity is incomplete and the native loader
   does not independently fail closed for malformed optional values. Use
   `contains` plus `decode` for present optional members, as Task 6 now does for
   `equipmentObjectID`, and add cross-language null-versus-omitted fixtures.
   `HangTen/Models/BoardPackageStore.swift:1174`,
   `HangTen/Models/BoardPackageStore.swift:1350`,
   `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:940`,
   `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:724`

3. **The converter silently deletes unrecognized legacy presentation
   members.** `_convert_presentation` builds a preservation-oriented `result`
   from the input, but never returns it; the fixed six-field literal returned
   afterward drops every other member. A valid catalog document augmented with
   `"extensionScalar": "retain-or-reject"` migrates successfully and loses
   that value. The current 61 files contain no such member, so the catalog-wide
   audit cannot expose this, but the documented reusable one-way utility must
   not silently destroy legacy data under its exact scalar-preservation
   contract. Validate the legacy presentation as a closed v1 object and refuse
   unknown members, or deliberately preserve any schema-supported member;
   remove the dead `result` construction and add the counterexample as a
   regression. `Tools/HangboardPackages/scripts/migrate_to_schema_v2.py:216`,
   `Tools/HangboardPackages/scripts/migrate_to_schema_v2.py:232`

## Minor

None.

## Independent verification

- Commit ancestry proves transitional Task 5 `d1913966` and both reviewed fix
  rounds (`38e8e7ec`, `05bb1c90`, approval `2266fa56`) precede Task 6
  `e171246e`; the final Task 5 skill approval `e60dd049` is Task 6's parent.
- An independent duplicate-key-aware, type-sensitive and order-sensitive audit
  compared every current document to `e60dd049`. It checked root metadata,
  logical hold order and metadata, original ownership exactly once, derived
  source geometry, every geometry member/piece/path-command order, and every
  scalar's Python type and value. Result: `61 packages, 897 logical holds, 89
  original presentations, 7 derived presentations`.
- Representative coverage included the 72-hold/712-command
  `trango-rock-prodigy-pivot`, derived `crimptonite-helium-mobile`, disjoint
  multi-presentation `captain-fingerfood-dual`, one-hold
  `aelith-cyclops-011`, and two-equipment-object
  `metolius-rock-rings-3d` packages.
- `migrate_to_schema_v2.py --check` reports all 61 v2 documents unchanged;
  direct duplicate-key loading was inspected as recursive
  `object_pairs_hook` rejection. The current converter preserves all catalog
  path/scalar/type/order data, but the Important counterexample above shows its
  general preserve-or-reject boundary is incomplete.
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passes with 61 complete packages and zero drafts.
- The complete package Python suite passes: `457 passed in 39.36s`.
- Python test symbols increased from 137 to 141. Swift
  `BoardPackageStoreTests` remains at 90 test methods; the four renamed methods
  replace transitional v1 assertions with strict-v2 equivalents, including
  explicit missing-version and legacy-v1 rejection. No simulator was created
  or used for this review.
- `git diff --check e60dd049 e171246e` passes. No model-media implementation was
  changed by Task 6; the functional Swift delta is legacy removal, raster
  subset/union validation, improved geometry errors, and the
  `equipmentObjectID` null fix.
