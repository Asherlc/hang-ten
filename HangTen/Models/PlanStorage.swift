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
    func rejectFormerPlanLibraryKeys(_ keys: Set<String>) throws {
        let container = try self.container(keyedBy: PlanLibraryCodingKey.self)
        guard let key = container.allKeys.first(where: { keys.contains($0.stringValue) }) else {
            return
        }

        throw DecodingError.dataCorruptedError(
            forKey: key,
            in: container,
            debugDescription: "Former plan-library field \(key.stringValue) is not supported."
        )
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
        try decoder.rejectFormerPlanLibraryKeys(["version"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        generatedAt = try container.decode(String.self, forKey: .generatedAt)
        defaultPlanID = try container.decodeIfPresent(String.self, forKey: .defaultPlanID)
        notes = try container.decode([String].self, forKey: .notes)
    }
}

/// Metadata that travels with a routine. The original source fields remain
/// first-class, while tags/equipment/notes give imported routines room to
/// describe themselves without adding more UI-specific fields to `TrainingPlan`.
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
    let equipment: [String]
    let notes: [String]

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
        equipment: [String] = [],
        notes: [String] = []
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
        self.equipment = equipment
        self.notes = notes
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
        case equipment
        case notes
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
        equipment = try container.decodeIfPresent([String].self, forKey: .equipment) ?? []
        notes = try container.decodeIfPresent([String].self, forKey: .notes) ?? []
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
        try container.encode(equipment, forKey: .equipment)
        try container.encode(notes, forKey: .notes)
    }
}

struct SemanticHoldMappingDefinition: Codable, Hashable {
    let holdIDs: [String]
    let kind: HoldKind?

    private enum CodingKeys: String, CodingKey {
        case holdIDs
        case kind
    }

    init(holdIDs: [String] = [], kind: HoldKind? = nil) {
        self.holdIDs = holdIDs
        self.kind = kind
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        holdIDs = try container.decodeIfPresent([String].self, forKey: .holdIDs) ?? []
        kind = try container.decodeIfPresent(HoldKind.self, forKey: .kind)
    }

    var isResolvable: Bool {
        !holdIDs.isEmpty || kind != nil
    }

    func holdTarget() -> HoldTarget {
        if !holdIDs.isEmpty {
            return .ids(holdIDs)
        }
        if let kind {
            return .kind(kind)
        }
        return .ids()
    }
}

/// A board-specific vocabulary for plan targets. Plans refer to `edge-19`
/// or `outer-jugs`, never to a physical board's IDs. Adding a new board only
/// requires another mapping document.
struct BoardMappingDefinition: Codable, Hashable {
    let boardID: String
    let semanticHolds: [String: SemanticHoldMappingDefinition]

    init(boardID: String, semanticHolds: [String: SemanticHoldMappingDefinition]) {
        self.boardID = boardID
        self.semanticHolds = semanticHolds
    }
}

typealias SemanticBoardMappingDefinition = BoardMappingDefinition

enum WorkoutTargetDefinition: Codable, Hashable {
    case semantic(String)
    case semantics([String])
    case holdIDs([String])
    case kind(HoldKind, fallbacks: [HoldFeature] = [], fingerCapacity: Int? = nil)
    case feature(HoldFeature, fallbacks: [HoldFeature], fingerCapacity: Int? = nil)

