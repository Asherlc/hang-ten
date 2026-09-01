import SwiftUI

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
    private var hasStarted = false

    init(slug: String, store: BoardEditorStore) {
        self.slug = slug
        self.store = store
    }

    func start() {
        guard !hasStarted else { return }
        hasStarted = true

        DispatchQueue.global(qos: .userInitiated).async { [slug, store] in
            let state: BoardEditorLoadingState
            do {
                try store.startEditing(slug: slug)
                let package = try store.loadDocument(slug: slug)
                guard let image = UIImage(contentsOfFile: package.imageURL.path) else {
                    throw BoardEditorStoreError.unreadablePresentationImage(slug: slug)
                }
                state = .loaded(package, image)
            } catch {
                state = .failed
            }

            DispatchQueue.main.async { [weak self] in
                self?.state = state
            }
        }
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
    }
}
