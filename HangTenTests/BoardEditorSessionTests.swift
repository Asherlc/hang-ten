import XCTest
@testable import HangTen

@MainActor
final class BoardEditorSessionTests: XCTestCase {
    private var temporaryDirectory: URL!
    private var store: BoardEditorStore!

    override func setUp() async throws {
        try await super.setUp()
        temporaryDirectory = FileManager.default.temporaryDirectory
            .appendingPathComponent("board-editor-session-\(UUID().uuidString)", isDirectory: true)
        let sourceLibrary = repositoryHangboardsURL()
        store = BoardEditorStore(baseDirectory: temporaryDirectory, sourceLibraryURL: sourceLibrary)
    }

    override func tearDown() async throws {
        if let temporaryDirectory {
            try? FileManager.default.removeItem(at: temporaryDirectory)
        }
        try await super.tearDown()
    }

    private func makeSession(slug: String = "zlagboard-pro") throws -> BoardEditorSession {
        _ = try store.startEditing(slug: slug)
        let package = try store.loadDocument(slug: slug)
        return BoardEditorSession(package: package, store: store)
    }

    private func firstPathHoldPiece(
        in document: BoardEditableDocument
    ) -> (holdID: String, pieceIndex: Int)? {
        for hold in document.holds {
            for (index, piece) in hold.geometry.enumerated() where piece.shape.type == "path" {
                return (hold.id, index)
            }
        }
        return nil
    }

    private func selectFirstPathPiece(_ session: inout BoardEditorSession) throws -> (
        holdID: String,
        pieceIndex: Int
    ) {
        guard let target = firstPathHoldPiece(in: session.document) else {
            throw XCTSkip("package has no path-shaped pieces")
        }
        session.select(holdID: target.holdID, pieceIndex: target.pieceIndex)
        return target
    }

    func testBoardCommandsMapFrameIntoBoardSpaceAndBack() throws {
        var session = try makeSession()
        let target = try selectFirstPathPiece(&session)
        let piece = session.hold(id: target.holdID)!.geometry[target.pieceIndex]
        let localAnchors = try XCTUnwrap(piece.shape.commands).compactMap { command in
            try? command.holdPathCommand().holdEndPoint
        }
        let boardCommands = try session.boardCommands(for: piece)
        let boardAnchors = boardCommands.compactMap(\.boardAnchor)

        XCTAssertEqual(localAnchors.count, boardAnchors.count)
        let frame = piece.frame.cgRect
        XCTAssertTrue(boardAnchors.allSatisfy { point in
            point.x >= frame.minX - 1e-9 && point.x <= frame.maxX + 1e-9 &&
                point.y >= frame.minY - 1e-9 && point.y <= frame.maxY + 1e-9
        })
    }

    func testCanvasAnnouncesIncompleteHoldMetadataWithoutRequiringOptionalFields() throws {
        var package = try store.loadDocument(slug: "zlagboard-pro")
        XCTAssertGreaterThanOrEqual(package.document.holds.count, 2)
        for index in package.document.holds.indices {
            package.document.holds[index].fingerCapacity = 1
            package.document.holds[index].depthRangeMillimeters = BoardEditableMillimeterRange(
                lowerBound: 10,
                upperBound: 12
            )
            package.document.holds[index].handCapacity = 1
        }
        let incompleteHoldID = package.document.holds[0].id
        package.document.holds[0].fingerCapacity = nil
        package.document.holds[1].sizeMillimeters = nil
        package.document.holds[1].features = nil

        let session = BoardEditorSession(package: package, store: store)
        let canvas = HoldEditorCanvasUIView()
        canvas.session = session

        XCTAssertEqual(
            canvas.accessibilityLabel,
            "Hangboard hold editor. 1 hold is missing required metadata."
        )
        XCTAssertEqual(canvas.accessibilityValue, "Incomplete hold: \(incompleteHoldID)")
    }

