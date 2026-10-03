import Foundation

struct ResolvedContactSnapshot: Codable, Hashable {
    let boardID: String
    let revisionID: String
    let modelSHA256: String?
    let requirement: ContactRequirement
    let contactIDs: [String]
    let positionID: String?
    /// Present for catalog task recordings; legacy snapshots keep one requirement.
    let handTargets: [PlanHandTarget]?

    init(
        boardID: String,
        revisionID: String,
        modelSHA256: String?,
        requirement: ContactRequirement,
        contactIDs: [String],
        positionID: String? = nil,
        handTargets: [PlanHandTarget]? = nil
    ) {
        self.boardID = boardID
        self.revisionID = revisionID
        self.modelSHA256 = modelSHA256
        self.requirement = requirement
        self.contactIDs = contactIDs
        self.positionID = positionID
        self.handTargets = handTargets
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case boardID, revisionID, modelSHA256, requirement, contactIDs, positionID, handTargets
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
                debugDescription: "Unsupported resolved contact snapshot field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        boardID = try container.decode(String.self, forKey: .boardID)
        revisionID = try container.decode(String.self, forKey: .revisionID)
        modelSHA256 = try container.decodeIfPresent(String.self, forKey: .modelSHA256)
        requirement = try container.decode(ContactRequirement.self, forKey: .requirement)
        contactIDs = try container.decode([String].self, forKey: .contactIDs)
        positionID = try container.decodeIfPresent(String.self, forKey: .positionID)
        handTargets = try container.decodeIfPresent([PlanHandTarget].self, forKey: .handTargets)
    }
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
    /// The actual hand assignment for work. This is separate from a plan's
    /// capability metadata so completed activity can be tracked by side.
    let handUse: WorkoutHandUse?
    let side: WorkoutSide?

    init(
        stepID: String,
        stepNumber: Int,
        kind: WorkoutSegmentKind,
        target: RecordedActivityTarget?,
        durationSeconds: TimeInterval?,
        handUse: WorkoutHandUse? = nil,
        side: WorkoutSide? = nil
    ) {
        self.stepID = stepID
        self.stepNumber = stepNumber
        self.kind = kind
        self.target = target
        self.durationSeconds = durationSeconds
        self.handUse = handUse
        self.side = side
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case stepID, stepNumber, kind, target, durationSeconds, handUse, side
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
        handUse = try container.decodeIfPresent(WorkoutHandUse.self, forKey: .handUse)
        side = try container.decodeIfPresent(WorkoutSide.self, forKey: .side)
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
        case .rest where handUse != nil || side != nil:
            throw DecodingError.dataCorruptedError(
                forKey: .handUse,
                in: container,
                debugDescription: "Recorded rest activity cannot contain hand-use metadata."
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
        case .rest where handUse != nil || side != nil:
            throw EncodingError.invalidValue(
                self,
                EncodingError.Context(
                    codingPath: encoder.codingPath,
                    debugDescription: "Recorded rest activity cannot contain hand-use metadata."
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
        try container.encodeIfPresent(handUse, forKey: .handUse)
        try container.encodeIfPresent(side, forKey: .side)
    }
}

struct RecordedActivityStepMeasurement: Codable, Hashable {
    let stepID: String
    let peakLoadKGF: Double?
    let actualLoadedDurationSeconds: TimeInterval?

    init(
        stepID: String,
        peakLoadKGF: Double?,
        actualLoadedDurationSeconds: TimeInterval?
    ) {
        self.stepID = stepID
        self.peakLoadKGF = peakLoadKGF
        self.actualLoadedDurationSeconds = actualLoadedDurationSeconds
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case stepID, peakLoadKGF, actualLoadedDurationSeconds
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
                debugDescription: "Unsupported activity measurement field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        stepID = try container.decode(String.self, forKey: .stepID)
        peakLoadKGF = try container.decodeIfPresent(Double.self, forKey: .peakLoadKGF)
        actualLoadedDurationSeconds = try container.decodeIfPresent(
            TimeInterval.self,
            forKey: .actualLoadedDurationSeconds
        )
    }
}

struct WorkoutActivityMetadata: Codable, Hashable {
    static let currentVersion = 3

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

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case version, segments, measurements
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
                debugDescription: "Unsupported workout activity metadata field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        version = try container.decode(Int.self, forKey: .version)
        guard version == 2 || version == Self.currentVersion else {
            throw DecodingError.dataCorruptedError(
                forKey: .version,
                in: container,
                debugDescription: "Unsupported workout activity version \(version)."
            )
        }
        if version == 2 {
            segments = try container.decode([LegacyRecordedActivitySegment].self, forKey: .segments)
                .map(RecordedActivitySegment.init(legacy:))
        } else {
            segments = try container.decode([RecordedActivitySegment].self, forKey: .segments)
        }
        measurements = try container.decodeIfPresent(
            [RecordedActivityStepMeasurement].self,
            forKey: .measurements
        )
    }
}

private struct LegacyRecordedActivitySegment: Codable {
    let stepID: String
    let stepNumber: Int
    let kind: WorkoutSegmentKind
    let target: RecordedActivityTarget?
    let durationSeconds: TimeInterval?

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
                debugDescription: "Unsupported legacy recorded activity field \(unknownKey.stringValue)."
            )
        }
        let container = try decoder.container(keyedBy: CodingKeys.self)
        stepID = try container.decode(String.self, forKey: .stepID)
        stepNumber = try container.decode(Int.self, forKey: .stepNumber)
        kind = try container.decode(WorkoutSegmentKind.self, forKey: .kind)
        target = try container.decodeIfPresent(RecordedActivityTarget.self, forKey: .target)
        durationSeconds = try container.decodeIfPresent(TimeInterval.self, forKey: .durationSeconds)
    }
}

