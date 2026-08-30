# Hangboard Issue Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any iOS or Android user report a hangboard issue through a Tally form that creates a labelled GitHub issue without requiring the reporter to have GitHub.

**Architecture:** A blocking catalog audit independently verifies every physical board presentation against current first-party evidence before either client exposes it. Both clients then build the same URL-encoded Tally form URL from the audited physical-presentation context and open it in the system browser from an equivalent board-details destination. The published form URL is an opt-in build configuration value; empty or invalid configuration keeps the action unavailable. Tally reCAPTCHA and a two-step Tally-to-GitHub Zap own public submission and issue creation.

**Tech Stack:** SwiftUI/XCTest, Android Jetpack Compose/JUnit/Compose UI tests, Tally, Zapier, GitHub Issues.

**Spec:** `docs/superpowers/specs/2026-08-30-hangboard-issue-reporting-design.md`

## Global Constraints

- Ship the equivalent report capability and board-details destination in iOS and Android; do not ship an iOS-only or reduced Android path.
- Reports are text-only: no screenshots, uploads, reporter account data, device IDs, location, or workout history.
- The repository is a candidate inventory only: independently discovered current manufacturer pages, galleries, manuals, hold guides, and directly linked assets are the sole authority for physical orientation and hold-to-presentation mapping.
- Hidden form fields are exactly `board_id`, `board_name`, `manufacturer`, `presentation_id`, `presentation_name`, `platform`, `app_version`, and `build`.
- Tally form URL values must be HTTPS, hosted by `tally.so` or a `*.tally.so` subdomain, and URL-encoded through platform URL APIs.
- The report control is unavailable for blank or invalid form configuration; a valid URL launch failure is retryable and user-visible.
- Every source-supported multi-presentation board lets a reporter select the current face/variant; both portrait and landscape retain access to the selector and report action. Phone orientation is a layout test concern and is never report payload data.
- GitHub target is `Asherlc/hang-ten`; every created report receives the `hangboard-report` label.
- Run tests before every commit and push every new commit to `origin`.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `HangTen/Models/HangboardIssueReport.swift` | iOS report context, configuration validation, and Tally URL builder. |
| `HangTenTests/HangboardIssueReportTests.swift` | iOS URL contract and invalid-config regression tests. |
| `HangTen/Views/TrainView.swift` | iOS detail-page presentation binding and browser hand-off/error UI. |
| `HangTenTests/BoardDetailTests.swift` | iOS presentation-selection and report-control visibility tests. |
| `HangTen/Config/Analytics.xcconfig` | Default empty iOS report-form configuration. |
| `HangTen.xcodeproj/project.pbxproj` | Exposes the iOS setting through `Info.plist` in Debug and Release. |
| `Android/app/build.gradle.kts` | Reads and validates `HANGBOARD_REPORT_FORM_URL` into `BuildConfig`. |
| `Android/app/src/main/java/com/hangten/android/report/HangboardIssueReport.kt` | Android report context, configuration validation, and Tally URL builder. |
| `Android/app/src/test/java/com/hangten/android/report/HangboardIssueReportTest.kt` | Android URL contract and invalid-config regression tests. |
| `Android/app/src/main/java/com/hangten/android/board/BoardCanvas.kt` | Renders and hit-tests an explicitly selected presentation. |
| `Android/app/src/main/java/com/hangten/android/ui/BoardDetailsScreen.kt` | Android equivalent board-details screen, variant control, layout adaptation, and report action. |
| `Android/app/src/main/java/com/hangten/android/ui/HangTenApp.kt` | Adds the board-details route and report URL hand-off. |
| `Android/app/src/main/java/com/hangten/android/ui/TrainScreen.kt` | Links the selected-board card to board details. |
| `Android/app/src/androidTest/java/com/hangten/android/ui/BoardDetailsScreenTest.kt` | Android portrait/landscape and variant/report-entry Compose tests. |
| `docs/hangboard-issue-reporting.md` | Tally, Zapier, GitHub-label provisioning and smoke-test runbook. |
| `README.md` | Links maintainers to the runbook and documents required release configuration. |
| `docs/source-audits/2026-08-30-independent-catalog-orientation-audit.md` | First-party source ledger for every candidate package, its physical revision, supported presentations, and any source-limited omissions. |
| `Tools/HangboardPackages/tests/test_catalog_orientation_audit.py` | Ensures the independent audit accounts for every discovered package and cites primary evidence for every declared presentation. |

