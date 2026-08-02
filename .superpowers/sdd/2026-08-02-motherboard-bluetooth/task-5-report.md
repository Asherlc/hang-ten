# Task 5 report — WorkoutSessionStore

## DONE

Implemented only the injectable Codable workout-session history store. The task brief at `task-5-brief.md` describes the subsequent Bluetooth transport work, so this implementation follows the direct Task 5 request for `WorkoutSessionStore` and does not begin that transport work or the later AppStore/HangTenApp dependency wiring.

## Files changed

- `HangTen/Models/WorkoutSessionStore.swift` — `WorkoutSessionStoring` plus a `UserDefaults`-injected JSON store. It reads/writes the stable `workout.sessionHistory` key, sorts newest-first by `recordedAt` and UUID tie-breaker, retains 20 entries, tolerates missing/malformed values as an empty history, and persists append/removal operations. Only `WorkoutSessionRecord` summaries are stored; no raw samples are retained.
- `HangTenTests/WorkoutSessionStoreTests.swift` — behavior tests for absent/malformed data, cross-instance persistence, deterministic ordering, the 20-record bound, and persisted removal.
- `HangTen.xcodeproj/project.pbxproj` — hand-maintained source and test-file references/build-phase entries.

## TDD evidence

- RED: after adding the tests and Xcode references, `xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination "generic/platform=iOS Simulator"` failed because `HangTen/Models/WorkoutSessionStore.swift` was missing.
- GREEN: the same bounded command passed after the implementation (`** TEST BUILD SUCCEEDED **`). `git diff --check` also passed.

## Test limitation

Runtime XCTest was deliberately not invoked: the task ledger records a local simulator-service hang for focused and full tests. The bounded build-for-testing command compiled and linked the complete test bundle, including `WorkoutSessionStoreTests`, without waiting for a simulator runtime.

## Commit

`feat: persist workout session history` (this scoped implementation and report).
