# Task 5 fix round 1 re-review

## Original Finding Verdicts

### 1. Python-compatible nine-decimal rounding — NOT ADDRESSED

The FMA branch fixes the cited true-midpoint case, and the magnitude guard prevents multiplication overflow near `1e300`, but the helper still multiplies and divides every smaller finite value. That round trip is not identity for many values that Python correctly leaves unchanged: for example, `boardDescriptorRoundedToNinePlaces(1e20)` evaluates to `9.999999999999998e19`, while Python `round(1e20, 9)` is `1e20`. `validateDescriptorVector` therefore still rejects a valid finite, already-nine-decimal model coordinate. The new overflow test only exercises a value above the guard threshold and misses this range. [HangTen/Models/TrainingModels.swift:7](../../../HangTen/Models/TrainingModels.swift#L7), [HangTen/Models/BoardPackageStore.swift:1584](../../../HangTen/Models/BoardPackageStore.swift#L1584), [HangTenTests/BoardPackageStoreTests.swift:70](../../../HangTenTests/BoardPackageStoreTests.swift#L70)

### 2. Logical-only `BoardHold` and consumer migration — NOT ADDRESSED

The stored spatial fields are gone and schema-v1 decoding now uses an appropriate loader-private adapter. However, the retained source-compatibility initializers silently discard their `geometry`/`frame` arguments, while `TrainingBoard` still creates an empty-media default presentation. Unchanged callers therefore compile but lose behavior. A concrete regression is `BoardTargetSubstitutionTests`: its helper supplies frames through the discarded initializer and no typed presentation media; `testUntaggedThreeFingerPocketSubstitutionKeepsOneHoldPerHand` now resolves no left/right frames and returns `[]` instead of `['left-29', 'right-29']`. That suite was not included in the reported downstream run. The migration must either update all such consumers/fixtures to typed media or remove the compatibility overloads so missed migrations fail at compile time rather than silently. [HangTen/Models/TrainingModels.swift:711](../../../HangTen/Models/TrainingModels.swift#L711), [HangTen/Models/TrainingModels.swift:900](../../../HangTen/Models/TrainingModels.swift#L900), [HangTenTests/BoardTargetSubstitutionTests.swift:15](../../../HangTenTests/BoardTargetSubstitutionTests.swift#L15), [HangTenTests/BoardTargetSubstitutionTests.swift:197](../../../HangTenTests/BoardTargetSubstitutionTests.swift#L197)

### 3. Reliable raw descriptor hold-order validation — NOT ADDRESSED

The scanner detects an ordinary unsorted `holds` object, but it does not accept the same JSON language as `JSONDecoder` and the Python parser: `memberNames` consumes `{` before skipping leading whitespace. A descriptor beginning with a valid space or newline is therefore rejected as malformed before normal decoding, even though Python accepts it and its hold order is otherwise canonical. The recursive `skipValue` implementation also has no nesting limit, so a sufficiently deeply nested malformed value can exhaust the stack before `JSONDecoder` gets the chance to reject it. Use a bounded parser/order-preserving JSON representation, and at minimum consume leading whitespace and cap nesting. [HangTen/Models/BoardPackageStore.swift:1476](../../../HangTen/Models/BoardPackageStore.swift#L1476), [HangTen/Models/BoardPackageStore.swift:1610](../../../HangTen/Models/BoardPackageStore.swift#L1610), [HangTen/Models/BoardPackageStore.swift:1642](../../../HangTen/Models/BoardPackageStore.swift#L1642)

## New Issues

### Critical

None.

### Important

- The untouched target-substitution regressions described under Finding 2 are new breakage introduced by the silent-discard compatibility initializers.

### Minor

None.

## Verification and Documentation

- The implementer report records the four focused regressions passing, `BoardPackageStoreTests` at 87/87, and `WorkoutActivityRecordingTests` at 35/35. I did not create or run a simulator for this review.
- The report now transparently names preliminary UUID `5B4DF924-CAC1-4111-BC0F-EA95141B9CA4`, states it ran no XCTest, and records its cleanup before test UUID `5B46ABB7-5D73-4298-811B-EF63E9618341`; it also states both were verified deleted. No documentation finding remains. [.superpowers/sdd/2026-09-08-model-first-package-schema-and-compiler/task-5-fix-1-report.md:94](task-5-fix-1-report.md#L94)

## Assessment

**Findings remain / Needs fixes.** The fix improves all three areas but does not yet provide exact Python rounding across finite doubles, complete typed-media migration, or robust raw JSON order validation.
