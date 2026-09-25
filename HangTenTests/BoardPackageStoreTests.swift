import SceneKit
import XCTest
@testable import HangTen

private func XCTAssertMalformedJSON(
    _ error: Error,
    resource: String,
    file: StaticString = #file,
    line: UInt = #line
) {
    guard case .malformedJSON(let r, _) = error as? BoardPackageStoreError, r == resource else {
        return XCTFail("Expected .malformedJSON(resource: \(resource)), got \(error)", file: file, line: line)
    }
}

final class BoardPackageStoreTests: XCTestCase {

    func testReusableModelMediaDecodesTwoInstances() throws {
        let board = try reusableFixtureBoard(named: "reusable-valid")
        guard case .model(let media) = board.defaultPresentation.media else {
            return XCTFail("fixture must decode model media")
        }
        XCTAssertEqual(media.instances?.count, 2)
        XCTAssertEqual(media.instances?[1].baseTransform.reflection, .x)
    }

    func testReusableModelDescriptorRejectsDuplicateContactSlotMember() throws {
        let fixture = try reusableFixtureBundle(named: "reusable-valid") { descriptorJSON in
            descriptorJSON.replacingOccurrences(
                of: #""contactSlots":{"#,
                with: #""contactSlots":{"edge":{"nodeIDs":["UnitEdge"],"facePlaneAABB":{"min":[0.1,0.2],"max":[0.4,0.6]},"center":[0.25,0.4]},"#
            )
        }
        addTeardownBlock { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage = error as? BoardPackageStoreError else {
                return XCTFail("expected invalid reusable descriptor rejection, got \(error)")
            }
        }
    }

