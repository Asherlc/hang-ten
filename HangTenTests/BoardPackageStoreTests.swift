import XCTest
@testable import HangTen

final class BoardPackageStoreTests: XCTestCase {
    func testStoreErrorsDoNotExposeRemovedLifecycleState() {
        let errors: [BoardPackageStoreError] = [
            .presentationAssetPathEscape(boardID: "package-board", path: "../primary.png"),
            .missingPresentationAsset(boardID: "package-board", path: "assets/primary.png"),
            .duplicateHoldID(boardID: "package-board", holdID: "jug-left"),
            .unknownSemanticHoldID(boardID: "package-board", holdID: "missing"),
            .unknownArtworkHoldID(boardID: "package-board", holdID: "missing"),
            .missingArtworkHoldID(boardID: "package-board", holdID: "missing"),
            .invalidPackage(boardID: "package-board", reason: "fixture")
        ]

        for error in errors {
            let description = error.localizedDescription.lowercased()
            XCTAssertFalse(description.contains("approved"))
            XCTAssertFalse(description.contains("draft"))
        }
    }

    func testStoreLoadsEveryCatalogPackageDataAndResources() throws {
        let fixture = try makeFixtureBundle()
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.board(id: "package-board"))
        let design = try XCTUnwrap(store.design(for: board.id))
        let imageURL = try XCTUnwrap(store.presentationImageURL(for: board))

        XCTAssertEqual(store.boards.map(\.id), ["package-board"])
        XCTAssertEqual(board.manufacturer, "Fixture Maker")
        XCTAssertEqual(board.name, "Approved Board")
        XCTAssertEqual(board.subtitle, "Package-owned fixture metadata.")
        XCTAssertEqual(board.dimensions, "20 × 10 cm")
        XCTAssertEqual(board.aspectRatio, 2)
        XCTAssertEqual(board.productURL.absoluteString, "https://example.com/package-board")
        XCTAssertEqual(board.holds.map(\.id), ["jug-left", "jug-right"])
        let firstHold = try XCTUnwrap(board.holds.first)
        XCTAssertEqual(firstHold.geometry.count, 2)
        XCTAssertEqual(firstHold.frame.rect, CGRect(x: 0.05, y: 0.2, width: 0.3, height: 0.4))
        XCTAssertNil(firstHold.sizeMillimeters)
        XCTAssertNil(firstHold.depthRangeMillimeters)
        XCTAssertNil(firstHold.gripType)
        XCTAssertNil(firstHold.fingerCapacity)
        XCTAssertNil(firstHold.features)
        XCTAssertNil(board.photoAssetName)
        XCTAssertEqual(
            store.semantics(for: "package-board")["outer-jugs"],
            ["jug-left", "jug-right"]
        )
        XCTAssertEqual(design.id, "package-board")
        XCTAssertEqual(design.layers.count, 1)
        XCTAssertEqual(design.holds.map(\.holdID), ["jug-left", "jug-left", "jug-right"])
        XCTAssertEqual(design.interactionFrame(for: firstHold.id), firstHold.frame.rect)
        let boardRect = CGRect(x: 0, y: 0, width: 200, height: 100)
        let pieces = design.holdPieces(for: firstHold.id)
        let drawnPaths = pieces.map { design.renderPath(for: $0, in: boardRect) }
        let interactionPath = BoardHoldPathShape(
            pieces: pieces
        ).path(in: boardRect)

        let firstPieceCenter = CGPoint(x: 20, y: 40)
        let roundedCornerOutside = CGPoint(x: 10.5, y: 20.5)
        let secondPieceCenter = CGPoint(x: 60, y: 40)
        let gapBetweenPieces = CGPoint(x: 40, y: 40)

        XCTAssertTrue(drawnPaths[0].contains(firstPieceCenter))
        XCTAssertFalse(drawnPaths[0].contains(roundedCornerOutside))
        XCTAssertTrue(drawnPaths[1].contains(secondPieceCenter))
        XCTAssertFalse(drawnPaths[1].contains(gapBetweenPieces))

