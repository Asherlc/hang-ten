import Foundation
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
        for _ in 0..<100 {
            if predicate() {
                break
            }
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
    let authenticatedUserResult: String
    let suspendsPolling: Bool
    let authenticatedUserError: Error?
    private let lock = NSLock()
    private var pollOutcomesStorage: [Result<GitHubDeviceAuthorizationResult, Error>]
    private var beforePollReturnStorage: (() -> Void)?
    private var challengeRequestCountStorage = 0
    private var pollRequestCountStorage = 0
    private var isPollingStorage = false
    private var suspendedPollCountStorage = 0
    private var pollContinuationStorage: CheckedContinuation<GitHubDeviceAuthorizationResult, Error>?

    var pollOutcomes: [Result<GitHubDeviceAuthorizationResult, Error>] {
        get { withLock { pollOutcomesStorage } }
        set { withLock { pollOutcomesStorage = newValue } }
    }

    var beforePollReturn: (() -> Void)? {
        get { withLock { beforePollReturnStorage } }
        set { withLock { beforePollReturnStorage = newValue } }
    }

    var challengeRequestCount: Int { withLock { challengeRequestCountStorage } }
    var pollRequestCount: Int { withLock { pollRequestCountStorage } }
    var isPolling: Bool { withLock { isPollingStorage } }
    var suspendedPollCount: Int { withLock { suspendedPollCountStorage } }

    init(
        challenge: GitHubDeviceChallenge,
        results: [GitHubDeviceAuthorizationResult],
        authenticatedUser: String,
        suspendsPolling: Bool = false,
        authenticatedUserError: Error? = nil
    ) {
        self.challenge = challenge
        pollOutcomesStorage = results.map(Result.success)
        authenticatedUserResult = authenticatedUser
        self.suspendsPolling = suspendsPolling
        self.authenticatedUserError = authenticatedUserError
    }

    func authenticatedUser(token: String) async throws -> String {
        if let authenticatedUserError { throw authenticatedUserError }
        return authenticatedUserResult
    }

    func requestDeviceChallenge(clientID: String) async throws -> GitHubDeviceChallenge {
        withLock { challengeRequestCountStorage += 1 }
        return challenge
    }

    func pollDeviceAuthorization(
        clientID: String,
        deviceCode: String
    ) async throws -> GitHubDeviceAuthorizationResult {
        let shouldSuspend = withLock { () -> Bool in
            pollRequestCountStorage += 1
            return suspendsPolling && pollRequestCountStorage == 1
        }
        if shouldSuspend {
            return try await withCheckedThrowingContinuation { continuation in
                withLock {
                    isPollingStorage = true
                    suspendedPollCountStorage += 1
                    pollContinuationStorage = continuation
                }
            }
        }
        let outcomeAndClosure = withLock { () -> (Result<GitHubDeviceAuthorizationResult, Error>, (() -> Void)?)? in
            guard !pollOutcomesStorage.isEmpty else { return nil }
            return (pollOutcomesStorage.removeFirst(), beforePollReturnStorage)
        }
        guard let (outcome, beforePollReturn) = outcomeAndClosure else {
            throw CancellationError()
        }
        let result = try outcome.get()
        beforePollReturn?()
        return result
    }

    func finishPolling(with result: GitHubDeviceAuthorizationResult) {
        let continuation = withLock { () -> CheckedContinuation<GitHubDeviceAuthorizationResult, Error>? in
            isPollingStorage = false
            defer { pollContinuationStorage = nil }
            return pollContinuationStorage
        }
        continuation?.resume(returning: result)
    }

    func finishPolling(throwing error: Error) {
        let continuation = withLock { () -> CheckedContinuation<GitHubDeviceAuthorizationResult, Error>? in
            isPollingStorage = false
            defer { pollContinuationStorage = nil }
            return pollContinuationStorage
        }
        continuation?.resume(throwing: error)
    }

    private func withLock<T>(_ body: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return body()
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