### Task 1: Independently audit catalog presentations and physical orientations

**Files:**
- Create: `docs/source-audits/2026-08-30-independent-catalog-orientation-audit.md`
- Create: `Tools/HangboardPackages/tests/test_catalog_orientation_audit.py`
- Modify: `Hangboards/<slug>/board.json` only where independent primary evidence proves a missing, incorrect, or unsupported presentation/hold assignment.

**Interfaces:**
- Produces: one source-audit record per discovered `Hangboards/<slug>/board.json`, containing `package`, `physical revision`, `reviewed date`, `first-party product URL`, `all reviewed first-party image/manual URLs`, `supported presentations`, `hold-to-presentation mapping`, and `source limitation`.
- Produces: corrected `board.json.presentations` and `hold.presentationID` values only after the record establishes the physical orientation.
- Consumes: no repository asset, JSON field, or previous source-audit claim as evidence; use them only to ensure every candidate receives a fresh audit.

- [ ] **Step 1: Write the failing audit-coverage test**

Create a test that discovers all direct `Hangboards/*/board.json` packages, parses the audit's one-row-per-package table, and fails if a package is missing, duplicated, lacks an HTTPS first-party source URL, or a declared presentation lacks an explicit evidence row. The test must not validate factual orientation claims from repository values; it validates that every review target has independently recorded evidence.

```python
def test_orientation_audit_covers_every_discovered_package() -> None:
    packages = {path.parent.name for path in (ROOT / "Hangboards").glob("*/board.json")}
    records = parse_orientation_audit(ROOT / "docs/source-audits/2026-08-30-independent-catalog-orientation-audit.md")
    assert set(records) == packages
    for record in records.values():
        assert record.primary_urls
        assert all(url.startswith("https://") for url in record.primary_urls)
        assert record.presentation_evidence or record.limitation
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `rtk pytest Tools/HangboardPackages/tests/test_catalog_orientation_audit.py -q`

Expected: failure because the independent audit and parser do not exist.

- [ ] **Step 3: Conduct and record the independent evidence review**

For every candidate product, use web search to independently locate the current manufacturer product page; open its complete gallery, every first-party image variant, downloadable manual, numbered hold guide, and linked product media. Review every visual manually. Record the exact URLs and image role, physical revision, and whether each face, reverse, side, inversion, rotation, or mounting orientation is source-supported. A hold visible and usable only after changing a board's physical orientation must be assigned to that explicit presentation. When evidence does not establish a claimed orientation or hold mapping, state that limitation and remove or omit the unsupported presentation rather than guessing.

Keep different physical revisions in separate packages. Keep sourced faces, sides, and mounting orientations of one revision in one package. Directly author or correct canonical paths only when primary evidence establishes the physical contact; do not use automated image detection, tracing, segmentation, registration, or vectorization.

- [ ] **Step 4: Run audit and package validation**

Run: `rtk pytest Tools/HangboardPackages/tests/test_catalog_orientation_audit.py -q && rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory && rtk scripts/hangboard-packages.sh status --root Hangboards`

Expected: audit coverage passes, package validation reports no unsupported package structure, and status reports no drafts.

- [ ] **Step 5: Manually review every changed presentation in Workbench and the app**

Start the Workbench with `rtk python Tools/HangboardWorkbench/server.py`, inspect every changed presentation's normal, active, and hit-test paths, then run the iOS and Android visual test flows for those exact presentations. Store only temporary review output under `.context`; shut down each exact local resource when review completes.

- [ ] **Step 6: Commit and push**

```bash
git add Hangboards docs/source-audits/2026-08-30-independent-catalog-orientation-audit.md Tools/HangboardPackages/tests/test_catalog_orientation_audit.py
git commit -m "Audit catalog hangboard orientations"
git push origin HEAD
```

### Task 2: Create the report form and issue automation runbook

**Files:**
- Create: `docs/hangboard-issue-reporting.md`
- Modify: `README.md: GitHub Device Flow release setup section`

**Interfaces:**
- Produces: published Tally form URL and the documented, immutable field mapping consumed by the two client builders.
- Produces: a manual acceptance procedure that proves a completed Tally submission creates a `hangboard-report` issue in `Asherlc/hang-ten`.

- [ ] **Step 1: Write the failing documentation-contract test**

Add a focused shell assertion in `scripts/tests/hangboard-issue-reporting-doc-test.zsh` that fails until the runbook includes every required hidden key, the three visible fields, `reCAPTCHA`, `Asherlc/hang-ten`, and `hangboard-report`.

```zsh
required=(board_id board_name manufacturer presentation_id presentation_name platform app_version build)
for key in $required; do
  rg -q "\`$key\`" docs/hangboard-issue-reporting.md || exit 1
