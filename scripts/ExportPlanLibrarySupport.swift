import Foundation

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
