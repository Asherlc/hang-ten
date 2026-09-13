import Foundation

struct RecordedActivitySegment: Codable, Hashable {
    let stepID: String
    let stepNumber: Int
    let kind: WorkoutSegmentKind
    let holdIDs: [String]
    let holdType: String?
    let sizeMillimeters: Double?
    let durationSeconds: TimeInterval?

    enum CodingKeys: String, CodingKey {
        case stepID, stepNumber, kind, holdIDs, holdType, sizeMillimeters, durationSeconds
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

enum ContactResolutionError: LocalizedError, Equatable {
    case noMatches
    case ambiguousSingle(candidateCount: Int)
    case invalidBilateralPair(candidateCount: Int)

    var errorDescription: String? {
        switch self {
        case .noMatches:
            "No physical contact satisfies the workout requirement."
        case .ambiguousSingle:
            "The workout requirement does not identify exactly one physical contact."
        case .invalidBilateralPair:
            "The workout requirement does not identify exactly one documented bilateral pair."
        }
    }
}

enum ContactResolver {
    static func resolve(
        _ requirement: ContactRequirement,
        step: WorkoutStep,
        board: BoardRevision
    ) throws -> [PhysicalContact] {
        let positionContactIDs = contactIDsForDefaultPosition(on: board)
        var candidates = board.contacts.filter { contact in
            positionContactIDs.contains(contact.id)
                && matches(requirement, contact: contact)
                && matches(stepGripType: step.gripType, contact: contact)
        }
        candidates = applying(step.side, to: candidates)

        switch requirement.selection {
        case .allMatching:
            guard !candidates.isEmpty else { throw ContactResolutionError.noMatches }
        case .single:
            guard candidates.count == 1 else {
                throw ContactResolutionError.ambiguousSingle(candidateCount: candidates.count)
            }
        case .bilateralPair:
            guard step.handUse == .double,
                  step.side == .both,
                  candidates.count == 2,
                  isDocumentedPair(candidates[0], candidates[1]) else {
                throw ContactResolutionError.invalidBilateralPair(candidateCount: candidates.count)
            }
        }

        return candidates
    }

    static func resolve(
        _ requirements: [ContactRequirement],
        step: WorkoutStep,
        board: BoardRevision
    ) throws -> [PhysicalContact] {
        let resolvedIDs = try requirements.reduce(into: Set<String>()) { result, requirement in
            result.formUnion(try resolve(requirement, step: step, board: board).map(\.id))
        }
        return board.contacts.filter { resolvedIDs.contains($0.id) }
    }

    private static func contactIDsForDefaultPosition(on board: BoardRevision) -> Set<String> {
        if let position = board.positions.first(where: {
            $0.presentationID == board.defaultPresentation.id
        }) {
            if !position.contactIDsWereExplicitlyAuthored {
                return board.defaultPresentation.contactIDs
            }
            return Set(position.contactIDs)
        }
        return board.defaultPresentation.contactIDs
    }

    private static func matches(
        _ requirement: ContactRequirement,
        contact: PhysicalContact
    ) -> Bool {
        if let kind = requirement.kind, contact.kind != kind { return false }
        if !requirement.requiredFeatures.isSubset(of: contact.features) { return false }
        if let fingerCapacity = requirement.fingerCapacity,
           contact.fingerCapacity != fingerCapacity { return false }
        if let handCapacity = requirement.handCapacity,
           contact.handCapacity != handCapacity { return false }
        if !requirement.compatibleGripTypes.isEmpty,
           requirement.compatibleGripTypes.isDisjoint(with: contact.gripTypes) {
            return false
        }
        if let requiredDepth = requirement.depthRangeMillimeters {
            guard let contactDepth = contact.depthRangeMillimeters,
                  contactDepth.upperBound >= requiredDepth.minimum,
                  contactDepth.lowerBound <= requiredDepth.maximum else {
                return false
            }
        }
        return true
    }

    private static func matches(
        stepGripType: GripType?,
        contact: PhysicalContact
    ) -> Bool {
        guard let stepGripType else { return true }
        return contact.gripTypes.isEmpty || contact.gripTypes.contains(stepGripType)
    }