done
rg -q 'Incorrect hold/specification' docs/hangboard-issue-reporting.md || exit 1
rg -q 'Missing or incorrect board' docs/hangboard-issue-reporting.md || exit 1
rg -q 'hangboard-report' docs/hangboard-issue-reporting.md || exit 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `zsh scripts/tests/hangboard-issue-reporting-doc-test.zsh`

Expected: failure because the runbook does not exist.

- [ ] **Step 3: Write the runbook and README link**

Document these exact operations:

1. In Tally, create a published form titled `Report a Hang Ten hangboard issue`.
2. Create required visible fields: category single-choice with the three spec values, title short-text, and description long-text. Add `/recaptcha` immediately above Submit.
3. Add the eight hidden fields named exactly as listed in Global Constraints; do not expose them as editable questions.
4. In GitHub, create the `hangboard-report` label in `Asherlc/hang-ten`.
5. In Zapier, create the free two-step Zap: **Tally — New Submission** then **GitHub — Create Issue**. Map title to the issue title; map category, description, and every hidden field into a Markdown body; apply `hangboard-report`.
6. Use a maintainer-owned GitHub connection with only the repository issue permission required. Never put a GitHub token in either app or this repository.
7. Set the public published Tally URL as `HANGBOARD_REPORT_FORM_URL` for iOS and Android release builds. Treat it as public configuration, not a secret.
8. Submit a test response for an audited multi-face board and record the resulting issue URL; confirm the label and all eight context values.

Add a README subsection linking to the runbook next to the existing release-configuration guidance.

- [ ] **Step 4: Run the documentation test to verify it passes**

Run: `zsh scripts/tests/hangboard-issue-reporting-doc-test.zsh`

Expected: exit 0.

- [ ] **Step 5: Commit and push**

```bash
git add docs/hangboard-issue-reporting.md scripts/tests/hangboard-issue-reporting-doc-test.zsh README.md
git commit -m "Document hangboard issue reporting setup"
git push origin HEAD
```

### Task 3: Add the iOS report URL contract and configuration

**Files:**
- Create: `HangTen/Models/HangboardIssueReport.swift`
- Create: `HangTenTests/HangboardIssueReportTests.swift`
- Modify: `HangTen/Config/Analytics.xcconfig`
- Modify: `HangTen.xcodeproj/project.pbxproj: Debug and Release HangTen build settings`

**Interfaces:**
- Produces: `HangboardIssueReportContext(board:presentationID:presentationName:interfaceOrientation:platform:appVersion:build:)`.
- Produces: `HangboardIssueReportURL.make(formURL:context:) -> URL?`, returning `nil` unless `formURL` is an HTTPS `tally.so` URL.
- Produces: `HangboardIssueReportConfiguration.formURL(bundle:) -> URL?`, reading `HANGBOARD_REPORT_FORM_URL` from `Info.plist`.

- [ ] **Step 1: Write failing XCTest cases**

