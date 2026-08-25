import SwiftUI

protocol GitHubTokenStoring {
    func save(_ token: String) throws
    func load() -> String?
    func delete() throws
}

protocol GitHubDeviceServicing {
    func authenticatedUser(token: String) async throws -> String
    func requestDeviceChallenge(clientID: String) async throws -> GitHubDeviceChallenge
    func pollDeviceAuthorization(
        clientID: String,
        deviceCode: String
    ) async throws -> GitHubDeviceAuthorizationResult
}

extension GitHubTokenStore: GitHubTokenStoring {}
extension GitHubBoardSyncService: GitHubDeviceServicing {}

@MainActor
final class GitHubSyncSession: ObservableObject {
    static let shared: GitHubSyncSession = {
        #if DEBUG
        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_GITHUB_DEVICE_CHALLENGE"] == "1" {
            return GitHubSyncSession(
                syncService: GitHubReviewDeviceService(),
                clientID: "review-client"
            )
        }
        #endif
        return GitHubSyncSession()
    }()

    @Published private(set) var username: String?
    @Published var lastError: String?
    @Published private(set) var deviceChallenge: GitHubDeviceChallenge?
    @Published private(set) var isSigningIn = false
    @Published private(set) var lastSuccessfulDeviceSignInID: UUID?

    private let tokenStore: any GitHubTokenStoring
    private let syncService: any GitHubDeviceServicing
    private let clientID: String
    private let sleep: (UInt64) async throws -> Void
    private let now: () -> Date
    private var authorizationTask: Task<Void, Never>?
    private var activeDeviceSignInTaskID: UUID?
    @Published private(set) var isDeviceSignInTaskActive = false

    init(
        tokenStore: any GitHubTokenStoring = GitHubTokenStore(),
        syncService: any GitHubDeviceServicing = GitHubBoardSyncService(),
        clientID: String = Bundle.main.object(forInfoDictionaryKey: "GITHUB_OAUTH_CLIENT_ID") as? String ?? "",
        sleep: @escaping (UInt64) async throws -> Void = { nanoseconds in
            try await Task.sleep(nanoseconds: nanoseconds)
        },
        now: @escaping () -> Date = Date.init
    ) {
        self.tokenStore = tokenStore
        self.syncService = syncService
        self.clientID = clientID.trimmingCharacters(in: .whitespacesAndNewlines)
        self.sleep = sleep
        self.now = now
    }

    var token: String? {
        tokenStore.load()
    }

    var isAuthenticated: Bool {
        username != nil && token != nil
    }

    func restoreSession() {
        guard tokenStore.load() != nil else { return }
        Task {
            if let token = tokenStore.load() {
                do {
                    username = try await syncService.authenticatedUser(token: token)
                } catch {
                    lastError = error.localizedDescription
                }
            }
        }
    }

    func signOut() {
        do {
            try tokenStore.delete()
            username = nil
            lastError = nil
        } catch {
            lastError = error.localizedDescription
        }
    }

    func startDeviceSignIn() {
        authorizationTask?.cancel()
        deviceChallenge = nil
        lastError = nil
        guard !clientID.isEmpty else {
            lastError = "GitHub sign-in is not configured."
            return
        }
        isSigningIn = true
        let taskID = UUID()
        activeDeviceSignInTaskID = taskID
        isDeviceSignInTaskActive = true
        authorizationTask = Task { [weak self] in
            await self?.completeDeviceSignIn(taskID: taskID)
        }
    }

    func cancelDeviceSignIn() {
        authorizationTask?.cancel()
        deviceChallenge = nil
        isSigningIn = false
    }

    private func completeDeviceSignIn(taskID: UUID) async {
        var completedSuccessfully = false
        defer {
            finishDeviceSignIn(
                taskID: taskID,
                completedSuccessfully: completedSuccessfully
            )
        }
        do {
            let challenge = try await syncService.requestDeviceChallenge(clientID: clientID)
            guard canPublishDeviceSignInState(taskID: taskID) else { return }
            deviceChallenge = challenge
            var interval = challenge.pollingInterval
            let deadline = now().addingTimeInterval(challenge.expiresIn)
            while canPublishDeviceSignInState(taskID: taskID) {
                let remainingLifetime = deadline.timeIntervalSince(now())
                guard remainingLifetime > 0 else {
                    publishDeviceSignInExpiry(taskID: taskID)
                    return
                }
                let delay = min(interval, remainingLifetime)
                try await sleep(try GitHubDeviceChallenge.sleepNanoseconds(for: delay))
                guard canPublishDeviceSignInState(taskID: taskID) else { return }
                guard now() < deadline else {
                    publishDeviceSignInExpiry(taskID: taskID)
                    return
                }
                let authorization = try await syncService.pollDeviceAuthorization(
                    clientID: clientID,
                    deviceCode: challenge.deviceCode
                )
                guard canPublishDeviceSignInState(taskID: taskID) else { return }
                guard now() < deadline else {
                    publishDeviceSignInExpiry(taskID: taskID)
                    return
                }
                switch authorization {
                case .authorizationPending:
                    continue
                case .slowDown:
                    interval += 5
                case .authorized(let token):
                    let login = try await syncService.authenticatedUser(token: token)
                    guard canPublishDeviceSignInState(taskID: taskID) else { return }
                    try tokenStore.save(token)
                    guard canPublishDeviceSignInState(taskID: taskID) else { return }
                    username = login
                    deviceChallenge = nil
                    completedSuccessfully = true
                    return
                }
            }
        } catch is CancellationError {
            // Cancellation is initiated by the user and must not change credentials.
        } catch {
            guard canPublishDeviceSignInState(taskID: taskID) else { return }
            deviceChallenge = nil
            lastError = error.localizedDescription
        }
    }

    private func canPublishDeviceSignInState(taskID: UUID) -> Bool {
        activeDeviceSignInTaskID == taskID && !Task.isCancelled
    }

    private func publishDeviceSignInExpiry(taskID: UUID) {
        guard canPublishDeviceSignInState(taskID: taskID) else { return }
        deviceChallenge = nil
        lastError = "GitHub authorization expired. Please try again."
    }

    private func finishDeviceSignIn(
        taskID: UUID,
        completedSuccessfully: Bool
    ) {
        guard activeDeviceSignInTaskID == taskID else { return }
        let shouldPublishSuccess = completedSuccessfully && !Task.isCancelled
        isSigningIn = false
        isDeviceSignInTaskActive = false
        activeDeviceSignInTaskID = nil
        authorizationTask = nil
        if shouldPublishSuccess {
            lastSuccessfulDeviceSignInID = taskID
        }
    }
}

