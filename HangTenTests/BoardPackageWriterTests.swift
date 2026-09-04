import XCTest
@testable import HangTen

final class BoardPackageWriterTests: XCTestCase {

    private func repositoryHangboardsURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Hangboards", isDirectory: true)
    }

    private func makePiece(
        frame: BoardPackageFrameDocument = BoardPackageFrameDocument(x: 0, y: 0, width: 1, height: 1),
        shape: BoardGeometryShapeDocument? = nil,
        shapeConstraint: ShapeConstraint? = nil,
        treatment: BoardGeometryTreatmentDocument? = nil
    ) -> BoardEditablePiece {
        let resolvedShape = shape ?? BoardGeometryShapeDocument(
            type: "path",
            commands: [
                BoardGeometryPathCommandDocument(command: "move", to: [0, 0], control: nil, control1: nil, control2: nil),
                BoardGeometryPathCommandDocument(command: "line", to: [1, 0], control: nil, control1: nil, control2: nil),
                BoardGeometryPathCommandDocument(command: "line", to: [1, 1], control: nil, control1: nil, control2: nil),
                BoardGeometryPathCommandDocument(command: "line", to: [0, 1], control: nil, control1: nil, control2: nil),
                BoardGeometryPathCommandDocument(command: "close", to: nil, control: nil, control1: nil, control2: nil),
            ],
            cornerRadiusFraction: nil
        )
        return BoardEditablePiece(
            frame: frame,
            shape: resolvedShape,
            shapeConstraint: shapeConstraint,
            treatment: treatment
        )
    }

    private func makeHold(
        id: String = "hold-one",
        name: String = "Hold one",
        kind: HoldKind = .jug,
        sloper: SloperMetadata? = nil,
        geometry: [BoardEditablePiece]? = nil
    ) -> BoardEditableHold {
        BoardEditableHold(
            id: id,
            name: name,
            kind: kind,
            sloper: sloper,
            presentationID: "front",
            geometry: geometry ?? [makePiece()]
        )
    }

    private func makeDocument(
        id: String = "test.board",
        manufacturer: String = "Test",
        name: String = "Test board",
        subtitle: String = "Fixture",
        productURL: String = "https://example.com/board",
        dimensions: String = "70 \u{00d7} 25 cm",
        aspectRatio: Double = 2.0,
        holds: [BoardEditableHold]? = nil
    ) -> BoardEditableDocument {
        BoardEditableDocument(
            id: id,
            manufacturer: manufacturer,
            name: name,
            subtitle: subtitle,
            productURL: URL(string: productURL)!,
            dimensions: dimensions,
            aspectRatio: aspectRatio,
            holds: holds ?? [makeHold()],
            presentations: [
                BoardEditablePresentation(
                    id: "front",
                    name: "Front",
                    assetPath: "assets/primary.png",
                    aspectRatio: aspectRatio,
                    isDefault: true
                )
            ]
        )
    }

    private func makeAliasDocument(
        anchor: BoardGeometryRotationAnchor? = .init(x: 0.5, y: 0.68),
        aliasAspectRatio: Double = 2.0,
        isInverted: Bool = true
    ) -> BoardEditableDocument {
        var document = makeDocument(
            holds: [
                makeHold(geometry: [
                    makePiece(
                        frame: .init(x: 0.05, y: 0.4, width: 0.1, height: 0.2)
                    ),
                    makePiece(
                        frame: .init(x: 0.35, y: 0.5, width: 0.1, height: 0.1)
                    ),
                ])
            ]
        )
        document.presentations.append(
            BoardEditablePresentation(
                id: "front-inverted",
                name: "Front upside down",
                assetPath: "assets/front-inverted.png",
                aspectRatio: aliasAspectRatio,
                isDefault: false,
                sourcePresentationID: "front",
                isInverted: isInverted,
                geometryRotationAnchor: anchor
            )
        )
        return document
    }

    private func shapeDroppingLastCommand(
        _ shape: BoardGeometryShapeDocument
    ) -> BoardGeometryShapeDocument {
        BoardGeometryShapeDocument(
            type: shape.type,
            commands: shape.commands.map { Array($0.dropLast()) },
            cornerRadiusFraction: nil
        )
    }

    private func bundledSlugs() throws -> [String] {
        try FileManager.default.contentsOfDirectory(at: repositoryHangboardsURL(), includingPropertiesForKeys: nil)
            .map(\.lastPathComponent)
            .sorted()
    }

    private func assertSemanticallyEqual(
        _ lhs: BoardEditableDocument,
        _ rhs: BoardEditableDocument,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(lhs.id, rhs.id, file: file, line: line)
        XCTAssertEqual(lhs.manufacturer, rhs.manufacturer, file: file, line: line)
        XCTAssertEqual(lhs.name, rhs.name, file: file, line: line)
        XCTAssertEqual(lhs.subtitle, rhs.subtitle, file: file, line: line)
        XCTAssertEqual(lhs.productURL.absoluteString, rhs.productURL.absoluteString, file: file, line: line)
        XCTAssertEqual(lhs.dimensions, rhs.dimensions, file: file, line: line)
        XCTAssertEqual(lhs.aspectRatio, rhs.aspectRatio, accuracy: 1e-12, file: file, line: line)
        XCTAssertEqual(lhs.equipmentObjects, rhs.equipmentObjects, file: file, line: line)
        XCTAssertEqual(lhs.presentations, rhs.presentations, file: file, line: line)
        XCTAssertEqual(lhs.holds.count, rhs.holds.count, file: file, line: line)
        for (leftHold, rightHold) in zip(lhs.holds, rhs.holds) {
            XCTAssertEqual(leftHold.id, rightHold.id, file: file, line: line)
            XCTAssertEqual(leftHold.name, rightHold.name, file: file, line: line)
            XCTAssertEqual(leftHold.kind, rightHold.kind, file: file, line: line)
            XCTAssertEqual(leftHold.sloper, rightHold.sloper, file: file, line: line)
            XCTAssertEqual(leftHold.sizeMillimeters, rightHold.sizeMillimeters, file: file, line: line)
            XCTAssertEqual(
                leftHold.depthRangeMillimeters, rightHold.depthRangeMillimeters,
                file: file, line: line
            )
            XCTAssertEqual(leftHold.gripType, rightHold.gripType, file: file, line: line)
            XCTAssertEqual(leftHold.fingerCapacity, rightHold.fingerCapacity, file: file, line: line)
            XCTAssertEqual(leftHold.handCapacity, rightHold.handCapacity, file: file, line: line)
            XCTAssertEqual(leftHold.features, rightHold.features, file: file, line: line)
            XCTAssertEqual(leftHold.geometry.count, rightHold.geometry.count, file: file, line: line)
            for (leftPiece, rightPiece) in zip(leftHold.geometry, rightHold.geometry) {
                XCTAssertEqual(leftPiece.frame.x, rightPiece.frame.x, accuracy: 1e-12, file: file, line: line)
                XCTAssertEqual(leftPiece.frame.y, rightPiece.frame.y, accuracy: 1e-12, file: file, line: line)
                XCTAssertEqual(leftPiece.frame.width, rightPiece.frame.width, accuracy: 1e-12, file: file, line: line)
                XCTAssertEqual(leftPiece.frame.height, rightPiece.frame.height, accuracy: 1e-12, file: file, line: line)
                XCTAssertEqual(leftPiece.shape.type, rightPiece.shape.type, file: file, line: line)
                if leftPiece.shape.type == "roundedRect" {
                    assertOptionalDoubleEqual(
                        leftPiece.shape.cornerRadiusFraction,
                        rightPiece.shape.cornerRadiusFraction,
                        accuracy: 1e-12,
                        file: file,
                        line: line
                    )
                } else {
                    XCTAssertEqual(
                        leftPiece.shape.commands?.count, rightPiece.shape.commands?.count,
                        file: file, line: line
                    )
                    for (leftCommand, rightCommand) in
                        zip(leftPiece.shape.commands ?? [], rightPiece.shape.commands ?? []) {
                        XCTAssertEqual(leftCommand.command, rightCommand.command, file: file, line: line)
                        for (leftValue, rightValue) in zip(leftCommand.to ?? [], rightCommand.to ?? []) {
                            XCTAssertEqual(leftValue, rightValue, accuracy: 1e-12, file: file, line: line)
                        }
                        for (leftValue, rightValue) in
                            zip(leftCommand.control ?? [], rightCommand.control ?? []) {
                            XCTAssertEqual(leftValue, rightValue, accuracy: 1e-12, file: file, line: line)
                        }
                        for (leftValue, rightValue) in
                            zip(leftCommand.control1 ?? [], rightCommand.control1 ?? []) {
                            XCTAssertEqual(leftValue, rightValue, accuracy: 1e-12, file: file, line: line)
                        }
                        for (leftValue, rightValue) in
                            zip(leftCommand.control2 ?? [], rightCommand.control2 ?? []) {
                            XCTAssertEqual(leftValue, rightValue, accuracy: 1e-12, file: file, line: line)
                        }
                    }
                }
                XCTAssertEqual(leftPiece.shapeConstraint, rightPiece.shapeConstraint, file: file, line: line)
                XCTAssertEqual(leftPiece.treatment?.type, rightPiece.treatment?.type, file: file, line: line)
                assertOptionalDoubleEqual(
                    leftPiece.treatment?.rimInsetFraction,
                    rightPiece.treatment?.rimInsetFraction,
                    accuracy: 1e-12,
                    file: file,
                    line: line
                )
                XCTAssertEqual(leftPiece.treatment?.depth, rightPiece.treatment?.depth, file: file, line: line)
            }
        }
    }

    func testWriterRoundTripPreservesOptionalSloperMetadataVariants() throws {
        let document = makeDocument(holds: [
            makeHold(
                id: "flat-angled",
                kind: .sloper,
                sloper: SloperMetadata(type: .flat, angleDegrees: 20)
            ),
            makeHold(
                id: "flat-unspecified-angle",
                kind: .sloper,
                sloper: SloperMetadata(type: .flat, angleDegrees: nil)
            ),
            makeHold(
                id: "round",
                kind: .sloper,
                sloper: SloperMetadata(type: .round, angleDegrees: nil)
            ),
            makeHold(id: "unspecified", kind: .sloper),
        ])

        let encoded = try BoardPackageWriter.data(for: document)
        let redecoded = try BoardEditableDocument(data: encoded)

        assertSemanticallyEqual(document, redecoded)
        XCTAssertEqual(redecoded.holds.map(\.sloper), [
            SloperMetadata(type: .flat, angleDegrees: 20),
            SloperMetadata(type: .flat, angleDegrees: nil),
            SloperMetadata(type: .round, angleDegrees: nil),
            nil,
        ])
    }

    func testWriterRoundTripsExplicitPositionsAndTransitions() throws {
        var document = makeDocument()
        document.positions = [
            BoardPosition(id: "front", presentationID: "front"),
            BoardPosition(id: "flipped", presentationID: "front-inverted"),
        ]
        document.positionTransitions = [
            BoardPositionTransition(
                fromPositionID: "front",
                toPositionID: "flipped",
                kind: .seamless
            ),
        ]
        document.presentations.append(
            BoardEditablePresentation(
                id: "front-inverted",
                name: "Front inverted",
                assetPath: "assets/front-inverted.png",
                aspectRatio: 2,
                isDefault: false,
                sourcePresentationID: "front",
                isInverted: true
            )
        )

        let redecoded = try BoardEditableDocument(data: BoardPackageWriter.data(for: document))

        XCTAssertEqual(redecoded.positions, document.positions)
        XCTAssertEqual(redecoded.positionTransitions, document.positionTransitions)
    }

    func testWriterLeavesLegacyTwoPresentationDocumentsWithoutExplicitPositions() throws {
        var document = makeDocument()
        var backHold = makeHold(id: "back-hold", name: "Back hold")
        backHold.presentationID = "back"
        document.holds.append(backHold)
        document.presentations.append(
            BoardEditablePresentation(
                id: "back",
                name: "Back",
                assetPath: "assets/back.png",
                aspectRatio: 2,
                isDefault: false
            )
        )

        let data = try BoardPackageWriter.data(for: document)
        let decoded = try BoardEditableDocument(data: data)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])

        XCTAssertNil(decoded.positions)
        XCTAssertNil(decoded.positionTransitions)
        XCTAssertNil(object["positions"])
        XCTAssertNil(object["positionTransitions"])
    }

    func testWriterRejectsHoldWithUnknownEquipmentObject() throws {
        var document = makeDocument()
        document.equipmentObjects = [EquipmentObject(id: "primary")]
        document.holds[0].equipmentObjectID = "missing"

        XCTAssertThrowsError(try BoardPackageWriter.data(for: document))
    }

    func testWriterRoundTripsExplicitEquipmentObjectAssignments() throws {
        var document = makeDocument()
        document.equipmentObjects = [EquipmentObject(id: "left"), EquipmentObject(id: "right")]
        document.holds = [
            makeHold(id: "left-hold", name: "Left hold"),
            makeHold(id: "right-hold", name: "Right hold"),
        ]
        document.holds[0].equipmentObjectID = "left"
        document.holds[1].equipmentObjectID = "right"

        let redecoded = try BoardEditableDocument(data: BoardPackageWriter.data(for: document))

        XCTAssertEqual(redecoded.equipmentObjects.map(\.id), ["left", "right"])
        XCTAssertEqual(redecoded.holds.map(\.equipmentObjectID), ["left", "right"])
    }

    func testWriterRoundTripsStrictMissingHandCapacityPolicy() throws {
        var document = makeDocument()
        document.equipmentObjects = [
            EquipmentObject(
                id: "primary",
                missingHandCapacityPolicy: .unavailable
            )
        ]

        let encoded = try BoardPackageWriter.data(for: document)
        let redecoded = try BoardEditableDocument(data: encoded)

        XCTAssertEqual(
            redecoded.equipmentObjects.first?.missingHandCapacityPolicy,
            .unavailable
        )
        let json = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )
        let equipmentObjects = try XCTUnwrap(
            json["equipmentObjects"] as? [[String: Any]]
        )
        XCTAssertEqual(
            equipmentObjects.first?["missingHandCapacityPolicy"] as? String,
            "unavailable"
        )
    }

    func testWriterRejectsInvalidSloperMetadataCombinations() throws {
        let invalidHolds = [
            makeHold(
                kind: .jug,
                sloper: SloperMetadata(type: .flat, angleDegrees: 20)
            ),
            makeHold(
                kind: .sloper,
                sloper: SloperMetadata(type: .round, angleDegrees: 20)
            ),
            makeHold(
                kind: .sloper,
                sloper: SloperMetadata(type: .flat, angleDegrees: -0.01)
            ),
            makeHold(
                kind: .sloper,
                sloper: SloperMetadata(type: .flat, angleDegrees: 90.01)
            ),
            makeHold(
                kind: .sloper,
                sloper: SloperMetadata(type: .flat, angleDegrees: .infinity)
            ),
        ]

        for invalidHold in invalidHolds {
            XCTAssertThrowsError(
                try BoardPackageWriter.data(for: makeDocument(holds: [invalidHold]))
            )
        }
    }

    private func assertOptionalDoubleEqual(
        _ lhs: Double?,
        _ rhs: Double?,
        accuracy: Double,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        switch (lhs, rhs) {
        case (nil, nil):
            break
        case (let left?, let right?):
            XCTAssertEqual(left, right, accuracy: accuracy, file: file, line: line)
        default:
            XCTFail("optional double presence mismatch", file: file, line: line)
        }
    }

    func testRoundTripEveryBundledPackageIsSemanticallyIdentical() throws {
        for slug in try bundledSlugs() {
            let originalData = try Data(
                contentsOf: repositoryHangboardsURL().appendingPathComponent("\(slug)/board.json")
            )
            let decoded = try BoardEditableDocument(data: originalData)
            let encoded = try BoardPackageWriter.data(for: decoded)
            let redecoded = try BoardEditableDocument(data: encoded)

            if redecoded != decoded {
                let difference = Self.describeFirstDifference(decoded, redecoded)
                    ?? "documents compare unequal at an unknown field"
                XCTFail("round-trip \(slug): redecoded document differs; first difference: \(difference)")
                continue
            }

            let reencoded = try BoardPackageWriter.data(for: redecoded)
            XCTAssertEqual(
                encoded, reencoded,
                "encoding must be a deterministic fixpoint for \(slug)"
            )
        }
    }

    func testEveryBundledPackageExplicitlyAssignsEveryHoldToAnEquipmentObject() throws {
        for slug in try bundledSlugs() {
            let data = try Data(
                contentsOf: repositoryHangboardsURL().appendingPathComponent("\(slug)/board.json")
            )
            let document = try XCTUnwrap(
                JSONSerialization.jsonObject(with: data) as? [String: Any],
                "\(slug) board document"
            )
            let objects = try XCTUnwrap(document["equipmentObjects"] as? [[String: Any]])
            XCTAssertFalse(objects.isEmpty, "\(slug) must declare equipment objects")
            let holds = try XCTUnwrap(document["holds"] as? [[String: Any]])

            for hold in holds {
                let holdID = try XCTUnwrap(hold["id"] as? String)
                XCTAssertNotNil(
                    hold["equipmentObjectID"] as? String,
                    "\(slug) hold \(holdID) must explicitly declare equipmentObjectID"
                )
            }
        }
    }

    func testWriterRoundTripPreservesOmittedDimensions() throws {
        let source = String(decoding: try BoardPackageWriter.data(for: makeDocument()), as: UTF8.self)
        let withoutDimensions = source.replacingOccurrences(
            of: "  \"dimensions\": \"70 \\u00d7 25 cm\",\n",
            with: ""
        )
        XCTAssertNotEqual(withoutDimensions, source)

        let decoded = try BoardEditableDocument(data: Data(withoutDimensions.utf8))
        XCTAssertNil(decoded.dimensions)

        let reencoded = try BoardPackageWriter.data(for: decoded)
        let output = String(decoding: reencoded, as: UTF8.self)
        XCTAssertFalse(output.contains("\"dimensions\""))
        XCTAssertNil(try BoardEditableDocument(data: reencoded).dimensions)
    }

    func testWriterRejectsExplicitlyEmptyDimensions() throws {
        let source = String(decoding: try BoardPackageWriter.data(for: makeDocument()), as: UTF8.self)
        let emptyDimensions = source.replacingOccurrences(
            of: "\"dimensions\": \"70 \\u00d7 25 cm\"",
            with: "\"dimensions\": \"\""
        )
        XCTAssertNotEqual(emptyDimensions, source)

        let decoded = try BoardEditableDocument(data: Data(emptyDimensions.utf8))
        XCTAssertThrowsError(try BoardPackageWriter.data(for: decoded)) { error in
            XCTAssertEqual(
                error as? BoardPackageWriterError,
                .invalid("board test.board: dimensions must not be empty when present")
            )
        }
    }

    func testEditorDocumentRoundTripsFlashBoardOrientationAliases() throws {
        let originalData = try Data(
            contentsOf: repositoryHangboardsURL()
                .appendingPathComponent("tension-flash-board/board.json")
        )
        let decoded = try BoardEditableDocument(data: originalData)

        let encoded = try BoardPackageWriter.data(for: decoded)
        let redecoded = try BoardEditableDocument(data: encoded)

        assertSemanticallyEqual(decoded, redecoded)
        XCTAssertEqual(encoded, try BoardPackageWriter.data(for: redecoded))
    }

    func testWriterRejectsInvalidPresentationAliasesAndAliasOwnedHoldsInEditorDocuments() throws {
        let encoded = try BoardPackageWriter.data(for: makeDocument())
        let source = String(decoding: encoded, as: UTF8.self)

        let invalidAliasSources = ["front-inverted", "unknown"]
        for sourcePresentationID in invalidAliasSources {
            let document = try editorDocument(
                source.replacingOccurrences(
                    of: "      \"default\": true\n",
                    with: "      \"default\": true,\n"
                        + "      \"sourcePresentationID\": \"\(sourcePresentationID)\",\n"
                        + "      \"isInverted\": true\n"
                )
            )

            XCTAssertThrowsError(try BoardPackageWriter.data(for: document)) { error in
                XCTAssertEqual(
                    error as? BoardPackageWriterError,
                    .invalid(
                        "board test.board: presentation front must reference a canonical presentation"
                    )
                )
            }
        }

        let aliasPresentation = """
            },
            {
              \"id\": \"front-inverted\",
              \"name\": \"Front upside down\",
              \"assetPath\": \"assets/front-inverted.png\",
              \"aspectRatio\": 2.0,
              \"default\": false,
              \"sourcePresentationID\": \"front\",
              \"isInverted\": true
            }
        """
        let withAlias = source.replacingOccurrences(
            of: "    }\n  ]\n}\n",
            with: aliasPresentation + "\n  ]\n}\n"
        )
        var aliasOwnedHold = try editorDocument(withAlias)
        var copiedHold = try XCTUnwrap(aliasOwnedHold.holds.first)
        copiedHold.id = "alias-owned-hold"
        copiedHold.presentationID = "front-inverted"
        aliasOwnedHold.holds.append(copiedHold)

        XCTAssertThrowsError(try BoardPackageWriter.data(for: aliasOwnedHold)) { error in
            XCTAssertEqual(
                error as? BoardPackageWriterError,
                .invalid(
                    "board test.board: hold alias-owned-hold must be owned by a canonical presentation"
                )
            )
        }
    }

    func testWriterRoundTripsAliasRotationAnchorInCanonicalOrder() throws {
        let input = try BoardPackageWriter.data(for: makeAliasDocument())
        let document = try BoardEditableDocument(data: input)

        let encoded = try BoardPackageWriter.data(for: document)
        let redecoded = try BoardEditableDocument(data: encoded)

        XCTAssertEqual(redecoded, document)
        XCTAssertEqual(try BoardPackageWriter.data(for: redecoded), encoded)
        XCTAssertEqual(
            redecoded.presentations[1].geometryRotationAnchor,
            BoardGeometryRotationAnchor(x: 0.5, y: 0.68)
        )
        XCTAssertTrue(
            String(decoding: encoded, as: UTF8.self).contains(
                "      \"isInverted\": true,\n"
                    + "      \"geometryRotationAnchor\": {\n"
                    + "        \"x\": 0.5,\n"
                    + "        \"y\": 0.68\n"
                    + "      }\n"
            )
        )
    }

    func testWriterOmitsAbsentAliasRotationAnchor() throws {
        let document = makeAliasDocument(anchor: nil)

        let encoded = try BoardPackageWriter.data(for: document)
        let redecoded = try BoardEditableDocument(data: encoded)

        XCTAssertNil(redecoded.presentations[1].geometryRotationAnchor)
        XCTAssertFalse(String(decoding: encoded, as: UTF8.self).contains("geometryRotationAnchor"))
    }

    func testWriterRejectsRotationAnchorOnCanonicalPresentation() throws {
        var document = makeDocument()
        document.presentations[0].geometryRotationAnchor = .center

        assertWriterInvalid(
            document,
            reason: "presentation front.geometryRotationAnchor requires sourcePresentationID"
        )
    }

    func testWriterRejectsRotationAnchorOnNonInvertedAlias() throws {
        assertWriterInvalid(
            makeAliasDocument(isInverted: false),
            reason: "presentation front-inverted.geometryRotationAnchor requires isInverted true"
        )
    }

    func testWriterRejectsNonFiniteRotationAnchor() throws {
        assertWriterInvalid(
            makeAliasDocument(anchor: .init(x: .infinity, y: 0.68)),
            reason: "presentation front-inverted.geometryRotationAnchor must contain finite normalized coordinates"
        )
    }

    func testWriterRejectsRotationAnchorCoordinatesOutsideTheNormalizedRange() throws {
        for anchor in [
            BoardGeometryRotationAnchor(x: 1.01, y: 0.68),
            BoardGeometryRotationAnchor(x: 0.5, y: -0.01),
        ] {
            assertWriterInvalid(
                makeAliasDocument(anchor: anchor),
                reason: "presentation front-inverted.geometryRotationAnchor must contain finite normalized coordinates"
            )
        }
    }

    func testWriterRejectsAliasAspectMismatch() throws {
        assertWriterInvalid(
            makeAliasDocument(aliasAspectRatio: 2.0001),
            reason: "presentation front-inverted.aspectRatio must match source presentation aspectRatio"
        )
    }

    func testWriterAcceptsTaskOneAliasAspectRoundingTolerance() throws {
        XCTAssertNoThrow(
            try BoardPackageWriter.data(
                for: makeAliasDocument(aliasAspectRatio: 2.000000001)
            )
        )
    }

    func testWriterAcceptsProjectedFrameOnArithmeticNoiseBoundary() throws {
        var document = makeAliasDocument(anchor: .init(x: 0.15, y: 0.15))
        document.holds[0].geometry[0] = makePiece(
            frame: .init(x: 0.1, y: 0.1, width: 0.2, height: 0.2)
        )
        document.holds[0].geometry[1] = makePiece(
            frame: .init(x: 0.12, y: 0.12, width: 0.1, height: 0.1)
        )

        XCTAssertNoThrow(try BoardPackageWriter.data(for: document))
    }

    func testWriterRejectsAnOffCanvasLaterPieceOfALaterSourceHold() throws {
        var document = makeAliasDocument()
        document.holds.append(
            makeHold(
                id: "hold-front-later",
                name: "Later front hold",
                geometry: [
                    makePiece(frame: .init(x: 0.05, y: 0.4, width: 0.1, height: 0.2)),
                    makePiece(frame: .init(x: 0.95, y: 0.5, width: 0.1, height: 0.1)),
                ]
            )
        )
        assertWriterInvalid(
            document,
            reason: "presentation front-inverted projects source hold geometry outside the normalized canvas"
        )
    }

    func testEditorStrictlyDecodesRotationAnchorObjectAndNumericCoordinates() throws {
        let encoded = try BoardPackageWriter.data(for: makeAliasDocument())
        let source = String(decoding: encoded, as: UTF8.self)
        let invalidSources = [
            source.replacingOccurrences(of: "        \"x\": 0.5,\n", with: ""),
            source.replacingOccurrences(of: "        \"y\": 0.68", with: "        \"y\": 0.68,\n        \"unexpected\": 1"),
            source.replacingOccurrences(of: "        \"x\": 0.5", with: "        \"x\": true"),
            source.replacingOccurrences(of: "        \"x\": 0.5", with: "        \"x\": 1e999"),
            source.replacingOccurrences(
                of: "{\n        \"x\": 0.5,\n        \"y\": 0.68\n      }",
                with: "null"
            ),
            source.replacingOccurrences(
                of: "{\n        \"x\": 0.5,\n        \"y\": 0.68\n      }",
                with: "\"center\""
            ),
        ]

        for invalidSource in invalidSources {
            XCTAssertNotEqual(invalidSource, source)
            XCTAssertThrowsError(try editorDocument(invalidSource))
        }
    }

    private func assertWriterInvalid(
        _ document: BoardEditableDocument,
        reason: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertThrowsError(try BoardPackageWriter.data(for: document), file: file, line: line) {
            XCTAssertEqual(
                $0 as? BoardPackageWriterError,
                .invalid("board \(document.id): \(reason)"),
                file: file,
                line: line
            )
        }
    }

    private func editorDocument(_ source: String) throws -> BoardEditableDocument {
        try BoardEditableDocument(data: Data(source.utf8))
    }

    private static func describeFirstDifference(
        _ left: BoardEditableDocument,
        _ right: BoardEditableDocument
    ) -> String? {
        if left.holds.count != right.holds.count {
            return "hold count \(left.holds.count) != \(right.holds.count)"
        }
        for (holdIndex, leftHold) in left.holds.enumerated() {
            let rightHold = right.holds[holdIndex]
            if leftHold.id != rightHold.id { return "holds[\(holdIndex)].id \(leftHold.id) != \(rightHold.id)" }
            if leftHold.name != rightHold.name { return "\(leftHold.id) name differs" }
            if leftHold.kind != rightHold.kind { return "\(leftHold.id) kind differs" }
            if leftHold.sloper != rightHold.sloper { return "\(leftHold.id) sloper metadata differs" }
            if leftHold.sizeMillimeters != rightHold.sizeMillimeters { return "\(leftHold.id) size differs" }
            if leftHold.depthRangeMillimeters != rightHold.depthRangeMillimeters { return "\(leftHold.id) depth differs" }
            if leftHold.gripType != rightHold.gripType { return "\(leftHold.id) gripType differs" }
            if leftHold.fingerCapacity != rightHold.fingerCapacity { return "\(leftHold.id) fingerCapacity differs" }
            if leftHold.handCapacity != rightHold.handCapacity { return "\(leftHold.id) handCapacity differs" }
            if leftHold.features != rightHold.features { return "\(leftHold.id) features differ" }
            if leftHold.geometry.count != rightHold.geometry.count {
                return "\(leftHold.id) piece count \(leftHold.geometry.count) != \(rightHold.geometry.count)"
            }
            for (pieceIndex, leftPiece) in leftHold.geometry.enumerated() {
                let rightPiece = rightHold.geometry[pieceIndex]
                let label = "\(leftHold.id).geometry[\(pieceIndex)]"
                if leftPiece.frame != rightPiece.frame { return "\(label) frame \(leftPiece.frame) != \(rightPiece.frame)" }
                if leftPiece.shape.type != rightPiece.shape.type { return "\(label) shape type differs" }
                if leftPiece.shape.cornerRadiusFraction != rightPiece.shape.cornerRadiusFraction {
                    return "\(label) corner radius differs"
                }
                if leftPiece.shapeConstraint != rightPiece.shapeConstraint {
                    return "\(label) constraint \(String(describing: leftPiece.shapeConstraint)) != \(String(describing: rightPiece.shapeConstraint))"
                }
                if leftPiece.treatment != rightPiece.treatment { return "\(label) treatment differs" }
                let leftCommands = leftPiece.shape.commands ?? []
                let rightCommands = rightPiece.shape.commands ?? []
                if leftCommands.count != rightCommands.count {
                    return "\(label) command count \(leftCommands.count) != \(rightCommands.count)"
                }
                for (commandIndex, leftCommand) in leftCommands.enumerated() {
                    let rightCommand = rightCommands[commandIndex]
                    if leftCommand != rightCommand {
                        return "\(label).commands[\(commandIndex)] \(describeCommand(leftCommand)) != \(describeCommand(rightCommand))"
                    }
                }
            }
        }
        return nil
    }

    private static func describeCommand(_ command: BoardGeometryPathCommandDocument) -> String {
        "\(command.command) to=\(command.to.map(describePoint) ?? "nil")"
            + " control=\(command.control.map(describePoint) ?? "nil")"
            + " control1=\(command.control1.map(describePoint) ?? "nil")"
            + " control2=\(command.control2.map(describePoint) ?? "nil")"
    }

    private static func describePoint(_ values: [Double]) -> String {
        values.map { value in
            String(format: "%.17g", value)
        }.joined(separator: ",")
    }

    func testCanonicalFormattingMatchesRepositoryConventions() throws {
        let document = makeDocument(
            id: "zlagboard.pro",
            dimensions: "70.5 \u{00d7} 25 cm",
            aspectRatio: 2.0,
            holds: [
                BoardEditableHold(
                    id: "edge-7-5-left",
                    name: "Left 7.5 mm edge",
                    kind: .edge,
                    sizeMillimeters: 7.5,
                    gripType: .halfCrimp,
                    fingerCapacity: 4,
                    handCapacity: 1,
                    features: [.incutEdge, .flatEdge],
                    presentationID: "front",
                    geometry: [
                        BoardEditablePiece(
                            frame: BoardPackageFrameDocument(x: 0.04, y: 0.479, width: 0.133, height: 0.11),
                            shape: BoardGeometryShapeDocument(
                                type: "path",
                                commands: [
                                    BoardGeometryPathCommandDocument(command: "move", to: [0.14673781227261695, 0], control: nil, control1: nil, control2: nil),
                                    BoardGeometryPathCommandDocument(command: "quad", to: [1, 0.5000000000000006], control: [1, 0], control1: nil, control2: nil),
                                    BoardGeometryPathCommandDocument(command: "curve", to: [0, 0], control: nil, control1: [-3.125e-06, 0.5], control2: [0, 0.2238576347894534]),
                                    BoardGeometryPathCommandDocument(command: "close", to: nil, control: nil, control1: nil, control2: nil),
                                ],
                                cornerRadiusFraction: nil
                            ),
                            shapeConstraint: ShapeConstraint(shape: .pill, rotationDegrees: 0),
                            treatment: BoardGeometryTreatmentDocument(type: "recess", rimInsetFraction: 0.12, depth: "deep")
                        )
                    ]
                )
            ]
        )

        let encoded = try BoardPackageWriter.data(for: document)
        let output = String(decoding: encoded, as: UTF8.self)
        XCTAssertTrue(output.hasPrefix("{\n  \"id\": \"zlagboard.pro\",\n"))
        XCTAssertTrue(output.contains("  \"dimensions\": \"70.5 \\u00d7 25 cm\",\n"))
        XCTAssertTrue(output.contains("  \"aspectRatio\": 2.0,\n"))
        XCTAssertTrue(output.contains("\"sizeMillimeters\": 7.5"))
        XCTAssertTrue(output.contains(
            "          \"shapeConstraint\": {\n"
                + "            \"shape\": \"pill\",\n"
                + "            \"rotationDegrees\": 0.0\n"
                + "          },\n"
        ))
        XCTAssertTrue(output.contains("\"control1\": [\n                  -3.125e-06,\n                  0.5\n                ]"))
        XCTAssertTrue(output.contains("\"to\": [\n                  1.0,\n                  0.5000000000000006\n                ]"))
        XCTAssertTrue(output.contains(
            "          \"treatment\": {\n"
                + "            \"type\": \"recess\",\n"
                + "            \"rimInsetFraction\": 0.12,\n"
                + "            \"depth\": \"deep\"\n"
                + "          }\n"
        ))
        XCTAssertTrue(output.contains("  \"features\": [\n        \"incutEdge\",\n        \"flatEdge\"\n      ],\n"))
        let expectedPresentations = [
            "  \"presentations\": [",
            "    {",
            "      \"id\": \"front\",",
            "      \"name\": \"Front\",",
            "      \"assetPath\": \"assets/primary.png\",",
            "      \"aspectRatio\": 2.0,",
            "      \"default\": true",
            "    }",
            "  ]",
        ]
        for expectedLine in expectedPresentations {
            XCTAssertTrue(output.contains(expectedLine + "\n"), "missing line: \(expectedLine)")
        }
        XCTAssertTrue(output.hasSuffix("}\n"))

        let lines = output.split(separator: "\n").map(String.init)
        XCTAssertEqual(lines[0], "{")
        XCTAssertEqual(lines[1], "  \"id\": \"zlagboard.pro\",")
        XCTAssertEqual(lines.last, "}")

        let redecoded = try BoardEditableDocument(data: encoded)
        assertSemanticallyEqual(document, redecoded)
    }

    func testDirectTwoAnchorCordRigRoundTripsInCanonicalOrder() throws {
        let initialBytes = try BoardPackageWriter.data(
            for: makeDocument(aspectRatio: 50.0 / 61.0)
        )
        var payload = try XCTUnwrap(
            JSONSerialization.jsonObject(with: initialBytes) as? [String: Any]
        )
        var presentations = try XCTUnwrap(payload["presentations"] as? [[String: Any]])
        presentations[0]["cordRig"] = [
            "type": "directTwoAnchor",
            "sceneSize": ["width": 1200, "height": 1464],
            "sourceFrame": ["x": 0, "y": 214, "width": 1200, "height": 1250],
            "innerFaceFrame": ["x": -100, "y": -10, "width": 1400, "height": 1400],
            "attachmentPoints": [
                ["x": 203, "y": 712],
                ["x": 997, "y": 712],
            ],
            "pullPoint": ["x": 600, "y": 71.5],
            "eyeletRadius": 34,
        ]
        payload["presentations"] = presentations

        let decoded = try BoardEditableDocument(
            data: JSONSerialization.data(withJSONObject: payload)
        )
        let expectedRig = BoardCordRig.directTwoAnchor(
            BoardDirectTwoAnchorCordRig(
                sceneSize: BoardCordSize(width: 1200, height: 1464),
                sourceFrame: BoardCordRect(x: 0, y: 214, width: 1200, height: 1250),
                innerFaceFrame: BoardCordRect(x: -100, y: -10, width: 1400, height: 1400),
                attachmentPoints: [
                    BoardCordPoint(x: 203, y: 712),
                    BoardCordPoint(x: 997, y: 712),
                ],
                pullPoint: BoardCordPoint(x: 600, y: 71.5),
                eyeletRadius: 34
            )
        )
        XCTAssertEqual(decoded.presentations.first?.cordRig, expectedRig)

        let encoded = try BoardPackageWriter.data(for: decoded)
        let redecoded = try BoardEditableDocument(data: encoded)

        XCTAssertEqual(redecoded, decoded)
        XCTAssertEqual(try BoardPackageWriter.data(for: redecoded), encoded)

        let topLevelRigKeys = String(decoding: encoded, as: UTF8.self)
            .split(separator: "\n", omittingEmptySubsequences: false)
            .compactMap { line -> String? in
                guard line.hasPrefix("        \"") && !line.hasPrefix("          \"") else {
                    return nil
                }
                return line.dropFirst(9).split(separator: "\"", maxSplits: 1).first.map(String.init)
            }
        XCTAssertEqual(
            topLevelRigKeys,
            [
                "type", "sceneSize", "sourceFrame", "innerFaceFrame",
                "attachmentPoints", "pullPoint", "eyeletRadius",
            ]
        )
    }

    func testReencodedRealPackageKeepsTopLevelOrderEscapesAndTrailingNewline() throws {
        let slug = "zlagboard-pro"
        let originalData = try Data(
            contentsOf: repositoryHangboardsURL().appendingPathComponent("\(slug)/board.json")
        )
        let decoded = try BoardEditableDocument(data: originalData)
        let encoded = try BoardPackageWriter.data(for: decoded)
        let output = String(decoding: encoded, as: UTF8.self)

        XCTAssertEqual(
            output.hasPrefix("{\n  \"id\": \"zlagboard.pro\",\n  \"manufacturer\": \"Zlagboard\","),
            true
        )
        XCTAssertTrue(output.contains("\\u00d7"), "non-ASCII multiplication sign must be escaped")
        XCTAssertTrue(output.hasSuffix("}\n"))
    }

    func testWriterRejectsLoaderInvalidDocuments() throws {
        var openPath = makeDocument()
        openPath.holds[0].geometry[0].shape = shapeDroppingLastCommand(
            openPath.holds[0].geometry[0].shape
        )
        XCTAssertThrowsError(try BoardPackageWriter.data(for: openPath))

        var secondMove = makeDocument()
        var secondMoveCommands = secondMove.holds[0].geometry[0].shape.commands ?? []
        secondMoveCommands[2] =
            BoardGeometryPathCommandDocument(command: "move", to: [1, 1], control: nil, control1: nil, control2: nil)
        secondMove.holds[0].geometry[0].shape = BoardGeometryShapeDocument(
            type: "path",
            commands: secondMoveCommands,
            cornerRadiusFraction: nil
        )
        XCTAssertThrowsError(try BoardPackageWriter.data(for: secondMove))

        var rotatedTooFar = makeDocument()
        rotatedTooFar.holds[0].geometry[0].shapeConstraint = ShapeConstraint(shape: .rectangle, rotationDegrees: 180)
        XCTAssertThrowsError(try BoardPackageWriter.data(for: rotatedTooFar))

        var unknownShape = makeDocument()
        unknownShape.holds[0].geometry[0] = BoardEditablePiece(
            frame: unknownShape.holds[0].geometry[0].frame,
            shape: BoardGeometryShapeDocument(type: "blob", commands: nil, cornerRadiusFraction: nil),
            shapeConstraint: nil,
            treatment: nil
        )
        XCTAssertThrowsError(try BoardPackageWriter.data(for: unknownShape))

        var oversizedRadius = makeDocument()
        oversizedRadius.holds[0].geometry[0] = BoardEditablePiece(
            frame: oversizedRadius.holds[0].geometry[0].frame,
            shape: BoardGeometryShapeDocument(type: "roundedRect", commands: nil, cornerRadiusFraction: 0.6),
            shapeConstraint: nil,
            treatment: nil
        )
        XCTAssertThrowsError(try BoardPackageWriter.data(for: oversizedRadius))

        var shelfWithoutInset = makeDocument()
        shelfWithoutInset.holds[0].geometry[0].treatment =
            BoardGeometryTreatmentDocument(type: "shelf", rimInsetFraction: nil, depth: nil)
        XCTAssertThrowsError(try BoardPackageWriter.data(for: shelfWithoutInset))

        var recessWithBadDepth = makeDocument()
        recessWithBadDepth.holds[0].geometry[0].treatment =
            BoardGeometryTreatmentDocument(type: "recess", rimInsetFraction: 0.1, depth: "bottomless")
        XCTAssertThrowsError(try BoardPackageWriter.data(for: recessWithBadDepth))

        XCTAssertThrowsError(
            try BoardPackageWriter.data(for: makeDocument(productURL: "http://example.com/board"))
        )
        XCTAssertThrowsError(
            try BoardPackageWriter.data(for: makeDocument(id: "Not A Slug"))
        )

        var badCapacity = makeDocument()
        badCapacity.holds[0].fingerCapacity = 5
        XCTAssertThrowsError(try BoardPackageWriter.data(for: badCapacity))

        var duplicateFeatures = makeDocument()
        duplicateFeatures.holds[0].features = [.mediumEdge, .mediumEdge]
        XCTAssertThrowsError(try BoardPackageWriter.data(for: duplicateFeatures))

        var zeroSize = makeDocument()
        zeroSize.holds[0].sizeMillimeters = 0
        XCTAssertThrowsError(try BoardPackageWriter.data(for: zeroSize))

        var invertedDepth = makeDocument()
        invertedDepth.holds[0].depthRangeMillimeters = BoardEditableMillimeterRange(lowerBound: 20, upperBound: 5)
        XCTAssertThrowsError(try BoardPackageWriter.data(for: invertedDepth))

        var conflictingDepthForms = makeDocument()
        conflictingDepthForms.holds[0].sizeMillimeters = 7.5
        conflictingDepthForms.holds[0].depthRangeMillimeters = BoardEditableMillimeterRange(
            lowerBound: 7.5,
            upperBound: 12.5
        )
        XCTAssertThrowsError(try BoardPackageWriter.data(for: conflictingDepthForms)) { error in
            XCTAssertEqual(
                error as? BoardPackageWriterError,
                .invalid("board test.board: hold hold-one must not specify both a size and depth range")
            )
        }

        let emptyGeometry = makeDocument(holds: [makeHold(geometry: [])])
        XCTAssertThrowsError(try BoardPackageWriter.data(for: emptyGeometry))

        let noHolds = makeDocument(holds: [])
        XCTAssertThrowsError(try BoardPackageWriter.data(for: noHolds))
    }

    func testBendableMarkSurvivesRoundTrip() throws {
        var document = makeDocument()
        document.holds[0].geometry[0].shape = BoardGeometryShapeDocument(
            type: "path",
            commands: [
                BoardGeometryPathCommandDocument(command: "move", to: [0, 0], control: nil, control1: nil, control2: nil),
                BoardGeometryPathCommandDocument(
                    command: "curve",
                    to: [1, 1],
                    control: nil,
                    control1: [0.25, 0],
                    control2: [0.75, 0.5],
                    bendable: true
                ),
                BoardGeometryPathCommandDocument(command: "close", to: nil, control: nil, control1: nil, control2: nil),
            ],
            cornerRadiusFraction: nil
        )

        let encoded = try BoardPackageWriter.data(for: document)
        let output = String(decoding: encoded, as: UTF8.self)
        XCTAssertTrue(output.contains("\"bendable\": true"))
        let redecoded = try BoardEditableDocument(data: encoded)
        XCTAssertEqual(
            redecoded.holds[0].geometry[0].shape.commands?[1].bendable,
            true
        )
    }

    func testSmoothMarkSurvivesRoundTrip() throws {
        var document = makeDocument()
        document.holds[0].geometry[0].shape = BoardGeometryShapeDocument(
            type: "path",
            commands: [
                BoardGeometryPathCommandDocument(command: "move", to: [0, 0], control: nil, control1: nil, control2: nil),
                BoardGeometryPathCommandDocument(
                    command: "curve",
                    to: [1, 1],
                    control: nil,
                    control1: [0.25, 0],
                    control2: [0.75, 0.5],
                    smooth: true
                ),
                BoardGeometryPathCommandDocument(command: "close", to: nil, control: nil, control1: nil, control2: nil),
            ],
            cornerRadiusFraction: nil
        )

        let encoded = try BoardPackageWriter.data(for: document)
        let output = String(decoding: encoded, as: UTF8.self)
        XCTAssertTrue(output.contains("\"smooth\": true"))
        let redecoded = try BoardEditableDocument(data: encoded)
        XCTAssertEqual(
            redecoded.holds[0].geometry[0].shape.commands?[1].smooth,
            true
        )
    }

    func testStrictDecoderRejectsUnknownKeys() throws {
        var document = makeDocument()
        let encoded = try BoardPackageWriter.data(for: document)

        var tampered = String(decoding: encoded, as: UTF8.self)
        tampered = tampered.replacingOccurrences(
            of: "\"dimensions\":",
            with: "\"legacyField\": true,\n  \"dimensions\":"
        )
        XCTAssertThrowsError(try BoardEditableDocument(data: Data(tampered.utf8)))

        document.holds[0].geometry[0].shapeConstraint = ShapeConstraint(
            shape: .roundedRectangle,
            rotationDegrees: -179.5
        )
        let constrainedBytes = try BoardPackageWriter.data(for: document)
        let redecoded = try BoardEditableDocument(data: constrainedBytes)
        XCTAssertEqual(redecoded.holds[0].geometry[0].shapeConstraint?.rotationDegrees, -179.5)
    }

    func testEditorDecoderRejectsUnknownKeysInEquipmentObjects() throws {
        let encoded = try BoardPackageWriter.data(for: makeDocument())
        var document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )
        document["equipmentObjects"] = [["id": "primary", "unexpected": true]]

        XCTAssertThrowsError(
            try BoardEditableDocument(data: JSONSerialization.data(withJSONObject: document))
        )
    }

    func testEditorDecoderRejectsUnknownKeysInPositions() throws {
        let encoded = try BoardPackageWriter.data(for: makeDocument())
        var document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )
        document["positions"] = [[
            "id": "front",
            "presentationID": "front",
            "unexpected": true,
        ]]

        XCTAssertThrowsError(
            try BoardEditableDocument(data: JSONSerialization.data(withJSONObject: document))
        )
    }

    func testEditorDecoderRejectsUnknownKeysInPositionTransitions() throws {
        let encoded = try BoardPackageWriter.data(for: makeDocument())
        var document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )
        document["positionTransitions"] = [[
            "fromPositionID": "front",
            "toPositionID": "flipped",
            "kind": "seamless",
            "unexpected": true,
        ]]

        XCTAssertThrowsError(
            try BoardEditableDocument(data: JSONSerialization.data(withJSONObject: document))
        )
    }

    func testEditorDecoderPreservesOmittedKindButRejectsNullKind() throws {
        let encoded = try BoardPackageWriter.data(for: makeDocument())
        let source = String(decoding: encoded, as: UTF8.self)
        let kind = "      \"kind\": \"jug\",\n"

        let omittedKind = source.replacingOccurrences(of: kind, with: "")
        let decoded = try BoardEditableDocument(data: Data(omittedKind.utf8))
        XCTAssertNil(decoded.holds[0].kind)

        let nullKind = source.replacingOccurrences(of: kind, with: "      \"kind\": null,\n")
        XCTAssertThrowsError(try BoardEditableDocument(data: Data(nullKind.utf8)))

        let unsupportedKind = source.replacingOccurrences(of: kind, with: "      \"kind\": \"unsupported\",\n")
        XCTAssertThrowsError(try BoardEditableDocument(data: Data(unsupportedKind.utf8)))
    }

    func testEditorDecoderRejectsExplicitNullPairedHoldIDOnNonGaston() throws {
        let encoded = try BoardPackageWriter.data(for: makeDocument())
        let source = String(decoding: encoded, as: UTF8.self)
        let insertion = "      \"pairedHoldID\": null,\n"
        let tampered = source.replacingOccurrences(
            of: "      \"presentationID\": \"front\",\n",
            with: insertion + "      \"presentationID\": \"front\",\n"
        )

        XCTAssertThrowsError(try BoardEditableDocument(data: Data(tampered.utf8)))
    }

    func testWriterRoundTripsReciprocalGastonPairMetadata() throws {
        let encoded = try BoardPackageWriter.data(for: makeDocument(holds: [
            makeHold(id: "gaston-left", name: "Left gaston"),
            makeHold(id: "gaston-right", name: "Right gaston"),
        ]))
        var payload = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )
        var holds = try XCTUnwrap(payload["holds"] as? [[String: Any]])
        holds[0]["kind"] = "gaston"
        holds[0]["pairedHoldID"] = "gaston-right"
        holds[1]["kind"] = "gaston"
        holds[1]["pairedHoldID"] = "gaston-left"
        payload["holds"] = holds
        let gastonDocument = try BoardEditableDocument(
            data: JSONSerialization.data(withJSONObject: payload)
        )

        let output = try BoardPackageWriter.data(for: gastonDocument)
        let redecoded = try BoardEditableDocument(data: output)

        XCTAssertEqual(redecoded.holds.map(\.pairedHoldID), ["gaston-right", "gaston-left"])
        XCTAssertTrue(String(decoding: output, as: UTF8.self).contains("\"pairedHoldID\": \"gaston-right\""))
    }
}