Create tests using a fixture board named `Pocket & Edge` and presentation `Face B — deep slopers`. Assert the generated URL preserves the base path and has exact decoded query values for every Global Constraint key, including `platform=iOS`. Add tests returning `nil` for empty, `http://`, `https://example.com`, and malformed values.

```swift
func testMakeEncodesEveryReportContextValue() throws {
    let url = try XCTUnwrap(HangboardIssueReportURL.make(
        formURL: URL(string: "https://tally.so/r/report")!,
        context: fixtureContext()
    ))
    let values = Dictionary(uniqueKeysWithValues: try XCTUnwrap(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems).map { ($0.name, $0.value) })
    XCTAssertEqual(values["board_name"], "Pocket & Edge")
    XCTAssertEqual(values["presentation_name"], "Face B — deep slopers")
    XCTAssertEqual(values["platform"], "iOS")
}
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/HangboardIssueReportTests`

Expected: compilation failure because the report types do not exist.

- [ ] **Step 3: Implement the minimal typed builder and build configuration**

Use `URLComponents` and `URLQueryItem` rather than manual string concatenation. Read app version/build from `CFBundleShortVersionString`/`CFBundleVersion`, defaulting to `"unknown"` only when the bundle values are absent. Set `HANGBOARD_REPORT_FORM_URL =` in `Analytics.xcconfig` and add `INFOPLIST_KEY_HANGBOARD_REPORT_FORM_URL = "$(HANGBOARD_REPORT_FORM_URL)"` to both target configurations.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/HangboardIssueReportTests`

Expected: all `HangboardIssueReportTests` pass.

- [ ] **Step 5: Commit and push**

```bash
git add HangTen/Models/HangboardIssueReport.swift HangTenTests/HangboardIssueReportTests.swift HangTen/Config/Analytics.xcconfig HangTen.xcodeproj/project.pbxproj
git commit -m "Add iOS hangboard issue report URLs"
git push origin HEAD
```

### Task 4: Add the iOS detail-page report action for every audited presentation

**Files:**
- Modify: `HangTen/Views/TrainView.swift: BoardDetailView`
- Modify: `HangTen/Views/BoardMapView.swift: BoardDetailMapView`
- Create: `HangTenTests/BoardDetailTests.swift`
- Modify: `HangTenUITests/OwlClimbPokerBoardMapInteractionUITests.swift`

**Interfaces:**
- Consumes: `HangboardIssueReportConfiguration.formURL(bundle:)` and `HangboardIssueReportURL.make(formURL:context:)` from Task 3.
- Produces: `BoardDetailMapView(..., selectedPresentationID: Binding<String>)`, allowing `BoardDetailView` to include the active presentation in the report context.

- [ ] **Step 1: Write failing unit and UI tests**

Add pure `BoardDetailView` presentation tests proving that a selected Face B produces `presentation_id=face-b`. Extend the existing Poker UI flow: select Face B, assert a `boardDetail.reportIssue` control is visible when a test configuration is provided, rotate the simulator to landscape, and assert both `boardDetail.presentationSelector` and `boardDetail.reportIssue` remain hittable.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardDetailTests -only-testing:HangTenUITests/OwlClimbPokerBoardMapInteractionUITests`

Expected: test failure because no bound presentation state or report action exists.

- [ ] **Step 3: Implement the action and lift presentation state**

