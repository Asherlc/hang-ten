import XCTest
@testable import HangTen

final class BoardTargetSubstitutionTests: XCTestCase {
    func testBoardHoldDepthMeasurementRejectsFixedAndVariableDepths() {
        let measurement = BoardHold.DepthMeasurement(
            sizeMillimeters: 7.5,
            depthRangeMillimeters: 7.5...12.5
        )

        XCTAssertNil(measurement)
    }

    private func hold(
        id: String,
        kind: HoldKind = .edge,
        feature: HoldFeature? = nil,
        fingerCapacity: Int? = nil,
        sizeMillimeters: Double? = nil,
        depthRangeMillimeters: ClosedRange<Double>? = nil,
        x: Double = 0,
        y: Double = 0,
        width: Double = 0.1,
        height: Double = 0.1
    ) -> BoardHold {
        BoardHold(
            id: id,
            name: id,
            shortLabel: id,
            detail: id,
            kind: kind,
            frame: HoldFrame(x: x, y: y, width: width, height: height),
            sizeMillimeters: sizeMillimeters,
            fingerCapacity: fingerCapacity,
            depthRangeMillimeters: depthRangeMillimeters,
            features: feature.map { [$0] }
        )
    }

    private func board(holds: [BoardHold]) -> TrainingBoard {
        TrainingBoard(
            id: "test-board",
            manufacturer: "Test",
            name: "Test Board",
            subtitle: "",
            dimensions: "30x60",
            aspectRatio: 0.5,
            holds: holds,
            productURL: URL(string: "https://example.com")!,
            photoAssetName: nil
        )
    }

