import Foundation
import simd

// Keep the pure suspension validator available without compiling UIKit and
// RealityKit rendering. These are the same result cases used by the app solver.
enum BoardModelSolvedSuspension {
    case single(SuspendedSolvedPresentation)
    case pairedLead(SuspendedPairedLeadSolvedPresentation)
    case twoBranch(SuspendedTwoBranchSolvedPresentation)
}

// The exporter compiles the plan resolver without the app's force-sensor
// module. This preserves the small measurement surface referenced by
// WorkoutActivityRecording without pulling the hardware stack into export.
struct WorkoutStepMeasurement {
    let stepID: String
    let peakLoadKGF: Double?
    let sampleCount: Int
    let actualLoadedDuration: TimeInterval
}

// Stub: the exporter does not need session-hand resolution.
enum WorkoutSessionHandResolver {
    static func sessionSteps(
        from steps: [WorkoutStep],
        preference: WorkoutSessionHandPreference,
        boardIsOneHanded: Bool
    ) -> [WorkoutStep] { steps }
}
