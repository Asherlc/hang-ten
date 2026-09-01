import SwiftUI

@MainActor
protocol BoardEditorLoadingCancellation {
    func cancel()
}

@MainActor
protocol BoardEditorLoadingScheduling {
    func schedule(_ work: @escaping @Sendable () async -> Void) -> BoardEditorLoadingCancellation
}

protocol BoardEditorImagePreparing: Sendable {
    func prepareDisplayImage(at url: URL) async -> UIImage?
    func prepareThumbnailImage(at url: URL, size: CGSize) async -> UIImage?
}

@MainActor
struct BoardEditorBackgroundLoadingScheduler: BoardEditorLoadingScheduling {
    func schedule(_ work: @escaping @Sendable () async -> Void) -> BoardEditorLoadingCancellation {
        BoardEditorLoadingTask(task: Task.detached(priority: .userInitiated) {
            await work()
        })
    }
}

struct BoardEditorUIKitImagePreparer: BoardEditorImagePreparing {
    private let displayPreparer: @Sendable (UIImage) async -> UIImage?
    private let thumbnailPreparer: @Sendable (UIImage, CGSize) async -> UIImage?

    init(
        displayPreparer: @escaping @Sendable (UIImage) async -> UIImage? = {
            await $0.byPreparingForDisplay()
        },
        thumbnailPreparer: @escaping @Sendable (UIImage, CGSize) async -> UIImage? = {
            await $0.byPreparingThumbnail(ofSize: $1)
        }
    ) {
        self.displayPreparer = displayPreparer
        self.thumbnailPreparer = thumbnailPreparer
    }

    func prepareDisplayImage(at url: URL) async -> UIImage? {
        guard let image = UIImage(contentsOfFile: url.path) else { return nil }
        return await displayPreparer(image)
    }

    func prepareThumbnailImage(at url: URL, size: CGSize) async -> UIImage? {
        guard !Task.isCancelled else { return nil }
        guard let image = UIImage(contentsOfFile: url.path) else { return nil }
        guard !Task.isCancelled else { return nil }
        let preparedImage = await thumbnailPreparer(image, size)
        guard !Task.isCancelled else { return nil }
        return preparedImage
    }
}

@MainActor
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
        scheduler: BoardEditorLoadingScheduling? = nil,
        imagePreparer: BoardEditorImagePreparing = BoardEditorUIKitImagePreparer()
    ) {
        self.slug = slug
        self.store = store
        self.scheduler = scheduler ?? BoardEditorBackgroundLoadingScheduler()
        self.imagePreparer = imagePreparer
    }

    func start() {
        guard activeLoadingID == nil else { return }
        let loadingID = UUID()
        activeLoadingID = loadingID

        let cancellation = scheduler.schedule { [weak self, slug, store, imagePreparer] in
            guard !Task.isCancelled,
                  await self?.isLoadingActive(loadingID) == true else {
                return
            }
            do {
                let package = try store.prepareEditablePackage(slug: slug)
                guard !Task.isCancelled,
                      await self?.isLoadingActive(loadingID) == true else {
                    return
                }
                guard let image = await imagePreparer.prepareDisplayImage(at: package.imageURL) else {
                    throw BoardEditorStoreError.unreadablePresentationImage(slug: slug)
                }
                guard !Task.isCancelled,
                      await self?.isLoadingActive(loadingID) == true else {
                    return
                }
                await self?.publish(.loaded(package, image), for: loadingID)
            } catch {
                guard !Task.isCancelled,
                      await self?.isLoadingActive(loadingID) == true else {
                    return
                }
                await self?.publish(.failed, for: loadingID)
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

    private func isLoadingActive(_ loadingID: UUID) -> Bool {
        activeLoadingID == loadingID
    }

    private func publish(_ state: BoardEditorLoadingState, for loadingID: UUID) {
        guard activeLoadingID == loadingID else { return }
        activeLoadingID = nil
        activeCancellation = nil
        self.state = state
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
