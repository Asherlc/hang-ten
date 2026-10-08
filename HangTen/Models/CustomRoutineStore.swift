import Foundation

private struct CustomRoutineCodingKey: CodingKey {
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
    func rejectFormerCustomRoutineKeys(_ keys: Set<String>) throws {
        let container = try container(keyedBy: CustomRoutineCodingKey.self)
        guard let key = container.allKeys.first(where: { keys.contains($0.stringValue) }) else {
            return
        }

        throw DecodingError.dataCorruptedError(
            forKey: key,
            in: container,
            debugDescription: "Former custom-routine field \(key.stringValue) is not supported."
        )
    }
}

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

/// A consecutive sequence of authored steps with a shared total run count.
/// A single-step set supplies the editor's individual repeat controls.
struct CustomRoutineSet: Codable, Hashable, Identifiable {
    static let supportedCounts = 1...100

    let id: String
    var stepIDs: [String]
    var repeatCount: Int

    /// Retains authored step IDs once; the repeat count includes the first run.
    init(id: String = UUID().uuidString, stepIDs: [String], repeatCount: Int = 2) {
        self.id = id
        self.stepIDs = stepIDs
        self.repeatCount = repeatCount
    }

    /// Returns the matching contiguous range, or nil for missing or reordered members.
    func range(in orderedStepIDs: [String]) -> Range<Int>? {
        guard let first = stepIDs.first,
              let start = orderedStepIDs.firstIndex(of: first),
              stepIDs.count <= orderedStepIDs.count - start else { return nil }
        let range = start..<(start + stepIDs.count)
        return Array(orderedStepIDs[range]) == stepIDs ? range : nil
    }
}

/// An editable routine whose steps remain unexpanded until workout resolution.
struct CustomRoutineDefinition: Codable, Hashable, Identifiable {
    let id: String
    let title: String
    let subtitle: String
    let difficulty: String?
    let category: String?
    let tags: [String]
    let targetMode: CustomRoutineTargetMode
    let steps: [WorkoutStepDefinition]
    let sets: [CustomRoutineSet]

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case subtitle
        case difficulty
        case category
        case tags
        case targetMode
        case steps
        case sets
        case legacySets = "repeatGroups"
    }

    /// Retains literal steps and their set declarations without expanding repeated runs.
    init(
        id: String,
        title: String,
        subtitle: String,
        difficulty: String?,
        category: String?,
        tags: [String],
        targetMode: CustomRoutineTargetMode,
        steps: [WorkoutStepDefinition],
        sets: [CustomRoutineSet] = []
    ) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.difficulty = difficulty
        self.category = category
        self.tags = tags
        self.targetMode = targetMode
        self.steps = steps
        self.sets = sets
    }

    /// Prefers current set data and falls back to the legacy repeatGroups field.
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        subtitle = try container.decode(String.self, forKey: .subtitle)
        difficulty = try container.decodeIfPresent(String.self, forKey: .difficulty)
        category = try container.decodeIfPresent(String.self, forKey: .category)
        tags = try container.decode([String].self, forKey: .tags)
        targetMode = try container.decode(CustomRoutineTargetMode.self, forKey: .targetMode)
        steps = try container.decode([WorkoutStepDefinition].self, forKey: .steps)
        sets = try container.decodeIfPresent([CustomRoutineSet].self, forKey: .sets)
            ?? container.decodeIfPresent([CustomRoutineSet].self, forKey: .legacySets)
            ?? []
    }

    /// Saves authored steps and set metadata using only the current sets field.
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(title, forKey: .title)
        try container.encode(subtitle, forKey: .subtitle)
        try container.encodeIfPresent(difficulty, forKey: .difficulty)
        try container.encodeIfPresent(category, forKey: .category)
        try container.encode(tags, forKey: .tags)
        try container.encode(targetMode, forKey: .targetMode)
        try container.encode(steps, forKey: .steps)
        try container.encode(sets, forKey: .sets)
    }
}

struct CustomRoutineLibrary: Codable, Hashable {
    let routines: [CustomRoutineDefinition]