    func testReusablePositionTransformsRejectReflection() throws {
        let fixture = try reusableFixtureBundle(named: "reusable-valid") { $0 }
        addTeardownBlock { fixture.remove() }
        let boardURL = fixture.rootURL
            .appendingPathComponent("Hangboards/fixture-model/board.json")
        var boardJSON = try String(contentsOf: boardURL, encoding: .utf8)
        let needle = #""positionTransforms":{"primary":{"rotation":[0,0,0,1],"translation":[0.000000000,0.000000000,0.000000000]}"#
        let replacement = #""positionTransforms":{"primary":{"reflection":"x","rotation":[0,0,0,1],"translation":[0.000000000,0.000000000,0.000000000]}"#
        XCTAssertTrue(boardJSON.contains(needle), "expected sortedKeys positionTransforms shape in fixture board.json")
        boardJSON = boardJSON.replacingOccurrences(of: needle, with: replacement)
        try Data(boardJSON.utf8).write(to: boardURL)

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage(_, let reason) = error as? BoardPackageStoreError else {
                return XCTFail("expected invalidPackage, got \(error)")
            }
            XCTAssertTrue(
                reason.contains("positionTransforms must omit reflection"),
                "unexpected reason: \(reason)"
            )
        }
    }

    func testOnDemandStoreLoadsEveryCorrectedBundledSuspensionPackage() throws {
        let store = try BoardPackageStore(bundle: .main, modelAssetMode: .onDemand)
        let expected: [(id: String, slug: String)] = [
            ("captain-fingerfood.dual", "captain-fingerfood-dual"),
            ("captain-fingerfood.pocket", "captain-fingerfood-pocket"),
            ("captain-fingerfood.unlevel", "captain-fingerfood-unlevel"),
            ("j-bryant.ftg-32", "j-bryant-ftg-32"),
            ("yy.baguette-evo", "yy-baguette-evo"),
        ]

        for item in expected {
            let board = try XCTUnwrap(store.board(id: item.id), item.id)
            let presentation = board.defaultPresentation
            guard case .model(let media) = presentation.media else {
                return XCTFail("\(item.id) must load as model media")
            }
            XCTAssertNotNil(media.suspension, item.id)
            XCTAssertNotNil(media.orientation, item.id)
            XCTAssertEqual(
                store.modelResource(for: board, presentationID: presentation.id),
                BoardModelResource(packageSlug: item.slug, assetPath: "assets/primary.usdz"),
                item.id
            )
            XCTAssertNil(
                store.presentationAssetURL(for: board, presentationID: presentation.id),
                "on-demand USDZ must not be treated as an ordinary bundled asset"
            )
        }
    }

    func testStoreRejectsV2AndLoadsV3ContactsWithMultipleBodies() throws {
        XCTAssertThrowsError(try BoardPackageStore(bundle: fixtureBundle(schemaVersion: 2)).boards)
        let board = try XCTUnwrap(BoardPackageStore(bundle: v3TwoBodyFixtureBundle()).boards.first)
        XCTAssertEqual(board.revisionID, "2026-09-contact-first")
        XCTAssertEqual(board.contacts.map(\.id), ["left-edge", "right-edge"])
    }

    func testAuthoredOneHandedBoardsReportHandCapacityOne() throws {
        let expectedOneHanded = [
            "captain-fingerfood.dual",
            "captain-fingerfood.pocket",
            "captain-fingerfood.unlevel",
            "lattice.mini-bar",
            "lattice.mxedge-lift-small",
            "lattice.mxedge-lift-large",
            "nature.stone-hanger-mini",
            "nature.stone-hanger-mini-karma8a",
            "plateau.lifting-edge",
            "frictitious.nug",
            "aelith.cyclops-011",
            "crimptonite.helium-mobile",
        ]

        for boardID in expectedOneHanded {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID), boardID)
            XCTAssertEqual(board.handCapacity, 1, boardID)
            XCTAssertTrue(board.isOneHanded, boardID)
        }
    }

    func testOmittedBoardHandCapacityDefaultsToTwoHanded() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "beastmaker-1000"))
        XCTAssertEqual(board.handCapacity, 2)
        XCTAssertFalse(board.isOneHanded)
    }

    func testStorePreservesBoardHandCapacityAndRejectsInvalidOrInconsistentValues() throws {
        let oneHanded = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["handCapacity"] = 1
            }
        }
        defer { oneHanded.remove() }

        let authored = try XCTUnwrap(BoardPackageStore(bundle: oneHanded.bundle).boards.first)
        XCTAssertEqual(authored.handCapacity, 1)
        XCTAssertTrue(authored.isOneHanded)

        for invalid in [0, 3] {
            let invalidFixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    board["handCapacity"] = invalid
                }
            }
            defer { invalidFixture.remove() }

            XCTAssertThrowsError(
                try BoardPackageStore(bundle: invalidFixture.bundle),
                "must reject board handCapacity \(invalid)"
            ) { error in
                XCTAssertEqual(
                    error as? BoardPackageStoreError,
                    .invalidPackage(
                        boardID: "fixture.board",
                        reason: "board handCapacity must be in \(PhysicalContact.validHandCapacityRange)"
                    )
                )
            }
        }

        let inconsistent = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["handCapacity"] = 1
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["handCapacity"] = 2
                board["contacts"] = holds
            }
        }
        defer { inconsistent.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: inconsistent.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "fixture.board",
                    reason: "one-handed board cannot include contact hold-left with handCapacity 2"
                )
            )
        }
    }

    func testMXEdgeLiftPackagesLoadTypedUnilateralResolutionPolicy() throws {
        let store = try BoardPackageStore(bundle: .main, modelAssetMode: .onDemand)

        XCTAssertEqual(
            try XCTUnwrap(store.board(id: "lattice.mxedge-lift-small"))
                .unilateralHandResolution,
            .athleteRelative
        )
        XCTAssertNil(
            try XCTUnwrap(store.board(id: "lattice.mxedge-lift-large"))
                .unilateralHandResolution
        )
    }

    func testStoreRejectsNullAndUnsupportedUnilateralHandResolution() throws {
        for value: Any in [NSNull(), "unsupported"] {
            let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
                try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                    board["unilateralHandResolution"] = value
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), "must reject value \(value)")
        }
    }

    func testStoreLeavesOmittedUnilateralHandResolutionNil() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                board.removeValue(forKey: "unilateralHandResolution")
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        XCTAssertNil(board.unilateralHandResolution)
    }

    func testOnDemandModelTagIsDeterministicAndSafeForValidatedPackageSlug() {
        let resource = BoardModelResource(
            packageSlug: "metolius-wood-grips-compact-ii",
            assetPath: "assets/primary.usdz"
        )

        XCTAssertEqual(
            resource.tag,
            "hang-ten-model-metolius-wood-grips-compact-ii"
        )
        XCTAssertTrue(resource.tag.allSatisfy { character in
            character.isLowercase || character.isNumber || character == "-"
        })
    }

    func testDebugSimulatorPackagedURLFindsOnlyTheExpectedODRAsset() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true)
        defer { fixture.remove() }
        let resource = BoardModelResource(
            packageSlug: "fixture-model",
            assetPath: "assets/primary.usdz"
        )
        let packagedURL = fixture.rootURL.appendingPathComponent(
            "OnDemandResources/fixture.assetpack/Hangboards/fixture-model/assets/primary.usdz"
        )
        try FileManager.default.createDirectory(
            at: packagedURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("packaged-model".utf8).write(to: packagedURL)
        let unrelatedURL = fixture.rootURL.appendingPathComponent(
            "OnDemandResources/unrelated.assetpack/Hangboards/other-board/assets/primary.usdz"
        )
        try FileManager.default.createDirectory(
            at: unrelatedURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("unrelated-model".utf8).write(to: unrelatedURL)

        #if DEBUG
        XCTAssertEqual(resource.debugSimulatorPackagedURL(in: fixture.bundle), packagedURL)
        #else
        XCTAssertNil(resource.debugSimulatorPackagedURL(in: fixture.bundle))
        #endif
    }

    @MainActor
    func testOnDemandModelLoaderRetainsAccessForSceneLifetimeAndSupportsRepeatedLoads() async throws {
        let fixture = try makeModelFixtureBundle(
            modelSHA256Matches: true,
            boardID: "fixture.scene-lifetime-\(UUID().uuidString.lowercased())"
        )
        defer { fixture.remove() }
        let bundledModelURL = fixture.rootURL.appendingPathComponent(
            "Hangboards/fixture-model/assets/primary.usdz"
        )
        let modelBytes = try Data(contentsOf: bundledModelURL)
        try FileManager.default.removeItem(at: bundledModelURL)
        let store = try BoardPackageStore(
            bundle: fixture.bundle,
            modelAssetMode: .onDemand
        )
        let board = try XCTUnwrap(store.boards.first)
        let presentation = board.defaultPresentation
        let requestedModelURL = fixture.rootURL.appendingPathComponent(
            "OnDemand/Hangboards/fixture-model/assets/primary.usdz"
        )
        var requestedTags: [Set<String>] = []
        var endCount = 0
        let access = BoardModelResourceAccess(
            requestFactory: { tags, _ in
                requestedTags.append(tags)
                return TestBoardModelResourceRequest(
                    begin: {
                        try FileManager.default.createDirectory(
                            at: requestedModelURL.deletingLastPathComponent(),
                            withIntermediateDirectories: true
                        )
                        try modelBytes.write(to: requestedModelURL)
                    },
                    end: {
                        endCount += 1
                        try? FileManager.default.removeItem(at: requestedModelURL)
                    }
                )
            },
            urlResolver: { _, _ in
                FileManager.default.fileExists(atPath: requestedModelURL.path)
                    ? requestedModelURL
                    : nil
            }
        )

        for attempt in 1...2 {
            var scene = await BoardModelAsset.$sceneLoaderForTesting.withValue({ _ in
                makeBoardModelFixtureScene()
            }) {
                await BoardModelLoader.load(
                    board: board,
                    presentation: presentation,
                    store: store,
                    resourceAccess: access
                )
            }

            XCTAssertNotNil(scene, "load \(attempt)")
            XCTAssertEqual(
                try Data(contentsOf: requestedModelURL),
                modelBytes,
                "load \(attempt)"
            )
            scene = nil
            XCTAssertFalse(
                FileManager.default.fileExists(atPath: requestedModelURL.path),
                "load \(attempt) must end access when its scene is released"
            )
        }

        XCTAssertEqual(
            requestedTags,
            [
                ["hang-ten-model-fixture-model"],
                ["hang-ten-model-fixture-model"]
            ]
        )
        XCTAssertEqual(endCount, 2)
    }

    @MainActor
    func testModelLoadsAreSerializedAcrossDistinctBoards() async throws {
        let loadCount = 4
        var fixtures: [FixtureBundle] = []
        defer { fixtures.forEach { $0.remove() } }
        var stores: [BoardPackageStore] = []
        for index in 0..<loadCount {
            let fixture = try makeModelFixtureBundle(
                modelSHA256Matches: true,
                boardID: "fixture.concurrent-\(index)-\(UUID().uuidString.lowercased())"
            )
            fixtures.append(fixture)
            stores.append(try BoardPackageStore(bundle: fixture.bundle))
        }

        let tracker = ModelLoadConcurrencyTracker()
        let results = await withTaskGroup(of: Bool.self, returning: [Bool].self) { group in
            for store in stores {
                group.addTask {
                    guard let board = store.boards.first else { return false }
                    let presentation = board.defaultPresentation
                    return await BoardModelAsset.$sceneLoaderForTesting.withValue({ _ in
                        tracker.enter()
                        Thread.sleep(forTimeInterval: 0.1)
                        tracker.exit()
                        return makeBoardModelFixtureScene()
                    }) {
                        await BoardModelLoader.load(
                            board: board,
                            presentation: presentation,
                            store: store
                        ) != nil
                    }
                }
            }
            var results: [Bool] = []
            for await result in group {
                results.append(result)
            }
            return results
        }

        XCTAssertEqual(results.filter { $0 }.count, loadCount, "every distinct board must load")
        XCTAssertEqual(tracker.peak, 1, "model decodes must never overlap across boards")
    }

    @MainActor
    func testCancelledQueuedModelLoadDoesNotJamOrLeakGate() async throws {
        let heldFixture = try makeModelFixtureBundle(
            modelSHA256Matches: true,
            boardID: "fixture.held-\(UUID().uuidString.lowercased())"
        )
        defer { heldFixture.remove() }
        let queuedFixture = try makeModelFixtureBundle(
            modelSHA256Matches: true,
            boardID: "fixture.queued-\(UUID().uuidString.lowercased())"
        )
        defer { queuedFixture.remove() }
        let afterFixture = try makeModelFixtureBundle(
            modelSHA256Matches: true,
            boardID: "fixture.after-\(UUID().uuidString.lowercased())"
        )
        defer { afterFixture.remove() }

        let heldStore = try BoardPackageStore(bundle: heldFixture.bundle)
        let queuedStore = try BoardPackageStore(bundle: queuedFixture.bundle)
        let afterStore = try BoardPackageStore(bundle: afterFixture.bundle)

        let heldBoard = try XCTUnwrap(heldStore.boards.first)
        let queuedBoard = try XCTUnwrap(queuedStore.boards.first)
        let afterBoard = try XCTUnwrap(afterStore.boards.first)

        let tracker = ModelLoadConcurrencyTracker()

        // Held load owns the gate while its decode sleeps for half a second.
        let held = Task { @MainActor in
            await BoardModelAsset.$sceneLoaderForTesting.withValue({ _ in
                tracker.enter()
                Thread.sleep(forTimeInterval: 0.5)
                tracker.exit()
                return makeBoardModelFixtureScene()
            }) {
                await BoardModelLoader.load(
                    board: heldBoard,
                    presentation: heldBoard.defaultPresentation,
                    store: heldStore
                )
            }
        }
        var waitIndex = 0
        while tracker.current == 0, waitIndex < 100 {
            waitIndex += 1
            try await Task.sleep(for: .milliseconds(10))
        }
        XCTAssertGreaterThanOrEqual(
            tracker.current,
            1,
            "held load must occupy the decode hook before the queued load is created"
        )

        // Queued behind held; cancelled before it is granted a slot. The hook is
        // set so a buggy (non-serializing) gate would let it succeed -- making the
        // nil assertion discriminate the gate rather than a junk-byte decode.
        let queued = Task { @MainActor in
            await BoardModelAsset.$sceneLoaderForTesting.withValue({ _ in
                makeBoardModelFixtureScene()
            }) {
                await BoardModelLoader.load(
                    board: queuedBoard,
                    presentation: queuedBoard.defaultPresentation,
                    store: queuedStore
                )
            }
        }
        var admissionIndex = 0
        while BoardModelAsset.queuedLoadWaiterCount == 0, admissionIndex < 100 {
            admissionIndex += 1
            try await Task.sleep(for: .milliseconds(10))
        }
        XCTAssertGreaterThanOrEqual(
            BoardModelAsset.queuedLoadWaiterCount,
            1,
            "queued load must register as a gate waiter before it is cancelled"
        )
        queued.cancel()

        let queuedResult = await queued.value
        let heldResult = await held.value

        XCTAssertNotNil(heldResult, "held load must still complete")
        XCTAssertNil(queuedResult, "cancelled queued load must return nil")

        // The fixture logs are junk bytes, so the hook is required for a
        // successful decode; it also keeps `after` independent of the gate timing.
        let after = await BoardModelAsset.$sceneLoaderForTesting.withValue({ _ in
            makeBoardModelFixtureScene()
        }) {
            await BoardModelLoader.load(
                board: afterBoard,
                presentation: afterBoard.defaultPresentation,
                store: afterStore
            )
        }
        XCTAssertNotNil(after, "gate must remain usable after a queued load is cancelled")
    }

    @MainActor
    func testCancelledOnDemandAccessCancelsProgressAndEndsOnlyAfterLateSuccess() async throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true)
        defer { fixture.remove() }

        let store = try BoardPackageStore(bundle: fixture.bundle)
        let board = try XCTUnwrap(store.boards.first)
        let presentation = try XCTUnwrap(board.presentations.first)

        XCTAssertEqual(presentation.media.kind, .model)
        XCTAssertEqual(
            board.contacts[0].resolvedFrame(in: presentation),
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
    }

    @MainActor
    func testModelLoaderFailsClosedWhenValidatedPackageModelIsMissingOrCorrupt() async throws {
        let mutations: [(name: String, mutate: (URL) throws -> Void)] = [
            ("missing", { try FileManager.default.removeItem(at: $0) }),
            ("corrupt", { try Data("not a USDZ".utf8).write(to: $0) })
        ]

        for mutation in mutations {
            let uniqueBoardID = "fixture.model-loader-\(mutation.name)-\(UUID().uuidString.lowercased())"
            let fixture = try makeModelFixtureBundle(
                modelSHA256Matches: true,
                boardID: uniqueBoardID
            )
            defer { fixture.remove() }
            let store = try BoardPackageStore(bundle: fixture.bundle)
            let board = try XCTUnwrap(store.board(id: uniqueBoardID))
            let presentation = board.defaultPresentation
            let assetURL = try XCTUnwrap(
                store.presentationAssetURL(for: board, presentationID: presentation.id)
            )

            XCTAssertNil(store.presentationImageURL(for: board, presentationID: presentation.id))
            try mutation.mutate(assetURL)

            let loaded = await BoardModelLoader.load(
                board: board,
                presentation: presentation,
                store: store
            )

            XCTAssertNil(loaded, mutation.name)
        }
    }

    func testModelCacheKeySeparatesDistinctDescriptorHashes() {
        let first = BoardModelKey(
            boardID: "fixture.board",
            presentationID: "primary",
            modelSHA256: String(repeating: "a", count: 64)
        )
        let replacement = BoardModelKey(
            boardID: "fixture.board",
            presentationID: "primary",
            modelSHA256: String(repeating: "b", count: 64)
        )

        XCTAssertNotEqual(first, replacement)
        XCTAssertEqual(Set([first, replacement]).count, 2)
    }

    func testStoreRejectsSharedCrossParserMalformedModelFixtureMatrix() throws {
        let fixtures = try validationFixtures()
        let matrix = try XCTUnwrap(fixtures["modelParserParity"] as? [[String: Any]])
        XCTAssertEqual(
            matrix.compactMap { $0["name"] as? String },
            [
                "paired-pose-mouths-null", "paired-pose-mouths-missing-lead",
                "paired-pose-mouths-coincident", "paired-pose-mouths-outside-bounds",
                "paired-pose-mouth-coincident-with-default-contact",
                "wrong-schema-version", "unknown-media-type", "escaped-typed-path",
                "extra-asset", "stale-sha", "omitted-node", "extra-node",
                "body-with-hold-id", "unbound-geometry", "invalid-camera",
                "unknown-suspension-field", "wrong-suspension-type",
                "missing-canonical-pose", "extra-canonical-pose",
                "duplicate-position-key", "nonunit-quaternion", "nonfinite-quaternion",
                "nonpositive-cord-values", "nonpositive-rest-length",
                "missing-attachment-node", "hold-attachment-node",
                "attachment-point-outside-bounds", "shorter-than-endpoint-distance",
                "raster-sibling", "second-model", "baked-cord-role", "baked-anchor-role",
                "model-inversion", "two-branch-unknown-member", "two-branch-wrong-discriminator",
                "two-branch-missing-passage", "two-branch-extra-passage", "two-branch-duplicate-passage-id",
                "two-branch-unknown-passage-node", "two-branch-hold-passage-node",
                "two-branch-nonfinite-passage-point", "two-branch-passage-point-out-of-bounds",
                "two-branch-missing-branch", "two-branch-duplicate-branch-id", "two-branch-wrong-branch-pair",
                "two-branch-branch-pair-order", "two-branch-distinct-branch-anchors",
                "two-branch-invalid-rest-length", "two-branch-invalid-radius", "two-branch-invalid-material",
                "two-branch-missing-pose", "two-branch-unknown-pose", "two-branch-duplicate-pose",
                "two-branch-explicit-null", "two-branch-scalar-kind-mismatch",
                "two-branch-suspension-member-order",
                "two-branch-directed-route-too-short", "two-branch-order-violation",
                "two-branch-excess-attachment-nodes", "two-branch-coincident-passage-endpoints",
                "two-branch-passage-anchor-coincidence",
                "directed-mixed-passage-representations", "directed-zero-bore",
                "directed-null-contact", "directed-empty-contact", "directed-short-route",
                "directed-mixed-mouth-fields",
                "paired-lead-three-attachments", "paired-lead-duplicate-id",
                "paired-lead-hold-node", "paired-lead-visible-anchor",
                "paired-lead-unknown-pose", "paired-lead-short-lead",
                "paired-lead-contact-points-null", "paired-lead-contact-point-nonfinite",
                "paired-lead-contact-points-coincident", "paired-lead-routed-lead-too-short",
                "paired-lead-suspension-member-order",
                "paired-lead-anchor-member-order", "paired-lead-cord-member-order",
                "paired-lead-empty-attachment-provenance", "paired-lead-empty-anchor-provenance",
                "paired-lead-empty-cord-material", "paired-lead-empty-cord-provenance"
            ]
        )

        for specification in matrix {
            let name = try XCTUnwrap(specification["name"] as? String)
            XCTAssertEqual(specification["pythonException"] as? String, "ValueError", name)
            let expectedCategory = try XCTUnwrap(specification["swiftError"] as? String)
            let fixture = try makeSharedModelParserParityFixtureBundle(specification)
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), name) { error in
                guard let packageError = error as? BoardPackageStoreError else {
                    return XCTFail("Expected BoardPackageStoreError for \(name), got \(error)")
                }
                switch (expectedCategory, packageError) {
                case ("invalidPackage", .invalidPackage), ("malformedJSON", .malformedJSON):
                    break
                default:
                    XCTFail("Expected \(expectedCategory) for \(name), got \(packageError)")
                }
            }
        }
    }

    func testStoreLoadsValidTwoBranchSuspensionFixture() throws {
        let fixture = try makeSharedModelParserParityFixtureBundle([
            "base": "twoBranchModel",
            "mutations": []
        ])
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .model(let media) = board.presentations[0].media,
              case .twoBranchCord(let suspension) = media.suspension else {
            return XCTFail("expected twoBranchCord model suspension")
        }
        let boardData = try Data(contentsOf: fixture.rootURL
            .appendingPathComponent("Hangboards/fixture-model/board.json"))
        XCTAssertTrue(
            String(decoding: boardData, as: UTF8.self)
                .contains(#""suspension":{"type":"twoBranchCord","passages":"#),
            "valid fixture must retain the declared two-branch member order"
        )
        XCTAssertEqual(suspension.passages.left.count, 2)
        XCTAssertEqual(suspension.passages.right.count, 2)
        XCTAssertEqual(suspension.branches.count, 2)
        XCTAssertEqual(Set(suspension.canonicalPoses.keys), ["primary", "secondary", "tertiary", "quaternary"])
        XCTAssertEqual(media.suspension?.cord.restLength, 0.92)
        XCTAssertEqual(suspension.branches.map(\.restLength), [0.92, 0.92])
        XCTAssertTrue(
            board.positions.allSatisfy { Set($0.contactIDs) == Set(media.descriptor.contacts.keys) },
            "implicit suspension positions materialize the descriptor inventory without partitioning it"
        )
        let solved = try SuspendedBoardPresentation.solve(
            pose: try XCTUnwrap(suspension.canonicalPoses["primary"]),
            suspension: suspension,
            bounds: media.descriptor.modelBounds
        )
        XCTAssertEqual(solved.branches.map(\.id), ["left-branch", "right-branch"])
        XCTAssertEqual(solved.branches[0].arcLength, 0.9159936, accuracy: 1e-5)
        XCTAssertEqual(solved.branches[1].arcLength, 0.9159936, accuracy: 1e-5)
    }

    func testStoreLoadsValidPairedLeadCordSuspensionFixture() throws {
        let fixture = try makeSharedModelParserParityFixtureBundle([
            "base": "pairedLeadCordModel",
            "mutations": []
        ])
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .model(let media) = board.presentations[0].media,
              case .pairedLeadCord(let suspension) = media.suspension else {
            return XCTFail("expected pairedLeadCord model suspension")
        }
        XCTAssertEqual(suspension.attachments.map(\.id), ["left-lead", "right-lead"])
        XCTAssertEqual(suspension.attachments.map(\.contactPointsInModel), [
            [[0.2, 0.5, 0.05], [0.2, 0.45, 0.05]],
            [[0.8, 0.5, 0.05], [0.8, 0.45, 0.05]],
        ])
        XCTAssertEqual(suspension.cord.restLength, 0.8)
        XCTAssertEqual(Set(suspension.canonicalPoses.keys), ["primary"])
    }

    func testStorePreservesPoseSpecificPairedLeadMouths() throws {
        let points = ["left-lead": [0.2, 0.45, 0.1], "right-lead": [0.8, 0.45, 0.1]]
        let fixture = try makeSharedModelParserParityFixtureBundle([
            "base": "pairedLeadCordModel",
            "mutations": [["target": "board", "op": "replace",
                "path": ["presentations", 0, "media", "suspension", "canonicalPoses", "primary", "attachmentPoints"],
                "value": points]]
        ])
        defer { fixture.remove() }
        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .model(let media) = board.presentations[0].media,
              case .pairedLeadCord(let suspension) = media.suspension else { return XCTFail("missing paired leads") }
        XCTAssertEqual(suspension.canonicalPoses["primary"]?.attachmentPoints, points)
    }

    func testStoreLoadsPairedLeadCordWithDistinctPointsOnSharedBodyNode() throws {
        let fixture = try makeSharedModelParserParityFixtureBundle([
            "base": "pairedLeadCordModel",
            "mutations": [[
                "target": "board",
                "op": "replace",
                "path": ["presentations", 0, "media", "suspension", "attachments", 1, "nodeID"],
                "value": "Body"
            ]]
        ])
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .model(let media) = board.presentations[0].media,
              case .pairedLeadCord(let suspension) = media.suspension else {
            return XCTFail("expected pairedLeadCord model suspension")
        }
        XCTAssertEqual(suspension.attachments.map(\.id), ["left-lead", "right-lead"])
        XCTAssertEqual(suspension.attachments.map(\.nodeID), ["Body", "Body"])
        XCTAssertEqual(suspension.attachments.map(\.pointInModel), [[0.2, 0.5, 0.1], [0.8, 0.5, 0.1]])
    }

    func testStorePreservesPoseCordContactsAndRejectsIncompleteOrTooLongRoutes() throws {
        let valid = ["left-lead": [[0.2, 0.6, 0.1]], "right-lead": [[0.8, 0.6, 0.1]]]
        let acceptedFixture = try makeSharedModelParserParityFixtureBundle([
            "base": "pairedLeadCordModel",
            "mutations": [["target": "board", "op": "replace",
                "path": ["presentations", 0, "media", "suspension", "canonicalPoses", "primary", "cordContactPoints"],
                "value": valid]]
        ])
        defer { acceptedFixture.remove() }
        let board = try XCTUnwrap(BoardPackageStore(bundle: acceptedFixture.bundle).boards.first)
        guard case .model(let media) = board.presentations[0].media,
              case .pairedLeadCord(let suspension) = media.suspension else {
            return XCTFail("missing paired-lead suspension")
        }
        XCTAssertEqual(suspension.canonicalPoses["primary"]?.cordContactPoints, valid)

        let rejectedCases: [([String: [[Double]]], String)] = [
            (["left-lead": [[0.2, 0.6, 0.1]]],
             "cordContactPoints must name every attachment or passage with a nonempty finite distinct route"),
            (["left-lead": [], "right-lead": [[0.8, 0.6, 0.1]]],
             "cordContactPoints must name every attachment or passage with a nonempty finite distinct route"),
            (["left-lead": [[0.2, 5, 0.1]], "right-lead": [[0.8, 0.6, 0.1]]],
             "pairedLeadCord pose primary restLength is shorter than routed lead"),
            (["left-lead": [[0.2, 0.5, 0.1]], "right-lead": [[0.8, 0.6, 0.1]]],
             "cordContactPoints resolved route points must be distinct"),
        ]
        for (routes, reason) in rejectedCases {
            let fixture = try makeSharedModelParserParityFixtureBundle([
                "base": "pairedLeadCordModel",
                "mutations": [["target": "board", "op": "replace",
                    "path": ["presentations", 0, "media", "suspension", "canonicalPoses", "primary", "cordContactPoints"],
                    "value": routes]]
            ])
            defer { fixture.remove() }
            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
                XCTAssertEqual(
                    error as? BoardPackageStoreError,
                    .invalidPackage(boardID: "fixture.paired-lead", reason: reason)
                )
            }
        }
    }

    func testStoreRejectsThroughBorePassagesForPairedLeadCord() throws {
        let fixture = try makeSharedModelParserParityFixtureBundle([
            "base": "pairedLeadCordModel",
            "mutations": [["target": "board", "op": "replace",
                "path": ["presentations", 0, "media", "suspension", "passages", "left", 0],
                "value": ["id": "left-lip", "nodeID": "Body",
                    "entryPointInModel": [0.2, 0.5, 0.1],
                    "exitPointInModel": [0.2, 0.35, 0.1],
                    "provenance": "displayEstimate"]]]
        ])
        defer { fixture.remove() }
        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(boardID: "fixture.paired-lead", reason: "pairedLeadCord requires exactly one non-through-bore passage per side with distinct IDs and finite in-bounds points")
            )
        }
    }

    func testStoreLoadsValidDirectedTwoBranchSuspensionFixture() throws {
        let fixture = try makeSharedModelParserParityFixtureBundle([
            "base": "directedTwoBranchModel",
            "mutations": []
        ])
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .model(let media) = board.presentations[0].media,
              case .twoBranchCord(let suspension) = media.suspension else {
            return XCTFail("expected directed twoBranchCord model suspension")
        }
        XCTAssertTrue((suspension.passages.left + suspension.passages.right).allSatisfy(\.isThroughBore))
        XCTAssertTrue(suspension.branches.allSatisfy {
            !$0.entryContactPoints.isEmpty && $0.exteriorContactPoints.count >= 2 && !$0.exitContactPoints.isEmpty
        })
    }

    func testSharedFixtureBuilderUsesDeclaredBaseDocument() throws {
        let fixture = try makeSharedModelParserParityFixtureBundle([
            "base": "twoBranchModel",
            "mutations": []
        ])
        defer { fixture.remove() }

        let boardData = try Data(contentsOf: fixture.rootURL
            .appendingPathComponent("Hangboards/fixture-model/board.json"))
        let board = try XCTUnwrap(
            try JSONSerialization.jsonObject(with: boardData) as? [String: Any]
        )
        let presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
        let media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
        let suspension = try XCTUnwrap(media["suspension"] as? [String: Any])
        XCTAssertEqual(suspension["type"] as? String, "twoBranchCord")
    }

    func testSharedFixtureBuilderAppliesNoncanonicalTwoBranchSuspensionMemberOrder() throws {
        let fixtures = try validationFixtures()
        let matrix = try XCTUnwrap(fixtures["modelParserParity"] as? [[String: Any]])
        let specification = try XCTUnwrap(
            matrix.first(where: { $0["name"] as? String == "two-branch-suspension-member-order" })
        )
        let fixture = try makeSharedModelParserParityFixtureBundle(specification)
        defer { fixture.remove() }

        let boardData = try Data(contentsOf: fixture.rootURL
            .appendingPathComponent("Hangboards/fixture-model/board.json"))
        let boardJSON = String(decoding: boardData, as: UTF8.self)
        XCTAssertTrue(
            boardJSON.contains(#""suspension":{"anchor":"#),
            "shared order fixture must preserve its deliberate noncanonical raw suspension member order"
        )
    }

    func testWrongTwoBranchDiscriminatorUsesInvalidPackageCategory() throws {
        let fixtures = try validationFixtures()
        let matrix = try XCTUnwrap(fixtures["modelParserParity"] as? [[String: Any]])
        let specification = try XCTUnwrap(
            matrix.first(where: { $0["name"] as? String == "two-branch-wrong-discriminator" })
        )
        let fixture = try makeSharedModelParserParityFixtureBundle(specification)
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case .invalidPackage = error as? BoardPackageStoreError else {
                return XCTFail("expected invalidPackage shape mismatch, got \(error)")
            }
        }
    }

    func testTwoBranchOrderAndDirectedRouteRegressionsUseDeclaredCategories() throws {
        let fixtures = try validationFixtures()
        let matrix = try XCTUnwrap(fixtures["modelParserParity"] as? [[String: Any]])
        for name in ["two-branch-suspension-member-order", "two-branch-directed-route-too-short"] {
            let specification = try XCTUnwrap(matrix.first(where: { $0["name"] as? String == name }))
            let fixture = try makeSharedModelParserParityFixtureBundle(specification)
            defer { fixture.remove() }
            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), name) { error in
                let expected = specification["swiftError"] as? String
                switch (expected, error as? BoardPackageStoreError) {
                case ("malformedJSON", .malformedJSON): break
                case ("invalidPackage", .invalidPackage): break
                default: XCTFail("unexpected category for \(name): \(error)")
                }
            }
        }
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

    func testFlashBoardExposesUprightAndInvertedConfigurationsForBothFaces() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "tension.flash-board"))
        XCTAssertEqual(board.contacts.count, 7)
        XCTAssertTrue(
            Set(board.contacts.map(\.id)).isSuperset(of: ["small-crimp-left", "small-crimp-right"])
        )

        XCTAssertEqual(
            board.positions.map(\.id),
            [
                "three-edge-upright",
                "three-edge-inverted",
                "two-edge-upright",
                "two-edge-inverted",
            ]
        )

        let expectedHoldIDsByPosition = [
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

        for (positionID, expectedHoldIDs) in expectedHoldIDsByPosition {
            let position = try XCTUnwrap(board.positions.first { $0.id == positionID })
            XCTAssertEqual(position.contactIDs, expectedHoldIDs)
            XCTAssertEqual(position.presentationID, "primary")
        }

        // The approved ODR model uses the tested two-branch suspension.
        let presentation = try XCTUnwrap(board.presentations.first)
        guard case .model(let media) = presentation.media,
              case .twoBranchCord(let suspension) = media.suspension else {
            XCTFail("Expected model media"); return
        }
        XCTAssertNil(media.orientation)
        XCTAssertEqual(
            media.descriptor.modelSHA256,
            "555191023ddc584c1a01dadba7bfe21ed5a81db570943a0697958df416cfdbac"
        )
        XCTAssertEqual(suspension.branches.count, 2)
        XCTAssertEqual(Set(suspension.canonicalPoses.keys), Set(expectedHoldIDsByPosition.keys))
    }

    func testPresentationContentExcludesLogicalHoldWithoutResolvableMediaFrame() {
        let hold = PhysicalContact(id: "left", name: "Left", kind: .edge)
        let presentation = BoardPresentation(
            id: "primary",
            name: "Primary",
            aspectRatio: 1,
            isDefault: true,
            media: .raster(
                BoardRasterMedia(assetPath: "assets/primary.png", contactGeometry: ["left": []])
            )
        )
        let board = BoardRevision(
            id: "fixture-missing-geometry",
            revisionID: "test-fixture",
            manufacturer: "Fixture",
            name: "Missing geometry",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            contacts: [hold],
            productURL: URL(string: "https://example.com/fixture-missing-geometry")!,
            photoAssetName: nil,
            presentations: [presentation]
        )

        let content = BoardMapPresentationContent(
            board: board,
            selectedPresentationID: presentation.id
        )

        XCTAssertTrue(content.holds.isEmpty)
    }

    func testStoreAcceptsCanonicalTieToEvenDescriptorCenter() throws {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(
                at: packageURL.appendingPathComponent("assets/primary.model.json")
            ) { descriptor in
                var holds = try XCTUnwrap(descriptor["contacts"] as? [String: [String: Any]])
                var hold = try XCTUnwrap(holds["hold-left"])
                hold["facePlaneAABB"] = [
                    "min": [0.1, 0.2],
                    "max": [0.100000023, 0.6]
                ]
                hold["center"] = [0.100000011, 0.4]
                holds["hold-left"] = hold
                descriptor["contacts"] = holds
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
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                var right = try XCTUnwrap(holds.first)
                right["id"] = "hold-right"
                right["name"] = "Right hold"
                holds.append(right)
                board["contacts"] = holds
            }
            let descriptorURL = packageURL.appendingPathComponent("assets/primary.model.json")
            try self.mutateJSONObject(at: descriptorURL) { descriptor in
                var nodes = try XCTUnwrap(descriptor["nodes"] as? [[String: Any]])
                nodes.append(["nodeID": "Right", "role": "contact", "contactID": "hold-right"])
                descriptor["nodes"] = nodes
                var holds = try XCTUnwrap(descriptor["contacts"] as? [String: Any])
                holds["hold-right"] = [
                    "nodeIDs": ["Right"],
                    "facePlaneAABB": ["min": [0.6, 0.2], "max": [0.9, 0.6]],
                    "center": [0.75, 0.4]
                ]
                descriptor["contacts"] = holds
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
            data: Data(#"{"ignored":"quote: \" and brace: }","contacts":{"hold-a":{}}}"#.utf8)
        )
        XCTAssertEqual(try escaped.memberNames(inRootObjectNamed: "contacts"), ["hold-a"])

        let excessiveDepth = BoardPackageJSONMemberOrder.maximumNestingDepth + 1
        let nestedValue = String(repeating: "[", count: excessiveDepth) + "0" +
            String(repeating: "]", count: excessiveDepth)
        var nested = BoardPackageJSONMemberOrder(
            data: Data("{\"ignored\":\(nestedValue),\"contacts\":{}}".utf8)
        )

        XCTAssertThrowsError(try nested.memberNames(inRootObjectNamed: "contacts"))
    }

    func testStoreLoadsV3RasterGeometryFromPresentationMedia() throws {
        let fixture = try makeRasterV3FixtureBundle()
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let presentation = try XCTUnwrap(board.presentations.first)

        XCTAssertEqual(presentation.media.kind, .raster)
        XCTAssertEqual(
            board.contacts[0].resolvedFrame(in: presentation),
            HoldFrame(x: 0.1, y: 0.2, width: 0.55, height: 0.4)
        )
    }

    func testStoreRejectsDuplicateOriginalRasterOwnership() throws {
        let fixture = try makeMultiPresentationFixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[1]["media"] as? [String: Any])
            var holdGeometry = try XCTUnwrap(media["contactGeometry"] as? [String: Any])
            holdGeometry["hold-left"] = self.fixtureHoldGeometry()["hold-left"]
            media["contactGeometry"] = holdGeometry
            presentations[1]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly once")
    }

    func testStoreRejectsRedundantEmptyOriginalRasterPresentation() throws {
        let fixture = try makeMultiPresentationFixtureBundle(
            boardMutation: { board in
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                presentations.append([
                    "id": "unused",
                    "name": "Unused",
                    "aspectRatio": 1,
                    "isDefault": false,
                    "derivation": ["type": "original"],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/unused.png",
                        "contactGeometry": [:],
                    ],
                ])
                board["presentations"] = presentations
            },
            mutateAssets: { assetsURL in
                try self.squarePresentationBytes().write(
                    to: assetsURL.appendingPathComponent("unused.png")
                )
            }
        )
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "at least one physical contact")
    }

    func testStoreRejectsRasterHoldOwnedOnlyByDerivedPresentation() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
            var holdGeometry = try XCTUnwrap(media["contactGeometry"] as? [String: Any])
            holdGeometry.removeValue(forKey: "hold-right")
            media["contactGeometry"] = holdGeometry
            presentations[0]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly once")
    }

    func testStoreRejectsDerivedRasterGeometryThatDiffersFromSource() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[1]["media"] as? [String: Any])
            var holdGeometry = try XCTUnwrap(
                media["contactGeometry"] as? [String: [[String: Any]]]
            )
            var pieces = try XCTUnwrap(holdGeometry["hold-left"])
            var frame = try XCTUnwrap(pieces[0]["frame"] as? [String: Any])
            frame["x"] = 0.2
            pieces[0]["frame"] = frame
            holdGeometry["hold-left"] = pieces
            media["contactGeometry"] = holdGeometry
            presentations[1]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly equal its source geometry")
    }

    func testStoreRejectsDerivedRasterGeometryWithDifferentPieceOrder() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[1]["media"] as? [String: Any])
            var holdGeometry = try XCTUnwrap(
                media["contactGeometry"] as? [String: [[String: Any]]]
            )
            holdGeometry["hold-left"]?.reverse()
            media["contactGeometry"] = holdGeometry
            presentations[1]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly equal its source geometry")
    }

    func testStoreRejectsDerivedRasterGeometryWithDifferentObjectMemberOrder() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle()
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
        let fixture = try makeDerivedRasterV3FixtureBundle()
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

    func testStoreAcceptsDerivedRasterGeometryWithEquivalentHighPrecisionFloatingValues() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle()
        defer { fixture.remove() }

        try replaceDerivedCornerRadiusTokens(
            in: fixture,
            source: "0.100000000000000005",
            derived: "0.100000000000000006"
        )

        XCTAssertNoThrow(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreAcceptsDerivedRasterGeometryWithEquivalentFloatingExponentValues() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle()
        defer { fixture.remove() }

        try replaceDerivedCornerRadiusTokens(
            in: fixture,
            source: "1e-1",
            derived: "0.1"
        )

        XCTAssertNoThrow(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreAcceptsDerivedRasterGeometryWithEquivalentSignedFloatingZeroValues() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle()
        defer { fixture.remove() }

        try replaceDerivedCornerRadiusTokens(
            in: fixture,
            source: "-0.0",
            derived: "0e0"
        )

        XCTAssertNoThrow(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreRejectsDerivedRasterGeometryWithAdjacentFloatingValues() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle()
        defer { fixture.remove() }

        try replaceDerivedCornerRadiusTokens(
            in: fixture,
            source: "0.1",
            derived: "0.10000000000000002"
        )

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly equal its source geometry")
    }

    func testStoreRejectsDerivedRasterGeometryWithDifferentIntegerValues() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle()
        defer { fixture.remove() }
        let boardURL = fixture.rootURL.appendingPathComponent(
            "Hangboards/fixture-model/board.json"
        )
        var sourceGeometry = fixtureDerivedHoldGeometry()
        var sourcePieces = try XCTUnwrap(sourceGeometry["hold-left"])
        sourcePieces[0]["shapeConstraint"] = [
            "shape": "roundedRectangle",
            "rotationDegrees": 0,
        ]
        sourceGeometry["hold-left"] = sourcePieces
        var derivedGeometry = sourceGeometry
        var derivedPieces = try XCTUnwrap(derivedGeometry["hold-left"])
        derivedPieces[0]["shapeConstraint"] = [
            "shape": "roundedRectangle",
            "rotationDegrees": 1,
        ]
        derivedGeometry["hold-left"] = derivedPieces
        let original = try JSONSerialization.data(
            withJSONObject: fixtureDerivedHoldGeometry(),
            options: [.sortedKeys]
        )
        try replaceTwoOccurrences(
            of: original,
            firstReplacement: try JSONSerialization.data(
                withJSONObject: sourceGeometry,
                options: [.sortedKeys]
            ),
            secondReplacement: try JSONSerialization.data(
                withJSONObject: derivedGeometry,
                options: [.sortedKeys]
            ),
            in: boardURL
        )

        assertStoreRejects(fixture.bundle, reasonContaining: "exactly equal its source geometry")
    }

    func testStoreAcceptsDerivedRasterGeometryWithEquivalentSignedIntegerZeroValues() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle()
        defer { fixture.remove() }
        let boardURL = fixture.rootURL.appendingPathComponent(
            "Hangboards/fixture-model/board.json"
        )
        var constrainedGeometry = fixtureDerivedHoldGeometry()
        var pieces = try XCTUnwrap(constrainedGeometry["hold-left"])
        pieces[0]["shapeConstraint"] = [
            "shape": "roundedRectangle",
            "rotationDegrees": 0,
        ]
        constrainedGeometry["hold-left"] = pieces
        let original = try JSONSerialization.data(
            withJSONObject: fixtureDerivedHoldGeometry(),
            options: [.sortedKeys]
        )
        let unsignedGeometry = try JSONSerialization.data(
            withJSONObject: constrainedGeometry,
            options: [.sortedKeys]
        )
        let signedGeometry = Data(
            String(decoding: unsignedGeometry, as: UTF8.self)
                .replacingOccurrences(
                    of: #""rotationDegrees":0"#,
                    with: #""rotationDegrees":-0"#
                )
                .utf8
        )
        XCTAssertNotEqual(signedGeometry, unsignedGeometry)
        try replaceTwoOccurrences(
            of: original,
            firstReplacement: signedGeometry,
            secondReplacement: unsignedGeometry,
            in: boardURL
        )

        XCTAssertNoThrow(try BoardPackageStore(bundle: fixture.bundle))
    }

    func testStoreRejectsNonfiniteDerivedRasterFloatingValue() throws {
        let fixture = try makeDerivedRasterV3FixtureBundle()
        defer { fixture.remove() }

        try replaceDerivedCornerRadiusTokens(
            in: fixture,
            source: "1e999",
            derived: "1e999"
        )

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
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

    func testStoreRejectsDescriptorContactInventoryDrift() throws {
        let missingHold = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(
                at: packageURL.appendingPathComponent("assets/primary.model.json")
            ) { descriptor in
                descriptor["contacts"] = [:]
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

    func testStoreRejectsIncompleteV3RasterContactOwnership() throws {
        let fixture = try makeRasterV3FixtureBundle { board in
            var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
            var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
            media["contactGeometry"] = ["hold-left": []]
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
                        "contactGeometry": [
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
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["equipmentObjectID"] = "missing"
                board["contacts"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "fixture.board",
                    reason: "contact hold-left references unknown equipment object missing"
                )
            )
        }
    }

    func testStoreDefaultsOmittedEquipmentObjectsToOnePrimaryObject() throws {
        let fixture = try makeFixtureBundle()
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(board.equipmentObjects.map(\.id), ["primary"])
        XCTAssertTrue(board.contacts.allSatisfy { $0.equipmentObjectID == "primary" })
    }

    func testStoreRejectsLegacyMissingHandCapacityPolicy() throws {
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

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
        }
    }

    func testStoreRejectsExplicitNullEquipmentObjectFields() throws {
        let mutations: [(String, (inout [String: Any]) throws -> Void)] = [
            ("board objects", { board in
                board["equipmentObjects"] = NSNull()
            }),
            ("hold object", { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["equipmentObjectID"] = NSNull()
                board["contacts"] = holds
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
                XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
            }
        }
    }

    func testStoreRejectsExplicitNullOrLegacyContactMetadata() throws {
        let mutations: [(String, (inout [String: Any]) throws -> Void)] = [
            ("dimensions", { board in
                board["dimensions"] = NSNull()
            }),
            ("sloper", { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["kind"] = "sloper"
                holds[0]["sloper"] = NSNull()
                board["contacts"] = holds
            }),
            ("size", { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["sizeMillimeters"] = NSNull()
                board["contacts"] = holds
            }),
            ("grip type", { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["gripType"] = NSNull()
                board["contacts"] = holds
            }),
            ("finger capacity", { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["fingerCapacity"] = NSNull()
                board["contacts"] = holds
            }),
            ("hand capacity", { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["handCapacity"] = NSNull()
                board["contacts"] = holds
            }),
            ("equipment object ID", { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["equipmentObjectID"] = NSNull()
                board["contacts"] = holds
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

    func testStoreAcceptsOmittedAndRejectsExplicitNullForOptionalContactShapeAndDepth() throws {
        for field in ["shape", "depth"] {
            let omittedFixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                    holds[0].removeValue(forKey: field)
                    board["contacts"] = holds
                }
            }
            defer { omittedFixture.remove() }

            let omittedBoard = try XCTUnwrap(BoardPackageStore(bundle: omittedFixture.bundle).boards.first)
            let omittedContact = try XCTUnwrap(omittedBoard.contacts.first)
            if field == "shape" {
                XCTAssertNil(omittedContact.shape)
            } else {
                XCTAssertNil(omittedContact.depth)
            }

            let nullFixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                    holds[0][field] = NSNull()
                    board["contacts"] = holds
                }
            }
            defer { nullFixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: nullFixture.bundle), "explicit null \(field) must be rejected")
        }
    }

    func testStoreAcceptsOmittedOptionalV3Metadata() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board.removeValue(forKey: "dimensions")
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let hold = try XCTUnwrap(board.contacts.first)
        XCTAssertNil(board.dimensions)
        XCTAssertNil(hold.depth)
        XCTAssertTrue(hold.gripTypes.isEmpty)
        XCTAssertNil(hold.fingerCapacity)
        XCTAssertNil(hold.handCapacity)
        XCTAssertNil(hold.shape)
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
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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

    func testStoreDecodesContactSloperShapes() throws {
        let variants: [(shape: HoldShape?, expected: HoldShape?)] = [
            (.flat, .flat),
            (.round, .round),
            (nil, nil),
        ]

        for variant in variants {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                    holds[0]["kind"] = "sloper"
                    if let shape = variant.shape { holds[0]["shape"] = shape.rawValue }
                    board["contacts"] = holds
                }
            }
            defer { fixture.remove() }

            let hold = try XCTUnwrap(
                BoardPackageStore(bundle: fixture.bundle).boards.first?.contacts.first
            )
            XCTAssertEqual(hold.shape, variant.expected)
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
                    var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                    holds[0]["kind"] = invalidHold.kind
                    holds[0]["sloper"] = invalidHold.metadata
                    board["contacts"] = holds
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
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["kind"] = "sloper"
                holds[0]["sloper"] = ["type": "flat", "angleDegrees": 20]
                board["contacts"] = holds
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
        let board = BoardRevision(
            id: "two-sided",
            revisionID: "test-fixture",
            manufacturer: "Example",
            name: "Two Sided",
            subtitle: "",
            dimensions: "10 in × 5 in",
            aspectRatio: 2,
            contacts: [
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
            depth: .range(.init(minimum: 12.5, maximum: 20))
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
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["depth"] = [
                    "range": ["minimum": 12.5, "maximum": 7.5],
                ]
                board["contacts"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
        }
    }

    func testStoreRejectsInvalidTaggedDepthPayloads() throws {
        let invalidMeasurements: [(name: String, field: String, value: Any)] = [
            (
                "zero depth",
                "depth",
                ["range": ["minimum": -7.5, "maximum": 7.5]]
            ),
            (
                "mixed depth representations",
                "depth",
                ["category": "large", "range": ["minimum": 25, "maximum": 30]]
            ),
        ]

        for measurement in invalidMeasurements {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                    holds[0][measurement.field] = measurement.value
                    board["contacts"] = holds
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle), measurement.name) { error in
                XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
            }
        }
    }

    func testStoreRejectsNonFiniteMillimeterMeasurementJSON() throws {
        let invalidMeasurements: [
            (name: String, finiteValue: String, nonFiniteValue: String)
        ] = [
            (
                "depth minimum",
                "\"minimum\":7.5",
                "\"minimum\":1e999"
            ),
            (
                "depth maximum",
                "\"maximum\":12.5",
                "\"maximum\":1e999"
            ),
        ]

        for measurement in invalidMeasurements {
            let fixture = try makeFixtureBundle { hangboardsURL in
                let boardURL = hangboardsURL.appendingPathComponent("fixture-model/board.json")
                try self.mutateBoard(at: boardURL) { board in
                    var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                    holds[0]["depth"] = ["range": ["minimum": 7.5, "maximum": 12.5]]
                    board["contacts"] = holds
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
                XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
            }
        }
    }

    func testStoreAcceptsFractionalEqualBoundDepthRange() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["depth"] = ["range": ["minimum": 7.5, "maximum": 7.5]]
                board["contacts"] = holds
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let hold = try XCTUnwrap(board.contacts.first)
        XCTAssertEqual(hold.depth, .range(.init(minimum: 7.5, maximum: 7.5)))
    }

    func testStoreDecodesForgeStyleCategoricalDepth() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["kind"] = "edge"
                holds[0]["shape"] = "flat"
                holds[0]["depth"] = ["category": "large"]
                board["contacts"] = holds
            }
        }
        defer { fixture.remove() }

        let hold = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first?.contacts.first)
        XCTAssertEqual(hold.shape, .flat)
        XCTAssertEqual(hold.depth, .category(.large))
    }

    func testStoreRejectsLegacyContactDepthRangeKey() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["depthRangeMillimeters"] = [
                    "lowerBound": 7.5,
                    "upperBound": 12.5,
                ]
                board["contacts"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
        }
    }

    func testStoreRejectsLegacyContactFeaturesKey() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["features"] = []
                board["contacts"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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
        let firstHold = try XCTUnwrap(board.contacts.first)
        XCTAssertEqual(board.manufacturer, "Alpha")
        XCTAssertEqual(board.name, "Alpha")
        let presentation = try XCTUnwrap(board.presentations.first)
        guard case .raster(let raster) = presentation.media else {
            return XCTFail("Expected schema-v3 raster media")
        }
        let pieces = try XCTUnwrap(raster.contactGeometry[firstHold.id])
        XCTAssertEqual(pieces.count, 2)
        let expectedFrame = CGRect(x: 0.05, y: 0.1, width: 0.4, height: 0.4)
        let frame = try XCTUnwrap(firstHold.resolvedFrame(in: presentation))
        XCTAssertEqual(frame.rect.origin.x, expectedFrame.origin.x, accuracy: 1e-12)
        XCTAssertEqual(frame.rect.origin.y, expectedFrame.origin.y, accuracy: 1e-12)
        XCTAssertEqual(frame.rect.size.width, expectedFrame.size.width, accuracy: 1e-12)
        XCTAssertEqual(frame.rect.size.height, expectedFrame.size.height, accuracy: 1e-12)
        XCTAssertNil(firstHold.depth)
        XCTAssertTrue(firstHold.gripTypes.isEmpty)
        XCTAssertNil(firstHold.fingerCapacity)
        XCTAssertNil(firstHold.handCapacity)
        XCTAssertNil(firstHold.shape)
        XCTAssertEqual(board.presentations.count, 1)
        XCTAssertEqual(presentation.id, "primary")
        XCTAssertEqual(presentation.name, "Primary")
        XCTAssertEqual(presentation.aspectRatio, 2)
        XCTAssertTrue(presentation.isDefault)
        XCTAssertEqual(raster.assetPath, "assets/primary.png")
        XCTAssertEqual(raster.contactGeometry["hold-left"]?.count, 2)
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
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
        }
    }

    func testStoreRejectsNullRequiredPresentationID() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["presentationID"] = NSNull()
                board["contacts"] = holds
            }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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
        XCTAssertEqual(board.contacts.map(\.id), ["hold-left", "hold-back"])
        XCTAssertEqual(board.presentations.map { $0.contactIDs }, [Set(["hold-left"]), Set(["hold-back"])])
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
                        "contactGeometry": self.fixtureHoldGeometry()
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
                        "contactGeometry": self.fixtureHoldGeometry()
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

    func testPositionResolverUsesResolvedSurfaceAndRejectsUnknownSurfaceOrHold() throws {
        let fixture = try makeMultiPresentationFixtureBundle(boardMutation: { board in
            board["positions"] = [["id": "front-pose", "presentationID": "front"],
                                  ["id": "back-pose", "presentationID": "back"]]
        })
        defer { fixture.remove() }
        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        let selection = BoardMapPresentationSelection(board: board, requestedPresentationID: "front",
            activeHoldID: nil, highlightedHoldIDs: ["hold-back"])
        XCTAssertEqual(BoardMapPresentationSelection.resolvePositionID(board: board,
            presentationID: selection.presentationID, activeHoldID: nil), "back-pose")
        XCTAssertEqual(BoardMapPresentationSelection.resolvePositionID(board: board,
            presentationID: "front", activeHoldID: "hold-left"), "front-pose")
        // Unknown presentations and cross-presentation holds resolve to no
        // position rather than borrowing another surface's membership.
        XCTAssertNil(BoardMapPresentationSelection.resolvePositionID(board: board,
            presentationID: "unpositioned", activeHoldID: nil))
        XCTAssertNil(BoardMapPresentationSelection.resolvePositionID(board: board,
            presentationID: "front", activeHoldID: "hold-back"))
        XCTAssertNil(BoardMapPresentationSelection.resolvePositionID(board: board,
            presentationID: "front", activeHoldID: "not-on-model"))
    }

    func testTwoBranchRejectsNonIdentifierPassageAndBranchIDs() throws {
        for mutations in [
            [["target": "board", "op": "replace", "path": ["presentations", 0, "media", "suspension", "branches", 0, "id"], "value": "invalid id"]],
            [["target": "board", "op": "replace", "path": ["presentations", 0, "media", "suspension", "passages", "left", 0, "id"], "value": "invalid id"],
             ["target": "board", "op": "replace", "path": ["presentations", 0, "media", "suspension", "branches", 0, "passageIDs", 0], "value": "invalid id"]],
        ] as [[[String: Any]]] {
            let fixture = try makeSharedModelParserParityFixtureBundle(["base": "twoBranchModel", "mutations": mutations])
            defer { fixture.remove() }
            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle))
        }
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
        let board = BoardRevision(
            id: "alias-fixture",
            revisionID: "test-fixture",
            manufacturer: "Example",
            name: "Alias fixture",
            subtitle: "",
            dimensions: "10 in × 5 in",
            aspectRatio: 2,
            contacts: [
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
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["handCapacity"] = 2
                board["contacts"] = holds
            }
        }
        defer { fixture.remove() }

        let hold = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first?.contacts.first)
        XCTAssertEqual(hold.handCapacity, 2)

        let invalidFixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["handCapacity"] = 3
                board["contacts"] = holds
            }
        }
        defer { invalidFixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: invalidFixture.bundle)) { error in
            XCTAssertEqual(
                error as? BoardPackageStoreError,
                .invalidPackage(
                    boardID: "fixture.board",
                    reason: "contact hold-left has an invalid hand capacity"
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
        let firstPiece = try XCTUnwrap(media.contactGeometry["hold-left"]?.first)

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

    /// Swift's discovery sort must match the shared non-ASCII ordering
    /// fixtures' expected package order.
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
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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
        let geometry = try XCTUnwrap(media.contactGeometry["hold-left"])
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
            XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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
        let frame = try XCTUnwrap(media.contactGeometry["hold-left"]?.first?.frame)
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
                    (board["contacts"] as? [[String: Any]])?.first
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
                board["contacts"] = supportedHolds
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                var left = template
                left["id"] = "gaston-left"
                left["name"] = "Left gaston"
                left["kind"] = "gaston"
                left["pairedContactID"] = "gaston-right"
                var right = template
                right["id"] = "gaston-right"
                right["name"] = "Right gaston"
                right["kind"] = "gaston"
                right["pairedContactID"] = "gaston-left"
                holds.append(contentsOf: [left, right])
                board["contacts"] = holds
                try self.replaceRasterHoldGeometry(
                    in: &board,
                    holdIDs: holds.compactMap { $0["id"] as? String }
                )
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(
            board.contacts.map { $0.kind.rawValue },
            ["jug", "edge", "pocket", "pinch", "sloper", "gaston", "gaston"]
        )
    }

    func testStoreAcceptsReciprocalGastonPairs() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                let template = try XCTUnwrap((board["contacts"] as? [[String: Any]])?.first)
                var left = template
                left["id"] = "gaston-left"
                left["name"] = "Left gaston"
                left["kind"] = "gaston"
                left["pairedContactID"] = "gaston-right"
                var right = template
                right["id"] = "gaston-right"
                right["name"] = "Right gaston"
                right["kind"] = "gaston"
                right["pairedContactID"] = "gaston-left"
                board["contacts"] = [left, right]
                try self.replaceRasterHoldGeometry(
                    in: &board,
                    holdIDs: ["gaston-left", "gaston-right"]
                )
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(board.contacts.map(\.kind), [.gaston, .gaston])
        XCTAssertEqual(board.contacts.map(\.pairedContactID), ["gaston-right", "gaston-left"])
    }

    func testStoreAcceptsReciprocalNonGastonPairs() throws {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                let template = try XCTUnwrap((board["contacts"] as? [[String: Any]])?.first)
                var left = template
                left["id"] = "edge-left"
                left["name"] = "Left edge"
                left["kind"] = "edge"
                left["side"] = "left"
                left["pairedContactID"] = "edge-right"
                var right = template
                right["id"] = "edge-right"
                right["name"] = "Right edge"
                right["kind"] = "edge"
                right["side"] = "right"
                right["pairedContactID"] = "edge-left"
                board["contacts"] = [left, right]
                try self.replaceRasterHoldGeometry(
                    in: &board,
                    holdIDs: ["edge-left", "edge-right"]
                )
            }
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)

        XCTAssertEqual(board.contacts.map(\.pairedContactID), ["edge-right", "edge-left"])
    }

    func testStoreRejectsInvalidGastonPairMetadata() throws {
        let invalidPairs: [(String, (inout [[String: Any]]) -> Void)] = [
            ("missing pair", { holds in
                holds[0]["kind"] = "gaston"
            }),
            ("invalid pair identifier", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedContactID"] = "not a valid identifier"
            }),
            ("explicit null pair on another kind", { holds in
                holds[0]["pairedContactID"] = NSNull()
            }),
            ("self pair", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedContactID"] = "gaston-left"
            }),
            ("unknown pair", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedContactID"] = "missing"
            }),
            ("non-gaston target", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedContactID"] = "gaston-right"
            }),
            ("non-reciprocal target", { holds in
                holds[0]["kind"] = "gaston"
                holds[0]["pairedContactID"] = "gaston-right"
                holds[1]["kind"] = "gaston"
                holds[1]["pairedContactID"] = "another-gaston"
            }),
        ]

        for (_, mutation) in invalidPairs {
            let fixture = try makeFixtureBundle { hangboardsURL in
                try self.mutateBoard(
                    at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
                ) { board in
                    let template = try XCTUnwrap((board["contacts"] as? [[String: Any]])?.first)
                    var left = template
                    left["id"] = "gaston-left"
                    left["name"] = "Left gaston"
                    var right = template
                    right["id"] = "gaston-right"
                    right["name"] = "Right gaston"
                    var holds = [left, right]
                    mutation(&holds)
                    board["contacts"] = holds
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
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                holds[0]["kind"] = "unsupported"
                board["contacts"] = holds
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
                        var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                        holds[0]["unexpected"] = true
                        board["contacts"] = holds
                    } else {
                        try self.mutateRasterGeometry(in: &board) { geometry in
                            geometry[0]["unexpected"] = true
                        }
                    }
                }
            }
            defer { fixture.remove() }

            XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
                XCTAssertMalformedJSON(error, resource: "Hangboards/fixture-model/board.json")
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
                            "contactGeometry": self.fixtureHoldGeometry()
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
                            "contactGeometry": self.fixtureHoldGeometry()
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
        XCTAssertEqual(board.contactIDs(inPosition: "front"), ["hold-left"])
        XCTAssertEqual(board.contactIDs(inPosition: "flipped"), ["hold-left"])
        XCTAssertEqual(board.transitionKind(from: "front", to: "front"), .same)
        XCTAssertEqual(board.transitionKind(from: "front", to: "flipped"), .seamless)
        XCTAssertEqual(board.transitionKind(from: "flipped", to: "front"), .setupRequired)
    }

    // This catches a loader that ignores authored model-position membership or
    // binds rotations to presentation IDs instead of position IDs.
    func testStoreDecodesModelOrientationAndExactPositionInventories() throws {
        let fixture = try makeOrientableModelFixtureBundle()
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .model(let media) = board.presentations[0].media else {
            return XCTFail("expected model media")
        }

        XCTAssertEqual(board.positions.map(\.contactIDs), [["hold-left"], ["hold-right"]])
        XCTAssertEqual(board.contactIDs(inPosition: "front"), ["hold-left"])
        XCTAssertEqual(board.contactIDs(inPosition: "reverse"), ["hold-right"])
        XCTAssertEqual(media.orientation?.pivot, "modelBoundsCenter")
        XCTAssertEqual(media.orientation?.rotations["front"], SIMD4(0, 0, 0, 1))
        XCTAssertEqual(media.orientation?.rotations["reverse"], SIMD4(0, 1, 0, 0))
    }

    // This catches permissive orientation parsing and partial inventories.
    // Orientation may coexist with suspension; suspension canonical poses govern rendering.
    func testStoreRejectsInvalidModelOrientationAndPositionInventory() throws {
        let mutations: [(String, (inout [String: Any]) throws -> Void, String)] = [
            ("wrong pivot", { board in
                self.mutateOrientation(in: &board) { $0["pivot"] = "boardOrigin" }
            }, "orientation pivot"),
            ("rotation inventory", { board in
                self.mutateOrientation(in: &board) { $0["rotations"] = ["front": [0, 0, 0, 1]] }
            }, "orientation rotations"),
            ("nonunit quaternion", { board in
                self.mutateOrientation(in: &board) { $0["rotations"] = ["front": [0, 0, 0, 2], "reverse": [0, 1, 0, 0]] }
            }, "orientation rotations"),
            ("noncanonical membership order", { board in
                var positions = try XCTUnwrap(board["positions"] as? [[String: Any]])
                positions[0]["contactIDs"] = ["hold-right", "hold-left"]
                positions[1]["contactIDs"] = []
                board["positions"] = positions
            }, "canonical board contact order")
        ]

        for (name, mutation, reason) in mutations {
            let fixture = try makeOrientableModelFixtureBundle(boardMutation: mutation)
            defer { fixture.remove() }
            assertStoreRejects(fixture.bundle, reasonContaining: reason)
        }
    }

    // This verifies that overlapping model position hold memberships are now accepted
    // (union-cover contract: holds may appear in multiple positions).
    func testStoreAcceptsOverlappingModelPositionHoldMemberships() throws {
        let fixture = try makeOrientableModelFixtureBundle { board in
            var positions = try XCTUnwrap(board["positions"] as? [[String: Any]])
            positions[1]["contactIDs"] = ["hold-left", "hold-right"]
            board["positions"] = positions
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        XCTAssertEqual(board.positions[0].contactIDs, ["hold-left"])
        XCTAssertEqual(board.positions[1].contactIDs, ["hold-left", "hold-right"])
    }

    func testStoreRejectsUnknownOrientationMember() throws {
        let fixture = try makeOrientableModelFixtureBundle { board in
            self.mutateOrientation(in: &board) { $0["unexpected"] = true }
        }
        defer { fixture.remove() }

        XCTAssertThrowsError(try BoardPackageStore(bundle: fixture.bundle)) { error in
            guard case BoardPackageStoreError.malformedJSON = error else {
                return XCTFail("Unexpected error: \(error)")
            }
        }
    }

    func testStoreParsesOrientationAndSuspensionIndependently() throws {
        let fixture = try makeOrientableModelFixtureBundle { board in
            var presentations = board["presentations"] as! [[String: Any]]
            var media = presentations[0]["media"] as! [String: Any]
            media["suspension"] = [
                "type": "singleCord",
                "attachment": [
                    "nodeID": "Body", "pointInModel": [0.5, 1.0, 0.05],
                    "provenance": "test",
                ],
                "anchor": [
                    "offsetFromBoardBounds": [0.0, 0.4, 0.0],
                    "visibility": "invisible", "provenance": "test",
                ],
                "cord": [
                    "restLength": 2.0, "radius": 0.002,
                    "material": "matteCord", "provenance": "test",
                ],
                "canonicalPoses": [
                    "front": [
                        "rotation": [0.0, 0.0, 0.0, 1.0],
                        "translation": [0.0, 0.0, 0.0],
                        "camera": ["viewDirection": [0.0, 0.0, -1.0], "fitPadding": 0.1],
                    ],
                    "reverse": [
                        "rotation": [0.0, 1.0, 0.0, 0.0],
                        "translation": [0.0, 0.0, 0.0],
                        "camera": ["viewDirection": [0.0, 0.0, -1.0], "fitPadding": 0.1],
                    ],
                ],
            ]
            presentations[0]["media"] = media
            board["presentations"] = presentations
        }
        defer { fixture.remove() }

        let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
        guard case .model(let media) = board.defaultPresentation.media else {
            return XCTFail("expected model media")
        }
        XCTAssertNotNil(media.orientation)
        XCTAssertNotNil(media.suspension)
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
                        "contactGeometry": self.fixtureHoldGeometry()
                    ],
                ],
                [
                    "id": "unused", "name": "Unused", "aspectRatio": 2,
                    "isDefault": false, "derivation": ["type": "original"],
                    "media": [
                        "type": "raster", "assetPath": "assets/unused.png",
                        "contactGeometry": [:]
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
                            "contactGeometry": self.fixtureHoldGeometry()
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
                            "contactGeometry": self.fixtureHoldGeometry()
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

    private func reusableFixtureBoard(named name: String) throws -> BoardRevision {
        let fixture = try reusableFixtureBundle(named: name)
        addTeardownBlock { fixture.remove() }
        return try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
    }

    private func reusableFixtureBundle(
        named name: String,
        descriptorRawMutation: @escaping (String) -> String = { $0 }
    ) throws -> FixtureBundle {
        let fixtures = try validationFixtures()
        let reusableFixtures = try XCTUnwrap(fixtures["reusableModelFixtures"] as? [String: Any])
        let reusableFixture = try XCTUnwrap(reusableFixtures[name] as? [String: Any])
        let board = try XCTUnwrap(reusableFixture["board"] as? [String: Any])
        let descriptor = try XCTUnwrap(reusableFixture["descriptor"] as? [String: Any])
        let assetBase64 = try XCTUnwrap(reusableFixture["assetBase64"] as? String)
        let modelBytes = try XCTUnwrap(Data(base64Encoded: assetBase64))

        let fixture = try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let assetsURL = packageURL.appendingPathComponent("assets")
            try FileManager.default.removeItem(at: assetsURL.appendingPathComponent("primary.png"))
            var boardJSON = String(
                decoding: try JSONSerialization.data(withJSONObject: board, options: [.sortedKeys]),
                as: UTF8.self
            )
            boardJSON = boardJSON.replacingOccurrences(
                of: #""translation":[-0.12,0,0]"#,
                with: #""translation":[-0.120000000,0.000000000,0.000000000]"#
            )
            boardJSON = boardJSON.replacingOccurrences(
                of: #""translation":[0,0,0]"#,
                with: #""translation":[0.000000000,0.000000000,0.000000000]"#
            )
            boardJSON = boardJSON.replacingOccurrences(
                of: #""translation":[0.12,0,0]"#,
                with: #""translation":[0.120000000,0.000000000,0.000000000]"#
            )
            try Data(boardJSON.utf8).write(to: packageURL.appendingPathComponent("board.json"))
            try modelBytes.write(to: assetsURL.appendingPathComponent("primary.usdz"))
            let descriptorJSON = String(
                decoding: try JSONSerialization.data(withJSONObject: descriptor, options: [.sortedKeys]),
                as: UTF8.self
            )
            try Data(descriptorRawMutation(descriptorJSON).utf8)
                .write(to: assetsURL.appendingPathComponent("primary.model.json"))
        }
        return fixture
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
                    primaryMedia["contactGeometry"] as? [String: [[String: Any]]]
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
                        "contactGeometry": ["hold-left": pieces]
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
                        "contactGeometry": ["hold-back": pieces]
                    ]
                ]]
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                var backHold = holds[0]
                backHold["id"] = "hold-back"
                backHold["name"] = "Back hold"
                holds.append(backHold)
                board["contacts"] = holds
                try boardMutation?(&board)
            }
            try mutateAssets?(assetsURL)
        }
    }

    private func makeDerivedRasterV3FixtureBundle(
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
                originalMedia["contactGeometry"] = self.fixtureDerivedHoldGeometry()
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
                        "contactGeometry": self.fixtureDerivedHoldGeometry(),
                    ],
                ])
                board["presentations"] = presentations
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                var rightHold = try XCTUnwrap(holds.first)
                rightHold["id"] = "hold-right"
                rightHold["name"] = "Right hold"
                holds.append(rightHold)
                board["contacts"] = holds
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

    private func makeModelFixtureBundle(
        modelSHA256Matches: Bool,
        boardID: String = "fixture.board",
        mutatePackage: ((URL) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        let fixtures = try validationFixtures()
        let model = try XCTUnwrap(fixtures["model"] as? [String: Any])
        var board = try XCTUnwrap(model["board"] as? [String: Any])
        board["id"] = boardID
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

    private func fixtureBundle(schemaVersion: Int) throws -> Bundle {
        let fixture = try makeFixtureBundle { hangboardsURL in
            try self.mutateBoard(
                at: hangboardsURL.appendingPathComponent("fixture-model/board.json")
            ) { board in
                board["schemaVersion"] = schemaVersion
            }
        }
        addTeardownBlock { fixture.remove() }
        return fixture.bundle
    }

    private func v3TwoBodyFixtureBundle() throws -> Bundle {
        let fixture = try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                board["schemaVersion"] = 3
                board["revisionID"] = "2026-09-contact-first"
                board["contacts"] = [
                    [
                        "id": "left-edge", "equipmentObjectID": "primary",
                        "name": "Left Edge", "kind": "edge",
                        "gripTypes": [],
                    ],
                    [
                        "id": "right-edge", "equipmentObjectID": "primary",
                        "name": "Right Edge", "kind": "edge",
                        "gripTypes": [],
                    ],
                ]
                board.removeValue(forKey: "holds")
            }
            try self.mutateJSONObject(
                at: packageURL.appendingPathComponent("assets/primary.model.json")
            ) { descriptor in
                descriptor["nodes"] = [
                    ["nodeID": "left-body", "role": "body"],
                    ["nodeID": "left-edge-node", "role": "contact", "contactID": "left-edge"],
                    ["nodeID": "right-body", "role": "body"],
                    ["nodeID": "right-edge-node", "role": "contact", "contactID": "right-edge"],
                ]
                descriptor["contacts"] = [
                    "left-edge": [
                        "nodeIDs": ["left-edge-node"],
                        "facePlaneAABB": ["min": [0.1, 0.2], "max": [0.4, 0.6]],
                        "center": [0.25, 0.4],
                    ],
                    "right-edge": [
                        "nodeIDs": ["right-edge-node"],
                        "facePlaneAABB": ["min": [0.6, 0.2], "max": [0.9, 0.6]],
                        "center": [0.75, 0.4],
                    ],
                ]
                descriptor.removeValue(forKey: "holds")
            }
        }
        addTeardownBlock { fixture.remove() }
        return fixture.bundle
    }

    private func makeOrientableModelFixtureBundle(
        boardMutation: ((inout [String: Any]) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        try makeModelFixtureBundle(modelSHA256Matches: true) { packageURL in
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("board.json")) { board in
                var holds = try XCTUnwrap(board["contacts"] as? [[String: Any]])
                var right = try XCTUnwrap(holds.first)
                right["id"] = "hold-right"
                right["name"] = "Right hold"
                holds.append(right)
                board["contacts"] = holds
                board["positions"] = [
                    ["id": "front", "presentationID": "primary", "contactIDs": ["hold-left"]],
                    ["id": "reverse", "presentationID": "primary", "contactIDs": ["hold-right"]]
                ]
                var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
                var media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
                media["orientation"] = [
                    "pivot": "modelBoundsCenter",
                    "rotations": [
                        "front": [0, 0, 0, 1],
                        "reverse": [0, 1, 0, 0]
                    ]
                ]
                presentations[0]["media"] = media
                board["presentations"] = presentations
                try boardMutation?(&board)
            }
            try self.mutateJSONObject(at: packageURL.appendingPathComponent("assets/primary.model.json")) { descriptor in
                var nodes = try XCTUnwrap(descriptor["nodes"] as? [[String: Any]])
                nodes.append(["nodeID": "Right", "role": "contact", "contactID": "hold-right"])
                descriptor["nodes"] = nodes
                var holds = try XCTUnwrap(descriptor["contacts"] as? [String: Any])
                holds["hold-right"] = [
                    "nodeIDs": ["Right"],
                    "facePlaneAABB": ["min": [0.6, 0.2], "max": [0.9, 0.6]],
                    "center": [0.75, 0.4]
                ]
                descriptor["contacts"] = holds
            }
        }
    }

    private func mutateOrientation(
        in board: inout [String: Any],
        mutation: (inout [String: Any]) -> Void
    ) {
        var presentations = board["presentations"] as! [[String: Any]]
        var media = presentations[0]["media"] as! [String: Any]
        var orientation = media["orientation"] as! [String: Any]
        mutation(&orientation)
        media["orientation"] = orientation
        presentations[0]["media"] = media
        board["presentations"] = presentations
    }

    private func makeSharedModelParserParityFixtureBundle(
        _ specification: [String: Any]
    ) throws -> FixtureBundle {
        let fixtures = try validationFixtures()
        let base = specification["base"] as? String ?? "model"
        let model = try XCTUnwrap(fixtures[base] as? [String: Any])
        var board = try copiedJSONObject(try XCTUnwrap(model["board"]))
        var descriptor = try copiedJSONObject(try XCTUnwrap(model["descriptor"]))
        let mutations = try XCTUnwrap(specification["mutations"] as? [[String: Any]])
        for mutation in mutations {
            let target = try XCTUnwrap(mutation["target"] as? String)
            switch target {
            case "board":
                try applySharedModelParserParityMutation(mutation, to: &board)
            case "descriptor":
                try applySharedModelParserParityMutation(mutation, to: &descriptor)
            default:
                throw NSError(
                    domain: "BoardPackageStoreTests",
                    code: 1,
                    userInfo: [NSLocalizedDescriptionKey: "unknown shared fixture target \(target)"]
                )
            }
        }
        let modelBase64 = try XCTUnwrap(model["assetBase64"] as? String)
        let modelBytes = try XCTUnwrap(Data(base64Encoded: modelBase64))
        let extraAssets = specification["extraAssets"] as? [[String: Any]] ?? []
        let boardObject = try XCTUnwrap(board as? [String: Any])
        var boardData = try JSONSerialization.data(withJSONObject: boardObject, options: [.sortedKeys])
        let presentations = try XCTUnwrap(boardObject["presentations"] as? [[String: Any]])
        let media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
        if let suspension = media["suspension"] as? [String: Any],
           let suspensionType = suspension["type"] as? String,
           ["twoBranchCord", "pairedLeadCord"].contains(suspensionType) {
            let serializedSuspension = try (
                suspensionType == "twoBranchCord"
                    ? serializedTwoBranchSuspension(suspension)
                    : serializedPairedLeadSuspension(suspension)
            )
            try replaceSerializedSuspension(
                in: &boardData,
                matching: try JSONSerialization.data(withJSONObject: suspension, options: [.sortedKeys]),
                with: serializedSuspension
            )
        }
        if specification["reorderTwoBranchSuspensionMembers"] as? Bool == true {
            let suspension = try XCTUnwrap(media["suspension"] as? [String: Any])
            let orderedKeys = ["type", "passages", "branches", "anchor", "canonicalPoses"]
            guard Set(suspension.keys) == Set(orderedKeys) else {
                throw NSError(
                    domain: "BoardPackageStoreTests",
                    code: 1,
                    userInfo: [NSLocalizedDescriptionKey: "unexpected two-branch suspension members"]
                )
            }

            try replaceSerializedSuspension(
                in: &boardData,
                matching: try serializedTwoBranchSuspension(suspension),
                with: try serializedTwoBranchSuspension(
                    suspension,
                    memberOrder: ["anchor", "branches", "canonicalPoses", "passages", "type"]
                )
            )
        }
        if specification["reorderPairedLeadSuspensionMembers"] as? Bool == true {
            let suspension = try XCTUnwrap(media["suspension"] as? [String: Any])
            let orderedKeys = ["type", "attachments", "passages", "anchor", "cord", "canonicalPoses"]
            guard Set(suspension.keys) == Set(orderedKeys) else {
                throw NSError(
                    domain: "BoardPackageStoreTests",
                    code: 1,
                    userInfo: [NSLocalizedDescriptionKey: "unexpected paired-lead suspension members"]
                )
            }
            try replaceSerializedSuspension(
                in: &boardData,
                matching: try serializedPairedLeadSuspension(suspension),
                with: try serializedPairedLeadSuspension(
                    suspension,
                    memberOrder: ["anchor", "attachments", "canonicalPoses", "cord", "passages", "type"]
                )
            )
        }
        if specification["reorderPairedLeadAnchorMembers"] as? Bool == true {
            let suspension = try XCTUnwrap(media["suspension"] as? [String: Any])
            try replaceSerializedSuspension(
                in: &boardData,
                matching: try serializedPairedLeadSuspension(suspension),
                with: try serializedPairedLeadSuspension(
                    suspension,
                    anchorMemberOrder: ["visibility", "offsetFromBoardBounds", "provenance"]
                )
            )
        }
        if specification["reorderPairedLeadCordMembers"] as? Bool == true {
            let suspension = try XCTUnwrap(media["suspension"] as? [String: Any])
            try replaceSerializedSuspension(
                in: &boardData,
                matching: try serializedPairedLeadSuspension(suspension),
                with: try serializedPairedLeadSuspension(
                    suspension,
                    cordMemberOrder: ["radius", "restLength", "material", "provenance"]
                )
            )
        }
        boardData = replacingRawNonfiniteSentinel(in: boardData)
        var descriptorData = try JSONSerialization.data(withJSONObject: descriptor, options: [.sortedKeys])
        descriptorData = replacingRawNonfiniteSentinel(in: descriptorData)

        return try makeFixtureBundle { hangboardsURL in
            let packageURL = hangboardsURL.appendingPathComponent("fixture-model")
            let assetsURL = packageURL.appendingPathComponent("assets")
            try FileManager.default.removeItem(at: assetsURL.appendingPathComponent("primary.png"))
            try boardData.write(to: packageURL.appendingPathComponent("board.json"))
            try descriptorData.write(to: assetsURL.appendingPathComponent("primary.model.json"))
            try modelBytes.write(to: assetsURL.appendingPathComponent("primary.usdz"))
            if specification["duplicateCanonicalPoseKey"] as? Bool == true {
                let presentations = try XCTUnwrap(boardObject["presentations"] as? [[String: Any]])
                let media = try XCTUnwrap(presentations[0]["media"] as? [String: Any])
                let suspension = try XCTUnwrap(media["suspension"] as? [String: Any])
                let canonicalPoses = try XCTUnwrap(suspension["canonicalPoses"] as? [String: Any])
                let pose = try XCTUnwrap(canonicalPoses["primary"])
                let poseObject = try XCTUnwrap(pose as? [String: Any])
                let poseData: Data
                if suspension["type"] as? String == "twoBranchCord" {
                    poseData = try self.serializedTwoBranchPose(poseObject)
                } else {
                    poseData = try JSONSerialization.data(withJSONObject: poseObject, options: [.sortedKeys])
                }
                let poseJSON = String(decoding: poseData, as: UTF8.self)
                let boardJSON = String(decoding: boardData, as: UTF8.self)
                let needle = "\"canonicalPoses\":{\"primary\":\(poseJSON)}"
                let replacement = "\"canonicalPoses\":{\"primary\":\(poseJSON),\"primary\":\(poseJSON)}"
                let duplicateBoardJSON: String
                if boardJSON.contains(needle) {
                    duplicateBoardJSON = boardJSON.replacingOccurrences(of: needle, with: replacement, options: [], range: nil)
                } else {
                    let prefix = "\"canonicalPoses\":{\"primary\":\(poseJSON),\""
                    XCTAssertTrue(boardJSON.contains(prefix))
                    duplicateBoardJSON = boardJSON.replacingOccurrences(
                        of: prefix,
                        with: "\"canonicalPoses\":{\"primary\":\(poseJSON),\"primary\":\(poseJSON),\"",
                        options: [],
                        range: nil
                    )
                }
                try duplicateBoardJSON.data(using: .utf8)!
                    .write(to: packageURL.appendingPathComponent("board.json"))
            }
            for extraAsset in extraAssets {
                let path = try XCTUnwrap(extraAsset["path"] as? String)
                let base64 = try XCTUnwrap(extraAsset["base64"] as? String)
                let bytes = try XCTUnwrap(Data(base64Encoded: base64))
                let url = packageURL.appendingPathComponent(path)
                try FileManager.default.createDirectory(
                    at: url.deletingLastPathComponent(),
                    withIntermediateDirectories: true
                )
                try bytes.write(to: url)
            }
        }
    }

    private func replacingRawNonfiniteSentinel(in data: Data) -> Data {
        var result = data
        let sentinel = Data(#""__raw_nonfinite_number_1e999__""#.utf8)
        let replacement = Data("1e999".utf8)
        while let range = result.range(of: sentinel) {
            result.replaceSubrange(range, with: replacement)
        }
        return result
    }

    private func replaceSerializedSuspension(
        in boardData: inout Data,
        matching original: Data,
        with replacement: Data
    ) throws {
        var needle = Data(#""suspension":"#.utf8)
        needle.append(original)
        var replacementBytes = Data(#""suspension":"#.utf8)
        replacementBytes.append(replacement)
        let range = try XCTUnwrap(boardData.range(of: needle))
        boardData.replaceSubrange(range, with: replacementBytes)
    }

    private func serializedTwoBranchSuspension(
        _ suspension: [String: Any],
        memberOrder: [String] = ["type", "passages", "branches", "anchor", "canonicalPoses"]
    ) throws -> Data {
        var serializedValues: [String: Data] = [:]
        if let passages = suspension["passages"] as? [String: Any] {
            serializedValues["passages"] = try serializedTwoBranchPassages(passages)
        }
        if let branches = suspension["branches"] as? [Any] {
            serializedValues["branches"] = try serializedJSONArray(branches.map { branch in
                if let object = branch as? [String: Any] {
                    return try self.serializedTwoBranchBranch(object)
                }
                return try JSONSerialization.data(withJSONObject: branch, options: [.sortedKeys, .fragmentsAllowed])
            })
        }
        if let anchor = suspension["anchor"] as? [String: Any] {
            serializedValues["anchor"] = try serializedTwoBranchAnchor(anchor)
        }
        if let poses = suspension["canonicalPoses"] as? [String: Any] {
            serializedValues["canonicalPoses"] = try serializedTwoBranchCanonicalPoses(poses)
        }
        return try orderedJSONObjectData(
            suspension,
            keys: memberOrder,
            serializedValues: serializedValues
        )
    }

    private func serializedPairedLeadSuspension(
        _ suspension: [String: Any],
        memberOrder: [String] = ["type", "attachments", "passages", "anchor", "cord", "canonicalPoses"],
        anchorMemberOrder: [String] = ["offsetFromBoardBounds", "visibility", "provenance"],
        cordMemberOrder: [String] = ["restLength", "radius", "material", "provenance"]
    ) throws -> Data {
        let attachments = try XCTUnwrap(suspension["attachments"] as? [Any])
        let passages = suspension["passages"] as? [String: Any]
        let anchor = try XCTUnwrap(suspension["anchor"] as? [String: Any])
        let cord = try XCTUnwrap(suspension["cord"] as? [String: Any])
        let poses = try XCTUnwrap(suspension["canonicalPoses"] as? [String: Any])
        var serializedValues: [String: Data] = [
            "attachments": try serializedJSONArray(attachments.map {
                let attachment = try XCTUnwrap($0 as? [String: Any])
                return try orderedJSONObjectData(
                    attachment,
                    keys: attachment["contactPointsInModel"] == nil
                        ? ["id", "nodeID", "pointInModel", "provenance"]
                        : ["id", "nodeID", "pointInModel", "contactPointsInModel", "provenance"]
                )
            }),
            "anchor": try orderedJSONObjectData(
                anchor,
                keys: anchorMemberOrder
            ),
            "cord": try orderedJSONObjectData(
                cord,
                keys: cordMemberOrder
            ),
            "canonicalPoses": try serializedTwoBranchCanonicalPoses(poses),
        ]
        if let passages {
            serializedValues["passages"] = try serializedTwoBranchPassages(passages)
        }
        return try orderedJSONObjectData(
            suspension,
            keys: memberOrder,
            serializedValues: serializedValues
        )
    }

    private func serializedTwoBranchPassages(_ passages: [String: Any]) throws -> Data {
        let left = try XCTUnwrap(passages["left"] as? [Any])
        let right = try XCTUnwrap(passages["right"] as? [Any])
        return try orderedJSONObjectData(
            passages,
            keys: ["left", "right"],
            serializedValues: [
                "left": try serializedJSONArray(left.map {
                    try self.serializedTwoBranchPassage(try XCTUnwrap($0 as? [String: Any]))
                }),
                "right": try serializedJSONArray(right.map {
                    try self.serializedTwoBranchPassage(try XCTUnwrap($0 as? [String: Any]))
                }),
            ]
        )
    }

    private func serializedTwoBranchPassage(_ passage: [String: Any]) throws -> Data {
        let pointKeys = passage["pointInModel"] != nil
            ? ["pointInModel"] : ["entryPointInModel", "exitPointInModel"]
        return try orderedJSONObjectData(
            passage,
            keys: ["id", "nodeID"] + pointKeys + ["provenance"]
        )
    }

    private func serializedTwoBranchBranch(_ branch: [String: Any]) throws -> Data {
        let contactKeys = branch["entryContactPoints"] != nil
            ? ["entryContactPoints", "exteriorContactPoints", "exitContactPoints"] : []
        return try orderedJSONObjectData(
            branch,
            keys: ["id", "passageIDs"] + contactKeys + ["restLength", "radius", "material", "provenance"]
        )
    }

    private func serializedTwoBranchAnchor(_ anchor: [String: Any]) throws -> Data {
        try orderedJSONObjectData(
            anchor,
            keys: ["offsetFromBoardBounds", "visibility", "provenance"]
        )
    }

    private func serializedTwoBranchCanonicalPoses(_ poses: [String: Any]) throws -> Data {
        let preferredOrder = ["primary", "secondary", "tertiary", "quaternary"]
        let poseKeys = preferredOrder.filter { poses[$0] != nil }
            + poses.keys.filter { !preferredOrder.contains($0) }.sorted()
        var serializedPoses: [String: Data] = [:]
        for key in poseKeys {
            serializedPoses[key] = try serializedTwoBranchPose(
                try XCTUnwrap(poses[key] as? [String: Any])
            )
        }
        return try orderedJSONObjectData(poses, keys: poseKeys, serializedValues: serializedPoses)
    }

    private func serializedTwoBranchPose(_ pose: [String: Any]) throws -> Data {
        let camera = try XCTUnwrap(pose["camera"] as? [String: Any])
        return try orderedJSONObjectData(
            pose,
            keys: ["rotation", "translation", "camera", "attachmentPoints", "cordContactPoints"].filter { pose[$0] != nil },
            serializedValues: ["camera": try orderedJSONObjectData(
                camera,
                keys: ["viewDirection", "fitPadding"]
            )]
        )
    }

    private func orderedJSONObjectData(
        _ object: [String: Any],
        keys: [String],
        serializedValues: [String: Data] = [:]
    ) throws -> Data {
        let orderedKeys = keys.filter { object[$0] != nil }
            + object.keys.filter { !keys.contains($0) }.sorted()
        let members = try orderedKeys.map { key -> String in
            let keyData = try JSONSerialization.data(withJSONObject: key, options: [.fragmentsAllowed])
            let valueData = try serializedValues[key] ?? JSONSerialization.data(
                withJSONObject: try XCTUnwrap(object[key]),
                options: [.sortedKeys, .fragmentsAllowed]
            )
            return String(decoding: keyData, as: UTF8.self) + ":" + String(decoding: valueData, as: UTF8.self)
        }
        return Data(("{" + members.joined(separator: ",") + "}").utf8)
    }

    private func serializedJSONArray(_ elements: [Data]) throws -> Data {
        Data(("[" + elements.map { String(decoding: $0, as: UTF8.self) }.joined(separator: ",") + "]").utf8)
    }

    private func copiedJSONObject(_ value: Any) throws -> Any {
        try JSONSerialization.jsonObject(
            with: JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        )
    }

    private func applySharedModelParserParityMutation(
        _ mutation: [String: Any],
        to document: inout Any
    ) throws {
        let operation = try XCTUnwrap(mutation["op"] as? String)
        let path = try XCTUnwrap(mutation["path"] as? [Any])
        try mutateSharedJSONObject(
            &document,
            path: ArraySlice(path),
            operation: operation,
            replacement: mutation["value"]
        )
    }

    private func mutateSharedJSONObject(
        _ document: inout Any,
        path: ArraySlice<Any>,
        operation: String,
        replacement: Any?
    ) throws {
        let component = try XCTUnwrap(path.first)
        if path.count == 1 {
            if let key = component as? String, var object = document as? [String: Any] {
                switch operation {
                case "replace":
                    object[key] = try XCTUnwrap(replacement)
                case "append":
                    var values = try XCTUnwrap(object[key] as? [Any])
                    values.append(try XCTUnwrap(replacement))
                    object[key] = values
                default:
                    throw NSError(
                        domain: "BoardPackageStoreTests",
                        code: 1,
                        userInfo: [NSLocalizedDescriptionKey: "unsupported object mutation \(operation)"]
                    )
                }
                document = object
                return
            }
            if let index = component as? Int, var values = document as? [Any] {
                switch operation {
                case "replace":
                    values[index] = try XCTUnwrap(replacement)
                case "remove":
                    values.remove(at: index)
                default:
                    throw NSError(
                        domain: "BoardPackageStoreTests",
                        code: 1,
                        userInfo: [NSLocalizedDescriptionKey: "unsupported array mutation \(operation)"]
                    )
                }
                document = values
                return
            }
            throw NSError(
                domain: "BoardPackageStoreTests",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "invalid shared fixture terminal path"]
            )
        }

        if let key = component as? String, var object = document as? [String: Any] {
            var child = try XCTUnwrap(object[key])
            try mutateSharedJSONObject(
                &child,
                path: path.dropFirst(),
                operation: operation,
                replacement: replacement
            )
            object[key] = child
            document = object
            return
        }
        if let index = component as? Int, var values = document as? [Any] {
            var child = values[index]
            try mutateSharedJSONObject(
                &child,
                path: path.dropFirst(),
                operation: operation,
                replacement: replacement
            )
            values[index] = child
            document = values
            return
        }
        throw NSError(
            domain: "BoardPackageStoreTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "invalid shared fixture path"]
        )
    }

    private func makeRasterV3FixtureBundle(
        mutateBoard: ((inout [String: Any]) throws -> Void)? = nil
    ) throws -> FixtureBundle {
        let fixtures = try validationFixtures()
        let model = try XCTUnwrap(fixtures["model"] as? [String: Any])
        var board = try XCTUnwrap(model["board"] as? [String: Any])
        var presentations = try XCTUnwrap(board["presentations"] as? [[String: Any]])
        presentations[0]["media"] = [
            "type": "raster",
            "assetPath": "assets/primary.png",
            "contactGeometry": [
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
        let holds = try XCTUnwrap(descriptor["contacts"] as? [String: Any])
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
                "schemaVersion": 3,
                "id": package.id,
                "revisionID": "2026-09-contact-first",
                "manufacturer": package.manufacturer,
                "name": package.name,
                "subtitle": "A physical fixture board.",
                "productURL": "https://example.com/\(package.id)",
                "dimensions": "20 × 10 cm",
                "aspectRatio": 2,
                "equipmentObjects": [["id": "primary"]],
                "presentations": [[
                    "id": "primary",
                    "name": "Primary",
                    "aspectRatio": 2,
                    "isDefault": true,
                    "derivation": ["type": "original"],
                    "media": [
                        "type": "raster",
                        "assetPath": "assets/primary.png",
                        "contactGeometry": [
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
                "contacts": [[
                    "id": "hold-left",
                    "equipmentObjectID": "primary",
                    "name": "Left hold",
                    "kind": "jug",
                    "gripTypes": []
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
        var holdGeometry = try XCTUnwrap(media["contactGeometry"] as? [String: [[String: Any]]])
        var geometry = try XCTUnwrap(holdGeometry[holdID])
        try mutation(&geometry)
        holdGeometry[holdID] = geometry
        media["contactGeometry"] = holdGeometry
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
        let holdGeometry = try XCTUnwrap(media["contactGeometry"] as? [String: [[String: Any]]])
        let pieces = try XCTUnwrap(holdGeometry.values.first)
        media["contactGeometry"] = Dictionary(
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

    private func replaceDerivedCornerRadiusTokens(
        in fixture: FixtureBundle,
        source sourceToken: String,
        derived derivedToken: String
    ) throws {
        let boardURL = fixture.rootURL.appendingPathComponent(
            "Hangboards/fixture-model/board.json"
        )
        let geometry = try JSONSerialization.data(
            withJSONObject: fixtureDerivedHoldGeometry(),
            options: [.sortedKeys]
        )
        let canonicalToken = #""cornerRadiusFraction":0.20000000000000001"#
        let sourceGeometry = Data(
            String(decoding: geometry, as: UTF8.self)
                .replacingOccurrences(
                    of: canonicalToken,
                    with: #""cornerRadiusFraction":\#(sourceToken)"#
                )
                .utf8
        )
        let derivedGeometry = Data(
            String(decoding: geometry, as: UTF8.self)
                .replacingOccurrences(
                    of: canonicalToken,
                    with: #""cornerRadiusFraction":\#(derivedToken)"#
                )
                .utf8
        )
        XCTAssertNotEqual(sourceGeometry, geometry)
        XCTAssertNotEqual(derivedGeometry, geometry)
        try replaceTwoOccurrences(
            of: geometry,
            firstReplacement: sourceGeometry,
            secondReplacement: derivedGeometry,
            in: boardURL
        )
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
        depth: HoldDepth? = nil,
        presentationID _: String = BoardPresentation.primaryID
    ) -> PhysicalContact {
        PhysicalContact(
            id: id,
            name: id,
            kind: kind,
            fingerCapacity: fingerCapacity,
            handCapacity: handCapacity,
            depth: depth ?? sizeMillimeters.map { .range(.init(minimum: $0, maximum: $0)) },
            gripTypes: Set(gripType.map { [$0] } ?? [])
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
                [BoardContactPiece(
                    id: "\(holdID)-piece",
                    contactID: holdID,
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
            media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry))
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

private func makeBoardModelFixtureScene() -> SCNScene {
    let scene = SCNScene()
    for (nodeID, size, position) in [
        ("Body", SIMD3<Float>(1, 1, 0.1), SIMD3<Float>(0.5, 0.5, 0.05)),
        ("Left", SIMD3<Float>(0.3, 0.4, 0.1), SIMD3<Float>(0.25, 0.4, 0.05))
    ] {
        let geometry = SCNBox(width: CGFloat(size.x), height: CGFloat(size.y), length: CGFloat(size.z), chamferRadius: 0)
        geometry.firstMaterial = SCNMaterial()
        let node = SCNNode(geometry: geometry)
        node.name = nodeID
        node.simdPosition = position
        scene.rootNode.addChildNode(node)
    }
    return scene
}

private final class TestBoardModelResourceRequest: BoardModelResourceRequesting {
    let progress = Progress(totalUnitCount: 1)
    private let beginAction: () throws -> Void
    private let endAction: () -> Void

    init(begin: @escaping () throws -> Void, end: @escaping () -> Void) {
        self.beginAction = begin
        self.endAction = end
    }

    func beginAccessingResources() async throws {
        try beginAction()
    }

    func endAccessingResources() {
        endAction()
    }
}

private final class ModelLoadConcurrencyTracker: @unchecked Sendable {
    private let lock = NSLock()
    private var active = 0
    private var peakActive = 0

    func enter() {
        lock.lock()
        active += 1
        peakActive = max(peakActive, active)
        lock.unlock()
    }

    func exit() {
        lock.lock()
        active -= 1
        lock.unlock()
    }

    var current: Int {
        lock.lock()
        defer { lock.unlock() }
        return active
    }

    var peak: Int {
        lock.lock()
        defer { lock.unlock() }
        return peakActive
    }
}