    private static func applying(
        _ side: WorkoutSide,
        to candidates: [PhysicalContact]
    ) -> [PhysicalContact] {
        guard side != .both else { return candidates }
        let requiredSide: ContactSide = side == .left ? .left : .right
        let sidedCandidates = candidates.filter { $0.side != nil }
        guard !sidedCandidates.isEmpty else { return candidates }
        return sidedCandidates.filter { $0.side == requiredSide }
    }

    private static func isDocumentedPair(
        _ first: PhysicalContact,
        _ second: PhysicalContact
    ) -> Bool {
        if first.pairedContactID == second.id,
           second.pairedContactID == first.id {
            return true
        }

        let sidesAreCompatible = Set([first.side, second.side]) == Set([.left, .right])
            || (first.side == nil && second.side == nil)
        return sidesAreCompatible
            && first.kind == second.kind
            && first.features == second.features
            && first.fingerCapacity == second.fingerCapacity
            && first.handCapacity == second.handCapacity
            && first.depthRangeMillimeters == second.depthRangeMillimeters
            && first.gripTypes == second.gripTypes
    }
}

struct WorkoutActivityRecorder {
    func segments(
        for plan: TrainingPlan,
        on board: BoardRevision,
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
                            guard observed.isFinite, observed >= 0 else {
                                throw WorkoutActivityRecordingError.invalidObservedDuration(key)
                            }
                            duration = observed
                        } else {
                            duration = nil
                        }
                    }
                }
                if segment.kind == .rest {
                    result.append(
                        RecordedActivitySegment(
                            stepID: step.id,
                            stepNumber: step.number,
                            kind: .rest,
                            holdIDs: [],
                            holdType: nil,
                            sizeMillimeters: nil,
                            durationSeconds: duration
                        )
                    )
                    continue
                }
                guard !segment.targets.isEmpty else {
                    guard allowsUntargetedRPTCSelfSelectedWork(segment, in: step, plan: plan) else {
                        throw WorkoutActivityRecordingError.unresolvedTarget(
                            stepID: step.id,
                            segmentIndex: index
                        )
                    }
                    result.append(
                        RecordedActivitySegment(
                            stepID: step.id,
                            stepNumber: step.number,
                            kind: .work,
                            holdIDs: [],
                            holdType: nil,
                            sizeMillimeters: nil,
                            durationSeconds: duration
                        )
                    )
                    continue
                }

                let holds: [PhysicalContact]
                do {
                    holds = try ContactResolver.resolve(segment.targets, step: step, board: board)
                } catch {
                    throw WorkoutActivityRecordingError.unresolvedTarget(
                        stepID: step.id,
                        segmentIndex: index
                    )
                }

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

                var groups: [(HoldKind, Double?, [String])] = []
                for hold in holds {
                    let recordedDepth = hold.depthRangeMillimeters.flatMap { range in
                        range.lowerBound == range.upperBound ? range.lowerBound : nil
                    }
                    let descriptor = (hold.kind, recordedDepth)
                    if let groupIndex = groups.firstIndex(where: {
                        $0.0 == descriptor.0 && $0.1 == descriptor.1
                    }) {
                        groups[groupIndex].2.append(hold.id)
                    } else {
                        groups.append((hold.kind, recordedDepth, [hold.id]))
                    }
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

    private func allowsUntargetedRPTCSelfSelectedWork(
        _ segment: WorkoutSegment,
        in step: WorkoutStep,
        plan: TrainingPlan
    ) -> Bool {
        let expectedStepIDs = Set((1...7).map { "rptc-repeaters-set-rep-\($0).segment-1" })
        return plan.id == LegacyPlanSeedCatalog.rptcRepeaters.id
            && plan.provenance == .official
            && plan.sourceURL == LegacyPlanSeedCatalog.rptcRepeaters.sourceURL
            && plan.boardID == nil
            && plan.steps.count == 15
            && expectedStepIDs.contains(step.id)
            && step.phase == .hang
            && step.targets.isEmpty
            && step.duration == 7
            && step.timedWorkDuration == 7
            && step.segments == [segment]
            && segment.kind == .work
            && segment.targets.isEmpty
            && segment.timing == .fixed
            && segment.duration == 7
    }

    func metadata(
        for plan: TrainingPlan,
        on board: BoardRevision,
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
