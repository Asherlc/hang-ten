import Foundation

extension HoldTarget {
    static func feature(
        _ feature: HoldFeature,
        fallbacks: [HoldFeature]
    ) -> HoldTarget {
        HoldTarget(
            holdIDs: [],
            kind: nil,
            feature: feature,
            fallbackFeatures: fallbacks
        )
    }
}

struct RecordedActivitySegment: Codable, Hashable {
    let stepID: String
    let stepNumber: Int
    let kind: WorkoutSegmentKind
    let holdIDs: [String]
    let holdType: String?
    let sizeMillimeters: Int?
    let durationSeconds: TimeInterval?
    let peakLoadKGF: Double?
    let actualLoadedDurationSeconds: TimeInterval?

    enum CodingKeys: String, CodingKey {
        case stepID, stepNumber, kind, holdIDs, holdType, sizeMillimeters, durationSeconds
        case peakLoadKGF, actualLoadedDurationSeconds
    }

    init(
        stepID: String,
        stepNumber: Int,
        kind: WorkoutSegmentKind,
        holdIDs: [String],
        holdType: String?,
        sizeMillimeters: Int?,
        durationSeconds: TimeInterval?,
        peakLoadKGF: Double? = nil,
        actualLoadedDurationSeconds: TimeInterval? = nil
    ) {
        self.stepID = stepID
        self.stepNumber = stepNumber
        self.kind = kind
        self.holdIDs = holdIDs
        self.holdType = holdType
        self.sizeMillimeters = sizeMillimeters
        self.durationSeconds = durationSeconds
        self.peakLoadKGF = peakLoadKGF
        self.actualLoadedDurationSeconds = actualLoadedDurationSeconds
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(stepID, forKey: .stepID)
        try container.encode(stepNumber, forKey: .stepNumber)
        try container.encode(kind, forKey: .kind)
        try container.encode(holdIDs, forKey: .holdIDs)
        try container.encodeIfPresent(holdType, forKey: .holdType)
        try container.encodeIfPresent(sizeMillimeters, forKey: .sizeMillimeters)
        try container.encodeIfPresent(durationSeconds, forKey: .durationSeconds)
        try container.encodeIfPresent(peakLoadKGF, forKey: .peakLoadKGF)
        try container.encodeIfPresent(actualLoadedDurationSeconds, forKey: .actualLoadedDurationSeconds)
    }
}

struct WorkoutActivityMetadata: Codable, Hashable {
    let version: Int
    let segments: [RecordedActivitySegment]

    init(version: Int = 1, segments: [RecordedActivitySegment]) {
        self.version = version
        self.segments = segments
    }
}

struct WorkoutActivitySegmentKey: Hashable {
    let stepID: String
    let segmentIndex: Int
}

enum WorkoutActivityRecordingError: LocalizedError, Equatable {
    case unresolvedTarget(stepID: String, segmentIndex: Int)
    case invalidObservedDuration(WorkoutActivitySegmentKey)

    var errorDescription: String? {
        switch self {
        case .unresolvedTarget:
            "Hang Ten could not match a workout activity to the selected board."
        case .invalidObservedDuration:
            "Hang Ten could not use the recorded workout duration."
        }
    }
}

internal enum BoardTargetResolver {
    static func resolveHoldIDs(for target: HoldTarget, on board: TrainingBoard) -> [String] {
        if !target.holdIDs.isEmpty {
            let available = Set(board.holds.map(\.id))
            return target.holdIDs.filter(available.contains)
        }
        if let feature = target.feature {
            let exact = board.holds.filter { $0.features.contains(feature) }
            if !exact.isEmpty { return exact.map(\.id) }
            for fallback in target.fallbackFeatures {
                let matches = board.holds.filter { $0.features.contains(fallback) }
                if !matches.isEmpty { return matches.map(\.id) }
            }
            return []
        }
        guard let kind = target.kind else { return [] }
        return board.holds.filter { $0.kind == kind }.map(\.id)
    }

    static func resolveHolds(for target: HoldTarget, on board: TrainingBoard) -> [BoardHold] {
        let ids = Set(resolveHoldIDs(for: target, on: board))
        return board.holds.filter { ids.contains($0.id) }
    }
}

