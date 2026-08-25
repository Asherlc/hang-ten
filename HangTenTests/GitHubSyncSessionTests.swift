import XCTest
@testable import HangTen

@MainActor
final class GitHubSyncSessionTests: XCTestCase {
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

    func testDeniedOrCancelledDeviceSignInDoesNotReplaceExistingToken() async throws {
        let tokenStore = FakeGitHubTokenStore(initialToken: "existing-token")
        let service = FakeGitHubDeviceService(
            challenge: .fixture,
            results: [.authorizationPending],
            authenticatedUser: "octocat"
        )
        let session = GitHubSyncSession(
            tokenStore: tokenStore,
            syncService: service,
            clientID: "client-public",
            sleep: { _ in }
        )

        session.startDeviceSignIn()
        await waitUntil { session.deviceChallenge != nil }
        session.cancelDeviceSignIn()

        XCTAssertEqual(tokenStore.loadedToken, "existing-token")
        XCTAssertTrue(tokenStore.savedTokens.isEmpty)
        XCTAssertNil(session.deviceChallenge)
        XCTAssertFalse(session.isSigningIn)
    }

    func testCancelledAuthorizedPollDoesNotReplaceExistingToken() async throws {
        let tokenStore = FakeGitHubTokenStore(initialToken: "existing-token")
        let service = FakeGitHubDeviceService(
            challenge: .fixture,
            results: [],
            authenticatedUser: "octocat",
            suspendsPolling: true
        )
        let session = GitHubSyncSession(
            tokenStore: tokenStore,
            syncService: service,
            clientID: "client-public",
            sleep: { _ in }
        )

        session.startDeviceSignIn()
        await waitUntil { service.isPolling }
        session.cancelDeviceSignIn()

        XCTAssertTrue(session.isDeviceSignInTaskActive)
        service.finishPolling(with: .authorized("oauth-token"))
        await waitUntil { session.isDeviceSignInTaskActive == false }

        XCTAssertEqual(tokenStore.loadedToken, "existing-token")
        XCTAssertTrue(tokenStore.savedTokens.isEmpty)
        XCTAssertNil(session.username)
    }

    func testMissingConfiguredClientIDShowsConfigurationErrorWithoutRequestingGitHub() async throws {
        let service = FakeGitHubDeviceService(challenge: .fixture, results: [], authenticatedUser: "octocat")
        let session = GitHubSyncSession(
            tokenStore: FakeGitHubTokenStore(),
            syncService: service,
            clientID: "",
            sleep: { _ in }
        )

        session.startDeviceSignIn()
        await waitUntil { session.isSigningIn == false }

        XCTAssertEqual(session.lastError, "GitHub sign-in is not configured.")
        XCTAssertEqual(service.challengeRequestCount, 0)
    }

    func testRepeatedSlowDownAddsExactlyFiveSecondsToEachFollowingDelay() async throws {
        let clock = FakeClock()
        let service = FakeGitHubDeviceService(
            challenge: GitHubDeviceChallenge.fixture(expiresIn: 100, pollingInterval: 5),
            results: [.slowDown, .slowDown, .authorized("oauth-token")],
            authenticatedUser: "octocat"
        )
        let session = GitHubSyncSession(
            tokenStore: FakeGitHubTokenStore(),
            syncService: service,
            clientID: "client-public",
            sleep: clock.sleep,
            now: { clock.current }
        )

        session.startDeviceSignIn()
        await waitUntil { session.isSigningIn == false }

        XCTAssertEqual(clock.delays, [5_000_000_000, 10_000_000_000, 15_000_000_000])
        XCTAssertEqual(service.pollRequestCount, 3)
        XCTAssertEqual(session.username, "octocat")
    }

    func testPollingCapsSleepAtExpiryAndNeverPollsAtOrAfterDeadline() async throws {
        let clock = FakeClock()
        let service = FakeGitHubDeviceService(
            challenge: GitHubDeviceChallenge.fixture(expiresIn: 12, pollingInterval: 10),
            results: [.authorizationPending],
            authenticatedUser: "octocat"
        )
        let session = GitHubSyncSession(
            tokenStore: FakeGitHubTokenStore(),
            syncService: service,
            clientID: "client-public",
            sleep: clock.sleep,
            now: { clock.current }
        )

        session.startDeviceSignIn()
        await waitUntil { session.isSigningIn == false }

        XCTAssertEqual(clock.delays, [10_000_000_000, 2_000_000_000])
        XCTAssertEqual(service.pollRequestCount, 1)
        XCTAssertEqual(session.lastError, "GitHub authorization expired. Please try again.")
        XCTAssertNil(session.deviceChallenge)
    }

