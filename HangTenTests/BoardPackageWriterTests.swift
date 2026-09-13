import XCTest
@testable import HangTen

final class BoardPackageWriterTests: XCTestCase {
    func testWriterEmitsV3ContactsWithRasterOwnedGeometry() throws {
        let encoded = try BoardPackageWriter.data(for: makeDocument())
        let document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )

        XCTAssertEqual(document["schemaVersion"] as? Int, 3)
        XCTAssertEqual(document["revisionID"] as? String, "test-revision")
        XCTAssertNil(document["holds"])
        let contacts = try XCTUnwrap(document["contacts"] as? [[String: Any]])
        XCTAssertEqual(contacts.map { $0["id"] as? String }, ["hold-one"])
        XCTAssertNil(contacts[0]["geometry"])
        XCTAssertNil(contacts[0]["sizeMillimeters"])
        XCTAssertNil(contacts[0]["gripType"])
        XCTAssertEqual(contacts[0]["gripTypes"] as? [String], [])

        let presentations = try XCTUnwrap(document["presentations"] as? [[String: Any]])
        XCTAssertEqual(presentations[0]["isDefault"] as? Bool, true)
        let media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
        XCTAssertEqual(media["type"] as? String, "raster")
        XCTAssertEqual(media["assetPath"] as? String, "assets/primary.png")
        let geometry = try XCTUnwrap(media["contactGeometry"] as? [String: Any])
        XCTAssertNotNil(geometry["hold-one"])
    }

    func testEditorDecoderRejectsLegacyRootHolds() throws {
        var payload = try jsonObject(for: makeDocument())
        payload["holds"] = payload.removeValue(forKey: "contacts")

        XCTAssertThrowsError(try decode(payload))
    }

    func testEditorDecoderRejectsLegacyContactMembers() throws {
        for (key, value) in [
            ("geometry", []),
            ("sizeMillimeters", 20),
            ("gripType", "openHand"),
        ] as [(String, Any)] {
            var payload = try jsonObject(for: makeDocument())
            var contacts = try XCTUnwrap(payload["contacts"] as? [[String: Any]])
            contacts[0][key] = value
            payload["contacts"] = contacts
            XCTAssertThrowsError(try decode(payload), "legacy member \(key) must be rejected")
        }
    }

    func testEditorDecoderRejectsLegacyFlatPresentation() throws {
        var payload = try jsonObject(for: makeDocument())
        payload["presentations"] = [[
            "id": "front",
            "name": "Front",
            "assetPath": "assets/primary.png",
            "aspectRatio": 2,
            "default": true,
        ]]

        XCTAssertThrowsError(try decode(payload))
    }

    func testWriterRejectsModelMediaAsNonEditable() throws {
        var document = makeDocument()
        document.presentations[0].media = .model(
            assetPath: "assets/primary.usdz",
            descriptorPath: "assets/primary.model.json"
        )

        XCTAssertThrowsError(try BoardPackageWriter.data(for: document)) { error in
            XCTAssertEqual(
                error as? BoardPackageWriterError,
                .invalid("board test.board: model-only packages are not editable")
            )
        }
    }

    func testEditorDecoderRecognizesModelMediaWithoutAdaptingIt() throws {
        let boardURL = repositoryHangboardsURL()
            .appendingPathComponent("beastmaker-1000/board.json")
        let document = try BoardEditableDocument(data: Data(contentsOf: boardURL))

        guard case .model(let assetPath, let descriptorPath) = document.presentations[0].media else {
            return XCTFail("expected typed model media")
        }
        XCTAssertEqual(assetPath, "assets/primary.usdz")
        XCTAssertEqual(descriptorPath, "assets/primary.model.json")
        XCTAssertThrowsError(try BoardPackageWriter.data(for: document))
    }

    func testRasterCatalogDocumentsRoundTripThroughV3Writer() throws {
        for slug in try FileManager.default.contentsOfDirectory(
            at: repositoryHangboardsURL(),
            includingPropertiesForKeys: nil
        ).map(\.lastPathComponent).sorted() {
            let boardURL = repositoryHangboardsURL().appendingPathComponent(slug + "/board.json")
            let document = try BoardEditableDocument(data: Data(contentsOf: boardURL))
            guard document.presentations.allSatisfy({ presentation in
                if case .raster = presentation.media { return true }
                return false
            }) else { continue }

            let encoded = try BoardPackageWriter.data(for: document)
            let decoded = try BoardEditableDocument(data: encoded)
            XCTAssertEqual(decoded, document, slug)
        }
    }

    func testWriterRejectsGeometryForUnknownContact() throws {
        var document = makeDocument()
        guard case .raster(let assetPath, var geometry) = document.presentations[0].media else {
            return XCTFail("fixture must use raster media")
        }
        geometry["not-a-contact"] = [makePiece()]
        document.presentations[0].media = .raster(
            assetPath: assetPath,
            contactGeometry: geometry
        )

        XCTAssertThrowsError(try BoardPackageWriter.data(for: document))
    }

    private func repositoryHangboardsURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Hangboards", isDirectory: true)
    }

    private func makeDocument() -> BoardEditableDocument {
        BoardEditableDocument(
            id: "test.board",
            revisionID: "test-revision",
            manufacturer: "Test",
            name: "Test board",
            subtitle: "Fixture",
            productURL: URL(string: "https://example.com/board")!,
            dimensions: "70 × 25 cm",
            aspectRatio: 2,
            contacts: [
                BoardEditableContact(id: "hold-one", name: "Hold one", kind: .jug),
            ],
            presentations: [
                BoardEditablePresentation(
                    id: "front",
                    name: "Front",
                    aspectRatio: 2,
                    isDefault: true,
                    media: .raster(
                        assetPath: "assets/primary.png",
                        contactGeometry: ["hold-one": [makePiece()]]
                    )
                ),
            ]
        )
    }

    private func makePiece() -> BoardEditablePiece {
        BoardEditablePiece(
            frame: BoardPackageFrameDocument(x: 0.1, y: 0.2, width: 0.3, height: 0.4),
            shape: BoardGeometryShapeDocument(
                type: "path",
                commands: [
                    .init(command: "move", to: [0, 0], control: nil, control1: nil, control2: nil),
                    .init(command: "line", to: [1, 0], control: nil, control1: nil, control2: nil),
                    .init(command: "line", to: [1, 1], control: nil, control1: nil, control2: nil),
                    .init(command: "line", to: [0, 1], control: nil, control1: nil, control2: nil),
                    .init(command: "close", to: nil, control: nil, control1: nil, control2: nil),
                ],
                cornerRadiusFraction: nil
            ),
            shapeConstraint: nil,
            treatment: nil
        )
    }

    private func jsonObject(for document: BoardEditableDocument) throws -> [String: Any] {
        try XCTUnwrap(
            JSONSerialization.jsonObject(with: BoardPackageWriter.data(for: document))
                as? [String: Any]
        )
    }

    private func decode(_ payload: [String: Any]) throws -> BoardEditableDocument {
        try BoardEditableDocument(data: JSONSerialization.data(withJSONObject: payload))
    }
}