    init(routines: [CustomRoutineDefinition]) {
        self.routines = routines
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectFormerCustomRoutineKeys(["schemaVersion"])
        let container = try decoder.container(keyedBy: CustomRoutineCodingKey.self)
        routines = try container.decode([CustomRoutineDefinition].self, forKey: CustomRoutineCodingKey(stringValue: "routines")!)
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
    case duplicateSetID(setIndex: Int)
    case invalidSetRepeatCount(setIndex: Int)
    case invalidSetSteps(setIndex: Int)
    case overlappingSetSteps(setIndex: Int)
    case invalidDuration(stepIndex: Int)
    case invalidActiveDuration(stepIndex: Int)
    case invalidHandUseSide(stepIndex: Int)
    case invalidActionRepetitions(stepIndex: Int)
    case invalidExternalLoad(stepIndex: Int)
    case terminalRestStep
    case missingTargets(stepIndex: Int)
    case restStepHasTargets(stepIndex: Int)
    case unknownBoard(boardID: String)
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
    /// Collects routine identity, step semantics, target compatibility, timing, and set validation failures.
    static func issues(
        for definition: CustomRoutineDefinition,
        availableBoards: [BoardRevision]
    ) -> [CustomRoutineValidationIssue] {
        var issues = idIssues(for: definition.id)
        if definition.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(.emptyTitle)
        }
        if definition.steps.isEmpty {
            issues.append(.missingSteps)
        } else if let issue = terminalRestIssue(for: definition) {
            issues.append(issue)
        }
        issues += setIssues(for: definition)

        let boards: [BoardRevision]
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
            if !WorkoutStepSemantics.hasValidHandUseAndSide(step.handUse, step.side) ||
                !WorkoutStepSemantics.hasValidHandUse(
                    step.handUse,
                    phase: step.phase,
                    action: step.action
                ) {
                issues.append(.invalidHandUseSide(stepIndex: stepIndex))
            }
            if !WorkoutStepSemantics.hasValidActionAndRepetitions(step.action, step.repetitions) {
                issues.append(.invalidActionRepetitions(stepIndex: stepIndex))
            }
            if !WorkoutStepSemantics.hasValidExternalLoad(step.externalLoadKGF) {
                issues.append(.invalidExternalLoad(stepIndex: stepIndex))
            }

            if step.phase == .rest {
                if step.segments.contains(where: { $0.target != nil }) {
                    issues.append(.restStepHasTargets(stepIndex: stepIndex))
                }
            } else {
                let workSegments = step.segments.filter { $0.kind == .work }
                if workSegments.isEmpty {
                    issues.append(.missingTargets(stepIndex: stepIndex))
                }
                for (segmentIndex, segment) in step.segments.enumerated() where segment.kind == .work {
                    switch segment.target {
                    case .none, .selfSelected:
                        issues.append(.missingWorkSegmentTargets(stepIndex: stepIndex, segmentIndex: segmentIndex))
                    case .tasks where segment.target?.isSelfSelected == true:
                        issues.append(.missingWorkSegmentTargets(stepIndex: stepIndex, segmentIndex: segmentIndex))
                    case .requirements, .tasks:
                        let requirements = segment.contactRequirements
                        if requirements.isEmpty {
                            issues.append(.missingWorkSegmentTargets(stepIndex: stepIndex, segmentIndex: segmentIndex))
                            continue
                        }
                        validate(
                            targets: requirements,
                            stepIndex: stepIndex,
                            segmentIndex: segmentIndex,
                            boards: boards,
                            targetMode: definition.targetMode,
                            handUse: step.handUse,
                            side: step.side,
                            issues: &issues
                        )
                    }
                }
            }
            for (segmentIndex, segment) in step.segments.enumerated() {
                if segment.kind == .rest && segment.target != nil {
                    issues.append(.restSegmentHasTargets(stepIndex: stepIndex, segmentIndex: segmentIndex))
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

    /// Reports duplicate IDs, unsupported counts, invalid ranges, and overlapping sets.
    static func setIssues(for definition: CustomRoutineDefinition) -> [CustomRoutineValidationIssue] {
        var issues: [CustomRoutineValidationIssue] = []
        var setIDs = Set<String>()
        var usedStepIDs = Set<String>()
        let stepIDs = definition.steps.map(\.id)
        for (index, set) in definition.sets.enumerated() {
            if !setIDs.insert(set.id).inserted {
                issues.append(.duplicateSetID(setIndex: index))
            }
            if !CustomRoutineSet.supportedCounts.contains(set.repeatCount) {
                issues.append(.invalidSetRepeatCount(setIndex: index))
            }
            if set.range(in: stepIDs) == nil || Set(set.stepIDs).count != set.stepIDs.count {
                issues.append(.invalidSetSteps(setIndex: index))
            }
            if !usedStepIDs.isDisjoint(with: set.stepIDs) {
                issues.append(.overlappingSetSteps(setIndex: index))
            }
            usedStepIDs.formUnion(set.stepIDs)
        }
        return issues
    }

    static func compatibleBoards(
        for definition: CustomRoutineDefinition,
        availableBoards: [BoardRevision]
    ) -> [BoardRevision] {
        availableBoards.filter { board in
            definition.steps.allSatisfy { step in
                (step.phase == .rest || targetsResolve(
                    step.workRequirements,
                    handUse: step.handUse,
                    side: step.side,
                    on: board
                )) && step.segments.allSatisfy { segment in
                    segment.kind == .rest || targetsResolve(
                        segment.contactRequirements,
                        handUse: step.handUse,
                        side: step.side,
                        on: board
                    )
                }
            }
        }
    }

    /// Permits final recovery only within a multi-step set that also contains work.
    static func terminalRestIssue(for definition: CustomRoutineDefinition) -> CustomRoutineValidationIssue? {
        guard definition.steps.last.map(stepEndsInRestAfterNormalization) == true else { return nil }
        // An athlete-authored work/rest set retains its complete final run,
        // including the selected recovery. Standalone final rests still fail.
        let stepIDs = definition.steps.map(\.id)
        for set in definition.sets {
            if CustomRoutineSet.supportedCounts.contains(set.repeatCount),
               let range = set.range(in: stepIDs),
               range.count > 1, range.upperBound == definition.steps.count,
               definition.steps[range].contains(where: { $0.phase != .rest }) {
                return nil
            }
        }
        return .terminalRestStep
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

    private static func validate(
        targets: [ContactRequirement],
        stepIndex: Int,
        segmentIndex: Int?,
        boards: [BoardRevision],
        targetMode: CustomRoutineTargetMode,
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        issues: inout [CustomRoutineValidationIssue]
    ) {
        guard targets.allSatisfy({ targetMatchesMode($0, targetMode: targetMode) }) else {
            issues.append(.targetModeMismatch(stepIndex: stepIndex, segmentIndex: segmentIndex))
            return
        }

        guard targets.allSatisfy({
            targetResolves($0, handUse: handUse, side: side, onAny: boards)
        }) else {
            if let segmentIndex {
                issues.append(.unresolvableSegmentTargets(stepIndex: stepIndex, segmentIndex: segmentIndex))
            } else {
                issues.append(.unresolvableTargets(stepIndex: stepIndex))
            }
            return
        }
    }

    private static func targetMatchesMode(
        _ target: ContactRequirement,
        targetMode: CustomRoutineTargetMode
    ) -> Bool {
        switch targetMode {
        case .boardSpecific:
            return true
        case .generic:
            return target.contactID == nil
        }
    }

    private static func targetsResolve(
        _ targets: [ContactRequirement],
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        on board: BoardRevision
    ) -> Bool {
        !targets.isEmpty && targets.allSatisfy {
            targetResolves($0, handUse: handUse, side: side, on: board)
        }
    }

    private static func targetResolves(
        _ target: ContactRequirement,
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        onAny boards: [BoardRevision]
    ) -> Bool {
        boards.contains {
            targetResolves(target, handUse: handUse, side: side, on: $0)
        }
    }

    private static func targetResolves(
        _ target: ContactRequirement,
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        on board: BoardRevision
    ) -> Bool {
        if handUse == .either {
            return [WorkoutSide.left, .right].allSatisfy { selectedSide in
                targetResolves(target, handUse: .single, side: selectedSide, on: board)
            }
        }
        let step = WorkoutStep(
            id: "custom-validation",
            number: 0,
            title: "Validation",
            instruction: "",
            accessory: "",
            duration: 1,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([target]),
                    timing: .undefined,
                    duration: nil
                )
            ],
            handUse: handUse,
            side: side
        )
        return (try? ContactResolver.resolve(target, step: step, board: board)) != nil
    }
}

enum CustomRoutineStoreError: LocalizedError {
    case validationFailed([CustomRoutineValidationIssue])

    var errorDescription: String? {
        switch self {
        case let .validationFailed(issues):
            return "Custom routine validation failed: \(issues)"
        }
    }
}

final class CustomRoutineStore: CustomRoutineStoring {
    static let defaultKey = "HangTen.customRoutines.v2"
    static let legacyKeys = ["HangTen.customRoutines", "HangTen.customRoutines.v1"]

    private let defaults: UserDefaults
    private let key: String
    private let availableBoards: [BoardRevision]

    private(set) var routines: [CustomRoutineDefinition]
    private(set) var persistenceError: String?

    init(
        defaults: UserDefaults = .standard,
        key: String = CustomRoutineStore.defaultKey,
        availableBoards: [BoardRevision] = BoardCatalog.all
    ) {
        self.defaults = defaults
        self.key = key
        self.availableBoards = availableBoards
        routines = []
        persistenceError = nil
        Self.removeLegacyPersistence(from: defaults)
        load()
    }

    static func removeLegacyPersistence(from defaults: UserDefaults) {
        legacyKeys.forEach(defaults.removeObject(forKey:))
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

    /// Validates the routine and resolves each set through the shared repeated-block planner.
    func plan(for definition: CustomRoutineDefinition) throws -> TrainingPlan {
        let definition = Self.normalize(definition)
        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: availableBoards)
        guard issues.isEmpty else {
            throw CustomRoutineStoreError.validationFailed(issues)
        }

        let boardID: String?
        let resolverBoards: [BoardRevision]
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
        var blocks: [WorkoutBlockDefinition] = []
        var references: [WorkoutBlockReference] = []
        let stepIDs = definition.steps.map(\.id)
        var index = 0
        while index < definition.steps.count {
            let set = definition.sets.first { $0.range(in: stepIDs)?.lowerBound == index }
            let end = set?.range(in: stepIDs)?.upperBound ?? index + 1
            let block = WorkoutBlockDefinition(
                id: "\(definition.id).custom-block-\(index)",
                steps: Array(definition.steps[index..<end])
            )
            blocks.append(block)
            references.append(WorkoutBlockReference(blockID: block.id, repeatCount: set?.repeatCount ?? 1))
            index = end
        }
        let planDefinition = PlanDefinition(
            id: definition.id,
            metadata: metadata,
            boardID: boardID,
            blocks: references
        )
        let library = PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "hang-ten.custom-routine",
                title: "Custom routine",
                generatedAt: "local"
            ),
            blocks: blocks,
            plans: [planDefinition]
        )
        let resolver = try PlanDefinitionResolver(library: library, availableBoards: resolverBoards)
        return try resolver.resolve(planDefinition)
    }

