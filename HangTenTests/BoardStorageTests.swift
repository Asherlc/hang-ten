import XCTest
@testable import HangTen

final class BoardStorageTests: XCTestCase {
    func testFrameOnlyBoardHoldCreatesRectangleGeometryAndDerivesBounds() throws {
        let suppliedFrame = HoldFrame(x: 0.2, y: 0.3, width: 0.4, height: 0.2)
        let hold = BoardHold(
            id: "legacy-frame-hold",
            name: "Legacy frame hold",
            shortLabel: "Legacy",
            detail: "Fixture",
            kind: .edge,
            frame: suppliedFrame
        )

        let piece = try XCTUnwrap(hold.geometry.first)
        XCTAssertEqual(hold.geometry.count, 1)
        XCTAssertEqual(piece.holdID, hold.id)
        XCTAssertEqual(piece.frame, suppliedFrame.rect)
        XCTAssertEqual(hold.frame.rect, suppliedFrame.rect)

        let path = piece.path(in: CGRect(x: 0, y: 0, width: 100, height: 100))
        XCTAssertTrue(path.contains(CGPoint(x: 40, y: 40)))
        XCTAssertFalse(path.contains(CGPoint(x: 10, y: 40)))
    }

    func testBoardLibraryPreservesUnknownPhysicalMetadataAndDerivesHoldFrameFromGeometry() throws {
        let store = try BoardLibraryStore(data: compactFixture)
        let board = try XCTUnwrap(store.boards.first)
        let hold = try XCTUnwrap(board.holds.first)

        XCTAssertEqual(board.id, "fixture.board")
        XCTAssertEqual(board.manufacturer, "Fixture Maker")
        XCTAssertEqual(hold.id, "fixture.hold")
        XCTAssertEqual(hold.geometry.count, 2)
        let expectedFrame = CGRect(x: 0.1, y: 0.2, width: 0.7, height: 0.4)
        XCTAssertEqual(hold.frame.rect.origin.x, expectedFrame.origin.x, accuracy: 1e-12)
        XCTAssertEqual(hold.frame.rect.origin.y, expectedFrame.origin.y, accuracy: 1e-12)
        XCTAssertEqual(hold.frame.rect.size.width, expectedFrame.size.width, accuracy: 1e-12)
        XCTAssertEqual(hold.frame.rect.size.height, expectedFrame.size.height, accuracy: 1e-12)
        XCTAssertNil(hold.sizeMillimeters)
        XCTAssertNil(hold.depthRangeMillimeters)
        XCTAssertNil(hold.gripType)
        XCTAssertNil(hold.fingerCapacity)
        XCTAssertNil(hold.features)
    }

    func testBoardLibraryLoadsAndExportsDeterministicSortedJSON() throws {
        let fixtureURL = try writeTemporaryFixture(compactFixture)
        defer { try? FileManager.default.removeItem(at: fixtureURL) }

        let store = try BoardLibraryStore(contentsOf: fixtureURL)
        let firstCompactExport = try store.encodedData(prettyPrinted: false)
        let secondCompactExport = try store.encodedData(prettyPrinted: false)
        let firstPrettyExport = try store.encodedData(prettyPrinted: true)
        let secondPrettyExport = try store.encodedData(prettyPrinted: true)

        XCTAssertEqual(firstCompactExport, secondCompactExport)
        XCTAssertEqual(firstPrettyExport, secondPrettyExport)
        XCTAssertEqual(firstCompactExport.first, UInt8(ascii: "{"))
        XCTAssertFalse(String(decoding: firstCompactExport, as: UTF8.self).contains("\n"))
        XCTAssertTrue(String(decoding: firstPrettyExport, as: UTF8.self).contains("\n"))

        for export in [firstCompactExport, firstPrettyExport] {
            let json = String(decoding: export, as: UTF8.self)
            let boards = try XCTUnwrap(json.range(of: "\"boards\""))
            let metadata = try XCTUnwrap(json.range(of: "\"metadata\""))
            let schemaVersion = try XCTUnwrap(json.range(of: "\"schemaVersion\""))

            XCTAssertLessThan(boards.lowerBound, metadata.lowerBound)
            XCTAssertLessThan(metadata.lowerBound, schemaVersion.lowerBound)
        }

        XCTAssertEqual(try BoardLibraryStore(data: firstCompactExport).boards, store.boards)
        XCTAssertEqual(try BoardLibraryStore(data: firstPrettyExport).boards, store.boards)
    }

    func testBoardLibraryStoreDistinguishesUnreadableURLs() {
        let unreadableURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("json")

        XCTAssertThrowsError(try BoardLibraryStore(contentsOf: unreadableURL)) { error in
            guard case BoardLibraryStoreError.reading = error else {
                return XCTFail("Expected a reading error, got: \(error)")
            }
        }
    }

