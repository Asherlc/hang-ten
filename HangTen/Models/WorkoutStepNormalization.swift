import Foundation

enum WorkoutStepNormalizationError: Error, Equatable {
    case unsupportedCompoundTiming(stepID: String, segmentIndex: Int)
    case invalidCompoundDuration(stepID: String, segmentIndex: Int?)
    case mismatchedCompoundDuration(
        stepID: String,
        expectedDuration: TimeInterval,
        actualDuration: TimeInterval
    )
}

enum WorkoutStepNormalizer {
    /// Materializes the implicit segments represented by a compact plan
    /// definition. Runtime resolution and DEBUG seed literalization must use
    /// this same canonical form before comparing plans.
    static func materializingImplicitSegments(_ step: WorkoutStep) -> WorkoutStep {
        guard step.segments.isEmpty else { return step }

        let segments: [WorkoutSegment]
        if step.phase == .rest {
            segments = [
                WorkoutSegment(
                    kind: .rest,
                    target: nil,
                    timing: .fixed,
                    duration: step.duration
                )
            ]
        } else if let activeDuration = step.timedWorkDuration {
            let workSegment = WorkoutSegment(
                kind: .work,
                targets: step.targets,
                timing: .fixed,
                duration: activeDuration
            )
            let restDuration = step.duration - activeDuration
            segments = restDuration > 0 && restDuration.isFinite
                ? [
                    workSegment,
                    WorkoutSegment(
                        kind: .rest,
                        target: nil,
                        timing: .fixed,
                        duration: restDuration
                    )
                ]
                : [workSegment]
        } else if !step.targets.isEmpty {
            segments = [
                WorkoutSegment(
                    kind: .work,
                    targets: step.targets,
                    timing: .undefined,
                    duration: nil
                )
            ]
        } else {
            return step
        }

        return WorkoutStep(
            id: step.id,
            number: step.number,
            title: step.title,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            targets: step.targets,
            segments: segments,
            gripType: step.gripType,
            fingerConfiguration: step.fingerConfiguration,
            timedWorkDuration: step.timedWorkDuration
        )
    }

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
            guard let duration = segment.duration,
                  duration.isFinite,
                  duration > 0 else {
                throw WorkoutStepNormalizationError.invalidCompoundDuration(
                    stepID: step.id,
                    segmentIndex: index
                )
            }
        }

        guard step.duration.isFinite, step.duration > 0 else {
            throw WorkoutStepNormalizationError.invalidCompoundDuration(
                stepID: step.id,
                segmentIndex: nil
            )
        }

        let actualDuration = step.segments.compactMap(\.duration).reduce(0, +)
        guard actualDuration == step.duration else {
            throw WorkoutStepNormalizationError.mismatchedCompoundDuration(
                stepID: step.id,
                expectedDuration: step.duration,
                actualDuration: actualDuration
            )
        }

        return step.segments.enumerated().map { index, segment in
            let duration = segmentDuration(segment)
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
                    gripType: step.gripType,
                    fingerConfiguration: step.fingerConfiguration,
                    timedWorkDuration: duration
                )
            case .rest:
                return WorkoutStep(
                    id: id,
                    number: step.number,
                    title: "Rest",
                    instruction: "",
                    accessory: "\(Int(duration))s rest",
                    duration: duration,
                    phase: .rest,
                    targets: [],
                    segments: [segment],
                    gripType: nil,
                    fingerConfiguration: nil
                )
            }
        }
    }

    private static func segmentDuration(_ segment: WorkoutSegment) -> TimeInterval {
        guard let duration = segment.duration else {
            preconditionFailure("Validated compound segments must have a duration")
        }
        return duration
    }
}
