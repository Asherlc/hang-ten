import Foundation

struct CustomRoutineStepDraft: Equatable, Identifiable {
    let id: String
    var title: String
    var instruction: String
    var accessory: String
    var duration: TimeInterval
    var phase: WorkoutPhase
    var targets: [WorkoutTargetDefinition]
    var timing: WorkoutSegmentTiming
    var gripType: GripType?
    let activeDuration: TimeInterval?

    init(
        id: String,
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [WorkoutTargetDefinition],
        timing: WorkoutSegmentTiming,
        gripType: GripType?,
        activeDuration: TimeInterval? = nil
    ) {
        self.id = id
        self.title = title
        self.instruction = instruction
        self.accessory = accessory
        self.duration = duration
        self.phase = phase
        self.targets = targets
        self.timing = timing
        self.gripType = gripType
        self.activeDuration = activeDuration
    }

    var isRest: Bool {
        phase == .rest
    }

    var isStopwatch: Bool {
        timing == .stopwatch
    }
}

struct CustomRoutineDraft: Equatable {
    let id: String?
    private let generatedID: String
    let targetMode: CustomRoutineTargetMode
    var title: String
    var subtitle: String
    var difficulty: String?
    var category: String?
    var tagsText: String
    var steps: [CustomRoutineStepDraft]

    init(createWith targetMode: CustomRoutineTargetMode) {
        self.init(
            createWith: targetMode,
            generatedID: "custom.\(UUID().uuidString)"
        )
    }

    private init(createWith targetMode: CustomRoutineTargetMode, generatedID: String) {
        id = nil
        self.generatedID = generatedID
        self.targetMode = targetMode
        title = ""
        subtitle = ""
        difficulty = nil
        category = nil
        tagsText = ""
        steps = []
    }

    init(duplicate definition: CustomRoutineDefinition) {
        self.init(
            definition: definition,
            id: nil,
            generatedID: "custom.\(UUID().uuidString)"
        )
    }

    init(editing definition: CustomRoutineDefinition) {
        self.init(
            definition: definition,
            id: definition.id,
            generatedID: definition.id
        )
    }

    private init(
        definition: CustomRoutineDefinition,
        id: String?,
        generatedID: String
    ) {
        self.id = id
        self.generatedID = generatedID
        targetMode = definition.targetMode
        title = definition.title
        subtitle = definition.subtitle
        difficulty = definition.difficulty
        category = definition.category
        tagsText = definition.tags.joined(separator: ", ")
        steps = definition.steps.map(Self.stepDraft(from:))
    }

    mutating func addStep() {
        steps.append(
            CustomRoutineStepDraft(
                id: UUID().uuidString,
                title: "New step",
                instruction: "",
                accessory: "",
                duration: 10,
                phase: .hang,
                targets: [],
                timing: .fixed,
                gripType: nil
            )
        )
    }

    mutating func updateStep(_ step: CustomRoutineStepDraft) {
        guard let index = steps.firstIndex(where: { $0.id == step.id }) else {
            return
        }
        steps[index] = step
    }

    mutating func removeSteps(at offsets: IndexSet) {
        for index in offsets.sorted(by: >) where steps.indices.contains(index) {
            steps.remove(at: index)
        }
    }

    mutating func moveSteps(from offsets: IndexSet, to destination: Int) {
        let sourceOffsets = offsets.filter { steps.indices.contains($0) }.sorted()
        guard !sourceOffsets.isEmpty else {
            return
        }

        let movingSteps = sourceOffsets.map { steps[$0] }
        for index in sourceOffsets.reversed() {
            steps.remove(at: index)
        }

        let boundedDestination = min(max(destination, 0), steps.count + sourceOffsets.count)
        let removedBeforeDestination = sourceOffsets.filter { $0 < boundedDestination }.count
        let insertionIndex = min(
            max(boundedDestination - removedBeforeDestination, 0),
            steps.count
        )
        steps.insert(contentsOf: movingSteps, at: insertionIndex)
    }

    func retargeted(
        to targetMode: CustomRoutineTargetMode,
        availableBoards: [TrainingBoard] = BoardCatalog.all
    ) -> CustomRoutineDraft {
        guard id == nil, targetMode != self.targetMode else {
            return self
        }

        var retargeted = CustomRoutineDraft(
            createWith: targetMode,
            generatedID: generatedID
        )
        retargeted.title = title
        retargeted.subtitle = subtitle
        retargeted.difficulty = difficulty
        retargeted.category = category
        retargeted.tagsText = tagsText
        retargeted.steps = steps.map { step in
            var step = step
            step.targets = Self.compatibleTargets(
                step.targets,
                for: targetMode,
                availableBoards: availableBoards
            )
            return step
        }
        return retargeted
    }

