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
        geometry: [BoardEditablePiece]? = nil
    ) -> BoardEditableHold {
        BoardEditableHold(
            id: id,
            name: name,
            kind: kind,
            geometry: geometry ?? [makePiece()]
        )
    }

    private func makeDocument(
        schemaVersion: Int = 1,
        id: String = "test-board",
        manufacturer: String = "Test",
        name: String = "Test board",
        subtitle: String = "Fixture",
        productURL: String = "https://example.com/board",
        dimensions: String = "70 \u{00d7} 25 cm",
        aspectRatio: Double = 2.0,
        holds: [BoardEditableHold]? = nil
    ) -> BoardEditableDocument {
        BoardEditableDocument(
            schemaVersion: schemaVersion,
            id: id,
            manufacturer: manufacturer,
            name: name,
            subtitle: subtitle,
            productURL: URL(string: productURL)!,
            dimensions: dimensions,
            aspectRatio: aspectRatio,
            presentationAssetPath: "assets/primary.png",
            holds: holds ?? [makeHold()]
        )
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
        XCTAssertEqual(lhs.schemaVersion, rhs.schemaVersion, file: file, line: line)
        XCTAssertEqual(lhs.id, rhs.id, file: file, line: line)
        XCTAssertEqual(lhs.manufacturer, rhs.manufacturer, file: file, line: line)
        XCTAssertEqual(lhs.name, rhs.name, file: file, line: line)
        XCTAssertEqual(lhs.subtitle, rhs.subtitle, file: file, line: line)
        XCTAssertEqual(lhs.productURL.absoluteString, rhs.productURL.absoluteString, file: file, line: line)
        XCTAssertEqual(lhs.dimensions, rhs.dimensions, file: file, line: line)
        XCTAssertEqual(lhs.aspectRatio, rhs.aspectRatio, accuracy: 1e-12, file: file, line: line)
        XCTAssertEqual(lhs.presentationAssetPath, rhs.presentationAssetPath, file: file, line: line)
        XCTAssertEqual(lhs.holds.count, rhs.holds.count, file: file, line: line)
        for (leftHold, rightHold) in zip(lhs.holds, rhs.holds) {
            XCTAssertEqual(leftHold.id, rightHold.id, file: file, line: line)
            XCTAssertEqual(leftHold.name, rightHold.name, file: file, line: line)
            XCTAssertEqual(leftHold.kind, rightHold.kind, file: file, line: line)
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

            assertSemanticallyEqual(decoded, redecoded, file: #filePath, line: #line)

            let reencoded = try BoardPackageWriter.data(for: redecoded)
            XCTAssertEqual(encoded, reencoded, "encoding must be a deterministic fixpoint for \(slug)")
        }
    }

    func testCanonicalFormattingMatchesRepositoryConventions() throws {
        let document = makeDocument(
            id: "zlagboard.pro",
            dimensions: "70.5 \u{00d7} 25 cm",
            aspectRatio: 2.0,
            holds: [
                BoardEditableHold(
                    id: "edge-30-left",
                    name: "Left 30 mm edge",
                    kind: .edge,
                    sizeMillimeters: 30,
                    depthRangeMillimeters: BoardEditableMillimeterRange(lowerBound: 10, upperBound: 22),
                    gripType: .halfCrimp,
                    fingerCapacity: 4,
                    handCapacity: 1,
                    features: [.incutEdge, .flatEdge],
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
        XCTAssertTrue(output.hasPrefix("{\n  \"schemaVersion\": 1,\n"))
        XCTAssertTrue(output.contains("  \"dimensions\": \"70.5 \\u00d7 25 cm\",\n"))
        XCTAssertTrue(output.contains("  \"aspectRatio\": 2.0,\n"))
        XCTAssertTrue(output.contains("\"presentation\": {\n    \"assetPath\": \"assets/primary.png\"\n  },\n"))
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
        XCTAssertTrue(output.hasSuffix("}\n"))

        let lines = output.split(separator: "\n").map(String.init)
        XCTAssertEqual(lines[0], "{")
        XCTAssertEqual(lines[1], "  \"schemaVersion\": 1,")
        XCTAssertEqual(lines[2], "  \"id\": \"zlagboard.pro\",")
        XCTAssertEqual(lines.last, "}")

        let redecoded = try BoardEditableDocument(data: encoded)
        assertSemanticallyEqual(document, redecoded)
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
            output.hasPrefix("{\n  \"schemaVersion\": 1,\n  \"id\": \"zlagboard.pro\",\n  \"manufacturer\": \"Zlagboard\","),
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
            try BoardPackageWriter.data(for: makeDocument(schemaVersion: 2))
        )
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
        duplicateFeatures.holds[0].features = [.jug, .jug]
        XCTAssertThrowsError(try BoardPackageWriter.data(for: duplicateFeatures))

        var zeroSize = makeDocument()
        zeroSize.holds[0].sizeMillimeters = 0
        XCTAssertThrowsError(try BoardPackageWriter.data(for: zeroSize))

        var invertedDepth = makeDocument()
        invertedDepth.holds[0].depthRangeMillimeters = BoardEditableMillimeterRange(lowerBound: 20, upperBound: 5)
        XCTAssertThrowsError(try BoardPackageWriter.data(for: invertedDepth))

        var emptyGeometry = makeDocument(holds: [makeHold(geometry: [])])
        XCTAssertThrowsError(try BoardPackageWriter.data(for: emptyGeometry))

        var noHolds = makeDocument(holds: [])
        XCTAssertThrowsError(try BoardPackageWriter.data(for: noHolds))
    }

    func testStrictDecoderRejectsUnknownKeys() throws {
        var document = makeDocument()
        let encoded = try BoardPackageWriter.data(for: document)
        _ = document

        var tampered = String(decoding: encoded, as: UTF8.self)
        tampered = tampered.replacingOccurrences(
            of: "\"schemaVersion\": 1,",
            with: "\"schemaVersion\": 1,\n  \"legacyField\": true,"
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
}
