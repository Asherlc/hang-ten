import XCTest
@testable import HangTen

final class WorkoutStepNormalizationTests: XCTestCase {
    func testFixedWorkAndRestSegmentsBecomeLiteralStepsInOrder() throws {
        let source = WorkoutStep(
            id: "repeaters",
            number: 4,
            title: "Repeaters",
            instruction: "Hang, then recover.",
            accessory: "20s work · 10s rest",
            duration: 30,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: 20),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
            ],
            gripType: .halfCrimp,
            timedWorkDuration: 20
        )

        let result = try WorkoutStepNormalizer.expand(source)

        XCTAssertEqual(result.map(\.id), ["repeaters.segment-1", "repeaters.segment-2"])
        XCTAssertEqual(result.map(\.duration), [20, 10])
        XCTAssertEqual(result.map(\.phase), [.hang, .rest])
        XCTAssertEqual(result.map { $0.segments.count }, [1, 1])
        XCTAssertEqual(result[0].targets, [.kind(.edge)])
        XCTAssertEqual(result[0].timedWorkDuration, 20)
        XCTAssertTrue(result[1].targets.isEmpty)
        XCTAssertTrue(result[1].instruction.isEmpty)
    }

    func testExpandedWorkRowUsesRetainedSegmentTargetAndGripSemantics() throws {
        let source = WorkoutStep(
            id: "different-targets",
            number: 2,
            title: "Targeted repeat",
            instruction: "Use the segment prescription.",
            accessory: "8s work · 4s rest",
            duration: 12,
            phase: .hang,
            targets: [.kind(.jug)],
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.mediumEdge),
                    timing: .fixed,
                    duration: 8
                ),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 4)
            ],
            gripType: .halfCrimp
        )

        let result = try WorkoutStepNormalizer.expand(source)

        XCTAssertEqual(result[0].targets, [.feature(.mediumEdge)])
        XCTAssertEqual(result[0].segments, [source.segments[0]])
        XCTAssertEqual(result[0].phase, .hang)
        XCTAssertEqual(result[0].gripType, .halfCrimp)
        XCTAssertEqual(result[0].duration, 8)
    }

    func testCompoundExpansionRetainsExactFingersOnWorkAndClearsThemOnRest() throws {
        let expectedConfiguration = try XCTUnwrap(FingerConfiguration(engagedFingers: [.index]))
        let source = WorkoutStep(
            id: "exact-fingers",
            number: 2,
            title: "Exact finger repeat",
            instruction: "Use only the prescribed finger.",
            accessory: "8s work · 4s rest",
            duration: 12,
            phase: .hang,
            targets: [.feature(.pocket, fingerCapacity: 3)],
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.pocket, fingerCapacity: 3),
                    timing: .fixed,
                    duration: 8
                ),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 4)
            ],
            gripType: .openHand,
            fingerConfiguration: expectedConfiguration
        )

        let result = try WorkoutStepNormalizer.expand(source)

        XCTAssertEqual(result[0].fingerConfiguration, expectedConfiguration)
        XCTAssertNil(result[1].fingerConfiguration)
    }

    func testSingleStopwatchStepRemainsOneStepWithItsCap() throws {
        let source = WorkoutStep(
            id: "max",
            number: 1,
            title: "Maximum hang",
            instruction: "Hang as long as possible.",
            accessory: "Up to 60s",
            duration: 60,
            phase: .hang,
            targets: [.feature(.roundSloper)],
            segments: [WorkoutSegment(
                kind: .work,
                target: .feature(.roundSloper),
                timing: .stopwatch,
                duration: nil
            )],
            gripType: .openHand
        )

        let result = try WorkoutStepNormalizer.expand(source)

        XCTAssertEqual(result, [source])
        XCTAssertEqual(result[0].segments[0].timing, .stopwatch)
        XCTAssertEqual(result[0].duration, 60)
    }

    func testCompoundNonFixedTimingIsRejected() {
        let source = WorkoutStep(
            id: "invalid",
            number: 1,
            title: "Invalid compound",
            instruction: "Invalid",
            accessory: "",
            duration: 60,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .stopwatch, duration: nil),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
            ]
        )

        XCTAssertThrowsError(try WorkoutStepNormalizer.expand(source)) { error in
            XCTAssertEqual(
                error as? WorkoutStepNormalizationError,
                .unsupportedCompoundTiming(stepID: "invalid", segmentIndex: 0)
            )
        }
    }

    func testCompoundSegmentsWithMismatchedDurationAreRejected() {
        let source = WorkoutStep(
            id: "mismatched",
            number: 1,
            title: "Mismatched compound",
            instruction: "Invalid",
            accessory: "",
            duration: 30,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: 20),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 5)
            ]
        )

        XCTAssertThrowsError(try WorkoutStepNormalizer.expand(source)) { error in
            XCTAssertEqual(
                error as? WorkoutStepNormalizationError,
                .mismatchedCompoundDuration(
                    stepID: "mismatched",
                    expectedDuration: 30,
                    actualDuration: 25
                )
            )
        }
    }

    func testCompoundStepWithZeroFixedSegmentDurationIsRejected() {
        let source = WorkoutStep(
            id: "zero-segment",
            number: 1,
            title: "Zero segment",
            instruction: "Invalid",
            accessory: "",
            duration: 10,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: 0),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
            ]
        )

        XCTAssertThrowsError(try WorkoutStepNormalizer.expand(source)) { error in
            XCTAssertEqual(
                error as? WorkoutStepNormalizationError,
                .invalidCompoundDuration(stepID: "zero-segment", segmentIndex: 0)
            )
        }
    }

    func testCompoundStepWithZeroEnclosingDurationIsRejectedBeforeMismatch() {
        let source = WorkoutStep(
            id: "zero-step",
            number: 1,
            title: "Zero step",
            instruction: "Invalid",
            accessory: "",
            duration: 0,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: 5),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 5)
            ]
        )

        XCTAssertThrowsError(try WorkoutStepNormalizer.expand(source)) { error in
            XCTAssertEqual(
                error as? WorkoutStepNormalizationError,
                .invalidCompoundDuration(stepID: "zero-step", segmentIndex: nil)
            )
        }
    }

    func testCompoundStepWithNegativeFixedSegmentDurationIsRejected() {
        let source = WorkoutStep(
            id: "negative-segment",
            number: 1,
            title: "Negative segment",
            instruction: "Invalid",
            accessory: "",
            duration: 10,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: -10),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
            ]
        )

        XCTAssertThrowsError(try WorkoutStepNormalizer.expand(source)) { error in
            XCTAssertEqual(
                error as? WorkoutStepNormalizationError,
                .invalidCompoundDuration(stepID: "negative-segment", segmentIndex: 0)
            )
        }
    }

    func testCompoundStepWithNonFiniteFixedSegmentDurationIsRejected() {
        let source = WorkoutStep(
            id: "non-finite-segment",
            number: 1,
            title: "Non-finite segment",
            instruction: "Invalid",
            accessory: "",
            duration: 10,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: .infinity),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 1)
            ]
        )

        XCTAssertThrowsError(try WorkoutStepNormalizer.expand(source)) { error in
            XCTAssertEqual(
                error as? WorkoutStepNormalizationError,
                .invalidCompoundDuration(stepID: "non-finite-segment", segmentIndex: 0)
            )
        }
    }

    func testCompoundStepWithNonFiniteEnclosingDurationIsRejected() {
        let source = WorkoutStep(
            id: "non-finite-step",
            number: 1,
            title: "Non-finite step",
            instruction: "Invalid",
            accessory: "",
            duration: .infinity,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .kind(.edge),
                    timing: .fixed,
                    duration: 5
                ),
                WorkoutSegment(
                    kind: .work,
                    target: .kind(.edge),
                    timing: .fixed,
                    duration: 5
                )
            ]
        )

        XCTAssertThrowsError(try WorkoutStepNormalizer.expand(source)) { error in
            XCTAssertEqual(
                error as? WorkoutStepNormalizationError,
                .invalidCompoundDuration(stepID: "non-finite-step", segmentIndex: nil)
            )
        }
    }

}