    func testBoardLibraryStoreDistinguishesMalformedReadableJSON() throws {
        let malformedURL = try writeTemporaryFixture(Data("{ malformed".utf8))
        defer { try? FileManager.default.removeItem(at: malformedURL) }

        XCTAssertThrowsError(try BoardLibraryStore(contentsOf: malformedURL)) { error in
            guard case BoardLibraryStoreError.decoding = error else {
                return XCTFail("Expected a decoding error, got: \(error)")
            }
        }
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

    func testBoardLibraryRejectsOutOfRangeHoldGeometry() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
            var hold = try XCTUnwrap(holds.first)
            var geometry = try XCTUnwrap(hold["geometry"] as? [[String: Any]])
            var piece = try XCTUnwrap(geometry.first)
            var frame = try XCTUnwrap(piece["frame"] as? [String: Any])
            frame["x"] = -0.1
            piece["frame"] = frame
            geometry[0] = piece
            hold["geometry"] = geometry
            holds[0] = hold
            board["holds"] = holds
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains {
            $0.path == "boards[0].holds[0].geometry[0].frame.x" &&
                $0.message.contains("between 0 and 1")
        })
    }

    func testBoardLibraryRejectsEmptyHoldGeometry() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
            holds[0]["geometry"] = []
            board["holds"] = holds
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains {
            $0.path == "boards[0].holds[0].geometry" &&
                $0.message.contains("at least one piece")
        })
    }

    func testDirectHoldConversionRejectsEmptyGeometryByThrowing() throws {
        let definition = try JSONDecoder().decode(
            BoardHoldDefinition.self,
            from: Data(#"{"id":"fixture.empty","name":"Empty","kind":"edge","geometry":[]}"#.utf8)
        )

        XCTAssertThrowsError(try definition.trainingBoardHold()) { error in
            XCTAssertEqual(
                String(describing: error),
                "hold fixture.empty geometry must include at least one piece"
            )
        }
    }

    func testBoardHoldDefinitionRejectsGeometryAndLegacyFrameTogether() throws {
        let data = Data(
            #"{"id":"fixture.ambiguous","name":"Ambiguous","kind":"edge","frame":{"x":0.1,"y":0.1,"width":0.2,"height":0.2},"geometry":[{"frame":{"x":0.1,"y":0.1,"width":0.2,"height":0.2},"shape":{"type":"roundedRect","cornerRadiusFraction":0.1}}]}"#.utf8
        )

        XCTAssertThrowsError(try JSONDecoder().decode(BoardHoldDefinition.self, from: data))
    }

    func testDirectHoldConversionRejectsInvalidFingerCapacityByThrowing() throws {
        let data = Data(
            #"{"id":"fixture.capacity","name":"Capacity","kind":"edge","fingerCapacity":0,"frame":{"x":0.1,"y":0.1,"width":0.2,"height":0.2}}"#.utf8
        )
        let definition = try JSONDecoder().decode(BoardHoldDefinition.self, from: data)

        XCTAssertThrowsError(try definition.trainingBoardHold()) { error in
            XCTAssertEqual(
                String(describing: error),
                "hold fixture.capacity has an invalid finger capacity"
            )
        }
    }

    func testBoardLibraryAcceptsEveryPhysicalHoldKindDuringDecoding() throws {
        let expectedKinds = ["jug", "edge", "pocket", "pinch", "sloper"]
        XCTAssertEqual(HoldKind.allCases.map(\.rawValue), expectedKinds)
        let data = try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            let template = try XCTUnwrap(
                (board["holds"] as? [[String: Any]])?.first
            )
            board["holds"] = expectedKinds.map { kind in
                var hold = template
                hold["id"] = "fixture.\(kind)"
                hold["name"] = "Fixture \(kind)"
                hold["kind"] = kind
                return hold
            }
            board["semanticHolds"] = [
                "fixture-edge": ["holdIDs": ["fixture.edge"]]
            ]
            boards[0] = board
            document["boards"] = boards
        }

        let board = try XCTUnwrap(BoardLibraryStore(data: data).boards.first)

        XCTAssertEqual(board.holds.map(\.kind.rawValue), expectedKinds)
    }

    func testBoardLibraryRejectsUnsupportedPhysicalHoldKindsDuringDecoding() throws {
        let data = try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
            holds[0]["kind"] = "unsupported"
            board["holds"] = holds
            boards[0] = board
            document["boards"] = boards
        }

        XCTAssertThrowsError(try BoardLibraryStore(data: data)) { error in
            guard case BoardLibraryStoreError.decoding = error else {
                return XCTFail("Expected a decoding error, got: \(error)")
            }
        }
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
        let definitionMapping = try XCTUnwrap(store.definition.boards.first?.semanticHolds["fixture-edge"])
        let runtimeMapping = try XCTUnwrap(store.boards.first?.semanticHolds["fixture-edge"])

        XCTAssertEqual(definitionMapping, SemanticHoldMappingDefinition(kind: .edge))
        XCTAssertEqual(runtimeMapping, SemanticHoldMappingDefinition(kind: .edge))
    }

    func testBoardLibraryRejectsEmptySemanticMappings() throws {
        let issues = validationIssues(for: try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            board["semanticHolds"] = ["fixture-edge": [:]]
            boards[0] = board
            document["boards"] = boards
        })

        XCTAssertTrue(issues.contains {
            $0.path == "boards[0].semanticHolds.fixture-edge" &&
                $0.message.contains("needs hold IDs or a hold kind")
        })
    }

    func testBoardLibraryRejectsUnsupportedSemanticKindsDuringDecoding() throws {
        let data = try fixtureData { document in
            var boards = try XCTUnwrap(document["boards"] as? [[String: Any]])
            var board = try XCTUnwrap(boards.first)
            board["semanticHolds"] = ["fixture-edge": ["kind": "unsupported"]]
            boards[0] = board
            document["boards"] = boards
        }

        XCTAssertThrowsError(try BoardLibraryStore(data: data)) { error in
            guard case BoardLibraryStoreError.decoding = error else {
                return XCTFail("Expected a decoding error, got: \(error)")
            }
        }
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
                  "kind": "edge",
                  "geometry": [
                    {
                      "frame": { "x": 0.1, "y": 0.2, "width": 0.2, "height": 0.4 },
                      "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.1 }
                    },
                    {
                      "frame": { "x": 0.6, "y": 0.3, "width": 0.2, "height": 0.2 },
                      "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.1 }
                    }
                  ]
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
