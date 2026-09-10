import XCTest
@testable import HangTen

enum BoardEditorTestFixtures {
    static func makeSourceLibrary(slug: String = "fixture-board") throws -> URL {
        try makeSourceLibrary(slug: slug, document: sampleDocument())
    }

    static func makeSourceLibrary(
        slug: String,
        document: BoardEditableDocument
    ) throws -> URL {
        let libraryURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardEditorStoreSource-\(UUID().uuidString)", isDirectory: true)
        let packageURL = libraryURL.appendingPathComponent(slug, isDirectory: true)
        try FileManager.default.createDirectory(
            at: packageURL.appendingPathComponent("assets", isDirectory: true),
            withIntermediateDirectories: true
        )
        try BoardPackageWriter.data(for: document)
            .write(to: packageURL.appendingPathComponent("board.json"))
        try pngBytes().write(to: packageURL.appendingPathComponent("assets/primary.png"))
        return libraryURL
    }

    static func pngBytes() throws -> Data {
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

    static func sampleDocument() -> BoardEditableDocument {
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

    static func sessionDocument() -> BoardEditableDocument {
        var document = sampleDocument()
        document.name = "Editor session fixture"
        document.holds[0].geometry[0].shapeConstraint = ShapeConstraint(
            shape: .rectangle,
            rotationDegrees: 0
        )

        for index in 2...7 {
            var hold = document.holds[0]
            hold.id = "hold-\(index)"
            hold.name = "Hold \(index)"
            hold.geometry[0].frame = BoardPackageFrameDocument(
                x: 0.05 + Double(index - 2) * 0.12,
                y: 0.65,
                width: 0.08,
                height: 0.16
            )
            if index == 2 {
                hold.geometry[0].shape = BoardGeometryShapeDocument(
                    type: "roundedRect",
                    commands: nil,
                    cornerRadiusFraction: 0.2
                )
                hold.geometry[0].shapeConstraint = nil
            }
            document.holds.append(hold)
        }
        return document
    }
}
