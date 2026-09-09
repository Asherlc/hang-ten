import XCTest
@testable import HangTen

final class WorkoutSegmentTests: XCTestCase {
    func testBoardHoldPreservesPhysicalSizeSeparatelyFromDisplayName() {
        let hold = BoardHold(
            id: "edge-21",
            name: "Left 21 mm edge",
            kind: .edge,
            sizeMillimeters: 21
        )

        XCTAssertEqual(hold.sizeMillimeters, 21)
        XCTAssertEqual(hold.kind, .edge)
    }

    func testWorkoutStepKeepsOrderedWorkAndRestSegments() {
        let step = WorkoutStep(
            id: "hang",
            number: 1,
            title: "Hang",
            instruction: "Hang",
            accessory: "20s hang · 10s rest",
            duration: 30,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: 20),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
            ]
        )

        XCTAssertEqual(step.segments.map(\.kind), [.work, .rest])
        XCTAssertEqual(step.segments.map(\.duration), [20, 10])
    }
}
