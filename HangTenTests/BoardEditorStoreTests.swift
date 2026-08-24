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
        let fixturesURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .appendingPathComponent("Fixtures/BoardPackageValidationFixtures.json")
        let fixtures = try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: fixturesURL)) as? [String: Any]
        )
        let png = try XCTUnwrap(fixtures["png"] as? [String: Any])
        let base64 = try XCTUnwrap(png["validTwoByOneBase64"] as? String)
        return try XCTUnwrap(Data(base64Encoded: base64))
    }

    private func sampleDocument() -> BoardEditableDocument {
        let piece = BoardEditablePiece(
            frame: BoardPackageFrameDocument(x: 0.1, y: 0.2, width: 0.3, height: 0.4),
            shape: BoardGeometryShapeDocument(
                type: "path",
                commands: [
                    BoardGeometryPathCommandDocument(command: "move", to: [0, 0], control: nil, control1: nil, control2: nil),
                    BoardGeometryPathCommandDocument(command: "line", to: [1, 0], control: nil, control1: nil, control2: nil),
                    BoardGeometryPathCommandDocument(command: "line", to: [1, 1], control: nil, control1: nil, control2: nil),
                    BoardGeometryPathCommandDocument(command: "line", to: [0, 1], control: nil, control1: nil, control2: nil),
                    BoardGeometryPathCommandDocument(command: "close", to: nil, control: nil, control1: nil, control2: nil),
                ],
                cornerRadiusFraction: nil
            ),
            shapeConstraint: nil,
            treatment: nil
        )
        let hold = BoardEditableHold(
            id: "hold-one",
            name: "Hold one",
            kind: .jug,
            geometry: [piece]
        )
        return BoardEditableDocument(
            schemaVersion: 1,
            id: "fixture.board",
            manufacturer: "Fixture",
            name: "Fixture board",
            subtitle: "Editing fixture",
            productURL: URL(string: "https://example.com/fixture")!,
            dimensions: "50 \u{00d7} 25 cm",
            aspectRatio: 2.0,
            presentationAssetPath: "assets/primary.png",
            holds: [hold]
        )
    }

    private func makeSourceLibrary(slug: String = "fixture-board") throws -> URL {
        let libraryURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardEditorStoreSource-\(UUID().uuidString)", isDirectory: true)
        let packageURL = libraryURL.appendingPathComponent(slug, isDirectory: true)
        try FileManager.default.createDirectory(
            at: packageURL.appendingPathComponent("assets", isDirectory: true),
            withIntermediateDirectories: true
        )
        try BoardPackageWriter.data(for: sampleDocument())
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
