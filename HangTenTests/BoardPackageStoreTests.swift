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
        XCTAssertEqual(firstHold.presentationID, "primary")
        XCTAssertEqual(
            board.presentations,
            [
                BoardPresentation(
                    id: "primary",
                    name: "Primary",
                    aspectRatio: 2,
                    isDefault: true
                )
            ]
        )
        XCTAssertEqual(store.semantics(for: board.id), [:])
        let imageURL = try XCTUnwrap(store.presentationImageURL(for: board))
        XCTAssertEqual(imageURL.lastPathComponent, "primary.png")
        XCTAssertEqual(try Data(contentsOf: imageURL), try presentationBytes())
    }

    func testStoreSynthesizesPrimaryPresentationWhenSchemaV1PresentationIsOmitted() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board.removeValue(forKey: "presentation")
            }
        }
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.boards.first)

        XCTAssertEqual(board.defaultPresentation.id, "primary")
        XCTAssertEqual(board.defaultPresentation.aspectRatio, 2)
        XCTAssertEqual(board.holds.map(\.presentationID), ["primary"])
        XCTAssertEqual(store.presentationImageURL(for: board)?.lastPathComponent, "primary.png")
    }

    func testStoreRejectsNullSchemaV1PresentationWhenKeyIsPresent() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["presentation"] = NSNull()
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

    func testStoreRejectsSchemaV1PresentationIDKeyEvenWhenValueIsNull() throws {
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
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("Expected invalidPackage, got \(error)")
            }
            XCTAssertEqual(reason, "schema version 1 holds cannot declare presentationID")
        }
    }

    func testStoreLoadsSchemaV2PresentationAssetsAndScopedHolds() throws {
        let fixture = try makeSchemaV2FixtureBundle()
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.boards.first)

        XCTAssertEqual(board.presentations.map(\.id), ["front", "back"])
        XCTAssertEqual(board.presentations.map(\.aspectRatio), [2, 1])
        XCTAssertEqual(board.defaultPresentation.id, "front")
        XCTAssertEqual(board.holds.map(\.id), ["hold-left", "hold-back"])
        XCTAssertEqual(board.holds.map(\.presentationID), ["front", "back"])
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

    func testStoreRejectsMalformedSchemaV2PresentationDocuments() throws {
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
                presentations[0]["default"] = false
                board["presentations"] = presentations
            },
            { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[1]["default"] = true
                board["presentations"] = presentations
            },
            { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0].removeValue(forKey: "presentationID")
                board["holds"] = holds
            },
            { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["presentationID"] = "unknown"
                board["holds"] = holds
            }
        ]

        for mutation in mutations {
            let fixture = try makeSchemaV2FixtureBundle(boardMutation: mutation)
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
        }
    }

    func testStoreAcceptsCanonicalNestedSchemaV2AssetsWithEqualBasenames() throws {
        let fixture = try makeSchemaV2FixtureBundle(
            boardMutation: { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[0]["assetPath"] = "assets/front/shared.png"
                presentations[1]["assetPath"] = "assets/rear/shared.png"
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

    func testStoreRejectsMissingUndeclaredAndSymlinkedSchemaV2Assets() throws {
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
            let fixture = try makeSchemaV2FixtureBundle(mutateAssets: mutateAssets)
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
        }
    }

    func testStoreRejectsNoncanonicalInPackageSchemaV2AssetPaths() throws {
        for assetPath in [
            "assets//back.png",
            "assets/./back.png",
            "assets/rear/../back.png",
            "assets/back.jpg"
        ] {
            let fixture = try makeSchemaV2FixtureBundle(boardMutation: { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations[1]["assetPath"] = assetPath
                board["presentations"] = presentations
            })
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
                guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                    return XCTFail("Expected invalidPackage for \(assetPath), got \(error)")
                }
                XCTAssertEqual(
                    reason,
                    "presentation asset path must name a PNG beneath assets"
                )
            }
        }
    }

    func testStoreAppliesSchemaV2AspectRatioToleranceAtPointOnePercentBoundary() throws {
        let accepted = try makeSchemaV2FixtureBundle(boardMutation: { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            presentations[1]["aspectRatio"] = 1.001
            board["presentations"] = presentations
        })
        defer { accepted.remove() }
        XCTAssertNoThrow(try BoardPackageStore(bundle: accepted.bundle))

        let rejected = try makeSchemaV2FixtureBundle(boardMutation: { board in
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

    func testStoreRejectsSchemaV2AssetEscapeMalformedPNGAndAspectMismatch() throws {
        let escaping = try makeSchemaV2FixtureBundle(boardMutation: { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            presentations[1]["assetPath"] = "../outside.png"
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

        let malformedPNG = try makeSchemaV2FixtureBundle(
            mutateAssets: { assetsURL in
                try Data("not a png".utf8).write(to: assetsURL.appendingPathComponent("back.png"))
            }
        )
        defer { malformedPNG.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: malformedPNG.bundle))

        let aspectMismatch = try makeSchemaV2FixtureBundle(boardMutation: { board in
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
        let fixture = try makeSchemaV2FixtureBundle()
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

    func testBoardMapSelectionPrioritizesInitialHighlightedHoldOverRequestedSurface() throws {
        let fixture = try makeSchemaV2FixtureBundle()
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
        let fixture = try makeSchemaV2FixtureBundle()
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
        let fixture = try makeSchemaV2FixtureBundle()
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

    func testBoardMapSelectionAppliesCallerPresentationChangeDespiteStaleActiveHold() throws {
        let fixture = try makeSchemaV2FixtureBundle()
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

    func testStoreRejectsPathWhoseRenderedCurveEscapesDeclaredFrame() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
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

    func testStoreRejectsEmptyGeometry() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(at: hangboardsURL.appendingPathComponent("fixture-model/board.json")) {
                var holds = try XCTUnwrap($0["holds"] as? [[String: Any]])
                holds[0]["geometry"] = []
                $0["holds"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreAcceptsOffCanvasFiniteHoldGeometry() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(at: hangboardsURL.appendingPathComponent("fixture-model/board.json")) {
                var holds = try XCTUnwrap($0["holds"] as? [[String: Any]])
                var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
                var frame = try XCTUnwrap(geometry[0]["frame"] as? [String: Any])
                frame["x"] = -0.1
                frame["y"] = 0.9
                frame["width"] = 1.2
                frame["height"] = 0.3
                geometry[0]["frame"] = frame
                holds[0]["geometry"] = geometry
                $0["holds"] = holds
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let frame = try XCTUnwrap(board.holds.first?.geometry.first?.frame)
        XCTAssertEqual(frame.origin.x, -0.1, accuracy: 1e-12)
        XCTAssertEqual(frame.origin.y, 0.9, accuracy: 1e-12)
        XCTAssertEqual(frame.width, 1.2, accuracy: 1e-12)
        XCTAssertEqual(frame.height, 0.3, accuracy: 1e-12)
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

    /// A Bezier control point only needs to be finite, but flattening it
    /// still quantizes into an Int64 (`QuantizedBoardPoint`) by scaling by
    /// 1e12, which traps for values outside Int64's range. An oversized
    /// finite control must fail validation instead of crashing the app.
    func testStoreRejectsControlPointsTooLargeToQuantize() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) {
                var holds = try XCTUnwrap($0["holds"] as? [[String: Any]])
                var geometry = try XCTUnwrap(holds[0]["geometry"] as? [[String: Any]])
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
                holds[0]["geometry"] = geometry
                $0["holds"] = holds
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

    private func squarePresentationBytes() throws -> Data {
        try XCTUnwrap(
            Data(
                base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            )
        )
    }

    private func makeSchemaV2FixtureBundle(
        boardMutation: ((inout [String: Any]) throws -> Void)? = nil,
        mutateAssets: ((URL) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let assetsURL = packageURL.appendingPathComponent("assets")
            try self.squarePresentationBytes().write(to: assetsURL.appendingPathComponent("back.png"))
            try self.mutateBoard(at: packageURL.appendingPathComponent("board.json")) { board in
                board["schemaVersion"] = 2
                board.removeValue(forKey: "presentation")
                board["presentations"] = [[
                    "id": "front",
                    "name": "Front",
                    "assetPath": "assets/primary.png",
                    "aspectRatio": 2,
                    "default": true
                ], [
                    "id": "back",
                    "name": "Back",
                    "assetPath": "assets/back.png",
                    "aspectRatio": 1,
                    "default": false
                ]]
                var holds = try XCTUnwrap(board["holds"] as? [[String: Any]])
                holds[0]["presentationID"] = "front"
                var backHold = holds[0]
                backHold["id"] = "hold-back"
                backHold["name"] = "Back hold"
                backHold["presentationID"] = "back"
                holds.append(backHold)
                board["holds"] = holds
                try boardMutation?(&board)
            }
            try mutateAssets?(assetsURL)
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
