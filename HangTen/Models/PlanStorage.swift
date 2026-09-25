import Foundation

private struct PlanLibraryCodingKey: CodingKey {
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

private extension Decoder {
    /// Silently ignores deprecated plan-library keys so that old JSON files
    /// (which included `schemaVersion`, `version`, or `boardMappings`) can
    /// still be loaded.  Individual plan/block definitions will still reject
    /// structurally incompatible data via their own strict decoders.
    func ignoreFormerPlanLibraryKeys(_ keys: Set<String>) throws {
        // Intentionally a no-op.  The keys are present but unused, so
        // `container(keyedBy:)` simply skips them.
        _ = try self.container(keyedBy: PlanLibraryCodingKey.self)
    }
}

struct PlanLibraryMetadata: Codable, Hashable {
    let id: String
    let title: String
    let generatedAt: String
    let defaultPlanID: String?
    let notes: [String]

    init(
        id: String,
        title: String,
        generatedAt: String,
        defaultPlanID: String? = nil,
        notes: [String] = []
    ) {
        self.id = id
        self.title = title
        self.generatedAt = generatedAt
        self.defaultPlanID = defaultPlanID
        self.notes = notes
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case generatedAt
        case defaultPlanID
        case notes
    }

    init(from decoder: Decoder) throws {
        try decoder.ignoreFormerPlanLibraryKeys(["version"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        generatedAt = try container.decode(String.self, forKey: .generatedAt)
        defaultPlanID = try container.decodeIfPresent(String.self, forKey: .defaultPlanID)
        notes = try container.decode([String].self, forKey: .notes)
    }
}

/// Metadata that travels with a routine. The original source fields remain
/// first-class, while tags and notes give imported routines room to describe
/// themselves without adding more UI-specific fields to `TrainingPlan`.
struct PlanMetadata: Codable, Hashable {
    let title: String
    let subtitle: String
    let level: String
    let sourceLabel: String
    let sourceURL: URL?
    let provenance: RoutineProvenance
    let category: String
    /// Curated athlete-facing labels. Unlike `tags`, these never expose
    /// library provenance or runtime requirements in the Plans filter.
    let workoutLabels: [String]
    let tags: [String]
    let notes: [String]
    /// Deprecated fields preserved for round-trip fidelity with old plan
    /// libraries.  Not used by the app; decoded so they survive a
    /// load→save cycle without data loss.
    let equipment: [String]?
    let disclaimer: String?

    init(
        title: String,
        subtitle: String,
        level: String,
        sourceLabel: String,
        sourceURL: URL?,
        provenance: RoutineProvenance,
        category: String = "general",
        workoutLabels: [String] = [],
        tags: [String] = [],
        notes: [String] = [],
        equipment: [String]? = nil,
        disclaimer: String? = nil
    ) {
        self.title = title
        self.subtitle = subtitle
        self.level = level
        self.sourceLabel = sourceLabel
        self.sourceURL = sourceURL
        self.provenance = provenance
        self.category = category
        self.workoutLabels = workoutLabels
        self.tags = tags
        self.notes = notes
        self.equipment = equipment
        self.disclaimer = disclaimer
    }

    var athleteFacingLabels: [String] {
        if provenance == .custom {
            return tags
        }
        return workoutLabels
    }

    private enum CodingKeys: String, CodingKey {
        case title
        case subtitle
        case level
        case sourceLabel
        case sourceURL
        case provenance
        case category
        case workoutLabels
        case tags
        case notes
        case equipment
        case disclaimer
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        title = try container.decode(String.self, forKey: .title)
        subtitle = try container.decode(String.self, forKey: .subtitle)
        level = try container.decode(String.self, forKey: .level)
        sourceLabel = try container.decode(String.self, forKey: .sourceLabel)
        sourceURL = try container.decodeIfPresent(URL.self, forKey: .sourceURL)
        provenance = try container.decode(RoutineProvenance.self, forKey: .provenance)
        category = try container.decodeIfPresent(String.self, forKey: .category) ?? "general"
        workoutLabels = try container.decodeIfPresent([String].self, forKey: .workoutLabels) ?? []
        tags = try container.decodeIfPresent([String].self, forKey: .tags) ?? []
        notes = try container.decodeIfPresent([String].self, forKey: .notes) ?? []
        equipment = try container.decodeIfPresent([String].self, forKey: .equipment)
        disclaimer = try container.decodeIfPresent(String.self, forKey: .disclaimer)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(title, forKey: .title)
        try container.encode(subtitle, forKey: .subtitle)
        try container.encode(level, forKey: .level)
        try container.encode(sourceLabel, forKey: .sourceLabel)
        try container.encodeIfPresent(sourceURL, forKey: .sourceURL)
        try container.encode(provenance, forKey: .provenance)
        try container.encode(category, forKey: .category)
        if !workoutLabels.isEmpty {
            try container.encode(workoutLabels, forKey: .workoutLabels)
        }
        try container.encode(tags, forKey: .tags)
        try container.encode(notes, forKey: .notes)
        try container.encodeIfPresent(equipment, forKey: .equipment)
        try container.encodeIfPresent(disclaimer, forKey: .disclaimer)
    }
}

enum ContactSelectionPolicy: String, Codable, Hashable {
    case single
    case bilateralPair
}

struct ContactRequirement: Codable, Hashable {
    /// An exact board contact selected by an athlete in a board-specific
    /// custom routine. Catalog requirements intentionally leave this nil so
    /// they can resolve against compatible boards.
    let contactID: String?
    let kind: HoldKind?
    let shape: HoldShape?
    let depth: HoldDepth?
    let fingerCapacity: Int?
    let handCapacity: Int?
    let selection: ContactSelectionPolicy

    init(
        contactID: String? = nil,
        kind: HoldKind? = nil,
        shape: HoldShape? = nil,
        depth: HoldDepth? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        selection: ContactSelectionPolicy = .single
    ) {
        if let fingerCapacity {
            precondition(PhysicalContact.validFingerCapacityRange.contains(fingerCapacity))
        }
        if let handCapacity {
            precondition(PhysicalContact.validHandCapacityRange.contains(handCapacity))
        }
        self.contactID = contactID
        self.kind = kind
        self.shape = shape
        self.depth = depth
        self.fingerCapacity = fingerCapacity
        self.handCapacity = handCapacity
        self.selection = selection
    }

    static func kind(
        _ kind: HoldKind,
        fingerCapacity: Int? = nil,
        selection: ContactSelectionPolicy = .single
    ) -> ContactRequirement {
        .init(kind: kind, fingerCapacity: fingerCapacity, selection: selection)
    }

    static func edge(
        depth: HoldDepth? = nil,
        selection: ContactSelectionPolicy = .single
    ) -> ContactRequirement {
        .init(kind: .edge, depth: depth, selection: selection)
    }

    func strippingExactContactID() -> ContactRequirement {
        ContactRequirement(
            kind: kind,
            shape: shape,
            depth: depth,
            fingerCapacity: fingerCapacity,
            handCapacity: handCapacity,
            selection: selection
        )
    }

    /// A copy of this requirement narrowed to a single-hand selection. A
    /// bilateral prescription resolving down to one hand must drop its
    /// `.bilateralPair` policy so `ContactResolver` accepts the requirement
    /// against the single-hand step.
    var singleHandSelection: ContactRequirement {
        guard selection != .single else { return self }
        return ContactRequirement(
            contactID: contactID,
            kind: kind,
            shape: shape,
            depth: depth,
            fingerCapacity: fingerCapacity,
            handCapacity: handCapacity,
            selection: .single
        )
    }

    /// A copy of this requirement widened to a two-hand paired selection. Used
    /// when a both-hands choice is materialized on a board that fits two hands:
    /// the step resolves to the board's paired left/right holds. An exact
    /// contact pin cannot form a pair, so it keeps its single selection.
    var bilateralSelection: ContactRequirement {
        guard contactID == nil else { return singleHandSelection }
        guard selection != .bilateralPair else { return self }
        return ContactRequirement(
            kind: kind,
            shape: shape,
            depth: depth,
            fingerCapacity: fingerCapacity,
            handCapacity: handCapacity,
            selection: .bilateralPair
        )
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case contactID, kind, shape, depth, fingerCapacity, handCapacity, selection
    }

    init(from decoder: Decoder) throws {
        let rawContainer = try decoder.container(keyedBy: PlanLibraryCodingKey.self)
        let allowedKeys = Set(CodingKeys.allCases.map(\.rawValue))
        if let unknownKey = rawContainer.allKeys.first(where: { !allowedKeys.contains($0.stringValue) }) {
            throw DecodingError.dataCorruptedError(
                forKey: unknownKey,
                in: rawContainer,
                debugDescription: "Unsupported contact requirement field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        contactID = try container.decodeIfPresent(String.self, forKey: .contactID)
        kind = try container.decodeIfPresent(HoldKind.self, forKey: .kind)
        shape = try container.decodeIfPresent(HoldShape.self, forKey: .shape)
        depth = try container.decodeIfPresent(HoldDepth.self, forKey: .depth)
        fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        handCapacity = try container.decodeIfPresent(Int.self, forKey: .handCapacity)
        selection = try container.decode(ContactSelectionPolicy.self, forKey: .selection)

        if let fingerCapacity,
           !PhysicalContact.validFingerCapacityRange.contains(fingerCapacity) {
            throw DecodingError.dataCorruptedError(
                forKey: .fingerCapacity,
                in: container,
                debugDescription: "Contact requirement fingerCapacity must be in \(PhysicalContact.validFingerCapacityRange)."
            )
        }
        if let handCapacity,
           !PhysicalContact.validHandCapacityRange.contains(handCapacity) {
            throw DecodingError.dataCorruptedError(
                forKey: .handCapacity,
                in: container,
                debugDescription: "Contact requirement handCapacity must be in \(PhysicalContact.validHandCapacityRange)."
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(contactID, forKey: .contactID)
        try container.encodeIfPresent(kind, forKey: .kind)
        try container.encodeIfPresent(shape, forKey: .shape)
        try container.encodeIfPresent(depth, forKey: .depth)
        try container.encodeIfPresent(fingerCapacity, forKey: .fingerCapacity)
        try container.encodeIfPresent(handCapacity, forKey: .handCapacity)
        try container.encode(selection, forKey: .selection)
    }
}

struct WorkoutSegmentDefinition: Codable, Hashable {
    let kind: WorkoutSegmentKind
    /// Required for work; must be nil for rest.
    let target: WorkoutSegmentTarget?
    let timing: WorkoutSegmentTiming
    let duration: TimeInterval?

    init(
        kind: WorkoutSegmentKind,
        target: WorkoutSegmentTarget?,
        timing: WorkoutSegmentTiming,
        duration: TimeInterval?
    ) {
        self.kind = kind
        self.target = target
        self.timing = timing
        self.duration = duration
    }

    var contactRequirements: [ContactRequirement] {
        target?.contactRequirements ?? []
    }

    private enum CodingKeys: String, CodingKey {
        case kind
        case target
        case targets
        case timing
        case duration
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        kind = try container.decode(WorkoutSegmentKind.self, forKey: .kind)
        timing = try container.decode(WorkoutSegmentTiming.self, forKey: .timing)
        duration = try container.decodeIfPresent(TimeInterval.self, forKey: .duration)

        if container.contains(.target) {
            let decoded = try container.decode(WorkoutSegmentTarget.self, forKey: .target)
            switch kind {
            case .work:
                target = decoded
            case .rest:
                throw DecodingError.dataCorruptedError(
                    forKey: .target,
                    in: container,
                    debugDescription: "Rest segments must not define a target."
                )
            }
        } else if container.contains(.targets) {
            // Temporary legacy migration: array form → tagged target.
            let legacy = try container.decode([ContactRequirement].self, forKey: .targets)
            switch kind {
            case .work:
                target = .fromLegacyTargets(legacy)
            case .rest:
                guard legacy.isEmpty else {
                    throw DecodingError.dataCorruptedError(
                        forKey: .targets,
                        in: container,
                        debugDescription: "Rest segments must not define a target."
                    )
                }
                target = nil
            }
        } else {
            switch kind {
            case .work:
                throw DecodingError.dataCorruptedError(
                    forKey: .target,
                    in: container,
                    debugDescription: "Work segments require a target."
                )
            case .rest:
                target = nil
            }
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(kind, forKey: .kind)
        try container.encode(timing, forKey: .timing)
        try container.encodeIfPresent(duration, forKey: .duration)
        switch kind {
        case .work:
            guard let target else {
                throw EncodingError.invalidValue(
                    Optional<WorkoutSegmentTarget>.none as Any,
                    EncodingError.Context(
                        codingPath: container.codingPath + [CodingKeys.target],
                        debugDescription: "Work segments require a target."
                    )
                )
            }
            try container.encode(target, forKey: .target)
        case .rest:
            guard target == nil else {
                throw EncodingError.invalidValue(
                    target as Any,
                    EncodingError.Context(
                        codingPath: container.codingPath + [CodingKeys.target],
                        debugDescription: "Rest segments must not define a target."
                    )
                )
            }
        }
    }
}

struct WorkoutStepDefinition: Codable, Hashable {
    let id: String
    let title: String
    let instruction: String
    let accessory: String
    let duration: TimeInterval
    let phase: WorkoutPhase
    let segments: [WorkoutSegmentDefinition]
    let gripType: GripType?
    let fingerConfiguration: FingerConfiguration?
    let activeDuration: TimeInterval?
    let handUse: WorkoutHandUse
    let side: WorkoutSide
    let action: WorkoutAction
    let repetitions: Int?
    let externalLoadKGF: Double?

    init(
        id: String,
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        segments: [WorkoutSegmentDefinition] = [],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil,
        activeDuration: TimeInterval? = nil,
        handUse: WorkoutHandUse = .double,
        side: WorkoutSide = .both,
        action: WorkoutAction = .hang,
        repetitions: Int? = nil,
        externalLoadKGF: Double? = nil
    ) {
        self.id = id
        self.title = title
        self.instruction = instruction
        self.accessory = accessory
        self.duration = duration
        self.phase = phase
        self.segments = segments
        self.gripType = gripType
        self.fingerConfiguration = fingerConfiguration
        self.activeDuration = activeDuration
        self.handUse = handUse
        self.side = side
        self.action = action
        self.repetitions = repetitions
        self.externalLoadKGF = externalLoadKGF
    }

    /// Contact requirements prescribed by work segments.
    var workRequirements: [ContactRequirement] {
        segments.flatMap(\.contactRequirements)
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case instruction
        case accessory
        case duration
        case phase
        case targets
        case segments
        case gripType
        case fingerConfiguration
        case activeDuration
        case handUse
        case side
        case action
        case repetitions
        case externalLoadKGF
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        instruction = try container.decode(String.self, forKey: .instruction)
        accessory = try container.decode(String.self, forKey: .accessory)
        duration = try container.decode(TimeInterval.self, forKey: .duration)
        phase = try container.decode(WorkoutPhase.self, forKey: .phase)
        let legacyTargets = try container.decodeIfPresent(
            [ContactRequirement].self,
            forKey: .targets
        ) ?? []
        var decodedSegments = try container.decodeIfPresent(
            [WorkoutSegmentDefinition].self,
            forKey: .segments
        ) ?? []
        // Temporary migration: promote legacy step-level targets onto a work
        // segment when the definition still uses the compact (no segments) form.
        if decodedSegments.isEmpty, phase != .rest, !legacyTargets.isEmpty {
            let timing: WorkoutSegmentTiming
            let segmentDuration: TimeInterval?
            if let activeDuration = try container.decodeIfPresent(
                TimeInterval.self,
                forKey: .activeDuration
            ) {
                timing = .fixed
                segmentDuration = activeDuration
            } else {
                timing = .undefined
                segmentDuration = nil
            }
            decodedSegments = [
                WorkoutSegmentDefinition(
                    kind: .work,
                    target: .fromLegacyTargets(legacyTargets),
                    timing: timing,
                    duration: segmentDuration
                )
            ]
        }
        segments = decodedSegments
        gripType = try container.decodeIfPresent(GripType.self, forKey: .gripType)
        fingerConfiguration = try container.decodeIfPresent(
            FingerConfiguration.self,
            forKey: .fingerConfiguration
        )
        activeDuration = try container.decodeIfPresent(
            TimeInterval.self,
            forKey: .activeDuration
        )
        handUse = try container.decodeIfPresent(WorkoutHandUse.self, forKey: .handUse) ?? .double
        side = try container.decodeIfPresent(WorkoutSide.self, forKey: .side) ?? .both
        action = try container.decodeIfPresent(WorkoutAction.self, forKey: .action) ?? .hang
        repetitions = try container.decodeIfPresent(Int.self, forKey: .repetitions)
        externalLoadKGF = try container.decodeIfPresent(Double.self, forKey: .externalLoadKGF)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(title, forKey: .title)
        try container.encode(instruction, forKey: .instruction)
        try container.encode(accessory, forKey: .accessory)
        try container.encode(duration, forKey: .duration)
        try container.encode(phase, forKey: .phase)
        try container.encode(segments, forKey: .segments)
        try container.encodeIfPresent(gripType, forKey: .gripType)
        try container.encodeIfPresent(fingerConfiguration, forKey: .fingerConfiguration)
        try container.encodeIfPresent(activeDuration, forKey: .activeDuration)
        try container.encode(handUse, forKey: .handUse)
        try container.encode(side, forKey: .side)
        try container.encode(action, forKey: .action)
        try container.encodeIfPresent(repetitions, forKey: .repetitions)
        try container.encodeIfPresent(externalLoadKGF, forKey: .externalLoadKGF)
    }
}

extension WorkoutStepDefinition {
    /// Keeps persistence and duplication on the same conversion boundary,
    /// including explicit segment timing and one-segment rest rows.
    static func from(
        _ step: WorkoutStep,
        id: String? = nil
    ) -> WorkoutStepDefinition {
        WorkoutStepDefinition(
            id: id ?? step.id,
            title: step.title,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            segments: step.segments.map { segment in
                WorkoutSegmentDefinition(
                    kind: segment.kind,
                    target: segment.target,
                    timing: segment.timing,
                    duration: segment.duration
                )
            },
            gripType: step.gripType,
            fingerConfiguration: step.fingerConfiguration,
            activeDuration: step.timedWorkDuration,
            handUse: step.handUse,
            side: step.side,
            action: step.action,
            repetitions: step.repetitions,
            externalLoadKGF: step.externalLoadKGF
        )
    }

    func strippingUnsupportedCustomCueFields() -> WorkoutStepDefinition {
        WorkoutStepDefinition(
            id: id,
            title: title,
            instruction: instruction,
            accessory: accessory,
            duration: duration,
            phase: phase,
            segments: segments,
            activeDuration: activeDuration,
            handUse: handUse,
            side: side,
            action: action,
            repetitions: repetitions,
            externalLoadKGF: externalLoadKGF
        )
    }

    func strippingExactContactIDs() -> WorkoutStepDefinition {
        WorkoutStepDefinition(
            id: id,
            title: title,
            instruction: instruction,
            accessory: accessory,
            duration: duration,
            phase: phase,
            segments: segments.map { segment in
                let strippedTarget: WorkoutSegmentTarget?
                switch segment.target {
                case .selfSelected:
                    strippedTarget = .selfSelected
                case .requirements(let requirements):
                    strippedTarget = .fromLegacyTargets(
                        requirements.map { $0.strippingExactContactID() }
                    )
                case nil:
                    strippedTarget = nil
                }
                return WorkoutSegmentDefinition(
                    kind: segment.kind,
                    target: strippedTarget,
                    timing: segment.timing,
                    duration: segment.duration
                )
            },
            gripType: gripType,
            fingerConfiguration: fingerConfiguration,
            activeDuration: activeDuration,
            handUse: handUse,
            side: side,
            action: action,
            repetitions: repetitions,
            externalLoadKGF: externalLoadKGF
        )
    }
}

/// A block is deliberately independent of a plan. Common warm-ups and
/// cool-downs can be referenced by many routines, while a plan-specific block
/// can still keep the exact historical step IDs and copy.
struct WorkoutBlockDefinition: Codable, Hashable {
    let id: String
    let title: String
    let steps: [WorkoutStepDefinition]

    init(id: String, title: String = "", steps: [WorkoutStepDefinition]) {
        self.id = id
        self.title = title
        self.steps = steps
    }
}

struct WorkoutBlockReference: Codable, Hashable {
    let blockID: String
    /// Optional IDs let a shared block preserve a routine's historic IDs.
    /// The count must match the referenced block's step count when supplied.
    let stepIDs: [String]
    let repeatCount: Int

    init(blockID: String, stepIDs: [String] = [], repeatCount: Int = 1) {
        self.blockID = blockID
        self.stepIDs = stepIDs
        self.repeatCount = repeatCount
    }

    private enum CodingKeys: String, CodingKey {
        case blockID
        case stepIDs
        case repeatCount
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        blockID = try container.decode(String.self, forKey: .blockID)
        stepIDs = try container.decodeIfPresent([String].self, forKey: .stepIDs) ?? []
        repeatCount = try container.decodeIfPresent(Int.self, forKey: .repeatCount) ?? 1
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(blockID, forKey: .blockID)
        if !stepIDs.isEmpty {
            try container.encode(stepIDs, forKey: .stepIDs)
        }
        if repeatCount != 1 {
            try container.encode(repeatCount, forKey: .repeatCount)
        }
    }
}

struct PlanDefinition: Codable, Hashable, Identifiable {
    let id: String
    let metadata: PlanMetadata
    let boardID: String?
    let blocks: [WorkoutBlockReference]

    init(
        id: String,
        metadata: PlanMetadata,
        boardID: String?,
        blocks: [WorkoutBlockReference]
    ) {
        self.id = id
        self.metadata = metadata
        self.boardID = boardID
        self.blocks = blocks
    }
}

struct PlanLibraryDefinition: Codable, Hashable {
    let metadata: PlanLibraryMetadata
    let blocks: [WorkoutBlockDefinition]
    let plans: [PlanDefinition]

    init(
        metadata: PlanLibraryMetadata,
        blocks: [WorkoutBlockDefinition],
        plans: [PlanDefinition]
    ) {
        self.metadata = metadata
        self.blocks = blocks
        self.plans = plans
    }

    private enum CodingKeys: String, CodingKey {
        case metadata
        case blocks
        case plans
    }

    init(from decoder: Decoder) throws {
        try decoder.ignoreFormerPlanLibraryKeys([
            "schemaVersion",
            "board" + "Mappings"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        metadata = try container.decode(PlanLibraryMetadata.self, forKey: .metadata)
        blocks = try container.decode([WorkoutBlockDefinition].self, forKey: .blocks)
        plans = try container.decode([PlanDefinition].self, forKey: .plans)
    }

    func validationIssues(availableBoards: [BoardRevision]) -> [PlanValidationIssue] {
        PlanLibraryValidator.issues(for: self, availableBoards: availableBoards)
    }
}

// MARK: - Validation

struct PlanValidationIssue: Codable, Hashable, CustomStringConvertible {
    let path: String
    let message: String

    var description: String {
        "\(path): \(message)"
    }
}

struct PlanValidationReport: Hashable {
    let issues: [PlanValidationIssue]

    var isValid: Bool { issues.isEmpty }
}

enum PlanLibraryStoreError: LocalizedError {
    case decoding(Error)
    case validationFailed([PlanValidationIssue])
    case missingPlan(String)
    case missingBlock(String)

    var errorDescription: String? {
        switch self {
        case .decoding(let error):
            return "The plan library could not be decoded: \(error.localizedDescription)"
        case .validationFailed(let issues):
            return issues.map(\.description).joined(separator: "\n")
        case .missingPlan(let id):
            return "The plan library does not contain plan \"\(id)\"."
        case .missingBlock(let id):
            return "The plan library does not contain block \"\(id)\"."
        }
    }
}

enum PlanLibraryValidator {
    static func issues(
        for library: PlanLibraryDefinition,
        availableBoards: [BoardRevision]
    ) -> [PlanValidationIssue] {
        var issues: [PlanValidationIssue] = []
        let boardByID = Dictionary(grouping: availableBoards, by: \.id)

        validateLibraryMetadata(library.metadata, issues: &issues)

        var plansReferencingBlockID: [String: [PlanDefinition]] = [:]
        for plan in library.plans {
            for reference in plan.blocks {
                plansReferencingBlockID[reference.blockID, default: []].append(plan)
            }
        }

        var blockByID: [String: WorkoutBlockDefinition] = [:]
        for (index, block) in library.blocks.enumerated() {
            let path = "blocks[\(index)]"
            if blockByID[block.id] != nil {
                issues.append(PlanValidationIssue(path: path, message: "Duplicate block ID \"\(block.id)\"."))
            }
            blockByID[block.id] = block
            validateBlock(
                block,
                path: path,
                plansReferencingBlock: plansReferencingBlockID[block.id, default: []],
                issues: &issues
            )
        }

        var planIDs = Set<String>()
        for (index, plan) in library.plans.enumerated() {
            let path = "plans[\(index)]"
            if !planIDs.insert(plan.id).inserted {
                issues.append(PlanValidationIssue(path: path, message: "Duplicate plan ID \"\(plan.id)\"."))
            }
            validatePlan(
                plan,
                path: path,
                blockByID: blockByID,
                boardByID: boardByID,
                availableBoards: availableBoards,
                issues: &issues
            )
        }

        if let defaultPlanID = library.metadata.defaultPlanID,
           !planIDs.contains(defaultPlanID) {
            issues.append(PlanValidationIssue(path: "metadata.defaultPlanID", message: "Unknown plan ID \"\(defaultPlanID)\"."))
        }

        return issues
    }

    private static func validateLibraryMetadata(
        _ metadata: PlanLibraryMetadata,
        issues: inout [PlanValidationIssue]
    ) {
        if metadata.id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "metadata.id", message: "Library ID cannot be empty."))
        }
        if metadata.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "metadata.title", message: "Library title cannot be empty."))
        }
    }

    private static func validateBlock(
        _ block: WorkoutBlockDefinition,
        path: String,
        plansReferencingBlock: [PlanDefinition],
        issues: inout [PlanValidationIssue]
    ) {
        if block.id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "\(path).id", message: "Block ID cannot be empty."))
        }
        if block.steps.isEmpty {
            issues.append(PlanValidationIssue(path: path, message: "A workout block must contain at least one step."))
        }

        var stepIDs = Set<String>()
        for (index, step) in block.steps.enumerated() {
            let stepPath = "\(path).steps[\(index)]"
            if !stepIDs.insert(step.id).inserted {
                issues.append(PlanValidationIssue(path: stepPath, message: "Duplicate step ID \"\(step.id)\" in block."))
            }
            let allowsUntargetedStep = !plansReferencingBlock.isEmpty &&
                plansReferencingBlock.allSatisfy {
                    allowsExplicitSelfSelectedWork(step, in: $0)
                }
            validateStep(
                step,
                path: stepPath,
                allowsUntargetedStep: allowsUntargetedStep,
                issues: &issues
            )
        }
    }

