import Foundation

enum CustomRoutineTargetMode: Hashable, Codable {
    case boardSpecific(boardID: String)
    case generic

    private enum CodingKeys: String, CodingKey {
        case kind
        case boardID
    }

    private enum Kind: String, Codable {
        case boardSpecific
        case generic
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        switch try container.decode(Kind.self, forKey: .kind) {
        case .boardSpecific:
            self = .boardSpecific(boardID: try container.decode(String.self, forKey: .boardID))
        case .generic:
            self = .generic
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case let .boardSpecific(boardID):
            try container.encode(Kind.boardSpecific, forKey: .kind)
            try container.encode(boardID, forKey: .boardID)
        case .generic:
            try container.encode(Kind.generic, forKey: .kind)
        }
    }
}

struct CustomRoutineDefinition: Codable, Hashable, Identifiable {
    let id: String
    let title: String
    let subtitle: String
    let difficulty: String?
    let category: String?
    let tags: [String]
    let targetMode: CustomRoutineTargetMode
    let steps: [WorkoutStepDefinition]

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case subtitle
        case difficulty
        case category
        case tags
        case targetMode
        case steps
    }

    init(
        id: String,
        title: String,
        subtitle: String,
        difficulty: String?,
        category: String?,
        tags: [String],
        targetMode: CustomRoutineTargetMode,
        steps: [WorkoutStepDefinition]
    ) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.difficulty = difficulty
        self.category = category
        self.tags = tags
        self.targetMode = targetMode
        self.steps = steps
    }
}

struct CustomRoutineLibrary: Codable, Hashable {
    static let currentSchemaVersion = 1

    let schemaVersion: Int
    let routines: [CustomRoutineDefinition]

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case routines
    }

    init(schemaVersion: Int = Self.currentSchemaVersion, routines: [CustomRoutineDefinition]) {
        self.schemaVersion = schemaVersion
        self.routines = routines
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        routines = try container.decode([CustomRoutineDefinition].self, forKey: .routines)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(schemaVersion, forKey: .schemaVersion)
        try container.encode(routines, forKey: .routines)
    }
}

protocol CustomRoutineStoring: AnyObject {
    var routines: [CustomRoutineDefinition] { get }
    var persistenceError: String? { get }
    func save(_ routine: CustomRoutineDefinition) throws
    func delete(id: String) throws
    func plan(for definition: CustomRoutineDefinition) throws -> TrainingPlan
}

enum CustomRoutineValidationIssue: Error, Equatable {
    case invalidID(id: String)
    case builtInIDCollision(id: String)
    case emptyTitle
    case missingSteps
    case duplicateStepID(stepIndex: Int)
    case invalidDuration(stepIndex: Int)
    case invalidActiveDuration(stepIndex: Int)
    case missingTargets(stepIndex: Int)
    case restStepHasTargets(stepIndex: Int)
    case unknownBoard(boardID: String)
    case unknownHoldID(stepIndex: Int, holdID: String)
    case unresolvableTargets(stepIndex: Int)
    case missingWorkSegmentTargets(stepIndex: Int, segmentIndex: Int)
    case restSegmentHasTargets(stepIndex: Int, segmentIndex: Int)
    case invalidRestSegmentTiming(stepIndex: Int, segmentIndex: Int)
    case missingFixedSegmentDuration(stepIndex: Int, segmentIndex: Int)
    case invalidSegmentDuration(stepIndex: Int, segmentIndex: Int)
    case unexpectedSegmentDuration(stepIndex: Int, segmentIndex: Int)
    case invalidCompoundSegmentTiming(stepIndex: Int, segmentIndex: Int)
    case compoundDurationMismatch(stepIndex: Int)
    case unresolvableSegmentTargets(stepIndex: Int, segmentIndex: Int)
    case targetModeMismatch(stepIndex: Int, segmentIndex: Int?)
    case noCompatibleBoard
}

enum CustomRoutineValidator {
    static func issues(
        for definition: CustomRoutineDefinition,
        availableBoards: [TrainingBoard]
    ) -> [CustomRoutineValidationIssue] {
        var issues = idIssues(for: definition.id)
        if definition.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(.emptyTitle)
        }
        if definition.steps.isEmpty {
            issues.append(.missingSteps)
        }

        let boards: [TrainingBoard]
        switch definition.targetMode {
        case let .boardSpecific(boardID):
            if let board = availableBoards.first(where: { $0.id == boardID }) {
                boards = [board]
            } else {
                boards = []
                issues.append(.unknownBoard(boardID: boardID))
            }
        case .generic:
            boards = availableBoards
        }

