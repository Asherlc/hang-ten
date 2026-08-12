# Hang Ten PostHog Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add anonymous, protected PostHog observability and OpenTelemetry diagnostics to Hang Ten without coupling features to vendor APIs.

**Architecture:** A typed telemetry boundary in HangTen/Models is injected into AppStore. PostHogTelemetry owns PostHog interaction; OpenTelemetryDiagnostics owns standard trace export. Both are composed once in HangTenApp. Views and domain models use only the boundary.

**Tech Stack:** Swift 5, SwiftUI, XCTest, Swift Package Manager, posthog-ios 3.59.3+, OpenTelemetry Swift 2.3.0+, OTLP/HTTP.

## Global Constraints

- Create a new Hang Ten PostHog project in the connected default organization; no project token or API key may be committed.
- Never call identify or set person properties.
- Never emit HealthKit samples, historical workout data, Bluetooth names/addresses/identifiers/raw force readings, plan identifiers/titles, custom-routine contents, free text, exact timestamps, exact durations, network bodies, or image content.
- Events are restricted to the approved names and categorical properties in docs/superpowers/specs/2026-08-11-posthog-observability-design.md.
- The only events are app tab selected(tab: today|plans|progress), plan browsed(source: catalog|favorite|custom), workout started(source: catalog|favorite|custom), workout finished(outcome: completed|abandoned; duration_bucket: under_5_minutes|5_to_10_minutes|10_to_15_minutes|15_plus_minutes), board selected(board_family), custom routine saved(no properties), health authorization finished(outcome: granted|denied|unavailable|error), motherboard connection finished(outcome: connected|failed|disconnected), and app diagnostic recorded(category|operation|error_kind).
- Replay uses wireframe mode, masks inputs and images, does not capture logs or network telemetry, and is paused during active workouts and HealthKit authorization.
- Telemetry failures must be non-fatal and must not block launch, workouts, persistence, Bluetooth, or HealthKit.
- Views and existing domain models must not import PostHog or OpenTelemetry.
- Product events and native replay/error tracking remain behind the PostHog adapter; diagnostics use OpenTelemetry API and OTLP transport where applicable.
- Use .context/DerivedData for every Xcode build and test.

---

## File Structure

| File | Responsibility |
| --- | --- |
| HangTen/Models/Telemetry.swift | Typed vocabulary, redaction-safe properties, protocols, no-op adapter, duration bucketing. |
| HangTen/Models/PostHogTelemetry.swift | Token validation, PostHog configuration, event translation, replay/flag/error adapter. |
| HangTen/Models/OpenTelemetryDiagnostics.swift | Standard tracer setup and redacted diagnostic-span export. |
| HangTen/Config/PostHog.xcconfig | Safe defaults plus optional local configuration include. |
| HangTen/Config/PostHog.local.xcconfig.example | Copyable token/host template; real sibling is ignored. |
| HangTen/HangTenApp.swift | Compose telemetry once and inject it into AppStore. |
| HangTen/Models/AppStore.swift | Emit approved events at business-operation boundaries. |
| HangTen/Models/MotherboardBluetoothService.swift | Emit categorical Motherboard connection outcomes through the portable contract. |
| HangTen/Views/RootView.swift | Emit navigation/workout lifecycle through AppStore and pause replay. |
| HangTenTests/TelemetryTests.swift | Contract, redaction, no-op, bucketing, and adapter tests. |
| HangTenTests/AppStoreTests.swift | App operation telemetry tests. |
| HangTenTests/MotherboardBluetoothServiceTests.swift | Connection outcome telemetry tests. |
| HangTen.xcodeproj/project.pbxproj | Target membership, SPM packages, config refs, and generated plist keys. |
| .gitignore and README.md | Token protection and operator instructions. |
| .github/workflows/ci.yml and .github/workflows/release.yml | Secure CI/release build-setting injection. |

### Task 1: Establish the portable telemetry contract