private extension RecordedActivitySegment {
    init(legacy: LegacyRecordedActivitySegment) {
        self.init(
            stepID: legacy.stepID,
            stepNumber: legacy.stepNumber,
            kind: legacy.kind,
            target: legacy.target,
            durationSeconds: legacy.durationSeconds
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
    case handSideRequired(stepID: String)
    case invalidObservedDuration(WorkoutActivitySegmentKey)

    var errorDescription: String? {
        switch self {
        case .unresolvedTarget:
            "Hang Ten could not match a workout activity to the selected board."
        case .handSideRequired:
            "Choose a left or right hand before starting this routine."
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
            "Hang Ten could not select a physical contact for the workout requirement."
        case .invalidBilateralPair:
            "Hang Ten could not form a geometrically valid bilateral pair for the workout requirement."
        }
    }
}

enum ContactResolver {
    struct Selection {
        let contacts: [PhysicalContact]
        let positionID: String?
    }

    /// Assigns one contact to each hand in a simultaneous plan task. Repeated
    /// IDs mean two hands share a capacity-two contact, or use the same contact
    /// on separate copies of a one-hand board.
    static func resolve(
        _ task: [PlanHandTarget],
        step: WorkoutStep,
        board: BoardRevision
    ) throws -> [PhysicalContact] {
        try resolveSelection(task, step: step, board: board).contacts
    }

    static func resolveSelection(
        _ task: [PlanHandTarget], step: WorkoutStep, board: BoardRevision
    ) throws -> Selection {
        guard board.positions.contains(where: { !$0.effectiveDepths.isEmpty }) else {
            let available = board.contacts.filter { contactIDsForDefaultPosition(on: board).contains($0.id) }
            return Selection(contacts: try resolveTaskCandidates(task, step: step, board: board,
                presentation: board.defaultPresentation, available: available), positionID: nil)
        }
        let preferred = board.positions.filter { $0.presentationID == board.defaultPresentation.id }
            + board.positions.filter { $0.presentationID != board.defaultPresentation.id }
        for position in preferred {
            guard let presentation = board.presentation(id: position.presentationID),
                  let contacts = try? resolveTaskCandidates(task, step: step, board: board,
                    presentation: presentation, available: board.contacts(inPosition: position.id)) else { continue }
            return Selection(contacts: contacts, positionID: position.id)
        }
        throw ContactResolutionError.noMatches
    }

    private static func resolveTaskCandidates(
        _ task: [PlanHandTarget], step: WorkoutStep, board: BoardRevision,
        presentation: BoardPresentation, available: [PhysicalContact]
    ) throws -> [PhysicalContact] {
        guard (1...2).contains(task.count) else { throw ContactResolutionError.noMatches }
        let candidates = task.map { hand in
            available.filter { contact in
                matches(hand.target?.legacyRequirement ?? ContactRequirement(), contact: contact)
                    && matches(stepGripType: step.gripType, contact: contact)
            }
        }
        guard candidates.allSatisfy({ !$0.isEmpty }) else { throw ContactResolutionError.noMatches }

        if task.count == 1 {
            let narrowed = board.isOneHanded ? candidates[0] : candidates[0].filter {
                contact($0, fits: task[0].side, in: presentation)
            }
            return try singleCandidate(from: narrowed, in: presentation)
        }

        let firstSide = task[0].side ?? (task[1].side == .left ? .right : .left)
        let secondSide = task[1].side ?? (firstSide == .left ? .right : .left)
        guard firstSide != secondSide else {
            throw ContactResolutionError.invalidBilateralPair(candidateCount: 0)
        }

        if board.isOneHanded {
            return try candidates.map { try singleCandidate(from: $0, in: presentation)[0] }
        }

        let firstCandidates = candidates[0].filter { contact($0, fits: firstSide, in: presentation) }
        let secondCandidates = candidates[1].filter { contact($0, fits: secondSide, in: presentation) }
        let pairs = firstCandidates.flatMap { first in
            secondCandidates.compactMap { second -> (PhysicalContact, PhysicalContact, CGFloat)? in
                guard first.id != second.id,
                      let firstFrame = first.resolvedFrame(in: presentation),
                      let secondFrame = second.resolvedFrame(in: presentation) else {
                    return nil
                }
                return (first, second, abs(firstFrame.rect.midX - secondFrame.rect.midX))
            }
        }
        if let best = pairs.sorted(by: { lhs, rhs in
            if lhs.2 != rhs.2 { return lhs.2 > rhs.2 }
            if lhs.0.id != rhs.0.id { return lhs.0.id < rhs.0.id }
            return lhs.1.id < rhs.1.id
        }).first {
            return [best.0, best.1]
        }

        let shared = candidates[0].filter { first in
            first.handCapacity == 2 && candidates[1].contains(where: { $0.id == first.id })
        }
        if let selected = try? singleCandidate(from: shared, in: presentation).first {
            return [selected, selected]
        }
        throw ContactResolutionError.invalidBilateralPair(candidateCount: candidates[0].count + candidates[1].count)
    }

    static func resolve(
        _ tasks: [[PlanHandTarget]],
        step: WorkoutStep,
        board: BoardRevision
    ) throws -> [[PhysicalContact]] {
        try tasks.map { try resolve($0, step: step, board: board) }
    }

    static func resolve(
        _ target: WorkoutSegmentTarget,
        step: WorkoutStep,
        board: BoardRevision
    ) throws -> [[PhysicalContact]] {
        switch target {
        case .selfSelected: return []
        case .requirements(let requirements):
            let selection = try resolveSelection(requirements, step: step, board: board)
            return try requirements.map {
                try resolveSelection($0, step: step, board: board, inPosition: selection.positionID).contacts
            }
        case .tasks(let tasks):
            return try resolve(tasks, step: step, board: board)
        }
    }

    private static func contact(
        _ contact: PhysicalContact,
        fits side: WorkoutSide?,
        in presentation: BoardPresentation
    ) -> Bool {
        guard let side else { return true }
        if let authored = contact.side { return authored.rawValue == side.rawValue }
        // Repeated model instances share a local descriptor frame. Their
        // authored equipment-object IDs identify the physical left/right unit.
        if contact.equipmentObjectID == "left-ring" { return side == .left }
        if contact.equipmentObjectID == "right-ring" { return side == .right }
        guard let frame = contact.resolvedFrame(in: presentation) else { return false }
        if frame.rect.minX <= 0.5 && frame.rect.maxX >= 0.5 { return true }
        return side == .left ? frame.rect.midX < 0.5 : frame.rect.midX > 0.5
    }

    static func resolve(
        _ requirement: ContactRequirement,
        step: WorkoutStep,
        board: BoardRevision
    ) throws -> [PhysicalContact] {
        try resolveSelection(requirement, step: step, board: board).contacts
    }

    static func resolveSelection(_ requirement: ContactRequirement, step: WorkoutStep, board: BoardRevision,
                                 inPosition positionID: String? = nil) throws -> Selection {
        if let positionID {
            guard let position = board.position(id: positionID),
                  let presentation = board.presentation(id: position.presentationID) else { throw ContactResolutionError.noMatches }
            return Selection(contacts: try resolveCandidates(requirement, step: step, presentation: presentation,
                contacts: board.contacts(inPosition: positionID)), positionID: positionID)
        }
        guard board.positions.contains(where: { !$0.effectiveDepths.isEmpty }) else {
            return Selection(contacts: try resolveCandidates(requirement, step: step, presentation: board.defaultPresentation,
                contacts: board.contacts.filter { contactIDsForDefaultPosition(on: board).contains($0.id) }), positionID: nil)
        }
        return try resolveSelection([requirement], step: step, board: board)
    }

    private static func resolveCandidates(_ requirement: ContactRequirement, step: WorkoutStep,
                                          presentation: BoardPresentation, contacts: [PhysicalContact]) throws -> [PhysicalContact] {
        var candidates = contacts.filter { contact in
            matches(requirement, contact: contact)
                && matches(stepGripType: step.gripType, contact: contact)
        }

        guard !candidates.isEmpty else {
            throw ContactResolutionError.noMatches
        }

        switch requirement.selection {
        case .single:
            candidates = try singleCandidate(from: candidates, in: presentation)
        case .bilateralPair:
            guard step.handUse == .double,
                  step.side == .both else {
                throw ContactResolutionError.invalidBilateralPair(candidateCount: candidates.count)
            }
            guard candidates.count >= 2,
                  let pair = outermostPair(from: candidates, in: presentation) else {
                throw ContactResolutionError.invalidBilateralPair(candidateCount: candidates.count)
            }
            candidates = pair
        }

        return candidates
    }

    static func resolve(
        _ requirements: [ContactRequirement],
        step: WorkoutStep,
        board: BoardRevision
    ) throws -> [PhysicalContact] {
        if board.positions.contains(where: { !$0.effectiveDepths.isEmpty }) {
            return try resolveSelection(requirements, step: step, board: board).contacts
        }
        let resolvedIDs = try requirements.reduce(into: Set<String>()) { result, requirement in
            result.formUnion(try resolve(requirement, step: step, board: board).map(\.id))
        }
        return board.contacts.filter { resolvedIDs.contains($0.id) }
    }

    static func resolveSelection(_ requirements: [ContactRequirement], step: WorkoutStep, board: BoardRevision) throws -> Selection {
        guard board.positions.contains(where: { !$0.effectiveDepths.isEmpty }) else {
            return Selection(contacts: try resolve(requirements, step: step, board: board), positionID: nil)
        }
        let preferred = board.positions.filter { $0.presentationID == board.defaultPresentation.id }
            + board.positions.filter { $0.presentationID != board.defaultPresentation.id }
        for position in preferred {
            guard let presentation = board.presentation(id: position.presentationID) else { continue }
            let available = board.contacts(inPosition: position.id)
            var selected = Set<String>()
            var valid = true
            for requirement in requirements {
                guard let contacts = try? resolveCandidates(requirement, step: step, presentation: presentation, contacts: available) else {
                    valid = false; break
                }
                selected.formUnion(contacts.map(\.id))
            }
            if valid { return Selection(contacts: available.filter { selected.contains($0.id) }, positionID: position.id) }
        }
        throw ContactResolutionError.noMatches
    }

    /// Every contact shown by the default presentation, including multi-position
    /// model boards where each authored position only lists a subset.
    private static func contactIDsForDefaultPosition(on board: BoardRevision) -> Set<String> {
        board.defaultPresentation.contactIDs
    }

    private static func matches(
        _ requirement: ContactRequirement,
        contact: PhysicalContact
    ) -> Bool {
        if let contactID = requirement.contactID, contact.id != contactID { return false }
        if let kind = requirement.kind, contact.kind != kind { return false }
        if let shape = requirement.shape, contact.shape != shape { return false }
        if let depth = requirement.depth, !depth.matches(contact.depth) { return false }
        if let fingerCapacity = requirement.fingerCapacity,
           contact.fingerCapacity != fingerCapacity { return false }
        if let handCapacity = requirement.handCapacity,
           contact.handCapacity != handCapacity { return false }
        return true
    }

    private static func matches(
        stepGripType: GripType?,
        contact: PhysicalContact
    ) -> Bool {
        guard let stepGripType else { return true }
        // Empty grip metadata means the contact does not constrain grip; only
        // non-empty inventories can reject an incompatible step grip.
        guard !contact.gripTypes.isEmpty else { return true }
        return contact.gripTypes.contains(stepGripType)
    }

    private static func singleCandidate(
        from candidates: [PhysicalContact],
        in presentation: BoardPresentation
    ) throws -> [PhysicalContact] {
        guard candidates.count > 1 else {
            guard candidates.count == 1 else {
                throw ContactResolutionError.ambiguousSingle(candidateCount: candidates.count)
            }
            return candidates
        }

        let framedCandidates = candidates.compactMap { contact -> (contact: PhysicalContact, frame: HoldFrame)? in
            guard let frame = contact.resolvedFrame(in: presentation) else {
                return nil
            }
            return (contact, frame)
        }
        guard framedCandidates.count == candidates.count,
              let selected = framedCandidates.min(by: { lhs, rhs in
                  let lhsDistance = abs(lhs.frame.rect.midX - 0.5)
                  let rhsDistance = abs(rhs.frame.rect.midX - 0.5)
                  if lhsDistance == rhsDistance {
                      return lhs.contact.id < rhs.contact.id
                  }
                  return lhsDistance < rhsDistance
              }) else {
            throw ContactResolutionError.ambiguousSingle(candidateCount: candidates.count)
        }
        return [selected.contact]
    }

    private static func outermostPair(
        from candidates: [PhysicalContact],
        in presentation: BoardPresentation
    ) -> [PhysicalContact]? {
        if case .model(let media) = presentation.media,
           let instances = media.instances, instances.count == 2, candidates.count == 2 {
            // Descriptor frames describe one reusable unit. Explicit slot maps
            // identify the corresponding grip across the two physical units.
            guard Set(instances.map(\.equipmentObjectID)).count == 2,
                  instances.allSatisfy({ !$0.equipmentObjectID.isEmpty }),
                  Set(candidates.map(\.id)).count == 2 else { return nil }
            var paired: [(contact: PhysicalContact, slotID: String)] = []
            for instance in instances {
                let owned = candidates.filter { $0.equipmentObjectID == instance.equipmentObjectID }
                guard owned.count == 1, let contact = owned.first else { return nil }
                let slots = instance.contactIDsBySlotID.filter { $0.value == contact.id }
                let mappingCount = instances.reduce(0) { count, item in
                    count + item.contactIDsBySlotID.values.filter { $0 == contact.id }.count
                }
                guard slots.count == 1, mappingCount == 1, let slotID = slots.keys.first else { return nil }
                paired.append((contact, slotID))
            }
            let first = paired[0], second = paired[1]
            guard first.slotID == second.slotID,
                  first.contact.kind == second.contact.kind,
                  first.contact.shape == second.contact.shape,
                  first.contact.depth == second.contact.depth,
                  first.contact.fingerCapacity == second.contact.fingerCapacity,
                  first.contact.handCapacity == second.contact.handCapacity else { return nil }
            return paired.map(\.contact)
        }

        let framedCandidates = candidates.compactMap { contact -> (contact: PhysicalContact, frame: HoldFrame)? in
            guard let frame = contact.resolvedFrame(in: presentation) else {
                return nil
            }
            return (contact, frame)
        }
        guard framedCandidates.count == candidates.count else { return nil }

        let leftmost = framedCandidates.min { lhs, rhs in
            if lhs.frame.rect.midX == rhs.frame.rect.midX {
                return lhs.contact.id < rhs.contact.id
            }
            return lhs.frame.rect.midX < rhs.frame.rect.midX
        }
        let rightmost = framedCandidates.max { lhs, rhs in
            if lhs.frame.rect.midX == rhs.frame.rect.midX {
                return lhs.contact.id < rhs.contact.id
            }
            return lhs.frame.rect.midX < rhs.frame.rect.midX
        }
        let horizontalMidpoint: CGFloat = 0.5
        guard let leftmost,
              let rightmost,
              leftmost.contact.id != rightmost.contact.id,
              leftmost.frame.rect.midX < horizontalMidpoint,
              rightmost.frame.rect.midX > horizontalMidpoint,
              leftmost.contact.kind == rightmost.contact.kind,
              leftmost.contact.shape == rightmost.contact.shape,
              leftmost.contact.depth == rightmost.contact.depth,
              leftmost.contact.fingerCapacity == rightmost.contact.fingerCapacity,
              leftmost.contact.handCapacity == rightmost.contact.handCapacity else {
            return nil
        }
        return [leftmost.contact, rightmost.contact]
    }
}

struct WorkoutActivityRecorder {
    /// Records activity for a completed session.
    ///
    /// Resolution priority:
    /// 1. `sessionSteps` — already-materialized session timeline (preferred)
    /// 2. `handPreference` — expand/materialize via `WorkoutSessionHandResolver`
    /// 3. `selectedHandSide` — legacy left/right-only path
    func segments(
        for plan: TrainingPlan,
        on board: BoardRevision,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:],
        selectedHandSide: WorkoutSide? = nil,
        handPreference: WorkoutSessionHandPreference? = nil,
        sessionSteps: [WorkoutStep]? = nil,
        performedTaskIndicesByStepID: [String: Set<Int>]? = nil,
        selectedTaskSidesByStepID: [String: [Int: WorkoutSide]]? = nil
    ) throws -> [RecordedActivitySegment] {
        let recordingSteps = try resolvedRecordingSteps(
            for: plan,
            on: board,
            selectedHandSide: selectedHandSide,
            handPreference: handPreference,
            sessionSteps: sessionSteps
        )
        var result: [RecordedActivitySegment] = []
        for recordedStep in recordingSteps {
            for (index, segment) in recordedStep.segments.enumerated() {
                let key = WorkoutActivitySegmentKey(stepID: recordedStep.id, segmentIndex: index)
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
                            stepID: recordedStep.id,
                            stepNumber: recordedStep.number,
                            kind: .rest,
                            target: nil,
                            durationSeconds: duration
                        )
                    )
                    continue
                }
                guard let segmentTarget = segment.target else {
                    guard allowsSourceLinkedUntargetedWork(segment, in: recordedStep, plan: plan) else {
                        throw WorkoutActivityRecordingError.unresolvedTarget(
                            stepID: recordedStep.id,
                            segmentIndex: index
                        )
                    }
                    result.append(
                        RecordedActivitySegment(
                            stepID: recordedStep.id,
                            stepNumber: recordedStep.number,
                            kind: .work,
                            target: .selfSelected,
                            durationSeconds: duration,
                            handUse: recordedStep.handUse,
                            side: recordedStep.side
                        )
                    )
                    continue
                }

                switch segmentTarget {
                case .selfSelected:
                    result.append(
                        RecordedActivitySegment(
                            stepID: recordedStep.id,
                            stepNumber: recordedStep.number,
                            kind: .work,
                            target: .selfSelected,
                            durationSeconds: duration,
                            handUse: recordedStep.handUse,
                            side: recordedStep.side
                        )
                    )
                case .tasks(let tasks):
                    let performed = performedTaskIndicesByStepID?[recordedStep.id] ?? [0]
                    let selectedIndices = performedTaskIndicesByStepID == nil
                        ? Array(tasks.indices)
                        : tasks.indices.filter { performed.contains($0) }
                    for taskIndex in selectedIndices {
                        let authoredTask = tasks[taskIndex]
                        let selectedSide = selectedTaskSidesByStepID?[recordedStep.id]?[taskIndex]
                        let task = authoredTask.map { hand in
                            PlanHandTarget(target: hand.target, side: hand.side ?? selectedSide)
                        }
                        let recordedTarget: RecordedActivityTarget
                        if task.allSatisfy({ $0.target == nil }) {
                            recordedTarget = .selfSelected
                        } else {
                            let contacts: [PhysicalContact]
                            var selectedPositionID: String?
                            if task.count == 1, task[0].side == nil {
                                contacts = []
                            } else {
                                do {
                                    let selection = try ContactResolver.resolveSelection(
                                        task, step: recordedStep, board: board
                                    )
                                    contacts = selection.contacts
                                    selectedPositionID = selection.positionID
                                } catch {
                                    guard allowsSourceLinkedRequirementFallback(
                                        segment,
                                        in: recordedStep,
                                        plan: plan
                                    ) else {
                                        throw WorkoutActivityRecordingError.unresolvedTarget(
                                            stepID: recordedStep.id,
                                            segmentIndex: index
                                        )
                                    }
                                    recordedTarget = .selfSelected
                                    result.append(RecordedActivitySegment(
                                        stepID: recordedStep.id,
                                        stepNumber: recordedStep.number,
                                        kind: .work,
                                        target: recordedTarget,
                                        durationSeconds: tasks.count == 1 ? duration : nil,
                                        handUse: task.count == 2 ? .double : task[0].side == nil ? .either : .single,
                                        side: task.count == 1 ? task[0].side ?? .both : .both
                                    ))
                                    continue
                                }
                            }
                            recordedTarget = .resolvedContacts(ResolvedContactSnapshot(
                                boardID: board.id,
                                revisionID: board.revisionID,
                                modelSHA256: modelSHA256(for: board.position(id: selectedPositionID).flatMap {
                                    board.presentation(id: $0.presentationID)
                                } ?? board.defaultPresentation),
                                requirement: ContactRequirement(),
                                contactIDs: zip(task, contacts).compactMap { hand, contact in
                                    hand.target == nil ? nil : contact.id
                                },
                                positionID: selectedPositionID,
                                handTargets: task
                            ))
                        }
                        result.append(RecordedActivitySegment(
                            stepID: recordedStep.id,
                            stepNumber: recordedStep.number,
                            kind: .work,
                            target: recordedTarget,
                            durationSeconds: tasks.count == 1 ? duration : nil,
                            handUse: task.count == 2 ? .double : task[0].side == nil ? .either : .single,
                            side: task.count == 1 ? task[0].side ?? .both : .both
                        ))
                    }
                case .requirements:
                    let requirements = segmentTarget.contactRequirements
                    do {
                        var resolvedSegments: [RecordedActivitySegment] = []
                        let positionID = try ContactResolver.resolveSelection(requirements,
                            step: recordedStep, board: board).positionID
                        for requirement in requirements {
                            let selection = try ContactResolver.resolveSelection(
                                requirement,
                                step: recordedStep,
                                board: board,
                                inPosition: positionID
                            )
                            resolvedSegments.append(
                                RecordedActivitySegment(
                                    stepID: recordedStep.id,
                                    stepNumber: recordedStep.number,
                                    kind: .work,
                                    target: .resolvedContacts(
                                        ResolvedContactSnapshot(
                                            boardID: board.id,
                                            revisionID: board.revisionID,
                                            modelSHA256: modelSHA256(for: board.position(id: selection.positionID).flatMap {
                                                board.presentation(id: $0.presentationID)
                                            } ?? board.defaultPresentation),
                                            requirement: requirement,
                                            contactIDs: selection.contacts.map(\.id),
                                            positionID: selection.positionID
                                        )
                                    ),
                                    durationSeconds: duration,
                                    handUse: recordedStep.handUse,
                                    side: recordedStep.side
                                )
                            )
                        }
                        result.append(contentsOf: resolvedSegments)
                    } catch {
                        guard allowsSourceLinkedRequirementFallback(
                            segment,
                            in: recordedStep,
                            plan: plan
                        ) else {
                            throw WorkoutActivityRecordingError.unresolvedTarget(
                                stepID: recordedStep.id,
                                segmentIndex: index
                            )
                        }
                        result.append(
                            RecordedActivitySegment(
                                stepID: recordedStep.id,
                                stepNumber: recordedStep.number,
                                kind: .work,
                                target: .selfSelected,
                                durationSeconds: duration,
                                handUse: recordedStep.handUse,
                                side: recordedStep.side
                            )
                        )
                    }
                }
            }
        }
        return result
    }

    private func resolvedRecordingSteps(
        for plan: TrainingPlan,
        on board: BoardRevision,
        selectedHandSide: WorkoutSide?,
        handPreference: WorkoutSessionHandPreference?,
        sessionSteps: [WorkoutStep]?
    ) throws -> [WorkoutStep] {
        if let sessionSteps {
            return sessionSteps
        }
        if let handPreference {
            return WorkoutSessionHandResolver.sessionSteps(
                from: plan.steps,
                preference: handPreference,
                boardIsOneHanded: board.isOneHanded
            )
        }
        return try plan.steps.map {
            try resolvedHandStep($0, selectedHandSide: selectedHandSide, board: board)
        }
    }

    private func resolvedHandStep(
        _ step: WorkoutStep,
        selectedHandSide: WorkoutSide?,
        board: BoardRevision
    ) throws -> WorkoutStep {
        let boardIsOneHanded = board.isOneHanded
        if step.segments.contains(where: { $0.target?.planTasks != nil }) { return step }
        guard step.handUse == .either || (step.handUse == .double && boardIsOneHanded) else { return step }
        guard selectedHandSide == .left || selectedHandSide == .right else {
            throw WorkoutActivityRecordingError.handSideRequired(stepID: step.id)
        }
        return step.resolvingEitherHand(selectedHandSide: selectedHandSide, boardIsOneHanded: boardIsOneHanded)!
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
        allowsBoardAgnosticSourceLinkedWork(segment, in: step, plan: plan)
            && (segment.target == nil || segment.target?.isSelfSelected == true)
    }

    /// Board-agnostic source plans soft-fall to self-selected when a prescribed
    /// requirement cannot resolve on the athlete's chosen board. Board-bound
    /// and custom plans still fail closed.
    private func allowsSourceLinkedRequirementFallback(
        _ segment: WorkoutSegment,
        in step: WorkoutStep,
        plan: TrainingPlan
    ) -> Bool {
        allowsBoardAgnosticSourceLinkedWork(segment, in: step, plan: plan)
    }

    private func allowsBoardAgnosticSourceLinkedWork(
        _ segment: WorkoutSegment,
        in step: WorkoutStep,
        plan: TrainingPlan
    ) -> Bool {
        plan.provenance != .custom
            && plan.sourceURL != nil
            && plan.boardID == nil
            && step.phase != .rest
            && step.phase != .conditioning
            && segment.kind == .work
    }

    func metadata(
        for plan: TrainingPlan,
        on board: BoardRevision,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:],
        selectedHandSide: WorkoutSide? = nil,
        handPreference: WorkoutSessionHandPreference? = nil,
        sessionSteps: [WorkoutStep]? = nil,
        performedTaskIndicesByStepID: [String: Set<Int>]? = nil,
        selectedTaskSidesByStepID: [String: [Int: WorkoutSide]]? = nil,
        stepMeasurements: [WorkoutStepMeasurement] = []
    ) throws -> WorkoutActivityMetadata {
        WorkoutActivityMetadata(
            segments: try segments(
                for: plan,
                on: board,
                stopwatchDurations: stopwatchDurations,
                selectedHandSide: selectedHandSide,
                handPreference: handPreference,
                sessionSteps: sessionSteps,
                performedTaskIndicesByStepID: performedTaskIndicesByStepID,
                selectedTaskSidesByStepID: selectedTaskSidesByStepID
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
