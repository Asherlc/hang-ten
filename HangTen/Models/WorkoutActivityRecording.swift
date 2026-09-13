import Foundation

struct ResolvedContactSnapshot: Codable, Hashable {
    let boardID: String
    let revisionID: String
    let modelSHA256: String?
    let requirement: ContactRequirement
    let contactIDs: [String]
}

enum RecordedActivityTarget: Codable, Hashable {
    case resolvedContacts(ResolvedContactSnapshot)
    case selfSelected

    var resolvedContactSnapshot: ResolvedContactSnapshot? {
        guard case .resolvedContacts(let snapshot) = self else { return nil }
        return snapshot
    }

    private enum Kind: String, Codable {
        case resolvedContacts
        case selfSelected
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case kind, resolution
    }

    init(from decoder: Decoder) throws {
        let rawContainer = try decoder.container(keyedBy: ActivityCodingKey.self)
        let allowedKeys = Set(CodingKeys.allCases.map(\.rawValue))
        if let unknownKey = rawContainer.allKeys.first(where: {
            !allowedKeys.contains($0.stringValue)
        }) {
            throw DecodingError.dataCorruptedError(
                forKey: unknownKey,
                in: rawContainer,
                debugDescription: "Unsupported recorded activity target field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        switch try container.decode(Kind.self, forKey: .kind) {
        case .resolvedContacts:
            self = .resolvedContacts(
                try container.decode(ResolvedContactSnapshot.self, forKey: .resolution)
            )
        case .selfSelected:
            guard !container.contains(.resolution) else {
                throw DecodingError.dataCorruptedError(
                    forKey: .resolution,
                    in: container,
                    debugDescription: "Self-selected activity targets cannot contain a contact resolution."
                )
            }
            self = .selfSelected
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .resolvedContacts(let snapshot):
            try container.encode(Kind.resolvedContacts, forKey: .kind)
            try container.encode(snapshot, forKey: .resolution)
        case .selfSelected:
            try container.encode(Kind.selfSelected, forKey: .kind)
        }
    }
}

struct RecordedActivitySegment: Codable, Hashable {
    let stepID: String
    let stepNumber: Int
    let kind: WorkoutSegmentKind
    let target: RecordedActivityTarget?
    let durationSeconds: TimeInterval?

    init(
        stepID: String,
        stepNumber: Int,
        kind: WorkoutSegmentKind,
        target: RecordedActivityTarget?,
        durationSeconds: TimeInterval?
    ) {
        self.stepID = stepID
        self.stepNumber = stepNumber
        self.kind = kind
        self.target = target
        self.durationSeconds = durationSeconds
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case stepID, stepNumber, kind, target, durationSeconds
    }