#if DEBUG
private struct GitHubReviewDeviceService: GitHubDeviceServicing {
    func authenticatedUser(token: String) async throws -> String {
        "review-user"
    }

    func requestDeviceChallenge(clientID: String) async throws -> GitHubDeviceChallenge {
        GitHubDeviceChallenge(
            deviceCode: "review-device-code",
            userCode: "ABCD-EFGH",
            verificationURL: URL(string: "https://github.com/login/device")!,
            expiresIn: 900,
            pollingInterval: 60
        )
    }

    func pollDeviceAuthorization(
        clientID: String,
        deviceCode: String
    ) async throws -> GitHubDeviceAuthorizationResult {
        try await Task.sleep(nanoseconds: 60_000_000_000)
        return .authorizationPending
    }
}
#endif

struct GitHubSignInView: View {
    @ObservedObject private var syncSession = GitHubSyncSession.shared
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    SectionLabel(title: "GitHub access")
                    Text("Approve Hang Ten in GitHub to connect your account.")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
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

                    if let lastError = syncSession.lastError {
                        Text(lastError)
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .foregroundStyle(Color.holdActiveDeep)

                        if syncSession.deviceChallenge != nil {
                            Button("Connect GitHub") { syncSession.startDeviceSignIn() }
                                .accessibilityIdentifier("github.connect")
                        }
                    }