    func testPollResponseArrivingAfterExpiryCannotAuthorize() async throws {
        let clock = FakeClock()
        let tokenStore = FakeGitHubTokenStore()
        let service = FakeGitHubDeviceService(
            challenge: GitHubDeviceChallenge.fixture(expiresIn: 6, pollingInterval: 5),
            results: [.authorized("late-token")],
            authenticatedUser: "octocat"
        )
        service.beforePollReturn = { clock.advance(by: 2) }
        let session = GitHubSyncSession(
            tokenStore: tokenStore,
            syncService: service,
            clientID: "client-public",
            sleep: clock.sleep,
            now: { clock.current }
        )

        session.startDeviceSignIn()
        await waitUntil { session.isSigningIn == false }

        XCTAssertTrue(tokenStore.savedTokens.isEmpty)
        XCTAssertNil(session.username)
        XCTAssertEqual(session.lastError, "GitHub authorization expired. Please try again.")
        XCTAssertNil(session.deviceChallenge)
    }

    func testValidationFailureDoesNotSaveTokenAndClearsChallenge() async throws {
        let tokenStore = FakeGitHubTokenStore(initialToken: "existing-token")
        let service = FakeGitHubDeviceService(
            challenge: .fixture,
            results: [.authorized("unvalidated-token")],
            authenticatedUser: "unused",
            authenticatedUserError: GitHubSyncError.unauthorized("Bad credentials")
        )
        let session = GitHubSyncSession(
            tokenStore: tokenStore,
            syncService: service,
            clientID: "client-public",
            sleep: { _ in }
        )

        session.startDeviceSignIn()
        await waitUntil { session.isSigningIn == false }

        XCTAssertEqual(tokenStore.loadedToken, "existing-token")
        XCTAssertTrue(tokenStore.savedTokens.isEmpty)
        XCTAssertEqual(session.lastError, "Bad credentials")
        XCTAssertNil(session.deviceChallenge)
        XCTAssertNil(session.lastSuccessfulDeviceSignInID)
    }

    func testSupersededAttemptCannotPublishItsLateError() async throws {
        let tokenStore = FakeGitHubTokenStore()
        let service = FakeGitHubDeviceService(
            challenge: .fixture,
            results: [.authorized("new-token")],
            authenticatedUser: "octocat",
            suspendsPolling: true
        )
        let session = GitHubSyncSession(
            tokenStore: tokenStore,
            syncService: service,
            clientID: "client-public",
            sleep: { _ in }
        )

        session.startDeviceSignIn()
        await waitUntil { service.suspendedPollCount == 1 }
        session.startDeviceSignIn()
        await waitUntil { session.username == "octocat" }

        service.finishPolling(throwing: GitHubSyncError.unauthorized("stale denial"))
        for _ in 0..<20 { await Task.yield() }

        XCTAssertEqual(tokenStore.savedTokens, ["new-token"])
        XCTAssertNil(session.lastError)
        XCTAssertNil(session.deviceChallenge)
    }

    func testRestoredTokenDoesNotSignalDeviceSignInSuccessOrHideActiveChallenge() async throws {
        let tokenStore = FakeGitHubTokenStore(initialToken: "existing-token")
        let service = FakeGitHubDeviceService(
            challenge: .fixture,
            results: [],
            authenticatedUser: "restored-user",
            suspendsPolling: true
        )
        let session = GitHubSyncSession(
            tokenStore: tokenStore,
            syncService: service,
            clientID: "client-public",
            sleep: { _ in }
        )

        session.startDeviceSignIn()
        await waitUntil { service.suspendedPollCount == 1 }
        session.restoreSession()
        await waitUntil { session.username == "restored-user" }

        XCTAssertNil(session.lastSuccessfulDeviceSignInID)
        XCTAssertEqual(session.deviceChallenge, .fixture)
        XCTAssertTrue(session.isDeviceSignInTaskActive)

        session.cancelDeviceSignIn()
        service.finishPolling(with: .authorizationPending)
        await waitUntil { session.isDeviceSignInTaskActive == false }
    }

