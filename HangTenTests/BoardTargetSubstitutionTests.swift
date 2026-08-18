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

    func testCrossKindMatchingFingerCapacity() {
        let board = board(holds: [
            hold(id: "e2", kind: .edge, feature: nil, fingerCapacity: 2)
        ])
        let target = HoldTarget.feature(.twoFingerPocket)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["e2"])
    }

    func testCrossKindMismatchedFingerCapacityExcluded() {
        let board = board(holds: [
            hold(id: "e4", kind: .edge, feature: nil, fingerCapacity: 4)
        ])
        let target = HoldTarget.feature(.twoFingerPocket)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
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

    func testEmptyBoardReturnsEmpty() {
        let board = board(holds: [])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
    }
}
