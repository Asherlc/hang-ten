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
        service.finishPolling(with: .authorized("oauth-token"))
        await waitUntil { session.isSigningIn == false }

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
    var results: [GitHubDeviceAuthorizationResult]
    let authenticatedUserResult: String
    let suspendsPolling: Bool
    private(set) var challengeRequestCount = 0
    private(set) var isPolling = false
    private var pollContinuation: CheckedContinuation<GitHubDeviceAuthorizationResult, Never>?

    init(
        challenge: GitHubDeviceChallenge,
        results: [GitHubDeviceAuthorizationResult],
        authenticatedUser: String,
        suspendsPolling: Bool = false
    ) {
        self.challenge = challenge
        self.results = results
        authenticatedUserResult = authenticatedUser
        self.suspendsPolling = suspendsPolling
    }

    func authenticatedUser(token: String) async throws -> String {
        authenticatedUserResult
    }

    func requestDeviceChallenge(clientID: String) async throws -> GitHubDeviceChallenge {
        challengeRequestCount += 1
        return challenge
    }

    func pollDeviceAuthorization(
        clientID: String,
        deviceCode: String
    ) async throws -> GitHubDeviceAuthorizationResult {
        if suspendsPolling {
            isPolling = true
            return await withCheckedContinuation { continuation in
                pollContinuation = continuation
            }
        }
        guard !results.isEmpty else {
            throw CancellationError()
        }
        return results.removeFirst()
    }

    func finishPolling(with result: GitHubDeviceAuthorizationResult) {
        isPolling = false
        pollContinuation?.resume(returning: result)
        pollContinuation = nil
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
}