struct WorkoutActivityRecorder {
    func segments(
        for plan: TrainingPlan,
        on board: TrainingBoard,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:],
        stepMeasurements: [String: WorkoutStepMeasurement] = [:]
    ) throws -> [RecordedActivitySegment] {
        var result: [RecordedActivitySegment] = []
        for step in plan.steps {
            for (index, segment) in step.segments.enumerated() {
                let key = WorkoutActivitySegmentKey(stepID: step.id, segmentIndex: index)
                let duration: TimeInterval?
                switch segment.kind {
                case .rest:
                    duration = segment.duration
                case .work:
                    switch segment.timing {
                    case .fixed: duration = segment.duration
                    case .undefined: duration = nil
                    case .stopwatch:
                        if let observed = stopwatchDurations[key] {
                            guard observed.isFinite, observed >= 0 else { throw WorkoutActivityRecordingError.invalidObservedDuration(key) }
                            duration = observed
                        } else { duration = nil }
                    }
                }
                if segment.kind == .rest {
                    result.append(RecordedActivitySegment(stepID: step.id, stepNumber: step.number, kind: .rest, holdIDs: [], holdType: nil, sizeMillimeters: nil, durationSeconds: duration))
                    continue
                }
                let load = measuredLoad(for: stepMeasurements[step.id])
                guard !segment.targets.isEmpty else { throw WorkoutActivityRecordingError.unresolvedTarget(stepID: step.id, segmentIndex: index) }
                let holdsByTarget = segment.targets.map {
                    BoardTargetResolver.resolveHolds(for: $0, on: board)
                }
                guard holdsByTarget.allSatisfy({ !$0.isEmpty }) else { throw WorkoutActivityRecordingError.unresolvedTarget(stepID: step.id, segmentIndex: index) }
                let holds = holdsByTarget.flatMap { $0 }
                guard !holds.isEmpty else { throw WorkoutActivityRecordingError.unresolvedTarget(stepID: step.id, segmentIndex: index) }
                if segment.targets.count > 1 {
                    result.append(
                        RecordedActivitySegment(
                            stepID: step.id,
                            stepNumber: step.number,
                            kind: .work,
                            holdIDs: holds.map(\.id),
                            holdType: nil,
                            sizeMillimeters: nil,
                            durationSeconds: duration,
                            peakLoadKGF: load.peakLoadKGF,
                            actualLoadedDurationSeconds: load.actualLoadedDurationSeconds
                        )
                    )
                    continue
                }
                var groups: [(HoldKind, Int?, [String])] = []
                for hold in holds {
                    let descriptor = (hold.kind, hold.sizeMillimeters)
                    if let i = groups.firstIndex(where: { $0.0 == descriptor.0 && $0.1 == descriptor.1 }) { groups[i].2.append(hold.id) }
                    else { groups.append((hold.kind, hold.sizeMillimeters, [hold.id])) }
                }
                result += groups.map { kind, size, ids in
                    RecordedActivitySegment(
                        stepID: step.id,
                        stepNumber: step.number,
                        kind: .work,
                        holdIDs: ids,
                        holdType: kind.rawValue,
                        sizeMillimeters: size,
                        durationSeconds: duration,
                        peakLoadKGF: load.peakLoadKGF,
                        actualLoadedDurationSeconds: load.actualLoadedDurationSeconds
                    )
                }
            }
        }
        return result
    }

    private func measuredLoad(
        for measurement: WorkoutStepMeasurement?
    ) -> (peakLoadKGF: Double?, actualLoadedDurationSeconds: TimeInterval?) {
        guard let measurement, measurement.sampleCount > 0 else {
            return (nil, nil)
        }

        let peakLoadKGF = measurement.peakLoadKGF.flatMap {
            $0.isFinite && $0 >= 0 ? $0 : nil
        }
        let loadedDuration = measurement.actualLoadedDuration
        let actualLoadedDurationSeconds = loadedDuration.isFinite && loadedDuration >= 0
            ? loadedDuration
            : nil
        return (peakLoadKGF, actualLoadedDurationSeconds)
    }

    func json(for metadata: WorkoutActivityMetadata) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(metadata)
        return String(decoding: data, as: UTF8.self)
    }
}
