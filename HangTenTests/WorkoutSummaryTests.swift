import XCTest
@testable import HangTen

final class WorkoutSummaryTests: XCTestCase {
    func testSummaryUsesActualLoadedDurationAndPeakInSelectedUnit() {
        let step = WorkoutStepMeasurement(
            stepID: "step",
            plannedActiveDuration: 7,
            intervals: [LoadInterval(start: 1, end: 4)],
            peakLoadKGF: 2,
            sampleCount: 20,
            status: .measured
        )

        XCTAssertEqual(step.actualLoadedDuration, 3, accuracy: 0.0001)
        XCTAssertEqual(
            MotherboardForceUnit.lbf.value(fromKilogramsForce: step.peakLoadKGF!),
            4.40925,
            accuracy: 0.0001
        )
    }
}
