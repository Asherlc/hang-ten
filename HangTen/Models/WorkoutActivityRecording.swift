import Foundation

extension HoldTarget {
    static func feature(
        _ feature: HoldFeature,
        fallbacks: [HoldFeature],
        fingerCapacity: Int? = nil
    ) -> HoldTarget {
        HoldTarget(
            holdIDs: [],
            kind: nil,
            feature: feature,
            fallbackFeatures: fallbacks,
            fingerCapacity: fingerCapacity
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

    enum CodingKeys: String, CodingKey { case stepID, stepNumber, kind, holdIDs, holdType, sizeMillimeters, durationSeconds }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(stepID, forKey: .stepID)
        try container.encode(stepNumber, forKey: .stepNumber)
        try container.encode(kind, forKey: .kind)
        try container.encode(holdIDs, forKey: .holdIDs)
        try container.encodeIfPresent(holdType, forKey: .holdType)
        try container.encodeIfPresent(sizeMillimeters, forKey: .sizeMillimeters)
        try container.encodeIfPresent(durationSeconds, forKey: .durationSeconds)
    }
}

struct RecordedActivityStepMeasurement: Codable, Hashable {
    let stepID: String
    let peakLoadKGF: Double?
    let actualLoadedDurationSeconds: TimeInterval?
}

struct WorkoutActivityMetadata: Codable, Hashable {
    let version: Int
    let segments: [RecordedActivitySegment]
    let measurements: [RecordedActivityStepMeasurement]?