    private static func validateStep(
        _ step: WorkoutStepDefinition,
        path: String,
        allowsUntargetedStep: Bool,
        issues: inout [PlanValidationIssue]
    ) {
        if step.id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "\(path).id", message: "Step ID cannot be empty."))
        }
        if !step.duration.isFinite || step.duration <= 0 {
            issues.append(PlanValidationIssue(path: "\(path).duration", message: "Duration must be finite and greater than zero."))
        }
        if !WorkoutStepSemantics.hasValidHandUseAndSide(step.handUse, step.side) ||
            !WorkoutStepSemantics.hasValidHandUse(
                step.handUse,
                phase: step.phase,
                action: step.action
            ) {
            issues.append(
                PlanValidationIssue(
                    path: "\(path).side",
                    message: "Single-hand steps require a left or right side; either-hand steps require both until session start and cannot be pull work; double-hand steps require both sides."
                )
            )
        }
        if !WorkoutStepSemantics.hasValidActionAndRepetitions(step.action, step.repetitions) {
            issues.append(
                PlanValidationIssue(
                    path: "\(path).repetitions",
                    message: "Loaded lifts require positive repetitions; hangs and isometric pulls cannot define repetitions."
                )
            )
        }
        if !WorkoutStepSemantics.hasValidExternalLoad(step.externalLoadKGF) {
            issues.append(
                PlanValidationIssue(
                    path: "\(path).externalLoadKGF",
                    message: "External load must be finite."
                )
            )
        }
        if let activeDuration = step.activeDuration {
            if !activeDuration.isFinite || activeDuration <= 0 {
                issues.append(PlanValidationIssue(path: "\(path).activeDuration", message: "Active duration must be finite and greater than zero."))
            }
            if activeDuration > step.duration {
                issues.append(PlanValidationIssue(path: "\(path).activeDuration", message: "Active duration cannot exceed total duration."))
            }
            if step.phase != .hang && step.phase != .pull {
                issues.append(PlanValidationIssue(path: "\(path).activeDuration", message: "Active duration is only valid for hang or pull steps."))
            }
        }
        if step.phase != .rest,
           step.phase != .conditioning,
           step.segments.isEmpty,
           !allowsUntargetedStep {
            issues.append(
                PlanValidationIssue(
                    path: "\(path).target",
                    message: "Non-rest steps need at least one target."
                )
            )
        }
        let isCompoundStep = step.segments.count > 1
        for (index, segment) in step.segments.enumerated() {
            let targetPath = "\(path).segments[\(index)].target"
            let timingPath = "\(path).segments[\(index)].timing"
            let durationPath = "\(path).segments[\(index)].duration"
            if segment.kind == .work {
                switch segment.target {
                case .none:
                    issues.append(
                        PlanValidationIssue(
                            path: targetPath,
                            message: "Work segments require a target."
                        )
                    )
                case .selfSelected:
                    if !allowsUntargetedStep {
                        issues.append(
                            PlanValidationIssue(
                                path: targetPath,
                                message: "Work segments require a target."
                            )
                        )
                    }
                case .requirements:
                    break
                }
            }
            if segment.kind == .rest && segment.target != nil {
                issues.append(
                    PlanValidationIssue(
                        path: targetPath,
                        message: "Rest segments must not define a target."
                    )
                )
            }
            if segment.kind == .rest && segment.timing != .fixed {
                issues.append(
                    PlanValidationIssue(
                        path: timingPath,
                        message: "Rest segments must use fixed timing."
                    )
                )
            }
            switch segment.timing {
            case .fixed:
                if segment.duration == nil {
                    issues.append(
                        PlanValidationIssue(
                            path: durationPath,
                            message: "Fixed segments require a duration."
                        )
                    )
                }
            case .stopwatch, .undefined:
                if segment.kind == .rest && segment.duration == nil {
                    issues.append(
                        PlanValidationIssue(
                            path: durationPath,
                            message: "Fixed and rest segments require a duration."
                        )
                    )
                } else if segment.duration != nil {
                    issues.append(
                        PlanValidationIssue(
                            path: durationPath,
                            message: "Stopwatch and undefined segments must not define a duration."
                        )
                    )
                }
            }
            if let duration = segment.duration {
                if isCompoundStep && segment.timing == .fixed {
                    if !duration.isFinite || duration <= 0 {
                        issues.append(
                            PlanValidationIssue(
                                path: durationPath,
                                message: "Segment duration must be finite and greater than zero."
                            )
                        )
                    }
                } else if !duration.isFinite || duration < 0 {
                    issues.append(
                        PlanValidationIssue(
                            path: durationPath,
                            message: "Segment duration must be finite and non-negative."
                        )
                    )
                }
                if duration > step.duration {
                    issues.append(
                        PlanValidationIssue(
                            path: durationPath,
                            message: "Segment duration cannot exceed total step duration."
                        )
                    )
                }
            }
        }

        if step.segments.count > 1 {
            for (index, segment) in step.segments.enumerated() where segment.timing != .fixed {
                issues.append(
                    PlanValidationIssue(
                        path: "\(path).segments[\(index)].timing",
                        message: "Compound segments must use fixed timing."
                    )
                )
            }
            let durations = step.segments.compactMap(\.duration)
            if durations.count == step.segments.count,
               durations.reduce(0, +) != step.duration {
                issues.append(
                    PlanValidationIssue(
                        path: "\(path).duration",
                        message: "Compound segment durations must equal the total step duration."
                    )
                )
            }
        }
    }

    private static func validatePlan(
        _ plan: PlanDefinition,
        path: String,
        blockByID: [String: WorkoutBlockDefinition],
        boardByID: [String: [BoardRevision]],
        availableBoards: [BoardRevision],
        issues: inout [PlanValidationIssue]
    ) {
        let metadataPath = "\(path).metadata"
        if plan.id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "\(path).id", message: "Plan ID cannot be empty."))
        }
        if plan.metadata.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "\(metadataPath).title", message: "Plan title cannot be empty."))
        }
        if plan.metadata.provenance != .custom,
           plan.metadata.subtitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "\(metadataPath).subtitle", message: "Plan subtitle cannot be empty."))
        }
        if plan.metadata.level.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "\(metadataPath).level", message: "Plan level cannot be empty."))
        }
        if plan.metadata.sourceLabel.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "\(metadataPath).sourceLabel", message: "Source label cannot be empty."))
        }
        let sourceScheme = plan.metadata.sourceURL?.scheme?.lowercased()
        if plan.metadata.provenance != .custom && sourceScheme != "http" && sourceScheme != "https" {
            issues.append(PlanValidationIssue(path: "\(metadataPath).sourceURL", message: "Source URL must use HTTP or HTTPS."))
        } else if let sourceScheme, sourceScheme != "http" && sourceScheme != "https" {
            issues.append(PlanValidationIssue(path: "\(metadataPath).sourceURL", message: "Source URL must use HTTP or HTTPS."))
        }
        if let boardID = plan.boardID, boardByID[boardID] == nil {
            issues.append(PlanValidationIssue(path: "\(path).boardID", message: "Unknown board ID \"\(boardID)\"."))
        }
        if plan.blocks.isEmpty {
            issues.append(PlanValidationIssue(path: "\(path).blocks", message: "A plan must reference at least one workout block."))
        }

        var expandedStepIDs = Set<String>()
        for (index, reference) in plan.blocks.enumerated() {
            let referencePath = "\(path).blocks[\(index)]"
            guard let block = blockByID[reference.blockID] else {
                issues.append(PlanValidationIssue(path: referencePath, message: "Unknown block ID \"\(reference.blockID)\"."))
                continue
            }
            if reference.repeatCount < 1 {
                issues.append(PlanValidationIssue(path: "\(referencePath).repeatCount", message: "Repeat count must be at least one."))
            }
            if !reference.stepIDs.isEmpty && reference.stepIDs.count != block.steps.count {
                issues.append(PlanValidationIssue(path: "\(referencePath).stepIDs", message: "Step ID overrides must match the referenced block's step count."))
            }
            if Set(reference.stepIDs).count != reference.stepIDs.count {
                issues.append(PlanValidationIssue(path: "\(referencePath).stepIDs", message: "Step ID overrides must be unique."))
            }

            let repetitions = max(0, reference.repeatCount)
            for repetition in 0..<repetitions {
                for (stepIndex, step) in block.steps.enumerated() {
                    let sourceID = reference.stepIDs.indices.contains(stepIndex) ? reference.stepIDs[stepIndex] : step.id
                    let suffix = repetitions > 1 ? "-\(repetition + 1)" : ""
                    let resolvedID = sourceID + suffix
                    for expandedID in expandedIDsEmittedByNormalizer(
                        for: step,
                        resolvedID: resolvedID
                    ) {
                        if !expandedStepIDs.insert(expandedID).inserted {
                            issues.append(PlanValidationIssue(path: referencePath, message: "Expanded step ID \"\(expandedID)\" is repeated in the plan."))
                        }
                    }
                    for (segmentIndex, segment) in step.segments.enumerated() {
                        let requirements = segment.contactRequirements
                        guard !requirements.isEmpty else { continue }
                        validateTargets(
                            requirements,
                            planBoardID: plan.boardID,
                            stepPath: "\(referencePath).steps[\(stepIndex)].segments[\(segmentIndex)]",
                            boardByID: boardByID,
                            availableBoards: availableBoards,
                            handUse: step.handUse,
                            side: step.side,
                            gripType: step.gripType,
                            issues: &issues
                        )
                    }
                }
            }
        }

        if let index = plan.blocks.indices.last {
            let reference = plan.blocks[index]
            if plan.metadata.provenance != .official,
               reference.repeatCount > 0,
               let block = blockByID[reference.blockID],
               let terminalStep = block.steps.last,
               stepEndsInRestAfterNormalization(terminalStep),
               !allowsSourceRequiredTerminalRest(in: plan, terminalStep: terminalStep) {
                issues.append(
                    PlanValidationIssue(
                        path: "\(path).blocks[\(index)].steps[\(block.steps.count - 1)]",
                        message: "A plan cannot end in a rest step."
                    )
                )
            }
        }
    }

    /// Plan IDs whose linked source tells the athlete to choose holds (or
    /// establishes no hold prescription, so inventing one would be unfaithful).
    /// Custom athlete-authored plans may also use `.selfSelected`.
    private static let plansAllowingExplicitSelfSelectedWork: Set<String> = [
        "rptc.seven-three-repeaters",
        "coach.bechtel-three-six-nine",
        "research.eva-int-hangs"
    ]

    /// Whether catalog validation may accept `.selfSelected` work (or compact
    /// hang rows that materialize as self-selected). Board-agnostic
    /// source-linked plans are no longer exempt merely because `boardID` is nil.
    private static func allowsExplicitSelfSelectedWork(
        _ step: WorkoutStepDefinition,
        in plan: PlanDefinition
    ) -> Bool {
        guard step.phase != .rest, step.phase != .conditioning else { return false }
        if plan.metadata.provenance == .custom {
            return true
        }
        return plansAllowingExplicitSelfSelectedWork.contains(plan.id)
    }

    private static func stepEndsInRestAfterNormalization(_ step: WorkoutStepDefinition) -> Bool {
        if step.segments.count > 1 {
            return step.segments.last?.kind == .rest
        }
        if step.segments.isEmpty,
           let activeDuration = step.activeDuration,
           activeDuration < step.duration {
            return true
        }
        return step.phase == .rest
    }

    /// The reported Megos protocol defines a 3-second recovery after every
    /// 7-second work interval, including its final repetition. Preserve that
    /// source-required terminal recovery rather than silently dropping it to
    /// satisfy the usual end-on-work-step convention.
    private static func allowsSourceRequiredTerminalRest(
        in plan: PlanDefinition,
        terminalStep: WorkoutStepDefinition
    ) -> Bool {
        guard plan.id == "research.megos-one-arm-7-3",
              plan.metadata.provenance == .adapted,
              plan.metadata.sourceURL == URL(string: "https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/"),
              terminalStep.id == "megos-7-3-set-6-right-rep-4",
              terminalStep.duration == 10,
              terminalStep.activeDuration == 7,
              terminalStep.segments.count == 2,
              terminalStep.segments[0].kind == .work,
              terminalStep.segments[0].timing == .fixed,
              terminalStep.segments[0].duration == 7,
              terminalStep.segments[1].kind == .rest,
              terminalStep.segments[1].timing == .fixed,
              terminalStep.segments[1].duration == 3 else {
            return false
        }
        return true
    }

    private static func expandedIDsEmittedByNormalizer(
        for step: WorkoutStepDefinition,
        resolvedID: String
    ) -> [String] {
        if step.segments.count > 1 {
            let durations = step.segments.compactMap(\.duration)
            guard step.segments.allSatisfy({ $0.timing == .fixed }),
                  durations.count == step.segments.count,
                  durations.allSatisfy({ $0.isFinite && $0 > 0 }),
                  step.duration.isFinite,
                  step.duration > 0,
                  durations.reduce(0, +) == step.duration else {
                return []
            }
            return step.segments.indices.map { "\(resolvedID).segment-\($0 + 1)" }
        }
        if step.segments.isEmpty,
           let activeDuration = step.activeDuration,
           activeDuration.isFinite,
           step.duration.isFinite,
           activeDuration > 0,
           activeDuration < step.duration {
            return ["\(resolvedID).segment-1", "\(resolvedID).segment-2"]
        }
        return [resolvedID]
    }

    private static func validateTargets(
        _ targets: [ContactRequirement],
        planBoardID: String?,
        stepPath: String,
        boardByID: [String: [BoardRevision]],
        availableBoards: [BoardRevision],
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        gripType: GripType?,
        issues: inout [PlanValidationIssue]
    ) {
        guard let planBoardID else { return }
        let boards = boardByID[planBoardID] ?? []

        for (index, target) in targets.enumerated() {
            let targetPath = "\(stepPath).targets[\(index)]"
            let resolvedHandAssignments: [(WorkoutHandUse, WorkoutSide)] = handUse == .either
                ? [(.single, .left), (.single, .right)]
                : [(handUse, side)]
            let resolvableBoards = boards.filter { board in
                resolvedHandAssignments.allSatisfy { assignment in
                    let (assignmentHandUse, assignmentSide) = assignment
                    let step = WorkoutStep(
                        id: "validation", number: 0, title: "Validation",
                        instruction: "", accessory: "", duration: 1, phase: .hang,
                        segments: [
                            WorkoutSegment(
                                kind: .work,
                                target: .fromLegacyTargets([target]),
                                timing: .undefined,
                                duration: nil
                            )
                        ],
                        gripType: gripType,
                        handUse: assignmentHandUse, side: assignmentSide
                    )
                    return (try? ContactResolver.resolve(target, step: step, board: board)) != nil
                }
            }
            let isValid = !boards.isEmpty && resolvableBoards.count == boards.count
            if !isValid {
                issues.append(
                    PlanValidationIssue(
                        path: targetPath,
                        message: "The contact requirement cannot resolve on declared board \"\(planBoardID)\"."
                    )
                )
            }
        }
    }
}

