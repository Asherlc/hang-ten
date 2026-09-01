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
        let libraryURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardEditorLoadingSource-\(UUID().uuidString)", isDirectory: true)
        let packageURL = libraryURL.appendingPathComponent("fixture-board", isDirectory: true)
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
        return BoardEditableDocument(
            id: "fixture.board",
            manufacturer: "Fixture",
            name: "Fixture board",
            subtitle: "Editing fixture",
            productURL: URL(string: "https://example.com/fixture")!,
            dimensions: "50 × 25 cm",
            aspectRatio: 2,
            holds: [
                BoardEditableHold(
                    id: "hold-one",
                    name: "Hold one",
                    kind: .jug,
                    presentationID: "front",
                    geometry: [piece]
                ),
            ],
            presentations: [
                BoardEditablePresentation(
                    id: "front",
                    name: "Front",
                    assetPath: "assets/primary.png",
                    aspectRatio: 2,
                    isDefault: true
                ),
            ]
        )
    }
}
