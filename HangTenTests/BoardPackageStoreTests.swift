import XCTest
import UIKit
@testable import HangTen

final class BoardPackageStoreTests: XCTestCase {
    func testStoreErrorsDoNotExposeRemovedLifecycleState() {
        let errors: [BoardPackageStoreError] = [
            .presentationAssetPathEscape(boardID: "package-board", path: "../primary.png"),
            .missingPresentationAsset(boardID: "package-board", path: "assets/primary.png"),
            .duplicateHoldID(boardID: "package-board", holdID: "jug-left"),
            .unknownSemanticHoldID(boardID: "package-board", holdID: "missing"),
            .invalidPackage(boardID: "package-board", reason: "fixture")
        ]

        for error in errors {
            let description = error.localizedDescription.lowercased()
            XCTAssertFalse(description.contains("approved"))
            XCTAssertFalse(description.contains("draft"))
        }
    }

    func testStoreLoadsPackageWithDirectArtworkEvidence() throws {
        let fixture = try makeFixtureBundle()
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        XCTAssertEqual(store.boards.map(\.id), ["package-board"])
        XCTAssertEqual(
            try XCTUnwrap(store.presentationImageURL(for: try XCTUnwrap(store.boards.first))).lastPathComponent,
            "primary.png"
        )
    }