// MARK: - Resolving definitions into the UI model

struct PlanDefinitionResolver {
    let library: PlanLibraryDefinition
    let availableBoards: [BoardRevision]

    init(
        library: PlanLibraryDefinition,
        availableBoards: [BoardRevision] = BoardCatalog.all
    ) throws {
        let issues = library.validationIssues(availableBoards: availableBoards)
        guard issues.isEmpty else {
            throw PlanLibraryStoreError.validationFailed(issues)
        }
        self.library = library
        self.availableBoards = availableBoards
    }

    func resolveAll() throws -> [TrainingPlan] {
        try library.plans.map(resolve)
    }

    func resolve(_ definition: PlanDefinition) throws -> TrainingPlan {
        guard library.plans.contains(where: { $0.id == definition.id }) else {
            throw PlanLibraryStoreError.missingPlan(definition.id)
        }

        let blocks = Dictionary(uniqueKeysWithValues: library.blocks.map { ($0.id, $0) })
        var steps: [WorkoutStep] = []
        steps.reserveCapacity(definition.blocks.reduce(0) { count, reference in
            count + (blocks[reference.blockID]?.steps.count ?? 0) * max(0, reference.repeatCount)
        })

        for reference in definition.blocks {
            guard let block = blocks[reference.blockID] else {
                throw PlanLibraryStoreError.missingBlock(reference.blockID)
            }
            for repetition in 0..<reference.repeatCount {
                for (stepIndex, stepDefinition) in block.steps.enumerated() {
                    let sourceID = reference.stepIDs.indices.contains(stepIndex) ? reference.stepIDs[stepIndex] : stepDefinition.id
                    let resolvedID = reference.repeatCount > 1 ? "\(sourceID)-\(repetition + 1)" : sourceID
                    let segments = stepDefinition.segments.map {
                        WorkoutSegment(
                            kind: $0.kind,
                            target: $0.target,
                            timing: $0.timing,
                            duration: $0.duration
                        )
                    }
                    let resolvedStep = WorkoutStep(
                        id: resolvedID,
                        number: steps.count + 1,
                        title: stepDefinition.title,
                        instruction: stepDefinition.instruction,
                        accessory: stepDefinition.accessory,
                        duration: stepDefinition.duration,
                        phase: stepDefinition.phase,
                        segments: segments,
                        gripType: stepDefinition.gripType,
                        fingerConfiguration: stepDefinition.fingerConfiguration,
                        handUse: stepDefinition.handUse,
                        side: stepDefinition.side,
                        action: stepDefinition.action,
                        repetitions: stepDefinition.repetitions,
                        externalLoadKGF: stepDefinition.externalLoadKGF,
                        timedWorkDuration: stepDefinition.activeDuration
                    )
                    let canonicalStep = WorkoutStepNormalizer.materializingImplicitSegments(resolvedStep)
                    for normalizedStep in try WorkoutStepNormalizer.expand(canonicalStep) {
                        steps.append(normalizedStep.withNumber(steps.count + 1))
                    }
                }
            }
        }

        return TrainingPlan(
            id: definition.id,
            title: definition.metadata.title,
            subtitle: definition.metadata.subtitle,
            level: definition.metadata.level,
            sourceLabel: definition.metadata.sourceLabel,
            sourceURL: definition.metadata.sourceURL,
            provenance: definition.metadata.provenance,
            boardID: definition.boardID,
            steps: steps
        )
    }

}

