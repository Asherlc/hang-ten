# iOS GitHub Device Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the iOS board editor's personal-access-token form with GitHub OAuth Device Flow using the OAuth App already used by the hosted Workbench.

**Architecture:** The iOS target exposes only the OAuth App's public client ID through its generated Info.plist. `GitHubBoardSyncService` owns device-code and token-poll HTTP parsing, while `GitHubSyncSession` owns the cancellable polling lifecycle, validates the GitHub user, and writes only a validated token to the existing Keychain store. The SwiftUI sheet presents the code and browser action without displaying or accepting tokens.

**Tech Stack:** Swift 5, SwiftUI, Foundation `URLSession`, Security Keychain, XCTest, XCUITest, Xcode project build settings.

**Spec:** `docs/superpowers/specs/2026-08-25-ios-github-device-flow-design.md`

## Global Constraints

- Reuse the GitHub OAuth App used by the hosted Workbench; enable GitHub Device Flow for that app before release.
- The iOS bundle contains only `GITHUB_OAUTH_CLIENT_ID`; it must not contain `GITHUB_CLIENT_SECRET` or any OAuth client secret.
- Request exactly `repo read:org` scopes.
- Keep OAuth access tokens out of URLs, view text, logs, and user defaults; save a successfully validated token only through the existing device-only `GitHubTokenStore` Keychain item.
- Do not change the hosted Workbench browser OAuth endpoints, cookies, repository paths, branches, pull behavior, push behavior, or PR behavior.
- Device authorization must respect GitHub's returned polling interval and add five seconds after each `slow_down` response.
- A missing or blank client ID is a configuration error; do not restore the PAT path.
- Every implementation task uses test-first red-green verification, a fresh implementer subagent, and an independent task review.

---

## File structure

| File | Responsibility |
| --- | --- |
| `HangTen/Config/PostHog.xcconfig` | Declares an empty public-client-ID build variable and optionally includes its local override. |
| `HangTen/Config/PostHog.local.xcconfig.example` | Documents the local public-client-ID override without storing a real ID. |
| `HangTen.xcodeproj/project.pbxproj` | Copies `GITHUB_OAUTH_CLIENT_ID` into the generated Debug and Release Info.plists. |
| `HangTen/Models/GitHubBoardSyncService.swift` | Defines device-flow values, sends form-encoded OAuth requests, and parses their typed outcomes. |
| `HangTen/Views/BoardEditor/GitHubEditorSyncViews.swift` | Reads the public configuration, owns sign-in state and cancellation, and renders the approval UI. |
| `HangTen/Views/RootView.swift` | Provides a DEBUG-only direct board-editor route for the sign-in UI test. |
| `HangTenTests/GitHubBoardSyncServiceTests.swift` | Verifies device-code request encoding, parsing, and all polling outcomes using the existing URL protocol stub. |
| `HangTenTests/GitHubSyncSessionTests.swift` | Verifies that a session saves only a validated OAuth token and preserves old credentials on cancellation/failure. |
| `HangTenUITests/GitHubSignInUITests.swift` | Verifies that the sign-in sheet exposes the device flow and no PAT text field. |
| `README.md` | Records the one-time GitHub OAuth App Device Flow and iOS build-variable setup. |

### Task 1: Public configuration and typed GitHub Device Flow client

**Files:**
- Modify: `HangTen/Config/PostHog.xcconfig`
- Modify: `HangTen/Config/PostHog.local.xcconfig.example`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTen/Models/GitHubBoardSyncService.swift`
- Modify: `HangTenTests/GitHubBoardSyncServiceTests.swift`

**Interfaces:**
- Produces: `GitHubDeviceChallenge`, `GitHubDeviceAuthorizationResult`, and `GitHubBoardSyncService.requestDeviceChallenge(clientID:)` / `pollDeviceAuthorization(clientID:deviceCode:)` for Task 2.
- Produces: `GITHUB_OAUTH_CLIENT_ID` as `Bundle.main.object(forInfoDictionaryKey: "GITHUB_OAUTH_CLIENT_ID") as? String` for Task 2.

- [ ] **Step 1: Write failing device-flow client tests**

Add the tests below to the existing URL-protocol suite. Configure `StubState.handler` to return the shown JSON, then assert form bodies with `URLComponents` or percent-decoded body text.

```swift
func testRequestDeviceChallengePostsClientAndExactScopes() async throws {
    StubState.handler = { [self] request in
        try response(request, data: json([
            "device_code": "device-secret",
            "user_code": "ABCD-EFGH",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        ]))
    }

    let challenge = try await makeService().requestDeviceChallenge(clientID: "client-public")

    XCTAssertEqual(challenge.userCode, "ABCD-EFGH")
    XCTAssertEqual(challenge.verificationURL.absoluteString, "https://github.com/login/device")
    let request = try recordedRequest(index: 0)
    XCTAssertEqual(request.url?.absoluteString, "https://github.com/login/device/code")
    XCTAssertEqual(request.value(forHTTPHeaderField: "Accept"), "application/json")
    XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/x-www-form-urlencoded")
    XCTAssertEqual(String(data: requestBody(request), encoding: .utf8), "client_id=client-public&scope=repo%20read%3Aorg")
}

