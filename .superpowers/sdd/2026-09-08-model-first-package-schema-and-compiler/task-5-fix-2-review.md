# Task 5 fix round 2 re-review

## Finding Verdicts

### 1. Python-compatible nine-decimal rounding — ADDRESSED

`boardDescriptorRoundedToNinePlaces` now returns finite values unchanged once their ULP exceeds the `1e-9` quantum, avoiding the lossy scale/unscale path that moved `1e20`; smaller values retain the FMA residual check for products rounded onto a half-integer and use ties-to-even otherwise. The boundary table covers the prior normalized midpoint, both sides of `2^22`, the `2^23` transition, `1e20`, `1e300`, and the greatest finite double. An independent 500,014-value check of the same algorithm against Python `round(value, 9)` across normalized values and the transition range found no mismatch. [HangTen/Models/TrainingModels.swift:7](../../../HangTen/Models/TrainingModels.swift#L7), [HangTen/Models/TrainingModels.swift:16](../../../HangTen/Models/TrainingModels.swift#L16), [HangTenTests/BoardPackageStoreTests.swift:66](../../../HangTenTests/BoardPackageStoreTests.swift#L66)

### 2. Logical-only `BoardHold` and complete typed-media migration — ADDRESSED

`BoardHold` now has only its logical initializer and stores no geometry, frame, or presentation identity. The schema-v1 loader still confines legacy spatial ownership to `BoardPackageLegacyHold` before normalizing it into raster presentation media. Removing the silent overloads made missed callers compile errors; the affected test helpers now either construct metadata-only logical holds or explicitly build `BoardRasterMedia`, including the formerly broken target-substitution fixtures. The report records successful build-for-testing plus all seven affected suites: 188 tests in the core group and 168 migration-suite tests, all passing. [HangTen/Models/TrainingModels.swift:620](../../../HangTen/Models/TrainingModels.swift#L620), [HangTen/Models/BoardPackageStore.swift:2329](../../../HangTen/Models/BoardPackageStore.swift#L2329), [HangTenTests/BoardTargetSubstitutionTests.swift:5](../../../HangTenTests/BoardTargetSubstitutionTests.swift#L5), [HangTenTests/BoardTargetSubstitutionTests.swift:54](../../../HangTenTests/BoardTargetSubstitutionTests.swift#L54)

### 3. Whitespace-, escape-, order-, and depth-correct descriptor scanning — ADDRESSED

The scanner now consumes leading JSON whitespace, continues to decode member strings with `JSONDecoder` so escaped quotes/braces cannot terminate them early, checks raw `holds` order before dictionary conversion, and applies an explicit 128-level bound to both object and array recursion. Trailing input and the rest of JSON syntax remain authoritative to the subsequent full `JSONDecoder` pass. Tests cover padded descriptors, escaped delimiters before `holds`, excessive nesting, and an unsorted hold map. Exposing the helper at module-internal scope for `@testable` access does not make it a public API or bypass the production loader's descriptor validation. [HangTen/Models/BoardPackageStore.swift:1602](../../../HangTen/Models/BoardPackageStore.swift#L1602), [HangTen/Models/BoardPackageStore.swift:1612](../../../HangTen/Models/BoardPackageStore.swift#L1612), [HangTen/Models/BoardPackageStore.swift:1647](../../../HangTen/Models/BoardPackageStore.swift#L1647), [HangTenTests/BoardPackageStoreTests.swift:147](../../../HangTenTests/BoardPackageStoreTests.swift#L147), [HangTenTests/BoardPackageStoreTests.swift:161](../../../HangTenTests/BoardPackageStoreTests.swift#L161)

## New Breakage in the Fix Diff

None.

## Out-of-Scope Observations

The reported always-run build-phase and empty-Sentry-DSN warnings predate this fix; no new warning or task-scoped defect is evidenced.

## Verdict

**Fix round: All findings addressed, no new Critical/Important breakage.**