    func testTranslateMovesFrameAndKeepsCommandsNormalized() throws {
        var session = try makeSession(slug: "lattice-triple-rung")
        let target = try selectFirstPathPiece(&session)
        let before = session.hold(id: target.holdID)!.geometry[target.pieceIndex]
        let beforeBounds = try HoldPathEngine.bounds(of: session.boardCommands(for: before))

        session.beginInteractiveEdit()
        try session.translateSelectedPiece(deltaX: 0.02, deltaY: 0.01, recordsHistory: false)

        let after = session.hold(id: target.holdID)!.geometry[target.pieceIndex]
        let afterCommands = try session.boardCommands(for: after)
        let afterBounds = HoldPathEngine.bounds(of: afterCommands)

        XCTAssertEqual(afterBounds.minX, beforeBounds.minX + 0.02, accuracy: 1e-9)
        XCTAssertEqual(afterBounds.minY, beforeBounds.minY + 0.01, accuracy: 1e-9)
        XCTAssertEqual(after.frame.width, before.frame.width, accuracy: 1e-9)
        XCTAssertLessThanOrEqual(after.frame.width, 1)
        XCTAssertNotNil(after.shapeConstraint == nil ? nil : after.shapeConstraint)
        XCTAssertTrue(after.shape.commands?.allSatisfy { command in
            command.to?.allSatisfy { (-0.0000001...1.0000001).contains($0) } ?? true
        } ?? false)
    }

    func testAnchorDragRewritesTightFrame() throws {
        var session = try makeSession(slug: "zlagboard-pro")
        let target = try selectFirstPathPiece(&session)
        session.select(handle: .anchor(commandIndex: 0))
        let pieceBefore = session.hold(id: target.holdID)!.geometry[target.pieceIndex]
        let commandsBefore = try session.boardCommands(for: pieceBefore)
        let firstAnchor = commandsBefore[0].boardAnchor!

        session.beginInteractiveEdit()
        try session.moveSelectedAnchor(commandIndex: 0, deltaX: -0.01, deltaY: 0, recordsHistory: false)

        let pieceAfter = session.hold(id: target.holdID)!.geometry[target.pieceIndex]
        XCTAssertEqual(pieceAfter.frame.x, pieceBefore.frame.x - 0.01, accuracy: 1e-9)
        XCTAssertEqual(pieceAfter.frame.width, pieceBefore.frame.width + 0.01, accuracy: 1e-9)
        try session.boardCommands(for: pieceAfter)
    }

    func testUndoRedoRoundTripRestoresDocument() throws {
        let session = try makeSession(slug: "lattice-triple-rung")
        var working = session
        let target = try selectFirstPathPiece(&working)
        let original = working.document

        working.beginInteractiveEdit()
        try working.translateSelectedPiece(deltaX: 0.03, deltaY: 0, recordsHistory: false)
        XCTAssertFalse(working.document == original)
        XCTAssertTrue(working.canUndo)

        working.undo()
        XCTAssertTrue(working.document == original)
        XCTAssertTrue(working.canRedo)

        working.redo()
        XCTAssertFalse(working.document == original)
        _ = target
    }

    func testSavePersistsEditsThroughStore() throws {
        var session = try makeSession(slug: "zlagboard-pro")
        let target = try selectFirstPathPiece(&session)
        session.beginInteractiveEdit()
        try session.translateSelectedPiece(deltaX: 0.005, deltaY: 0.002, recordsHistory: false)
        session.save()
        XCTAssertTrue(session.isSaved)

        let reloaded = try store.loadDocument(slug: session.slug)
        let savedPiece = reloaded.document.holds.first { $0.id == target.holdID }?
            .geometry[target.pieceIndex]
        let originalPiece = session.hold(id: target.holdID)?.geometry[target.pieceIndex]
        XCTAssertEqual(savedPiece?.frame, originalPiece?.frame)
    }