        var stepIDs = Set<String>()
        for (stepIndex, step) in definition.steps.enumerated() {
            if !stepIDs.insert(step.id).inserted {
                issues.append(.duplicateStepID(stepIndex: stepIndex))
            }
            if !step.duration.isFinite || step.duration <= 0 {
                issues.append(.invalidDuration(stepIndex: stepIndex))
            }
            if let activeDuration = step.activeDuration,
               !activeDuration.isFinite || activeDuration <= 0 || activeDuration > step.duration {
                issues.append(.invalidActiveDuration(stepIndex: stepIndex))
            }

            if step.phase == .rest {
                if !step.targets.isEmpty {
                    issues.append(.restStepHasTargets(stepIndex: stepIndex))
                }
            } else if step.targets.isEmpty {
                issues.append(.missingTargets(stepIndex: stepIndex))
            }
            if !step.targets.isEmpty {
                validate(
                    targets: step.targets,
                    stepIndex: stepIndex,
                    segmentIndex: nil,
                    boards: boards,
                    targetMode: definition.targetMode,
                    issues: &issues
                )
            }

            for (segmentIndex, segment) in step.segments.enumerated() {
                if segment.kind == .work && segment.targets.isEmpty {
                    issues.append(.missingWorkSegmentTargets(stepIndex: stepIndex, segmentIndex: segmentIndex))
                } else if segment.kind == .rest && !segment.targets.isEmpty {
                    issues.append(.restSegmentHasTargets(stepIndex: stepIndex, segmentIndex: segmentIndex))
                }
                if !segment.targets.isEmpty {
                    validate(
                        targets: segment.targets,
                        stepIndex: stepIndex,
                        segmentIndex: segmentIndex,
                        boards: boards,
                        targetMode: definition.targetMode,
                        issues: &issues
                    )
                }

                if segment.kind == .rest && segment.timing != .fixed {
                    issues.append(.invalidRestSegmentTiming(stepIndex: stepIndex, segmentIndex: segmentIndex))
                }
                switch segment.timing {
                case .fixed:
                    guard let duration = segment.duration else {
                        issues.append(.missingFixedSegmentDuration(stepIndex: stepIndex, segmentIndex: segmentIndex))
                        break
                    }
                    if !duration.isFinite || duration <= 0 {
                        issues.append(.invalidSegmentDuration(stepIndex: stepIndex, segmentIndex: segmentIndex))
                    }
                case .stopwatch, .undefined:
                    if segment.duration != nil {
                        issues.append(.unexpectedSegmentDuration(stepIndex: stepIndex, segmentIndex: segmentIndex))
                    }
                }
            }

            if step.segments.count > 1 {
                for (segmentIndex, segment) in step.segments.enumerated()
                where segment.timing != .fixed {
                    issues.append(
                        .invalidCompoundSegmentTiming(
                            stepIndex: stepIndex,
                            segmentIndex: segmentIndex
                        )
                    )
                }
                let durations = step.segments.compactMap(\.duration)
                if durations.count == step.segments.count,
                   durations.reduce(0, +) != step.duration {
                    issues.append(.compoundDurationMismatch(stepIndex: stepIndex))
                }
            }
        }

