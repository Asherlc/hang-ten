# Task 6 fix round 1 report

## Result

Resolved all three Important review findings without rewriting any converted
board package. This is a shared parser/converter correction, not work that must
be repeated for every board: all 61 existing packages pass the stricter
contract, and future packages inherit it automatically.

## Clarification ruling

The brief's phrase "derived-chain packages" was ambiguous against the existing
schema and review. The controller ruled that this fix must preserve valid
original-to-derived relationships while retaining the existing rejection of
derived-to-derived chains. The implementation does not expand schema
acceptance.

## Implementation

- Python and Swift now require original raster presentations to partition the
  complete logical hold inventory exactly once. A hold duplicated between two
  unrelated originals or absent from every original is rejected.
- Every derived raster presentation must carry geometry exactly equal to its
  declared original source. Equality preserves hold/member/array/path-command
  order, scalar values, and integer-versus-floating scalar type.
  - Python compares the order-preserving decoded JSON recursively.
  - Swift uses a bounded raw JSON semantic reader because `JSONDecoder`
    intentionally erases object order and normalizes numeric representations.
- Swift optional v2 metadata now means omission only for `dimensions`,
  `sloper`, size/depth range, grip type, finger/hand capacities, `features`,
  and `equipmentObjectID`. A present `null` is decoded as the concrete type and
  rejected; omission retains the prior nil/default behavior.
- The legacy converter now validates presentation objects against a closed
  allowlist, reports missing and unknown keys, and no longer contains dead
  pseudo-preservation code that was bypassed by its return value.

No `Hangboards/*/board.json` file changed.

## Counterexamples and TDD

Before production edits, direct Python counterexamples demonstrated that the
old parser accepted duplicate original ownership, a hold owned only by a
derived presentation while other original ownership remained, and swapped
derived geometry. The converter also silently deleted `extensionScalar`.

Focused Python RED:

```text
8 failed, 23 passed
```

Focused Python GREEN:

```text
31 passed in 0.84s
```

The first usable Swift RED result contained five tests:

```text
3 failed, 2 passed
```

Duplicate ownership, derived geometry drift, and the explicit-null matrix were
red; the omission control was green. The initial one-hold derived-only fixture
was already rejected by the pre-existing nonempty-presentation rule, so it was
subsequently strengthened to two logical holds: removing one from the original
leaves that original nonempty and isolates the former union-ownership defect.
The exact-equality suite also covers piece order, object-member order, numeric
scalar type, and scalar value.

Focused Swift GREEN after implementation:

```text
8 passed, 0 failed
```

## Full verification

```text
Python package suite: 465 passed in 39.56s
converter --check: checked 61 schema-v2 board packages
final inventory: 61 complete packages, 0 drafts
exact schemaVersion count: 61
semantic audit: 61 packages, 897 logical holds,
                89 original presentations, 7 derived presentations
Swift BoardPackageStoreTests: 98 passed, 0 failed, 0 skipped
git diff --check: passed
```

The semantic audit compared current packages to pre-migration commit
`e60dd049` with type- and order-sensitive equality. It verified unchanged root
metadata, logical hold order/metadata, presentation metadata, exact original
geometry ownership, and exact derived source reuse.

## Simulator lifecycle

All simulator destinations used the exact name
`Hang Ten Paseo shaky-rat Review`, iPhone 16, iOS 26.5, and an explicit UUID.
Commands were polled in bounded 30-second intervals. The authoritative final
xcresult summary was:

```text
deviceId: 8FE98E43-FDA8-45D4-833A-A6417BB8283E
result: Passed
totalTestCount: 98
passedTests: 98
failedTests: 0
skippedTests: 0
```

Three sequential exact-name devices were used rather than the requested one,
and that deviation is recorded explicitly:

- `17C35900-D71C-43CD-9BFC-F74BF983F6E6` exposed a test-only compile error;
  the guarded shell's exit cleanup immediately archived and deleted it.
- `65A3E984-2B61-48D7-BFE1-736D47B062C5` produced the focused RED/GREEN and
  first 98-test result, then was archived and deleted. A later fixture audit
  found the derived-only case was not isolating the intended old behavior.
- `8FE98E43-FDA8-45D4-833A-A6417BB8283E` reran the complete 98-test suite after
  that fixture correction and produced the authoritative summary above.

Final cleanup verified all three UUIDs and the exact name absent, both workspace
simulator manifests at zero bytes, and all task-owned DerivedData/xcresult paths
absent. Shared and unknown simulators were untouched.

## Commit

Commit message: `fix: enforce strict raster migration parity`.
The immutable hash is reported after commit because a commit cannot contain its
own final hash.

## Reusable skill candidates

- Add a general recipe for semantic JSON equality that preserves object-member
  order and numeric scalar type across Python and Swift.
- Add a fixture-review checkpoint that proves every rejection test reaches the
  intended rule rather than an earlier validation guard.
- Add a simulator test harness that keeps cleanup traps installed across
  compile failures and automatically emits the final xcresult summary.

No skill was changed in this fix.
