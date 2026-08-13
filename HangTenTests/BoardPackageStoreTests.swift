import XCTest
@testable import HangTen

final class BoardPackageStoreTests: XCTestCase {
    func testStoreLoadsOnlyApprovedPackageDataAndResources() throws {
        let fixture = try makeFixtureBundle()
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.board(id: "approved-board"))
        let design = try XCTUnwrap(store.design(for: board.id))
        let imageURL = try XCTUnwrap(store.presentationImageURL(for: board))

        XCTAssertEqual(store.boards.map(\.id), ["approved-board"])
        XCTAssertNil(store.board(id: "draft-board"))
        XCTAssertEqual(board.manufacturer, "Fixture Maker")
        XCTAssertEqual(board.name, "Approved Board")
        XCTAssertEqual(board.subtitle, "Package-owned fixture metadata.")
        XCTAssertEqual(board.dimensions, "20 × 10 cm")
        XCTAssertEqual(board.aspectRatio, 2)
        XCTAssertEqual(board.productURL.absoluteString, "https://example.com/approved-board")
        XCTAssertEqual(board.holds.map(\.id), ["jug-left", "jug-right"])
        XCTAssertEqual(board.holds.first?.gripType, .openHand)
        XCTAssertEqual(board.holds.first?.fingerCapacity, 4)
        XCTAssertEqual(board.holds.first?.cueStyle, .outerJug)
        XCTAssertEqual(board.holds.first?.features, [.jug])
        XCTAssertNil(board.photoAssetName)
        XCTAssertEqual(
            store.semantics(for: "approved-board")["outer-jugs"],
            ["jug-left", "jug-right"]
        )
        XCTAssertEqual(design.id, "approved-board")
        XCTAssertEqual(design.layers.count, 1)
        XCTAssertEqual(design.holds.map(\.holdID), ["jug-left", "jug-right"])
        XCTAssertEqual(imageURL.lastPathComponent, "presentation.png")
        XCTAssertEqual(try Data(contentsOf: imageURL), presentationBytes)
    }

    func testStoreReportsMalformedJSONResource() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try Data("{ malformed".utf8).write(to: packageURL.appendingPathComponent("board.json"))
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .malformedJSON(resource: "Hangboards/approved-board/board.json")
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
                    .missingApprovedSidecar(boardID: "approved-board", filename: filename)
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
                .unknownArtworkHoldID(boardID: "approved-board", holdID: "unknown-hold")
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
                .missingArtworkHoldID(boardID: "approved-board", holdID: "jug-right")
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
                .presentationAssetPathEscape(boardID: "approved-board", path: "../escaped.png")
            )
        }
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
                .approvedPackagePathEscape(boardID: "approved-board", path: "board.json")
            )
        }
    }

    func testStoreRejectsUnknownKeysAtSidecarRoots() throws {
        for (relativePath, resource) in [
            ("../catalog.json", "Hangboards/catalog.json"),
            ("board.json", "Hangboards/approved-board/board.json"),
            ("semantics.json", "Hangboards/approved-board/semantics.json"),
            ("artwork.json", "Hangboards/approved-board/artwork.json")
        ] {
            try assertMalformedJSON(relativePath: relativePath, resource: resource) { document in
                document["unexpected"] = true
            }
        }
    }

    func testStoreRejectsUnknownKeysInNestedPackageDocuments() throws {
        try assertMalformedJSON(
            relativePath: "board.json",
            resource: "Hangboards/approved-board/board.json"
        ) { board in
            var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
            holds[0]["unexpected"] = true
            board["holds"] = holds
        }

        try assertMalformedJSON(
            relativePath: "semantics.json",
            resource: "Hangboards/approved-board/semantics.json"
        ) { semantics in
            var mappings = try XCTUnwrap(semantics["semanticHolds"] as? [String: Any])
            var outerJugs = try XCTUnwrap(mappings["outer-jugs"] as? [String: Any])
            outerJugs["unexpected"] = true
            mappings["outer-jugs"] = outerJugs
            semantics["semanticHolds"] = mappings
        }

        try assertMalformedJSON(
            relativePath: "artwork.json",
            resource: "Hangboards/approved-board/artwork.json"
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
        let packageURL = hangboardsURL.appendingPathComponent("approved-board", isDirectory: true)
        let assetsURL = packageURL.appendingPathComponent("assets", isDirectory: true)

        try FileManager.default.createDirectory(at: assetsURL, withIntermediateDirectories: true)
        try propertyListData().write(to: bundleURL.appendingPathComponent("Info.plist"))
        try catalogData.write(to: hangboardsURL.appendingPathComponent("catalog.json"))
        try boardData.write(to: packageURL.appendingPathComponent("board.json"))
        try semanticsData.write(to: packageURL.appendingPathComponent("semantics.json"))
        try artworkData.write(to: packageURL.appendingPathComponent("artwork.json"))
        try presentationBytes.write(to: assetsURL.appendingPathComponent("presentation.png"))
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
            XCTAssertEqual(boardID, "approved-board")
        }
    }

    private var catalogData: Data {
        Data(
            #"""
            {
              "schemaVersion": 1,
              "boards": [
                { "id": "approved-board", "path": "approved-board", "status": "approved" },
                { "id": "draft-board", "path": "draft-board", "status": "draft" }
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
              "id": "approved-board",
              "manufacturer": "Fixture Maker",
              "name": "Approved Board",
              "subtitle": "Package-owned fixture metadata.",
              "productURL": "https://example.com/approved-board",
              "dimensions": "20 × 10 cm",
              "aspectRatio": 2,
              "presentation": { "assetPath": "assets/presentation.png" },
              "holds": [
                {
                  "id": "jug-left",
                  "name": "Left jug",
                  "shortLabel": "JL",
                  "detail": "Left fixture jug.",
                  "kind": "jug",
                  "frame": { "x": 0.05, "y": 0.2, "width": 0.3, "height": 0.4 },
                  "sizeMillimeters": null,
                  "depthRangeMillimeters": null,
                  "gripType": "openHand",
                  "fingerCapacity": 4,
                  "cueStyle": "outerJug",
                  "features": ["jug"]
                },
                {
                  "id": "jug-right",
                  "name": "Right jug",
                  "shortLabel": "JR",
                  "detail": "Right fixture jug.",
                  "kind": "jug",
                  "frame": { "x": 0.65, "y": 0.2, "width": 0.3, "height": 0.4 },
                  "sizeMillimeters": null,
                  "depthRangeMillimeters": null,
                  "gripType": "openHand",
                  "fingerCapacity": 4,
                  "cueStyle": "outerJug",
                  "features": ["jug"]
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
              "boardID": "approved-board",
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
              "boardID": "approved-board",
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