        if definition.targetMode == .generic,
           !definition.steps.isEmpty,
           compatibleBoards(for: definition, availableBoards: availableBoards).isEmpty {
            issues.append(.noCompatibleBoard)
        }
        return issues
    }

    static func idIssues(for id: String) -> [CustomRoutineValidationIssue] {
        var issues: [CustomRoutineValidationIssue] = []
        if id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
            !id.hasPrefix("custom.") || id == "custom." {
            issues.append(.invalidID(id: id))
        }
        if PlanCatalog.all.contains(where: { $0.id == id }) {
            issues.append(.builtInIDCollision(id: id))
        }
        return issues
    }

    static func compatibleBoards(
        for definition: CustomRoutineDefinition,
        availableBoards: [TrainingBoard]
    ) -> [TrainingBoard] {
        availableBoards.filter { board in
            definition.steps.allSatisfy { step in
                (step.phase == .rest || targetsResolve(step.targets, on: board)) && step.segments.allSatisfy { segment in
                    segment.kind == .rest || targetsResolve(segment.targets, on: board)
                }
            }
        }
    }

    private static func validate(
        targets: [WorkoutTargetDefinition],
        stepIndex: Int,
        segmentIndex: Int?,
        boards: [TrainingBoard],
        targetMode: CustomRoutineTargetMode,
        issues: inout [CustomRoutineValidationIssue]
    ) {
        guard targets.allSatisfy({ targetMatchesMode($0, targetMode: targetMode) }) else {
            issues.append(.targetModeMismatch(stepIndex: stepIndex, segmentIndex: segmentIndex))
            return
        }

        if targetMode.isBoardSpecific {
            let knownHoldIDs = Set(boards.flatMap(\.holds).map(\.id))
            for target in targets {
                guard case let .holdIDs(holdIDs) = target else { continue }
                for holdID in holdIDs where !knownHoldIDs.contains(holdID) {
                    issues.append(.unknownHoldID(stepIndex: stepIndex, holdID: holdID))
                }
            }
        }

        guard targets.allSatisfy({ targetResolves($0, onAny: boards) }) else {
            if let segmentIndex {
                issues.append(.unresolvableSegmentTargets(stepIndex: stepIndex, segmentIndex: segmentIndex))
            } else {
                issues.append(.unresolvableTargets(stepIndex: stepIndex))
            }
            return
        }
    }

    private static func targetMatchesMode(
        _ target: WorkoutTargetDefinition,
        targetMode: CustomRoutineTargetMode
    ) -> Bool {
        switch (targetMode, target) {
        case (.boardSpecific, .holdIDs), (.generic, .kind), (.generic, .feature):
            true
        default:
            false
        }
    }

    private static func targetsResolve(
        _ targets: [WorkoutTargetDefinition],
        on board: TrainingBoard
    ) -> Bool {
        !targets.isEmpty && targets.allSatisfy { targetResolves($0, on: board) }
    }

    private static func targetResolves(
        _ target: WorkoutTargetDefinition,
        onAny boards: [TrainingBoard]
    ) -> Bool {
        boards.contains { targetResolves(target, on: $0) }
    }

    private static func targetResolves(_ target: WorkoutTargetDefinition, on board: TrainingBoard) -> Bool {
        switch target {
        case .semantic, .semantics:
            return false
        case let .holdIDs(holdIDs):
            return !holdIDs.isEmpty && Set(holdIDs).isSubset(of: Set(board.holds.map(\.id)))
        case let .kind(kind):
            return board.holds.contains { $0.kind == kind }
        case let .feature(feature, fallbacks):
            let acceptedFeatures = Set([feature] + fallbacks)
            return board.holds.contains {
                !($0.features ?? []).isDisjoint(with: acceptedFeatures)
            }
        }
    }
}

enum CustomRoutineStoreError: LocalizedError {
    case validationFailed([CustomRoutineValidationIssue])
    case unsupportedSchema(Int)

    var errorDescription: String? {
        switch self {
        case let .validationFailed(issues):
            return "Custom routine validation failed: \(issues)"
        case let .unsupportedSchema(version):
            return "Unsupported custom routine schema version \(version)."
        }
    }
}

final class CustomRoutineStore: CustomRoutineStoring {
    static let defaultKey = "HangTen.customRoutines.v1"

    private let defaults: UserDefaults
    private let key: String
    private let availableBoards: [TrainingBoard]

    private(set) var routines: [CustomRoutineDefinition]
    private(set) var persistenceError: String?

    init(
        defaults: UserDefaults = .standard,
        key: String = CustomRoutineStore.defaultKey,
        availableBoards: [TrainingBoard] = BoardCatalog.all
    ) {
        self.defaults = defaults
        self.key = key
        self.availableBoards = availableBoards
        routines = []
        persistenceError = nil
        load()
    }

    func save(_ routine: CustomRoutineDefinition) throws {
        let flattenedRoutineDefinition = try flattenedDefinition(from: routine)

        var updatedRoutines = routines
        if let index = updatedRoutines.firstIndex(where: { $0.id == flattenedRoutineDefinition.id }) {
            updatedRoutines[index] = flattenedRoutineDefinition
        } else {
            updatedRoutines.append(flattenedRoutineDefinition)
        }
        try persist(updatedRoutines)
        routines = updatedRoutines
        persistenceError = nil
    }

    func delete(id: String) throws {
        var updatedRoutines = routines
        guard let index = updatedRoutines.firstIndex(where: { $0.id == id }) else { return }
        updatedRoutines.remove(at: index)
        try persist(updatedRoutines)
        routines = updatedRoutines
        persistenceError = nil
    }

    func plan(for definition: CustomRoutineDefinition) throws -> TrainingPlan {
        let definition = Self.normalize(definition)
        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: availableBoards)
        guard issues.isEmpty else {
            throw CustomRoutineStoreError.validationFailed(issues)
        }

