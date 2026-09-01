import SwiftUI

protocol BoardEditorLoadingCancellation {
    func cancel()
}

protocol BoardEditorLoadingScheduling {
    func schedule(_ work: @escaping @Sendable () async -> Void) -> BoardEditorLoadingCancellation
}

protocol BoardEditorImagePreparing {
    func prepareDisplayImage(at url: URL) async -> UIImage?
    func prepareThumbnailImage(at url: URL, size: CGSize) async -> UIImage?
}

struct BoardEditorBackgroundLoadingScheduler: BoardEditorLoadingScheduling {
    func schedule(_ work: @escaping @Sendable () async -> Void) -> BoardEditorLoadingCancellation {
        BoardEditorLoadingTask(task: Task.detached(priority: .userInitiated) {
            await work()
        })
    }
}

struct BoardEditorUIKitImagePreparer: BoardEditorImagePreparing {
    func prepareDisplayImage(at url: URL) async -> UIImage? {
        guard let image = UIImage(contentsOfFile: url.path) else { return nil }
        return await image.byPreparingForDisplay() ?? image
    }

    func prepareThumbnailImage(at url: URL, size: CGSize) async -> UIImage? {
        guard let image = UIImage(contentsOfFile: url.path) else { return nil }
        if let thumbnail = await image.byPreparingThumbnail(ofSize: size) {
            return thumbnail
        }
        return await image.byPreparingForDisplay() ?? image
    }
}

private final class BoardEditorLoadingTask: BoardEditorLoadingCancellation {
    private let task: Task<Void, Never>

    init(task: Task<Void, Never>) {
        self.task = task
    }

    func cancel() {
        task.cancel()
    }
}

enum BoardEditorLoadingState {
    case loading
    case loaded(BoardEditedPackage, UIImage)
    case failed
}

@MainActor
final class BoardEditorLoader: ObservableObject {
    @Published private(set) var state: BoardEditorLoadingState = .loading

    private let slug: String
    private let store: BoardEditorStore
    private let scheduler: BoardEditorLoadingScheduling
    private let imagePreparer: BoardEditorImagePreparing
    private var activeLoadingID: UUID?
    private var activeCancellation: BoardEditorLoadingCancellation?

    init(
        slug: String,
        store: BoardEditorStore,
        scheduler: BoardEditorLoadingScheduling = BoardEditorBackgroundLoadingScheduler(),
        imagePreparer: BoardEditorImagePreparing = BoardEditorUIKitImagePreparer()
    ) {
        self.slug = slug
        self.store = store
        self.scheduler = scheduler
        self.imagePreparer = imagePreparer
    }

    func start() {
        guard activeLoadingID == nil else { return }
        let loadingID = UUID()
        activeLoadingID = loadingID

        let cancellation = scheduler.schedule { [slug, store, imagePreparer] in
            let state: BoardEditorLoadingState
            do {
                try store.startEditing(slug: slug)
                let package = try store.loadDocument(slug: slug)
                guard let image = await imagePreparer.prepareDisplayImage(at: package.imageURL) else {
                    throw BoardEditorStoreError.unreadablePresentationImage(slug: slug)
                }
                state = .loaded(package, image)
            } catch {
                state = .failed
            }

            await MainActor.run { [weak self] in
                guard let self, self.activeLoadingID == loadingID else { return }
                self.activeLoadingID = nil
                self.activeCancellation = nil
                self.state = state
            }
        }
        if activeLoadingID == loadingID {
            activeCancellation = cancellation
        } else {
            cancellation.cancel()
        }
    }

    func cancel() {
        activeLoadingID = nil
        activeCancellation?.cancel()
        activeCancellation = nil
    }
}

struct BoardEditorLoadingView: View {
    @StateObject private var loader: BoardEditorLoader
    private let store: BoardEditorStore

    init(slug: String, store: BoardEditorStore) {
        self.store = store
        _loader = StateObject(wrappedValue: BoardEditorLoader(slug: slug, store: store))
    }

    var body: some View {
        Group {
            switch loader.state {
            case .loading:
                ProgressView()
            case let .loaded(package, image):
                BoardEditorScreen(package: package, image: image, store: store)
            case .failed:
                Text("This board package could not be opened for editing.")
                    .foregroundStyle(Color.hangMuted)
                    .padding()
            }
        }
        .background(Color.hangBackground)
        .task {
            loader.start()
        }
        .onDisappear {
            loader.cancel()
        }
    }
}