struct PlanLibraryStore {
    let definition: PlanLibraryDefinition
    let plans: [TrainingPlan]
    let validationReport: PlanValidationReport

    init(
        definition: PlanLibraryDefinition,
        availableBoards: [BoardRevision] = BoardCatalog.all
    ) throws {
        let issues = definition.validationIssues(availableBoards: availableBoards)
        guard issues.isEmpty else {
            throw PlanLibraryStoreError.validationFailed(issues)
        }
        let resolver = try PlanDefinitionResolver(library: definition, availableBoards: availableBoards)
        self.definition = definition
        self.plans = try resolver.resolveAll()
        self.validationReport = PlanValidationReport(issues: issues)
    }

    init(
        data: Data,
        decoder: JSONDecoder = JSONDecoder(),
        availableBoards: [BoardRevision] = BoardCatalog.all
    ) throws {
        let definition: PlanLibraryDefinition
        do {
            definition = try decoder.decode(PlanLibraryDefinition.self, from: data)
        } catch {
            throw PlanLibraryStoreError.decoding(error)
        }
        try self.init(definition: definition, availableBoards: availableBoards)
    }

    init(
        builtInData data: Data,
        decoder: JSONDecoder = JSONDecoder(),
        packageStore: BoardPackageStore = BoardCatalog.packageStore
    ) throws {
        let definition: PlanLibraryDefinition
        do {
            definition = try decoder.decode(PlanLibraryDefinition.self, from: data)
        } catch {
            throw PlanLibraryStoreError.decoding(error)
        }
        try self.init(builtInDefinition: definition, packageStore: packageStore)
    }

