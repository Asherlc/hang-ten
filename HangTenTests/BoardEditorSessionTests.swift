import XCTest
@testable import HangTen

@MainActor
final class BoardEditorSessionTests: XCTestCase {
    private struct AliasFixture {
        let sourceLibraryURL: URL
        let canonicalPNG: Data
        let aliasPNG: Data
    }

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

    private func package(
        _ source: BoardEditedPackage,
        replacing document: BoardEditableDocument
    ) -> BoardEditedPackage {
        BoardEditedPackage(
            slug: source.slug,
            packageURL: source.packageURL,
            document: document,
            imageURL: source.imageURL,
            pixelWidth: source.pixelWidth,
            pixelHeight: source.pixelHeight
        )
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

    private func makeSelectedSloperSession(
        metadata: SloperMetadata? = nil
    ) throws -> BoardEditorSession {
        _ = try store.startEditing(slug: "zlagboard-pro")
        let loadedPackage = try store.loadDocument(slug: "zlagboard-pro")
        var document = loadedPackage.document
        document.holds[0].kind = .sloper
        document.holds[0].sloper = metadata
        let holdID = document.holds[0].id
        let session = BoardEditorSession(
            package: package(loadedPackage, replacing: document),
            store: store
        )
        session.select(holdID: holdID)
        return session
    }

    private func aliasFixtureCordRig() -> BoardDirectTwoAnchorCordRig {
        BoardDirectTwoAnchorCordRig(
            sceneSize: BoardCordSize(width: 200, height: 100),
            sourceFrame: BoardCordRect(x: 0, y: 0, width: 200, height: 100),
            innerFaceFrame: BoardCordRect(x: 0, y: 0, width: 200, height: 100),
            attachmentPoints: [
                BoardCordPoint(x: 40, y: 70),
                BoardCordPoint(x: 160, y: 70),
            ],
            pullPoint: BoardCordPoint(x: 100, y: 10),
            eyeletRadius: 4
        )
    }

    private func aliasFixtureDocument(isRigged: Bool) -> BoardEditableDocument {
        var document = BoardEditorTestFixtures.sampleDocument()
        let cordRig: BoardCordRig? = isRigged
            ? .directTwoAnchor(aliasFixtureCordRig())
            : nil
        document.presentations = [
            BoardEditablePresentation(
                id: "front",
                name: "Front",
                assetPath: "assets/primary.png",
                aspectRatio: 2,
                isDefault: false,
                cordRig: cordRig
            ),
            BoardEditablePresentation(
                id: "front-inverted",
                name: "Front inverted",
                assetPath: "assets/front-inverted.png",
                aspectRatio: 2,
                isDefault: true,
                sourcePresentationID: "front",
                isInverted: true,
                geometryRotationAnchor: .center
            ),
            BoardEditablePresentation(
                id: "other",
                name: "Other",
                assetPath: "assets/other.png",
                aspectRatio: 2,
                isDefault: false
            ),
        ]

        var hiddenHold = document.holds[0]
        hiddenHold.id = "other-hold"
        hiddenHold.name = "Other hold"
        hiddenHold.presentationID = "other"
        hiddenHold.geometry[0].frame = BoardPackageFrameDocument(
            x: 0.2,
            y: 0.35,
            width: 0.1,
            height: 0.1
        )
        document.holds.append(hiddenHold)
        return document
    }

    private func solidPNG(_ color: UIColor) -> Data {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        return UIGraphicsImageRenderer(
            size: CGSize(width: 200, height: 100),
            format: format
        ).pngData { context in
            color.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 200, height: 100))
        }
    }

    private func makeAliasFixture(isRigged: Bool) throws -> AliasFixture {
        let sourceLibraryURL = temporaryDirectory.appendingPathComponent(
            "alias-source-\(UUID().uuidString)",
            isDirectory: true
        )
        let packageURL = sourceLibraryURL.appendingPathComponent(
            "alias-fixture",
            isDirectory: true
        )
        let assetsURL = packageURL.appendingPathComponent("assets", isDirectory: true)
        try FileManager.default.createDirectory(
            at: assetsURL,
            withIntermediateDirectories: true
        )

        let canonicalPNG = solidPNG(.red)
        let aliasPNG = solidPNG(.blue)
        try BoardPackageWriter.data(for: aliasFixtureDocument(isRigged: isRigged))
            .write(to: packageURL.appendingPathComponent("board.json"))
        try canonicalPNG.write(to: assetsURL.appendingPathComponent("primary.png"))
        try aliasPNG.write(to: assetsURL.appendingPathComponent("front-inverted.png"))
        try solidPNG(.green).write(to: assetsURL.appendingPathComponent("other.png"))
        return AliasFixture(
            sourceLibraryURL: sourceLibraryURL,
            canonicalPNG: canonicalPNG,
            aliasPNG: aliasPNG
        )
    }

    private func loadAliasFixture(isRigged: Bool) throws -> (
        package: BoardEditedPackage,
        store: BoardEditorStore,
        fixture: AliasFixture
    ) {
        let fixture = try makeAliasFixture(isRigged: isRigged)
        let fixtureStore = BoardEditorStore(
            baseDirectory: temporaryDirectory.appendingPathComponent(
                "alias-edits-\(UUID().uuidString)",
                isDirectory: true
            ),
            sourceLibraryURL: fixture.sourceLibraryURL
        )
        _ = try fixtureStore.startEditing(slug: "alias-fixture")
        return (
            try fixtureStore.loadDocument(slug: "alias-fixture"),
            fixtureStore,
            fixture
        )
    }

    func testSelectedSloperMetadataTransitionsPreserveOnlyValidAngleState() throws {
        let session = try makeSelectedSloperSession()
        XCTAssertNil(session.selectedHold?.sloper)

        try session.setSelectedSloperType(.flat)
        XCTAssertEqual(
            session.selectedHold?.sloper,
            SloperMetadata(type: .flat, angleDegrees: nil)
        )

        try session.setSelectedSloperAngleDegrees(20)
        XCTAssertEqual(
            session.selectedHold?.sloper,
            SloperMetadata(type: .flat, angleDegrees: 20)
        )

        try session.setSelectedSloperType(.round)
        XCTAssertEqual(
            session.selectedHold?.sloper,
            SloperMetadata(type: .round, angleDegrees: nil)
        )

        try session.setSelectedSloperType(nil)
        XCTAssertNil(session.selectedHold?.sloper)
    }

    func testSloperMetadataEditsUndoOneTransitionAtATime() throws {
        let session = try makeSelectedSloperSession()

        try session.setSelectedSloperType(.flat)
        try session.setSelectedSloperAngleDegrees(20)
        try session.setSelectedSloperType(.round)
        try session.setSelectedSloperType(nil)

        session.undo()
        XCTAssertEqual(session.selectedHold?.sloper, SloperMetadata(type: .round, angleDegrees: nil))
        session.undo()
        XCTAssertEqual(session.selectedHold?.sloper, SloperMetadata(type: .flat, angleDegrees: 20))
        session.undo()
        XCTAssertEqual(session.selectedHold?.sloper, SloperMetadata(type: .flat, angleDegrees: nil))
        session.undo()
        XCTAssertNil(session.selectedHold?.sloper)
        XCTAssertFalse(session.canUndo)
    }

    func testSloperAngleUpdateRejectsInvalidOrInapplicableValuesWithoutChangingDocument() throws {
        let session = try makeSelectedSloperSession()
        let unspecified = session.document

        XCTAssertThrowsError(try session.setSelectedSloperAngleDegrees(20))
        XCTAssertEqual(session.document, unspecified)
        XCTAssertFalse(session.canUndo)

        try session.setSelectedSloperType(.round)
        let round = session.document
        XCTAssertThrowsError(try session.setSelectedSloperAngleDegrees(20))
        XCTAssertEqual(session.document, round)

        try session.setSelectedSloperType(.flat)
        let flat = session.document
        for invalidAngle in [-0.01, 90.01, .infinity, .nan] {
            XCTAssertThrowsError(try session.setSelectedSloperAngleDegrees(invalidAngle))
            XCTAssertEqual(session.document, flat)
        }
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

    func testCanvasExposesAggregateAndPerHoldWarningsForIncompleteMetadata() throws {
        _ = try store.startEditing(slug: "zlagboard-pro")
        let loadedPackage = try store.loadDocument(slug: "zlagboard-pro")
        var document = loadedPackage.document
        XCTAssertGreaterThanOrEqual(document.holds.count, 2)
        for index in document.holds.indices {
            document.holds[index].fingerCapacity = 1
            document.holds[index].depthRangeMillimeters = BoardEditableMillimeterRange(
                lowerBound: 10,
                upperBound: 12
            )
            document.holds[index].handCapacity = 1
        }
        let incompleteHoldID = document.holds[0].id
        document.holds[0].fingerCapacity = nil
        document.holds[1].sizeMillimeters = nil
        document.holds[1].features = nil

        let session = BoardEditorSession(package: package(loadedPackage, replacing: document), store: store)
        let canvas = HoldEditorCanvasUIView(frame: CGRect(x: 0, y: 0, width: 320, height: 160))
        canvas.session = session
        canvas.updateMetadataWarningAccessibility()

        let elements = try XCTUnwrap(canvas.accessibilityElements as? [UIAccessibilityElement])
        XCTAssertEqual(elements.count, 2)
        XCTAssertEqual(
            elements[0].accessibilityLabel,
            "Hangboard hold editor. 1 hold is missing required metadata."
        )
        XCTAssertEqual(elements[0].accessibilityValue, "Incomplete hold: \(incompleteHoldID)")
        XCTAssertEqual(elements[1].accessibilityLabel, "Incomplete hold metadata: \(incompleteHoldID)")
        XCTAssertEqual(elements[1].accessibilityValue, "Missing: finger capacity")
        XCTAssertGreaterThan(elements[1].accessibilityFrameInContainerSpace.width, 0)
        XCTAssertGreaterThan(elements[1].accessibilityFrameInContainerSpace.height, 0)
    }

    func testCanvasHighlightsOnlyEdgesAndPocketsMissingDepthMetadata() throws {
        _ = try store.startEditing(slug: "zlagboard-pro")
        let loadedPackage = try store.loadDocument(slug: "zlagboard-pro")
        var document = loadedPackage.document
        document.holds = Array(document.holds.prefix(7))
        XCTAssertEqual(document.holds.count, 7)

        let kinds: [HoldKind] = [.jug, .sloper, .pinch, .edge, .pocket, .edge, .pocket]
        for index in document.holds.indices {
            document.holds[index].kind = kinds[index]
            document.holds[index].fingerCapacity = 1
            document.holds[index].handCapacity = 1
            document.holds[index].sizeMillimeters = nil
            document.holds[index].depthRangeMillimeters = nil
        }
        document.holds[3].sizeMillimeters = 12
        document.holds[4].depthRangeMillimeters = BoardEditableMillimeterRange(
            lowerBound: 10,
            upperBound: 12
        )

        let session = BoardEditorSession(
            package: package(loadedPackage, replacing: document),
            store: store
        )
        try withExtendedLifetime(session) {
            let canvas = HoldEditorCanvasUIView(frame: CGRect(x: 0, y: 0, width: 320, height: 160))
            canvas.session = session
            canvas.updateMetadataWarningAccessibility()

            let elements = try XCTUnwrap(canvas.accessibilityElements as? [UIAccessibilityElement])
            XCTAssertEqual(elements.count, 3)
            XCTAssertEqual(elements[0].accessibilityLabel, "Hangboard hold editor. 2 holds are missing required metadata.")
            XCTAssertEqual(
                elements[0].accessibilityValue,
                "Incomplete holds: \(document.holds[5].id), \(document.holds[6].id)"
            )
            XCTAssertEqual(
                elements.dropFirst().compactMap(\.accessibilityLabel),
                [
                    "Incomplete hold metadata: \(document.holds[5].id)",
                    "Incomplete hold metadata: \(document.holds[6].id)",
                ]
            )
            XCTAssertTrue(elements.dropFirst().allSatisfy {
                $0.accessibilityValue == "Missing: depth"
                    && $0.accessibilityFrameInContainerSpace.width > 0
                    && $0.accessibilityFrameInContainerSpace.height > 0
            })
        }
    }

    func testCanvasAppliesTheSessionSelectedBackgroundColor() {
        let canvas = HoldEditorCanvasUIView(frame: CGRect(x: 0, y: 0, width: 320, height: 160))

        canvas.editorBackgroundColor = .black

        XCTAssertEqual(canvas.backgroundColor, .black)
    }

    func testRiggedEditorArtworkRendersTheDefaultPresentationOnItsSceneCanvas() throws {
        _ = try store.startEditing(slug: "frictitious-port-a-board")
        let package = try store.loadDocument(slug: "frictitious-port-a-board")
        let sourceImage = try XCTUnwrap(UIImage(contentsOfFile: package.imageURL.path))

        let artwork = BoardEditorCanvasArtwork.make(
            package: package,
            sourceImage: sourceImage
        )

        XCTAssertNotNil(artwork.directTwoAnchorRig)
        XCTAssertEqual(artwork.image.size, CGSize(width: 1200, height: 1464))
        XCTAssertFalse(artwork.image === sourceImage)
    }

    func testRiggedDefaultAliasLoadsAndRendersItsCanonicalSourceArtwork() throws {
        let loaded = try loadAliasFixture(isRigged: true)

        XCTAssertEqual(loaded.package.imageURL.lastPathComponent, "primary.png")
        XCTAssertEqual(try Data(contentsOf: loaded.package.imageURL), loaded.fixture.canonicalPNG)
        XCTAssertNotEqual(try Data(contentsOf: loaded.package.imageURL), loaded.fixture.aliasPNG)

        let sourceImage = try XCTUnwrap(
            UIImage(contentsOfFile: loaded.package.imageURL.path)
        )
        let artwork = BoardEditorCanvasArtwork.make(
            package: loaded.package,
            sourceImage: sourceImage
        )
        XCTAssertNotNil(artwork.directTwoAnchorRig)
        XCTAssertEqual(artwork.sourcePresentationID, "front")
        XCTAssertEqual(artwork.image.size, CGSize(width: 200, height: 100))
        XCTAssertEqual(
            artwork.projection.project(
                CGPoint(x: 20, y: 30),
                in: CGRect(x: 0, y: 0, width: 200, height: 100)
            ),
            CGPoint(x: 180, y: 70)
        )
    }

    func testRiggedDefaultAliasShowsOnlyCanonicalSourceHolds() throws {
        let loaded = try loadAliasFixture(isRigged: true)
        let session = BoardEditorSession(package: loaded.package, store: loaded.store)
        let sourceImage = try XCTUnwrap(
            UIImage(contentsOfFile: loaded.package.imageURL.path)
        )
        let canvas = HoldEditorCanvasUIView(
            frame: CGRect(x: 0, y: 0, width: 400, height: 200)
        )
        canvas.session = session
        canvas.boardArtwork = BoardEditorCanvasArtwork.make(
            package: loaded.package,
            sourceImage: sourceImage
        )
        canvas.updateMetadataWarningAccessibility()

        XCTAssertEqual(session.incompleteMetadataHoldIDs, ["hold-one", "other-hold"])
        let elements = try XCTUnwrap(
            canvas.accessibilityElements as? [UIAccessibilityElement]
        )
        XCTAssertEqual(
            elements.dropFirst().compactMap(\.accessibilityLabel),
            ["Incomplete hold metadata: hold-one"]
        )
    }

    func testRiggedInvertedAliasInverseProjectsHitTestingAndDragEditing() throws {
        let loaded = try loadAliasFixture(isRigged: true)
        let session = BoardEditorSession(package: loaded.package, store: loaded.store)
        let sourceImage = try XCTUnwrap(
            UIImage(contentsOfFile: loaded.package.imageURL.path)
        )
        let canvas = HoldEditorCanvasUIView(
            frame: CGRect(x: 0, y: 0, width: 400, height: 200)
        )
        canvas.session = session
        canvas.boardArtwork = BoardEditorCanvasArtwork.make(
            package: loaded.package,
            sourceImage: sourceImage
        )

        // The canonical hold center is (0.25, 0.4). A 180-degree projection
        // puts it at (0.75, 0.6) in the fitted 376 x 188 scene at (12, 6).
        let pan = TestBoardEditorPanGestureRecognizer()
        let selector = NSSelectorFromString("handlePan:")
        XCTAssertTrue(canvas.responds(to: selector))
        pan.locationValue = CGPoint(x: 294, y: 118.8)
        pan.simulatedState = .began
        _ = canvas.perform(selector, with: pan)

        XCTAssertEqual(
            session.selectedPiece,
            BoardEditorSession.PieceSelection(holdID: "hold-one", pieceIndex: 0)
        )

        // Moving +10% right and down on the inverted screen is -10% on each
        // canonical board axis.
        pan.locationValue = CGPoint(x: 331.6, y: 137.6)
        pan.simulatedState = .changed
        _ = canvas.perform(selector, with: pan)

        let movedFrame = try XCTUnwrap(session.selectedPieceDocument?.frame)
        XCTAssertEqual(movedFrame.x, 0, accuracy: 1e-9)
        XCTAssertEqual(movedFrame.y, 0.1, accuracy: 1e-9)
        XCTAssertEqual(movedFrame.width, 0.3, accuracy: 1e-9)
        XCTAssertEqual(movedFrame.height, 0.4, accuracy: 1e-9)

        pan.simulatedState = .ended
        _ = canvas.perform(selector, with: pan)
        XCTAssertTrue(session.canUndo)
    }

    func testNonRiggedDefaultAliasKeepsItsOwnStaticArtworkFallback() throws {
        let loaded = try loadAliasFixture(isRigged: false)

        XCTAssertEqual(
            loaded.package.imageURL.lastPathComponent,
            "front-inverted.png"
        )
        XCTAssertEqual(try Data(contentsOf: loaded.package.imageURL), loaded.fixture.aliasPNG)
        let sourceImage = try XCTUnwrap(
            UIImage(contentsOfFile: loaded.package.imageURL.path)
        )
        let artwork = BoardEditorCanvasArtwork.make(
            package: loaded.package,
            sourceImage: sourceImage
        )
        XCTAssertNil(artwork.directTwoAnchorRig)
        XCTAssertTrue(artwork.image === sourceImage)
    }

    func testCanvasMapsEditableHoldsThroughRiggedArtworkFaceRect() throws {
        let sourceLibrary = try BoardEditorTestFixtures.makeSourceLibrary()
        addTeardownBlock { try? FileManager.default.removeItem(at: sourceLibrary) }
        let fixtureStore = BoardEditorStore(
            baseDirectory: temporaryDirectory.appendingPathComponent("face-rect", isDirectory: true),
            sourceLibraryURL: sourceLibrary
        )
        _ = try fixtureStore.startEditing(slug: "fixture-board")
        let package = try fixtureStore.loadDocument(slug: "fixture-board")
        let session = BoardEditorSession(package: package, store: fixtureStore)
        let rig = BoardDirectTwoAnchorCordRig(
            sceneSize: BoardCordSize(width: 200, height: 100),
            sourceFrame: BoardCordRect(x: 0, y: 0, width: 200, height: 100),
            innerFaceFrame: BoardCordRect(x: 20, y: 10, width: 160, height: 80),
            attachmentPoints: [
                BoardCordPoint(x: 40, y: 60),
                BoardCordPoint(x: 160, y: 60),
            ],
            pullPoint: BoardCordPoint(x: 100, y: 10),
            eyeletRadius: 4
        )
        let canvas = HoldEditorCanvasUIView(
            frame: CGRect(x: 0, y: 0, width: 320, height: 160)
        )
        canvas.session = session
        canvas.boardArtwork = BoardEditorCanvasArtwork(
            image: UIImage(),
            presentationAspectRatio: 2,
            directTwoAnchorRig: rig,
            projection: BoardPresentationGeometryProjection(isInverted: false)
        )
        canvas.updateMetadataWarningAccessibility()

        let warning = try XCTUnwrap(
            (canvas.accessibilityElements as? [UIAccessibilityElement])?.last
        )
        let frame = warning.accessibilityFrameInContainerSpace
        XCTAssertEqual(frame.minX, 63.744, accuracy: 0.001)
        XCTAssertEqual(frame.minY, 43.904, accuracy: 0.001)
        XCTAssertEqual(frame.width, 72.192, accuracy: 0.001)
        XCTAssertEqual(frame.height, 48.128, accuracy: 0.001)
    }

    func testViewportOperationsRefreshIncompleteHoldAccessibilityFrame() throws {
        _ = try store.startEditing(slug: "zlagboard-pro")
        let loadedPackage = try store.loadDocument(slug: "zlagboard-pro")
        var document = loadedPackage.document
        document.holds = [document.holds[0]]
        document.holds[0].fingerCapacity = nil
        document.holds[0].depthRangeMillimeters = BoardEditableMillimeterRange(
            lowerBound: 10,
            upperBound: 12
        )
        document.holds[0].handCapacity = 1

        let session = BoardEditorSession(
            package: package(loadedPackage, replacing: document),
            store: store
        )
        let canvas = HoldEditorCanvasUIView(frame: CGRect(x: 0, y: 0, width: 320, height: 160))
        canvas.session = session
        let frameBeforePan = try XCTUnwrap(
            (canvas.accessibilityElements as? [UIAccessibilityElement])?.last
        ).accessibilityFrameInContainerSpace

        canvas.beginViewportPan()
        canvas.updateViewportPan(translation: CGPoint(x: 48, y: 16))

        let frameAfterPan = try XCTUnwrap(
            (canvas.accessibilityElements as? [UIAccessibilityElement])?.last
        ).accessibilityFrameInContainerSpace
        XCTAssertNotEqual(frameAfterPan, frameBeforePan)

        canvas.beginViewportZoom()
        canvas.updateViewportZoom(scale: 1.5)

        let frameAfterPinch = try XCTUnwrap(
            (canvas.accessibilityElements as? [UIAccessibilityElement])?.last
        ).accessibilityFrameInContainerSpace
        XCTAssertNotEqual(frameAfterPinch, frameAfterPan)
    }

    func testIncompleteMetadataRequiresKindFingerDepthAndHandForEdgesButNotSizeOrFeatures() throws {
        _ = try store.startEditing(slug: "zlagboard-pro")
        let loadedPackage = try store.loadDocument(slug: "zlagboard-pro")
        var document = loadedPackage.document
        let holdID = document.holds[0].id
        document.holds = [document.holds[0]]
        document.holds[0].kind = .edge
        document.holds[0].fingerCapacity = 1
        document.holds[0].depthRangeMillimeters = BoardEditableMillimeterRange(
            lowerBound: 10,
            upperBound: 12
        )
        document.holds[0].handCapacity = 1
        document.holds[0].sizeMillimeters = nil
        document.holds[0].features = nil

        let completeSession = BoardEditorSession(
            package: package(loadedPackage, replacing: document),
            store: store
        )
        XCTAssertEqual(completeSession.incompleteMetadataHoldIDs, [])

        document.holds[0].kind = nil
        XCTAssertEqual(
            BoardEditorSession(
                package: package(loadedPackage, replacing: document),
                store: store
            ).incompleteMetadataHoldIDs,
            [holdID]
        )
        document.holds[0].kind = .edge

        document.holds[0].fingerCapacity = nil
        XCTAssertEqual(
            BoardEditorSession(
                package: package(loadedPackage, replacing: document),
                store: store
            ).incompleteMetadataHoldIDs,
            [holdID]
        )
        document.holds[0].fingerCapacity = 1

        document.holds[0].depthRangeMillimeters = nil
        XCTAssertEqual(
            BoardEditorSession(
                package: package(loadedPackage, replacing: document),
                store: store
            ).incompleteMetadataHoldIDs,
            [holdID]
        )
        document.holds[0].depthRangeMillimeters = BoardEditableMillimeterRange(
            lowerBound: 10,
            upperBound: 12
        )

        document.holds[0].handCapacity = nil
        XCTAssertEqual(
            BoardEditorSession(
                package: package(loadedPackage, replacing: document),
                store: store
            ).incompleteMetadataHoldIDs,
            [holdID]
        )
    }

    func testIncompleteMetadataRequiresDepthOnlyForEdgesAndPockets() throws {
        _ = try store.startEditing(slug: "zlagboard-pro")
        let loadedPackage = try store.loadDocument(slug: "zlagboard-pro")
        var document = loadedPackage.document
        document.holds = Array(document.holds.prefix(5))
        XCTAssertEqual(document.holds.count, 5)

        let kinds: [HoldKind] = [.jug, .sloper, .pinch, .edge, .pocket]
        for index in document.holds.indices {
            document.holds[index].kind = kinds[index]
            document.holds[index].fingerCapacity = 1
            document.holds[index].handCapacity = 1
            document.holds[index].sizeMillimeters = nil
            document.holds[index].depthRangeMillimeters = nil
        }

        document.holds[3].sizeMillimeters = 12
        document.holds[4].depthRangeMillimeters = BoardEditableMillimeterRange(
            lowerBound: 10,
            upperBound: 12
        )

        let completeSession = BoardEditorSession(
            package: package(loadedPackage, replacing: document),
            store: store
        )
        XCTAssertEqual(completeSession.incompleteMetadataHoldIDs, [])

        document.holds[3].sizeMillimeters = nil
        document.holds[4].depthRangeMillimeters = nil
        let incompleteSession = BoardEditorSession(
            package: package(loadedPackage, replacing: document),
            store: store
        )
        XCTAssertEqual(
            incompleteSession.incompleteMetadataHoldIDs,
            [document.holds[3].id, document.holds[4].id]
        )
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
        let pieceBefore = session.hold(id: target.holdID)!.geometry[target.pieceIndex]
        let commandsBefore = try session.boardCommands(for: pieceBefore)
        var leftmostAnchorCandidate: (index: Int, point: CGPoint)?
        for (index, command) in commandsBefore.enumerated() {
            guard let point = command.boardAnchor else { continue }
            guard let current = leftmostAnchorCandidate else {
                leftmostAnchorCandidate = (index: index, point: point)
                continue
            }
            if point.x < current.point.x ||
                (point.x == current.point.x && index < current.index) {
                leftmostAnchorCandidate = (index: index, point: point)
            }
        }
        let leftmostAnchor = try XCTUnwrap(leftmostAnchorCandidate)
        session.select(handle: .anchor(commandIndex: leftmostAnchor.index))

        session.beginInteractiveEdit()
        try session.moveSelectedAnchor(
            commandIndex: leftmostAnchor.index,
            deltaX: -0.01,
            deltaY: 0,
            recordsHistory: false
        )

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

@MainActor
private final class TestBoardEditorPanGestureRecognizer: UIPanGestureRecognizer {
    var simulatedState: UIGestureRecognizer.State = .possible
    var locationValue = CGPoint.zero

    override var state: UIGestureRecognizer.State {
        get { simulatedState }
        set { simulatedState = newValue }
    }

    override var numberOfTouches: Int { 1 }

    override func location(in view: UIView?) -> CGPoint {
        locationValue
    }

    override func translation(in view: UIView?) -> CGPoint {
        .zero
    }
}
