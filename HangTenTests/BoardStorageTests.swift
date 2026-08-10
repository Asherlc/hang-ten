import XCTest
@testable import HangTen

final class BoardStorageTests: XCTestCase {
    func testBoardLibraryDecodesCompactBoardMetadataAndHoldFrame() throws {
        let store = try BoardLibraryStore(data: compactFixture)
        let board = try XCTUnwrap(store.boards.first)
        let hold = try XCTUnwrap(board.holds.first)

        XCTAssertEqual(board.id, "fixture.board")
        XCTAssertEqual(board.manufacturer, "Fixture Maker")
        XCTAssertEqual(hold.id, "fixture.hold")
        XCTAssertEqual(hold.frame.rect, CGRect(x: 0.1, y: 0.2, width: 0.3, height: 0.4))
        XCTAssertEqual(hold.gripType, .openHand)
        XCTAssertEqual(hold.fingerCapacity, 4)
        XCTAssertEqual(hold.cueStyle, .slot)
        XCTAssertEqual(hold.features, [])
    }

    func testBoardLibraryLoadsAndExportsDeterministicSortedJSON() throws {
        let fixtureURL = try writeTemporaryFixture(compactFixture)
        defer { try? FileManager.default.removeItem(at: fixtureURL) }

        let store = try BoardLibraryStore(contentsOf: fixtureURL)
        let firstExport = try store.encodedData(prettyPrinted: true)
        let secondExport = try store.encodedData(prettyPrinted: true)
        let roundTripped = try BoardLibraryStore(data: firstExport)

        XCTAssertEqual(firstExport, secondExport)
        XCTAssertEqual(firstExport.first, UInt8(ascii: "{"))
        XCTAssertTrue(String(decoding: firstExport, as: UTF8.self).contains("\n"))
        XCTAssertEqual(roundTripped.boards, store.boards)
    }

    func testBundledCompactIIFixtureDecodesEveryBoardHold() throws {
        let resourceURL = try XCTUnwrap(
            Bundle(for: Self.self).url(forResource: "BoardLibrary", withExtension: "json")
        )
        let store = try BoardLibraryStore(contentsOf: resourceURL)
        let board = try XCTUnwrap(store.boards.first)

        XCTAssertEqual(board.id, "metolius.wood-grips-compact-ii")
        XCTAssertEqual(board.holds.count, 19)
        XCTAssertEqual(board.productURL.absoluteString, "https://www.metoliusclimbing.com/collections/training-boards/products/wood-grips-ii-training-boards")
        XCTAssertEqual(board.photoAssetName, "CompactBoardIllustration")
        XCTAssertEqual(board, BoardCatalog.compactII)
    }

    func testBoardLibraryRejectsDuplicateBoardIDs() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            boards.append(try XCTUnwrap(boards.first))
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains { $0.path == "boards[1].id" && $0.message.contains("Duplicate board ID") })
    }

    func testBoardLibraryRejectsDuplicateHoldIDs() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
            holds.append(try XCTUnwrap(holds.first))
            board["holds"] = holds
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains { $0.path == "boards[0].holds[1].id" && $0.message.contains("Duplicate hold ID") })
    }

    func testBoardLibraryRejectsOutOfRangeHoldFrames() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
            var hold = try XCTUnwrap(holds.first)
            var frame = try XCTUnwrap(hold["frame"] as? [String: Any])
            frame["x"] = -0.1
            hold["frame"] = frame
            holds[0] = hold
            board["holds"] = holds
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains { $0.path == "boards[0].holds[0].frame.x" && $0.message.contains("between 0 and 1") })
    }

    func testBoardLibraryRejectsNonPositiveAspectRatios() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            board["aspectRatio"] = 0
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains { $0.path == "boards[0].aspectRatio" && $0.message.contains("positive") })
    }

    func testBoardLibraryRejectsInvalidFingerCapacities() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
            var hold = try XCTUnwrap(holds.first)
            hold["fingerCapacity"] = 0
            holds[0] = hold
            board["holds"] = holds
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains { $0.path == "boards[0].holds[0].fingerCapacity" && $0.message.contains("1...4") })
    }

    func testBoardLibraryRejectsUnknownSemanticHoldIDs() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            var semanticHolds = try XCTUnwrap(board["semanticHolds"] as? [String: Any])
            semanticHolds["fixture-edge"] = ["holdIDs": ["missing.hold"]]
            board["semanticHolds"] = semanticHolds
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains { $0.path == "boards[0].semanticHolds.fixture-edge.holdIDs[0]" && $0.message.contains("Unknown hold ID") })
    }

    func testBoardLibraryDecodesKindOnlySemanticMappings() throws {
        let data = try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            board["semanticHolds"] = ["fixture-edge": ["kind": "edge"]]
            boards[0] = board
            document["boards"] = boards
        }

        let store = try BoardLibraryStore(data: data)
        let mapping = try XCTUnwrap(store.definition.boards.first?.semanticHolds["fixture-edge"])

        XCTAssertEqual(mapping.holdIDs, [])
        XCTAssertEqual(mapping.kind, .edge)
    }

    func testBoardLibraryRejectsSemanticMappingsWithBothIDsAndKinds() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            var semanticHolds = try XCTUnwrap(board["semanticHolds"] as? [String: Any])
            semanticHolds["fixture-edge"] = ["holdIDs": ["fixture.hold"], "kind": "edge"]
            board["semanticHolds"] = semanticHolds
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains { $0.path == "boards[0].semanticHolds.fixture-edge" && $0.message.contains("both hold IDs and a hold kind") })
    }

    private var compactFixture: Data {
        Data(
            #"""
            {
              "schemaVersion": 1,
              "metadata": {
                "id": "fixture.library",
                "version": "1.0.0",
                "title": "Fixture library",
                "generatedAt": "2026-08-10",
                "defaultBoardID": "fixture.board",
                "notes": []
              },
              "boards": [{
                "id": "fixture.board",
                "manufacturer": "Fixture Maker",
                "name": "Fixture Board",
                "subtitle": "A test board.",
                "dimensions": "10 × 5",
                "aspectRatio": 2,
                "holds": [{
                  "id": "fixture.hold",
                  "name": "Fixture edge",
                  "shortLabel": "F",
                  "detail": "A fixture edge.",
                  "kind": "edge",
                  "frame": { "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4 }
                }],
                "semanticHolds": {
                  "fixture-edge": { "holdIDs": ["fixture.hold"] }
                },
                "productURL": "https://example.com/fixture-board",
                "photoAssetName": null
              }]
            }
            """#.utf8
        )
    }

    private func fixtureData(
        mutating mutation: (inout [String: Any]) throws -> Void
    ) throws -> Data {
        var document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: compactFixture) as? [String: Any]
        )
        try mutation(&document)
        return try JSONSerialization.data(withJSONObject: document)
    }

    private func validationIssues(for data: Data) -> [BoardLibraryValidationIssue] {
        do {
            _ = try BoardLibraryStore(data: data)
            XCTFail("Expected board-library validation to fail.")
            return []
        } catch let BoardLibraryStoreError.validationFailed(issues) {
            return issues
        } catch {
            XCTFail("Expected a validation error, got: \(error)")
            return []
        }
    }

    private func writeTemporaryFixture(_ data: Data) throws -> URL {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("json")
        try data.write(to: url)
        return url
    }
}