func testPollDeviceAuthorizationMapsPendingSlowDownAndApprovedToken() async throws {
    let cases: [(payload: [String: Any], expected: GitHubDeviceAuthorizationResult)] = [
        (["error": "authorization_pending"], .authorizationPending),
        (["error": "slow_down"], .slowDown),
        (["access_token": "oauth-token", "token_type": "bearer"], .authorized("oauth-token")),
    ]
    for item in cases {
        StubState.handler = { [self] request in try response(request, data: json(item.payload)) }
        XCTAssertEqual(
            try await makeService().pollDeviceAuthorization(clientID: "client-public", deviceCode: "device-secret"),
            item.expected
        )
    }
    let request = try recordedRequest(index: 2)
    XCTAssertEqual(
        String(data: requestBody(request), encoding: .utf8),
        "client_id=client-public&device_code=device-secret&grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code"
    )
}

func testDeviceChallengeRejectsMissingOrInvalidFields() async throws {
    let invalidPayloads: [[String: Any]] = [
        ["user_code": "ABCD-EFGH", "verification_uri": "https://github.com/login/device", "expires_in": 900, "interval": 5],
        ["device_code": "device-secret", "user_code": "ABCD-EFGH", "verification_uri": "http://github.com/login/device", "expires_in": 900, "interval": 5],
        ["device_code": "device-secret", "user_code": "ABCD-EFGH", "verification_uri": "https://github.com/login/device", "expires_in": 900, "interval": 0],
    ]
    for payload in invalidPayloads {
        StubState.handler = { [self] request in try response(request, data: json(payload)) }
        do {
            _ = try await makeService().requestDeviceChallenge(clientID: "client-public")
            XCTFail("invalid challenge must fail")
        } catch {
            XCTAssertEqual(error as? GitHubSyncError, .invalidResponse("GitHub returned invalid device authorization data"))
        }
    }
}

func testPollDeviceAuthorizationMapsDeniedAndExpiredResponses() async throws {
    let cases = [
        ("access_denied", "GitHub authorization was denied."),
        ("expired_token", "GitHub authorization expired. Please try again."),
    ]
    for (errorCode, message) in cases {
        StubState.handler = { [self] request in try response(request, data: json(["error": errorCode])) }
        do {
            _ = try await makeService().pollDeviceAuthorization(clientID: "client-public", deviceCode: "device-secret")
            XCTFail("\(errorCode) must fail")
        } catch let error as GitHubSyncError {
            XCTAssertEqual(error, .unauthorized(message))
        }
    }
}
```

- [ ] **Step 2: Run the new tests and verify red**

Run:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,name=iPhone 17 Pro,OS=latest" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/GitHubBoardSyncServiceTests test
```

Expected: compilation fails because the device-flow types and service methods do not exist.

- [ ] **Step 3: Add the public build configuration**

Add a blank base value and local override documentation:

```xcconfig
GITHUB_OAUTH_CLIENT_ID =
#include? "PostHog.local.xcconfig"
```

```xcconfig
// Optional public client ID for GitHub OAuth Device Flow. Do not add a client secret.
GITHUB_OAUTH_CLIENT_ID = your_github_oauth_client_id
```

Add this to both the HangTen Debug and Release generated-Info.plist build settings:

```text
INFOPLIST_KEY_GITHUB_OAUTH_CLIENT_ID = "$(GITHUB_OAUTH_CLIENT_ID)";
```

- [ ] **Step 4: Add minimal typed device-flow support**

Keep existing GitHub REST requests unchanged. Add values and methods that use a distinct GitHub OAuth base URL and form encoding:

```swift
struct GitHubDeviceChallenge: Equatable {
    let deviceCode: String
    let userCode: String
    let verificationURL: URL
    let expiresIn: TimeInterval
    let pollingInterval: TimeInterval
}

enum GitHubDeviceAuthorizationResult: Equatable {
    case authorizationPending
    case slowDown
    case authorized(String)
}

func requestDeviceChallenge(clientID: String) async throws -> GitHubDeviceChallenge
func pollDeviceAuthorization(
    clientID: String,
    deviceCode: String
) async throws -> GitHubDeviceAuthorizationResult
```

`requestDeviceChallenge` posts `client_id` and exactly `scope=repo read:org` to `https://github.com/login/device/code`. `pollDeviceAuthorization` posts `client_id`, `device_code`, and `grant_type=urn:ietf:params:oauth:grant-type:device_code` to `https://github.com/login/oauth/access_token`. Both requests use `Accept: application/json` and `application/x-www-form-urlencoded`. Parse only non-empty strings, a positive finite `expires_in`, a positive finite `interval`, and an HTTPS `verification_uri`; map `authorization_pending` and `slow_down` to result cases, map `access_denied` and `expired_token` to safe `GitHubSyncError` messages, and reject all other payloads as invalid responses. Never put a received access token in an error message.

- [ ] **Step 5: Run focused tests and verify green**

Run the Step 2 command. Expected: `GitHubBoardSyncServiceTests` passes, including all new request, parse, and outcome coverage.

- [ ] **Step 6: Commit Task 1**

```sh
rtk git add HangTen/Config/PostHog.xcconfig HangTen/Config/PostHog.local.xcconfig.example HangTen.xcodeproj/project.pbxproj HangTen/Models/GitHubBoardSyncService.swift HangTenTests/GitHubBoardSyncServiceTests.swift
rtk git commit -m "Add GitHub device flow client"
```

### Task 2: Cancellable device-flow session and token persistence

**Files:**
- Modify: `HangTen/Views/BoardEditor/GitHubEditorSyncViews.swift`
- Create: `HangTenTests/GitHubSyncSessionTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: Task 1's `GitHubDeviceChallenge`, `GitHubDeviceAuthorizationResult`, client-ID Info.plist value, `requestDeviceChallenge(clientID:)`, and `pollDeviceAuthorization(clientID:deviceCode:)`.
- Produces: `GitHubSyncSession.startDeviceSignIn()`, `cancelDeviceSignIn()`, `deviceChallenge`, `isSigningIn`, and `lastError` for Task 3.

- [ ] **Step 1: Write failing session tests with fakes**

Introduce protocols for the minimal service and token-store surface so the session can be instantiated with test fakes. Add the file to the test target and implement these tests:

```swift
@MainActor
func testDeviceSignInPersistsOnlyValidatedTokenAndUsername() async throws {
    let service = FakeGitHubDeviceService(
        challenge: .fixture,
        results: [.authorizationPending, .authorized("oauth-token")],
        authenticatedUser: "octocat"
    )
    let tokenStore = FakeGitHubTokenStore()
    let session = GitHubSyncSession(
        tokenStore: tokenStore,
        syncService: service,
        clientID: "client-public",
        sleep: { _ in }
    )

    session.startDeviceSignIn()
    await waitUntil { session.isSigningIn == false }

    XCTAssertEqual(tokenStore.savedTokens, ["oauth-token"])
    XCTAssertEqual(session.username, "octocat")
    XCTAssertNil(session.deviceChallenge)
}

@MainActor
func testDeniedOrCancelledDeviceSignInDoesNotReplaceExistingToken() async throws {
    let tokenStore = FakeGitHubTokenStore(initialToken: "existing-token")
    let service = FakeGitHubDeviceService(
        challenge: .fixture,
        results: [.authorizationPending],
        authenticatedUser: "octocat"
    )
    let session = GitHubSyncSession(tokenStore: tokenStore, syncService: service, clientID: "client-public", sleep: { _ in })
    session.startDeviceSignIn()
    await waitUntil { session.deviceChallenge != nil }
    session.cancelDeviceSignIn()
    XCTAssertEqual(tokenStore.loadedToken, "existing-token")
    XCTAssertTrue(tokenStore.savedTokens.isEmpty)
    XCTAssertNil(session.deviceChallenge)
    XCTAssertFalse(session.isSigningIn)
}