    init(
        builtInDefinition definition: PlanLibraryDefinition,
        packageStore: BoardPackageStore = BoardCatalog.packageStore
    ) throws {
        try self.init(
            definition: definition,
            availableBoards: packageStore.boards
        )
    }

    init(
        contentsOf url: URL,
        decoder: JSONDecoder = JSONDecoder(),
        availableBoards: [BoardRevision] = BoardCatalog.all
    ) throws {
        do {
            try self.init(
                data: Data(contentsOf: url),
                decoder: decoder,
                availableBoards: availableBoards
            )
        } catch let error as PlanLibraryStoreError {
            throw error
        } catch {
            throw PlanLibraryStoreError.decoding(error)
        }
    }

    func encodedData(prettyPrinted: Bool = false) throws -> Data {
        let encoder = JSONEncoder()
        if prettyPrinted {
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        }
        return try encoder.encode(definition)
    }

    func write(
        to url: URL,
        prettyPrinted: Bool = true,
        options: Data.WritingOptions = []
    ) throws {
        try encodedData(prettyPrinted: prettyPrinted).write(to: url, options: options)
    }

    func plan(id: String) -> TrainingPlan? {
        plans.first { $0.id == id }
    }

    static func metadataByPlanID(_ plans: [PlanDefinition]) -> [String: PlanMetadata] {
        plans.reduce(into: [String: PlanMetadata]()) { metadataByID, plan in
            if metadataByID[plan.id] == nil {
                metadataByID[plan.id] = plan.metadata
            }
        }
    }