    func testExactMatchStillWorks() {
        let board = board(holds: [
            hold(id: "a", kind: .edge, feature: .smallEdge)
        ])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["a"])
    }

    func testSameKindDifferentFeature() {
        let board = board(holds: [
            hold(id: "a", kind: .edge, feature: .mediumEdge)
        ])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["a"])
    }

    func testUntaggedThreeFingerPocketSubstitutionKeepsOneHoldPerHand() {
        let board = board(holds: [
            hold(id: "left-29", kind: .pocket, fingerCapacity: 3, x: 0.1),
            hold(id: "left-19", kind: .pocket, fingerCapacity: 3, x: 0.3),
            hold(id: "right-29", kind: .pocket, fingerCapacity: 3, x: 0.7),
            hold(id: "right-19", kind: .pocket, fingerCapacity: 3, x: 0.9)
        ])

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(
                for: .kind(.pocket, fingerCapacity: 3),
                on: board
            ),
            ["left-29", "right-29"]
        )
    }

    func testGenericPocketFallbackOnCompactIIUsesMirroredThreeFingerPair() {
        let compactII = BoardCatalog.board(for: "metolius.wood-grips-compact-ii")

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(
                for: .kind(.pocket),
                on: compactII
            ),
            ["pocket-29-three-left", "pocket-29-three-right"]
        )
    }

    func testGenericPocketKindSelectsOneMirroredCapacityPair() {
        let board = board(holds: [
            hold(
                id: "two-left-off-row",
                kind: .pocket,
                fingerCapacity: 2,
                x: 0.1,
                y: 0.1
            ),
            hold(
                id: "two-right-off-row",
                kind: .pocket,
                fingerCapacity: 2,
                x: 0.8,
                y: 0.5
            ),
            hold(
                id: "three-left-mirrored",
                kind: .pocket,
                fingerCapacity: 3,
                x: 0.2,
                y: 0.2
            ),
            hold(
                id: "three-right-mirrored",
                kind: .pocket,
                fingerCapacity: 3,
                x: 0.7,
                y: 0.2
            )
        ])

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board),
            ["three-left-mirrored", "three-right-mirrored"]
        )
    }

    func testGenericPocketKindSelectsMatchingAsymmetricPair() {
        let board = board(holds: [
            hold(
                id: "left-three",
                kind: .pocket,
                fingerCapacity: 3,
                x: 0.1,
                y: 0.2
            ),
            hold(
                id: "right-three",
                kind: .pocket,
                fingerCapacity: 3,
                x: 0.65,
                y: 0.2
            )
        ])

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board),
            ["left-three", "right-three"]
        )
    }

    func testGenericPocketFallbackDoesNotPairCrossRowMismatchedShapeCandidates() {
        let board = board(holds: [
            hold(
                id: "left-off-row",
                kind: .pocket,
                fingerCapacity: 3,
                x: 0.1,
                y: 0.1
            ),
            hold(
                id: "right-off-row",
                kind: .pocket,
                fingerCapacity: 3,
                x: 0.65,
                y: 0.5,
                width: 0.2,
                height: 0.2
            )
        ])

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board),
            ["left-off-row"]
        )
    }

    func testGenericPocketFallbackDoesNotPairUnknownCapacities() {
        let board = board(holds: [
            hold(id: "left-unknown", kind: .pocket, x: 0.2, y: 0.2),
            hold(id: "right-unknown", kind: .pocket, x: 0.7, y: 0.2)
        ])

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board),
            ["left-unknown"]
        )
    }

    func testGenericPocketKindCenterOnlyReturnsUnresolved() {
        let board = board(holds: [
            hold(
                id: "center",
                kind: .pocket,
                fingerCapacity: 4,
                x: 0.45,
                width: 0.1
            )
        ])

        XCTAssertTrue(
            BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board).isEmpty
        )
    }

    func testGenericPocketFallbackSkipsCenteredFirstCandidateWhenNoPair() {
        let board = board(holds: [
            hold(id: "center", kind: .pocket, fingerCapacity: 4, x: 0.45),
            hold(id: "left", kind: .pocket, fingerCapacity: 3, x: 0.1)
        ])

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board),
            ["left"]
        )
    }

    func testGenericPocketFallbackDoesNotPairACenteredPocketAsTheOtherHand() {
        let board = board(holds: [
            hold(id: "left-three", kind: .pocket, fingerCapacity: 3, x: 0.1),
            hold(id: "center-four", kind: .pocket, fingerCapacity: 4, x: 0.46)
        ])

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board),
            ["left-three"]
        )
    }

    func testGenericPocketFallbackPrefersSameRowMirroredPairOverCrossRowPair() {
        let board = board(holds: [
            hold(id: "left-same-row", kind: .pocket, fingerCapacity: 3, x: 0.1, y: 0.2),
            hold(id: "right-same-row", kind: .pocket, fingerCapacity: 3, x: 0.8, y: 0.2),
            hold(id: "left-cross-row", kind: .pocket, fingerCapacity: 3, x: 0.2, y: 0.8),
            hold(id: "right-cross-row", kind: .pocket, fingerCapacity: 3, x: 0.7, y: 0.1)
        ])

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board),
            ["left-same-row", "right-same-row"]
        )
    }

    func testSameKindEdgeCandidateOutranksPocketSubstitution() {
        let board = board(holds: [
            hold(id: "edge", kind: .edge, feature: .mediumEdge),
            hold(id: "pocket", kind: .pocket)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.smallEdge),
            on: board
        )

        XCTAssertEqual(result, ["edge"])
    }

    func testCrossKindMatchingFingerCapacity() {
        let board = board(holds: [
            hold(id: "e2", kind: .edge, feature: nil, fingerCapacity: 2)
        ])
        let target = HoldTarget.kind(.pocket, fingerCapacity: 2)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["e2"])
    }

    func testCrossKindMismatchedFingerCapacityExcluded() {
        let board = board(holds: [
            hold(id: "e4", kind: .edge, feature: nil, fingerCapacity: 4)
        ])
        let target = HoldTarget.kind(.pocket, fingerCapacity: 2)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
    }

    func testPocketKindWithoutFingerCapacityDoesNotSubstituteEdges() {
        let board = board(holds: [
            hold(id: "e2", kind: .edge, feature: nil, fingerCapacity: 2)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board)

        XCTAssertTrue(result.isEmpty)
    }

    func testPocketKindWithoutFingerCapacityResolvesOnlyPockets() {
        let board = board(holds: [
            hold(id: "edge", kind: .edge),
            hold(id: "pocket", kind: .pocket)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(for: .kind(.pocket), on: board)

        XCTAssertEqual(result, ["pocket"])
    }

    func testFeatureTargetCanUseExistingCapacityAgnosticFallback() {
        let board = board(holds: [
            hold(id: "fallback-edge", feature: .largeEdge, fingerCapacity: 4),
            hold(id: "unrelated-jug", kind: .jug)
        ])
        let target = HoldTarget.feature(
            .smallEdge,
            fingerCapacity: 2,
            fallback: .largeEdge
        )

        let result = BoardTargetResolver.resolveHoldIDs(for: target, on: board)

        XCTAssertEqual(result, ["fallback-edge"])
    }

    func testResolveHoldIDsPrefersExactCapacityFallbackOverMismatchedFallbackAndWrongPocket() {
        let board = board(holds: [
            hold(id: "wrong-capacity-pocket", kind: .pocket, fingerCapacity: 4, x: 0.1),
            hold(id: "mismatched-first-fallback", feature: .mediumEdge, fingerCapacity: 4),
            hold(id: "exact-later-fallback", feature: .largeEdge, fingerCapacity: 2)
        ])
        let target = HoldTarget.kind(
            .pocket,
            fallbacks: [.mediumEdge, .largeEdge],
            fingerCapacity: 2
        )

        XCTAssertEqual(
            BoardTargetResolver.resolveHoldIDs(for: target, on: board),
            ["exact-later-fallback"]
        )
    }

    func testResolveHoldIDsUsesCapacityAgnosticPocketFallbackBeforeWrongCapacityPocket() {
        let board = board(holds: [
            hold(id: "wrong-capacity-pocket", kind: .pocket, fingerCapacity: 4, x: 0.1),
            hold(id: "declared-fallback", feature: .largeEdge, fingerCapacity: 4)
        ])
        let target = HoldTarget.kind(
            .pocket,
            fingerCapacity: 2,
            fallback: .largeEdge
        )

        XCTAssertEqual(
            BoardTargetResolver.resolveHoldIDs(for: target, on: board),
            ["declared-fallback"]
        )
    }

    func testResolveHoldIDsDoesNotBroadenCapacityAgnosticFallbackForOtherKinds() {
        let board = board(holds: [
            hold(id: "mismatched-fallback", feature: .largeEdge, fingerCapacity: 4)
        ])
        let target = HoldTarget.kind(
            .edge,
            fingerCapacity: 2,
            fallback: .largeEdge
        )

        XCTAssertTrue(BoardTargetResolver.resolveHoldIDs(for: target, on: board).isEmpty)
    }

    func testSubstitutionUsesClosestMatchForExplicitEdgeFallback() {
        let board = board(holds: [
            hold(id: "generic-edge", kind: .edge, feature: nil)
        ])
        let target = HoldTarget.kind(
            .pocket,
            fingerCapacity: 2,
            fallback: .mediumEdge
        )

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertEqual(result, ["generic-edge"])
    }

    func testCapacityQualifiedPocketUsesDeclaredFallbackBeforeWrongCapacityPocket() {
        let board = board(holds: [
            hold(id: "wrong-capacity-pocket", kind: .pocket, fingerCapacity: 4, x: 0.1),
            hold(id: "declared-fallback-edge", kind: .edge, feature: .largeEdge, fingerCapacity: 4)
        ])
        let target = HoldTarget.kind(
            .pocket,
            fingerCapacity: 2,
            fallback: .largeEdge
        )

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: target, on: board),
            ["declared-fallback-edge"]
        )
    }

    func testCapacityQualifiedPocketPrefersExactCapacityPocketOverDeclaredFallback() {
        let board = board(holds: [
            hold(id: "exact-pocket", kind: .pocket, fingerCapacity: 2, x: 0.1),
            hold(id: "declared-fallback-edge", kind: .edge, feature: .largeEdge, fingerCapacity: 4)
        ])
        let target = HoldTarget.kind(
            .pocket,
            fingerCapacity: 2,
            fallback: .largeEdge
        )

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: target, on: board),
            ["exact-pocket"]
        )
    }

    func testCapacityQualifiedPocketOrderingIsExactThenFallbacksThenWrongCapacity() {
        let target = HoldTarget.kind(
            .pocket,
            fallbacks: [.mediumEdge, .largeEdge],
            fingerCapacity: 2
        )

        let exactBoard = board(holds: [
            hold(id: "exact-pocket", kind: .pocket, fingerCapacity: 2, x: 0.1),
            hold(id: "wrong-capacity-pocket", kind: .pocket, fingerCapacity: 4, x: 0.2),
            hold(id: "medium-edge", feature: .mediumEdge),
            hold(id: "large-edge", feature: .largeEdge)
        ])
        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: target, on: exactBoard),
            ["exact-pocket"]
        )

        let fallbackBoard = board(holds: [
            hold(id: "wrong-capacity-pocket", kind: .pocket, fingerCapacity: 4, x: 0.1),
            hold(id: "medium-edge", feature: .mediumEdge),
            hold(id: "large-edge", feature: .largeEdge)
        ])
        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: target, on: fallbackBoard),
            ["medium-edge"]
        )

        let wrongCapacityOnlyBoard = board(holds: [
            hold(id: "wrong-capacity-pocket", kind: .pocket, fingerCapacity: 4, x: 0.1)
        ])
        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: target, on: wrongCapacityOnlyBoard),
            ["wrong-capacity-pocket"]
        )
    }

    func testSubstitutionPrefersMatchingFingerCapacityWithinSameKindTier() {
        let board = board(holds: [
            hold(id: "e2", kind: .edge, feature: nil, fingerCapacity: 2),
            hold(id: "e4", kind: .edge, feature: nil, fingerCapacity: 4)
        ])
        let target = HoldTarget.feature(.incutEdge, fingerCapacity: 4)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["e4"])
    }

    func testSameKindNoFeatureMatch() {
        let board = board(holds: [
            hold(id: "j", kind: .edge, feature: nil)
        ])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["j"])
    }

    /// A board with generic, untagged edges cannot distinguish a semantic
    /// edge request. The physical-kind fallback must remain a usable,
    /// bounded cue rather than highlighting every edge on the board.
    func testMetadataLightSameKindFallbackSelectsOneRepresentativeHold() {
        let board = board(holds: [
            hold(id: "first-edge", kind: .edge),
            hold(id: "second-edge", kind: .edge),
            hold(id: "third-edge", kind: .edge)
        ])
        let target = HoldTarget.feature(.mediumEdge)

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertEqual(result, ["first-edge"])
    }

    func testMetadataLightEdgeFallbackSelectsOneEdgePerBoardHalf() {
        let board = board(holds: [
            hold(id: "left-edge", x: 0.1),
            hold(id: "left-extra", x: 0.3),
            hold(id: "right-edge", x: 0.8)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.largeEdge),
            on: board
        )

        XCTAssertEqual(result, ["left-edge", "right-edge"])
    }

    /// A 20 mm medium-edge target must prefer a documented 20/15 mm
    /// continuous contact over shallower and deeper metadata-light edges.
    func testMetadataLightMediumEdgeFallbackPrefersNearestDocumentedDepthRange() {
        let board = board(holds: [
            hold(id: "10-8", depthRangeMillimeters: 8...10),
            hold(id: "30-25", depthRangeMillimeters: 25...30),
            hold(id: "20-15", depthRangeMillimeters: 15...20)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.mediumEdge),
            on: board
        )

        XCTAssertEqual(result, ["20-15"])
    }

    /// Depth metadata is optional, so a documented scalar measurement also
    /// outranks unknown or farther range measurements in a physical fallback.
    func testMetadataLightLargeEdgeFallbackUsesNearestScalarDepthBeforeUnknownHold() {
        let board = board(holds: [
            hold(id: "unknown"),
            hold(id: "20-15", depthRangeMillimeters: 15...20),
            hold(id: "29", sizeMillimeters: 29)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.largeEdge),
            on: board
        )

        XCTAssertEqual(result, ["29"])
    }

    func testKindTargetSubstitutesByKind() {
        let board = board(holds: [
            hold(id: "e1", kind: .edge, feature: .largeEdge)
        ])
        let target = HoldTarget.kind(.edge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["e1"])
    }

    func testJugKindTargetResolvesEveryJug() {
        let board = board(holds: [
            hold(id: "left-jug", kind: .jug, x: 0.1),
            hold(id: "right-jug", kind: .jug, x: 0.8)
        ])

        XCTAssertEqual(
            BoardTargetResolver.resolveHoldIDs(for: .kind(.jug), on: board),
            ["left-jug", "right-jug"]
        )
    }

    func testThreeFingerPocketKindTargetResolvesOneHoldPerBoardSide() {
        let board = board(holds: [
            hold(id: "left-three", kind: .pocket, fingerCapacity: 3, x: 0.1),
            hold(id: "left-two", kind: .pocket, fingerCapacity: 2, x: 0.3),
            hold(id: "right-three", kind: .pocket, fingerCapacity: 3, x: 0.7),
            hold(id: "right-two", kind: .pocket, fingerCapacity: 2, x: 0.9)
        ])
        let target = HoldTarget(
            holdIDs: [],
            kind: .pocket,
            feature: nil,
            fallbackFeatures: [],
            fingerCapacity: 3
        )

        XCTAssertEqual(
            BoardTargetResolver.resolveHoldIDs(for: target, on: board),
            ["left-three", "right-three"]
        )
    }

    func testEdgeFeatureSubstitutesUnknownCapacityPocketsWhenBoardHasNoEdges() {
        let board = board(holds: [
            hold(id: "pocket", kind: .pocket)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.smallEdge),
            on: board,
            gripType: .openHand
        )

        XCTAssertEqual(result, ["pocket"])
    }

    @MainActor
    func testCrimpStepsRejectJugsOpenHandRailsAndPockets() throws {
        let incompatibleBoard = board(holds: [
            hold(id: "jug", kind: .jug),
            hold(id: "open-hand-rail", feature: .largeOpenHandRail),
            hold(id: "pocket", kind: .pocket)
        ])
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)

        for gripType in [GripType.halfCrimp, .fullCrimp] {
            let step = WorkoutStep(
                id: "crimp-step",
                number: 1,
                title: "Crimp step",
                instruction: "Crimp an edge.",
                accessory: "",
                duration: 7,
                phase: .hang,
                targets: [.feature(.mediumEdge, fallback: .largeOpenHandRail)],
                gripType: gripType
            )

            XCTAssertTrue(store.holdIDs(for: step, on: incompatibleBoard).isEmpty)
        }
    }

    func testCrimpResolverRejectsJugsOpenHandRailsAndPockets() {
        let incompatibleBoard = board(holds: [
            hold(id: "jug", kind: .jug),
            hold(id: "open-hand-rail", feature: .largeOpenHandRail),
            hold(id: "pocket", kind: .pocket)
        ])
        let target = HoldTarget.feature(
            .mediumEdge,
            fallback: .largeOpenHandRail
        )

        for gripType in [GripType.halfCrimp, .fullCrimp] {
            XCTAssertTrue(
                BoardTargetResolver.substituteHoldIDs(
                    for: target,
                    on: incompatibleBoard,
                    gripType: gripType
                ).isEmpty
            )
        }
    }

    func testEdgeFeatureFallbackSelectsOnePocketPerHandWhenCapacityIsUnspecified() {
        let board = board(holds: [
            hold(id: "upper-left", kind: .pocket, x: 0.1),
            hold(id: "upper-right", kind: .pocket, x: 0.8),
            hold(id: "lower-left", kind: .pocket, x: 0.2),
            hold(id: "lower-right", kind: .pocket, x: 0.7)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.smallEdge),
            on: board
        )

        XCTAssertEqual(result, ["upper-left", "upper-right"])
    }

    func testEdgeKindSubstitutesPocketsWhenBoardHasNoEdges() {
        let board = board(holds: [
            hold(id: "pocket", kind: .pocket)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .kind(.edge),
            on: board
        )

        XCTAssertEqual(result, ["pocket"])
    }

    func testEdgeFeatureCapacitySubstitutesOnlyMatchingPocketCapacity() {
        let board = board(holds: [
            hold(id: "two-finger", kind: .pocket, fingerCapacity: 2),
            hold(id: "three-finger", kind: .pocket, fingerCapacity: 3)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.smallEdge, fingerCapacity: 2),
            on: board
        )

        XCTAssertEqual(result, ["two-finger"])
    }

    func testPinchDoesNotSubstitutePockets() {
        let board = board(holds: [
            hold(id: "pocket", kind: .pocket)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.mediumPinch),
            on: board
        )

        XCTAssertTrue(result.isEmpty)
    }

    @MainActor
    func testBeastmaker1000ResolvesMaxHangsOnMeasuredTwentyMillimeterEdges() throws {
        let board = try XCTUnwrap(BoardCatalog.all.first { $0.id == "beastmaker-1000" })
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)

        XCTAssertEqual(
            store.holdIDs(for: try XCTUnwrap(PlanCatalog.maxHangs.steps.first), on: board),
            ["pocket-bottom-outer-left", "pocket-bottom-outer-right"]
        )
        XCTAssertFalse(store.isIncompatible(PlanCatalog.maxHangs, on: board))
    }

    @MainActor
    func testBeastmaker2000OpenHandLargeEdgePrefersMirroredThirtyThreeMillimeterEdges() throws {
        let board = try XCTUnwrap(BoardCatalog.board(for: "beastmaker-2000"))
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        let step = WorkoutStep(
            id: "open-hand-29-mm",
            number: 1,
            title: "29 mm open edge",
            instruction: "",
            accessory: "",
            duration: 7,
            phase: .hang,
            targets: [.feature(.largeEdge)],
            gripType: .openHand
        )

        XCTAssertEqual(store.holdIDs(for: step, on: board), ["front-middle-9", "front-middle-1"])
    }

    func testAbrahangsHalfFourHangUsesBothBeastmaker2000EndEdges() throws {
        let board = try XCTUnwrap(BoardCatalog.board(for: "beastmaker-2000"))
        let plan = try XCTUnwrap(PlanCatalog.all.first { $0.id == "research.abrahangs" })
        let step = try XCTUnwrap(plan.steps.first { $0.title == "Abrahang · Half 4 Hang" })
        let target = try XCTUnwrap(step.targets.first)

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(
                for: target,
                on: board,
                gripType: step.gripType
            ),
            ["front-lower-1", "front-lower-9"]
        )
    }

    func testExplicitBeastmaker2000HoldIDRemainsUnchanged() throws {
        let board = try XCTUnwrap(BoardCatalog.board(for: "beastmaker-2000"))

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(
                for: .ids("front-lower-5"),
                on: board,
                gripType: .halfCrimp
            ),
            ["front-lower-5"]
        )
    }

    @MainActor
    func testMaxHangsResolvesOnBoardWithCompatibleEdge() throws {
        let board = board(holds: [
            hold(id: "large-edge", feature: .largeEdge)
        ])
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)

        XCTAssertFalse(store.isIncompatible(PlanCatalog.maxHangs, on: board))
        XCTAssertEqual(
            store.holdIDs(for: try XCTUnwrap(PlanCatalog.maxHangs.steps.first), on: board),
            ["large-edge"]
        )
    }

    @MainActor
    func testMultiTargetCrimpStepRetainsNonCrimpTargetAndRemainsCompatible() throws {
        let board = board(holds: [
            hold(id: "medium-edge", feature: .mediumEdge),
            hold(id: "jug", kind: .jug)
        ])
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        let methodPlan = LegacyPlanSeedCatalog.methodEMOM
        let step = try XCTUnwrap(methodPlan.steps.first { $0.id == "method-emom-minute-3" })
        let plan = TrainingPlan(
            id: methodPlan.id,
            title: methodPlan.title,
            subtitle: methodPlan.subtitle,
            level: methodPlan.level,
            sourceLabel: methodPlan.sourceLabel,
            sourceURL: methodPlan.sourceURL,
            provenance: methodPlan.provenance,
            boardID: methodPlan.boardID,
            steps: [step]
        )

        XCTAssertEqual(store.holdIDs(for: step, on: board), ["medium-edge", "jug"])
        XCTAssertFalse(store.isIncompatible(plan, on: board))
    }

    @MainActor
    func testBeastmaker1000ResolvesREIMediumPinchFallbackOnMeasuredMediumEdges() throws {
        let board = try XCTUnwrap(BoardCatalog.all.first { $0.id == "beastmaker-1000" })
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        let mediumPinchStep = try XCTUnwrap(
            LegacyPlanSeedCatalog.reiHangboardSample.steps.first { step in
                step.targets.contains { $0.feature == .mediumPinch }
            }
        )

        XCTAssertEqual(
            store.holdIDs(for: mediumPinchStep, on: board),
            ["pocket-bottom-outer-left", "pocket-bottom-outer-right"]
        )
        XCTAssertFalse(store.isIncompatible(LegacyPlanSeedCatalog.reiHangboardSample, on: board))
    }

    func testEmptyBoardReturnsEmpty() {
        let board = board(holds: [])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
    }

    /// A board with no pocket holds at all (not merely an unmatched
    /// capacity) must still resolve via the target's declared fallback
    /// feature, not just its declared kind's own closest-match search.
    func testClosestMatchTriesDeclaredFallbackFeatureWhenBoardHasNoHoldOfThePrimaryKind() {
        let board = board(holds: [
            hold(id: "edge", kind: .edge, feature: nil, fingerCapacity: nil)
        ])
        let target = HoldTarget.kind(.pocket, fingerCapacity: 2, fallback: .largeEdge)

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertEqual(result, ["edge"])
    }

    func testPocketTargetWithoutFallbackDoesNotSubstituteMetadataLightEdge() {
        let board = board(holds: [
            hold(id: "edge", kind: .edge, feature: nil, fingerCapacity: nil)
        ])
        let target = HoldTarget.kind(.pocket, fingerCapacity: 2)

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertTrue(result.isEmpty)
    }

    /// A declared fallback only substitutes on its own kind; it must not
    /// inherit byFeatureGroup's edge-to-pocket rescue, or a plan author's
    /// single named fallback would silently reach two substitutions deep.
    func testDeclaredFallbackDoesNotInheritTheEdgeToPocketRescue() {
        let board = board(holds: [
            hold(id: "pocket", kind: .pocket)
        ])
        let target = HoldTarget.feature(.mediumPinch, fallback: .mediumEdge)

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertTrue(result.isEmpty)
    }

    func testOtherGroupDoesNotCrossKindMatchJugToOpenHandRail() {
        let board = board(holds: [
            hold(id: "r1", kind: .edge, feature: .largeOpenHandRail)
        ])
        let target = HoldTarget.kind(.jug)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
    }
}