**Files:**
- Create: HangTen/Models/Telemetry.swift
- Create: HangTenTests/TelemetryTests.swift
- Modify: HangTen.xcodeproj/project.pbxproj

**Interfaces:**
- Produces TelemetryTracking.track(_:), DiagnosticReporting.record(_:), FeatureFlagProviding.isEnabled(_:default:), and SessionReplayControlling.start()/stop().
- Produces HangTenTelemetryEvent with only the nine approved event names/properties.
- Produces NoOpTelemetry, which conforms to all four protocols without side effects.

- [ ] **Step 1: Write the failing telemetry-contract tests**

~~~swift
func testWorkoutFinishedUsesOnlyOutcomeAndCoarseDurationBucket() {
    let event = HangTenTelemetryEvent.workoutFinished(
        outcome: .completed,
        elapsed: 731
    )

    XCTAssertEqual(event.name, "workout finished")
    XCTAssertEqual(event.properties, [
        "outcome": "completed",
        "duration_bucket": "10_to_15_minutes"
    ])
    XCTAssertFalse(event.properties.values.contains("731"))
}

func testNoOpTelemetryHasNoRecordedSideEffects() {
    let telemetry = NoOpTelemetry()
    telemetry.track(.customRoutineSaved)
    telemetry.record(.init(category: .persistence, operation: "save", error: TestError()))
    XCTAssertFalse(telemetry.isEnabled("future-flag", default: false))
}
~~~

- [ ] **Step 2: Run the focused test to verify it fails**

Run: xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/TelemetryTests

Expected: compilation fails because HangTenTelemetryEvent and NoOpTelemetry do not exist.

- [ ] **Step 3: Implement the minimal contract**

~~~swift
protocol TelemetryTracking: AnyObject {
    func track(_ event: HangTenTelemetryEvent)
}

protocol DiagnosticReporting: AnyObject {
    func record(_ diagnostic: HangTenDiagnostic)
}

protocol FeatureFlagProviding: AnyObject {
    func isEnabled(_ key: String, default defaultValue: Bool) -> Bool
}

protocol SessionReplayControlling: AnyObject {
    func start()
    func stop()
}
~~~

Define finite enums for every allowed property. Map elapsed seconds to under_5_minutes, 5_to_10_minutes, 10_to_15_minutes, or 15_plus_minutes; never expose elapsed seconds. Define HangTenDiagnostic with only categorical category, operation, and errorKind; derive kind from error type, never localizedDescription. Make NoOpTelemetry conform to all contracts and return the caller-supplied flag default.

- [ ] **Step 4: Add target membership and run focused tests**

Run: xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/TelemetryTests

Expected: all TelemetryTests pass without a telemetry SDK.

- [ ] **Step 5: Commit**

~~~bash
git add HangTen/Models/Telemetry.swift HangTenTests/TelemetryTests.swift HangTen.xcodeproj/project.pbxproj
git commit -m "feat: add portable telemetry contract"
~~~

### Task 2: Add isolated PostHog and OpenTelemetry adapters

**Files:**
- Create: HangTen/Models/PostHogTelemetry.swift
- Create: HangTen/Models/OpenTelemetryDiagnostics.swift
- Create: HangTen/Config/PostHog.xcconfig
- Create: HangTen/Config/PostHog.local.xcconfig.example
- Modify: .gitignore, HangTen/HangTenApp.swift, HangTen.xcodeproj/project.pbxproj, HangTenTests/TelemetryTests.swift

**Interfaces:**
- Consumes Task 1 contracts without extending the event/property vocabulary.
- Produces TelemetryComposition.make(bundle:) -> TelemetryDependencies. Its exact stored properties are tracking: any TelemetryTracking, diagnostics: any DiagnosticReporting, flags: any FeatureFlagProviding, replay: any SessionReplayControlling, and isNoOp: Bool.
- PostHogTelemetry is the only type importing PostHog; OpenTelemetryDiagnostics is the only type importing OpenTelemetry modules.

