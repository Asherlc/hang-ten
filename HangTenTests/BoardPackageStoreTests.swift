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
