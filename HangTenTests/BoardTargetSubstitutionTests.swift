import XCTest
@testable import HangTen

final class BoardTargetSubstitutionTests: XCTestCase {
    private func hold(
        id: String,
        kind: HoldKind = .edge,
        feature: HoldFeature? = nil,
        fingerCapacity: Int? = nil,
        sizeMillimeters: Double? = nil,
        depthRangeMillimeters: ClosedRange<Double>? = nil,
        x: Double = 0
    ) -> BoardHold {
        BoardHold(
            id: id,
            name: id,
            shortLabel: id,
            detail: id,
            kind: kind,
            frame: HoldFrame(x: x, y: 0, width: 0.1, height: 0.1),
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

    func testSameKindEdgeCandidateOutranksPocketSubstitution() {
        let board = board(holds: [
            hold(id: "edge", kind: .edge, feature: .mediumEdge),
            hold(id: "pocket", kind: .pocket, feature: .pocket)
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
        let target = HoldTarget.feature(.pocket, fingerCapacity: 2)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["e2"])
    }

    func testCrossKindMismatchedFingerCapacityExcluded() {
        let board = board(holds: [
            hold(id: "e4", kind: .edge, feature: nil, fingerCapacity: 4)
        ])
        let target = HoldTarget.feature(.pocket, fingerCapacity: 2)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
    }

    func testResolveHoldIDsUsesExplicitFallbackDespiteMismatchedFingerCapacity() {
        let board = board(holds: [
            hold(id: "fallback-edge", feature: .largeEdge, fingerCapacity: 4),
            hold(id: "unrelated-jug", kind: .jug, feature: .jug)
        ])
        let target = HoldTarget.feature(
            .smallEdge,
            fingerCapacity: 2,
            fallback: .largeEdge
        )

        let result = BoardTargetResolver.resolveHoldIDs(for: target, on: board)

        XCTAssertEqual(result, ["fallback-edge"])
    }

    func testSubstitutionUsesClosestMatchForExplicitEdgeFallback() {
        let board = board(holds: [
            hold(id: "generic-edge", kind: .edge, feature: nil)
        ])
        let target = HoldTarget.feature(
            .pocket,
            fingerCapacity: 2,
            fallback: .mediumEdge
        )

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertEqual(result, ["generic-edge"])
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

    func testEdgeFeatureSubstitutesUnknownCapacityPocketsWhenBoardHasNoEdges() {
        let board = board(holds: [
            hold(id: "pocket", kind: .pocket, feature: .pocket)
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
            hold(id: "jug", kind: .jug, feature: .jug),
            hold(id: "open-hand-rail", feature: .largeOpenHandRail),
            hold(id: "pocket", kind: .pocket, feature: .pocket)
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
                targets: [.feature(.mediumEdge, fallback: .largeOpenHandRail, .jug)],
                gripType: gripType
            )

            XCTAssertTrue(store.holdIDs(for: step, on: incompatibleBoard).isEmpty)
        }
    }

    func testCrimpResolverRejectsJugsOpenHandRailsAndPockets() {
        let incompatibleBoard = board(holds: [
            hold(id: "jug", kind: .jug, feature: .jug),
            hold(id: "open-hand-rail", feature: .largeOpenHandRail),
            hold(id: "pocket", kind: .pocket, feature: .pocket)
        ])
        let target = HoldTarget.feature(
            .mediumEdge,
            fallback: .largeOpenHandRail,
            .jug
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
            hold(id: "upper-left", kind: .pocket, feature: .pocket, x: 0.1),
            hold(id: "upper-right", kind: .pocket, feature: .pocket, x: 0.8),
            hold(id: "lower-left", kind: .pocket, feature: .pocket, x: 0.2),
            hold(id: "lower-right", kind: .pocket, feature: .pocket, x: 0.7)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.smallEdge),
            on: board
        )

        XCTAssertEqual(result, ["upper-left", "upper-right"])
    }

    func testEdgeKindSubstitutesPocketsWhenBoardHasNoEdges() {
        let board = board(holds: [
            hold(id: "pocket", kind: .pocket, feature: .pocket)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .kind(.edge),
            on: board
        )

        XCTAssertEqual(result, ["pocket"])
    }

    func testEdgeFeatureCapacitySubstitutesOnlyMatchingPocketCapacity() {
        let board = board(holds: [
            hold(id: "two-finger", kind: .pocket, feature: .pocket, fingerCapacity: 2),
            hold(id: "three-finger", kind: .pocket, feature: .pocket, fingerCapacity: 3)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.smallEdge, fingerCapacity: 2),
            on: board
        )

        XCTAssertEqual(result, ["two-finger"])
    }

    func testPinchDoesNotSubstitutePockets() {
        let board = board(holds: [
            hold(id: "pocket", kind: .pocket, feature: .pocket)
        ])

        let result = BoardTargetResolver.substituteHoldIDs(
            for: .feature(.mediumPinch),
            on: board
        )

        XCTAssertTrue(result.isEmpty)
    }

    @MainActor
    func testBeastmaker1000IsIncompatibleWithRuntimeMaxHangs() throws {
        let board = try XCTUnwrap(BoardCatalog.all.first { $0.id == "beastmaker-1000" })
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)

        XCTAssertTrue(store.isIncompatible(PlanCatalog.maxHangs, on: board))
        XCTAssertTrue(
            store.holdIDs(for: try XCTUnwrap(PlanCatalog.maxHangs.steps.first), on: board).isEmpty
        )
    }

    @MainActor
    func testBeastmaker2000OpenHandLargeEdgeHighlightsMirroredOuterEdges() throws {
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

        XCTAssertEqual(store.holdIDs(for: step, on: board), ["front-lower-1", "front-lower-9"])
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
            hold(id: "jug", kind: .jug, feature: .jug)
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
    func testBeastmaker1000IsIncompatibleWithUnsupportedREIPinchRoutine() throws {
        let board = try XCTUnwrap(BoardCatalog.all.first { $0.id == "beastmaker-1000" })
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)

        XCTAssertTrue(store.isIncompatible(LegacyPlanSeedCatalog.reiHangboardSample, on: board))
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
        let target = HoldTarget.feature(.pocket, fingerCapacity: 2, fallback: .largeEdge)

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertEqual(result, ["edge"])
    }

    func testPocketTargetWithoutFallbackDoesNotSubstituteMetadataLightEdge() {
        let board = board(holds: [
            hold(id: "edge", kind: .edge, feature: nil, fingerCapacity: nil)
        ])
        let target = HoldTarget.feature(.pocket, fingerCapacity: 2)

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertTrue(result.isEmpty)
    }

    /// A declared fallback only substitutes on its own kind; it must not
    /// inherit byFeatureGroup's edge-to-pocket rescue, or a plan author's
    /// single named fallback would silently reach two substitutions deep.
    func testDeclaredFallbackDoesNotInheritTheEdgeToPocketRescue() {
        let board = board(holds: [
            hold(id: "pocket", kind: .pocket, feature: .pocket)
        ])
        let target = HoldTarget.feature(.mediumPinch, fallback: .mediumEdge)

        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)

        XCTAssertTrue(result.isEmpty)
    }

    func testOtherGroupDoesNotCrossKindMatchJugToOpenHandRail() {
        let board = board(holds: [
            hold(id: "r1", kind: .edge, feature: .largeOpenHandRail)
        ])
        let target = HoldTarget.feature(.jug)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
    }
}