- [ ] **Step 1: Write failing adapter/configuration tests**

~~~swift
func testConfigurationWithoutAProjectTokenBuildsNoOpDependencies() {
    let configuration = PostHogConfiguration(
        projectToken: "$(POSTHOG_CLIENT_TOKEN)",
        host: ""
    )

    XCTAssertFalse(configuration.isConfigured)
    XCTAssertTrue(TelemetryComposition.make(configuration: configuration).isNoOp)
}

func testPostHogAdapterTranslatesOnlyTypedProperties() {
    let client = RecordingPostHogClient()
    let telemetry = PostHogTelemetry(client: client)

    telemetry.track(.boardSelected(family: .motherboard))

    XCTAssertEqual(client.captures, [
        ("board selected", ["board_family": "motherboard"])
    ])
}
~~~

- [ ] **Step 2: Run focused tests to verify the adapters are absent**

Run: xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/TelemetryTests

Expected: compilation fails because PostHogConfiguration, TelemetryComposition, and PostHogTelemetry do not exist.

- [ ] **Step 3: Add packages and safe configuration plumbing**

Add PostHog from https://github.com/PostHog/posthog-ios.git at 3.59.3+ and the OpenTelemetry API, SDK, and HTTP OTLP exporter products from https://github.com/open-telemetry/opentelemetry-swift.git at 2.3.0+ to the app target. Add POSTHOG_CLIENT_TOKEN and POSTHOG_HOST Info.plist keys in both app configurations. Reference the tracked config below, and ignore only the real local override.

~~~xcconfig
POSTHOG_CLIENT_TOKEN =
POSTHOG_HOST = https://us.i.posthog.com
#include? "PostHog.local.xcconfig"
~~~

- [ ] **Step 4: Implement non-fatal, privacy-safe adapters**

Configure PostHog only when the token begins phc_. Configure anonymous replay in wireframe mode with maskAllTextInputs = true, maskAllImages = true, replay log capture off, replay network telemetry off, and exception autocapture on. Translate events through internal PostHogCapturing so tests use RecordingPostHogClient, not SDK internals. Missing/failed flags return the caller default.

Configure OTel with service name com.hangten.training and an OTLP/HTTP exporter for the configured PostHog trace endpoint plus project-token authorization. Export only typed diagnostic category, operation, and error-kind attributes. Missing/invalid configuration or setup failure keeps diagnostics no-op and never throws from launch.

- [ ] **Step 5: Compose once and verify packages + tests**

~~~swift
let telemetry = TelemetryComposition.make(bundle: .main)
_store = StateObject(wrappedValue: AppStore(
    motherboardBluetoothService: motherboardBluetoothService,
    motherboardSettingsStore: motherboardSettingsStore,
    workoutSessionStore: workoutSessionStore,
    telemetry: telemetry
))
~~~

Run: xcodebuild -resolvePackageDependencies -project HangTen.xcodeproj -scheme HangTen -derivedDataPath .context/DerivedData && xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/TelemetryTests

Expected: packages resolve; both configured and no-op paths pass.

- [ ] **Step 6: Commit**

~~~bash
git add HangTen/Models/PostHogTelemetry.swift HangTen/Models/OpenTelemetryDiagnostics.swift HangTen/Config .gitignore HangTen/HangTenApp.swift HangTen.xcodeproj/project.pbxproj HangTenTests/TelemetryTests.swift
git commit -m "feat: configure PostHog telemetry adapters"
~~~

### Task 3: Emit approved business events and protect sensitive replay

**Files:**
- Modify: HangTen/Models/AppStore.swift
- Modify: HangTen/Models/MotherboardBluetoothService.swift
- Modify: HangTen/Views/RootView.swift
- Modify: HangTenTests/AppStoreTests.swift
- Modify: HangTenTests/MotherboardBluetoothServiceTests.swift
- Modify: HangTenTests/TelemetryTests.swift