    static let builtIn: PlanLibraryStore = loadBuiltIn()

    private static func loadBuiltIn() -> PlanLibraryStore {
        let bundles = [Bundle.main, Bundle(for: PlanLibraryBundleToken.self)]
        if let url = bundles.compactMap({ $0.url(forResource: "PlanLibrary", withExtension: "json") }).first {
            do {
                return try PlanLibraryStore(builtInData: Data(contentsOf: url))
            } catch {
                fatalError("Bundled plan library failed validation: \(error.localizedDescription)")
            }
        }

        // Command-line tools and some unit-test runners do not carry the app's
        // resources. The migration document keeps those environments useful
        // without weakening validation of the actual bundled file.
        do {
            return try PlanLibraryStore(
                builtInDefinition: BuiltInPlanLibraryDefinition.document
            )
        } catch {
            fatalError("Built-in plan library failed validation: \(error.localizedDescription)")
        }
    }
}

typealias PlanStore = PlanLibraryStore

private final class PlanLibraryBundleToken {}

// MARK: - Built-in plan library definition

/// Source-audited workout labels for the built-in library. These are assigned
/// from documented routine steps, never inferred from a plan title.
private enum PlanWorkoutLabelAudit {
    static func labels(for planID: String) -> [String] {
        labelsByPlanID[planID] ?? []
    }

