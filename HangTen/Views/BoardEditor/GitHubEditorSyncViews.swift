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
    static let shared = GitHubSyncSession()

    @Published private(set) var username: String?
    @Published var lastError: String?
    @Published private(set) var deviceChallenge: GitHubDeviceChallenge?
    @Published private(set) var isSigningIn = false

    private let tokenStore: any GitHubTokenStoring
    private let syncService: any GitHubDeviceServicing
    private let clientID: String
    private let sleep: (UInt64) async throws -> Void
    private var authorizationTask: Task<Void, Never>?

    init(
        tokenStore: any GitHubTokenStoring = GitHubTokenStore(),
        syncService: any GitHubDeviceServicing = GitHubBoardSyncService(),
        clientID: String = Bundle.main.object(forInfoDictionaryKey: "GITHUB_OAUTH_CLIENT_ID") as? String ?? "",
        sleep: @escaping (UInt64) async throws -> Void = { nanoseconds in
            try await Task.sleep(nanoseconds: nanoseconds)
        }
    ) {
        self.tokenStore = tokenStore
        self.syncService = syncService
        self.clientID = clientID.trimmingCharacters(in: .whitespacesAndNewlines)
        self.sleep = sleep
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

    func signIn(token: String) async throws -> String {
        let login = try await syncService.authenticatedUser(token: token)
        try tokenStore.save(token)
        username = login
        return login
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

    func cancelDeviceSignIn() {
        authorizationTask?.cancel()
        authorizationTask = nil
        deviceChallenge = nil
        isSigningIn = false
    }

    private func completeDeviceSignIn() async {
        defer { isSigningIn = false }
        do {
            let challenge = try await syncService.requestDeviceChallenge(clientID: clientID)
            guard !Task.isCancelled else { return }
            deviceChallenge = challenge
            var interval = challenge.pollingInterval
            let deadline = Date().addingTimeInterval(challenge.expiresIn)
            while !Task.isCancelled && Date() < deadline {
                try await sleep(UInt64(interval * 1_000_000_000))
                guard !Task.isCancelled else { return }
                let authorization = try await syncService.pollDeviceAuthorization(
                    clientID: clientID,
                    deviceCode: challenge.deviceCode
                )
                guard !Task.isCancelled else { return }
                switch authorization {
                case .authorizationPending:
                    continue
                case .slowDown:
                    interval += 5
                case .authorized(let token):
                    let login = try await syncService.authenticatedUser(token: token)
                    guard !Task.isCancelled else { return }
                    try tokenStore.save(token)
                    username = login
                    deviceChallenge = nil
                    return
                }
            }
            if !Task.isCancelled {
                lastError = "GitHub authorization expired. Please try again."
            }
        } catch is CancellationError {
            // Cancellation is initiated by the user and must not change credentials.
        } catch {
            lastError = error.localizedDescription
        }
    }
}

struct GitHubSignInView: View {
    @ObservedObject private var syncSession = GitHubSyncSession.shared
    @Environment(\.dismiss) private var dismiss
    @State private var token = ""
    @State private var isSigningIn = false
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    SectionLabel(title: "GitHub access")
                    Text(
                        "Create a fine-grained personal access token for hang-ten with Contents read-and-write and Pull requests read-and-write permissions. The token stays in this device's Keychain."
                    )
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)

                    SecureField("Personal access token", text: $token)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .font(.system(size: 14, design: .monospaced))
                        .padding(12)
                        .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .accessibilityIdentifier("github.token")

                    if let errorText {
                        Text(errorText)
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .foregroundStyle(Color.holdActiveDeep)
                    }

                    Button {
                        signIn()
                    } label: {
                        HStack {
                            if isSigningIn {
                                ProgressView().tint(Color.hangGreenDark)
                            } else {
                                Text("Connect")
                                    .font(.system(size: 15, weight: .bold, design: .rounded))
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 46)
                        .background(Color.hangGreen.opacity(0.25), in: RoundedRectangle(cornerRadius: 13, style: .continuous))
                        .foregroundStyle(Color.hangGreenDark)
                    }
                    .disabled(token.trimmingCharacters(in: .whitespaces).isEmpty || isSigningIn)
                    .accessibilityIdentifier("github.connect")
                }
                .padding(18)
            }
            .background(Color.hangBackground)
            .navigationTitle("GitHub")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }

    private func signIn() {
        isSigningIn = true
        errorText = nil
        let trimmed = token.trimmingCharacters(in: .whitespaces)
        Task {
            defer { isSigningIn = false }
            do {
                _ = try await syncSession.signIn(token: trimmed)
                dismiss()
            } catch {
                errorText = error.localizedDescription
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