**Interfaces:**
- Consumes TelemetryDependencies via AppStore(telemetry:).
- Produces AppStore.selectBoard(_:), recordTabSelection(_:), recordPlanBrowse(_:), recordWorkoutStarted(source:), recordWorkoutFinished(outcome:elapsed:), and replay-safe HealthKit lifecycle methods.
- Produces MotherboardBluetoothService(telemetry:) with a no-op default and only categorical connection outcomes.
- Views call only AppStore methods; no view imports a telemetry dependency.

- [ ] **Step 1: Write failing operation-boundary tests with a recording fake**

~~~swift
func testCompletedWorkoutEmitsOnlySourceOutcomeAndDurationBucket() {
    let telemetry = RecordingTelemetry()
    let store = makeStore(telemetry: telemetry)

    store.markSessionComplete(
        PlanCatalog.all[0],
        startDate: Date(timeIntervalSinceReferenceDate: 1_000),
        endDate: Date(timeIntervalSinceReferenceDate: 1_731)
    )

    XCTAssertEqual(telemetry.events.last?.name, "workout finished")
    XCTAssertNil(telemetry.events.last?.properties["plan_id"])
    XCTAssertNil(telemetry.events.last?.properties["duration_seconds"])
}
~~~

Also test tab selection, board selection, custom-routine persistence success, categorical HealthKit authorization outcome, categorical Motherboard connection outcome, replay stop at workout start and HealthKit request, plus replay restart after sensitive-flow dismissal.

- [ ] **Step 2: Run focused tests to verify behavior is absent**

Run: xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/AppStoreTests -only-testing:HangTenTests/TelemetryTests

Expected: tests fail because AppStore does not accept or use telemetry.

- [ ] **Step 3: Inject contracts and emit events at boundaries**

Inject a no-op-default telemetry dependency into AppStore and MotherboardBluetoothService. Compose telemetry before creating the Bluetooth service in HangTenApp, then pass telemetry.tracking into the service. Replace the sole direct board assignment in RootView with store.selectBoard(_:). Record tabs on selection change, plan browsing on navigation entry, custom-routine saves only after persistence succeeds, workout start at the first active session transition, completed workout after saved-session completion, and abandoned workout when an active session ends without completion. Use only source/outcome/coarse bucket values. Stop replay before workout presentation and HealthKit authorization, and restart after the sensitive flow ends.

Record categorical diagnostics at existing persistence, HealthKit, and Motherboard failures using error types only. Do not send localized descriptions or model objects.

- [ ] **Step 4: Run focused tests and full unit suite**

Run: xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test

Expected: all unit tests pass; event tests prove prohibited properties are absent.

- [ ] **Step 5: Commit**

~~~bash
git add HangTen/Models/AppStore.swift HangTen/Models/MotherboardBluetoothService.swift HangTen/Views/RootView.swift HangTenTests/AppStoreTests.swift HangTenTests/MotherboardBluetoothServiceTests.swift HangTenTests/TelemetryTests.swift
git commit -m "feat: instrument anonymous app lifecycle events"
~~~

### Task 4: Configure the PostHog project and verify end-to-end behavior

**Files:**
- Modify: README.md
- Modify locally only: HangTen/Config/PostHog.local.xcconfig

**Interfaces:**
- Consumes the newly created project token and ingestion host.
- Produces the Hang Ten App Health dashboard: anonymous opens, workout funnel, error-tracking view.

- [ ] **Step 1: Create/configure the PostHog project**

In the authenticated default organization create Hang Ten. Enable session recording and iOS exception autocapture. Keep replay masked with no replay logs/network telemetry. Create no targeting rules, experiments, surveys, or behavior-changing flags.

- [ ] **Step 2: Configure the ignored local client settings**

~~~xcconfig
// HangTen/Config/PostHog.local.xcconfig
POSTHOG_CLIENT_TOKEN = phc_replace_with_the_hang_ten_project_token
POSTHOG_HOST = https://replace_with_the_project_ingestion_host
~~~