    init(
        version: Int = 1,
        segments: [RecordedActivitySegment],
        measurements: [RecordedActivityStepMeasurement]? = nil
    ) {
        self.version = version
        self.segments = segments
        self.measurements = measurements
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
            let exact = matching(feature, fingerCapacity: target.fingerCapacity, on: board)
            if !exact.isEmpty { return exact.map(\.id) }
            for fallback in target.fallbackFeatures {
                let matches = matching(fallback, fingerCapacity: target.fingerCapacity, on: board)
                if !matches.isEmpty { return matches.map(\.id) }

                // A fallback identifies a physically available substitute, not
                // the source-prescribed finger capacity. Preserve capacity for
                // the primary target, but do not reject an explicit fallback
                // merely because that substitute has no matching capacity.
                let capacityAgnosticMatches = matching(fallback, fingerCapacity: nil, on: board)
                if !capacityAgnosticMatches.isEmpty { return capacityAgnosticMatches.map(\.id) }

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

    static func substituteHoldIDs(for target: HoldTarget, on board: TrainingBoard) -> [String] {
        let primary = resolveHoldIDs(for: target, on: board)
        if !primary.isEmpty { return primary }
        return closestMatch(for: target, on: board)
    }

    static func substituteHolds(for target: HoldTarget, on board: TrainingBoard) -> [BoardHold] {
        let ids = Set(substituteHoldIDs(for: target, on: board))
        return board.holds.filter { ids.contains($0.id) }
    }

    /// A target's feature must match exactly; its finger count (when
    /// specified) must too, since `.pocket` alone no longer implies a count.
    private static func matching(_ feature: HoldFeature, fingerCapacity: Int?, on board: TrainingBoard) -> [BoardHold] {
        board.holds.filter { hold in
            guard hold.features?.contains(feature) == true else { return false }
            guard let fingerCapacity else { return true }
            return hold.fingerCapacity == fingerCapacity
        }
    }

    private static func closestMatch(for target: HoldTarget, on board: TrainingBoard) -> [String] {
        if let feature = target.feature {
            let primary = byFeatureGroup(feature, target: target, on: board)
            if !primary.isEmpty { return primary }
            // resolveHoldIDs already tried each fallback as an exact tagged
            // match; a board missing that tagging (or the primary feature's
            // kind entirely, e.g. no pockets) still deserves a same-kind
            // substitution for its declared fallbacks before giving up. This
            // intentionally skips byFeatureGroup's own further rescues (edge
            // boards standing in for pockets): a plan author who named one
            // specific fallback feature didn't ask for that fallback's
            // fallbacks too.
            for fallback in target.fallbackFeatures {
                let matches = sameKindOrGroup(fallback, target: target, on: board)
                if !matches.isEmpty { return matches }
            }
            return []
        }
        guard let kind = target.kind else { return [] }
        let sameKind = preferringFingerCapacity(
            board.holds.filter { $0.kind == kind },
            target: target
        )
        if !sameKind.isEmpty { return sameKind.map(\.id) }
        guard kind == .edge else { return [] }
        return crossKindPockets(for: target, on: board).map(\.id)
    }

    private static func byFeatureGroup(_ feature: HoldFeature, target: HoldTarget, on board: TrainingBoard) -> [String] {
        let direct = sameKindOrGroup(feature, target: target, on: board)
        if !direct.isEmpty { return direct }

        if feature.holdKind == .edge {
            let pockets = crossKindPockets(for: target, on: board)
            if !pockets.isEmpty { return pockets.map(\.id) }
        }

        if let capacity = target.fingerCapacity {
            let crossKind = board.holds.filter { $0.fingerCapacity == capacity }
            if !crossKind.isEmpty { return crossKind.map(\.id) }
        }

        return []
    }

    /// A feature's own group tag, then its physical kind regardless of
    /// tagging. Deliberately stops short of `byFeatureGroup`'s further
    /// cross-kind rescues, which exist for a target's own declared feature,
    /// not for stepping through a declared fallback's fallbacks.
    private static func sameKindOrGroup(_ feature: HoldFeature, target: HoldTarget, on board: TrainingBoard) -> [String] {
        let group = feature.featureGroup
        let groupFeatures = Set(HoldFeature.allCases.filter { $0.featureGroup == group })

        let sameGroup = board.holds.filter { hold in
            guard hold.kind == feature.holdKind,
                  let features = hold.features else { return false }
            return !features.isDisjoint(with: groupFeatures)
        }
        let preferredSameGroup = preferringFingerCapacity(sameGroup, target: target)
        if !preferredSameGroup.isEmpty { return preferredSameGroup.map(\.id) }

        let sameKind = board.holds.filter { $0.kind == feature.holdKind }
        let preferredSameKind = preferringFingerCapacity(sameKind, target: target)
        return preferredSameKind.map(\.id)
    }

    /// When the target specifies a finger count, prefer candidates that
    /// match it; if none do, fall back to the unfiltered set rather than
    /// losing the substitution entirely over a capacity mismatch.
    private static func preferringFingerCapacity(_ holds: [BoardHold], target: HoldTarget) -> [BoardHold] {
        guard let capacity = target.fingerCapacity else { return holds }
        let matching = holds.filter { $0.fingerCapacity == capacity }
        return matching.isEmpty ? holds : matching
    }

    private static func crossKindPockets(for target: HoldTarget, on board: TrainingBoard) -> [BoardHold] {
        let pockets = board.holds.filter { $0.kind == .pocket }
        guard let capacity = target.fingerCapacity else { return pockets }
        return pockets.filter { $0.fingerCapacity == capacity }
    }
}

struct WorkoutActivityRecorder {
    func segments(
        for plan: TrainingPlan,
        on board: TrainingBoard,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:]
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
                guard !segment.targets.isEmpty else { throw WorkoutActivityRecordingError.unresolvedTarget(stepID: step.id, segmentIndex: index) }
                let holdsByTarget = segment.targets.map {
                    BoardTargetResolver.substituteHolds(for: $0, on: board)
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
                            durationSeconds: duration
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
                        durationSeconds: duration
                    )
                }
            }
        }
        return result
    }

    func metadata(
        for plan: TrainingPlan,
        on board: TrainingBoard,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:],
        stepMeasurements: [WorkoutStepMeasurement] = []
    ) throws -> WorkoutActivityMetadata {
        WorkoutActivityMetadata(
            segments: try segments(
                for: plan,
                on: board,
                stopwatchDurations: stopwatchDurations
            ),
            measurements: measuredSteps(from: stepMeasurements)
        )
    }

    private func measuredSteps(
        from measurements: [WorkoutStepMeasurement]
    ) -> [RecordedActivityStepMeasurement]? {
        let result = measurements.compactMap { measurement -> RecordedActivityStepMeasurement? in
            guard measurement.sampleCount > 0 else { return nil }
            let peakLoadKGF = measurement.peakLoadKGF.flatMap {
                $0.isFinite && $0 >= 0 ? $0 : nil
            }
            let loadedDuration = measurement.actualLoadedDuration
            let actualLoadedDurationSeconds = loadedDuration.isFinite && loadedDuration >= 0
                ? loadedDuration
                : nil
            guard peakLoadKGF != nil || actualLoadedDurationSeconds != nil else { return nil }
            return RecordedActivityStepMeasurement(
                stepID: measurement.stepID,
                peakLoadKGF: peakLoadKGF,
                actualLoadedDurationSeconds: actualLoadedDurationSeconds
            )
        }
        return result.isEmpty ? nil : result
    }

    func json(for metadata: WorkoutActivityMetadata) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(metadata)
        return String(decoding: data, as: UTF8.self)
    }
}
