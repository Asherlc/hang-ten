import SwiftUI

@MainActor
final class BoardEditorResetCoordinator: ObservableObject {
    @Published private(set) var resettingSlugs: Set<String> = []

    func isResetting(_ slug: String) -> Bool {
        resettingSlugs.contains(slug)
    }

    func allowsPackageActions(for slug: String) -> Bool {
        !isResetting(slug)
    }

    @discardableResult
    func beginReset(
        slug: String,
        store: BoardEditorStore,
        refreshEdited: @MainActor @escaping () -> Void
    ) -> Bool {
        guard resettingSlugs.insert(slug).inserted else { return false }

        Task { @MainActor [weak self, store, slug] in
            let resetTask = Task.detached(priority: .userInitiated) {
                try store.reset(slug: slug)
            }
            _ = try? await resetTask.value
            guard let self else { return }
            refreshEdited()
            self.resettingSlugs.remove(slug)
        }
        return true
    }
}

struct BoardEditorListView: View {
    @ObservedObject private var syncSession = GitHubSyncSession.shared
    @State private var editorStore = BoardEditorStore()
    @StateObject private var resetCoordinator = BoardEditorResetCoordinator()
    @State private var editedSlugs: Set<String> = []
    @State private var openSlug: SlugRoute?
    @State private var resetTarget: TrainingBoard?
    @State private var showsGitHubSheet = false
    @State private var pushTarget: TrainingBoard?

    private let syncService = GitHubBoardSyncService()

    private var boards: [TrainingBoard] { BoardCatalog.packageStore.boards }

