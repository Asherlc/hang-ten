# Task 6 fix round 2 report

## Result

Resolved both remaining Python/Swift raster-validation parity gaps without
changing any board package. Every raster presentation must now own at least one
logical hold, and Swift raw derived/source comparison now uses Python-decoded
numeric semantics while retaining JSON numeric kind and ordered structure.

This is a shared loader correction. It applies automatically to all existing
and future schema-v2 raster packages; it is not per-board migration work.

## Implementation

- Restored Swift's per-raster `media.holdGeometry` nonempty guard before subset,
  geometry, and exact-original-ownership validation. A redundant empty original
  can no longer pass merely because other originals form the full partition.
- Replaced Decimal-backed raw numeric equality with a kind-preserving value:
  - integer tokens remain arbitrary-precision strings, so distinct accepted
    integer values are compared exactly without `Int64` narrowing;
  - JSON's only lexically distinct equal integer zero, `-0`, is normalized to
    `0`, matching Python `int` equality;
  - floating tokens decode to finite `Double` values, matching Python's decoded
    `float`/binary64 equality for high-precision, exponent, underflow, and signed
    zero spellings;
  - integer and floating kinds remain distinct, and overflow/nonfinite floating
    values fail closed.
- Preserved the existing ordered raw representation for objects and arrays, so
  member order, array order, strings, booleans, nulls, and every nested value
  still participate in exact derived/source equality.
- Corrected the prior derived-only ownership fixture to leave the original
  raster nonempty while omitting one hold. It therefore continues to exercise
  the exact-one ownership check rather than the newly restored earlier guard.

No Python production change was needed: `_json_values_are_exactly_equal`
already compares standard `json.loads` values recursively with exact type and
member/array order.

## Counterexamples and focused TDD

Before production edits, source inspection and direct runtime tests confirmed
both review cases. The focused RED xcresult on the isolated simulator reported:

```text
result: Failed
totalTestCount: 7
passedTests: 4
failedTests: 3
```

The intended failures were:

- a redundant empty original raster presentation was accepted;
- `0.100000000000000005` versus `0.100000000000000006` was rejected even
  though both decode to the same binary64 value.

The third failure was a test-only shape-constraint spelling error in the exact
integer-value control. After correcting `roundedRect` to the schema spelling
`roundedRectangle`, that control passed against the pre-fix equality behavior.
The initial controls also proved existing acceptance of equivalent exponent and
signed-floating-zero spellings, rejection of an adjacent `Double`, preservation
of integer-versus-floating kind, and overflow rejection.

After the minimal production change, the same seven-test focused GREEN passed:

```text
Executed 7 tests, with 0 failures
```

An additional `-0` versus `0` integer characterization passed against the final
implementation. The final regression matrix covers:

- every raster presentation being nonempty;
- equivalent high-precision floating tokens;
- equivalent exponent spellings;
- signed floating zero;
- a genuinely different adjacent `Double`;
- integer-versus-floating type distinction;
- distinct integer values;
- signed integer zero;
- nonfinite/overflow rejection.

## Full verification

The authoritative `BoardPackageStoreTests` xcresult summary was:

```text
deviceId: 5A21D952-9C41-422B-A9B8-6531D6C48594
result: Passed
totalTestCount: 106
passedTests: 106
failedTests: 0
skippedTests: 0
```

All xcodebuild invocations used an explicit simulator UUID, a workspace-local
DerivedData path, a PTY, and polling intervals of no more than 30 seconds.

Repository-wide checks:

```text
Python package suite: 465 passed in 39.59s
converter --check: checked 61 schema-v2 board packages
final inventory: 61 complete packages, 0 drafts
exact count: packages=61 schema_v2=61 other=0
semantic audit: 61 packages, 897 logical holds,
                89 original presentations, 7 derived presentations
git diff --name-only HEAD -- Hangboards: empty
git diff --check: passed
```

The semantic audit migrated each pre-schema-v2 document from `e60dd049` in
memory and recursively compared it with the current package using Python-type-
and-member-order-sensitive equality. It verified the complete live inventory,
not a fixed package list.

## Simulator ownership and cleanup

- Exact name: `Hang Ten Paseo shaky-rat Review`
- Exact UUID: `5A21D952-9C41-422B-A9B8-6531D6C48594`
- Device/runtime: iPhone 16, iOS 26.5 (23F77)
- The UUID was written to the pending and owned workspace manifests before
  boot/build work, with an active exit cleanup guard for the simulator and exact
  task artifacts.
- Cleanup ran the workspace archive hook and then verified:
  - exact UUID and exact name absent from `simctl list devices`;
  - `.context/paseo-pending-simulators` is zero bytes;
  - `.context/paseo-owned-simulators` is zero bytes;
  - task DerivedData, RED/GREEN/full xcresults, and the UUID record are absent.

Exactly one simulator was created. Shared, standard, and unknown simulators were
left untouched.

## Commit

Commit message: `fix: align raster equality semantics`.
The immutable commit hash is reported after commit because a commit cannot
contain its own hash.

## Reusable skill candidates

- Document the cross-language JSON numeric rule explicitly: preserve integer
  versus floating kind, keep integers arbitrary-precision, normalize integer
  signed zero, and compare floating tokens after finite binary64 decoding.
- Add a standard raster-parity fixture matrix containing redundant empty media,
  exact-one ownership, equivalent exponent/high-precision/signed-zero values,
  an adjacent binary64 value, integer-kind distinction, and overflow.
- Reuse the live-inventory semantic audit pattern: migrate a historical catalog
  in memory, then recursively compare Python types, object-member order, array
  order, and values against every current package.

No skill was modified in this bounded fix.
