# Task 1 report: Debug-only board-editor settings visibility

## Implementation summary

Wrapped only the Settings `Board packages` section (including the existing Board editor link) in `#if DEBUG`. The pre-existing `showsEditorReview` initialization and `navigationDestination` are unchanged, preserving the DEBUG review route.

Added `SettingsBoardEditorVisibilityUITests`, which launches the app, opens Settings through the normal toolbar, and asserts the real `settings.boardEditor` control is present in Debug and absent in Release. This is an accessibility-tree behavior assertion, not a source-text assertion.

## TDD evidence

The behavior test and its project membership were added before production code.

RED command, before the guard:

```
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -configuration Release -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath /private/tmp/hangten-editor-visibility-red-5 -only-testing:HangTenUITests/SettingsBoardEditorVisibilityUITests
```

Result: Xcode reached `Resolve Package Graph`, checked out the four declared Swift packages, then exited before compiling or executing the selected test. No `Build` directory or XCTest result was produced, so the anticipated assertion failure (`XCTAssertFalse` receiving the still-visible `settings.boardEditor`) could not be captured in this environment. This is a verification-environment limitation, not test evidence; rerun this command in a functioning Xcode environment to record the expected red assertion.

GREEN production change: added the `#if DEBUG` / `#endif` around the Board packages `VStack` in `AppSettingsView`.

## Commands and results

| Command | Result |
| --- | --- |
| `codegraph explore "AppSettingsView board editor section relevant tests current source"` | CodeGraph correctly reported no repository index; continued with normal inspection per its instruction. |
| `xcodebuild test ... -configuration Release ... -only-testing:HangTenUITests/SettingsBoardEditorVisibilityUITests` | Did not reach test execution; stopped after package graph resolution as described above. |
| `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -configuration Debug -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO ...` | Did not reach compilation; stopped after `Resolve Package Graph`. |
| `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -configuration Release -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO ...` | Did not reach compilation; stopped after `Resolve Package Graph`. |
| `git diff --check` | Passed with no whitespace errors. |
| `plutil -lint HangTen.xcodeproj/project.pbxproj` | Passed: `HangTen.xcodeproj/project.pbxproj: OK`. |

## Files changed

- `HangTen/Views/AppSettingsView.swift`
- `HangTenUITests/SettingsBoardEditorVisibilityUITests.swift`
- `HangTen.xcodeproj/project.pbxproj`
- `.superpowers/sdd/ios-editor-visibility-plan/task-1-report.md`

## Self-review

- Debug Settings retains the exact existing Board packages heading and Board editor link.
- Release compiles out the entire Board packages section; it therefore exposes neither the heading nor link.
- The existing DEBUG-only review-route state and destination were intentionally left unchanged.
- No account, authentication, GitHub, or board-editor behavior was changed.
- The UI test mutates the intended production behavior: removing the Debug guard makes the Release assertion fail, while hiding the block in Debug makes the Debug assertion fail.

## Concerns

Xcode’s package-resolution process exits before producing any build or XCTest output in this environment, so fresh Debug/Release build and test execution remains unverified here. The exact test and build commands above should be rerun where package resolution completes.