    func testStoreRequiresDirectArtworkDocument() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try FileManager.default.removeItem(at: packageURL.appendingPathComponent("artwork.json"))
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .missingPackageSidecar(boardID: "package-board", filename: "artwork.json")
            )
        }
    }

    func testStoreRejectsArtworkEvidenceWithUnknownCanonicalKey() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("evidence.json")) { evidence in
                var artworkEvidence = try XCTUnwrap(evidence["artworkEvidence"] as? [String: Any])
                artworkEvidence["layers.unknown-layer"] = artworkEvidence["silhouette"]
                evidence["artworkEvidence"] = artworkEvidence
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .malformedJSON(resource: "Hangboards/package-board/evidence.json")
            )
        }
    }

    func testStoreRejectsMalformedArtworkEvidenceMapping() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("evidence.json")) { evidence in
                var artworkEvidence = try XCTUnwrap(evidence["artworkEvidence"] as? [String: Any])
                artworkEvidence["silhouette"] = ["sourceIDs": ["fixture-source"]]
                evidence["artworkEvidence"] = artworkEvidence
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .malformedJSON(resource: "Hangboards/package-board/evidence.json")
            )
        }
    }

    func testStoreLoadsEveryCatalogPackageDataAndResources() throws {
        let fixture = try makeFixtureBundle()
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.board(id: "package-board"))
        let imageURL = try XCTUnwrap(store.presentationImageURL(for: board))

        XCTAssertEqual(store.boards.map(\.id), ["package-board"])
        XCTAssertEqual(board.manufacturer, "Fixture Maker")
        XCTAssertEqual(board.name, "Approved Board")
        XCTAssertEqual(board.subtitle, "Package-owned fixture metadata.")
        XCTAssertEqual(board.dimensions, "20 × 10 cm")
        XCTAssertEqual(board.aspectRatio, 2)
        XCTAssertEqual(board.productURL.absoluteString, "https://example.com/package-board")
        XCTAssertEqual(board.holds.map(\.id), ["jug-left", "jug-right"])
        XCTAssertEqual(board.holds.first?.gripType, .openHand)
        XCTAssertEqual(board.holds.first?.fingerCapacity, 4)
        XCTAssertEqual(board.holds.first?.cueStyle, .outerJug)
        XCTAssertEqual(board.holds.first?.features, [.jug])
        XCTAssertNil(board.photoAssetName)
        XCTAssertEqual(
            store.semantics(for: "package-board")["outer-jugs"],
            ["jug-left", "jug-right"]
        )
        XCTAssertEqual(imageURL.lastPathComponent, "primary.png")
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
                .malformedJSON(resource: "Hangboards/package-board/board.json")
            )
        }
    }

    func testStoreReportsEachMissingPackageSidecar() throws {
        for filename in ["board.json", "artwork.json", "evidence.json", "semantics.json"] {
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

    func testStoreRejectsAbsentAndNullPresentationDeclarations() throws {
        for presentation: Any? in [nil, NSNull()] {
            let fixture = try makeFixtureBundle { packageURL in
                try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                    board["presentation"] = presentation
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
                XCTAssertEqual(
                    error as? BoardPackageStoreError,
                    .invalidPackage(
                        boardID: "package-board",
                        reason: "presentation declaration is required"
                    )
                )
            }
        }
    }

    func testStoreRejectsNonPrimaryPresentationPath() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                board["presentation"] = ["assetPath": "assets/alternate.png"]
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "package-board",
                    reason: "presentation asset path must be assets/primary.png"
                )
            )
        }
    }

    func testStoreRejectsMissingPrimaryPresentationAsset() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try FileManager.default.removeItem(
                at: packageURL.appendingPathComponent("assets/primary.png")
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .missingPresentationAsset(boardID: "package-board", path: "assets/primary.png")
            )
        }
    }

    func testStoreRejectsUndecodablePrimaryPresentationAsset() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try Data("not a PNG".utf8).write(
                to: packageURL.appendingPathComponent("assets/primary.png")
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "package-board",
                    reason: "presentation asset must be a decodable PNG"
                )
            )
        }
    }

    func testStoreRejectsDecodableJPEGRenamedToPrimaryPNG() throws {
        let jpegBytes = try self.makeJPEGBytes()
        XCTAssertNotNil(UIImage(data: jpegBytes))
        let fixture = try makeFixtureBundle { packageURL in
            try jpegBytes.write(
                to: packageURL.appendingPathComponent("assets/primary.png")
            )
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "package-board",
                    reason: "presentation asset must be a decodable PNG"
                )
            )
        }
    }

    func testStoreRejectsUnsupportedEvidenceSchema() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("evidence.json")) { evidence in
                evidence["schemaVersion"] = 2
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .malformedJSON(resource: "Hangboards/package-board/evidence.json")
            )
        }
    }

    func testStoreRejectsEvidenceBoardIDMismatch() throws {
        let fixture = try makeFixtureBundle { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("evidence.json")) { evidence in
                evidence["boardID"] = "other-board"
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .boardIDMismatch(
                    expected: "package-board",
                    actual: "other-board",
                    resource: "Hangboards/package-board/evidence.json"
                )
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
                .packagePathEscape(boardID: "package-board", path: "board.json")
            )
        }
    }

    func testStoreRejectsUnknownKeysAtSidecarRoots() throws {
        for (relativePath, resource) in [
            ("../catalog.json", "Hangboards/catalog.json"),
            ("board.json", "Hangboards/package-board/board.json"),
            ("artwork.json", "Hangboards/package-board/artwork.json"),
            ("evidence.json", "Hangboards/package-board/evidence.json"),
            ("semantics.json", "Hangboards/package-board/semantics.json")
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

    }

    func testStoreRejectsMalformedNestedArtworkGeometry() throws {
        try assertMalformedJSON(
            relativePath: "artwork.json",
            resource: "Hangboards/package-board/artwork.json"
        ) { artwork in
            var pieces = try XCTUnwrap(artwork["holdPieces"] as? [[String: Any]])
            var shape = try XCTUnwrap(pieces[0]["shape"] as? [String: Any])
            shape["unexpected"] = true
            pieces[0]["shape"] = shape
            artwork["holdPieces"] = pieces
        }

        try assertMalformedJSON(
            relativePath: "artwork.json",
            resource: "Hangboards/package-board/artwork.json"
        ) { artwork in
            var layers = try XCTUnwrap(artwork["layers"] as? [[String: Any]])
            layers[0]["role"] = "unsupported-role"
            artwork["layers"] = layers
        }

        try assertMalformedJSON(
            relativePath: "artwork.json",
            resource: "Hangboards/package-board/artwork.json"
        ) { artwork in
            var pieces = try XCTUnwrap(artwork["holdPieces"] as? [[String: Any]])
            pieces[0]["treatment"] = ["type": "recess", "rimInsetFraction": 0.1, "depth": "unknown"]
            artwork["holdPieces"] = pieces
        }
    }

    func testStoreRejectsBoardFrameThatDoesNotMatchArtworkOutline() throws {
        try assertInvalidPackage { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["frame"] = ["x": 0.06, "y": 0.2, "width": 0.3, "height": 0.4]
                board["holds"] = holds
            }
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
        try! XCTUnwrap(
            Data(base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlQjXcAAAAASUVORK5CYII=")
        )
    }

    private func makeJPEGBytes() throws -> Data {
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: 1, height: 1))
        let image = renderer.image { context in
            UIColor.systemRed.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 1, height: 1))
        }

        return try XCTUnwrap(image.jpegData(compressionQuality: 1))
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
        try artworkData.write(to: packageURL.appendingPathComponent("artwork.json"))
        try evidenceData.write(to: packageURL.appendingPathComponent("evidence.json"))
        try semanticsData.write(to: packageURL.appendingPathComponent("semantics.json"))
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
              "canvasFrame": { "x": 0, "y": 0, "width": 1, "height": 1 },
              "palette": "sculptedWood",
              "silhouette": { "type": "roundedRect", "cornerRadiusFraction": 0.1 },
              "layers": [
                {
                  "id": "top-plane",
                  "role": "topPlane",
                  "frame": { "x": 0, "y": 0, "width": 1, "height": 1 },
                  "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.1 }
                }
              ],
              "holdPieces": [
                {
                  "id": "jug-left-outline",
                  "holdID": "jug-left",
                  "frame": { "x": 0.05, "y": 0.2, "width": 0.3, "height": 0.4 },
                  "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.1 },
                  "treatment": { "type": "surface" }
                },
                {
                  "id": "jug-right-outline",
                  "holdID": "jug-right",
                  "frame": { "x": 0.65, "y": 0.2, "width": 0.3, "height": 0.4 },
                  "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.1 },
                  "treatment": { "type": "surface" }
                }
              ]
            }
            """#.utf8
        )
    }

    private var evidenceData: Data {
        let mapping: [String: Any] = [
            "sourceIDs": ["fixture-source"],
            "method": "reviewed-human-authored-normalization"
        ]
        let fieldEvidence = Dictionary(
            uniqueKeysWithValues: [
                "manufacturer", "name", "subtitle", "productURL", "dimensions", "aspectRatio"
            ].map { ($0, mapping) }
        )
        let holdEvidence = Dictionary(
            uniqueKeysWithValues: ["jug-left", "jug-right"].flatMap { holdID in
                [
                    "id", "name", "shortLabel", "detail", "kind", "frame", "sizeMillimeters",
                    "depthRangeMillimeters", "gripType", "fingerCapacity", "cueStyle", "features"
                ].map { field in ("\(holdID).\(field)", mapping) }
            }
        )
        let artworkEvidence = Dictionary(
            uniqueKeysWithValues: [
                "silhouette", "layers.top-plane", "holdPieces.jug-left-outline",
                "holdPieces.jug-right-outline"
            ].map { ($0, mapping) }
        )
        return try! JSONSerialization.data(
            withJSONObject: [
                "schemaVersion": 1,
                "boardID": "package-board",
                "checkedAt": "2026-08-14",
                "sources": [[
                    "id": "fixture-source",
                    "title": "Fixture source",
                    "url": "https://example.com/source"
                ]],
                "fieldEvidence": fieldEvidence,
                "holdEvidence": holdEvidence,
                "semanticEvidence": ["outer-jugs": mapping],
                "artworkEvidence": artworkEvidence,
                "assetEvidence": ["assets/primary.png": mapping]
            ],
            options: [.sortedKeys]
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
