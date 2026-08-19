import XCTest
@testable import HangTen

final class BoardPackageStoreTests: XCTestCase {
    func testStoreDiscoversDirectChildPackagesWithoutCatalogAndSortsThem() throws {
        let fixture = try makeFixtureBundle(
            packages: [
                PackageSpec(slug: "zeta-model", id: "zeta.board", manufacturer: "Zeta", name: "Model"),
                PackageSpec(slug: "alpha-zulu", id: "alpha.zulu", manufacturer: "Alpha", name: "Zulu"),
                PackageSpec(slug: "alpha-alpha-b", id: "alpha.b", manufacturer: "Alpha", name: "Alpha"),
                PackageSpec(slug: "alpha-alpha-a", id: "alpha.a", manufacturer: "Alpha", name: "Alpha")
            ],
            draftSlugs: ["draft-model"]
        )
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)

        XCTAssertEqual(store.boards.map(\.id), ["alpha.a", "alpha.b", "alpha.zulu", "zeta.board"])
        let board = try XCTUnwrap(store.board(id: "alpha.a"))
        let firstHold = try XCTUnwrap(board.holds.first)
        XCTAssertEqual(board.manufacturer, "Alpha")
        XCTAssertEqual(board.name, "Alpha")
        XCTAssertEqual(firstHold.geometry.count, 2)
        let expectedFrame = CGRect(x: 0.05, y: 0.1, width: 0.4, height: 0.4)
        XCTAssertEqual(firstHold.frame.rect.origin.x, expectedFrame.origin.x, accuracy: 1e-12)
        XCTAssertEqual(firstHold.frame.rect.origin.y, expectedFrame.origin.y, accuracy: 1e-12)
        XCTAssertEqual(firstHold.frame.rect.size.width, expectedFrame.size.width, accuracy: 1e-12)
        XCTAssertEqual(firstHold.frame.rect.size.height, expectedFrame.size.height, accuracy: 1e-12)
        XCTAssertNil(firstHold.sizeMillimeters)
        XCTAssertNil(firstHold.depthRangeMillimeters)
        XCTAssertNil(firstHold.gripType)
        XCTAssertNil(firstHold.fingerCapacity)
        XCTAssertNil(firstHold.features)
        XCTAssertEqual(store.semantics(for: board.id), [:])
        let imageURL = try XCTUnwrap(store.presentationImageURL(for: board))
        XCTAssertEqual(imageURL.lastPathComponent, "primary.png")
        XCTAssertEqual(try Data(contentsOf: imageURL), try presentationBytes())
    }

    func testStoreAcceptsShapeConstraintWithoutChangingRuntimeBoardShape() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                geometry[0]["shapeConstraint"] = [
                    "shape": "oval",
                    "rotationDegrees": 15
                ]
                holds[0]["geometry"] = geometry
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let firstPiece = try XCTUnwrap(board.holds.first?.geometry.first)

        XCTAssertEqual(
            firstPiece.shape,
            .roundedRect(cornerRadiusFraction: 0.2)
        )
    }

    func testStoreRejectsInvalidShapeConstraints() throws {
        let invalidConstraints: [[String: Any]] = [
            ["rotationDegrees": 0],
            ["shape": "oval"],
            ["shape": "triangle", "rotationDegrees": 0],
            ["shape": "circle", "rotationDegrees": true],
            ["shape": "rectangle", "rotationDegrees": -180.01],
            ["shape": "oval", "rotationDegrees": 180],
            ["shape": "oval", "rotationDegrees": 0, "unexpected": true]
        ]
        for constraint in invalidConstraints {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                    var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                    geometry[0]["shapeConstraint"] = constraint
                    holds[0]["geometry"] = geometry
                    board["holds"] = holds
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
        }
    }

    func testStoreRejectsNonFiniteShapeConstraintRotation() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            let boardURL = hangboardsURL.appendingPathComponent("fixture-model/board.json")
            try self.mutateBoard(at: boardURL) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                geometry[0]["shapeConstraint"] = [
                    "shape": "pill",
                    "rotationDegrees": 0
                ]
                holds[0]["geometry"] = geometry
                board["holds"] = holds
            }
            let finiteJSON = try XCTUnwrap(String(data: Data(contentsOf: boardURL), encoding: .utf8))
            let nonFiniteJSON = finiteJSON.replacingOccurrences(
                of: "\"rotationDegrees\":0",
                with: "\"rotationDegrees\":1e999"
            )
            XCTAssertNotEqual(nonFiniteJSON, finiteJSON)
            try Data(nonFiniteJSON.utf8).write(to: boardURL)
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreUsesSharedNonASCIIOrderingContract() throws {
        let fixtures = try validationFixtures()
        let ordering = try XCTUnwrap(fixtures["ordering"] as? [String: Any])
        let packageFixtures = try XCTUnwrap(ordering["packages"] as? [[String: String]])
        let expectedBoardIDs = try XCTUnwrap(ordering["expectedBoardIDs"] as? [String])
        let packages = try packageFixtures.map { package in
            PackageSpec(
                slug: try XCTUnwrap(package["slug"]),
                id: try XCTUnwrap(package["id"]),
                manufacturer: try XCTUnwrap(package["manufacturer"]),
                name: try XCTUnwrap(package["name"])
            )
        }
        let fixture = try makeFixtureBundle(packages: packages)
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)

        XCTAssertEqual(store.boards.map(\.id), expectedBoardIDs)
    }

    func testStoreRejectsDuplicateDiscoveredBoardIDs() throws {
        let fixture = try makeFixtureBundle(packages: [
            PackageSpec(slug: "first-model", id: "duplicate.board"),
            PackageSpec(slug: "second-model", id: "duplicate.board")
        ])
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(error as? BoardPackageStoreError, .duplicateBoardID("duplicate.board"))
        }
    }

    func testStoreFailsClosedForMalformedCompletedPackage() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try Data("{ malformed".utf8).write(
                to: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .malformedJSON(resource: "Hangboards/fixture-model/board.json")
            )
        }
    }

    func testStoreRejectsMissingPrimaryImage() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try FileManager.default.removeItem(
                at: hangboardsURL.appendingPathComponent("fixture-model/assets/primary.png")
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreRejectsPlausiblePNGHeaderWithoutCompleteImageData() throws {
        let truncated = try pngFixture(named: "plausibleHeaderTruncatedBase64")
        XCTAssertEqual(truncated.count, 24)
        XCTAssertEqual(
            truncated.prefix(8),
            Data([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
        )
        let fixture = try makeFixtureBundle { hangboardsURL in
            try truncated.write(
                to: hangboardsURL.appendingPathComponent("fixture-model/assets/primary.png")
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreRejectsSharedIndexedPNGWithDuplicatePalette() throws {
        let duplicatePalette = try pngFixture(named: "duplicatePaletteBase64")
        XCTAssertEqual(
            duplicatePalette.ranges(of: Data("PLTE".utf8)).count,
            2
        )
        let fixture = try makeFixtureBundle { hangboardsURL in
            try duplicatePalette.write(
                to: hangboardsURL.appendingPathComponent("fixture-model/assets/primary.png")
            )
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["aspectRatio"] = 1
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreAcceptsAspectRatioMatchingPresentationPixels() throws {
        let fixture = try makeFixtureBundle()
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(board.aspectRatio, 2)
    }

    func testStoreRejectsAspectRatioThatDoesNotMatchPresentationPixels() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["aspectRatio"] = 34.0 / 7.0
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(reason.contains("aspect ratio must match"), reason)
        }
    }

    func testStoreRejectsPresentationPathOtherThanPrimaryAsset() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["presentation"] = ["assetPath": "assets/alternate.png"]
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertEqual(reason, "presentation.assetPath must be assets/primary.png")
        }
    }

    func testStoreRejectsPresentationPathThatEscapesPackage() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["presentation"] = ["assetPath": "../outside/primary.png"]
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .presentationAssetPathEscape(
                    boardID: "fixture.board",
                    path: "../outside/primary.png"
                )
            )
        }
    }

    func testStoreRejectsPathWithMatchingControlPointsButNotContourUseDeclaredFrame() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                geometry[0]["shape"] = [
                    "type": "path",
                    "commands": [
                        ["command": "move", "to": [0.25, 0.25]],
                        ["command": "curve", "to": [0.75, 0.25], "control1": [0.0, 0.0], "control2": [1.0, 0.0]],
                        ["command": "curve", "to": [0.25, 0.75], "control1": [1.0, 1.0], "control2": [0.0, 1.0]],
                        ["command": "close"]
                    ]
                ]
                holds[0]["geometry"] = geometry
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(reason.contains("frame must match its shape bounds"), reason)
        }
    }

    func testStoreRejectsSidecarsAndExtraAssets() throws {
        for relativePath in ["semantics.json", "assets/alternate.png"] {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try Data("{}".utf8).write(
                    to: hangboardsURL.appendingPathComponent("fixture-model/\(relativePath)")
                )
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), relativePath)
        }
    }

    func testStoreRejectsRootCatalogFiles() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try Data("{}".utf8).write(
                to: hangboardsURL.appendingPathComponent("catalog.json")
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(let boardID, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertEqual(boardID, "catalog.json")
            XCTAssertTrue(reason.contains("direct child directories"))
        }
    }

    func testStoreRejectsSymlinkedPackageAndMembers() throws {
        let linkedPackageFixture = try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let outsideURL = hangboardsURL.deletingLastPathComponent().appendingPathComponent("outside")
            try FileManager.default.moveItem(at: packageURL, to: outsideURL)
            try FileManager.default.createSymbolicLink(at: packageURL, withDestinationURL: outsideURL)
        }
        defer { linkedPackageFixture.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: linkedPackageFixture.bundle))

        let linkedMemberFixture = try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let boardURL = packageURL.appendingPathComponent("board.json")
            let outsideURL = hangboardsURL
                .deletingLastPathComponent()
                .appendingPathComponent("outside-board.json")
            try FileManager.default.moveItem(at: boardURL, to: outsideURL)
            try FileManager.default.createSymbolicLink(at: boardURL, withDestinationURL: outsideURL)
        }
        defer { linkedMemberFixture.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: linkedMemberFixture.bundle)) { error in
            guard case .packagePathEscape(let boardID, let path) = error as? BoardPackageStoreError else {
                return XCTFail("Expected packagePathEscape, got \(error)")
            }
            XCTAssertEqual(boardID, "fixture-model")
            XCTAssertTrue(path.hasSuffix("/fixture-model/board.json"), path)
        }
    }

    func testStoreRejectsEmptyAndOutOfRangeGeometry() throws {
        for mutation in [
            { (holds: inout [[String: Any]]) in holds[0]["geometry"] = [] },
            { (holds: inout [[String: Any]]) in
                var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                var frame = try XCTUnwrap(geometry[0]["frame"] as? [String: Any])
                frame["x"] = -0.1
                geometry[0]["frame"] = frame
                holds[0]["geometry"] = geometry
            }
        ] {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(at: hangboardsURL.appendingPathComponent("fixture-model/board.json")) {
                    var holds = try XCTUnwrap($0["holds"] as? [[String: Any]])
                    try mutation(&holds)
                    $0["holds"] = holds
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
                guard case .invalidPackage(let boardID, let reason) = error as? BoardPackageStoreError else {
                    return XCTFail("Expected invalidPackage, got \(error)")
                }
                XCTAssertEqual(boardID, "fixture.board")
                XCTAssertTrue(reason.contains("geometry"))
            }
        }
    }

    func testStoreRejectsSharedOutOfBoundsNormalizedFrames() throws {
        let validationFixtures = try validationFixtures()
        let frames = try XCTUnwrap(
            validationFixtures["outOfBoundsFrames"] as? [[String: Any]]
        )
        for frameFixture in frames {
            let name = try XCTUnwrap(frameFixture["name"] as? String)
            let frame = try XCTUnwrap(frameFixture["frame"] as? [String: Any])
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                    var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                    geometry[0]["frame"] = frame
                    holds[0]["geometry"] = geometry
                    board["holds"] = holds
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), name)
        }
    }

    func testStoreAcceptsExactlySupportedPhysicalHoldKinds() throws {
        let expectedKinds = ["jug", "edge", "pocket", "pinch", "sloper"]
        XCTAssertEqual(HoldKind.allCases.map(\.rawValue), expectedKinds)
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                let template = try XCTUnwrap(
                    (board["holds"] as? [[String: Any]])?.first
                )
                board["holds"] = expectedKinds.map { kind in
                    var hold = template
                    hold["id"] = "hold-\(kind)"
                    hold["name"] = "Fixture \(kind)"
                    hold["kind"] = kind
                    return hold
                }
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(board.holds.map(\.kind.rawValue), expectedKinds)
    }

    func testStoreRejectsUnsupportedPhysicalHoldKind() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["kind"] = "unsupported"
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreRejectsSharedMalformedPathShapes() throws {
        let validationFixtures = try validationFixtures()
        let shapes = try XCTUnwrap(
            validationFixtures["malformedPathShapes"] as? [[String: Any]]
        )
        for shape in shapes {
            let name = try XCTUnwrap(shape["name"] as? String)
            let expectedMessage = try XCTUnwrap(shape["expectedMessage"] as? String)
            let commands = try XCTUnwrap(shape["commands"] as? [[String: Any]])
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) {
                    var holds = try XCTUnwrap($0["holds"] as? [[String: Any]])
                    var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                    geometry[0]["shape"] = ["type": "path", "commands": commands]
                    holds[0]["geometry"] = geometry
                    $0["holds"] = holds
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), name) { error in
                guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                    return XCTFail("Expected invalidPackage for \(name), got \(error)")
                }
                XCTAssertTrue(reason.contains(expectedMessage), reason)
            }
        }
    }

    func testStoreRejectsUnknownKeysAtBoardHoldAndGeometryRoots() throws {
        for location in ["board", "hold", "geometry"] {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(at: hangboardsURL.appendingPathComponent("fixture-model/board.json")) {
                    if location == "board" {
                        $0["unexpected"] = true
                    } else {
                        var holds = try XCTUnwrap($0["holds"] as? [[String: Any]])
                        if location == "hold" {
                            holds[0]["unexpected"] = true
                        } else {
                            var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                            geometry[0]["unexpected"] = true
                            holds[0]["geometry"] = geometry
                        }
                        $0["holds"] = holds
                    }
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
                XCTAssertEqual(
                    error as? BoardPackageStoreError,
                    .malformedJSON(resource: "Hangboards/fixture-model/board.json")
                )
            }
        }
    }

    private func validationFixtures() throws -> [String: Any] {
        let fixtureURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .appendingPathComponent("Fixtures/BoardPackageValidationFixtures.json")
        return try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: fixtureURL)) as? [String: Any]
        )
    }

    private func pngFixture(named name: String) throws -> Data {
        let fixtures = try validationFixtures()
        let png = try XCTUnwrap(fixtures["png"] as? [String: Any])
        let encoded = try XCTUnwrap(png[name] as? String)
        return try XCTUnwrap(Data(base64Encoded: encoded))
    }

    private func presentationBytes() throws -> Data {
        try pngFixture(named: "validTwoByOneBase64")
    }

    private func makeFixtureBundle(
        packages: [PackageSpec] = [PackageSpec(slug: "fixture-model", id: "fixture.board")],
        draftSlugs: [String] = [],
        mutate: ((URL) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        let bundleURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardPackageStoreTests-\(UUID().uuidString)")
            .appendingPathExtension("bundle")
        let hangboardsURL = bundleURL.appendingPathComponent("Hangboards", isDirectory: true)
        try FileManager.default.createDirectory(at: hangboardsURL, withIntermediateDirectories: true)
        try propertyListData().write(to: bundleURL.appendingPathComponent("Info.plist"))

        for package in packages {
            let packageURL = hangboardsURL.appendingPathComponent(package.slug, isDirectory: true)
            let assetsURL = packageURL.appendingPathComponent("assets", isDirectory: true)
            try FileManager.default.createDirectory(at: assetsURL, withIntermediateDirectories: true)
            try boardData(for: package).write(to: packageURL.appendingPathComponent("board.json"))
            try presentationBytes().write(to: assetsURL.appendingPathComponent("primary.png"))
        }
        for slug in draftSlugs {
            let assetsURL = hangboardsURL.appendingPathComponent("\(slug)/assets", isDirectory: true)
            try FileManager.default.createDirectory(at: assetsURL, withIntermediateDirectories: true)
            try presentationBytes().write(to: assetsURL.appendingPathComponent("primary.png"))
        }
        try mutate?(hangboardsURL)

        return FixtureBundle(rootURL: bundleURL, bundle: try XCTUnwrap(Bundle(url: bundleURL)))
    }

    private func propertyListData() throws -> Data {
        try PropertyListSerialization.data(
            fromPropertyList: [
                "CFBundleIdentifier": "com.hangten.tests.board-package-fixture.\(UUID().uuidString)",
                "CFBundleName": "BoardPackageFixture",
                "CFBundlePackageType": "BNDL",
                "CFBundleVersion": "1"
            ],
            format: .xml,
            options: 0
        )
    }

    private func boardData(for package: PackageSpec) throws -> Data {
        try JSONSerialization.data(
            withJSONObject: [
                "schemaVersion": 1,
                "id": package.id,
                "manufacturer": package.manufacturer,
                "name": package.name,
                "subtitle": "A physical fixture board.",
                "productURL": "https://example.com/\(package.id)",
                "dimensions": "20 × 10 cm",
                "aspectRatio": 2,
                "presentation": ["assetPath": "assets/primary.png"],
                "holds": [[
                    "id": "hold-left",
                    "name": "Left hold",
                    "kind": "jug",
                    "geometry": [[
                        "frame": ["x": 0.05, "y": 0.2, "width": 0.1, "height": 0.3],
                        "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.2]
                    ], [
                        "frame": ["x": 0.35, "y": 0.1, "width": 0.1, "height": 0.2],
                        "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.1],
                        "treatment": ["type": "surface"]
                    ]]
                ]]
            ],
            options: [.sortedKeys]
        )
    }

    private func mutateBoard(
        at url: URL,
        mutation: (inout [String: Any]) throws -> Void
    ) throws {
        var document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any]
        )
        try mutation(&document)
        try JSONSerialization.data(withJSONObject: document, options: [.sortedKeys]).write(to: url)
    }
}

private struct PackageSpec {
    let slug: String
    let id: String
    let manufacturer: String
    let name: String

    init(
        slug: String,
        id: String,
        manufacturer: String = "Fixture Maker",
        name: String = "Fixture Board"
    ) {
        self.slug = slug
        self.id = id
        self.manufacturer = manufacturer
        self.name = name
    }
}

private struct FixtureBundle {
    let rootURL: URL
    let bundle: Bundle

    func remove() {
        try? FileManager.default.removeItem(at: rootURL)
    }
}
