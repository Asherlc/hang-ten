import XCTest
@testable import HangTen

final class BoardPackageStoreTests: XCTestCase {

    func testStoreLoadsV2ModelAndRejectsLegacyV1AfterMigration() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true)
        defer { fixture.remove() }
        let legacyFixture = try legacyV1FixtureBundle()
        defer { legacyFixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.boards.first)
        let presentation = try XCTUnwrap(board.presentations.first)

        XCTAssertEqual(presentation.media.kind, .model)
        XCTAssertEqual(
            board.holds[0].resolvedFrame(in: presentation),
            HoldFrame(x: 0.1, y: 0.2, width: 0.3, height: 0.4)
        )
        XCTAssertEqual(
            store.presentationAssetURL(for: board),
            fixture.rootURL.appendingPathComponent("Hangboards/fixture-model/assets/primary.usdz")
        )
        XCTAssertEqual(
            store.presentationDescriptorURL(for: board),
            fixture.rootURL.appendingPathComponent("Hangboards/fixture-model/assets/primary.model.json")
        )
        XCTAssertThrowsError(try BoardPackageStore(bundle: legacyFixture.bundle))
    }

    func testModelPresentationContentUsesTypedMediaHoldInventory() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true)
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let content = BoardMapPresentationContent(
            board: board,
            selectedPresentationID: board.defaultPresentation.id
        )

        XCTAssertEqual(content.holds.map(\.id), ["hold-left"])
    }

    func testStoreAcceptsCanonicalTieToEvenDescriptorCenter() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(
                at: packageURL.appendingPathComponent("assets/primary.model.json")
            ) { descriptor in
                var holds = try XCTUnwrap(descriptor["holds"] as? [String: [String: Any]])
                var hold = try XCTUnwrap(holds["hold-left"])
                hold["facePlaneAABB"] = [
                    "min": [0.1, 0.2],
                    "max": [0.100000023, 0.6]
                ]
                hold["center"] = [0.100000011, 0.4]
                holds["hold-left"] = hold
                descriptor["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertNoThrow(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testDescriptorRoundingMatchesPythonAcrossDoublePrecisionTransition() {
        let transition = Double(1 << 22)
        let cases: [(value: Double, expected: Double)] = [
            (0.1000000115, 0.100000011),
            (transition.nextDown, transition),
            (transition.nextUp, transition.nextUp),
            (Double(1 << 23).nextUp, Double(1 << 23).nextUp),
            (1.0e20, 1.0e20),
            (1.0e300, 1.0e300),
            (Double.greatestFiniteMagnitude, Double.greatestFiniteMagnitude)
        ]

        for item in cases {
            XCTAssertEqual(
                boardDescriptorRoundedToNinePlaces(item.value),
                item.expected,
                "Python round(value, 9) parity failed for \(item.value)"
            )
        }
    }

    func testStoreHandlesFiniteScaleOverflowAndRejectsNonFiniteDescriptorValues() throws {
        let finite = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(
                at: packageURL.appendingPathComponent("assets/primary.model.json")
            ) { descriptor in
                descriptor["modelBounds"] = [
                    "min": [1.0e300, 0, 0],
                    "max": [1.000000000000001e300, 1, 0.1]
                ]
            }
        }
        defer { finite.remove() }
        XCTAssertNoThrow(try BoardPackageStore(bundle: finite.bundle))

        let nonFinite = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            let descriptorURL = packageURL.appendingPathComponent("assets/primary.model.json")
            try self.mutateJSONObject(at: descriptorURL) { descriptor in
                descriptor["modelBounds"] = [
                    "min": [0, 0, 0],
                    "max": [1.25, 1, 0.1]
                ]
            }
            let finiteJSON = try XCTUnwrap(
                String(data: Data(contentsOf: descriptorURL), encoding: .utf8)
            )
            let nonFiniteJSON = finiteJSON.replacingOccurrences(of: "1.25", with: "1e999")
            XCTAssertNotEqual(nonFiniteJSON, finiteJSON)
            try Data(nonFiniteJSON.utf8).write(to: descriptorURL)
        }
        defer { nonFinite.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: nonFinite.bundle))
    }

    func testStoreRejectsUnsortedDescriptorHoldMembers() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds.append(["id": "hold-right", "name": "Right hold", "kind": "jug"])
                board["holds"] = holds
            }
            let descriptorURL = packageURL.appendingPathComponent("assets/primary.model.json")
            try self.mutateJSONObject(at: descriptorURL) { descriptor in
                var nodes = try XCTUnwrap(descriptor["nodes"] as? [[String: Any]])
                nodes.append(["nodeID": "Right", "role": "hold", "holdID": "hold-right"])
                descriptor["nodes"] = nodes
                var holds = try XCTUnwrap(descriptor["holds"] as? [String: Any])
                holds["hold-right"] = [
                    "nodeIDs": ["Right"],
                    "facePlaneAABB": ["min": [0.6, 0.2], "max": [0.9, 0.6]],
                    "center": [0.75, 0.4]
                ]
                descriptor["holds"] = holds
            }
            try self.reverseDescriptorHoldMemberOrder(at: descriptorURL)
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreAcceptsDescriptorWithLeadingAndTrailingJSONWhitespace() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            let descriptorURL = packageURL.appendingPathComponent("assets/primary.model.json")
            let descriptor = try Data(contentsOf: descriptorURL)
            var padded = Data(" \n\t".utf8)
            padded.append(descriptor)
            padded.append(Data("\r\n ".utf8))
            try padded.write(to: descriptorURL)
        }
        defer { fixture.remove() }

        XCTAssertNoThrow(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testDescriptorMemberOrderScannerRejectsExcessiveNestingWithoutLosingEscapes() throws {
        var escaped = BoardPackageJSONMemberOrder(
            data: Data(#"{"ignored":"quote: \" and brace: }","holds":{"hold-a":{}}}"#.utf8)
        )
        XCTAssertEqual(try escaped.memberNames(inRootObjectNamed: "holds"), ["hold-a"])

        let excessiveDepth = BoardPackageJSONMemberOrder.maximumNestingDepth + 1
        let nestedValue = String(repeating: "[", count: excessiveDepth) + "0" +
            String(repeating: "]", count: excessiveDepth)
        var nested = BoardPackageJSONMemberOrder(
            data: Data("{\"ignored\":\(nestedValue),\"holds\":{}}".utf8)
        )

        XCTAssertThrowsError(try nested.memberNames(inRootObjectNamed: "holds"))
    }

    func testStoreLoadsV2RasterGeometryFromPresentationMedia() throws {
        let fixture = try makeRasterV2FixtureBundle()
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let presentation = try XCTUnwrap(board.presentations.first)

        XCTAssertEqual(presentation.media.kind, .raster)
        XCTAssertEqual(
            board.holds[0].resolvedFrame(in: presentation),
            HoldFrame(x: 0.1, y: 0.2, width: 0.55, height: 0.4)
        )
    }

    func testStoreRejectsDuplicateOriginalRasterOwnership() throws {
        let fixture = try makeMultiPresentationFixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[1]["media"] as? [String: Any])
            var holdGeometry = try XCTUnwrap(media["holdGeometry"] as? [String: Any])
            holdGeometry["hold-left"] = self.fixtureHoldGeometry()["hold-left"]
            media["holdGeometry"] = holdGeometry
            presentations[1]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly once")
    }

    func testStoreRejectsRasterHoldOwnedOnlyByDerivedPresentation() throws {
        let fixture = try makeDerivedRasterV2FixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
            media["holdGeometry"] = [:]
            presentations[0]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly once")
    }

    func testStoreRejectsDerivedRasterGeometryThatDiffersFromSource() throws {
        let fixture = try makeDerivedRasterV2FixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[1]["media"] as? [String: Any])
            var holdGeometry = try XCTUnwrap(
                media["holdGeometry"] as? [String: [[String: Any]]]
            )
            var pieces = try XCTUnwrap(holdGeometry["hold-left"])
            var frame = try XCTUnwrap(pieces[0]["frame"] as? [String: Any])
            frame["x"] = 0.2
            pieces[0]["frame"] = frame
            holdGeometry["hold-left"] = pieces
            media["holdGeometry"] = holdGeometry
            presentations[1]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly equal its source geometry")
    }

    func testStoreRejectsDerivedRasterGeometryWithDifferentPieceOrder() throws {
        let fixture = try makeDerivedRasterV2FixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[1]["media"] as? [String: Any])
            var holdGeometry = try XCTUnwrap(
                media["holdGeometry"] as? [String: [[String: Any]]]
            )
            holdGeometry["hold-left"]?.reverse()
            media["holdGeometry"] = holdGeometry
            presentations[1]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly equal its source geometry")
    }

    func testStoreRejectsDerivedRasterGeometryWithDifferentObjectMemberOrder() throws {
        let fixture = try makeDerivedRasterV2FixtureBundle()
        defer { fixture.remove() }
        let boardURL = fixture.rootURL.appendingPathComponent(
            "Hangboards/fixture-model/board.json"
        )
        let geometry = try JSONSerialization.data(
            withJSONObject: fixtureDerivedHoldGeometry(),
            options: [.sortedKeys]
        )
        var reordered = geometry
        let sortedFrame = Data(
            #"{"height":0.29999999999999999,"width":0.10000000000000001,"x":0.050000000000000003,"y":0.20000000000000001}"#.utf8
        )
        let reorderedFrame = Data(
            #"{"y":0.20000000000000001,"x":0.050000000000000003,"width":0.10000000000000001,"height":0.29999999999999999}"#.utf8
        )
        let frameRange = try XCTUnwrap(reordered.range(of: sortedFrame))
        reordered.replaceSubrange(frameRange, with: reorderedFrame)
        try replaceSecondOccurrence(of: geometry, with: reordered, in: boardURL)

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly equal its source geometry")
    }

    func testStoreRejectsDerivedRasterGeometryWithDifferentNumericScalarType() throws {
        let fixture = try makeDerivedRasterV2FixtureBundle()
        defer { fixture.remove() }
        let boardURL = fixture.rootURL.appendingPathComponent(
            "Hangboards/fixture-model/board.json"
        )
        let geometry = try JSONSerialization.data(
            withJSONObject: fixtureDerivedHoldGeometry(),
            options: [.sortedKeys]
        )
        let sourceGeometry = Data(
            String(decoding: geometry, as: UTF8.self)
                .replacingOccurrences(
                    of: #""cornerRadiusFraction":0.20000000000000001"#,
                    with: #""cornerRadiusFraction":0.0"#
                )
                .utf8
        )
        let derivedGeometry = Data(
            String(decoding: sourceGeometry, as: UTF8.self)
                .replacingOccurrences(of: #""cornerRadiusFraction":0.0"#, with: #""cornerRadiusFraction":0"#)
                .utf8
        )
        try replaceTwoOccurrences(
            of: geometry,
            firstReplacement: sourceGeometry,
            secondReplacement: derivedGeometry,
            in: boardURL
        )

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly equal its source geometry")
    }

    func testStoreRejectsStaleModelHashAndMissingDescriptor() throws {
        let stale = try makeModelFixtureBundle(modelSHA256Matches: false)
        defer { stale.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: stale.bundle))

        let missing = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try FileManager.default.removeItem(
                at: packageURL.appendingPathComponent("assets/primary.model.json")
            )
        }
        defer { missing.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: missing.bundle))
    }

    func testStoreRejectsDescriptorNodeAndHoldInventoryDrift() throws {
        let extraNode = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(
                at: packageURL.appendingPathComponent("assets/primary.model.json")
            ) { descriptor in
                var nodes = try XCTUnwrap(descriptor["nodes"] as? [[String: Any]])
                nodes.append(["nodeID": "Other", "role": "body"])
                descriptor["nodes"] = nodes
            }
        }
        defer { extraNode.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: extraNode.bundle))

        let missingHold = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(
                at: packageURL.appendingPathComponent("assets/primary.model.json")
            ) { descriptor in
                descriptor["holds"] = [:]
            }
        }
        defer { missingHold.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: missingHold.bundle))
    }

    func testStoreRejectsMalformedDescriptorVectorsRolesAndUnknownFields() throws {
        let mutations: [(String, (inout [String: Any]) throws -> Void)] = [
            ("fixed vector length", { descriptor in
                var bounds = try XCTUnwrap(descriptor["modelBounds"] as? [String: Any])
                bounds["min"] = [0, 0]
                descriptor["modelBounds"] = bounds
            }),
            ("duplicate node ID", { descriptor in
                var nodes = try XCTUnwrap(descriptor["nodes"] as? [[String: Any]])
                nodes[1]["nodeID"] = "Body"
                descriptor["nodes"] = nodes
            }),
            ("invalid role", { descriptor in
                var nodes = try XCTUnwrap(descriptor["nodes"] as? [[String: Any]])
                nodes[1] = ["nodeID": "Left", "role": "decoration"]
                descriptor["nodes"] = nodes
            }),
            ("unknown root field", { descriptor in
                descriptor["unexpected"] = true
            }),
        ]

        for (name, mutation) in mutations {
            let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
                try self.mutateJSONObject(
                    at: packageURL.appendingPathComponent("assets/primary.model.json"),
                    mutation: mutation
                )
            }
            defer { fixture.remove() }
            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), name)
        }
    }

    func testStoreRejectsInvalidModelCamera() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
                media["display"] = [
                    "camera": [
                        "type": "orthographic",
                        "viewDirection": [0, 0, 0],
                        "up": [0, 1, 0],
                        "fitPadding": 0.08
                    ]
                ]
                presentations[0]["media"] = media
                board["presentations"] = presentations
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreRejectsIncompleteV2RasterHoldOwnership() throws {
        let fixture = try makeRasterV2FixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
            media["holdGeometry"] = ["hold-left": []]
            presentations[0]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreRejectsUnknownMediaTagAndDerivedModel() throws {
        let unknown = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
                media["type"] = "video"
                presentations[0]["media"] = media
                board["presentations"] = presentations
            }
        }
        defer { unknown.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: unknown.bundle))

        let derived = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[0]["derivation"] = [
                    "type": "derived",
                    "sourcePresentationID": "primary",
                    "isInverted": true
                ]
                board["presentations"] = presentations
            }
        }
        defer { derived.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: derived.bundle))
    }

    func testStoreRejectsMixedModelAndRasterPackage() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            let assetsURL = packageURL.appendingPathComponent("assets")
            try self.presentationBytes().write(to: assetsURL.appendingPathComponent("fallback.png"))
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations.append([
                    "id": "fallback",
                    "name": "Fallback",
                    "aspectRatio": 2,
                    "isDefault": false,
                    "derivation": ["type": "original"],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/fallback.png",
                        "holdGeometry": [
                            "hold-left": [[
                                "frame": ["x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4],
                                "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.2]
                            ]]
                        ]
                    ]
                ])
                board["presentations"] = presentations
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreRejectsHoldWithUnknownEquipmentObject() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["equipmentObjects"] = [["id": "primary"]]
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["equipmentObjectID"] = "missing"
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "fixture.board",
                    reason: "hold hold-left references unknown equipment object missing"
                )
            )
        }
    }

    func testStoreDefaultsOmittedEquipmentObjectsToOnePrimaryObject() throws {
        let fixture = try makeFixtureBundle()
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(board.equipmentObjects.map(\.id), ["primary"])
        XCTAssertEqual(
            board.equipmentObjects.map(\.missingHandCapacityPolicy),
            [.legacyBilateral]
        )
        XCTAssertTrue(board.holds.allSatisfy { $0.equipmentObjectID == "primary" })
    }

    func testStoreLoadsStrictMissingHandCapacityPolicy() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["equipmentObjects"] = [[
                    "id": "primary",
                    "missingHandCapacityPolicy": "unavailable"
                ]]
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(
            board.equipmentObjects.first?.missingHandCapacityPolicy,
            .unavailable
        )
    }

    func testStoreRejectsExplicitNullEquipmentObjectFields() throws {
        let mutations: [(String, (inout [String: Any]) throws -> Void)] = [
            ("board objects", { board in
                board["equipmentObjects"] = NSNull()
            }),
            ("hold object", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["equipmentObjectID"] = NSNull()
                board["holds"] = holds
            }),
        ]

        for (name, mutation) in mutations {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json"),
                    mutation: mutation
                )
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), name) { error in
                XCTAssertEqual(
                    error as? BoardPackageStoreError,
                    .malformedJSON(resource: "Hangboards/fixture-model/board.json")
                )
            }
        }
    }

    func testStoreRejectsExplicitNullOptionalV2Metadata() throws {
        let mutations: [(String, (inout [String: Any]) throws -> Void)] = [
            ("dimensions", { board in
                board["dimensions"] = NSNull()
            }),
            ("sloper", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["kind"] = "sloper"
                holds[0]["sloper"] = NSNull()
                board["holds"] = holds
            }),
            ("size", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["sizeMillimeters"] = NSNull()
                board["holds"] = holds
            }),
            ("depth range", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["depthRangeMillimeters"] = NSNull()
                board["holds"] = holds
            }),
            ("grip type", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["gripType"] = NSNull()
                board["holds"] = holds
            }),
            ("finger capacity", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["fingerCapacity"] = NSNull()
                board["holds"] = holds
            }),
            ("hand capacity", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["handCapacity"] = NSNull()
                board["holds"] = holds
            }),
            ("features", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["features"] = NSNull()
                board["holds"] = holds
            }),
            ("equipment object ID", { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["equipmentObjectID"] = NSNull()
                board["holds"] = holds
            }),
        ]

        for (name, mutation) in mutations {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json"),
                    mutation: mutation
                )
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), name)
        }
    }

    func testStoreAcceptsOmittedOptionalV2Metadata() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board.removeValue(forKey: "dimensions")
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let hold = try XCTUnwrap(board.holds.first)
        XCTAssertNil(board.dimensions)
        XCTAssertNil(hold.sloper)
        XCTAssertNil(hold.sizeMillimeters)
        XCTAssertNil(hold.depthRangeMillimeters)
        XCTAssertNil(hold.gripType)
        XCTAssertNil(hold.fingerCapacity)
        XCTAssertNil(hold.handCapacity)
        XCTAssertNil(hold.features)
        XCTAssertEqual(hold.equipmentObjectID, "primary")
    }

    func testStoreRejectsUnknownKeysInEquipmentObjects() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["equipmentObjects"] = [["id": "primary", "unexpected": true]]
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

    func testStoreLoadsPackageWithOmittedDimensions() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board.removeValue(forKey: "dimensions")
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        XCTAssertNil(board.dimensions)
    }

    func testStoreRejectsExplicitlyEmptyDimensions() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["dimensions"] = ""
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "fixture.board",
                    reason: "dimensions must not be empty when present"
                )
            )
        }
    }

    func testStoreDecodesOptionalSloperMetadataVariants() throws {
        let variants: [(metadata: [String: Any]?, expected: SloperMetadata?)] = [
            (["type": "flat", "angleDegrees": 20], SloperMetadata(type: .flat, angleDegrees: 20)),
            (["type": "flat"], SloperMetadata(type: .flat, angleDegrees: nil)),
            (["type": "round"], SloperMetadata(type: .round, angleDegrees: nil)),
            (nil, nil),
        ]

        for variant in variants {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                    holds[0]["kind"] = "sloper"
                    if let metadata = variant.metadata {
                        holds[0]["sloper"] = metadata
                    }
                    board["holds"] = holds
                }
            }
            defer { fixture.remove() }

            let hold = try XCTUnwrap(
                BoardPackageStore(bundle: fixture.bundle).boards.first?.holds.first
            )
            XCTAssertEqual(hold.sloper, variant.expected)
        }
    }

    func testStoreRejectsInvalidSloperMetadataCombinations() throws {
        let invalidHolds: [(kind: String, metadata: [String: Any])] = [
            ("jug", ["type": "flat", "angleDegrees": 20]),
            ("sloper", ["type": "round", "angleDegrees": 20]),
            ("sloper", ["type": "flat", "angleDegrees": -0.01]),
            ("sloper", ["type": "flat", "angleDegrees": 90.01]),
            ("sloper", ["type": "domed"]),
            ("sloper", ["type": "flat", "unexpected": true]),
        ]

        for invalidHold in invalidHolds {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                    holds[0]["kind"] = invalidHold.kind
                    holds[0]["sloper"] = invalidHold.metadata
                    board["holds"] = holds
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
        }
    }

    func testStoreRejectsNonFiniteSloperAngle() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            let boardURL = hangboardsURL.appendingPathComponent("fixture-model/board.json")
            try self.mutateBoard(at: boardURL) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["kind"] = "sloper"
                holds[0]["sloper"] = ["type": "flat", "angleDegrees": 20]
                board["holds"] = holds
            }
            let finiteJSON = try XCTUnwrap(
                String(data: Data(contentsOf: boardURL), encoding: .utf8)
            )
            let nonFiniteJSON = finiteJSON.replacingOccurrences(
                of: "\"angleDegrees\":20",
                with: "\"angleDegrees\":1e999"
            )
            XCTAssertNotEqual(nonFiniteJSON, finiteJSON)
            try Data(nonFiniteJSON.utf8).write(to: boardURL)
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testBoardDetailHoldMapNumbersOnlyTheHoldsOnTheVisiblePresentation() {
        let board = TrainingBoard(
            id: "two-sided",
            manufacturer: "Example",
            name: "Two Sided",
            subtitle: "",
            dimensions: "10 in × 5 in",
            aspectRatio: 2,
            holds: [
                boardDetailHold(id: "front-a", presentationID: "front"),
                boardDetailHold(id: "back-a", presentationID: "back"),
                boardDetailHold(id: "front-b", presentationID: "front")
            ],
            productURL: URL(string: "https://example.com/two-sided")!,
            photoAssetName: nil,
            presentations: [
                boardDetailPresentation(id: "front", holdIDs: ["front-a", "front-b"], isDefault: true),
                boardDetailPresentation(id: "back", holdIDs: ["back-a"], isDefault: false)
            ]
        )

        let map = BoardDetailHoldMap(board: board, presentationID: "front")

        XCTAssertEqual(map.entries.map(\.hold.id), ["front-a", "front-b"])
        XCTAssertEqual(map.entries.map(\.number), [1, 2])
    }

    func testBoardDetailContentOrderPlacesSelectedHoldBeforeHoldLegend() {
        XCTAssertEqual(
            BoardDetailContentOrder.sections(hasSelectedHold: true),
            [.map, .selectedHold, .holdLegend]
        )
    }

    func testBoardHoldSpecificationsPresentOnlyDeclaredFacts() {
        let declaredHold = boardDetailHold(
            id: "declared",
            kind: .pocket,
            sizeMillimeters: 18,
            gripType: .openHand,
            fingerCapacity: 3,
            handCapacity: 1
        )
        let rangedHold = boardDetailHold(
            id: "ranged",
            kind: .edge,
            depthRangeMillimeters: 12.5...20
        )
        let unspecifiedHold = boardDetailHold(id: "unspecified", kind: .sloper)

        XCTAssertEqual(
            BoardHoldSpecifications.entries(for: declaredHold),
            [
                .init(label: "Kind", value: "Pocket"),
                .init(label: "Depth", value: "18 mm"),
                .init(label: "Grip", value: "Open hand"),
                .init(label: "Finger capacity", value: "3"),
                .init(label: "Hand capacity", value: "1")
            ]
        )
        XCTAssertEqual(
            BoardHoldSpecifications.entries(for: rangedHold),
            [
                .init(label: "Kind", value: "Edge"),
                .init(label: "Depth range", value: "12.5 mm–20 mm")
            ]
        )
        XCTAssertEqual(
            BoardHoldSpecifications.entries(for: unspecifiedHold),
            [.init(label: "Kind", value: "Sloper")]
        )
    }
    func testStoreRejectsInvertedFractionalDepthRange() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["depthRangeMillimeters"] = [
                    "lowerBound": 12.5,
                    "upperBound": 7.5,
                ]
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "fixture.board",
                    reason: "hold hold-left has an invalid depth range"
                )
            )
        }
    }

    func testStoreRejectsNonPositiveFractionalMillimeterMeasurements() throws {
        let invalidMeasurements: [(name: String, field: String, value: Any, reason: String)] = [
            ("zero size", "sizeMillimeters", 0.0, "hold hold-left has a non-positive size"),
            ("negative size", "sizeMillimeters", -7.5, "hold hold-left has a non-positive size"),
            (
                "zero depth",
                "depthRangeMillimeters",
                ["lowerBound": 0.0, "upperBound": 7.5],
                "hold hold-left has an invalid depth range"
            ),
            (
                "negative depth",
                "depthRangeMillimeters",
                ["lowerBound": -7.5, "upperBound": 7.5],
                "hold hold-left has an invalid depth range"
            ),
        ]

        for measurement in invalidMeasurements {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                    holds[0][measurement.field] = measurement.value
                    board["holds"] = holds
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), measurement.name) { error in
                XCTAssertEqual(
                    error as? BoardPackageStoreError,
                    .invalidPackage(boardID: "fixture.board", reason: measurement.reason)
                )
            }
        }
    }

    func testStoreRejectsNonFiniteMillimeterMeasurementJSON() throws {
        let invalidMeasurements: [
            (name: String, finiteValue: String, nonFiniteValue: String)
        ] = [
            (
                "size",
                "\"sizeMillimeters\":7.5",
                "\"sizeMillimeters\":1e999"
            ),
            (
                "depth lower bound",
                "\"lowerBound\":7.5",
                "\"lowerBound\":1e999"
            ),
            (
                "depth upper bound",
                "\"upperBound\":12.5",
                "\"upperBound\":1e999"
            ),
        ]

        for measurement in invalidMeasurements {
            let fixture = try makeFixtureBundle { hangboardsURL in
                let boardURL = hangboardsURL.appendingPathComponent("fixture-model/board.json")
                try self.mutateBoard(at: boardURL) { board in
                    var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                    holds[0]["sizeMillimeters"] = 7.5
                    holds[0]["depthRangeMillimeters"] = [
                        "lowerBound": 7.5,
                        "upperBound": 12.5,
                    ]
                    board["holds"] = holds
                }
                let finiteJSON = try XCTUnwrap(String(data: Data(contentsOf: boardURL), encoding: .utf8))
                let nonFiniteJSON = finiteJSON.replacingOccurrences(
                    of: measurement.finiteValue,
                    with: measurement.nonFiniteValue
                )
                XCTAssertNotEqual(nonFiniteJSON, finiteJSON)
                try Data(nonFiniteJSON.utf8).write(to: boardURL)
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), measurement.name) { error in
                XCTAssertEqual(
                    error as? BoardPackageStoreError,
                    .malformedJSON(resource: "Hangboards/fixture-model/board.json")
                )
            }
        }
    }

    func testStoreAcceptsFractionalFixedMillimeterMeasurement() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["sizeMillimeters"] = 7.5
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let hold = try XCTUnwrap(board.holds.first)
        XCTAssertEqual(hold.sizeMillimeters, 7.5)
        XCTAssertNil(hold.depthRangeMillimeters)
    }

    func testStoreRejectsHoldWithFixedAndVariableDepths() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["sizeMillimeters"] = 7.5
                holds[0]["depthRangeMillimeters"] = [
                    "lowerBound": 7.5,
                    "upperBound": 12.5,
                ]
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "fixture.board",
                    reason: "hold hold-left must not specify both a size and depth range"
                )
            )
        }
    }

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
        let presentation = try XCTUnwrap(board.presentations.first)
        guard case .raster(let raster) = presentation.media else {
            return XCTFail("Expected schema-v2 raster media")
        }
        let pieces = try XCTUnwrap(raster.holdGeometry[firstHold.id])
        XCTAssertEqual(pieces.count, 2)
        let expectedFrame = CGRect(x: 0.05, y: 0.1, width: 0.4, height: 0.4)
        let frame = try XCTUnwrap(firstHold.resolvedFrame(in: presentation))
        XCTAssertEqual(frame.rect.origin.x, expectedFrame.origin.x, accuracy: 1e-12)
        XCTAssertEqual(frame.rect.origin.y, expectedFrame.origin.y, accuracy: 1e-12)
        XCTAssertEqual(frame.rect.size.width, expectedFrame.size.width, accuracy: 1e-12)
        XCTAssertEqual(frame.rect.size.height, expectedFrame.size.height, accuracy: 1e-12)
        XCTAssertNil(firstHold.sizeMillimeters)
        XCTAssertNil(firstHold.depthRangeMillimeters)
        XCTAssertNil(firstHold.gripType)
        XCTAssertNil(firstHold.fingerCapacity)
        XCTAssertNil(firstHold.handCapacity)
        XCTAssertNil(firstHold.features)
        XCTAssertEqual(board.presentations.count, 1)
        XCTAssertEqual(presentation.id, "primary")
        XCTAssertEqual(presentation.name, "Primary")
        XCTAssertEqual(presentation.aspectRatio, 2)
        XCTAssertTrue(presentation.isDefault)
        XCTAssertEqual(raster.assetPath, "assets/primary.png")
        XCTAssertEqual(raster.holdGeometry["hold-left"]?.count, 2)
        XCTAssertEqual(store.semantics(for: board.id), [:])
        let imageURL = try XCTUnwrap(store.presentationImageURL(for: board))
        XCTAssertEqual(imageURL.lastPathComponent, "primary.png")
        XCTAssertEqual(try Data(contentsOf: imageURL), try presentationBytes())
    }

    func testStoreRejectsFormerPresentationField() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["presentation"] = ["assetPath": "assets/primary.png"]
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

    func testStoreRejectsMissingSchemaVersion() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board.removeValue(forKey: "schemaVersion")
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

    func testStoreRejectsNullRequiredPresentationID() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["presentationID"] = NSNull()
                board["holds"] = holds
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

    func testStoreLoadsPresentationAssetsAndScopedHolds() throws {
        let fixture = try makeMultiPresentationFixtureBundle()
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.boards.first)

        XCTAssertEqual(board.presentations.map(\.id), ["front", "back"])
        XCTAssertEqual(board.presentations.map(\.aspectRatio), [2, 1])
        XCTAssertEqual(board.defaultPresentation.id, "front")
        XCTAssertEqual(board.holds.map(\.id), ["hold-left", "hold-back"])
        XCTAssertEqual(board.presentations.map { $0.holdIDs }, [Set(["hold-left"]), Set(["hold-back"])])
        let frontURL = try XCTUnwrap(
            store.presentationImageURL(for: board, presentationID: "front")
        )
        let backURL = try XCTUnwrap(
            store.presentationImageURL(for: board, presentationID: "back")
        )
        XCTAssertEqual(frontURL.lastPathComponent, "primary.png")
        XCTAssertEqual(backURL.lastPathComponent, "back.png")
        XCTAssertEqual(try Data(contentsOf: backURL), try squarePresentationBytes())
    }

    func testStoreRejectsMalformedPresentationDocuments() throws {
        let mutations: [(inout [String: Any]) throws -> Void] = [
            { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[0].removeValue(forKey: "id")
                board["presentations"] = presentations
            },
            { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[1]["id"] = "front"
                board["presentations"] = presentations
            },
            { board in
                board["presentations"] = []
            },
            { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[0]["isDefault"] = false
                board["presentations"] = presentations
            },
            { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[1]["isDefault"] = true
                board["presentations"] = presentations
            },
            { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[0].removeValue(forKey: "derivation")
                board["presentations"] = presentations
            },
            { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
                media["type"] = "unknown"
                presentations[0]["media"] = media
                board["presentations"] = presentations
            }
        ]

        for mutation in mutations {
            let fixture = try makeMultiPresentationFixtureBundle(boardMutation: mutation)
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
        }
    }

    func testStoreRejectsDerivedPresentationChains() throws {
        let aliasChainFixture = try makeMultiPresentationFixtureBundle(
            boardMutation: { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations.append([
                    "id": "front-inverted",
                    "name": "Front upside down",
                    "aspectRatio": 2,
                    "isDefault": false,
                    "derivation": [
                        "type": "derived",
                        "sourcePresentationID": "front",
                        "isInverted": true
                    ],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/front-inverted.png",
                        "holdGeometry": self.fixtureHoldGeometry()
                    ]
                ])
                presentations.append([
                    "id": "front-inverted-twice",
                    "name": "Front twice inverted",
                    "aspectRatio": 2,
                    "isDefault": false,
                    "derivation": [
                        "type": "derived",
                        "sourcePresentationID": "front-inverted",
                        "isInverted": false
                    ],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/front-inverted-twice.png",
                        "holdGeometry": self.fixtureHoldGeometry()
                    ]
                ])
                board["presentations"] = presentations
            },
            mutateAssets: { assetsURL in
                let primary = try Data(contentsOf: assetsURL.appendingPathComponent("primary.png"))
                try primary.write(to: assetsURL.appendingPathComponent("front-inverted.png"))
                try primary.write(to: assetsURL.appendingPathComponent("front-inverted-twice.png"))
            }
        )
        defer { aliasChainFixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: aliasChainFixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(reason.contains("derived presentation relationships"), reason)
        }

    }

    func testStoreAcceptsCanonicalNestedAssetsWithEqualBasenames() throws {
        let fixture = try makeMultiPresentationFixtureBundle(
            boardMutation: { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                for (index, path) in ["assets/front/shared.png", "assets/rear/shared.png"].enumerated() {
                    var media = try XCTUnwrap(presentations[index]["media"] as? [String: Any])
                    media["assetPath"] = path
                    presentations[index]["media"] = media
                }
                board["presentations"] = presentations
            },
            mutateAssets: { assetsURL in
                let frontURL = assetsURL.appendingPathComponent("front/shared.png")
                let rearURL = assetsURL.appendingPathComponent("rear/shared.png")
                try FileManager.default.createDirectory(
                    at: frontURL.deletingLastPathComponent(),
                    withIntermediateDirectories: true
                )
                try FileManager.default.createDirectory(
                    at: rearURL.deletingLastPathComponent(),
                    withIntermediateDirectories: true
                )
                try self.presentationBytes().write(to: frontURL)
                try self.squarePresentationBytes().write(to: rearURL)
                try FileManager.default.removeItem(
                    at: assetsURL.appendingPathComponent("primary.png")
                )
                try FileManager.default.removeItem(
                    at: assetsURL.appendingPathComponent("back.png")
                )
            }
        )
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.boards.first)

        XCTAssertEqual(
            store.presentationImageURL(for: board, presentationID: "front").map {
                Array($0.pathComponents.suffix(3))
            },
            ["assets", "front", "shared.png"]
        )
        XCTAssertEqual(
            store.presentationImageURL(for: board, presentationID: "back").map {
                Array($0.pathComponents.suffix(3))
            },
            ["assets", "rear", "shared.png"]
        )
    }

    func testStoreRejectsMissingUndeclaredAndSymlinkedAssets() throws {
        let mutations: [((URL) throws -> Void)] = [
            { assetsURL in
                try FileManager.default.removeItem(at: assetsURL.appendingPathComponent("back.png"))
            },
            { assetsURL in
                try self.squarePresentationBytes().write(
                    to: assetsURL.appendingPathComponent("extra.png")
                )
            },
            { assetsURL in
                let backURL = assetsURL.appendingPathComponent("back.png")
                try FileManager.default.removeItem(at: backURL)
                try FileManager.default.createSymbolicLink(
                    at: backURL,
                    withDestinationURL: assetsURL.appendingPathComponent("primary.png")
                )
            }
        ]

        for mutateAssets in mutations {
            let fixture = try makeMultiPresentationFixtureBundle(mutateAssets: mutateAssets)
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
        }
    }

    func testStoreRejectsNoncanonicalInPackageAssetPaths() throws {
        for assetPath in [
            "assets//back.png",
            "assets/./back.png",
            "assets/rear/../back.png",
            "assets/back.jpg"
        ] {
            let fixture = try makeMultiPresentationFixtureBundle(boardMutation: { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                var media = try XCTUnwrap(presentations[1]["media"] as? [String: Any])
                media["assetPath"] = assetPath
                presentations[1]["media"] = media
                board["presentations"] = presentations
            })
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
                guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                    return XCTFail("Expected invalidPackage for \(assetPath), got \(error)")
                }
                XCTAssertEqual(
                    reason,
                    "typed presentation asset path is invalid"
                )
            }
        }
    }

    func testStoreAppliesAspectRatioToleranceAtPointOnePercentBoundary() throws {
        let accepted = try makeMultiPresentationFixtureBundle(boardMutation: { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            presentations[1]["aspectRatio"] = 1.001
            board["presentations"] = presentations
        })
        defer { accepted.remove() }
        XCTAssertNoThrow(try BoardPackageStore(bundle: accepted.bundle))

        let rejected = try makeMultiPresentationFixtureBundle(boardMutation: { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            presentations[1]["aspectRatio"] = 1.0010001
            board["presentations"] = presentations
        })
        defer { rejected.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: rejected.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertEqual(
                reason,
                "aspect ratio must match presentation image width/height within 0.1%"
            )
        }
    }

    func testStoreRejectsAssetEscapeMalformedPNGAndAspectMismatch() throws {
        let escaping = try makeMultiPresentationFixtureBundle(boardMutation: { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[1]["media"] as? [String: Any])
            media["assetPath"] = "../outside.png"
            presentations[1]["media"] = media
            board["presentations"] = presentations
        })
        defer { escaping.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: escaping.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .presentationAssetPathEscape(
                    boardID: "fixture.board",
                    path: "../outside.png"
                )
            )
        }

        let malformedPNG = try makeMultiPresentationFixtureBundle(
            mutateAssets: { assetsURL in
                try Data("not a png".utf8).write(to: assetsURL.appendingPathComponent("back.png"))
            }
        )
        defer { malformedPNG.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: malformedPNG.bundle))

        let aspectMismatch = try makeMultiPresentationFixtureBundle(boardMutation: { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            presentations[1]["aspectRatio"] = 2
            board["presentations"] = presentations
        })
        defer { aspectMismatch.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: aspectMismatch.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(reason.contains("aspect ratio must match"), reason)
        }
    }

    func testBoardMapPresentationSelectionUsesMatchingImageAndHoldPaths() throws {
        let fixture = try makeMultiPresentationFixtureBundle()
        defer { fixture.remove() }
        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.boards.first)

        let defaultContent = BoardMapPresentationContent(
            board: board,
            selectedPresentationID: nil
        )
        XCTAssertEqual(defaultContent.presentation.id, "front")
        XCTAssertEqual(defaultContent.holds.map(\.id), ["hold-left"])

        let backContent = BoardMapPresentationContent(
            board: board,
            selectedPresentationID: "back"
        )
        XCTAssertEqual(backContent.presentation.id, "back")
        XCTAssertEqual(backContent.holds.map(\.id), ["hold-back"])
        XCTAssertEqual(
            store.presentationImageURL(
                for: board,
                presentationID: backContent.presentation.id
            )?.lastPathComponent,
            "back.png"
        )
    }

    func testFlashBoardExposesUprightAndInvertedConfigurationsForBothFaces() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "tension.flash-board"))

        XCTAssertEqual(
            board.presentations.map(\.id),
            [
                "three-edge-upright",
                "three-edge-inverted",
                "two-edge-upright",
                "two-edge-inverted",
            ]
        )

        let expectedHoldIDsByConfiguration = [
            "three-edge-upright": [
                "three-edge-left",
                "three-edge-center",
                "three-edge-right",
            ],
            "three-edge-inverted": [
                "three-edge-left",
                "three-edge-center",
                "three-edge-right",
            ],
            "two-edge-upright": [
                "two-edge-left",
                "two-edge-right",
                "small-crimp-left",
                "small-crimp-right",
            ],
            "two-edge-inverted": [
                "two-edge-left",
                "two-edge-right",
                "small-crimp-left",
                "small-crimp-right",
            ],
        ]

        for (configurationID, expectedHoldIDs) in expectedHoldIDsByConfiguration {
            let content = BoardMapPresentationContent(
                board: board,
                selectedPresentationID: configurationID
            )
            XCTAssertEqual(content.presentation.id, configurationID)
            XCTAssertEqual(content.holds.map(\.id), expectedHoldIDs)
        }
    }

    func testBoardMapSelectionPrioritizesInitialHighlightedHoldOverRequestedSurface() throws {
        let fixture = try makeMultiPresentationFixtureBundle()
        defer { fixture.remove() }
        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        let selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: "front",
            activeHoldID: nil,
            highlightedHoldIDs: ["hold-back"]
        )

        XCTAssertEqual(selection.presentationID, "back")
    }

    func testBoardMapSelectionMovesToNewActiveHoldWhenAnotherSurfaceIsAlreadyHighlighted() throws {
        let fixture = try makeMultiPresentationFixtureBundle()
        defer { fixture.remove() }
        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        var selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: nil,
            activeHoldID: "hold-left",
            highlightedHoldIDs: ["hold-left"]
        )

        selection.updateHighlights(
            from: ["hold-left"],
            to: ["hold-left", "hold-back"],
            activeHoldID: "hold-back",
            on: board
        )

        XCTAssertEqual(selection.presentationID, "back")
    }

    func testBoardMapSelectionKeepsManuallySelectedSurfaceWhileAddingAndRemovingHolds() throws {
        let fixture = try makeMultiPresentationFixtureBundle()
        defer { fixture.remove() }
        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        var selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: nil,
            activeHoldID: "hold-left",
            highlightedHoldIDs: ["hold-left"]
        )

        selection.selectPresentation(id: "back", on: board)
        selection.updateHighlights(
            from: ["hold-left"],
            to: ["hold-left", "hold-back"],
            activeHoldID: "hold-back",
            on: board
        )
        XCTAssertEqual(selection.presentationID, "back")

        selection.updateHighlights(
            from: ["hold-left", "hold-back"],
            to: ["hold-left"],
            activeHoldID: "hold-back",
            on: board
        )
        XCTAssertEqual(selection.presentationID, "back")
    }

    func testBoardMapSelectionKeepsAnInvertedAliasForItsSourceHolds() {
        let board = TrainingBoard(
            id: "alias-fixture",
            manufacturer: "Example",
            name: "Alias fixture",
            subtitle: "",
            dimensions: "10 in × 5 in",
            aspectRatio: 2,
            holds: [
                boardDetailHold(id: "front-hold", presentationID: "front"),
                boardDetailHold(id: "back-hold", presentationID: "back")
            ],
            productURL: URL(string: "https://example.com/alias-fixture")!,
            photoAssetName: nil,
            presentations: [
                boardDetailPresentation(id: "front", holdIDs: ["front-hold"], isDefault: true),
                boardDetailPresentation(
                    id: "front-inverted",
                    holdIDs: ["front-hold"],
                    isDefault: false,
                    sourcePresentationID: "front",
                    isInverted: true
                ),
                boardDetailPresentation(id: "back", holdIDs: ["back-hold"], isDefault: false)
            ]
        )
        var selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: "front-inverted",
            activeHoldID: nil,
            highlightedHoldIDs: []
        )

        selection.activateHold(id: "front-hold", on: board)
        XCTAssertEqual(selection.presentationID, "front-inverted")

        selection.updateHighlights(
            from: [],
            to: ["front-hold"],
            activeHoldID: nil,
            on: board
        )
        XCTAssertEqual(selection.presentationID, "front-inverted")
    }

    func testBoardMapSelectionAppliesCallerPresentationChangeDespiteStaleActiveHold() throws {
        let fixture = try makeMultiPresentationFixtureBundle()
        defer { fixture.remove() }
        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        var selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: nil,
            activeHoldID: "hold-left",
            highlightedHoldIDs: ["hold-left"]
        )

        selection.updateRequestedPresentation(
            id: "back",
            activeHoldID: "hold-left",
            highlightedHoldIDs: ["hold-left"],
            on: board
        )

        XCTAssertEqual(selection.presentationID, "back")
    }

    func testStorePreservesOptionalHandCapacityAndRejectsInvalidValues() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["handCapacity"] = 2
                board["holds"] = holds
            }
        }
        defer { fixture.remove() }

        let hold = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first?.holds.first)
        XCTAssertEqual(hold.handCapacity, 2)

        let invalidFixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["handCapacity"] = 3
                board["holds"] = holds
            }
        }
        defer { invalidFixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: invalidFixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "fixture.board",
                    reason: "hold hold-left has an invalid hand capacity"
                )
            )
        }
    }

    func testStoreAcceptsShapeConstraintWithoutChangingRuntimeBoardShape() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                try self.mutateRasterGeometry(in: &board) { geometry in
                geometry[0]["shapeConstraint"] = [
                    "shape": "oval",
                    "rotationDegrees": 15
                ]
                }
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .raster(let media) = board.defaultPresentation.media else {
            return XCTFail("Expected raster media")
        }
        let firstPiece = try XCTUnwrap(media.holdGeometry["hold-left"]?.first)

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
                    try self.mutateRasterGeometry(in: &board) { geometry in
                    geometry[0]["shapeConstraint"] = constraint
                    }
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
                try self.mutateRasterGeometry(in: &board) { geometry in
                geometry[0]["shapeConstraint"] = [
                    "shape": "pill",
                    "rotationDegrees": 0
                ]
                }
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

    /// Swift's discovery sort must agree with the Workbench's directory
    /// discovery order on the same shared non-ASCII fixture cases, so the
    /// two independent sort implementations can't silently diverge.
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

    func testStoreRejectsFormerPresentationPathField() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["presentation"] = ["assetPath": "assets/alternate.png"]
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

    func testStoreRejectsFormerPresentationPathEscape() throws {
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
                .malformedJSON(resource: "Hangboards/fixture-model/board.json")
            )
        }
    }

    func testStoreRejectsPathWithMatchingControlPointsButNotContourUseDeclaredFrame() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                try self.mutateRasterGeometry(in: &board) { geometry in
                geometry[0]["shape"] = [
                    "type": "path",
                    "commands": [
                        ["command": "move", "to": [0.25, 0.25]],
                        ["command": "curve", "to": [0.75, 0.25], "control1": [0.0, 0.0], "control2": [1.0, 0.0]],
                        ["command": "curve", "to": [0.25, 0.75], "control1": [1.0, 1.0], "control2": [0.0, 1.0]],
                        ["command": "close"]
                    ]
                ]
                }
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

    func testStoreAcceptsBendableCurveMetadataWithoutChangingHoldGeometry() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                try self.mutateRasterGeometry(in: &board) { geometry in
                geometry[0]["shape"] = [
                    "type": "path",
                    "commands": [
                        ["command": "move", "to": [0, 0]],
                        ["command": "curve", "control1": [0, 0], "control2": [1, 0], "to": [1, 1], "bendable": true],
                        ["command": "line", "to": [0, 1]],
                        ["command": "close"]
                    ]
                ]
                }
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .raster(let media) = board.defaultPresentation.media else {
            return XCTFail("Expected raster media")
        }
        let geometry = try XCTUnwrap(media.holdGeometry["hold-left"])
        XCTAssertEqual(geometry.count, 2)
        XCTAssertEqual(geometry[0].frame, CGRect(x: 0.05, y: 0.2, width: 0.1, height: 0.3))
    }

    func testBendableCurveMetadataDoesNotChangeEncodedRuntimeDocument() throws {
        let document = try JSONDecoder().decode(
            BoardGeometryPathCommandDocument.self,
            from: Data(
                """
                {"command":"curve","control1":[0,0],"control2":[1,0],"to":[1,1],"bendable":true}
                """.utf8
            )
        )

        let encoded = try JSONEncoder().encode(document)
        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )

        XCTAssertEqual(object["command"] as? String, "curve")
        XCTAssertEqual(object["to"] as? [Double], [1, 1])
        XCTAssertEqual(object["control1"] as? [Double], [0, 0])
        XCTAssertEqual(object["control2"] as? [Double], [1, 0])
        XCTAssertNil(object["bendable"])
    }

    func testStoreRejectsBendableMetadataOnLineCommand() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                try self.mutateRasterGeometry(in: &board) { geometry in
                geometry[0]["shape"] = [
                    "type": "path",
                    "commands": [
                        ["command": "move", "to": [0, 0]],
                        ["command": "line", "to": [1, 0], "bendable": true],
                        ["command": "line", "to": [1, 1]],
                        ["command": "line", "to": [0, 1]],
                        ["command": "close"]
                    ]
                ]
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

    func testStoreRejectsPathWhoseRenderedCurveEscapesDeclaredFrame() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                try self.mutateRasterGeometry(in: &board) { geometry in
                geometry[0]["shape"] = [
                    "type": "path",
                    "commands": [
                        ["command": "move", "to": [0, 0]],
                        ["command": "line", "to": [1, 0]],
                        ["command": "line", "to": [1, 1]],
                        ["command": "quad", "control": [-16, 2], "to": [0, 1]],
                        ["command": "close"]
                    ]
                ]
                }
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

    func testStoreRejectsEmptyGeometry() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(at: hangboardsURL.appendingPathComponent("fixture-model/board.json")) { board in
                try self.mutateRasterGeometry(in: &board) { geometry in
                    geometry = []
                }
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreAcceptsOffCanvasFiniteHoldGeometry() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(at: hangboardsURL.appendingPathComponent("fixture-model/board.json")) {
                try self.mutateRasterGeometry(in: &$0) { geometry in
                var frame = try XCTUnwrap(geometry[0]["frame"] as? [String: Any])
                frame["x"] = -0.1
                frame["y"] = 0.9
                frame["width"] = 1.2
                frame["height"] = 0.3
                geometry[0]["frame"] = frame
                }
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .raster(let media) = board.defaultPresentation.media else {
            return XCTFail("Expected raster media")
        }
        let frame = try XCTUnwrap(media.holdGeometry["hold-left"]?.first?.frame)
        XCTAssertEqual(frame.origin.x, -0.1, accuracy: 1e-12)
        XCTAssertEqual(frame.origin.y, 0.9, accuracy: 1e-12)
        XCTAssertEqual(frame.width, 1.2, accuracy: 1e-12)
        XCTAssertEqual(frame.height, 0.3, accuracy: 1e-12)
    }

    func testStoreAcceptsExactlySupportedPhysicalHoldKinds() throws {
        let expectedKinds = ["jug", "edge", "pocket", "pinch", "sloper", "gaston"]
        XCTAssertEqual(HoldKind.allCases.map(\.rawValue), expectedKinds)
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                let template = try XCTUnwrap(
                    (board["holds"] as? [[String: Any]])?.first
                )
                let supportedHolds: [[String: Any]] = expectedKinds.compactMap { kind in
                    if kind == "gaston" {
                        return nil
                    }
                    var hold = template
                    hold["id"] = "hold-\(kind)"
                    hold["name"] = "Fixture \(kind)"
                    hold["kind"] = kind
                    return hold
                }
                board["holds"] = supportedHolds
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                var left = template
                left["id"] = "gaston-left"
                left["name"] = "Left gaston"
                left["kind"] = "gaston"
                left["pairedHoldID"] = "gaston-right"
                var right = template
                right["id"] = "gaston-right"
                right["name"] = "Right gaston"
                right["kind"] = "gaston"
                right["pairedHoldID"] = "gaston-left"
                holds.append(contentsOf: [left, right])
                board["holds"] = holds
                try self.replaceRasterHoldGeometry(
                    in: &board,
                    holdIDs: holds.compactMap { $0["id"] as? String }
                )
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(
            board.holds.map { $0.kind.rawValue },
            ["jug", "edge", "pocket", "pinch", "sloper", "gaston", "gaston"]
        )
    }

    func testStoreAcceptsReciprocalGastonPairs() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                let template = try XCTUnwrap((board["holds"] as? [[String: Any]])?.first)
                var left = template
                left["id"] = "gaston-left"
                left["name"] = "Left gaston"
                left["kind"] = "gaston"
                left["pairedHoldID"] = "gaston-right"
                var right = template
                right["id"] = "gaston-right"
                right["name"] = "Right gaston"
                right["kind"] = "gaston"
                right["pairedHoldID"] = "gaston-left"
                board["holds"] = [left, right]
                try self.replaceRasterHoldGeometry(
                    in: &board,
                    holdIDs: ["gaston-left", "gaston-right"]
                )
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(board.holds.map(\.kind), [.gaston, .gaston])
        XCTAssertEqual(board.holds.map(\.pairedHoldID), ["gaston-right", "gaston-left"])
    }

    func testStoreRejectsInvalidGastonPairMetadata() throws {
        let invalidPairs: [(String, (inout [[String: Any]]) -> Void)] = [
            ("missing pair", { holds in
                holds[0]["kind"] = "gaston"
            }),
            ("invalid pair identifier", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedHoldID"] = "not a valid identifier"
            }),
            ("pair on another kind", { holds in
                holds[0]["pairedHoldID"] = "gaston-right"
            }),
            ("explicit null pair on another kind", { holds in
                holds[0]["pairedHoldID"] = NSNull()
            }),
            ("self pair", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedHoldID"] = "gaston-left"
            }),
            ("unknown pair", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedHoldID"] = "missing"
            }),
            ("non-gaston target", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedHoldID"] = "gaston-right"
            }),
            ("non-reciprocal target", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedHoldID"] = "gaston-right"
                holds[1]["kind"] = "gaston"
                holds[1]["pairedHoldID"] = "another-gaston"
            }),
        ]

        for (_, mutation) in invalidPairs {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    let template = try XCTUnwrap((board["holds"] as? [[String: Any]])?.first)
                    var left = template
                    left["id"] = "gaston-left"
                    left["name"] = "Left gaston"
                    var right = template
                    right["id"] = "gaston-right"
                    right["name"] = "Right gaston"
                    var holds = [left, right]
                    mutation(&holds)
                    board["holds"] = holds
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
        }
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
                    try self.mutateRasterGeometry(in: &$0) { geometry in
                    geometry[0]["shape"] = ["type": "path", "commands": commands]
                    }
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

    func testStoreAcceptsSharedSelfCrossingPathShapes() throws {
        let validationFixtures = try validationFixtures()
        let shapes = try XCTUnwrap(
            validationFixtures["selfCrossingPathShapes"] as? [[String: Any]]
        )
        for shape in shapes {
            let name = try XCTUnwrap(shape["name"] as? String)
            let commands = try XCTUnwrap(shape["commands"] as? [[String: Any]])
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) {
                    try self.mutateRasterGeometry(in: &$0) { geometry in
                    geometry[0]["shape"] = ["type": "path", "commands": commands]
                    }
                }
            }
            defer { fixture.remove() }

            XCTAssertNoThrow(try BoardPackageStore(bundle: fixture.bundle), name)
        }
    }

    func testStoreRejectsContourWithMoreThan1024FlattenedSegments() throws {
        var commands: [[String: Any]] = [
            ["command": "move", "to": [0, 0]]
        ]
        for index in 1...1025 {
            commands.append([
                "command": "line",
                "to": index.isMultiple(of: 2) ? [0, 0] : [1, 0]
            ])
        }
        commands.append(["command": "close"])

        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) {
                try self.mutateRasterGeometry(in: &$0) { geometry in
                geometry[0]["shape"] = ["type": "path", "commands": commands]
                }
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(
                reason.contains("must contain no more than 1024 flattened segments"),
                reason
            )
        }
    }

    func testStoreRejectsExcessiveCurvesBeforeAWorkIntensiveSuffix() throws {
        var commands: [[String: Any]] = [
            ["command": "move", "to": [0, 0]]
        ]
        commands.append(contentsOf: Array(
            repeating: [
                "command": "curve",
                "control1": [0, 0],
                "control2": [1, 1],
                "to": [0, 0]
            ],
            count: 33
        ))
        commands.append(["command": "line", "to": [0]])
        commands.append(["command": "close"])

        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) {
                try self.mutateRasterGeometry(in: &$0) { geometry in
                geometry[0]["shape"] = ["type": "path", "commands": commands]
                }
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(
                reason.contains("must contain no more than 1024 flattened segments"),
                reason
            )
        }
    }

    func testStoreRejectsMaximumSizeExactlyRetracedContourQuickly() throws {
        let vertexCount = 256
        let step = vertexCount / 2 - 1
        var order: [Int] = []
        var visited: Set<Int> = []
        var index = 0
        while !visited.contains(index) {
            visited.insert(index)
            order.append(index)
            index = (index + step) % vertexCount
        }
        let vertices = order.map { index in
            let angle = 2 * Double.pi * Double(index) / Double(vertexCount)
            return [0.5 + 0.4 * cos(angle), 0.5 + 0.4 * sin(angle)]
        }
        var commands: [[String: Any]] = [
            ["command": "move", "to": vertices[0]]
        ]
        commands.append(contentsOf: vertices.dropFirst().map {
            ["command": "line", "to": $0]
        })
        commands.append(contentsOf: vertices.dropLast().reversed().map {
            ["command": "line", "to": $0]
        })
        commands.append(["command": "close"])

        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) {
                try self.mutateRasterGeometry(in: &$0) { geometry in
                geometry[0]["shape"] = ["type": "path", "commands": commands]
                }
            }
        }
        defer { fixture.remove() }

        let started = ContinuousClock.now
        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(reason.contains("must enclose area"), reason)
        }
        XCTAssertLessThan(started.duration(to: .now), .seconds(1))
    }

    /// A Bezier control point only needs to be finite, but flattening it
    /// still quantizes into an Int64 (`QuantizedBoardPoint`) by scaling by
    /// 1e12, which traps for values outside Int64's range. An oversized
    /// finite control must fail validation instead of crashing the app.
    func testStoreRejectsControlPointsTooLargeToQuantize() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) {
                try self.mutateRasterGeometry(in: &$0) { geometry in
                geometry[0]["shape"] = [
                    "type": "path",
                    "commands": [
                        ["command": "move", "to": [0, 0]],
                        ["command": "line", "to": [1, 0]],
                        ["command": "curve", "control1": [100_000_000, 0.5], "control2": [0.5, 0.5], "to": [1, 1]],
                        ["command": "line", "to": [0, 1]],
                        ["command": "close"]
                    ]
                ]
                }
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(reason.contains("too large to represent"), reason)
        }
    }

    func testStoreRejectsUnknownKeysAtBoardHoldAndGeometryRoots() throws {
        for location in ["board", "hold", "geometry"] {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(at: hangboardsURL.appendingPathComponent("fixture-model/board.json")) { board in
                    if location == "board" {
                        board["unexpected"] = true
                    } else if location == "hold" {
                        var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                        holds[0]["unexpected"] = true
                        board["holds"] = holds
                    } else {
                        try self.mutateRasterGeometry(in: &board) { geometry in
                            geometry[0]["unexpected"] = true
                        }
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

    func testStoreDecodesPositionsAndDirectedTransitions() throws {
        let positionFixtures = try XCTUnwrap(
            try validationFixtures()["boardPositions"] as? [String: Any]
        )
        let positions = try XCTUnwrap(positionFixtures["positions"] as? [[String: Any]])
        let positionTransitions = try XCTUnwrap(
            positionFixtures["positionTransitions"] as? [[String: Any]]
        )
        let fixture = try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            try self.presentationBytes().write(
                to: packageURL.appendingPathComponent("assets/front-inverted.png")
            )
            try self.mutateBoard(at: packageURL.appendingPathComponent("board.json")) { board in
                board["presentations"] = [
                    [
                        "id": "primary", "name": "Primary", "aspectRatio": 2,
                        "isDefault": true, "derivation": ["type": "original"],
                        "media": [
                            "type": "raster", "assetPath": "assets/primary.png",
                            "holdGeometry": self.fixtureHoldGeometry()
                        ],
                    ],
                    [
                        "id": "front-inverted", "name": "Front inverted",
                        "aspectRatio": 2, "isDefault": false,
                        "derivation": [
                            "type": "derived", "sourcePresentationID": "primary",
                            "isInverted": true
                        ],
                        "media": [
                            "type": "raster", "assetPath": "assets/front-inverted.png",
                            "holdGeometry": self.fixtureHoldGeometry()
                        ],
                    ],
                ]
                board["positions"] = positions
                board["positionTransitions"] = positionTransitions
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(board.positions.map(\.id), ["front", "flipped"])
        XCTAssertEqual(board.holdIDs(inPosition: "front"), ["hold-left"])
        XCTAssertEqual(board.holdIDs(inPosition: "flipped"), ["hold-left"])
        XCTAssertEqual(board.transitionKind(from: "front", to: "front"), .same)
        XCTAssertEqual(board.transitionKind(from: "front", to: "flipped"), .seamless)
        XCTAssertEqual(board.transitionKind(from: "flipped", to: "front"), .setupRequired)
    }

    func testStoreRejectsInvalidPositionsAndTransitions() throws {
        let mutations: [(String, (inout [String: Any]) -> Void)] = [
            ("duplicate position ID", { board in
                var positions = board["positions"] as! [[String: Any]]
                positions.append(["id": "front", "presentationID": "primary"])
                board["positions"] = positions
            }),
            ("unknown position presentation", { board in
                var positions = board["positions"] as! [[String: Any]]
                positions[0]["presentationID"] = "missing"
                board["positions"] = positions
            }),
            ("duplicate transition", { board in
                var transitions = board["positionTransitions"] as! [[String: Any]]
                transitions.append(transitions[0])
                board["positionTransitions"] = transitions
            }),
            ("unknown transition source", { board in
                var transitions = board["positionTransitions"] as! [[String: Any]]
                transitions[0]["fromPositionID"] = "missing"
                board["positionTransitions"] = transitions
            }),
            ("unknown transition destination", { board in
                var transitions = board["positionTransitions"] as! [[String: Any]]
                transitions[0]["toPositionID"] = "missing"
                board["positionTransitions"] = transitions
            }),
            ("self transition", { board in
                var transitions = board["positionTransitions"] as! [[String: Any]]
                transitions[0]["toPositionID"] = "front"
                board["positionTransitions"] = transitions
            }),
            ("unsupported transition kind", { board in
                var transitions = board["positionTransitions"] as! [[String: Any]]
                transitions[0]["kind"] = "invented"
                board["positionTransitions"] = transitions
            }),
            ("unknown position key", { board in
                var positions = board["positions"] as! [[String: Any]]
                positions[0]["unexpected"] = true
                board["positions"] = positions
            }),
            ("unknown transition key", { board in
                var transitions = board["positionTransitions"] as! [[String: Any]]
                transitions[0]["unexpected"] = true
                board["positionTransitions"] = transitions
            }),
        ]

        for (name, mutation) in mutations {
            let fixture = try positionFixtureBundle(boardMutation: mutation)
            defer { fixture.remove() }
            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), name)
        }

        for field in ["positions", "positionTransitions"] {
            let fixture = try positionFixtureBundle { board in board[field] = NSNull() }
            defer { fixture.remove() }
            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), field)
        }

        let fixture = try positionFixtureBundle { board in
            board["presentations"] = [
                [
                    "id": "primary", "name": "Primary", "aspectRatio": 2,
                    "isDefault": true, "derivation": ["type": "original"],
                    "media": [
                        "type": "raster", "assetPath": "assets/primary.png",
                        "holdGeometry": self.fixtureHoldGeometry()
                    ],
                ],
                [
                    "id": "unused", "name": "Unused", "aspectRatio": 2,
                    "isDefault": false, "derivation": ["type": "original"],
                    "media": [
                        "type": "raster", "assetPath": "assets/unused.png",
                        "holdGeometry": [:]
                    ],
                ],
            ]
            board["positions"] = [["id": "unused", "presentationID": "unused"]]
            board.removeValue(forKey: "positionTransitions")
        }
        defer { fixture.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    private func positionFixtureBundle(
        boardMutation: @escaping (inout [String: Any]) -> Void
    ) throws -> FixtureBundle {
        try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let assetsURL = packageURL.appendingPathComponent("assets")
            try self.presentationBytes().write(to: assetsURL.appendingPathComponent("front-inverted.png"))
            try self.presentationBytes().write(to: assetsURL.appendingPathComponent("unused.png"))
            try self.mutateBoard(at: packageURL.appendingPathComponent("board.json")) { board in
                board["presentations"] = [
                    [
                        "id": "primary", "name": "Primary", "aspectRatio": 2,
                        "isDefault": true, "derivation": ["type": "original"],
                        "media": [
                            "type": "raster", "assetPath": "assets/primary.png",
                            "holdGeometry": self.fixtureHoldGeometry()
                        ],
                    ],
                    [
                        "id": "front-inverted", "name": "Front inverted",
                        "aspectRatio": 2, "isDefault": false,
                        "derivation": [
                            "type": "derived", "sourcePresentationID": "primary",
                            "isInverted": true
                        ],
                        "media": [
                            "type": "raster", "assetPath": "assets/front-inverted.png",
                            "holdGeometry": self.fixtureHoldGeometry()
                        ],
                    ],
                ]
                board["positions"] = [
                    ["id": "front", "presentationID": "primary"],
                    ["id": "flipped", "presentationID": "front-inverted"],
                ]
                board["positionTransitions"] = [
                    ["fromPositionID": "front", "toPositionID": "flipped", "kind": "seamless"],
                ]
                boardMutation(&board)
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

    private func squarePresentationBytes() throws -> Data {
        try XCTUnwrap(
            Data(
                base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            )
        )
    }

    private func makeMultiPresentationFixtureBundle(
        boardMutation: ((inout [String: Any]) throws -> Void)? = nil,
        mutateAssets: ((URL) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let assetsURL = packageURL.appendingPathComponent("assets")
            try self.squarePresentationBytes().write(to: assetsURL.appendingPathComponent("back.png"))
            try self.mutateBoard(at: packageURL.appendingPathComponent("board.json")) { board in
                let existingPresentations = try XCTUnwrap(
                    board["presentations"] as? [[String: Any]]
                )
                let primaryMedia = try XCTUnwrap(
                    existingPresentations[0]["media"] as? [String: Any]
                )
                let geometry = try XCTUnwrap(
                    primaryMedia["holdGeometry"] as? [String: [[String: Any]]]
                )
                let pieces = try XCTUnwrap(geometry["hold-left"])
                board["presentations"] = [[
                    "id": "front",
                    "name": "Front",
                    "aspectRatio": 2,
                    "isDefault": true,
                    "derivation": ["type": "original"],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/primary.png",
                        "holdGeometry": ["hold-left": pieces]
                    ]
                ], [
                    "id": "back",
                    "name": "Back",
                    "aspectRatio": 1,
                    "isDefault": false,
                    "derivation": ["type": "original"],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/back.png",
                        "holdGeometry": ["hold-back": pieces]
                    ]
                ]]
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                var backHold = holds[0]
                backHold["id"] = "hold-back"
                backHold["name"] = "Back hold"
                holds.append(backHold)
                board["holds"] = holds
                try boardMutation?(&board)
            }
            try mutateAssets?(assetsURL)
        }
    }

    private func makeDerivedRasterV2FixtureBundle(
        boardMutation: ((inout [String: Any]) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let assetsURL = packageURL.appendingPathComponent("assets")
            try self.presentationBytes().write(
                to: assetsURL.appendingPathComponent("inverted.png")
            )
            try self.mutateBoard(at: packageURL.appendingPathComponent("board.json")) { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                var originalMedia = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
                originalMedia["holdGeometry"] = self.fixtureDerivedHoldGeometry()
                presentations[0]["media"] = originalMedia
                presentations.append([
                    "id": "inverted",
                    "name": "Inverted",
                    "aspectRatio": 2,
                    "isDefault": false,
                    "derivation": [
                        "type": "derived",
                        "sourcePresentationID": "primary",
                        "isInverted": true,
                    ],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/inverted.png",
                        "holdGeometry": self.fixtureDerivedHoldGeometry(),
                    ],
                ])
                board["presentations"] = presentations
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                var rightHold = try XCTUnwrap(holds.first)
                rightHold["id"] = "hold-right"
                rightHold["name"] = "Right hold"
                holds.append(rightHold)
                board["holds"] = holds
                try boardMutation?(&board)
            }
        }
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

    private func legacyV1FixtureBundle() throws -> FixtureBundle {
        try makeFixtureBundle { hangboardsURL in
            try self.legacyBoardData(for: PackageSpec(slug: "fixture-model", id: "fixture.board"))
                .write(to: hangboardsURL.appendingPathComponent("fixture-model/board.json"))
        }
    }

    private func makeModelFixtureBundle(
        modelSHA256Matches: Bool,
        mutatePackage: ((URL) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        let fixtures = try validationFixtures()
        let model = try XCTUnwrap(fixtures["model"] as? [String: Any])
        let board = try XCTUnwrap(model["board"] as? [String: Any])
        var descriptor = try XCTUnwrap(model["descriptor"] as? [String: Any])
        if !modelSHA256Matches {
            descriptor["modelSHA256"] = String(repeating: "0", count: 64)
        }
        let modelBase64 = try XCTUnwrap(model["assetBase64"] as? String)
        let modelBytes = try XCTUnwrap(Data(base64Encoded: modelBase64))

        return try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let assetsURL = packageURL.appendingPathComponent("assets")
            try FileManager.default.removeItem(at: assetsURL.appendingPathComponent("primary.png"))
            try JSONSerialization.data(withJSONObject: board, options: [.sortedKeys])
                .write(to: packageURL.appendingPathComponent("board.json"))
            try modelBytes.write(to: assetsURL.appendingPathComponent("primary.usdz"))
            try JSONSerialization.data(withJSONObject: descriptor, options: [.sortedKeys])
                .write(to: assetsURL.appendingPathComponent("primary.model.json"))
            try mutatePackage?(packageURL)
        }
    }

    private func makeRasterV2FixtureBundle(
        mutateBoard: ((inout [String: Any]) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        let fixtures = try validationFixtures()
        let model = try XCTUnwrap(fixtures["model"] as? [String: Any])
        var board = try XCTUnwrap(model["board"] as? [String: Any])
        var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
        presentations[0]["media"] = [
            "type": "raster",
            "assetPath": "assets/primary.png",
            "holdGeometry": [
                "hold-left": [[
                    "frame": ["x": 0.1, "y": 0.2, "width": 0.2, "height": 0.4],
                    "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.2]
                ], [
                    "frame": ["x": 0.45, "y": 0.3, "width": 0.2, "height": 0.2],
                    "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.2]
                ]]
            ]
        ]
        board["presentations"] = presentations
        try mutateBoard?(&board)
        return try makeFixtureBundle { hangboardsURL in
            let boardURL = hangboardsURL.appendingPathComponent("fixture-model/board.json")
            try JSONSerialization.data(withJSONObject: board, options: [.sortedKeys]).write(to: boardURL)
        }
    }

    private func mutateJSONObject(
        at url: URL,
        mutation: (inout [String: Any]) throws -> Void
    ) throws {
        var object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any]
        )
        try mutation(&object)
        try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys]).write(to: url)
    }

    private func reverseDescriptorHoldMemberOrder(at url: URL) throws {
        let data = try Data(contentsOf: url)
        let descriptor = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
        let holds = try XCTUnwrap(descriptor["holds"] as? [String: Any])
        let sortedHolds = try JSONSerialization.data(withJSONObject: holds, options: [.sortedKeys])
        let right = try XCTUnwrap(holds["hold-right"])
        let left = try XCTUnwrap(holds["hold-left"])
        let rightData = try JSONSerialization.data(withJSONObject: right, options: [.sortedKeys])
        let leftData = try JSONSerialization.data(withJSONObject: left, options: [.sortedKeys])
        var unsortedHolds = Data("{\"hold-right\":".utf8)
        unsortedHolds.append(rightData)
        unsortedHolds.append(Data(",\"hold-left\":".utf8))
        unsortedHolds.append(leftData)
        unsortedHolds.append(Data("}".utf8))
        var unsortedDescriptor = data
        let range = try XCTUnwrap(unsortedDescriptor.range(of: sortedHolds))
        unsortedDescriptor.replaceSubrange(range, with: unsortedHolds)
        try unsortedDescriptor.write(to: url)
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
                "schemaVersion": 2,
                "id": package.id,
                "manufacturer": package.manufacturer,
                "name": package.name,
                "subtitle": "A physical fixture board.",
                "productURL": "https://example.com/\(package.id)",
                "dimensions": "20 × 10 cm",
                "aspectRatio": 2,
                "presentations": [[
                    "id": "primary",
                    "name": "Primary",
                    "aspectRatio": 2,
                    "isDefault": true,
                    "derivation": ["type": "original"],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/primary.png",
                        "holdGeometry": [
                            "hold-left": [[
                                "frame": ["x": 0.05, "y": 0.2, "width": 0.1, "height": 0.3],
                                "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.2]
                            ], [
                                "frame": ["x": 0.35, "y": 0.1, "width": 0.1, "height": 0.2],
                                "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.1],
                                "treatment": ["type": "surface"]
                            ]]
                        ]
                    ]
                ]],
                "holds": [[
                    "id": "hold-left",
                    "name": "Left hold",
                    "kind": "jug"
                ]]
            ],
            options: [.sortedKeys]
        )
    }

    private func legacyBoardData(for package: PackageSpec) throws -> Data {
        try JSONSerialization.data(
            withJSONObject: [
                "id": package.id,
                "manufacturer": package.manufacturer,
                "name": package.name,
                "subtitle": "A physical fixture board.",
                "productURL": "https://example.com/\(package.id)",
                "dimensions": "20 × 10 cm",
                "aspectRatio": 2,
                "presentations": [[
                    "id": "primary",
                    "name": "Primary",
                    "assetPath": "assets/primary.png",
                    "aspectRatio": 2,
                    "default": true
                ]],
                "holds": [[
                    "id": "hold-left",
                    "name": "Left hold",
                    "kind": "jug",
                    "presentationID": "primary",
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

    private func mutateRasterGeometry(
        in board: inout [String: Any],
        presentationIndex: Int = 0,
        holdID: String = "hold-left",
        mutation: (inout [[String: Any]]) throws -> Void
    ) throws {
        var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
        var media = try XCTUnwrap(presentations[presentationIndex]["media"] as? [String: Any])
        var holdGeometry = try XCTUnwrap(media["holdGeometry"] as? [String: [[String: Any]]])
        var geometry = try XCTUnwrap(holdGeometry[holdID])
        try mutation(&geometry)
        holdGeometry[holdID] = geometry
        media["holdGeometry"] = holdGeometry
        presentations[presentationIndex]["media"] = media
        board["presentations"] = presentations
    }

    private func replaceRasterHoldGeometry(
        in board: inout [String: Any],
        presentationIndex: Int = 0,
        holdIDs: [String]
    ) throws {
        var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
        var media = try XCTUnwrap(presentations[presentationIndex]["media"] as? [String: Any])
        let holdGeometry = try XCTUnwrap(media["holdGeometry"] as? [String: [[String: Any]]])
        let pieces = try XCTUnwrap(holdGeometry.values.first)
        media["holdGeometry"] = Dictionary(
            uniqueKeysWithValues: holdIDs.map { ($0, pieces) }
        )
        presentations[presentationIndex]["media"] = media
        board["presentations"] = presentations
    }

    private func fixtureHoldGeometry() -> [String: [[String: Any]]] {
        [
            "hold-left": [[
                "frame": ["x": 0.05, "y": 0.2, "width": 0.1, "height": 0.3],
                "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.2]
            ], [
                "frame": ["x": 0.35, "y": 0.1, "width": 0.1, "height": 0.2],
                "shape": ["type": "roundedRect", "cornerRadiusFraction": 0.1],
                "treatment": ["type": "surface"]
            ]]
        ]
    }

    private func fixtureDerivedHoldGeometry() -> [String: [[String: Any]]] {
        var geometry = fixtureHoldGeometry()
        geometry["hold-right"] = geometry["hold-left"]
        return geometry
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

    private func replaceSecondOccurrence(
        of original: Data,
        with replacement: Data,
        in url: URL
    ) throws {
        var data = try Data(contentsOf: url)
        let firstRange = try XCTUnwrap(data.range(of: original))
        let searchStart = firstRange.upperBound
        let secondRange = try XCTUnwrap(
            data.range(of: original, in: searchStart..<data.endIndex)
        )
        data.replaceSubrange(secondRange, with: replacement)
        try data.write(to: url)
    }

    private func replaceTwoOccurrences(
        of original: Data,
        firstReplacement: Data,
        secondReplacement: Data,
        in url: URL
    ) throws {
        var data = try Data(contentsOf: url)
        let firstRange = try XCTUnwrap(data.range(of: original))
        data.replaceSubrange(firstRange, with: firstReplacement)
        let searchStart = firstRange.lowerBound + firstReplacement.count
        let secondRange = try XCTUnwrap(
            data.range(of: original, in: searchStart..<data.endIndex)
        )
        data.replaceSubrange(secondRange, with: secondReplacement)
        try data.write(to: url)
    }

    private func assertStoreRejects(_ bundle: Bundle, reasonContaining expected: String) {
        XCTAssertThrowsError(try BoardPackageStore(bundle: bundle)) { error in
            guard case let BoardPackageStoreError.invalidPackage(_, reason) = error else {
                return XCTFail("Unexpected error: \(error)")
            }
            XCTAssertTrue(reason.contains(expected), "Unexpected reason: \(reason)")
        }
    }

    private func boardDetailHold(
        id: String,
        kind: HoldKind = .jug,
        sizeMillimeters: Double? = nil,
        gripType: GripType? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        depthRangeMillimeters: ClosedRange<Double>? = nil,
        presentationID _: String = BoardPresentation.primaryID
    ) -> BoardHold {
        BoardHold(
            id: id,
            name: id,
            kind: kind,
            sizeMillimeters: sizeMillimeters,
            gripType: gripType,
            fingerCapacity: fingerCapacity,
            handCapacity: handCapacity,
            depthRangeMillimeters: depthRangeMillimeters
        )
    }

    private func boardDetailPresentation(
        id: String,
        holdIDs: [String],
        isDefault: Bool,
        sourcePresentationID: String? = nil,
        isInverted: Bool = false
    ) -> BoardPresentation {
        let geometry = Dictionary(uniqueKeysWithValues: holdIDs.map { holdID in
            (
                holdID,
                [BoardHoldPiece(
                    id: "\(holdID)-piece",
                    holdID: holdID,
                    frame: CGRect(x: 0.1, y: 0.1, width: 0.2, height: 0.2),
                    shape: .roundedRect(cornerRadiusFraction: 0),
                    treatment: .surface
                )]
            )
        })
        return BoardPresentation(
            id: id,
            name: id,
            aspectRatio: 2,
            isDefault: isDefault,
            sourcePresentationID: sourcePresentationID,
            isInverted: isInverted,
            media: .raster(BoardRasterMedia(assetPath: "", holdGeometry: geometry))
        )
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