Move the selected presentation ID from `BoardDetailMapView` into `BoardDetailView` as `@State`, initialize it from the board default, and bind it through the map view. Preserve current hold-selection behavior when a new face is selected. Add the report button below the map/hold card only when `HangboardIssueReportConfiguration.formURL(bundle:)` succeeds. Use `@Environment(\.openURL)`; on `.discarded` show a SwiftUI alert with “Couldn’t open the report form” and a Retry action. Include selected presentation and current interface orientation in the context. Give the button `boardDetail.reportIssue`.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardDetailTests -only-testing:HangTenUITests/OwlClimbPokerBoardMapInteractionUITests`

Expected: all selected iOS tests pass in portrait and landscape.

- [ ] **Step 5: Commit and push**

```bash
git add HangTen/Views/TrainView.swift HangTen/Views/BoardMapView.swift HangTenTests/BoardDetailTests.swift HangTenUITests/OwlClimbPokerBoardMapInteractionUITests.swift
git commit -m "Add iOS hangboard issue reporting"
git push origin HEAD
```

### Task 5: Add the Android report URL contract and build configuration

**Files:**
- Modify: `Android/app/build.gradle.kts`
- Create: `Android/app/src/main/java/com/hangten/android/report/HangboardIssueReport.kt`
- Create: `Android/app/src/test/java/com/hangten/android/report/HangboardIssueReportTest.kt`

**Interfaces:**
- Produces: `HangboardIssueReportContext` with the same eight field values as Task 3.
- Produces: `HangboardIssueReportUrl.make(formUrl: String, context: HangboardIssueReportContext): Uri?`.
- Produces: `BuildConfig.HANGBOARD_REPORT_FORM_URL` from the optional Gradle property of the same name.

- [ ] **Step 1: Write failing JUnit cases**

Create the same `Pocket & Edge` / `Face B — deep slopers` fixture. Parse the resulting Android `Uri`, assert every query parameter exactly matches the fixture, and assert invalid blank, HTTP, non-Tally host, and malformed URLs return `null`.

```kotlin
@Test fun encodesAllContextFieldsForFaceB() {
    val url = assertNotNull(HangboardIssueReportUrl.make("https://tally.so/r/report", fixtureContext()))
    assertEquals("Pocket & Edge", url.getQueryParameter("board_name"))
    assertEquals("Face B — deep slopers", url.getQueryParameter("presentation_name"))
    assertEquals("Android", url.getQueryParameter("platform"))
}
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `cd Android && ./gradlew testDebugUnitTest --tests com.hangten.android.report.HangboardIssueReportTest`

Expected: compilation failure because the report package and BuildConfig field do not exist.

- [ ] **Step 3: Implement the minimal builder and configuration**

Read `HANGBOARD_REPORT_FORM_URL` with `providers.gradleProperty(...).orElse("")`. Reuse the existing `asBuildConfigString()` helper after validating that any nonblank value parses as HTTPS and the host equals `tally.so` or ends in `.tally.so`. Build query parameters with `Uri.Builder.appendQueryParameter`; never interpolate unescaped user or board text.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `cd Android && ./gradlew testDebugUnitTest --tests com.hangten.android.report.HangboardIssueReportTest`

Expected: all report URL unit tests pass.

- [ ] **Step 5: Commit and push**

```bash
git add Android/app/build.gradle.kts Android/app/src/main/java/com/hangten/android/report/HangboardIssueReport.kt Android/app/src/test/java/com/hangten/android/report/HangboardIssueReportTest.kt
git commit -m "Add Android hangboard issue report URLs"
git push origin HEAD
```

### Task 6: Add Android board details with presentation parity and the report action

**Files:**
- Modify: `Android/app/src/main/java/com/hangten/android/board/BoardCanvas.kt`
- Create: `Android/app/src/main/java/com/hangten/android/ui/BoardDetailsScreen.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/ui/HangTenApp.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/ui/TrainScreen.kt`
- Create: `Android/app/src/androidTest/java/com/hangten/android/ui/BoardDetailsScreenTest.kt`

**Interfaces:**
- Consumes: `HangboardIssueReportUrl.make` and `BuildConfig.HANGBOARD_REPORT_FORM_URL` from Task 5.
- Produces: `BoardCanvas(..., presentationId: String, ...)`, preserving default-presentation behavior for existing callers with a default argument.
- Produces: `BoardDetailsScreen(board: Board, onOpenReport: (Uri) -> Unit, ...)` with an equivalent board-specific report action.

- [ ] **Step 1: Write failing Compose tests**