    init(from decoder: Decoder) throws {
        let rawContainer = try decoder.container(keyedBy: ActivityCodingKey.self)
        let allowedKeys = Set(CodingKeys.allCases.map(\.rawValue))
        if let unknownKey = rawContainer.allKeys.first(where: {
            !allowedKeys.contains($0.stringValue)
        }) {
            throw DecodingError.dataCorruptedError(
                forKey: unknownKey,
                in: rawContainer,
                debugDescription: "Unsupported recorded activity field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        stepID = try container.decode(String.self, forKey: .stepID)
        stepNumber = try container.decode(Int.self, forKey: .stepNumber)
        kind = try container.decode(WorkoutSegmentKind.self, forKey: .kind)
        target = try container.decodeIfPresent(RecordedActivityTarget.self, forKey: .target)
        durationSeconds = try container.decodeIfPresent(
            TimeInterval.self,
            forKey: .durationSeconds
        )
        switch kind {
        case .work where target == nil:
            throw DecodingError.dataCorruptedError(
                forKey: .target,
                in: container,
                debugDescription: "Recorded work activity requires an explicit target."
            )
        case .rest where target != nil:
            throw DecodingError.dataCorruptedError(
                forKey: .target,
                in: container,
                debugDescription: "Recorded rest activity cannot contain a target."
            )
        default:
            break
        }
    }

    func encode(to encoder: Encoder) throws {
        switch kind {
        case .work where target == nil:
            throw EncodingError.invalidValue(
                self,
                EncodingError.Context(
                    codingPath: encoder.codingPath,
                    debugDescription: "Recorded work activity requires an explicit target."
                )
            )
        case .rest where target != nil:
            throw EncodingError.invalidValue(
                self,
                EncodingError.Context(
                    codingPath: encoder.codingPath,
                    debugDescription: "Recorded rest activity cannot contain a target."
                )
            )
        default:
            break
        }

        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(stepID, forKey: .stepID)
        try container.encode(stepNumber, forKey: .stepNumber)
        try container.encode(kind, forKey: .kind)
        try container.encodeIfPresent(target, forKey: .target)
        try container.encodeIfPresent(durationSeconds, forKey: .durationSeconds)
    }
}

struct RecordedActivityStepMeasurement: Codable, Hashable {
    let stepID: String
    let peakLoadKGF: Double?
    let actualLoadedDurationSeconds: TimeInterval?
}

struct WorkoutActivityMetadata: Codable, Hashable {
    static let currentVersion = 2

    let version: Int
    let segments: [RecordedActivitySegment]
    let measurements: [RecordedActivityStepMeasurement]?

    init(
        segments: [RecordedActivitySegment],
        measurements: [RecordedActivityStepMeasurement]? = nil
    ) {
        version = Self.currentVersion
        self.segments = segments
        self.measurements = measurements
    }

    private enum CodingKeys: String, CodingKey {
        case version, segments, measurements
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        version = try container.decode(Int.self, forKey: .version)
        guard version == Self.currentVersion else {
            throw DecodingError.dataCorruptedError(
                forKey: .version,
                in: container,
                debugDescription: "Unsupported workout activity version \(version)."
            )
        }
        segments = try container.decode([RecordedActivitySegment].self, forKey: .segments)
        measurements = try container.decodeIfPresent(
            [RecordedActivityStepMeasurement].self,
            forKey: .measurements
        )
    }
}

private struct ActivityCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
        intValue = nil
    }

    init?(intValue: Int) {
        stringValue = String(intValue)
        self.intValue = intValue
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
        return contact.gripTypes.contains(stepGripType)
    }

    private static func applying(
        _ side: WorkoutSide,
        to candidates: [PhysicalContact]
    ) -> [PhysicalContact] {
        guard side != .both else { return candidates }
        let requiredSide: ContactSide = side == .left ? .left : .right
        return candidates.filter { $0.side == requiredSide }
    }

    private static func isDocumentedPair(
        _ first: PhysicalContact,
        _ second: PhysicalContact
    ) -> Bool {
        first.pairedContactID == second.id
            && second.pairedContactID == first.id
            && Set([first.side, second.side]) == Set([.left, .right])
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
                            target: nil,
                            durationSeconds: duration
                        )
                    )
                    continue
                }
                guard !segment.targets.isEmpty else {
                    guard allowsSourceLinkedUntargetedWork(segment, in: step, plan: plan) else {
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
                            target: .selfSelected,
                            durationSeconds: duration
                        )
                    )
                    continue
                }

                for requirement in segment.targets {
                    let contacts: [PhysicalContact]
                    do {
                        contacts = try ContactResolver.resolve(
                            requirement,
                            step: step,
                            board: board
                        )
                    } catch {
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
                            target: .resolvedContacts(
                                ResolvedContactSnapshot(
                                    boardID: board.id,
                                    revisionID: board.revisionID,
                                    modelSHA256: modelSHA256(for: board.defaultPresentation),
                                    requirement: requirement,
                                    contactIDs: contacts.map(\.id)
                                )
                            ),
                            durationSeconds: duration
                        )
                    )
                }
            }
        }
        return result
    }

    private func modelSHA256(for presentation: BoardPresentation) -> String? {
        guard case .model(let media) = presentation.media else { return nil }
        return media.descriptor.modelSHA256
    }

    private func allowsSourceLinkedUntargetedWork(
        _ segment: WorkoutSegment,
        in step: WorkoutStep,
        plan: TrainingPlan
    ) -> Bool {
        plan.provenance != .custom
            && plan.sourceURL != nil
            && step.phase != .rest
            && step.phase != .conditioning
            && segment.kind == .work
            && segment.targets.isEmpty
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