    func definition() -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: id ?? generatedID,
            title: title.trimmingCharacters(in: .whitespacesAndNewlines),
            subtitle: subtitle.trimmingCharacters(in: .whitespacesAndNewlines),
            difficulty: normalizedOptional(difficulty),
            category: normalizedOptional(category),
            tags: CustomRoutineTagNormalizer.normalizedTags(from: tagsText),
            targetMode: targetMode,
            steps: steps.map(Self.stepDefinition(from:))
        )
    }

    private static func stepDraft(from definition: WorkoutStepDefinition) -> CustomRoutineStepDraft {
        CustomRoutineStepDraft(
            id: definition.id,
            title: definition.title,
            instruction: definition.instruction,
            accessory: definition.accessory,
            duration: definition.duration,
            phase: definition.phase,
            targets: definition.targets,
            timing: definition.segments.first?.timing ?? .fixed,
            gripType: definition.gripType,
            activeDuration: definition.activeDuration
        )
    }

    private static func stepDefinition(from step: CustomRoutineStepDraft) -> WorkoutStepDefinition {
        let timing: WorkoutSegmentTiming = step.isRest ? .fixed : step.timing
        let targets = step.isRest ? [] : step.targets
        let segmentDuration: TimeInterval? = timing == .fixed ? step.duration : nil
        let segment = WorkoutSegmentDefinition(
            kind: step.isRest ? .rest : .work,
            targets: targets,
            timing: timing,
            duration: segmentDuration
        )
        return WorkoutStepDefinition(
            id: step.id,
            title: step.title,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            targets: targets,
            segments: [segment],
            gripType: step.isRest ? nil : step.gripType,
            activeDuration: step.activeDuration
        )
    }

    private static func compatibleTargets(
        _ targets: [WorkoutTargetDefinition],
        for targetMode: CustomRoutineTargetMode,
        availableBoards: [TrainingBoard]
    ) -> [WorkoutTargetDefinition] {
        switch targetMode {
        case let .boardSpecific(boardID):
            guard let board = availableBoards.first(where: { $0.id == boardID }) else {
                return []
            }
            let knownHoldIDs = Set(board.holds.map(\.id))
            return targets.compactMap { target in
                guard case let .holdIDs(holdIDs) = target else { return nil }
                let compatibleIDs = holdIDs.filter(knownHoldIDs.contains)
                return compatibleIDs.isEmpty ? nil : .holdIDs(compatibleIDs)
            }
        case .generic:
            return targets.filter { target in
                switch target {
                case .kind, .feature:
                    true
                default:
                    false
                }
            }
        }
    }

    private func normalizedOptional(_ value: String?) -> String? {
        guard let value else {
            return nil
        }
        let normalized = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized.isEmpty ? nil : normalized
    }

}

enum CustomRoutineTagNormalizer {
    static func normalizedTags(from text: String) -> [String] {
        normalizedTags(from: [text])
    }

    static func normalizedTags(from tags: [String]) -> [String] {
        var seen = Set<String>()
        return tags
            .flatMap { $0.split(separator: ",", omittingEmptySubsequences: false).map(String.init) }
            .compactMap { tag in
                let normalized = tag.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !normalized.isEmpty, seen.insert(normalized.lowercased()).inserted else {
                    return nil
                }
                return normalized
            }
    }
}

struct CustomRoutineMetadataOptions: Equatable {
    static let defaultMetadata = PlanCatalog.all.compactMap { PlanCatalog.metadata(for: $0.id) }

    let difficulties: [String]
    let categories: [String]

    init(metadata: [PlanMetadata] = CustomRoutineMetadataOptions.defaultMetadata) {
        difficulties = Self.sortedUnique(metadata.map(\.level) + ["Custom"])
        categories = Self.sortedUnique(metadata.map(\.category) + ["custom"])
    }

    private static func sortedUnique(_ values: [String]) -> [String] {
        Array(Set(values)).sorted { lhs, rhs in
            let comparison = lhs.localizedCaseInsensitiveCompare(rhs)
            if comparison == .orderedSame {
                return lhs < rhs
            }
            return comparison == .orderedAscending
        }
    }
}
