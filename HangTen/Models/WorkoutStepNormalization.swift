import Foundation

enum WorkoutStepNormalizationError: Error, Equatable {
    case unsupportedCompoundTiming(stepID: String, segmentIndex: Int)
    case mismatchedCompoundDuration(
        stepID: String,
        expectedDuration: TimeInterval,
        actualDuration: TimeInterval
    )
}

enum WorkoutStepNormalizer {
    static func expand(_ step: WorkoutStep) throws -> [WorkoutStep] {
        guard step.segments.count > 1 else {
            return [step]
        }

        for (index, segment) in step.segments.enumerated() {
            guard segment.timing == .fixed, segment.duration != nil else {
                throw WorkoutStepNormalizationError.unsupportedCompoundTiming(
                    stepID: step.id,
                    segmentIndex: index
                )
            }
        }

        let actualDuration = step.segments.compactMap(\.duration).reduce(0, +)
        guard actualDuration == step.duration else {
            throw WorkoutStepNormalizationError.mismatchedCompoundDuration(
                stepID: step.id,
                expectedDuration: step.duration,
                actualDuration: actualDuration
            )
        }

        return try step.segments.enumerated().map { index, segment in
            let duration = try segmentDuration(segment, stepID: step.id, segmentIndex: index)
            let id = "\(step.id).segment-\(index + 1)"

            switch segment.kind {
            case .work:
                return WorkoutStep(
                    id: id,
                    number: step.number,
                    title: step.title,
                    instruction: step.instruction,
                    accessory: step.accessory,
                    duration: duration,
                    phase: step.phase,
                    targets: segment.targets,
                    segments: [segment],
                    gripType: step.gripType
                )
            case .rest:
                return WorkoutStep(
                    id: id,
                    number: step.number,
                    title: "Rest",
                    instruction: "Step off the board, shake out, and breathe.",
                    accessory: "\(Int(duration))s rest",
                    duration: duration,
                    phase: .rest,
                    targets: [],
                    segments: [segment],
                    gripType: nil
                )
            }
        }
    }

    private static func segmentDuration(
        _ segment: WorkoutSegment,
        stepID: String,
        segmentIndex: Int
    ) throws -> TimeInterval {
        guard let duration = segment.duration else {
            throw WorkoutStepNormalizationError.unsupportedCompoundTiming(
                stepID: stepID,
                segmentIndex: segmentIndex
            )
        }
        return duration
    }
}
