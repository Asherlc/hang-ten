import XCTest
@testable import HangTen

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

    @MainActor
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

    @MainActor
    func testStartReturnsBeforeControlledWorkCompletes() async throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = BoardEditorStore(
            baseDirectory: storeDirectory,
            sourceLibraryURL: sourceLibraryURL
        )
        let scheduler = ControlledBoardEditorLoadingScheduler()
        let loader = BoardEditorLoader(
            slug: "fixture-board",
            store: store,
            scheduler: scheduler
        )

        loader.start()

        assertLoading(loader.state)
        XCTAssertTrue(scheduler.hasPendingWork)

        await scheduler.runPendingWork()
        try await waitForTerminalState(of: loader)

        guard case let .loaded(_, image) = loader.state else {
            return XCTFail("Expected controlled work to publish a loaded result, got \(loader.state)")
        }
        XCTAssertEqual(image.size, CGSize(width: 2, height: 1))
    }

    @MainActor
    func testCancelBeforeControlledWorkPreventsPackageCreation() async throws {
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
        XCTAssertFalse(store.hasEdits(slug: "fixture-board"))
        XCTAssertFalse(scheduler.hasPendingWork)
    }

    @MainActor
    func testCancelDuringImagePreparationSuppressesTerminalState() async throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = BoardEditorStore(
            baseDirectory: storeDirectory,
            sourceLibraryURL: sourceLibraryURL
        )
        let scheduler = ControlledBoardEditorLoadingScheduler()
        let imagePreparer = BlockingBoardEditorImagePreparer()
        let loader = BoardEditorLoader(
            slug: "fixture-board",
            store: store,
            scheduler: scheduler,
            imagePreparer: imagePreparer
        )

        loader.start()
        let work = Task { @MainActor in
            await scheduler.runPendingWork()
        }
        await imagePreparer.waitUntilDisplayPreparationStarts()

        loader.cancel()
        await imagePreparer.finishDisplayPreparation()
        await work.value

        assertLoading(loader.state)
        XCTAssertTrue(store.hasEdits(slug: "fixture-board"))
    }

    @MainActor
    func testProductionImagePreparerReturnsNilWhenDisplayPreparationFails() async throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let imageURL = sourceLibraryURL.appendingPathComponent("fixture-board/assets/primary.png")
        let preparer = BoardEditorUIKitImagePreparer(
            displayPreparer: { _ in nil },
            thumbnailPreparer: { _, _ in nil }
        )

        let displayImage = await preparer.prepareDisplayImage(at: imageURL)
        let thumbnailImage = await preparer.prepareThumbnailImage(
            at: imageURL,
            size: CGSize(width: 74, height: 52)
        )

        XCTAssertNil(displayImage)
        XCTAssertNil(thumbnailImage)
    }

    @MainActor
    private func assertLoading(_ state: BoardEditorLoadingState) {
        guard case .loading = state else {
            XCTFail("Expected loader to begin in loading state, got \(state)")
            return
        }
    }

    @MainActor
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

@MainActor
private final class ControlledBoardEditorLoadingScheduler: BoardEditorLoadingScheduling {
    private var work: (() async -> Void)?

    var hasPendingWork: Bool { work != nil }

    func schedule(_ work: @escaping @Sendable () async -> Void) -> BoardEditorLoadingCancellation {
        self.work = work
        return ControlledBoardEditorLoadingCancellation(scheduler: self)
    }

    func runPendingWork() async {
        await work?()
    }
}

@MainActor
private final class ControlledBoardEditorLoadingCancellation: BoardEditorLoadingCancellation {
    private weak var scheduler: ControlledBoardEditorLoadingScheduler?

    init(scheduler: ControlledBoardEditorLoadingScheduler) {
        self.scheduler = scheduler
    }

    func cancel() {
        scheduler?.cancelPendingWork()
    }
}

private extension ControlledBoardEditorLoadingScheduler {
    func cancelPendingWork() {
        work = nil
    }
}

private actor BlockingBoardEditorImagePreparer: BoardEditorImagePreparing {
    private var displayPreparationStarted = false
    private var startContinuation: CheckedContinuation<Void, Never>?
    private var finishContinuation: CheckedContinuation<UIImage?, Never>?

    func prepareDisplayImage(at url: URL) async -> UIImage? {
        displayPreparationStarted = true
        startContinuation?.resume()
        return await withCheckedContinuation { finishContinuation = $0 }
    }

    func prepareThumbnailImage(at url: URL, size: CGSize) async -> UIImage? {
        nil
    }

    func waitUntilDisplayPreparationStarts() async {
        guard !displayPreparationStarted else { return }
        await withCheckedContinuation { startContinuation = $0 }
    }

    func finishDisplayPreparation() {
        finishContinuation?.resume(returning: nil)
        finishContinuation = nil
    }
}