    func testTerminalFailureClearsChallengeAndRetryCanSucceed() async throws {
        let service = FakeGitHubDeviceService(
            challenge: .fixture,
            results: [.authorizationPending],
            authenticatedUser: "octocat"
        )
        service.pollOutcomes = [
            .failure(GitHubSyncError.unauthorized("GitHub authorization was denied.")),
            .success(.authorized("oauth-token")),
        ]
        let session = GitHubSyncSession(
            tokenStore: FakeGitHubTokenStore(),
            syncService: service,
            clientID: "client-public",
            sleep: { _ in }
        )

        session.startDeviceSignIn()
        await waitUntil { session.isSigningIn == false }
        XCTAssertNil(session.deviceChallenge)
        XCTAssertEqual(session.lastError, "GitHub authorization was denied.")

        session.startDeviceSignIn()
        await waitUntil { session.isSigningIn == false }
        XCTAssertNil(session.deviceChallenge)
        XCTAssertNil(session.lastError)
        XCTAssertEqual(session.username, "octocat")
    }

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
}

private final class FakeGitHubTokenStore: GitHubTokenStoring {
    private(set) var loadedToken: String?
    private(set) var savedTokens: [String] = []

    init(initialToken: String? = nil) {
        loadedToken = initialToken
    }

    func save(_ token: String) throws {
        savedTokens.append(token)
        loadedToken = token
    }

    func load() -> String? {
        loadedToken
    }

    func delete() throws {
        loadedToken = nil
    }
}

private final class FakeGitHubDeviceService: GitHubDeviceServicing {
    let challenge: GitHubDeviceChallenge
    var pollOutcomes: [Result<GitHubDeviceAuthorizationResult, Error>]
    let authenticatedUserResult: String
    let suspendsPolling: Bool
    let authenticatedUserError: Error?
    var beforePollReturn: (() -> Void)?
    private(set) var challengeRequestCount = 0
    private(set) var pollRequestCount = 0
    private(set) var isPolling = false
    private(set) var suspendedPollCount = 0
    private var pollContinuation: CheckedContinuation<GitHubDeviceAuthorizationResult, Error>?

    init(
        challenge: GitHubDeviceChallenge,
        results: [GitHubDeviceAuthorizationResult],
        authenticatedUser: String,
        suspendsPolling: Bool = false,
        authenticatedUserError: Error? = nil
    ) {
        self.challenge = challenge
        pollOutcomes = results.map(Result.success)
        authenticatedUserResult = authenticatedUser
        self.suspendsPolling = suspendsPolling
        self.authenticatedUserError = authenticatedUserError
    }

    func authenticatedUser(token: String) async throws -> String {
        if let authenticatedUserError { throw authenticatedUserError }
        return authenticatedUserResult
    }

    func requestDeviceChallenge(clientID: String) async throws -> GitHubDeviceChallenge {
        challengeRequestCount += 1
        return challenge
    }

    func pollDeviceAuthorization(
        clientID: String,
        deviceCode: String
    ) async throws -> GitHubDeviceAuthorizationResult {
        pollRequestCount += 1
        if suspendsPolling && pollRequestCount == 1 {
            isPolling = true
            suspendedPollCount += 1
            return try await withCheckedThrowingContinuation { continuation in
                pollContinuation = continuation
            }
        }
        guard !pollOutcomes.isEmpty else {
            throw CancellationError()
        }
        let result = try pollOutcomes.removeFirst().get()
        beforePollReturn?()
        return result
    }

    func finishPolling(with result: GitHubDeviceAuthorizationResult) {
        isPolling = false
        pollContinuation?.resume(returning: result)
        pollContinuation = nil
    }

    func finishPolling(throwing error: Error) {
        isPolling = false
        pollContinuation?.resume(throwing: error)
        pollContinuation = nil
    }
}

@MainActor
private final class FakeClock {
    private(set) var current = Date(timeIntervalSince1970: 1_000)
    private(set) var delays: [UInt64] = []

    func sleep(nanoseconds: UInt64) async throws {
        delays.append(nanoseconds)
        current.addTimeInterval(Double(nanoseconds) / 1_000_000_000)
    }

    func advance(by interval: TimeInterval) {
        current.addTimeInterval(interval)
    }
}

private extension GitHubDeviceChallenge {
    static let fixture = GitHubDeviceChallenge(
        deviceCode: "device-code",
        userCode: "ABCD-EFGH",
        verificationURL: URL(string: "https://github.com/login/device")!,
        expiresIn: 900,
        pollingInterval: 5
    )

    static func fixture(
        expiresIn: TimeInterval,
        pollingInterval: TimeInterval
    ) -> GitHubDeviceChallenge {
        GitHubDeviceChallenge(
            deviceCode: "device-code",
            userCode: "ABCD-EFGH",
            verificationURL: URL(string: "https://github.com/login/device")!,
            expiresIn: expiresIn,
            pollingInterval: pollingInterval
        )
    }
}