    private static let labelsByPlanID: [String: [String]] = [
        "metolius.generic-ten-minute.entry": ["max-effort", "pull-ups", "core"],
        "metolius.generic-ten-minute.intermediate": ["max-effort", "pull-ups", "core"],
        "metolius.generic-ten-minute.advanced": ["max-effort", "pull-ups"],
        "metolius.contact.entry": ["max-effort", "pull-ups", "core"],
        "metolius.contact.intermediate": ["max-effort", "pull-ups", "core"],
        "metolius.contact.advanced": ["max-effort", "pull-ups", "core"],
        "metolius.simulator-3d.entry": ["max-effort", "pull-ups", "core"],
        "metolius.simulator-3d.intermediate": ["max-effort", "pull-ups", "core"],
        "metolius.simulator-3d.advanced": ["max-effort", "pull-ups", "core"],
        "research.max-hangs": ["max-effort"],
        "research.force-feedback-f100": ["max-effort"],
        "research.seven-three-repeaters": ["repeaters"],
        "coach.horst-seven-fifty-three": ["max-effort"],
        "coach.bechtel-three-six-nine": ["max-effort"],
        "device.zlagboard-sixty-sixty": ["endurance"],
        "hoopers-beta.introductory-home-hangboard": ["warm-up", "pull-ups", "core"],
        "method.intermediate-hangboarding.repeaters": ["repeaters"],
        "method.intermediate-hangboarding.emom": ["max-effort", "pull-ups", "core"],
        "rei.hangboard-sample-workout": ["warm-up", "pull-ups"],
        "metolius.rock-rings.ten-minute": ["pull-ups", "core"]
    ]
}

/// Converts the seed routines into the bundled plan library without changing
/// their resolved timing or order.
enum BuiltInPlanLibraryDefinition {
    static let document: PlanLibraryDefinition = makeDocument()