    private enum CodingKeys: String, CodingKey {
        case semantic
        case semantics
        case holdIDs
        case kind
        case feature
        case fallbackFeatures
        case fingerCapacity
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        if let value = try container.decodeIfPresent(String.self, forKey: .semantic) {
            self = .semantic(value)
            return
        }
        if let value = try container.decodeIfPresent([String].self, forKey: .semantics) {
            self = .semantics(value)
            return
        }
        if let value = try container.decodeIfPresent([String].self, forKey: .holdIDs) {
            self = .holdIDs(value)
            return
        }
        let fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        if let fingerCapacity,
           !BoardHold.validFingerCapacityRange.contains(fingerCapacity) {
            throw DecodingError.dataCorruptedError(
                forKey: .fingerCapacity,
                in: container,
                debugDescription: "Workout target fingerCapacity must be in \(BoardHold.validFingerCapacityRange)."
            )
        }
        let fallbackRawValues = try container.decodeIfPresent(
            [String].self,
            forKey: .fallbackFeatures
        ) ?? []
        let fallbacks = try fallbackRawValues.compactMap { rawValue -> HoldFeature? in
            switch rawValue {
            case HoldKind.jug.rawValue, HoldKind.pocket.rawValue:
                // Deprecated duplicate feature aliases normalize away. A
                // fallback list remains feature-only, so these cannot become
                // fallback kinds.
                return nil
            default:
                guard let feature = HoldFeature(rawValue: rawValue) else {
                    throw DecodingError.dataCorruptedError(
                        forKey: .fallbackFeatures,
                        in: container,
                        debugDescription: "Unknown fallback hold feature \"\(rawValue)\"."
                    )
                }
                return feature
            }
        }
        if let value = try container.decodeIfPresent(HoldKind.self, forKey: .kind) {
            self = .kind(value, fallbacks: fallbacks, fingerCapacity: fingerCapacity)
            return
        }
        if let rawValue = try container.decodeIfPresent(String.self, forKey: .feature) {
            switch rawValue {
            case HoldKind.jug.rawValue:
                self = .kind(.jug, fallbacks: fallbacks, fingerCapacity: fingerCapacity)
                return
            case HoldKind.pocket.rawValue:
                self = .kind(.pocket, fallbacks: fallbacks, fingerCapacity: fingerCapacity)
                return
            default:
                guard let value = HoldFeature(rawValue: rawValue) else {
                    throw DecodingError.dataCorruptedError(
                        forKey: .feature,
                        in: container,
                        debugDescription: "Unknown hold feature \"\(rawValue)\"."
                    )
                }
            self = .feature(value, fallbacks: fallbacks, fingerCapacity: fingerCapacity)
            return
            }
        }

        throw DecodingError.dataCorruptedError(
            forKey: .semantic,
            in: container,
            debugDescription: "A workout target must contain semantic, semantics, holdIDs, or kind."
        )
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        switch self {
        case .semantic(let value):
            try container.encode(value, forKey: .semantic)
        case .semantics(let values):
            try container.encode(values, forKey: .semantics)
        case .holdIDs(let values):
            try container.encode(values, forKey: .holdIDs)
        case let .kind(value, fallbacks, fingerCapacity):
            try container.encode(value, forKey: .kind)
            if !fallbacks.isEmpty {
                try container.encode(fallbacks, forKey: .fallbackFeatures)
            }
            try container.encodeIfPresent(fingerCapacity, forKey: .fingerCapacity)
        case let .feature(value, fallbacks, fingerCapacity):
            if value == .jug {
                try container.encode(HoldKind.jug, forKey: .kind)
                if !fallbacks.isEmpty {
                    try container.encode(fallbacks, forKey: .fallbackFeatures)
                }
                try container.encodeIfPresent(fingerCapacity, forKey: .fingerCapacity)
                return
            }
            try container.encode(value, forKey: .feature)
            if !fallbacks.isEmpty {
                try container.encode(fallbacks, forKey: .fallbackFeatures)
            }
            try container.encodeIfPresent(fingerCapacity, forKey: .fingerCapacity)
        }
    }
}

struct WorkoutSegmentDefinition: Codable, Hashable {
    let kind: WorkoutSegmentKind
    let targets: [WorkoutTargetDefinition]
    let timing: WorkoutSegmentTiming
    let duration: TimeInterval?

    init(
        kind: WorkoutSegmentKind,
        targets: [WorkoutTargetDefinition],
        timing: WorkoutSegmentTiming,
        duration: TimeInterval?
    ) {
        self.kind = kind
        self.targets = targets
        self.timing = timing
        self.duration = duration
    }