Run: git check-ignore -v HangTen/Config/PostHog.local.xcconfig

Expected: the real local token file is ignored and never staged.

- [ ] **Step 3: Build, launch, and create representative anonymous telemetry**

Run: xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData build

Launch on an isolated simulator; select tabs, browse a plan, start/exit a workout, and attempt HealthKit authorization. Confirm replay is unavailable during workout and HealthKit surfaces but available during normal navigation.

- [ ] **Step 4: Verify ingestion and create the dashboard**

Confirm PostHog contains only anonymous lifecycle events/allowed categorical properties, protected replay behavior, and exception capture. Create Hang Ten App Health with application opens, a workout started to completed workout finished funnel, and error-tracking / app diagnostic recorded tiles.

- [ ] **Step 5: Document and commit repository-safe setup**

Document copying the local config example, correct host/token entry, privacy settings, and intentional no-op behavior when configuration is absent.

~~~bash
git add README.md
git commit -m "docs: document PostHog observability setup"
~~~

### Task 5: Supply PostHog build settings in CI and release

**Files:**
- Modify: .github/workflows/ci.yml
- Modify: .github/workflows/release.yml
- Modify: README.md
- Modify: docs/superpowers/specs/2026-08-11-posthog-observability-design.md

**Interfaces:**
- Consumes GitHub `POSTHOG_CLIENT_TOKEN` secrets and `POSTHOG_HOST` variables.
- Produces token-aware trusted CI and release archives without embedding a
  credential in the repository.

- [ ] **Step 1: Inject repository configuration into CI Xcode commands**

For each CI build and test `xcodebuild` command, set its environment from
`secrets.POSTHOG_CLIENT_TOKEN` and `vars.POSTHOG_HOST`, defaulting the host to
`https://us.i.posthog.com`. Write both values into a mode-`0600` temporary
xcconfig under `RUNNER_TEMP`, pass only that file path through `-xcconfig`, and
remove it with an exit trap. Do not interpolate or print either value in a
captured command or log. An absent secret, including on a fork pull request,
must yield the app's existing no-op telemetry composition rather than a workflow
failure.

- [ ] **Step 2: Inject environment-scoped configuration into the signed archive**

In the existing `app-store-connect` environment, read the same secret and
variable names and pass them through the same temporary xcconfig to the archive
`xcodebuild` command. Leave CodeQL unconfigured because it does not produce a
distributable telemetry-enabled app.

- [ ] **Step 3: Document the required GitHub configuration**

Document the repository secret `POSTHOG_CLIENT_TOKEN` (the PostHog public
client key), repository variable `POSTHOG_HOST`, and matching secret/variable
in `app-store-connect` for release. Explain the host default and intentional
no-op behavior when a token is unavailable.

- [ ] **Step 4: Validate workflow syntax and commit**

Parse both workflow YAML files, inspect the final diff, and confirm no token
value is present.

~~~bash
git add .github/workflows/ci.yml .github/workflows/release.yml README.md docs/superpowers/specs/2026-08-11-posthog-observability-design.md docs/superpowers/plans/2026-08-11-posthog-observability.md
git commit -m "ci: inject PostHog settings into trusted builds"
~~~

## Plan Self-Review

- **Spec coverage:** Task 1 enforces portable redaction; Task 2 adds PostHog, OTel, safe configuration, replay, flags, and errors; Task 3 integrates approved events and sensitive replay decisions; Task 4 creates/configures the live project and verifies it; Task 5 injects the token safely for trusted CI and release builds.
- **Placeholder scan:** No implementation placeholders remain. The live token is deliberately external and ignored, rather than an unresolved source value.
- **Type consistency:** Tasks 2–3 consume Task 1 protocols and HangTenTelemetryEvent only. TelemetryComposition.make(bundle:) is the single composition API and AppStore(telemetry:) is the app feature injection point.
