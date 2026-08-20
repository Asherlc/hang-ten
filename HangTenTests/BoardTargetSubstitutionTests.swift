import XCTest
@testable import HangTen

final class BoardTargetSubstitutionTests: XCTestCase {
    private func hold(
        id: String,
        kind: HoldKind = .edge,
        feature: HoldFeature? = nil,
        fingerCapacity: Int? = nil
    ) -> BoardHold {
        BoardHold(
            id: id,
            name: id,
            shortLabel: id,
            detail: id,
            kind: kind,
            frame: HoldFrame(x: 0, y: 0, width: 0.1, height: 0.1),
            fingerCapacity: fingerCapacity,
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
            on: board
        )

        XCTAssertEqual(result, ["pocket"])
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
    func testBeastmaker1000SupportsGenericEdgeRoutineButNotUnsupportedREIPinchRoutine() throws {
        let board = try XCTUnwrap(BoardCatalog.all.first { $0.id == "beastmaker-1000" })
        let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)

        XCTAssertFalse(store.isIncompatible(LegacyPlanSeedCatalog.methodRepeaters, on: board))
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