    var body: some View {
        ScrollView(showsIndicators: false) {
            LazyVStack(alignment: .leading, spacing: 14) {
                githubCard
                ForEach(boards, id: \.id) { board in
                    row(board)
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 30)
        }
        .background(Color.hangBackground)
        .navigationTitle("Board editor")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            refreshEdited()
            syncSession.restoreSession()
            #if DEBUG
            if openSlug == nil,
               let reviewSlug = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_EDITOR_SLUG"] {
                openSlug = SlugRoute(slug: reviewSlug)
            }
            if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_GITHUB_SIGN_IN"] == "1" {
                showsGitHubSheet = true
            }
            #endif
        }
        .navigationDestination(item: $openSlug) { route in
            BoardEditorLoadingView(slug: route.slug, store: editorStore)
        }
        .confirmationDialog(
            "Reset local edits for \(resetTarget?.name ?? "this board")?",
            isPresented: Binding(
                get: { resetTarget != nil },
                set: { if !$0 { resetTarget = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("Discard local edits", role: .destructive) {
                if let target = resetTarget {
                    resetCoordinator.beginReset(slug: target.id, store: editorStore) {
                        refreshEdited()
                    }
                }
                resetTarget = nil
            }
            Button("Cancel", role: .cancel) { resetTarget = nil }
        } message: {
            Text("The bundled package stays untouched; your locally edited copy is deleted.")
        }
        .sheet(isPresented: $showsGitHubSheet) {
            GitHubSignInView()
        }
        .sheet(item: $pushTarget) { board in
            GitHubPushSheet(board: board, editorStore: editorStore, syncService: syncService)
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
        }
    }

    private func refreshEdited() {
        editedSlugs = Set(editorStore.editedSlugs())
    }

    private func row(_ board: TrainingBoard) -> some View {
        let allowsPackageActions = resetCoordinator.allowsPackageActions(for: board.id)
        return Button {
            guard resetCoordinator.allowsPackageActions(for: board.id) else { return }
            openSlug = SlugRoute(slug: board.id)
        } label: {
            HStack(spacing: 14) {
                BoardEditorThumbnailView(
                    imageURL: BoardCatalog.packageStore.presentationImageURL(for: board)
                )
                VStack(alignment: .leading, spacing: 4) {
                    Text(board.name)
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                        .multilineTextAlignment(.leading)
                    Text("\(board.manufacturer) · \(board.holds.count) holds")
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                    if editedSlugs.contains(board.id) {
                        Pill(title: "Local edits", tint: .holdActiveDeep, fill: Color.holdActive.opacity(0.12))
                    }
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.hangMuted)
            }
            .padding(14)
            .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(Color.hangLine.opacity(0.8), lineWidth: 1)
            }
        }
        .buttonStyle(.plain)
        .disabled(!allowsPackageActions)
        .contextMenu {
            Button {
                guard resetCoordinator.allowsPackageActions(for: board.id) else { return }
                pushTarget = board
            } label: {
                Label("Push to GitHub…", systemImage: "arrow.up.circle")
            }
            .disabled(!allowsPackageActions)
            Button {
                pullFromGitHub(board)
            } label: {
                Label("Pull latest from GitHub", systemImage: "arrow.down.circle")
            }
            .disabled(!allowsPackageActions)
            if editedSlugs.contains(board.id) {
                Button(role: .destructive) {
                    guard resetCoordinator.allowsPackageActions(for: board.id) else { return }
                    resetTarget = board
                } label: {
                    Label("Discard local edits", systemImage: "trash")
                }
                .disabled(!allowsPackageActions)
            }
        }
    }

    private var githubCard: some View {
        Group {
            if let username = syncSession.username {
                HStack(spacing: 12) {
                    Image(systemName: "checkmark.seal.fill")
                        .foregroundStyle(Color.hangGreenDark)
                    Text("Signed in to GitHub as \(username)")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Spacer()
                    Button("Sign out") {
                        syncSession.signOut()
                    }
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                }
            } else {
                Button {
                    showsGitHubSheet = true
                } label: {
                    HStack(spacing: 12) {
                        Image(systemName: "person.crop.circle.badge.plus")
                            .foregroundStyle(Color.hangGreenDark)
                        Text("Connect GitHub to pull and push packages")
                            .font(.system(size: 13, weight: .semibold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Spacer()
                        Image(systemName: "chevron.right")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(Color.hangMuted)
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .padding(14)
        .background(Color.hangGreen.opacity(0.1), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private func pullFromGitHub(_ board: TrainingBoard) {
        guard resetCoordinator.allowsPackageActions(for: board.id) else { return }
        guard let token = syncSession.token else {
            showsGitHubSheet = true
            return
        }
        Task {
            do {
                let branch = try await syncService.defaultBranch(token: token)
                let payload = try await syncService.fetchBoardPackage(token: token, branch: branch, slug: board.id)
                let document = try BoardEditableDocument(data: payload.boardJSON)
                try editorStore.save(document: document, slug: board.id)
                try editorStore.persistPulledImage(
                    slug: board.id,
                    assetPath: payload.assetPath,
                    data: payload.primaryPNG
                )
                refreshEdited()
            } catch {
                syncSession.lastError = error.localizedDescription
            }
        }
    }
}

private struct BoardEditorThumbnailView: View {
    private static let displaySize = CGSize(width: 74, height: 52)

    let imageURL: URL?
    @State private var image: UIImage?
    private let imagePreparer = BoardEditorUIKitImagePreparer()

    var body: some View {
        Group {
            if let image {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(width: 74, height: 52)
            } else {
                Rectangle()
                    .fill(Color.hangWoodLight.opacity(0.5))
                    .frame(width: 74, height: 52)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
        }
        .task(id: imageURL) {
            image = nil
            guard let imageURL else { return }
            let preparedImage = await Task.detached(priority: .userInitiated) { [imagePreparer] in
                await imagePreparer.prepareThumbnailImage(
                    at: imageURL,
                    size: Self.displaySize
                )
            }.value
            guard !Task.isCancelled else { return }
            image = preparedImage
        }
    }
}

struct SlugRoute: Identifiable, Hashable {
    let slug: String
    var id: String { slug }
}