@MainActor
func testMissingConfiguredClientIDShowsConfigurationErrorWithoutRequestingGitHub() async throws {
    let service = FakeGitHubDeviceService(challenge: .fixture, results: [], authenticatedUser: "octocat")
    let session = GitHubSyncSession(tokenStore: FakeGitHubTokenStore(), syncService: service, clientID: "", sleep: { _ in })
    session.startDeviceSignIn()
    await waitUntil { session.isSigningIn == false }
    XCTAssertEqual(session.lastError, "GitHub sign-in is not configured.")
    XCTAssertEqual(service.challengeRequestCount, 0)
}

@MainActor
private func waitUntil(
    _ predicate: @escaping @MainActor () -> Bool,
    file: StaticString = #filePath,
    line: UInt = #line
) async {
    for _ in 0..<100 where !predicate() {
        await Task.yield()
    }
    XCTAssertTrue(predicate(), file: file, line: line)
}
```

- [ ] **Step 2: Run the new session tests and verify red**

Run:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,name=iPhone 17 Pro,OS=latest" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/GitHubSyncSessionTests test
```

Expected: compilation fails because the injectable session interfaces and device-flow methods do not exist.

- [ ] **Step 3: Make `GitHubSyncSession` testable and implement polling**

Keep `GitHubSyncSession.shared` for production, but give the class an injectable initializer. Extract protocols that cover `save`, `load`, `delete`, `authenticatedUser`, `requestDeviceChallenge`, and `pollDeviceAuthorization`; make `GitHubTokenStore` and `GitHubBoardSyncService` conform. Resolve and trim `GITHUB_OAUTH_CLIENT_ID` from `Bundle.main` for the production singleton.

Implement the lifecycle below; the injected sleep closure takes nanoseconds so tests can avoid real waits:

```swift
func startDeviceSignIn() {
    guard !clientID.isEmpty else {
        lastError = "GitHub sign-in is not configured."
        return
    }
    authorizationTask?.cancel()
    lastError = nil
    isSigningIn = true
    authorizationTask = Task { [weak self] in
        await self?.completeDeviceSignIn()
    }
}

private func completeDeviceSignIn() async {
    defer { isSigningIn = false }
    do {
        let challenge = try await syncService.requestDeviceChallenge(clientID: clientID)
        deviceChallenge = challenge
        var interval = challenge.pollingInterval
        let deadline = Date().addingTimeInterval(challenge.expiresIn)
        while !Task.isCancelled && Date() < deadline {
            try await sleep(UInt64(interval * 1_000_000_000))
            switch try await syncService.pollDeviceAuthorization(clientID: clientID, deviceCode: challenge.deviceCode) {
            case .authorizationPending: continue
            case .slowDown: interval += 5
            case .authorized(let token):
                let login = try await syncService.authenticatedUser(token: token)
                try tokenStore.save(token)
                username = login
                deviceChallenge = nil
                return
            }
        }
        if !Task.isCancelled { lastError = "GitHub authorization expired. Please try again." }
    } catch is CancellationError {
        // Cancellation is initiated by the user and must not change credentials.
    } catch {
        lastError = error.localizedDescription
    }
}
```

Map cancellation and elapsed challenge time to retryable error text without deleting an existing token. `cancelDeviceSignIn()` must cancel the owned task, clear the displayed challenge, and avoid modifying stored credentials. A failed `/user` validation must not write the new token.

- [ ] **Step 4: Run focused session tests and verify green**

Run the Step 2 command. Expected: all `GitHubSyncSessionTests` pass and no real five-second delay occurs in test execution.

- [ ] **Step 5: Commit Task 2**

```sh
rtk git add HangTen/Views/BoardEditor/GitHubEditorSyncViews.swift HangTenTests/GitHubSyncSessionTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "Manage GitHub device authorization sessions"
```

### Task 3: Device-flow sign-in sheet, UI regression coverage, and operator documentation

