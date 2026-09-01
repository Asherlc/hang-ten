import XCTest
@testable import HangTen

@MainActor
final class BoardEditorLoadingTests: XCTestCase {
    private var storeDirectory: URL!

    override func setUpWithError() throws {
        try super.setUpWithError()
        storeDirectory = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardEditorLoadingTests-\(UUID().uuidString)", isDirectory: true)
    }

    override func tearDownWithError() throws {
        if let storeDirectory {
            try? FileManager.default.removeItem(at: storeDirectory)
        }
        storeDirectory = nil
        try super.tearDownWithError()
    }

    func testLoaderPublishesLoadedPackageAndFailureStates() async throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = BoardEditorStore(
            baseDirectory: storeDirectory,
            sourceLibraryURL: sourceLibraryURL
        )

        let loader = BoardEditorLoader(slug: "fixture-board", store: store)
        assertLoading(loader.state)
        loader.start()
        try await waitForTerminalState(of: loader)

        guard case let .loaded(package, image) = loader.state else {
            return XCTFail("Expected fixture board to load, got \(loader.state)")
        }
        XCTAssertEqual(package.slug, "fixture-board")
        XCTAssertEqual(package.pixelWidth, 2)
        XCTAssertEqual(package.pixelHeight, 1)
        XCTAssertEqual(image.size.width, 2)
        XCTAssertEqual(image.size.height, 1)

        let missingLoader = BoardEditorLoader(slug: "missing-board", store: store)
        assertLoading(missingLoader.state)
        missingLoader.start()
        try await waitForTerminalState(of: missingLoader)

        guard case .failed = missingLoader.state else {
            return XCTFail("Expected missing board to fail, got \(missingLoader.state)")
        }
    }

    func testStartReturnsBeforeControlledWorkCompletesAndPublishesPreparedImage() async throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = BoardEditorStore(
            baseDirectory: storeDirectory,
            sourceLibraryURL: sourceLibraryURL
        )
        let scheduler = ControlledBoardEditorLoadingScheduler()
        let preparedImage = try XCTUnwrap(UIImage(data: try pngBytes()))
        let loader = BoardEditorLoader(
            slug: "fixture-board",
            store: store,
            scheduler: scheduler,
            imagePreparer: FixedBoardEditorImagePreparer(image: preparedImage)
        )

        loader.start()

        assertLoading(loader.state)
        XCTAssertTrue(scheduler.hasPendingWork)

        await scheduler.runPendingWork()
        try await waitForTerminalState(of: loader)

        guard case let .loaded(_, image) = loader.state else {
            return XCTFail("Expected controlled work to publish a loaded result, got \(loader.state)")
        }
        XCTAssertTrue(image === preparedImage)
    }

    func testCancelSuppressesControlledWorkCompletion() async throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = BoardEditorStore(
            baseDirectory: storeDirectory,
            sourceLibraryURL: sourceLibraryURL
        )
        let scheduler = ControlledBoardEditorLoadingScheduler()
        let loader = BoardEditorLoader(slug: "fixture-board", store: store, scheduler: scheduler)

        loader.start()
        loader.cancel()
        await scheduler.runPendingWork()

        assertLoading(loader.state)
        XCTAssertNoThrow(try store.loadDocument(slug: "fixture-board"))
    }

    private func assertLoading(_ state: BoardEditorLoadingState) {
        guard case .loading = state else {
            XCTFail("Expected loader to begin in loading state, got \(state)")
            return
        }
    }

    private func waitForTerminalState(of loader: BoardEditorLoader) async throws {
        let deadline = Date().addingTimeInterval(3)
        while case .loading = loader.state {
            guard Date() < deadline else {
                return XCTFail("Timed out waiting for board loading to finish")
            }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
    }

    private func makeSourceLibrary() throws -> URL {
        let libraryURL = try BoardEditorTestFixtures.makeSourceLibrary()
        addTeardownBlock { try? FileManager.default.removeItem(at: libraryURL) }
        return libraryURL
    }

    private func pngBytes() throws -> Data {
        try BoardEditorTestFixtures.pngBytes()
    }
}

private final class ControlledBoardEditorLoadingScheduler: BoardEditorLoadingScheduling {
    private var work: (() async -> Void)?

    var hasPendingWork: Bool { work != nil }

    func schedule(_ work: @escaping @Sendable () async -> Void) -> BoardEditorLoadingCancellation {
        self.work = work
        return ControlledBoardEditorLoadingCancellation()
    }

    func runPendingWork() async {
        await work?()
    }
}

private final class ControlledBoardEditorLoadingCancellation: BoardEditorLoadingCancellation {
    func cancel() {}
}

private struct FixedBoardEditorImagePreparer: BoardEditorImagePreparing {
    let image: UIImage

    func prepareDisplayImage(at url: URL) async -> UIImage? {
        image
    }

    func prepareThumbnailImage(at url: URL, size: CGSize) async -> UIImage? {
        image
    }
}