    private static func makeDocument() -> PlanLibraryDefinition {
        let legacyPlans = LegacyPlanSeedCatalog.all
        var blocks: [WorkoutBlockDefinition] = []
        var blockIDs = Set<String>()
        var definitions: [PlanDefinition] = []

        let sharedWarmUp: WorkoutBlockDefinition? = LegacyPlanSeedCatalog.maxHangs.steps.first.flatMap { step in
            guard step.phase == .warmUp,
                  step.duration == LegacyPlanSeedCatalog.sharedWarmUpDuration else {
                return nil
            }

            return WorkoutBlockDefinition(
                id: "shared.progressive-warm-up",
                title: "Progressive warm-up",
                steps: [WorkoutStepDefinition.from(step, id: "warm-up")]
            )
        }
        let sharedCoolDown = legacyPlans.first {
            $0.steps.last?.phase == .coolDown
                && $0.steps.last?.duration == LegacyPlanSeedCatalog.sharedCoolDownDuration
        }?.steps.last.map {
            WorkoutBlockDefinition(
                id: "shared.cool-down",
                title: "Cool down",
                steps: [WorkoutStepDefinition.from($0, id: "cool-down")]
            )
        }

        if let sharedWarmUp {
            blocks.append(sharedWarmUp)
            blockIDs.insert(sharedWarmUp.id)
        }
        if let sharedCoolDown {
            blocks.append(sharedCoolDown)
            blockIDs.insert(sharedCoolDown.id)
        }

        for plan in legacyPlans {
            let (definition, planBlocks) = makeDefinition(
                from: plan,
                sharedWarmUp: sharedWarmUp,
                sharedCoolDown: sharedCoolDown,
                existingBlockIDs: blockIDs
            )
            definitions.append(definition)
            for block in planBlocks where blockIDs.insert(block.id).inserted {
                blocks.append(block)
            }
        }

        return PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "hang-ten.built-in",
                title: "Hang Ten training plans",
                generatedAt: "2026-08-01",
                defaultPlanID: LegacyPlanSeedCatalog.metoliusTenMinute.id,
                notes: [
                    "Generic Metolius sequences are faithful task-order expansions marked adapted because the app adds guided timing.",
                    "Generic Metolius cycles remain ten 60-second minutes; defaults are 5 seconds per pull-up and 1 second per other counted repetition.",
                    "All research and coach routines are explicitly marked as adapted.",
                    "Board-specific and board-agnostic catalog work uses source-backed contact requirements; .selfSelected is limited to custom plans and an explicit allowlist of athlete-chosen-hold sources."
                ]
            ),
            blocks: blocks,
            plans: definitions
        )
    }

    private static func makeDefinition(
        from plan: TrainingPlan,
        sharedWarmUp: WorkoutBlockDefinition?,
        sharedCoolDown: WorkoutBlockDefinition?,
        existingBlockIDs: Set<String>
    ) -> (PlanDefinition, [WorkoutBlockDefinition]) {
        let category: String
        if plan.id.hasPrefix("research.") {
            category = "research"
        } else if plan.id.hasPrefix("coach.") {
            category = "coach"
        } else if plan.id.hasPrefix("device.") {
            category = "device"
        } else if [
            LegacyPlanSeedCatalog.hoopersBetaIntroductory.id,
            LegacyPlanSeedCatalog.methodRepeaters.id,
            LegacyPlanSeedCatalog.methodEMOM.id
        ].contains(plan.id) {
            category = "coach"
        } else if plan.id == LegacyPlanSeedCatalog.reiHangboardSample.id {
            category = "retailer"
        } else {
            category = "manufacturer"
        }

        let notes: [String]
        if plan.id.hasPrefix("metolius.generic-ten-minute.") {
            notes = [
                "Source-linked Metolius sequence with faithful task-order expansion and adapted guided timing.",
                "The source cycles remain ten 60-second minutes; the app uses 5 seconds per pull-up and 1 second per other counted repetition when no duration is prescribed."
            ]
        } else if plan.id.hasPrefix("metolius.contact.") || plan.id.hasPrefix("metolius.simulator-3d.") || plan.id.hasPrefix("metolius.rock-rings.") {
            notes = [
                "Official board-specific Metolius source cycles retain the manufacturer task order and remaining-time rest."
            ]
        } else if plan.id == LegacyPlanSeedCatalog.hoopersBetaIntroductory.id {
            notes = [
                "Exact round order, counts, hold durations, rest intervals, and optional Round 5 guidance are retained.",
                "The app uses manual 60-second conditioning rows where Hooper's Beta gives a rep range or coach-guided movement rather than a standalone timer."
            ]
        } else if plan.id == LegacyPlanSeedCatalog.methodRepeaters.id || plan.id == LegacyPlanSeedCatalog.methodEMOM.id {
            notes = [
                "Both Method Climbing workouts are included; source ranges and exact EMOM order are retained.",
                "The app defaults repeater ranges to 7s/7s and 105s recovery, and uses 5 seconds per pull-up or 1 second per knee raise where the source gives no movement duration."
            ]
        } else if plan.id == LegacyPlanSeedCatalog.reiHangboardSample.id {
            notes = [
                "Source warm-up alternatives, five grip groups, 7–10s/5s interval guidance, six repeats, recovery, and pain warning are retained.",
                "The app defaults the source ranges to 7 seconds and uses a manual 25-minute warm-up preview."
            ]
        } else if plan.id == LegacyPlanSeedCatalog.rptcRepeaters.id {
            notes = [
                "Official Rock Prodigy set template: seven 7s/3s two-handed dead-hang repetitions, the table's 2m 53s recovery to 4:00, then a separate 3-minute between-set rest.",
                "The source leaves the 5–10 grips and 1–3 sets per grip to the athlete, so the app intentionally supplies no target, grip order, or fixed workout duration."
            ]
        } else {
            notes = ["Preserved from the original Hang Ten routine catalog."]
        }

        var tags = ["built-in", category]
        if plan.id == LegacyPlanSeedCatalog.forceF80.id || plan.id == LegacyPlanSeedCatalog.forceF100.id {
            tags.append("requires-instrumented-12mm-force-feedback")
        }

        let metadata = PlanMetadata(
            title: plan.title,
            subtitle: plan.subtitle,
            level: plan.level,
            sourceLabel: plan.sourceLabel,
            sourceURL: plan.sourceURL,
            provenance: plan.provenance,
            category: category,
            workoutLabels: PlanWorkoutLabelAudit.labels(for: plan.id),
            tags: tags,
            notes: notes
        )

        var references: [WorkoutBlockReference] = []
        var blocks: [WorkoutBlockDefinition] = []
        var firstIndex = 0
        var lastIndex = plan.steps.count

        if let first = plan.steps.first,
           let sharedWarmUp,
           first.phase == .warmUp,
           first.duration == LegacyPlanSeedCatalog.sharedWarmUpDuration,
           first.title == sharedWarmUp.title,
           first.instruction == sharedWarmUp.steps[0].instruction {
            references.append(WorkoutBlockReference(blockID: sharedWarmUp.id, stepIDs: [first.id]))
            firstIndex = 1
        } else if let first = plan.steps.first {
            let block = WorkoutBlockDefinition(
                id: "\(plan.id).warm-up",
                title: first.title,
                steps: [WorkoutStepDefinition.from(first)]
            )
            blocks.append(block)
            references.append(WorkoutBlockReference(blockID: block.id))
            firstIndex = 1
        }

        if let last = plan.steps.last,
           let sharedCoolDown,
           last.phase == .coolDown,
           last.duration == LegacyPlanSeedCatalog.sharedCoolDownDuration,
           last.title == sharedCoolDown.title,
           last.instruction == sharedCoolDown.steps[0].instruction {
            lastIndex -= 1
        }

        if firstIndex < lastIndex {
            let middleBlock = WorkoutBlockDefinition(
                id: "\(plan.id).main",
                title: plan.title,
                steps: plan.steps[firstIndex..<lastIndex].map {
                    WorkoutStepDefinition.from($0)
                }
            )
            blocks.append(middleBlock)
            references.append(WorkoutBlockReference(blockID: middleBlock.id))
        }

        if lastIndex < plan.steps.count, let sharedCoolDown {
            references.append(WorkoutBlockReference(blockID: sharedCoolDown.id, stepIDs: [plan.steps[lastIndex].id]))
        }

        // This guard makes the generated block IDs stable even if a future
        // routine is supplied with an ID that collides with a shared block.
        if !existingBlockIDs.isDisjoint(with: Set(blocks.map(\.id))) {
            blocks = blocks.map { block in
                guard existingBlockIDs.contains(block.id) else { return block }
                let renamedID = "\(block.id).routine"
                return WorkoutBlockDefinition(id: renamedID, title: block.title, steps: block.steps)
            }
            references = references.map { reference in
                guard existingBlockIDs.contains(reference.blockID) else { return reference }
                return WorkoutBlockReference(blockID: "\(reference.blockID).routine", stepIDs: reference.stepIDs, repeatCount: reference.repeatCount)
            }
        }

        return (
            PlanDefinition(id: plan.id, metadata: metadata, boardID: plan.boardID, blocks: references),
            blocks
        )
    }

}

// MARK: - Compatibility facade

#if DEBUG
/// Builds the DEBUG drift-guard baseline at the same literal-step boundary
/// used by the runtime resolver.
private func literalizedLegacyPlanCatalog() -> [TrainingPlan] {
    LegacyPlanSeedCatalog.all.map { seedPlan in
        let literalSteps: [WorkoutStep]
        do {
            literalSteps = try seedPlan.steps
                .map(WorkoutStepNormalizer.materializingImplicitSegments)
                .flatMap(WorkoutStepNormalizer.expand)
                .enumerated()
                .map { index, step in
                    step.withNumber(index + 1)
                }
        } catch {
            preconditionFailure(
                "Legacy plan \(seedPlan.id) could not be literalized: \(error)"
            )
        }

        return TrainingPlan(
            id: seedPlan.id,
            title: seedPlan.title,
            subtitle: seedPlan.subtitle,
            level: seedPlan.level,
            sourceLabel: seedPlan.sourceLabel,
            sourceURL: seedPlan.sourceURL,
            provenance: seedPlan.provenance,
            boardID: seedPlan.boardID,
            steps: literalSteps
        )
    }
}
#endif

/// Runtime callers keep the small `PlanCatalog` API they already use, while
/// the data behind it now comes from one validated, versioned store.
enum PlanCatalog {
    private static let store: PlanLibraryStore = {
        let result = PlanLibraryStore.builtIn
        #if DEBUG
        assert(
            result.plans == literalizedLegacyPlanCatalog(),
            "Bundled plan definitions drifted from the source-audited seed catalog"
        )
        #endif
        return result
    }()

    private static let metadataByID = PlanLibraryStore.metadataByPlanID(store.definition.plans)

    static let all: [TrainingPlan] = store.plans

    static let metoliusEntry = required("metolius.generic-ten-minute.entry")
    static let metoliusIntermediate = required("metolius.generic-ten-minute.intermediate")
    static let metoliusAdvanced = required("metolius.generic-ten-minute.advanced")
    static let metoliusTenMinute = metoliusEntry
    static let maxHangs = required("research.max-hangs")
    static let forceF80 = required("research.force-feedback-f80")
    static let forceF100 = required("research.force-feedback-f100")
    static let evaIntHangs = required("research.eva-int-hangs")
    static let repeaters = required("research.seven-three-repeaters")
    static let abrahangs = required("research.abrahangs")
    static let horst753 = required("coach.horst-seven-fifty-three")
    static let ladders = required("coach.bechtel-three-six-nine")
    static let densityHangs = required("coach.density-hangs")
    static let zlagboardEndurance = required("device.zlagboard-sixty-sixty")
    static let hoopersBetaIntroductory = required("hoopers-beta.introductory-home-hangboard")
    static let methodRepeaters = required("method.intermediate-hangboarding.repeaters")
    static let methodEMOM = required("method.intermediate-hangboarding.emom")
    static let reiHangboardSample = required("rei.hangboard-sample-workout")
    static let metoliusRockRing = required("metolius.rock-rings.ten-minute")

    static func plan(id: String) -> TrainingPlan? {
        store.plan(id: id)
    }

    static func metadata(for id: String) -> PlanMetadata? {
        metadataByID[id]
    }

    static var definition: PlanLibraryDefinition {
        store.definition
    }

    private static func required(_ id: String) -> TrainingPlan {
        guard let plan = store.plan(id: id) else {
            fatalError("Built-in plan \(id) is missing")
        }
        return plan
    }
}
