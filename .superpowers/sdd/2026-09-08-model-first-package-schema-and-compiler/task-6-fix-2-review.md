# Task 6 fix round 2 re-review

## Finding dispositions

### 1. Redundant empty raster presentation — addressed

Swift again rejects a raster presentation whose `holdGeometry` is empty before
performing the package-wide subset, ownership, and derived-presentation checks
(`HangTen/Models/BoardPackageStore.swift:720`). This matches the Python
validator's nonempty-presentation rule and preserves the intended validation
ordering.

The regression fixture is valid up to that rule: it adds a redundant original
presentation with an empty geometry map, a valid aspect ratio, and a real
square PNG asset, so asset and aspect-ratio validation cannot mask the target
failure (`HangTenTests/BoardPackageStoreTests.swift:206`). The related
derived-only ownership fixture now leaves the original presentation nonempty
while removing one original owner, allowing it to exercise the exact-one
ownership rule rather than the earlier empty-presentation rule
(`HangTenTests/BoardPackageStoreTests.swift:235`).

### 2. Python-compatible raw numeric equality — addressed

The Swift raw JSON representation now records number kind separately from
number value (`HangTen/Models/BoardPackageStore.swift:1077`). Integer tokens
remain arbitrary-precision normalized strings, with only JSON integer `-0`
normalized to `0`; they are not narrowed through `Int`, `Int64`, or `Double`.
Floating tokens are decoded through `Double` and must be finite
(`HangTen/Models/BoardPackageStore.swift:1215`). This matches `json.loads` for
the equality contract under review:

- integer and floating tokens remain different kinds;
- floating tokens compare by their decoded binary64 value, so high-precision
  spellings that round to the same value, equivalent exponent notation,
  signed floating zero, and finite underflow compare equal;
- adjacent representable `Double` values compare unequal;
- arbitrary exact integers retain their complete value;
- overflowing/nonfinite floating tokens fail validation.

The surrounding raw representation continues to compare object member order,
array order, scalar type, and decoded scalar value, while rejecting duplicate
decoded object keys. String escapes therefore compare by decoded string value,
as Python does. The derived/source geometry check still compares these raw
structures directly, so the numeric fix does not weaken ordering, type, or
value enforcement.

The tests cover high-precision rounding
(`HangTenTests/BoardPackageStoreTests.swift:345`), exponent equivalence
(`HangTenTests/BoardPackageStoreTests.swift:358`), signed floating zero
(`HangTenTests/BoardPackageStoreTests.swift:371`), adjacent binary64 values
(`HangTenTests/BoardPackageStoreTests.swift:384`), unequal exact integers
(`HangTenTests/BoardPackageStoreTests.swift:397`), integer signed zero
(`HangTenTests/BoardPackageStoreTests.swift:437`), nonfinite overflow
(`HangTenTests/BoardPackageStoreTests.swift:477`), and the pre-existing
integer-versus-floating distinction. Their token-replacement helpers assert
that the intended fixture mutation actually occurred.

## New issues

### Critical

None.

### Important

None.

### Minor

None.

## Verification

- Full Python package suite: 465 passed.
- Converter check: all 61 discovered packages are schema v2.
- Final inventory validation: 61 boards and zero drafts, exit status 0.
- Independent Python/Swift numeric matrix confirmed equivalent high-precision,
  exponent, signed-zero, underflow, adjacent-Double, arbitrary-integer, and
  overflow behavior.
- `git diff --check a533649d e66e8990` passed.
- `git diff --name-only a533649d..e66e8990 -- Hangboards` was empty.
- The temporary Swift module cache used for the independent matrix was deleted
  and verified absent.
- No simulator was created or used.

## Verdict

Approved. Both remaining Task 6 findings are addressed, fixture validation
ordering is sound, no Hangboards data changed, and no new breakage was found.