    /// Reconstructs editable patterns and set counts from a resolved plan's declared repeats.
    static func definition(
        from plan: TrainingPlan,
        metadata: PlanMetadata,
        id: String
    ) throws -> CustomRoutineDefinition {
        var steps: [WorkoutStepDefinition] = []
        var sets: [CustomRoutineSet] = []
        var index = 0
        for item in plan.stepRepeats.sorted(by: { $0.stepRange.lowerBound < $1.stepRange.lowerBound }) {
            guard item.repeatCount > 1,
                  CustomRoutineSet.supportedCounts.contains(item.repeatCount),
                  item.stepRange.lowerBound >= index,
                  item.stepRange.upperBound <= plan.steps.count,
                  !item.stepRange.isEmpty,
                  item.stepRange.count % item.repeatCount == 0,
                  item.patternTitles.isEmpty || item.patternTitles.count == item.patternStepCount else { continue }
            steps += plan.steps[index..<item.stepRange.lowerBound].map { WorkoutStepDefinition.from($0) }
            let patternRange = item.stepRange.lowerBound..<(item.stepRange.lowerBound + item.patternStepCount)
            let pattern = plan.steps[patternRange].enumerated().map { offset, step in
                WorkoutStepDefinition.from(
                    step, title: item.patternTitles.isEmpty ? nil : item.patternTitles[offset]
                )
            }
            steps += pattern
            sets.append(CustomRoutineSet(
                id: "\(id).set-\(sets.count + 1)",
                stepIDs: pattern.map(\.id), repeatCount: item.repeatCount
            ))
            index = item.stepRange.upperBound
        }
        steps += plan.steps[index...].map { WorkoutStepDefinition.from($0) }
        let definition = normalize(
            CustomRoutineDefinition(
                id: id,
                title: metadata.title,
                subtitle: metadata.subtitle,
                difficulty: metadata.level,
                category: metadata.category,
                tags: metadata.tags,
                targetMode: plan.boardID.map { .boardSpecific(boardID: $0) } ?? .generic,
                steps: steps,
                sets: sets
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

    /// Canonicalizes compound steps and remaps set member IDs while retaining each repeat pattern once.
    private func flattenedDefinition(
        from definition: CustomRoutineDefinition
    ) throws -> CustomRoutineDefinition {
        // Validate the expanded session, but persist each authored step only
        // once so repeat ranges and counts remain editable after reopening.
        _ = try plan(for: definition)
        let normalized = Self.normalize(definition)
        var expandedIDsBySourceID: [String: [String]] = [:]
        let literalSteps = try normalized.steps.flatMap { step in
            let canonical = WorkoutStepNormalizer.materializingImplicitSegments(step.resolvedStep())
            let expanded = try WorkoutStepNormalizer.expand(canonical)
            expandedIDsBySourceID[step.id] = expanded.map(\.id)
            return expanded.map { WorkoutStepDefinition.from($0).strippingUnsupportedCustomCueFields() }
        }
        let flattenedRoutineDefinition = Self.normalize(
            CustomRoutineDefinition(
                id: definition.id,
                title: definition.title,
                subtitle: definition.subtitle,
                difficulty: definition.difficulty,
                category: definition.category,
                tags: definition.tags,
                targetMode: definition.targetMode,
                steps: literalSteps,
                sets: normalized.sets.map { set in
                    CustomRoutineSet(
                        id: set.id,
                        stepIDs: set.stepIDs.flatMap { expandedIDsBySourceID[$0] ?? [] },
                        repeatCount: set.repeatCount
                    )
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
        _ = try plan(for: flattenedRoutineDefinition)
        return flattenedRoutineDefinition
    }

    /// Normalizes metadata and portable or historic targets while retaining authored set membership.
    private static func normalize(_ definition: CustomRoutineDefinition) -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: definition.id,
            title: definition.title.trimmingCharacters(in: .whitespacesAndNewlines),
            subtitle: definition.subtitle.trimmingCharacters(in: .whitespacesAndNewlines),
            difficulty: normalizedOptional(definition.difficulty),
            category: normalizedOptional(definition.category),
            tags: normalizedTags(definition.tags),
            targetMode: definition.targetMode,
            steps: definition.steps.map {
                let step = $0.strippingUnsupportedCustomCueFields()
                if case let .boardSpecific(boardID) = definition.targetMode,
                   boardID == "plateau.lifting-edge" {
                    return migratingLegacyPlateauTargets(in: step)
                }
                return definition.targetMode.isBoardSpecific ? step : step.strippingExactContactIDs()
            },
            sets: definition.sets
        )
    }

    /// The pre-native Plateau package represented its 10/15 mm configurations
    /// as separate blocker contacts. Persisted exact selections must now retain
    /// those depths on the one physical edge, rather than select its default 18 mm.
    private static func migratingLegacyPlateauTargets(
        in step: WorkoutStepDefinition
    ) -> WorkoutStepDefinition {
        guard step.phase != .rest, step.handUse != .double else { return step }
        let segments = step.segments.map { segment in
            guard segment.kind == .work,
                  case let .requirements(requirements) = segment.target else { return segment }
            return WorkoutSegmentDefinition(
                kind: segment.kind,
                target: .requirements(requirements.map(migratingLegacyPlateauRequirement)),
                timing: segment.timing,
                duration: segment.duration
            )
        }
        guard segments != step.segments else { return step }
        return WorkoutStepDefinition(
            id: step.id,
            title: step.title,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            segments: segments,
            gripType: step.gripType,
            fingerConfiguration: step.fingerConfiguration,
            activeDuration: step.activeDuration,
            handUse: step.handUse,
            side: step.side,
            action: step.action,
            repetitions: step.repetitions,
            externalLoadKGF: step.externalLoadKGF
        )
    }

    private static func migratingLegacyPlateauRequirement(
        _ requirement: ContactRequirement
    ) -> ContactRequirement {
        let historicDepth: Double
        switch requirement.contactID {
        case "blocker-edge-10": historicDepth = 10
        case "blocker-edge-15": historicDepth = 15
        default: return requirement
        }
        // Main's contacts were one-hand edges without shape/finger-capacity
        // facts. Do not reinterpret an incompatible or unknown prescription.
        guard requirement.kind == nil || requirement.kind == .edge,
              requirement.shape == nil,
              requirement.fingerCapacity == nil,
              requirement.handCapacity == nil || requirement.handCapacity == 1,
              requirement.selection == .single else { return requirement }
        if let depth = requirement.depth {
            switch depth {
            case let .range(range):
                guard historicDepth >= range.minimum,
                      historicDepth <= range.maximum else { return requirement }
            case let .category(size):
                guard size.depthRange.contains(historicDepth) else { return requirement }
            }
        }
        return ContactRequirement(
            contactID: "edge-18",
            kind: requirement.kind,
            shape: requirement.shape,
            depth: .range(.init(minimum: historicDepth, maximum: historicDepth)),
            fingerCapacity: requirement.fingerCapacity,
            handCapacity: requirement.handCapacity,
            selection: requirement.selection
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
