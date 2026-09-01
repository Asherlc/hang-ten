import XCTest
@testable import HangTen

final class BoardEditorStoreTests: XCTestCase {

    private var storeDirectory: URL!

    override func setUpWithError() throws {
        try super.setUpWithError()
        storeDirectory = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardEditorStoreTests-\(UUID().uuidString)", isDirectory: true)
    }

    override func tearDownWithError() throws {
        if let storeDirectory {
            try? FileManager.default.removeItem(at: storeDirectory)
        }
        storeDirectory = nil
        try super.tearDownWithError()
    }

    private func pngBytes() throws -> Data {
        try BoardEditorTestFixtures.pngBytes()
    }

    private func sampleDocument() -> BoardEditableDocument {
        BoardEditorTestFixtures.sampleDocument()
    }

    private func makeSourceLibrary(slug: String = "fixture-board") throws -> URL {
        let libraryURL = try BoardEditorTestFixtures.makeSourceLibrary(slug: slug)
        addTeardownBlock { try? FileManager.default.removeItem(at: libraryURL) }
        return libraryURL
    }

    private func makeSourceLibraryWithMissingHoldKind(
        slug: String = "missing-kind-board"
    ) throws -> URL {
        let libraryURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardEditorStoreSource-\(UUID().uuidString)", isDirectory: true)
        let packageURL = libraryURL.appendingPathComponent(slug, isDirectory: true)
        try FileManager.default.createDirectory(
            at: packageURL.appendingPathComponent("assets", isDirectory: true),
            withIntermediateDirectories: true
        )

        let encodedDocument = try BoardPackageWriter.data(for: sampleDocument())
        var board = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encodedDocument) as? [String: Any]
        )
        var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
        holds[0].removeValue(forKey: "kind")
        board["holds"] = holds
        try JSONSerialization.data(withJSONObject: board, options: [.sortedKeys])
            .write(to: packageURL.appendingPathComponent("board.json"))
        try pngBytes().write(to: packageURL.appendingPathComponent("assets/primary.png"))
        addTeardownBlock { try? FileManager.default.removeItem(at: libraryURL) }
        return libraryURL
    }

    private func makeStore(sourceLibraryURL: URL) -> BoardEditorStore {
        BoardEditorStore(baseDirectory: storeDirectory, sourceLibraryURL: sourceLibraryURL)
    }

    func testStartEditingCopiesBundledPackageVerbatimAndIsIdempotent() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)

        let packageURL = try store.startEditing(slug: "fixture-board")

        let originalJSON = try Data(
            contentsOf: sourceLibraryURL.appendingPathComponent("fixture-board/board.json")
        )
        let copiedJSON = try Data(contentsOf: packageURL.appendingPathComponent("board.json"))
        XCTAssertEqual(originalJSON, copiedJSON)
        XCTAssertEqual(
            try Data(contentsOf: sourceLibraryURL.appendingPathComponent("fixture-board/assets/primary.png")),
            try Data(contentsOf: packageURL.appendingPathComponent("assets/primary.png"))
        )
        XCTAssertTrue(store.hasEdits(slug: "fixture-board"))

        let secondCallURL = try store.startEditing(slug: "fixture-board")
        XCTAssertEqual(secondCallURL, packageURL)
        XCTAssertEqual(
            try Data(contentsOf: packageURL.appendingPathComponent("board.json")),
            originalJSON
        )
    }

    func testLoadDocumentReturnsDecodedDocumentWithImageDimensions() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)
        try store.startEditing(slug: "fixture-board")

        let loaded = try store.loadDocument(slug: "fixture-board")

        XCTAssertEqual(loaded.slug, "fixture-board")
        XCTAssertEqual(loaded.document.id, "fixture.board")
        XCTAssertEqual(loaded.document.holds.first?.id, "hold-one")
        XCTAssertEqual(loaded.pixelWidth, 2)
        XCTAssertEqual(loaded.pixelHeight, 1)
        XCTAssertEqual(loaded.imageURL.lastPathComponent, "primary.png")
    }

    func testPrepareEditablePackageLoadsAnExistingPackageOnce() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let setupStore = makeStore(sourceLibraryURL: sourceLibraryURL)
        try setupStore.startEditing(slug: "fixture-board")
        let documentLoads = DocumentLoadCounter()
        let store = BoardEditorStore(
            baseDirectory: storeDirectory,
            sourceLibraryURL: sourceLibraryURL,
            documentWillLoad: {
                documentLoads.increment()
            }
        )

        let package = try store.prepareEditablePackage(slug: "fixture-board")

        XCTAssertEqual(package.slug, "fixture-board")
        XCTAssertEqual(documentLoads.value, 1)
    }

    func testPrepareEditablePackageKeepsResetQueuedUntilDocumentLoads() async throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let preparationHasStarted = expectation(description: "preparation starts loading")
        let allowDocumentLoad = DispatchSemaphore(value: 0)
        let resetAttempt = ResetAttempt()
        let store = BoardEditorStore(
            baseDirectory: storeDirectory,
            sourceLibraryURL: sourceLibraryURL,
            preparationWillLoadDocument: {
                preparationHasStarted.fulfill()
                allowDocumentLoad.wait()
            }
        )

        let preparation = Task.detached { () throws -> BoardEditedPackage in
            try store.prepareEditablePackage(slug: "fixture-board")
        }
        await fulfillment(of: [preparationHasStarted], timeout: 10)

        let reset = Task.detached { () throws -> Void in
            await resetAttempt.begin()
            try store.reset(slug: "fixture-board")
        }
        await resetAttempt.waitUntilStarted()
        try await Task.sleep(for: .milliseconds(20))

        XCTAssertTrue(store.hasEdits(slug: "fixture-board"))
        allowDocumentLoad.signal()

        let package = try await preparation.value
        try await reset.value
        XCTAssertEqual(package.slug, "fixture-board")
        XCTAssertEqual(package.pixelWidth, 2)
        XCTAssertEqual(package.pixelHeight, 1)
        XCTAssertFalse(store.hasEdits(slug: "fixture-board"))
    }

    func testPreparationForAnotherStoreIsNotBlockedByAnUnrelatedStore() async throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let preparationHasStarted = expectation(description: "first preparation starts loading")
        let allowPreparation = DispatchSemaphore(value: 0)
        let firstStore = BoardEditorStore(
            baseDirectory: storeDirectory.appendingPathComponent("first", isDirectory: true),
            sourceLibraryURL: sourceLibraryURL,
            preparationWillLoadDocument: {
                preparationHasStarted.fulfill()
                allowPreparation.wait()
            }
        )
        let secondStore = BoardEditorStore(
            baseDirectory: storeDirectory.appendingPathComponent("second", isDirectory: true),
            sourceLibraryURL: sourceLibraryURL
        )

        let firstPreparation = Task.detached { () throws -> BoardEditedPackage in
            try firstStore.prepareEditablePackage(slug: "fixture-board")
        }
        await fulfillment(of: [preparationHasStarted], timeout: 10)

        let secondPreparationFinished = expectation(description: "second preparation finishes")
        let secondPreparation = Task.detached { () throws -> BoardEditedPackage in
            defer { secondPreparationFinished.fulfill() }
            return try secondStore.prepareEditablePackage(slug: "fixture-board")
        }
        await fulfillment(of: [secondPreparationFinished], timeout: 10)

        allowPreparation.signal()
        _ = try await firstPreparation.value
        let secondPackage = try await secondPreparation.value

        XCTAssertEqual(secondPackage.slug, "fixture-board")
    }

    func testStartEditingPreservesEditedDocumentWhenDeclaredPresentationAssetIsMissing() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)
        try store.startEditing(slug: "fixture-board")
        let packageURL = try store.exportedFileURL(slug: "fixture-board")
        var editedDocument = try store.loadDocument(slug: "fixture-board").document
        editedDocument.name = "Edited fixture board"
        try store.save(document: editedDocument, slug: "fixture-board")
        let editedBoardData = try Data(contentsOf: packageURL.appendingPathComponent("board.json"))
        try FileManager.default.removeItem(at: packageURL.appendingPathComponent("assets"))

        XCTAssertThrowsError(try store.startEditing(slug: "fixture-board")) { error in
            XCTAssertEqual(error as? BoardEditorStoreError, .unreadablePresentationImage(slug: "fixture-board"))
        }
        XCTAssertEqual(
            try Data(contentsOf: packageURL.appendingPathComponent("board.json")),
            editedBoardData
        )
    }

    func testStartEditingRejectsEmptyAssetsDirectoryForDeclaredPresentation() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)
        try store.startEditing(slug: "fixture-board")
        let packageURL = try store.exportedFileURL(slug: "fixture-board")
        try FileManager.default.removeItem(at: packageURL.appendingPathComponent("assets/primary.png"))

        XCTAssertThrowsError(try store.startEditing(slug: "fixture-board")) { error in
            XCTAssertEqual(error as? BoardEditorStoreError, .unreadablePresentationImage(slug: "fixture-board"))
        }
    }

    @MainActor
    func testMissingHoldKindLoadsWithWarningAndRoundTripsWithoutInventingKind() throws {
        let sourceLibraryURL = try makeSourceLibraryWithMissingHoldKind()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)
        try store.startEditing(slug: "missing-kind-board")

        let loaded = try store.loadDocument(slug: "missing-kind-board")
        XCTAssertNil(loaded.document.holds[0].kind)

        let session = BoardEditorSession(package: loaded, store: store)
        XCTAssertEqual(session.incompleteMetadataHoldIDs, ["hold-one"])
        XCTAssertEqual(session.metadataWarningAccessibilityValue, "Incomplete hold: hold-one")

        try store.save(document: loaded.document, slug: "missing-kind-board")
        let reloaded = try store.loadDocument(slug: "missing-kind-board")
        XCTAssertNil(reloaded.document.holds[0].kind)

        let savedJSON = try XCTUnwrap(
            JSONSerialization.jsonObject(
                with: Data(contentsOf: reloaded.packageURL.appendingPathComponent("board.json"))
            ) as? [String: Any]
        )
        let savedHold = try XCTUnwrap(savedJSON["holds"] as? [[String: Any]])[0]
        XCTAssertNil(savedHold["kind"])
    }

    func testSaveRoundTripsEditedDocumentWithoutStaleCaches() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)
        try store.startEditing(slug: "fixture-board")
        let loaded = try store.loadDocument(slug: "fixture-board")
        var document = loaded.document
        let originalBytes = try Data(contentsOf: loaded.packageURL.appendingPathComponent("board.json"))

        document.holds[0].name = "Renamed hold"
        try store.save(document: document, slug: "fixture-board")

        let reloaded = try store.loadDocument(slug: "fixture-board")
        XCTAssertEqual(reloaded.document.holds[0].name, "Renamed hold")
        XCTAssertEqual(reloaded.document, document)
        XCTAssertNotEqual(
            try Data(contentsOf: reloaded.packageURL.appendingPathComponent("board.json")),
            originalBytes
        )
        XCTAssertEqual(store.editedSlugs(), ["fixture-board"])
    }

    func testResetRemovesEditedPackageAndExportedFileURLExists() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)
        try store.startEditing(slug: "fixture-board")

        let exportedURL = try store.exportedFileURL(slug: "fixture-board")
        XCTAssertTrue(FileManager.default.fileExists(atPath: exportedURL.path))
        XCTAssertTrue(
            FileManager.default.fileExists(atPath: exportedURL.appendingPathComponent("assets/primary.png").path)
        )

        try store.reset(slug: "fixture-board")
        XCTAssertFalse(store.hasEdits(slug: "fixture-board"))
        XCTAssertEqual(store.editedSlugs(), [])
        XCTAssertTrue(FileManager.default.fileExists(
            atPath: sourceLibraryURL.appendingPathComponent("fixture-board/board.json").path
        ))
    }

    func testSaveRejectsInvalidDocumentsLeavingPreviousFileIntact() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)
        try store.startEditing(slug: "fixture-board")
        let loaded = try store.loadDocument(slug: "fixture-board")
        var document = loaded.document
        let previousBytes = try Data(contentsOf: loaded.packageURL.appendingPathComponent("board.json"))

        document.holds[0].geometry[0].shape = BoardGeometryShapeDocument(
            type: "path",
            commands: Array((document.holds[0].geometry[0].shape.commands ?? []).dropLast()),
            cornerRadiusFraction: nil
        )

        XCTAssertThrowsError(try store.save(document: document, slug: "fixture-board"))
        XCTAssertEqual(
            try Data(contentsOf: loaded.packageURL.appendingPathComponent("board.json")),
            previousBytes
        )
    }

    func testOperationsRequireStartedEditingAndKnownSlugs() throws {
        let sourceLibraryURL = try makeSourceLibrary()
        let store = makeStore(sourceLibraryURL: sourceLibraryURL)

        XCTAssertThrowsError(try store.loadDocument(slug: "fixture-board")) { error in
            XCTAssertEqual(error as? BoardEditorStoreError, .missingEditedPackage(slug: "fixture-board"))
        }
        XCTAssertThrowsError(try store.save(document: sampleDocument(), slug: "fixture-board"))
        XCTAssertThrowsError(try store.exportedFileURL(slug: "fixture-board"))

        XCTAssertThrowsError(try store.startEditing(slug: "missing-board")) { error in
            XCTAssertEqual(error as? BoardEditorStoreError, .missingSourcePackage(slug: "missing-board"))
        }
        XCTAssertFalse(store.hasEdits(slug: "UPPER-CASE"))
    }
}

private final class DocumentLoadCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0

    func increment() {
        lock.lock()
        defer { lock.unlock() }
        count += 1
    }

    var value: Int {
        lock.lock()
        defer { lock.unlock() }
        return count
    }
}

private actor ResetAttempt {
    private var started = false
    private var continuation: CheckedContinuation<Void, Never>?

    func begin() {
        started = true
        continuation?.resume()
        continuation = nil
    }

    func waitUntilStarted() async {
        guard !started else { return }
        await withCheckedContinuation { continuation = $0 }
    }
}