        XCTAssertTrue(interactionPath.contains(firstPieceCenter))
        XCTAssertFalse(interactionPath.contains(roundedCornerOutside))
        XCTAssertTrue(interactionPath.contains(secondPieceCenter))
        XCTAssertFalse(interactionPath.contains(gapBetweenPieces))
        XCTAssertEqual(imageURL.lastPathComponent, "primary.png")
        XCTAssertEqual(try Data(contentsOf: imageURL), presentationBytes)
    }

    func testStoreRejectsEmptyPhysicalHoldGeometry() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["geometry"] = []
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(let boardID, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertEqual(boardID, "package-board")
            XCTAssertTrue(reason.contains("geometry"))
        }
    }

    func testStoreRejectsOutOfRangePhysicalHoldGeometry() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                var frame = try XCTUnwrap(geometry[0]["frame"] as? [String: Any])
                frame["x"] = -0.1
                geometry[0]["frame"] = frame
                holds[0]["geometry"] = geometry
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(let boardID, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertEqual(boardID, "package-board")
            XCTAssertTrue(reason.contains("geometry"))
        }
    }

    func testStoreRejectsUnsupportedPhysicalHoldKindsDuringDecoding() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["kind"] = "unsupported"
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .malformedJSON(resource: "Hangboards/package-board/board.json")
            )
        }
    }

    func testStoreReportsMalformedJSONResource() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try Data("{ malformed".utf8).write(to: packageURL.appendingPathComponent("board.json"))
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .malformedJSON(resource: "Hangboards/package-board/board.json")
            )
        }
    }

    func testStoreReportsEachMissingApprovedSidecar() throws {
        for filename in ["board.json", "semantics.json", "artwork.json"] {
            let fixture = try makeFixtureBundle { packageURL in
                try FileManager.default.removeItem(at: packageURL.appendingPathComponent(filename))
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), filename) { error in
                XCTAssertEqual(
                    error as? BoardPackageStoreError,
                    .missingPackageSidecar(boardID: "package-board", filename: filename)
                )
            }
        }
    }

    func testStoreRejectsArtworkWithUnknownHoldID() throws {
        let fixture = try makeFixtureBundle { packageURL in
            let artworkURL = packageURL.appendingPathComponent("artwork.json")
            try self.mutateJSONObject(at: artworkURL) { artwork in
                var pieces = try XCTUnwrap(artwork["holdPieces"] as? [[String: Any]])
                pieces[0]["holdID"] = "unknown-hold"
                artwork["holdPieces"] = pieces
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .unknownArtworkHoldID(boardID: "package-board", holdID: "unknown-hold")
            )
        }
    }

    func testStoreRejectsArtworkMissingPhysicalHoldID() throws {
        let fixture = try makeFixtureBundle { packageURL in
            let artworkURL = packageURL.appendingPathComponent("artwork.json")
            try self.mutateJSONObject(at: artworkURL) { artwork in
                var pieces = try XCTUnwrap(artwork["holdPieces"] as? [[String: Any]])
                pieces.removeLast()
                artwork["holdPieces"] = pieces
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .missingArtworkHoldID(boardID: "package-board", holdID: "jug-right")
            )
        }
    }

    func testStoreRejectsPresentationAssetPathEscape() throws {
        let fixture = try makeFixtureBundle { packageURL in
            let boardURL = packageURL.appendingPathComponent("board.json")
            try self.mutateJSONObject(at: boardURL) { board in
                board["presentation"] = ["assetPath": "../escaped.png"]
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .presentationAssetPathEscape(boardID: "package-board", path: "../escaped.png")
            )
        }
    }

    func testStoreTreatsNullPresentationAsAbsent() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                board["presentation"] = NSNull()
            }
        }
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.board(id: "package-board"))

        XCTAssertNil(store.presentationImageURL(for: board))
    }

    func testStoreRejectsApprovedSidecarSymlinkEscapingPackage() throws {
        let fixture = try makeFixtureBundle { packageURL in
            let boardURL = packageURL.appendingPathComponent("board.json")
            let escapedURL = packageURL.deletingLastPathComponent()
                .appendingPathComponent("escaped-board.json")
            try FileManager.default.moveItem(at: boardURL, to: escapedURL)
            try FileManager.default.createSymbolicLink(
                at: boardURL,
                withDestinationURL: escapedURL
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .packagePathEscape(boardID: "package-board", path: "board.json")
            )
        }
    }

    func testStoreRejectsUnknownKeysAtSidecarRoots() throws {
        for (relativePath, resource) in [
            ("../catalog.json", "Hangboards/catalog.json"),
            ("board.json", "Hangboards/package-board/board.json"),
            ("semantics.json", "Hangboards/package-board/semantics.json"),
            ("artwork.json", "Hangboards/package-board/artwork.json")
        ] {
            try assertMalformedJSON(relativePath: relativePath, resource: resource) { document in
                document["unexpected"] = true
            }
        }
    }

    func testStoreRejectsUnknownKeysInNestedPackageDocuments() throws {
        try assertMalformedJSON(
            relativePath: "board.json",
            resource: "Hangboards/package-board/board.json"
        ) { board in
            var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
            holds[0]["unexpected"] = true
            board["holds"] = holds
        }

        try assertMalformedJSON(
            relativePath: "semantics.json",
            resource: "Hangboards/package-board/semantics.json"
        ) { semantics in
            var mappings = try XCTUnwrap(semantics["semanticHolds"] as? [String: Any])
            var outerJugs = try XCTUnwrap(mappings["outer-jugs"] as? [String: Any])
            outerJugs["unexpected"] = true
            mappings["outer-jugs"] = outerJugs
            semantics["semanticHolds"] = mappings
        }

        try assertMalformedJSON(
            relativePath: "artwork.json",
            resource: "Hangboards/package-board/artwork.json"
        ) { artwork in
            var pieces = try XCTUnwrap(artwork["holdPieces"] as? [[String: Any]])
            var treatment = try XCTUnwrap(pieces[0]["treatment"] as? [String: Any])
            treatment["unexpected"] = true
            pieces[0]["treatment"] = treatment
            artwork["holdPieces"] = pieces
        }
    }

    func testStoreRejectsEmptyDuplicateAndNonPositiveBoardMetadata() throws {
        try assertInvalidPackage { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                board["manufacturer"] = ""
            }
        }

        try assertInvalidPackage { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["sizeMillimeters"] = 0
                board["holds"] = holds
            }
        }

        try assertInvalidPackage { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["depthRangeMillimeters"] = ["lowerBound": 0, "upperBound": 10]
                board["holds"] = holds
            }
        }

        try assertInvalidPackage { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["features"] = ["jug", "jug"]
                board["holds"] = holds
            }
        }
    }

    func testStoreRejectsEmptyAndDuplicateSemanticHoldIDs() throws {
        try assertInvalidPackage { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("semantics.json")) { semantics in
                var mappings = try XCTUnwrap(semantics["semanticHolds"] as? [String: Any])
                mappings[""] = mappings.removeValue(forKey: "outer-jugs")
                semantics["semanticHolds"] = mappings
            }
        }

        try assertInvalidPackage { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("semantics.json")) { semantics in
                semantics["semanticHolds"] = ["outer-jugs": ["holdIDs": []]]
            }
        }

        try assertInvalidPackage { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("semantics.json")) { semantics in
                semantics["semanticHolds"] = [
                    "outer-jugs": ["holdIDs": ["jug-left", "jug-left"]]
                ]
            }
        }
    }

    private var presentationBytes: Data {
        Data([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
    }

    private func makeFixtureBundle(
        mutate: ((URL) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        let bundleURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardPackageStoreTests-\(UUID().uuidString)")
            .appendingPathExtension("bundle")
        let hangboardsURL = bundleURL.appendingPathComponent("Hangboards", isDirectory: true)
        let packageURL = hangboardsURL.appendingPathComponent("package-board", isDirectory: true)
        let assetsURL = packageURL.appendingPathComponent("assets", isDirectory: true)

        try FileManager.default.createDirectory(at: assetsURL, withIntermediateDirectories: true)
        try propertyListData().write(to: bundleURL.appendingPathComponent("Info.plist"))
        try catalogData.write(to: hangboardsURL.appendingPathComponent("catalog.json"))
        try boardData.write(to: packageURL.appendingPathComponent("board.json"))
        try semanticsData.write(to: packageURL.appendingPathComponent("semantics.json"))
        try artworkData.write(to: packageURL.appendingPathComponent("artwork.json"))
        try presentationBytes.write(to: assetsURL.appendingPathComponent("primary.png"))
        try mutate?(packageURL)

        let bundle = try XCTUnwrap(Bundle(url: bundleURL))
        return FixtureBundle(rootURL: bundleURL, bundle: bundle)
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

    private func mutateJSONObject(
        at url: URL,
        mutation: (inout [String: Any]) throws -> Void
    ) throws {
        var object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any]
        )
        try mutation(&object)
        try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
            .write(to: url)
    }

    private func assertMalformedJSON(
        relativePath: String,
        resource: String,
        mutation: @escaping (inout [String: Any]) throws -> Void
    ) throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(
                at: packageURL.appendingPathComponent(relativePath).standardizedFileURL,
                mutation: mutation
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), resource) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .malformedJSON(resource: resource)
            )
        }
    }

    private func assertInvalidPackage(
        mutation: @escaping (URL) throws -> Void
    ) throws {
        let fixture = try makeFixtureBundle(mutate: mutation)
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(let boardID, _) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertEqual(boardID, "package-board")
        }
    }

    private var catalogData: Data {
        Data(
            #"""
            {
              "schemaVersion": 1,
              "boards": [
                { "id": "package-board", "path": "package-board" }
              ]
            }
            """#.utf8
        )
    }

    private var boardData: Data {
        Data(
            #"""
            {
              "schemaVersion": 1,
              "id": "package-board",
              "manufacturer": "Fixture Maker",
              "name": "Approved Board",
              "subtitle": "Package-owned fixture metadata.",
              "productURL": "https://example.com/package-board",
              "dimensions": "20 × 10 cm",
              "aspectRatio": 2,
              "presentation": { "assetPath": "assets/primary.png" },
              "holds": [
                {
                  "id": "jug-left",
                  "name": "Left jug",
                  "kind": "jug",
                  "geometry": [
                    {
                      "frame": { "x": 0.05, "y": 0.2, "width": 0.1, "height": 0.4 },
                      "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.2 }
                    },
                    {
                      "frame": { "x": 0.25, "y": 0.25, "width": 0.1, "height": 0.3 },
                      "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.2 }
                    }
                  ]
                },
                {
                  "id": "jug-right",
                  "name": "Right jug",
                  "kind": "jug",
                  "geometry": [{
                    "frame": { "x": 0.65, "y": 0.2, "width": 0.3, "height": 0.4 },
                    "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.2 }
                  }]
                }
              ]
            }
            """#.utf8
        )
    }

    private var semanticsData: Data {
        Data(
            #"""
            {
              "schemaVersion": 1,
              "boardID": "package-board",
              "semanticHolds": {
                "outer-jugs": { "holdIDs": ["jug-left", "jug-right"] }
              }
            }
            """#.utf8
        )
    }

    private var artworkData: Data {
        Data(
            #"""
            {
              "schemaVersion": 1,
              "boardID": "package-board",
              "canvasFrame": { "x": 0.05, "y": 0.05, "width": 0.9, "height": 0.9 },
              "palette": "sculptedWood",
              "silhouette": { "type": "roundedRect", "cornerRadiusFraction": 0.1 },
              "layers": [{
                "id": "face",
                "role": "faceLight",
                "frame": { "x": 0, "y": 0, "width": 1, "height": 1 },
                "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.1 }
              }],
              "holdPieces": [
                {
                  "id": "jug-left-piece",
                  "holdID": "jug-left",
                  "frame": { "x": 0.05, "y": 0.2, "width": 0.3, "height": 0.4 },
                  "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.2 },
                  "treatment": { "type": "shelf", "rimInsetFraction": 0.06 }
                },
                {
                  "id": "jug-right-piece",
                  "holdID": "jug-right",
                  "frame": { "x": 0.65, "y": 0.2, "width": 0.3, "height": 0.4 },
                  "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.2 },
                  "treatment": { "type": "surface" }
                }
              ]
            }
            """#.utf8
        )
    }
}

private struct FixtureBundle {
    let rootURL: URL
    let bundle: Bundle

    func remove() {
        try? FileManager.default.removeItem(at: rootURL)
    }
}
