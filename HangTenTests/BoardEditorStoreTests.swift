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
