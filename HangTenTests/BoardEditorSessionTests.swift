import XCTest
@testable import HangTen

@MainActor
final class BoardEditorSessionTests: XCTestCase {
    private let slug = "editor-session-fixture"
    private var editDirectory: URL!
    private var sourceLibraryURL: URL!
    private var store: BoardEditorStore!

    override func setUp() async throws {
        try await super.setUp()
        editDirectory = FileManager.default.temporaryDirectory
            .appendingPathComponent("board-editor-session-\(UUID().uuidString)", isDirectory: true)
        sourceLibraryURL = try BoardEditorTestFixtures.makeSourceLibrary(
            slug: slug,
            document: BoardEditorTestFixtures.sessionDocument()
        )
        store = BoardEditorStore(baseDirectory: editDirectory, sourceLibraryURL: sourceLibraryURL)
    }

    override func tearDown() async throws {
        if let editDirectory { try? FileManager.default.removeItem(at: editDirectory) }
        if let sourceLibraryURL { try? FileManager.default.removeItem(at: sourceLibraryURL) }
        try await super.tearDown()
    }

    func testSessionReadsGeometryFromTypedRasterMedia() throws {
        let session = try makeSession()
        session.select(contactID: "hold-one")

        XCTAssertEqual(session.selectedContact?.id, "hold-one")
        XCTAssertEqual(session.selectedPieceDocument, session.document.geometry(forContactID: "hold-one")?[0])
    }

    func testSessionEditsRasterContactGeometryAndUndoRedo() throws {
        let session = try makeSession()
        session.select(contactID: "hold-one")
        let before = try XCTUnwrap(session.selectedPieceDocument)

        try session.translateSelectedPiece(deltaX: 0.05, deltaY: 0.04, recordsHistory: true)
        let after = try XCTUnwrap(session.selectedPieceDocument)
        XCTAssertNotEqual(after.frame, before.frame)
        XCTAssertFalse(session.isSaved)

        session.undo()
        XCTAssertEqual(session.selectedPieceDocument, before)
        session.redo()
        XCTAssertEqual(session.selectedPieceDocument, after)
    }

    func testSessionSavePersistsV3RasterGeometry() throws {
        let session = try makeSession()
        session.select(contactID: "hold-one")
        try session.translateSelectedPiece(deltaX: 0.02, deltaY: 0, recordsHistory: true)

        try session.save()

        let reloaded = try store.loadDocument(slug: slug)
        XCTAssertEqual(
            reloaded.document.geometry(forContactID: "hold-one"),
            session.document.geometry(forContactID: "hold-one")
        )
        let payload = try XCTUnwrap(
            JSONSerialization.jsonObject(
                with: Data(contentsOf: reloaded.packageURL.appendingPathComponent("board.json"))
            ) as? [String: Any]
        )
        XCTAssertEqual(payload["schemaVersion"] as? Int, 3)
        XCTAssertNil(payload["holds"])
    }

    func testRoundedRectConversionWritesBackToRasterMedia() throws {
        let session = try makeSession()
        session.select(contactID: "hold-2")
        XCTAssertTrue(session.isRoundedRectPiece)

        try session.convertRoundedRectToPath()

        XCTAssertEqual(session.selectedPieceDocument?.shape.type, "path")
        XCTAssertNotNil(session.document.geometry(forContactID: "hold-2"))
    }

    func testNormalizedConstraintDegreesWrapsIntoRange() {
        XCTAssertEqual(BoardEditorSession.normalizedConstraintDegrees(185), -175)
        XCTAssertEqual(BoardEditorSession.normalizedConstraintDegrees(-185), 175)
        XCTAssertEqual(BoardEditorSession.normalizedConstraintDegrees(180), -180)
    }

    private func makeSession() throws -> BoardEditorSession {
        let package = try store.prepareEditablePackage(slug: slug)
        return BoardEditorSession(package: package, store: store)
    }
}
