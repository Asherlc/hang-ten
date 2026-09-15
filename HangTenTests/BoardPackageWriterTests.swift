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
            descriptorPath: "assets/primary.model.json",
            display: try modelDisplay(),
            suspension: nil,
            orientation: nil
        )

        XCTAssertThrowsError(try BoardPackageWriter.data(for: document)) { error in
            XCTAssertEqual(
                error as? BoardPackageWriterError,
                .invalid("board test.board: model-only packages are not editable")
            )
        }
    }

    func testEditorDecoderPreservesTypedModelDisplayAndOrientationWithoutAdaptingIt() throws {
        let boardURL = repositoryHangboardsURL()
            .appendingPathComponent("captain-fingerfood-pocket/board.json")
        let document = try BoardEditableDocument(data: Data(contentsOf: boardURL))

        guard case .model(
            let assetPath,
            let descriptorPath,
            let display,
            let suspension,
            let orientation
        ) = document.presentations[0].media else {
            return XCTFail("expected typed model media")
        }
        XCTAssertEqual(assetPath, "assets/primary.usdz")
        XCTAssertEqual(descriptorPath, "assets/primary.model.json")
        XCTAssertEqual(display.camera.type, "orthographic")
        XCTAssertEqual(display.camera.viewDirection, [0, 0, -1])
        XCTAssertEqual(display.camera.up, [0, 1, 0])
        XCTAssertEqual(display.camera.fitPadding, 0.08)
        XCTAssertNil(suspension)
        XCTAssertEqual(orientation?.pivot, "modelBoundsCenter")
        XCTAssertEqual(
            orientation?.rotations["edge-20-front"],
            [0.199367862, 0, 0, 0.979924719]
        )
        XCTAssertThrowsError(try BoardPackageWriter.data(for: document)) { error in
            XCTAssertEqual(
                error as? BoardPackageWriterError,
                .invalid("board captain-fingerfood.pocket: model-only packages are not editable")
            )
        }
    }

    func testEditorDecoderPreservesTypedModelSuspensionWithoutAdaptingIt() throws {
        let boardURL = repositoryHangboardsURL()
            .appendingPathComponent("beastmaker-1000/board.json")
        var payload = try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: boardURL)) as? [String: Any]
        )
        var presentations = try XCTUnwrap(payload["presentations"] as? [[String: Any]])
        var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
        media["suspension"] = [
            "type": "singleCord",
            "attachment": [
                "nodeID": "body-main",
                "pointInModel": [0.1, 0.2, 0.3],
                "provenance": "fixture attachment",
            ],
            "anchor": [
                "offsetFromBoardBounds": [0.0, 0.4, 0.0],
                "visibility": "invisible",
                "provenance": "fixture anchor",
            ],
            "cord": [
                "restLength": 1.25,
                "radius": 0.004,
                "material": "polyester",
                "provenance": "fixture cord",
            ],
            "canonicalPoses": [
                "primary": [
                    "rotation": [0.0, 0.0, 0.0, 1.0],
                    "translation": [0.0, 0.1, 0.0],
                    "camera": [
                        "viewDirection": [0.0, 0.0, -1.0],
                        "fitPadding": 0.12,
                    ],
                ],
            ],
        ]
        presentations[0]["media"] = media
        payload["presentations"] = presentations

        let document = try decode(payload)
        guard case .model(_, _, _, let suspension, _) = document.presentations[0].media,
              case .singleCord(let singleCord) = suspension else {
            return XCTFail("expected typed single-cord suspension")
        }
        XCTAssertEqual(singleCord.type, "singleCord")
        XCTAssertEqual(singleCord.attachment.nodeID, "body-main")
        XCTAssertEqual(singleCord.attachment.pointInModel, [0.1, 0.2, 0.3])
        XCTAssertEqual(singleCord.attachment.provenance, "fixture attachment")
        XCTAssertEqual(singleCord.anchor.offsetFromBoardBounds, [0, 0.4, 0])
        XCTAssertEqual(singleCord.anchor.visibility, "invisible")
        XCTAssertEqual(singleCord.anchor.provenance, "fixture anchor")
        XCTAssertEqual(singleCord.cord.restLength, 1.25)
        XCTAssertEqual(singleCord.cord.radius, 0.004)
        XCTAssertEqual(singleCord.cord.material, "polyester")
        XCTAssertEqual(singleCord.cord.provenance, "fixture cord")
        XCTAssertEqual(singleCord.canonicalPoses["primary"]?.rotation, [0, 0, 0, 1])
        XCTAssertEqual(singleCord.canonicalPoses["primary"]?.translation, [0, 0.1, 0])
        XCTAssertEqual(
            singleCord.canonicalPoses["primary"]?.camera.viewDirection,
            [0, 0, -1]
        )
        XCTAssertEqual(singleCord.canonicalPoses["primary"]?.camera.fitPadding, 0.12)
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

    func testGeometryReadsAndWritesOnlyTheDeclaredDefaultRasterPresentation() throws {
        var document = makeDocument()
        var nonDefaultPiece = makePiece()
        nonDefaultPiece.frame = BoardPackageFrameDocument(
            x: 0.05,
            y: 0.1,
            width: 0.2,
            height: 0.3
        )
        let nonDefault = BoardEditablePresentation(
            id: "alternate",
            name: "Alternate",
            aspectRatio: 2,
            isDefault: false,
            media: .raster(
                assetPath: "assets/alternate.png",
                contactGeometry: ["hold-one": [nonDefaultPiece]]
            )
        )
        document.presentations.insert(nonDefault, at: 0)

        XCTAssertEqual(document.geometry(forContactID: "hold-one")?[0].frame.x, 0.1)

        var replacement = makePiece()
        replacement.frame = BoardPackageFrameDocument(
            x: 0.7,
            y: 0.2,
            width: 0.2,
            height: 0.3
        )
        document.replaceGeometry(forContactID: "hold-one", with: [replacement])

        guard case .raster(_, let alternateGeometry) = document.presentations[0].media,
              case .raster(_, let defaultGeometry) = document.presentations[1].media else {
            return XCTFail("expected two raster presentations")
        }
        XCTAssertEqual(alternateGeometry["hold-one"]?[0], nonDefaultPiece)
        XCTAssertEqual(defaultGeometry["hold-one"]?[0], replacement)
        XCTAssertEqual(document.geometry(forContactID: "hold-one")?[0], replacement)
    }

    func testReplacingGeometryDoesNotMutateADerivedDefaultRasterPresentation() throws {
        var document = makeDocument()
        document.presentations[0].derivation = .derived(
            sourcePresentationID: "source",
            isInverted: false
        )
        guard case .raster(_, let originalGeometry) = document.presentations[0].media else {
            return XCTFail("fixture must use raster media")
        }
        XCTAssertEqual(document.geometry(forContactID: "hold-one"), originalGeometry["hold-one"])

        var replacement = makePiece()
        replacement.frame = BoardPackageFrameDocument(
            x: 0.7,
            y: 0.2,
            width: 0.2,
            height: 0.3
        )
        document.replaceGeometry(forContactID: "hold-one", with: [replacement])

        guard case .raster(_, let geometry) = document.presentations[0].media else {
            return XCTFail("expected raster media")
        }
        XCTAssertEqual(geometry, originalGeometry)
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

    private func modelDisplay() throws -> BoardPackageModelDisplayDocument {
        try JSONDecoder().decode(
            BoardPackageModelDisplayDocument.self,
            from: Data(#"{"camera":{"type":"orthographic","viewDirection":[0,0,-1],"up":[0,1,0],"fitPadding":0.08}}"#.utf8)
        )
    }
}