        let boardID: String?
        let resolverBoards: [TrainingBoard]
        switch definition.targetMode {
        case let .boardSpecific(id):
            boardID = id
            resolverBoards = availableBoards.filter { $0.id == id }
        case .generic:
            boardID = nil
            resolverBoards = CustomRoutineValidator.compatibleBoards(
                for: definition,
                availableBoards: availableBoards
            )
        }
        let metadata = Self.metadata(for: definition)
        let block = WorkoutBlockDefinition(
            id: "\(definition.id).custom-block",
            title: definition.title,
            steps: definition.steps
        )
        let planDefinition = PlanDefinition(
            id: definition.id,
            metadata: metadata,
            boardID: boardID,
            blocks: [WorkoutBlockReference(blockID: block.id)]
        )
        let library = PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "hang-ten.custom-routine",
                version: "1",
                title: "Custom routine",
                generatedAt: "local"
            ),
            boardMappings: [],
            blocks: [block],
            plans: [planDefinition]
        )
        let resolver = try PlanDefinitionResolver(library: library, availableBoards: resolverBoards)
        return try resolver.resolve(planDefinition)
    }

    static func definition(
        from plan: TrainingPlan,
        metadata: PlanMetadata,
        id: String
    ) throws -> CustomRoutineDefinition {
        let definition = normalize(
            CustomRoutineDefinition(
                id: id,
                title: metadata.title,
                subtitle: metadata.subtitle,
                difficulty: metadata.level,
                category: metadata.category,
                tags: metadata.tags,
                targetMode: plan.boardID.map { .boardSpecific(boardID: $0) } ?? .generic,
                steps: plan.steps.map { WorkoutStepDefinition.from($0) }
            )
        )
        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)
        guard issues.isEmpty else {
            throw CustomRoutineStoreError.validationFailed(issues)
        }
        return definition
    }

    static func metadata(for definition: CustomRoutineDefinition) -> PlanMetadata {
        PlanMetadata(
            title: definition.title,
            subtitle: definition.subtitle,
            level: definition.difficulty ?? "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom,
            category: definition.category ?? "custom",
            tags: definition.tags
        )
    }

    private func load() {
        guard let data = defaults.data(forKey: key) else { return }
        do {
            let library = try JSONDecoder().decode(CustomRoutineLibrary.self, from: data)
            guard library.schemaVersion == CustomRoutineLibrary.currentSchemaVersion else {
                throw CustomRoutineStoreError.unsupportedSchema(library.schemaVersion)
            }
            var loadedRoutineIDs = Set<String>()
            let validRoutines = library.routines.filter { routine in
                CustomRoutineValidator.idIssues(for: routine.id).isEmpty &&
                    loadedRoutineIDs.insert(routine.id).inserted
            }
            routines = validRoutines.map(Self.normalize)
            if validRoutines.count != library.routines.count {
                persistenceError = "Some custom routines could not be loaded."
            }
        } catch {
            routines = []
            persistenceError = error.localizedDescription
        }
    }

    private func persist(_ routines: [CustomRoutineDefinition]) throws {
        let library = CustomRoutineLibrary(routines: routines)
        let data = try JSONEncoder().encode(library)
        defaults.set(data, forKey: key)
    }

    private func flattenedDefinition(
        from definition: CustomRoutineDefinition
    ) throws -> CustomRoutineDefinition {
        let plan = try plan(for: definition)
        let flattenedRoutineDefinition = Self.normalize(
            CustomRoutineDefinition(
                id: definition.id,
                title: definition.title,
                subtitle: definition.subtitle,
                difficulty: definition.difficulty,
                category: definition.category,
                tags: definition.tags,
                targetMode: definition.targetMode,
                steps: plan.steps.map {
                    WorkoutStepDefinition.from($0).strippingUnsupportedCustomCueFields()
                }
            )
        )
        let issues = CustomRoutineValidator.issues(
            for: flattenedRoutineDefinition,
            availableBoards: availableBoards
        )
        guard issues.isEmpty else {
            throw CustomRoutineStoreError.validationFailed(issues)
        }
        return flattenedRoutineDefinition
    }

    private static func normalize(_ definition: CustomRoutineDefinition) -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: definition.id,
            title: definition.title.trimmingCharacters(in: .whitespacesAndNewlines),
            subtitle: definition.subtitle.trimmingCharacters(in: .whitespacesAndNewlines),
            difficulty: normalizedOptional(definition.difficulty),
            category: normalizedOptional(definition.category),
            tags: normalizedTags(definition.tags),
            targetMode: definition.targetMode,
            steps: definition.steps.map { $0.strippingUnsupportedCustomCueFields() }
        )
    }

    private static func normalizedOptional(_ value: String?) -> String? {
        guard let value else { return nil }
        let normalized = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized.isEmpty ? nil : normalized
    }

    private static func normalizedTags(_ tags: [String]) -> [String] {
        CustomRoutineTagNormalizer.normalizedTags(from: tags)
    }
}

private extension CustomRoutineTargetMode {
    var isBoardSpecific: Bool {
        if case .boardSpecific = self {
            return true
        }
        return false
    }
}