    private enum CodingKeys: String, CodingKey {
        case kind
        case targets
        case timing
        case duration
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        kind = try container.decode(WorkoutSegmentKind.self, forKey: .kind)
        targets = try container.decode([WorkoutTargetDefinition].self, forKey: .targets)
        timing = try container.decode(WorkoutSegmentTiming.self, forKey: .timing)
        duration = try container.decodeIfPresent(TimeInterval.self, forKey: .duration)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(kind, forKey: .kind)
        try container.encode(targets, forKey: .targets)
        try container.encode(timing, forKey: .timing)
        try container.encodeIfPresent(duration, forKey: .duration)
    }
}

struct WorkoutStepDefinition: Codable, Hashable {
    let id: String
    let title: String
    let instruction: String
    let accessory: String
    let duration: TimeInterval
    let phase: WorkoutPhase
    let targets: [WorkoutTargetDefinition]
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
        targets: [WorkoutTargetDefinition],
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
        self.targets = targets
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
        targets = try container.decode([WorkoutTargetDefinition].self, forKey: .targets)
        segments = try container.decodeIfPresent(
            [WorkoutSegmentDefinition].self,
            forKey: .segments
        ) ?? []
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
        try container.encode(targets, forKey: .targets)
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

extension WorkoutTargetDefinition {
    /// Converts a resolved runtime target back into a portable definition.
    /// A caller may supply a semantic ID lookup when it owns reusable board
    /// mappings; local custom routines intentionally persist direct targets.
    static func from(
        _ target: HoldTarget,
        semanticHoldID: (([String]) -> String?)? = nil
    ) -> WorkoutTargetDefinition {
        if let kind = target.kind {
            return .kind(
                kind,
                fallbacks: target.fallbackFeatures,
                fingerCapacity: target.fingerCapacity
            )
        }
        if let feature = target.feature {
            return .feature(feature, fallbacks: target.fallbackFeatures, fingerCapacity: target.fingerCapacity)
        }
        if let semanticID = semanticHoldID?(target.holdIDs) {
            return .semantic(semanticID)
        }
        return .holdIDs(target.holdIDs)
    }
}

extension WorkoutStepDefinition {
    /// Keeps persistence and duplication on the same conversion boundary,
    /// including explicit segment timing and one-segment rest rows.
    static func from(
        _ step: WorkoutStep,
        id: String? = nil,
        semanticHoldID: (([String]) -> String?)? = nil
    ) -> WorkoutStepDefinition {
        WorkoutStepDefinition(
            id: id ?? step.id,
            title: step.title,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            targets: step.targets.map { WorkoutTargetDefinition.from($0, semanticHoldID: semanticHoldID) },
            segments: step.segments.map { segment in
                WorkoutSegmentDefinition(
                    kind: segment.kind,
                    targets: segment.targets.map {
                        WorkoutTargetDefinition.from($0, semanticHoldID: semanticHoldID)
                    },
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
            targets: targets,
            segments: segments,
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
    let boardMappings: [BoardMappingDefinition]
    let blocks: [WorkoutBlockDefinition]
    let plans: [PlanDefinition]

    init(
        metadata: PlanLibraryMetadata,
        boardMappings: [BoardMappingDefinition],
        blocks: [WorkoutBlockDefinition],
        plans: [PlanDefinition]
    ) {
        self.metadata = metadata
        self.boardMappings = boardMappings
        self.blocks = blocks
        self.plans = plans
    }

    private enum CodingKeys: String, CodingKey {
        case metadata
        case boardMappings
        case blocks
        case plans
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectFormerPlanLibraryKeys(["schemaVersion"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        metadata = try container.decode(PlanLibraryMetadata.self, forKey: .metadata)
        boardMappings = try container.decode([BoardMappingDefinition].self, forKey: .boardMappings)
        blocks = try container.decode([WorkoutBlockDefinition].self, forKey: .blocks)
        plans = try container.decode([PlanDefinition].self, forKey: .plans)
    }

    func validationIssues(availableBoards: [TrainingBoard]) -> [PlanValidationIssue] {
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
    case missingBoardMapping(String)
    case missingSemanticTarget(String)

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
        case .missingBoardMapping(let id):
            return "The plan library does not contain a board mapping for \"\(id)\"."
        case .missingSemanticTarget(let id):
            return "The board mapping does not contain semantic target \"\(id)\"."
        }
    }
}

enum PlanLibraryValidator {
    static func issues(
        for library: PlanLibraryDefinition,
        availableBoards: [TrainingBoard]
    ) -> [PlanValidationIssue] {
        var issues: [PlanValidationIssue] = []
        let boardByID = Dictionary(grouping: availableBoards, by: \.id)
        let boardIDs = Set(boardByID.keys)

        validateLibraryMetadata(library.metadata, issues: &issues)

        var planMappingByBoardID: [String: BoardMappingDefinition] = [:]
        for (index, mapping) in library.boardMappings.enumerated() {
            let path = "boardMappings[\(index)]"
            if planMappingByBoardID[mapping.boardID] != nil {
                issues.append(PlanValidationIssue(path: path, message: "Duplicate board mapping ID \"\(mapping.boardID)\"."))
            }
            planMappingByBoardID[mapping.boardID] = mapping

            if !boardIDs.contains(mapping.boardID) {
                issues.append(PlanValidationIssue(path: path, message: "Unknown board ID \"\(mapping.boardID)\"."))
            }

            guard let board = boardByID[mapping.boardID]?.first else { continue }
            let knownHoldIDs = Set(board.holds.map(\.id))
            for (semanticID, target) in mapping.semanticHolds {
                let semanticPath = "\(path).semanticHolds.\(semanticID)"
                if semanticID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    issues.append(PlanValidationIssue(path: semanticPath, message: "Semantic ID cannot be empty."))
                }
                if target.holdIDs.isEmpty && target.kind == nil {
                    issues.append(PlanValidationIssue(path: semanticPath, message: "A semantic mapping needs hold IDs or a hold kind."))
                }
                if target.kind != nil && !target.holdIDs.isEmpty {
                    issues.append(PlanValidationIssue(path: semanticPath, message: "A semantic mapping cannot contain both hold IDs and a hold kind."))
                }
                if Set(target.holdIDs).count != target.holdIDs.count {
                    issues.append(PlanValidationIssue(path: semanticPath, message: "Hold IDs must be unique."))
                }
                for holdID in target.holdIDs where !knownHoldIDs.contains(holdID) {
                    issues.append(PlanValidationIssue(path: semanticPath, message: "Unknown hold ID \"\(holdID)\" for board \"\(mapping.boardID)\"."))
                }
                if let kind = target.kind,
                   !board.holds.contains(where: { $0.kind == kind }) {
                    issues.append(
                        PlanValidationIssue(
                            path: semanticPath,
                            message: "Hold kind \"\(kind.rawValue)\" has no matching hold on board \"\(mapping.boardID)\"."
                        )
                    )
                }
            }
        }

        let mappingByBoardID = planMappingByBoardID

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
                mappingByBoardID: mappingByBoardID,
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
                    allowsUntargetedRPTCSelfSelectedHang(step, in: $0)
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
        if !WorkoutStepSemantics.hasValidHandUseAndSide(step.handUse, step.side) {
            issues.append(
                PlanValidationIssue(
                    path: "\(path).side",
                    message: "Single-hand steps require a left or right side, while double-hand steps require both sides."
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
           step.targets.isEmpty,
           !allowsUntargetedStep {
            issues.append(PlanValidationIssue(path: "\(path).targets", message: "Non-rest steps need at least one target."))
        }
        let isCompoundStep = step.segments.count > 1
        for (index, segment) in step.segments.enumerated() {
            let targetPath = "\(path).segments[\(index)].targets"
            let timingPath = "\(path).segments[\(index)].timing"
            let durationPath = "\(path).segments[\(index)].duration"
            if segment.kind == .work && segment.targets.isEmpty {
                issues.append(
                    PlanValidationIssue(
                        path: targetPath,
                        message: "Work segments require a target."
                    )
                )
            }
            if segment.kind == .rest && !segment.targets.isEmpty {
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
        mappingByBoardID: [String: BoardMappingDefinition],
        boardByID: [String: [TrainingBoard]],
        availableBoards: [TrainingBoard],
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
                    validateTargets(
                        step.targets,
                        planBoardID: plan.boardID,
                        stepPath: "\(referencePath).steps[\(stepIndex)]",
                        mappingByBoardID: mappingByBoardID,
                        boardByID: boardByID,
                        availableBoards: availableBoards,
                        issues: &issues
                    )
                    for (segmentIndex, segment) in step.segments.enumerated() {
                        guard !segment.targets.isEmpty else { continue }
                        validateTargets(
                            segment.targets,
                            planBoardID: plan.boardID,
                            stepPath: "\(referencePath).steps[\(stepIndex)].segments[\(segmentIndex)]",
                            mappingByBoardID: mappingByBoardID,
                            boardByID: boardByID,
                            availableBoards: availableBoards,
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

    private static func allowsUntargetedRPTCSelfSelectedHang(
        _ step: WorkoutStepDefinition,
        in plan: PlanDefinition
    ) -> Bool {
        let expectedDuration: TimeInterval
        switch step.id {
        case "rptc-repeaters-set-rep-1",
            "rptc-repeaters-set-rep-2",
            "rptc-repeaters-set-rep-3",
            "rptc-repeaters-set-rep-4",
            "rptc-repeaters-set-rep-5",
            "rptc-repeaters-set-rep-6":
            expectedDuration = 10
        case "rptc-repeaters-set-rep-7":
            expectedDuration = 180
        default:
            return false
        }

        return plan.id == LegacyPlanSeedCatalog.rptcRepeaters.id &&
            plan.metadata.provenance == .official &&
            plan.metadata.sourceURL == LegacyPlanSeedCatalog.rptcRepeaters.sourceURL &&
            plan.boardID == nil &&
            step.phase == .hang &&
            step.segments.isEmpty &&
            step.activeDuration == 7 &&
            step.duration == expectedDuration
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
        _ targets: [WorkoutTargetDefinition],
        planBoardID: String?,
        stepPath: String,
        mappingByBoardID: [String: BoardMappingDefinition],
        boardByID: [String: [TrainingBoard]],
        availableBoards: [TrainingBoard],
        issues: inout [PlanValidationIssue]
    ) {
        let boardIDs: [String]
        if let planBoardID {
            boardIDs = [planBoardID]
        } else {
            boardIDs = availableBoards.map(\.id)
        }

        for (index, target) in targets.enumerated() {
            let targetPath = "\(stepPath).targets[\(index)]"
            switch target {
            case .semantic(let semanticID):
                validateSemantic(semanticID, boardIDs: boardIDs, targetPath: targetPath, mappingByBoardID: mappingByBoardID, issues: &issues)
            case .semantics(let semanticIDs):
                if semanticIDs.isEmpty {
                    issues.append(PlanValidationIssue(path: targetPath, message: "A semantic target list cannot be empty."))
                }
                for semanticID in semanticIDs {
                    validateSemantic(semanticID, boardIDs: boardIDs, targetPath: targetPath, mappingByBoardID: mappingByBoardID, issues: &issues)
                }
            case .holdIDs(let holdIDs):
                if holdIDs.isEmpty {
                    issues.append(PlanValidationIssue(path: targetPath, message: "A direct hold target cannot be empty."))
                }
                for boardID in boardIDs {
                    let knownHoldIDs = Set(boardByID[boardID]?.first?.holds.map(\.id) ?? [])
                    for holdID in holdIDs where !knownHoldIDs.contains(holdID) {
                        issues.append(PlanValidationIssue(path: targetPath, message: "Unknown hold ID \"\(holdID)\" for board \"\(boardID)\"."))
                    }
                }
            case .kind:
                break
            case let .feature(feature, fallbacks, fingerCapacity):
                let runtimeTarget = HoldTarget(
                    holdIDs: [],
                    kind: nil,
                    feature: feature,
                    fallbackFeatures: fallbacks,
                    fingerCapacity: fingerCapacity
                )
                let hasCompatibleBoard = boardIDs.contains { boardID in
                    guard let board = boardByID[boardID]?.first else { return false }
                    return !BoardTargetResolver.substituteHoldIDs(for: runtimeTarget, on: board).isEmpty
                }
                if !hasCompatibleBoard {
                    issues.append(
                        PlanValidationIssue(
                            path: targetPath,
                            message: "No compatible board exposes feature \"\(feature.rawValue)\" or its fallbacks."
                        )
                    )
                }
            }
        }
    }

    private static func validateSemantic(
        _ semanticID: String,
        boardIDs: [String],
        targetPath: String,
        mappingByBoardID: [String: BoardMappingDefinition],
        issues: inout [PlanValidationIssue]
    ) {
        for boardID in boardIDs {
            guard let mapping = mappingByBoardID[boardID] else {
                issues.append(PlanValidationIssue(path: targetPath, message: "Missing board mapping for \"\(boardID)\"."))
                continue
            }
            guard let semantic = mapping.semanticHolds[semanticID] else {
                issues.append(PlanValidationIssue(path: targetPath, message: "Unknown semantic target \"\(semanticID)\" for board \"\(boardID)\"."))
                continue
            }
            if !semantic.isResolvable {
                issues.append(PlanValidationIssue(path: targetPath, message: "Semantic target \"\(semanticID)\" has no hold mapping."))
            }
        }
    }
}

// MARK: - Resolving definitions into the UI model

struct PlanDefinitionResolver {
    let library: PlanLibraryDefinition
    let availableBoards: [TrainingBoard]

    init(
        library: PlanLibraryDefinition,
        availableBoards: [TrainingBoard] = BoardCatalog.all
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

        let board = availableBoards.first { $0.id == definition.boardID }
            ?? BoardCatalog.board(for: definition.boardID)
        let mapping = library.boardMappings.first { $0.boardID == board.id }

        for reference in definition.blocks {
            guard let block = blocks[reference.blockID] else {
                throw PlanLibraryStoreError.missingBlock(reference.blockID)
            }
            for repetition in 0..<reference.repeatCount {
                for (stepIndex, stepDefinition) in block.steps.enumerated() {
                    let sourceID = reference.stepIDs.indices.contains(stepIndex) ? reference.stepIDs[stepIndex] : stepDefinition.id
                    let resolvedID = reference.repeatCount > 1 ? "\(sourceID)-\(repetition + 1)" : sourceID
                    let targets = try resolveTargets(stepDefinition.targets, mapping: mapping, board: board)
                    let segments = try resolveSegments(
                        stepDefinition,
                        targets: targets,
                        mapping: mapping,
                        board: board
                    )
                    let resolvedStep = WorkoutStep(
                        id: resolvedID,
                        number: steps.count + 1,
                        title: stepDefinition.title,
                        instruction: stepDefinition.instruction,
                        accessory: stepDefinition.accessory,
                        duration: stepDefinition.duration,
                        phase: stepDefinition.phase,
                        targets: targets,
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

    private func resolveTargets(
        _ targets: [WorkoutTargetDefinition],
        mapping: BoardMappingDefinition?,
        board: TrainingBoard
    ) throws -> [HoldTarget] {
        var resolved: [HoldTarget] = []

        for target in targets {
            switch target {
            case .semantic(let semanticID):
                guard let mapping, let semantic = mapping.semanticHolds[semanticID] else {
                    throw PlanLibraryStoreError.missingSemanticTarget(semanticID)
                }
                resolved.append(semantic.holdTarget())
            case .semantics(let semanticIDs):
                for semanticID in semanticIDs {
                    guard let mapping, let semantic = mapping.semanticHolds[semanticID] else {
                        throw PlanLibraryStoreError.missingSemanticTarget(semanticID)
                    }
                    resolved.append(semantic.holdTarget())
                }
            case .holdIDs(let holdIDs):
                resolved.append(.ids(holdIDs))
            case let .kind(kind, fallbacks, fingerCapacity):
                // Kind targets remain board-independent and retain the
                // original fallback behavior used by AppStore.holdIDs(for:on:).
                _ = board
                resolved.append(
                    .kind(kind, fallbacks: fallbacks, fingerCapacity: fingerCapacity)
                )
            case let .feature(feature, fallbacks, fingerCapacity):
                resolved.append(
                    HoldTarget(
                        holdIDs: [],
                        kind: nil,
                        feature: feature,
                        fallbackFeatures: fallbacks,
                        fingerCapacity: fingerCapacity
                    )
                )
            }
        }

        return resolved
    }

    private func resolveSegments(
        _ step: WorkoutStepDefinition,
        targets: [HoldTarget],
        mapping: BoardMappingDefinition?,
        board: TrainingBoard
    ) throws -> [WorkoutSegment] {
        guard !step.segments.isEmpty else { return [] }

        return try step.segments.map { definition in
            let segmentTargets = try resolveTargets(
                definition.targets,
                mapping: mapping,
                board: board
            )
            return WorkoutSegment(
                kind: definition.kind,
                targets: segmentTargets,
                timing: definition.timing,
                duration: definition.duration
            )
        }
    }
}

struct PlanLibraryStore {
    let definition: PlanLibraryDefinition
    let plans: [TrainingPlan]
    let validationReport: PlanValidationReport

    init(
        definition: PlanLibraryDefinition,
        availableBoards: [TrainingBoard] = BoardCatalog.all
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
        availableBoards: [TrainingBoard] = BoardCatalog.all
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
        availableBoards: [TrainingBoard] = BoardCatalog.all
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
        "rei.hangboard-sample-workout": ["warm-up", "pull-ups"]
    ]
}

/// Converts the seed routines into the bundled plan library without changing
/// their resolved timing or order.
enum BuiltInPlanLibraryDefinition {
    private static let boardMappings = LegacyPlanSeedBoardMappings.all

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
                steps: [WorkoutStepDefinition.from(step, id: "warm-up", semanticHoldID: semanticID(for:))]
            )
        }
        let sharedCoolDown = legacyPlans.first {
            $0.steps.last?.phase == .coolDown
                && $0.steps.last?.duration == LegacyPlanSeedCatalog.sharedCoolDownDuration
        }?.steps.last.map {
            WorkoutBlockDefinition(
                id: "shared.cool-down",
                title: "Cool down",
                steps: [WorkoutStepDefinition.from($0, id: "cool-down", semanticHoldID: semanticID(for:))]
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
                    "Board mappings keep plan targets semantic and board-specific IDs replaceable."
                ]
            ),
            boardMappings: boardMappings,
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
        let semanticHoldID: ([String]) -> String? = plan.boardID == nil
            ? semanticID(for:)
            : { _ in nil }
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
        } else if plan.id.hasPrefix("metolius.contact.") || plan.id.hasPrefix("metolius.simulator-3d.") {
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
            equipment: ["hangboard"],
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
                steps: [WorkoutStepDefinition.from(first, semanticHoldID: semanticHoldID)]
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
                    WorkoutStepDefinition.from($0, semanticHoldID: semanticHoldID)
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

    private static func semanticID(for holdIDs: [String]) -> String? {
        let targetIDs = Set(holdIDs)
        for mapping in boardMappings {
            if let semanticID = mapping.semanticHolds.first(where: {
                Set($0.value.holdIDs) == targetIDs
            })?.key {
                return semanticID
            }
        }
        return nil
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

    static let evidenceOverviewURL = URL(string: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9806751/")!

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