Use a fixture board with `face-a` and `face-b` presentations. Assert that the Board Details route opens from Train, the selector exposes both faces, choosing Face B changes the selected semantics, and `Report a hangboard issue` is displayed and clickable only with a valid Tally URL. Use `DeviceConfigurationOverride` (or a separate landscape activity configuration) to assert the face selector and report action are visible in landscape. Capture the opened `Uri` through a lambda and assert it includes `presentation_id=face-b`, `platform=Android`, and both orientation values in separate tests.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `cd Android && ./gradlew connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.hangten.android.ui.BoardDetailsScreenTest`

Expected: failures because no route, selector-aware canvas, or report action exists.

- [ ] **Step 3: Implement the parity screen and navigation**

1. Add `BoardDetails` to `HangTenDestination`; route from the Train selected-board card with a `View board details` control.
2. Refactor `BoardCanvas` to take `presentationId`, select the matching `BoardPresentation`, use that image path, and filter hit-testing/rendering to that exact presentation.
3. In `BoardDetailsScreen`, initialize state from the default presentation, render a Material 3 single-choice presentation selector only when there is more than one presentation, render `BoardCanvas` for that state, and show the selected hold name.
4. Use `BoxWithConstraints` to make the selector/content a row on wide landscape and a column on portrait; keep the report action after the content in both layouts.
5. Build the report context from the selected board/presentation, `resources.configuration.orientation`, `BuildConfig.VERSION_NAME`, and `BuildConfig.VERSION_CODE`; launch it with `Intent(Intent.ACTION_VIEW, uri)`. If `resolveActivity` is null or `startActivity` throws, show a Compose snackbar with a Retry button.
6. Hide the report action when `HangboardIssueReportUrl.make` returns null.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `cd Android && ./gradlew connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.hangten.android.ui.BoardDetailsScreenTest`

Expected: all board-details tests pass for multi-face boards in portrait and landscape.

- [ ] **Step 5: Commit and push**

```bash
git add Android/app/src/main/java/com/hangten/android/board/BoardCanvas.kt Android/app/src/main/java/com/hangten/android/ui/BoardDetailsScreen.kt Android/app/src/main/java/com/hangten/android/ui/HangTenApp.kt Android/app/src/main/java/com/hangten/android/ui/TrainScreen.kt Android/app/src/androidTest/java/com/hangten/android/ui/BoardDetailsScreenTest.kt
git commit -m "Add Android hangboard issue reporting"
git push origin HEAD
```

### Task 7: Run cross-platform verification and provision the published form

**Files:**
- Modify: `docs/hangboard-issue-reporting.md` only to record the Tally form URL, Zap name, and the test issue URL after successful manual validation.

**Interfaces:**
- Consumes: the completed client URL builders and published Tally configuration from Tasks 1–5.
- Produces: fresh evidence that iOS and Android can report every board presentation from portrait and landscape.

- [ ] **Step 1: Run the complete iOS test suite**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'`

Expected: exit 0 with no XCTest failures.

- [ ] **Step 2: Run the complete Android unit and instrumentation suites**

Run: `cd Android && ./gradlew testDebugUnitTest connectedDebugAndroidTest`

Expected: exit 0 with no failing tests.

- [ ] **Step 3: Perform the external acceptance test**

Configure both release-equivalent builds with the published `HANGBOARD_REPORT_FORM_URL`. From an audited board with multiple presentations, submit one report for each selected physical presentation from each platform. Verify Tally reCAPTCHA succeeds, GitHub creates an issue in `Asherlc/hang-ten`, the `hangboard-report` label is present, and all eight hidden fields match the selected face and client configuration. Separately verify portrait and landscape layouts preserve the selector and report action.

- [ ] **Step 4: Re-run documentation test and inspect the diff**

Run: `zsh scripts/tests/hangboard-issue-reporting-doc-test.zsh && git diff --check && git status --short`

Expected: documentation test and whitespace check exit 0; status contains only intended runbook evidence changes.

- [ ] **Step 5: Commit and push the recorded acceptance evidence**

```bash
git add docs/hangboard-issue-reporting.md
git commit -m "Verify hangboard issue reporting flow"
git push origin HEAD
```