    func testConstrainedResizeRespectsPixelDerivedMinimums() throws {
        var session = try makeSession(slug: "metolius-simulator-3d")
        let holds = session.document.holds
        let constrainedTarget = holds.enumerated().compactMap { _, hold -> (String, Int)? in
            for (index, piece) in hold.geometry.enumerated()
            where piece.shape.type == "path" && piece.shapeConstraint != nil {
                return (hold.id, index)
            }
            return nil
        }.first

        guard let constrainedTarget else {
            throw XCTSkip("package has no constrained path pieces")
        }
        session.select(holdID: constrainedTarget.0, pieceIndex: constrainedTarget.1)
        guard let piece = session.selectedPieceDocument,
              let constraint = piece.shapeConstraint else {
            return XCTFail("expected constrained piece")
        }
        let startPath = try session.boardCommands(for: piece)
        let startCenter = BoardEditorSession.anchorCentroid(startPath)
        let farPointer = CGPoint(x: startCenter.x - 10, y: startCenter.y - 10)

        session.beginInteractiveEdit()
        try session.resizeConstrained(
            handle: .nw,
            pointerBoardSpace: farPointer,
            recordsHistory: false
        )

        let resized = session.hold(id: constrainedTarget.0)!.geometry[constrainedTarget.1]
        let resizedCommands = try session.boardCommands(for: resized)
        let bounds = HoldPathEngine.bounds(of: resizedCommands)
        XCTAssertGreaterThanOrEqual(bounds.width + 1e-9, session.minimumResizeWidth)
        XCTAssertGreaterThanOrEqual(bounds.height + 1e-9, session.minimumResizeHeight)
        XCTAssertEqual(constraint.rotationDegrees, resized.shapeConstraint?.rotationDegrees)
    }

    func testRoundedRectConversionProducesEquivalentOutline() throws {
        var session = try makeSession(slug: "evolv-kilter-basic-long")
        let roundedTarget = session.document.holds.compactMap { hold -> (String, Int)? in
            for (index, piece) in hold.geometry.enumerated()
            where piece.shape.type == "roundedRect" {
                return (hold.id, index)
            }
            return nil
        }.first

        guard let roundedTarget else {
            throw XCTSkip("package has no roundedRect pieces")
        }
        session.select(holdID: roundedTarget.0, pieceIndex: roundedTarget.1)
        XCTAssertTrue(session.isRoundedRectPiece)
        let before = session.selectedPieceDocument!

        try session.convertRoundedRectToPath()

        let converted = session.hold(id: roundedTarget.0)!.geometry[roundedTarget.1]
        XCTAssertEqual(converted.shape.type, "path")
        XCTAssertEqual(converted.shapeConstraint, before.shapeConstraint)
        let convertedCommands = try session.boardCommands(for: converted)
        let bounds = HoldPathEngine.bounds(of: convertedCommands)
        XCTAssertEqual(bounds.width, CGFloat(before.frame.width), accuracy: 1e-9)
        XCTAssertEqual(bounds.height, CGFloat(before.frame.height), accuracy: 1e-9)
    }

    func testPresetApplicationRegeneratesConstrainedPrimitive() throws {
        var session = try makeSession(slug: "zlagboard-pro")
        let target = try selectFirstPathPiece(&session)
        let before = session.hold(id: target.holdID)!.geometry[target.pieceIndex]
        let beforeBounds = HoldPathEngine.bounds(of: try session.boardCommands(for: before))

        try session.applyPreset(.pill)

        let after = session.hold(id: target.holdID)!.geometry[target.pieceIndex]
        XCTAssertEqual(after.shapeConstraint?.shape, ShapeConstraintShape.pill)
        let afterCommands = try session.boardCommands(for: after)
        let afterBounds = HoldPathEngine.bounds(of: afterCommands)
        XCTAssertEqual(afterBounds.width, beforeBounds.width, accuracy: 1e-6)
        XCTAssertEqual(afterBounds.height, beforeBounds.height, accuracy: 1e-6)
        let afterAnchors = afterCommands.compactMap({ $0.boardAnchor }).count
        XCTAssertGreaterThan(afterAnchors, 4, "pill regeneration must reshape the outline")
    }

    func testNormalizedConstraintDegreesWrapsIntoRange() {
        XCTAssertEqual(BoardEditorSession.normalizedConstraintDegrees(185), -175)
        XCTAssertEqual(BoardEditorSession.normalizedConstraintDegrees(-185), 175)
        XCTAssertEqual(BoardEditorSession.normalizedConstraintDegrees(180), -180)
        XCTAssertEqual(BoardEditorSession.normalizedConstraintDegrees(-0.0), 0)
        XCTAssertEqual(BoardEditorSession.normalizedConstraintDegrees(359.5), -0.5)
    }

    private func repositoryHangboardsURL() -> URL {
        let environment = ProcessInfo.processInfo.environment
        if let configured = environment["HANGTEN_TEST_HANGBOARDS_ROOT"] {
            return URL(fileURLWithPath: configured, isDirectory: true)
        }
        let fallback = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Hangboards", isDirectory: true)
        return fallback
    }
}
