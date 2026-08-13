import Foundation

// MARK: - Versioned plan definitions

/// The schema version is part of the persisted document rather than being
/// inferred from the app version. That lets a future decoder migrate old
/// training libraries without changing the runtime workout model.
enum PlanDefinitionSchema {
    static let currentVersion = 3
}

struct PlanLibraryMetadata: Codable, Hashable {
    let id: String
    let version: String
    let title: String
    let generatedAt: String
    let defaultPlanID: String?
    let notes: [String]

    init(
        id: String,
        version: String,
        title: String,
        generatedAt: String,
        defaultPlanID: String? = nil,
        notes: [String] = []
    ) {
        self.id = id
        self.version = version
        self.title = title
        self.generatedAt = generatedAt
        self.defaultPlanID = defaultPlanID
        self.notes = notes
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
    let tags: [String]
    let equipment: [String]
    let notes: [String]
    let disclaimer: String?

    init(
        title: String,
        subtitle: String,
        level: String,
        sourceLabel: String,
        sourceURL: URL?,
        provenance: RoutineProvenance,
        category: String = "general",
        tags: [String] = [],
        equipment: [String] = [],
        notes: [String] = [],
        disclaimer: String? = nil
    ) {
        self.title = title
        self.subtitle = subtitle
        self.level = level
        self.sourceLabel = sourceLabel
        self.sourceURL = sourceURL
        self.provenance = provenance
        self.category = category
        self.tags = tags
        self.equipment = equipment
        self.notes = notes
        self.disclaimer = disclaimer
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
    case kind(HoldKind)
    case feature(HoldFeature, fallbacks: [HoldFeature])

    private enum CodingKeys: String, CodingKey {
        case semantic
        case semantics
        case holdIDs
        case kind
        case feature
        case fallbackFeatures
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
        if let value = try container.decodeIfPresent(HoldKind.self, forKey: .kind) {
            self = .kind(value)
            return
        }
        if let value = try container.decodeIfPresent(HoldFeature.self, forKey: .feature) {
            let fallbacks = try container.decodeIfPresent(
                [HoldFeature].self,
                forKey: .fallbackFeatures
            ) ?? []
            self = .feature(value, fallbacks: fallbacks)
            return
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
        case .kind(let value):
            try container.encode(value, forKey: .kind)
        case let .feature(value, fallbacks):
            try container.encode(value, forKey: .feature)
            if !fallbacks.isEmpty {
                try container.encode(fallbacks, forKey: .fallbackFeatures)
            }
        }
    }
}

struct WorkoutSegmentDefinition: Codable, Hashable {
    let kind: WorkoutSegmentKind
    let targets: [WorkoutTargetDefinition]
    var target: WorkoutTargetDefinition? { targets.first }
    let timing: WorkoutSegmentTiming
    let duration: TimeInterval?

    init(
        kind: WorkoutSegmentKind,
        target: WorkoutTargetDefinition?,
        timing: WorkoutSegmentTiming,
        duration: TimeInterval?
    ) {
        self.init(
            kind: kind,
            targets: target.map { [$0] } ?? [],
            timing: timing,
            duration: duration
        )
    }

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
        case target
        case targets
        case timing
        case duration
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        kind = try container.decode(WorkoutSegmentKind.self, forKey: .kind)
        if let decodedTargets = try container.decodeIfPresent(
            [WorkoutTargetDefinition].self,
            forKey: .targets
        ) {
            targets = decodedTargets
        } else if let legacyTarget = try container.decodeIfPresent(
            WorkoutTargetDefinition.self,
            forKey: .target
        ) {
            targets = [legacyTarget]
        } else {
            targets = []
        }
        timing = try container.decode(WorkoutSegmentTiming.self, forKey: .timing)
        duration = try container.decodeIfPresent(TimeInterval.self, forKey: .duration)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(kind, forKey: .kind)
        if targets.count == 1 {
            try container.encode(targets[0], forKey: .target)
        } else if !targets.isEmpty {
            try container.encode(targets, forKey: .targets)
        }
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
        activeDuration: TimeInterval? = nil
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
            return .kind(kind)
        }
        if let feature = target.feature {
            return .feature(feature, fallbacks: target.fallbackFeatures)
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
            activeDuration: step.timedWorkDuration
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
            activeDuration: activeDuration
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
    let schemaVersion: Int
    let metadata: PlanLibraryMetadata
    let boardMappings: [BoardMappingDefinition]
    let blocks: [WorkoutBlockDefinition]
    let plans: [PlanDefinition]

    init(
        schemaVersion: Int = PlanDefinitionSchema.currentVersion,
        metadata: PlanLibraryMetadata,
        boardMappings: [BoardMappingDefinition],
        blocks: [WorkoutBlockDefinition],
        plans: [PlanDefinition]
    ) {
        self.schemaVersion = schemaVersion
        self.metadata = metadata
        self.boardMappings = boardMappings
        self.blocks = blocks
        self.plans = plans
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
    case unsupportedSchema(Int)
    case validationFailed([PlanValidationIssue])
    case missingPlan(String)
    case missingBlock(String)
    case missingBoardMapping(String)
    case missingSemanticTarget(String)

    var errorDescription: String? {
        switch self {
        case .decoding(let error):
            return "The plan library could not be decoded: \(error.localizedDescription)"
        case .unsupportedSchema(let version):
            return "The plan library uses unsupported schema version \(version)."
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

        if library.schemaVersion != PlanDefinitionSchema.currentVersion {
            issues.append(
                PlanValidationIssue(
                    path: "schemaVersion",
                    message: "Expected \(PlanDefinitionSchema.currentVersion), got \(library.schemaVersion)."
                )
            )
        }

        validateLibraryMetadata(library.metadata, issues: &issues)

        var planMappingByBoardID: [String: BoardMappingDefinition] = [:]
        var planMappingPathByBoardID: [String: String] = [:]
        for (index, mapping) in library.boardMappings.enumerated() {
            let path = "boardMappings[\(index)]"
            if planMappingByBoardID[mapping.boardID] != nil {
                issues.append(PlanValidationIssue(path: path, message: "Duplicate board mapping ID \"\(mapping.boardID)\"."))
            }
            planMappingByBoardID[mapping.boardID] = mapping
            planMappingPathByBoardID[mapping.boardID] = path

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
            }
        }

        var mappingByBoardID: [String: BoardMappingDefinition] = [:]
        var semanticMappingPathByBoardID: [String: [String: String]] = [:]
        for (index, board) in availableBoards.enumerated() where mappingByBoardID[board.id] == nil {
            mappingByBoardID[board.id] = BoardMappingDefinition(
                boardID: board.id,
                semanticHolds: board.semanticHolds
            )
            semanticMappingPathByBoardID[board.id] = Dictionary(
                uniqueKeysWithValues: board.semanticHolds.keys.map {
                    ($0, "boards[\(index)].semanticHolds.\($0)")
                }
            )
        }
        for (boardID, mapping) in planMappingByBoardID {
            var semanticHolds = mappingByBoardID[boardID]?.semanticHolds ?? [:]
            semanticHolds.merge(mapping.semanticHolds) { _, planMapping in planMapping }
            var semanticPaths = semanticMappingPathByBoardID[boardID] ?? [:]
            for semanticID in mapping.semanticHolds.keys {
                semanticPaths[semanticID] = "\(planMappingPathByBoardID[boardID]!).semanticHolds.\(semanticID)"
            }
            mappingByBoardID[boardID] = BoardMappingDefinition(
                boardID: boardID,
                semanticHolds: semanticHolds
            )
            semanticMappingPathByBoardID[boardID] = semanticPaths
        }

        for (boardID, mapping) in mappingByBoardID {
            guard let board = boardByID[boardID]?.first else { continue }
            for (semanticID, target) in mapping.semanticHolds {
                guard let kind = target.kind,
                      !board.holds.contains(where: { $0.kind == kind }) else {
                    continue
                }
                issues.append(
                    PlanValidationIssue(
                        path: semanticMappingPathByBoardID[boardID]?[semanticID] ?? "semanticHolds.\(semanticID)",
                        message: "Hold kind \"\(kind.rawValue)\" has no matching hold on board \"\(boardID)\"."
                    )
                )
            }
        }

        var blockByID: [String: WorkoutBlockDefinition] = [:]
        for (index, block) in library.blocks.enumerated() {
            let path = "blocks[\(index)]"
            if blockByID[block.id] != nil {
                issues.append(PlanValidationIssue(path: path, message: "Duplicate block ID \"\(block.id)\"."))
            }
            blockByID[block.id] = block
            validateBlock(block, path: path, issues: &issues)
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
        if metadata.version.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "metadata.version", message: "Library version cannot be empty."))
        }
        if metadata.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "metadata.title", message: "Library title cannot be empty."))
        }
    }

    private static func validateBlock(
        _ block: WorkoutBlockDefinition,
        path: String,
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
            validateStep(step, path: stepPath, issues: &issues)
        }
    }

    private static func validateStep(
        _ step: WorkoutStepDefinition,
        path: String,
        issues: inout [PlanValidationIssue]
    ) {
        if step.id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(PlanValidationIssue(path: "\(path).id", message: "Step ID cannot be empty."))
        }
        if !step.duration.isFinite || step.duration <= 0 {
            issues.append(PlanValidationIssue(path: "\(path).duration", message: "Duration must be finite and greater than zero."))
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
        if step.phase != .rest && step.phase != .conditioning && step.targets.isEmpty {
            issues.append(PlanValidationIssue(path: "\(path).targets", message: "Non-rest steps need at least one target."))
        }
        let isCompoundStep = step.segments.count > 1
        for (index, segment) in step.segments.enumerated() {
            let targetPath = "\(path).segments[\(index)].target"
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
            case let .feature(feature, fallbacks):
                let acceptedFeatures = [feature] + fallbacks
                let hasCompatibleBoard = boardIDs.contains { boardID in
                    boardByID[boardID]?.first?.holds.contains { hold in
                        hold.features.contains { acceptedFeatures.contains($0) }
                    } == true
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
        guard library.schemaVersion == PlanDefinitionSchema.currentVersion else {
            throw PlanLibraryStoreError.unsupportedSchema(library.schemaVersion)
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
        let planMapping = library.boardMappings.first { $0.boardID == board.id }
        let mapping = BoardMappingDefinition(
            boardID: board.id,
            semanticHolds: board.semanticHolds.merging(planMapping?.semanticHolds ?? [:]) {
                _, planMapping in planMapping
            }
        )

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
                        timedWorkDuration: stepDefinition.activeDuration
                    )
                    for normalizedStep in try WorkoutStepNormalizer.expand(resolvedStep) {
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
            case .kind(let kind):
                // Kind targets remain board-independent and retain the
                // original fallback behavior used by AppStore.holdIDs(for:on:).
                _ = board
                resolved.append(.kind(kind))
            case let .feature(feature, fallbacks):
                resolved.append(
                    HoldTarget(
                        holdIDs: [],
                        kind: nil,
                        feature: feature,
                        fallbackFeatures: fallbacks
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
        if step.segments.isEmpty {
            if step.phase == .rest {
                return [
                    WorkoutSegment(
                        kind: .rest,
                        target: nil,
                        timing: .fixed,
                        duration: step.duration
                    )
                ]
            }
            if let activeDuration = step.activeDuration {
                let workSegment = WorkoutSegment(
                    kind: .work,
                    targets: targets,
                    timing: .fixed,
                    duration: activeDuration
                )
                var segments = [workSegment]
                let restDuration = step.duration - activeDuration
                if restDuration > 0, restDuration.isFinite {
                    segments.append(
                        WorkoutSegment(
                            kind: .rest,
                            target: nil,
                            timing: .fixed,
                            duration: restDuration
                        )
                    )
                }
                return segments
            }
            if !targets.isEmpty {
                return [
                    WorkoutSegment(
                        kind: .work,
                        targets: targets,
                        timing: .undefined,
                        duration: nil
                    )
                ]
            }
            return []
        }

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
        let normalizedDefinition = Self.normalizedDefinition(definition)
        let issues = normalizedDefinition.validationIssues(availableBoards: availableBoards)
        guard issues.isEmpty else {
            throw PlanLibraryStoreError.validationFailed(issues)
        }
        let resolver = try PlanDefinitionResolver(library: normalizedDefinition, availableBoards: availableBoards)
        self.definition = normalizedDefinition
        self.plans = try resolver.resolveAll()
        self.validationReport = PlanValidationReport(issues: issues)
    }

    private static func normalizedDefinition(_ definition: PlanLibraryDefinition) -> PlanLibraryDefinition {
        guard definition.schemaVersion == 2 else { return definition }
        return PlanLibraryDefinition(
            schemaVersion: PlanDefinitionSchema.currentVersion,
            metadata: definition.metadata,
            boardMappings: definition.boardMappings,
            blocks: definition.blocks,
            plans: definition.plans
        )
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
                return try PlanLibraryStore(contentsOf: url)
            } catch {
                fatalError("Bundled plan library failed validation: \(error.localizedDescription)")
            }
        }

        // Command-line tools and some unit-test runners do not carry the app's
        // resources. The migration document keeps those environments useful
        // without weakening validation of the actual bundled file.
        do {
            return try PlanLibraryStore(definition: BuiltInPlanLibraryDefinition.document)
        } catch {
            fatalError("Built-in plan library failed validation: \(error.localizedDescription)")
        }
    }
}

typealias PlanStore = PlanLibraryStore

private final class PlanLibraryBundleToken {}

// MARK: - Built-in migration document

/// Converts the existing routines once into the versioned representation.
/// Keeping this conversion next to the definitions makes it possible to
/// compare the resolved plans against the legacy catalog while the storage
/// format is introduced, and avoids silently changing any routine timing.
enum BuiltInPlanLibraryDefinition {
    private static let boardMappings: [BoardMappingDefinition] = BoardCatalog.all.map { board in
        BoardMappingDefinition(
            boardID: board.id,
            semanticHolds: BoardCatalog.packageStore.semantics(for: board.id).mapValues {
                SemanticHoldMappingDefinition(holdIDs: $0)
            }
        )
    }

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
                version: "3.0.0",
                title: "Hang Ten training plans",
                generatedAt: "2026-08-01",
                defaultPlanID: LegacyPlanSeedCatalog.metoliusTenMinute.id,
                notes: [
                    "Source-linked Metolius sequences are faithful task-order expansions marked adapted because the app adds guided timing.",
                    "Source cycles remain ten 60-second minutes; defaults are 5 seconds per pull-up and 1 second per other counted repetition.",
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
        let category: String
        if plan.id.hasPrefix("research.") {
            category = "research"
        } else if plan.id.hasPrefix("coach.") {
            category = "coach"
        } else if plan.id.hasPrefix("device.") {
            category = "device"
        } else if [
            LegacyPlanSeedCatalog.latticeLiteHomeAdaptations.id,
            LegacyPlanSeedCatalog.hoopersBetaIntroductory.id,
            LegacyPlanSeedCatalog.methodRepeaters.id,
            LegacyPlanSeedCatalog.methodEMOM.id,
            LegacyPlanSeedCatalog.latticeBeginnerGuide.id
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
        } else if plan.id == LegacyPlanSeedCatalog.latticeLiteHomeAdaptations.id {
            notes = [
                "Weekly-template frequencies are preserved exactly from the source sample week.",
                "The app uses 60-second manual/coach-guided preview rows because the source template does not prescribe task durations or counts."
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
        } else if plan.id == LegacyPlanSeedCatalog.latticeBeginnerGuide.id {
            notes = [
                "Reference-plan guidance is preserved without inventing counts or a weekly schedule.",
                "The app uses coach-guided preview rows; the 20-second foot-supported hang remains explicitly an example, not a universal prescription."
            ]
        } else if plan.id == LegacyPlanSeedCatalog.reiHangboardSample.id {
            notes = [
                "Source warm-up alternatives, five grip groups, 7–10s/5s interval guidance, six repeats, recovery, and pain warning are retained.",
                "The app defaults the source ranges to 7 seconds and uses a manual 25-minute warm-up preview."
            ]
        } else if plan.id == LegacyPlanSeedCatalog.rockProdigyIntermediate.id {
            notes = [
                "Trango's official manual URL: https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155",
                "The exact intermediate 7-rep then 6-rep sequence, 7s/3s intervals, 3-minute set rests, two-hand dead-hang-only rule, and no pull-ups/no lock-offs are retained.",
                "This plan is board-specific to the Trango Rock Prodigy Training Center; its warm-up jug, variable large rail, deep MR pocket, thin crimp, shallow 3-finger slot, wide pinch, and sloper resolve to the RPTC feature inventory."
            ]
        } else {
            notes = ["Preserved from the original Hang Ten routine catalog."]
        }

        let metadata = PlanMetadata(
            title: plan.title,
            subtitle: plan.subtitle,
            level: plan.level,
            sourceLabel: plan.sourceLabel,
            sourceURL: plan.sourceURL,
            provenance: plan.provenance,
            category: category,
            tags: ["built-in", category],
            equipment: ["hangboard"],
            notes: notes,
            disclaimer: "Warm up thoroughly, keep the board secure, and stop if you feel pain."
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
                steps: [WorkoutStepDefinition.from(first, semanticHoldID: semanticID(for:))]
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
                    WorkoutStepDefinition.from($0, semanticHoldID: semanticID(for:))
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
    static let latticeLiteHomeAdaptations = required("lattice.lite-home-adaptations")
    static let hoopersBetaIntroductory = required("hoopers-beta.introductory-home-hangboard")
    static let methodRepeaters = required("method.intermediate-hangboarding.repeaters")
    static let methodEMOM = required("method.intermediate-hangboarding.emom")
    static let latticeBeginnerGuide = required("lattice.beginner-climbers-training-guide")
    static let reiHangboardSample = required("rei.hangboard-sample-workout")
    static let rockProdigyIntermediate = required("trango.rock-prodigy-training-center.intermediate")

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
