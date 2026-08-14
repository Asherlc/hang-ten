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

    func testStoreLoadsPackageWithoutArtworkDocument() throws {
        let fixture = try makeFixtureBundle()
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        XCTAssertEqual(store.boards.map(\.id), ["package-board"])
        XCTAssertEqual(
            try XCTUnwrap(store.presentationImageURL(for: try XCTUnwrap(store.boards.first))).lastPathComponent,
            "primary.png"
        )
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
        for filename in ["board.json", "evidence.json", "semantics.json"] {
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
        XCTAssertNotNil(UIImage(data: self.jpegBytes))
        let fixture = try makeFixtureBundle { packageURL in
            try self.jpegBytes.write(
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

    private var jpegBytes: Data {
        try! XCTUnwrap(
            Data(base64Encoded: "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAH/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/AL//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/AL//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/AL//2gAMAwEAAgADAAAAEP/EABQQAQAAAAAAAAAAAAAAAAAAABD/2gAIAQEAAT8QH//EABQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQMBAT8QH//EABQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQIBAT8QH//Z")
        )
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

    private var evidenceData: Data {
        Data(
            #"""
            {
              "schemaVersion": 1,
              "boardID": "package-board",
              "checkedAt": "2026-08-14",
              "sources": [],
              "fieldEvidence": {},
              "holdEvidence": {},
              "semanticEvidence": {},
              "assetEvidence": {}
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