**Files:**
- Modify: `HangTen/Views/BoardEditor/GitHubEditorSyncViews.swift`
- Modify: `HangTen/Views/BoardEditor/BoardEditorListView.swift`
- Modify: `HangTen/Views/RootView.swift`
- Create: `HangTenUITests/GitHubSignInUITests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 2's observable `GitHubSyncSession` device-flow state and actions.
- Produces: a device-flow-only GitHub sign-in sheet, accessible controls, a DEBUG test route, and release setup documentation.

- [ ] **Step 1: Write the failing UI test**

Add a DEBUG launch route from `RootReviewDestination.initial(environment:)` to a `NavigationStack { BoardEditorListView() }` when `HANGTEN_REVIEW_BOARD_EDITOR=1`. In `BoardEditorListView.onAppear`, present the GitHub sheet in DEBUG when `HANGTEN_REVIEW_GITHUB_SIGN_IN=1`. Then add this UI test:

```swift
final class GitHubSignInUITests: XCTestCase {
    func testGitHubSheetUsesDeviceFlowAndDoesNotExposePATInput() throws {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_EDITOR": "1",
            "HANGTEN_REVIEW_GITHUB_SIGN_IN": "1",
        ]
        app.launch()

        XCTAssertTrue(app.buttons["github.connect"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["github.device-flow.description"].exists)
        XCTAssertFalse(app.secureTextFields["github.token"].exists)
    }
}
```

- [ ] **Step 2: Run the UI test and verify red**

Run:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,name=iPhone 17 Pro,OS=latest" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenUITests/GitHubSignInUITests test
```

Expected: the test fails because the DEBUG route and device-flow accessibility identifiers do not yet exist.

- [ ] **Step 3: Replace the PAT sheet with the device-flow UI**

Remove the PAT instructional text, `SecureField`, `github.token` identifier, and token-parameter `signIn` method. Render the state below instead:

```swift
Text("Approve Hang Ten in GitHub to connect your account.")
    .accessibilityIdentifier("github.device-flow.description")

if let challenge = syncSession.deviceChallenge {
    Text(challenge.userCode)
        .font(.system(size: 28, weight: .bold, design: .monospaced))
        .accessibilityIdentifier("github.device-code")
    Button("Open GitHub") { openURL(challenge.verificationURL) }
        .accessibilityIdentifier("github.open-verification")
    Button("Cancel sign-in") { syncSession.cancelDeviceSignIn() }
        .accessibilityIdentifier("github.cancel")
} else {
    Button("Connect GitHub") { syncSession.startDeviceSignIn() }
        .accessibilityIdentifier("github.connect")
}
```

Keep the sheet open while authorization is pending. Dismiss it only when `isAuthenticated` becomes true after a successful validated sign-in. Render `lastError` with the existing error style and retain a retryable Connect action. Keep the existing GitHub account card, sign out, pull, commit, and PR controls unchanged.

- [ ] **Step 4: Add the DEBUG-only test route and project references**

Extend `RootReviewDestination` with `.boardEditor`, render it in a navigation stack, and add the `GitHubSignInUITests.swift` file reference/build file to the UI test target. Gate both launch-environment behaviors with `#if DEBUG` so no production navigation is added.

- [ ] **Step 5: Document release setup**

Add a README section that directs the maintainer to enable Device Flow in the existing GitHub OAuth App, configure the public `GITHUB_OAUTH_CLIENT_ID` in CI/local Xcode configuration, and never distribute `GITHUB_CLIENT_SECRET`. State that the app requests `repo read:org` and no longer accepts personal access tokens.

- [ ] **Step 6: Run UI test and focused unit suite to verify green**

Run:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,name=iPhone 17 Pro,OS=latest" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenUITests/GitHubSignInUITests \
  -only-testing:HangTenTests/GitHubBoardSyncServiceTests \
  -only-testing:HangTenTests/GitHubSyncSessionTests test
```

Expected: all selected tests pass, the sheet exposes `github.connect` and `github.device-flow.description`, and no `github.token` secure field exists.

- [ ] **Step 7: Commit Task 3**

```sh
rtk git add HangTen/Views/BoardEditor/GitHubEditorSyncViews.swift HangTen/Views/BoardEditor/BoardEditorListView.swift HangTen/Views/RootView.swift HangTenUITests/GitHubSignInUITests.swift HangTen.xcodeproj/project.pbxproj README.md
rtk git commit -m "Use GitHub device flow in board editor"
```

## Final verification

- [ ] Run the full iOS simulator suite with the repository-standard command:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 17 Pro,OS=latest" \
  -parallel-testing-enabled YES \
  -maximum-parallel-testing-workers 1 \
  -derivedDataPath .context/DerivedData \
  CODE_SIGN_IDENTITY="-" test
```

- [ ] Confirm the final diff contains no OAuth client secret, PAT entry field, or `github.token` identifier.
- [ ] Manually enable Device Flow for the existing GitHub OAuth App and set its public client ID for the iOS Release build before distributing the app.