                    if syncSession.isSigningIn {
                        ProgressView().tint(Color.hangGreenDark)
                    }
                }
                .padding(18)
            }
            .background(Color.hangBackground)
            .navigationTitle("GitHub")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(syncSession.isDeviceSignInTaskActive ? "Cancel sign-in" : "Cancel") {
                        if syncSession.isDeviceSignInTaskActive {
                            syncSession.cancelDeviceSignIn()
                        } else {
                            dismiss()
                        }
                    }
                }
            }
        }
        .interactiveDismissDisabled(syncSession.isDeviceSignInTaskActive)
        .onChange(of: syncSession.lastSuccessfulDeviceSignInID) { _, successfulTaskID in
            if successfulTaskID != nil {
                dismiss()
            }
        }
        .onDisappear {
            if syncSession.isDeviceSignInTaskActive {
                syncSession.cancelDeviceSignIn()
            }
        }
    }
}

struct GitHubPushSheet: View {
    let board: TrainingBoard
    let editorStore: BoardEditorStore
    let syncService: GitHubBoardSyncService

    @ObservedObject private var syncSession = GitHubSyncSession.shared
    @Environment(\.dismiss) private var dismiss
    @State private var branchName = GitHubPushSheet.defaultBranchName()
    @State private var commitMessage = ""
    @State private var isPushing = false
    @State private var pushedPRURL: URL?
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    SectionLabel(title: "Push board geometry")
                    Text(board.name)
                        .font(.system(size: 17, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)

                    field(label: "Branch", text: $branchName)
                    field(label: "Commit message", text: $commitMessage)

                    if let errorText {
                        Text(errorText)
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .foregroundStyle(Color.holdActiveDeep)
                    }

                    if let pushedPRURL {
                        VStack(alignment: .leading, spacing: 10) {
                            Label("Pull request opened", systemImage: "checkmark.circle.fill")
                                .foregroundStyle(Color.hangGreenDark)
                            Link(pushedPRURL.absoluteString, destination: pushedPRURL)
                                .font(.system(size: 12, design: .monospaced))
                        }
                    }

                    Button {
                        push()
                    } label: {
                        HStack {
                            if isPushing {
                                ProgressView().tint(Color.hangGreenDark)
                            } else {
                                Text("Commit and open pull request")
                                    .font(.system(size: 15, weight: .bold, design: .rounded))
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 46)
                        .background(Color.hangGreen.opacity(0.25), in: RoundedRectangle(cornerRadius: 13, style: .continuous))
                        .foregroundStyle(Color.hangGreenDark)
                    }
                    .disabled(
                        isPushing
                            || commitMessage.trimmingCharacters(in: .whitespaces).isEmpty
                            || pushedPRURL != nil
                    )
                    .accessibilityIdentifier("github.push")

                    Text("Hang Ten commits only board.json for \(board.id). Presentation images stay local.")
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }
                .padding(18)
            }
            .background(Color.hangBackground)
            .navigationTitle("GitHub")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private static func defaultBranchName() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd-HHmm"
        return "board-editor/\(formatter.string(from: Date()))-geometry"
    }

    private func field(label: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            SectionLabel(title: label)
            TextField(label == "Branch" ? "board-editor/…" : "Describe the change", text: text)
                .textFieldStyle(.plain)
                .font(.system(size: 14, design: .rounded))
                .padding(12)
                .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
    }

    private func push() {
        guard let token = syncSession.token else { return }
        isPushing = true
        errorText = nil
        let branch = branchName.trimmingCharacters(in: .whitespaces)
        let message = commitMessage.trimmingCharacters(in: .whitespaces)
        Task {
            defer { isPushing = false }
            do {
                let base = try await syncService.defaultBranch(token: token)
                let headSHA = try await syncService.branchHeadSHA(token: token, branch: base)
                if try await syncService.listBranches(token: token).contains(branch) == false {
                    try await syncService.createBranch(token: token, name: branch, fromSHA: headSHA)
                }
                let packageURL = try editorStore.exportedFileURL(slug: board.id)
                let data = try Data(contentsOf: packageURL.appendingPathComponent("board.json"))
                _ = try await syncService.commitFile(
                    token: token,
                    branch: branch,
                    path: "Hangboards/\(board.id)/board.json",
                    content: data,
                    message: message,
                    sha: nil
                )
                pushedPRURL = try await syncService.createPullRequest(
                    token: token,
                    title: "[board-editor] \(board.name) geometry",
                    head: branch,
                    base: base,
                    body: "Geometry edited on device with the native Hang Ten board editor."
                )
            } catch {
                errorText = error.localizedDescription
            }
        }
    }
}
