import Foundation

struct CustomRoutineStepDraft: Equatable, Identifiable {
    var id: String
    var title: String
    var instruction: String
    var accessory: String
    var duration: TimeInterval
    var phase: WorkoutPhase
    var targets: [ContactRequirement]
    var timing: WorkoutSegmentTiming
    let activeDuration: TimeInterval?
    var handUse: WorkoutHandUse
    var side: WorkoutSide
    var action: WorkoutAction
    var repetitions: Int?
    var externalLoadKGF: Double?

    /// One exercise control writes both underlying playback classifications.
    var exercise: CustomRoutineExercise {
        get {
            if isRest { return .rest }
            switch action {
            case .hang: return .hang
            case .isometricPull: return .isometricPull
            case .loadedLift: return .loadedLift
            }
        }
        set {
            let wasRest = isRest
            let usesExerciseName = title == exercise.label
            switch newValue {
            case .rest:
                phase = .rest
                targets = []
                timing = .fixed
                handUse = .double
                side = .both
                action = .hang
                repetitions = nil
                externalLoadKGF = nil
            case .hang, .isometricPull, .loadedLift:
                action = switch newValue {
                case .hang, .rest: .hang
                case .isometricPull: .isometricPull
                case .loadedLift: .loadedLift
                }
                if wasRest || phase == .hang || phase == .pull {
                    phase = newValue == .hang ? .hang : .pull
                }
                repetitions = newValue == .loadedLift ? max(repetitions ?? 1, 1) : nil
                if (phase == .pull || action == .isometricPull) && handUse == .either {
                    transitionHandUse(to: .double)
                }
            }
            // Canonical names continue to follow the exercise after saving and reopening.
            if usesExerciseName { title = newValue.label }
        }
    }

    var displayTitle: String {
        let name = title.trimmingCharacters(in: .whitespacesAndNewlines)
        return name.isEmpty ? exercise.label : name
    }

    /// A single choice keeps hand use, side and hold selection policy consistent.
    var handChoice: CustomRoutineHandChoice {
        get {
            switch handUse {
            case .double: .both
            case .either: .either
            case .single: side == .right ? .right : .left
            }
        }
        set {
            let use: WorkoutHandUse = switch newValue {
            case .both: .double
            case .either: .either
            case .left, .right: .single
            }
            if use != handUse { transitionHandUse(to: use) }
            side = newValue == .left ? .left : newValue == .right ? .right : .both
        }
    }

    mutating func transitionHandUse(to handUse: WorkoutHandUse) {
        self.handUse = handUse
        side = handUse == .single ? .left : .both

        let selection: ContactSelectionPolicy = handUse == .double ? .bilateralPair : .single
        targets = targets.map { target in
            ContactRequirement(
                contactID: handUse == .single ? target.contactID : nil,
                kind: target.kind,
                shape: target.shape,
                depth: target.depth,
                fingerCapacity: target.fingerCapacity,
                handCapacity: target.handCapacity,
                selection: selection
            )
        }
    }

    init(
        id: String,
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [ContactRequirement],
        timing: WorkoutSegmentTiming,
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
        self.timing = timing
        self.activeDuration = activeDuration
        self.handUse = handUse
        self.side = side
        self.action = action
        self.repetitions = repetitions
        self.externalLoadKGF = externalLoadKGF
    }

    var isRest: Bool {
        phase == .rest
    }

    var isStopwatch: Bool {
        timing == .stopwatch
    }
}

/// Resolves the editor preview through a valid athlete-hand alternative. An
/// either-hand definition deliberately retains `.both` until a session starts,
/// which is not a contact-resolver input for a single-contact requirement.
/// Both-hands preview also includes the capacity-aware materialization (paired
/// holds on two-hand boards, one hold on one-hand boards).
enum CustomRoutineBoardPreview {
    static func presentationID(for step: CustomRoutineStepDraft, on board: BoardRevision) -> String? {
        guard !step.targets.isEmpty else { return nil }
        for resolved in resolvedSteps(for: step, boardIsOneHanded: board.isOneHanded) {
            if let selection = try? ContactResolver.resolveSelection(resolved.workRequirements, step: resolved, board: board),
               let position = board.position(id: selection.positionID) {
                return position.presentationID
            }
        }
        return nil
    }

    static func contactIDs(
        for step: CustomRoutineStepDraft,
        on board: BoardRevision
    ) -> Set<String> {
        guard !step.targets.isEmpty else {
            return []
        }
        let resolvedSteps = resolvedSteps(for: step, boardIsOneHanded: board.isOneHanded)
        return Set(resolvedSteps.flatMap {
            (try? ContactResolver.resolve($0.workRequirements, step: $0, board: board).map(\.id)) ?? []
        })
    }

    static func toggle(
        _ hold: PhysicalContact,
        in step: inout CustomRoutineStepDraft,
        on board: BoardRevision
    ) {
        let selected = contactIDs(for: step, on: board).contains(hold.id)
        let configured = board.positions.contains { !$0.effectiveDepths.isEmpty }
        let selectedDepth = resolvedSteps(for: step, boardIsOneHanded: board.isOneHanded).lazy.compactMap { resolved in
            let selection = try? ContactResolver.resolveSelection(
                resolved.workRequirements, step: resolved, board: board)
            return selection?.contacts.first { $0.id == hold.id }?.depth
        }.first
        if selected && (!configured || selectedDepth == hold.depth) {
            step.targets = []
            return
        }
        step.targets = [requirement(for: hold, handUse: step.handUse)]
    }

    private static func resolvedSteps(for draft: CustomRoutineStepDraft, boardIsOneHanded: Bool) -> [WorkoutStep] {
        let workTarget: WorkoutSegmentTarget = draft.targets.isEmpty
            ? .selfSelected
            : .fromLegacyTargets(draft.targets)
        let step = WorkoutStep(
            id: draft.id,
            number: 0,
            title: draft.displayTitle,
            instruction: draft.instruction,
            accessory: draft.accessory,
            duration: draft.duration,
            phase: draft.phase,
            segments: draft.phase == .rest
                ? [WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: draft.duration)]
                : [WorkoutSegment(kind: .work, target: workTarget, timing: draft.timing, duration: draft.timing == .fixed ? draft.duration : nil)],
            handUse: draft.handUse,
            side: draft.side,
            action: draft.action,
            repetitions: draft.repetitions,
            externalLoadKGF: draft.externalLoadKGF
        )
        guard WorkoutSessionHandResolver.stepNeedsHandResolution(
            step,
            boardIsOneHanded: boardIsOneHanded
        ) else {
            return [step]
        }
        let leftRight = [WorkoutSide.left, .right].compactMap {
            step.resolvingEitherHand(selectedHandSide: $0, boardIsOneHanded: boardIsOneHanded)
        }
        let both = WorkoutSessionHandResolver.materialized(
            step,
            preference: .both,
            boardIsOneHanded: boardIsOneHanded
        )
        return leftRight + [both]
    }

    private static func requirement(
        for contact: PhysicalContact,
        handUse: WorkoutHandUse
    ) -> ContactRequirement {
        ContactRequirement(
            contactID: handUse == .single ? contact.id : nil,
            kind: contact.kind,
            shape: contact.shape,
            depth: contact.depth,
            fingerCapacity: contact.fingerCapacity,
            handCapacity: contact.handCapacity,
            selection: handUse == .double ? .bilateralPair : .single
        )
    }
}

/// One reorderable editor row, containing an ungrouped step or an entire set.
enum CustomRoutineEditorItem: Equatable, Identifiable {
    case step(CustomRoutineStepDraft)
    case set(CustomRoutineSet, steps: [CustomRoutineStepDraft])

    var id: String {
        switch self {
        case let .step(step): "step.\(step.id)"
        case let .set(set, _): "set.\(set.id)"
        }
    }

    var stepIDs: [String] {
        switch self {
        case let .step(step): [step.id]
        case let .set(_, steps): steps.map(\.id)
        }
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
    var sets: [CustomRoutineSet]

    init(createWith targetMode: CustomRoutineTargetMode) {
        self.init(
            createWith: targetMode,
            generatedID: "custom.\(UUID().uuidString)"
        )
    }

    /// Initializes an empty unsaved draft with one identity retained across later conversions.
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
        sets = []
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

    /// Loads authored rows and their set metadata while choosing persisted or duplicated identity.
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
        sets = definition.sets
    }

    /// Adds to the selected set, defaulting to the last visible set or a new once-only set.
    mutating func addStep(to setID: String? = nil) {
        let destination = setID ?? steps.last.flatMap { last in
            sets.first(where: { $0.stepIDs.contains(last.id) })?.id
        }
        appendSteps([Self.newStep()], to: destination)
    }

    /// Starts a separate once-only set with its first editable step.
    @discardableResult
    mutating func addSet() -> CustomRoutineSet {
        let step = Self.newStep()
        let set = CustomRoutineSet(stepIDs: [step.id], repeatCount: 1)
        steps.append(step)
        sets.append(set)
        return set
    }

    /// Adds one-run sets for unused consecutive ranges in a planner copy, retaining existing repeats.
    func assigningDefaultSets() -> CustomRoutineDraft {
        var grouped = self
        let usedIDs = Set(sets.flatMap(\.stepIDs))
        var index = 0
        while index < steps.count {
            if usedIDs.contains(steps[index].id) {
                index += 1
                continue
            }
            let start = index
            while index < steps.count, !usedIDs.contains(steps[index].id) {
                index += 1
            }
            grouped.sets.append(CustomRoutineSet(
                stepIDs: steps[start..<index].map(\.id),
                repeatCount: 1
            ))
        }
        return grouped
    }

    /// Leaves duration unauthored until the athlete supplies it.
    private static func newStep() -> CustomRoutineStepDraft {
        CustomRoutineStepDraft(
            id: UUID().uuidString,
            title: "",
            instruction: "",
            accessory: "",
            duration: 0,
            phase: .hang,
            targets: [],
            timing: .fixed,
            activeDuration: nil
        )
    }

    /// Inserts at a set's end so subsequent sets remain contiguous; a nil destination starts a new set.
    private mutating func appendSteps(_ additions: [CustomRoutineStepDraft], to setID: String?) {
        if let setID {
            guard let index = sets.firstIndex(where: { $0.id == setID }),
                  let range = sets[index].range(in: steps.map(\.id)) else { return }
            steps.insert(contentsOf: additions, at: range.upperBound)
            sets[index].stepIDs.append(contentsOf: additions.map(\.id))
        } else {
            steps.append(contentsOf: additions)
            sets.append(CustomRoutineSet(stepIDs: additions.map(\.id), repeatCount: 1))
        }
    }

    /// Appends left/right copies to the source set while retaining later sets and mirrored targets.
    mutating func addLeftAndRightPair(
        from step: CustomRoutineStepDraft,
        board: BoardRevision? = nil
    ) {
        var left = step
        left.id = UUID().uuidString
        left.handUse = .single
        left.side = .left
        left.targets = Self.targets(step.targets, mirroredOnto: .left, of: board)

        var right = step
        right.id = UUID().uuidString
        right.handUse = .single
        right.side = .right
        right.targets = Self.targets(step.targets, mirroredOnto: .right, of: board)

        appendSteps([left, right], to: sets.first(where: { $0.stepIDs.contains(step.id) })?.id)
    }

    /// An exact contact belongs to one physical side of the board, so copying it
    /// verbatim would point both generated steps at the same hold. Swap in the
    /// board's paired contact when it exists and sits on the side being
    /// generated; otherwise keep the athlete's target untouched rather than
    /// inventing a pair.
    private static func targets(
        _ targets: [ContactRequirement],
        mirroredOnto side: ContactSide,
        of board: BoardRevision?
    ) -> [ContactRequirement] {
        guard let board else { return targets }
        return targets.map { target in
            guard let contactID = target.contactID,
                  let contact = board.contacts.first(where: { $0.id == contactID }),
                  contact.side != side,
                  let pairedContactID = contact.pairedContactID,
                  let paired = board.contacts.first(where: { $0.id == pairedContactID }),
                  paired.side == side
            else {
                return target
            }
            return ContactRequirement(
                contactID: paired.id,
                kind: target.kind,
                shape: target.shape,
                depth: target.depth,
                fingerCapacity: target.fingerCapacity,
                handCapacity: target.handCapacity,
                selection: target.selection
            )
        }
    }

    mutating func updateStep(_ step: CustomRoutineStepDraft) {
        guard let index = steps.firstIndex(where: { $0.id == step.id }) else {
            return
        }
        steps[index] = step
    }

    /// Every declared set occupies one editor row, including sets with a single step.
    var editorItems: [CustomRoutineEditorItem] {
        let stepIDs = steps.map(\.id)
        var items: [CustomRoutineEditorItem] = []
        var index = 0
        while index < steps.count {
            if let set = sets.first(where: {
                $0.range(in: stepIDs)?.lowerBound == index
            }), let range = set.range(in: stepIDs) {
                items.append(.set(set, steps: Array(steps[range])))
                index = range.upperBound
            } else {
                items.append(.step(steps[index]))
                index += 1
            }
        }
        return items
    }

    /// Deletes every authored member of the selected editor rows and prunes their sets.
    mutating func removeEditorItems(at offsets: IndexSet) {
        let items = editorItems
        let removedIDs = Set(offsets.filter { items.indices.contains($0) }.flatMap { items[$0].stepIDs })
        removeSteps(at: IndexSet(steps.indices.filter { removedIDs.contains(steps[$0].id) }))
    }

    /// Translates editor row offsets into authored step offsets, keeping sets together.
    mutating func moveEditorItems(from offsets: IndexSet, to destination: Int) {
        let items = editorItems
        let movedIDs = Set(offsets.filter { items.indices.contains($0) }.flatMap { items[$0].stepIDs })
        let stepOffsets = IndexSet(steps.indices.filter { movedIDs.contains(steps[$0].id) })
        let boundedDestination = min(max(destination, 0), items.count)
        let stepDestination = items.prefix(boundedDestination).reduce(0) { $0 + $1.stepIDs.count }
        moveSteps(from: stepOffsets, to: stepDestination)
    }

    /// Removes steps from their sets and drops set metadata when no members remain.
    mutating func removeSteps(at offsets: IndexSet) {
        for index in offsets.sorted(by: >) where steps.indices.contains(index) {
            steps.remove(at: index)
        }
        let remainingIDs = Set(steps.map(\.id))
        sets = sets.compactMap { set in
            var set = set
            set.stepIDs.removeAll { !remainingIDs.contains($0) }
            return set.stepIDs.isEmpty ? nil : set
        }
    }

    /// Moves a selected member's complete set and avoids splitting another set at insertion.
    mutating func moveSteps(from offsets: IndexSet, to destination: Int) {
        let stepIDs = steps.map(\.id)
        var movingOffsets = Set(offsets.filter { steps.indices.contains($0) })
        // A set is one sequence: moving any member moves the whole range.
        for set in sets {
            if let range = set.range(in: stepIDs), !movingOffsets.isDisjoint(with: range) {
                movingOffsets.formUnion(range)
            }
        }
        let sourceOffsets = movingOffsets.sorted()
        guard !sourceOffsets.isEmpty else {
            return
        }

        let movingSteps = sourceOffsets.map { steps[$0] }
        for index in sourceOffsets.reversed() {
            steps.remove(at: index)
        }

        var boundedDestination = min(max(destination, 0), stepIDs.count)
        for set in sets {
            if let range = set.range(in: stepIDs),
               boundedDestination > range.lowerBound, boundedDestination < range.upperBound {
                boundedDestination = destination > sourceOffsets[0] ? range.upperBound : range.lowerBound
            }
        }
        let removedBeforeDestination = sourceOffsets.filter { $0 < boundedDestination }.count
        let insertionIndex = min(
            max(boundedDestination - removedBeforeDestination, 0),
            steps.count
        )
        steps.insert(contentsOf: movingSteps, at: insertionIndex)
    }

    /// Proposes the first consecutive pair outside existing sets, without changing the draft.
    func newSet() -> CustomRoutineSet? {
        let usedIDs = Set(sets.flatMap(\.stepIDs))
        for index in steps.indices.dropLast() {
            let pair = steps[index...index + 1].map(\.id)
            if usedIDs.isDisjoint(with: pair) {
                return CustomRoutineSet(stepIDs: pair)
            }
        }
        return nil
    }

    /// Inserts or replaces a valid set; unsupported counts, gaps, and overlaps are ignored.
    mutating func updateSet(_ set: CustomRoutineSet) {
        guard CustomRoutineSet.supportedCounts.contains(set.repeatCount),
              set.range(in: steps.map(\.id)) != nil,
              sets.filter({ $0.id != set.id }).allSatisfy({
                  Set($0.stepIDs).isDisjoint(with: set.stepIDs)
              }) else { return }
        if let index = sets.firstIndex(where: { $0.id == set.id }) {
            sets[index] = set
        } else {
            sets.append(set)
        }
    }

    /// Ungroups the set while retaining all authored steps and their edits.
    mutating func removeSet(id: String) {
        sets.removeAll { $0.id == id }
    }

    /// Retargets only unsaved drafts, preserving their identity and sets while filtering incompatible
    /// targets.
    func retargeted(
        to targetMode: CustomRoutineTargetMode,
        availableBoards: [BoardRevision] = BoardCatalog.all
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
        retargeted.sets = sets
        retargeted.steps = steps.map { step in
            var step = step
            step.targets = Self.compatibleTargets(
                step.targets,
                for: targetMode,
                from: self.targetMode,
                availableBoards: availableBoards
            )
            return step
        }
        return retargeted
    }

    /// Produces normalized editable metadata and literal steps without expanding set repetitions.
    func definition() -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: id ?? generatedID,
            title: title.trimmingCharacters(in: .whitespacesAndNewlines),
            subtitle: subtitle.trimmingCharacters(in: .whitespacesAndNewlines),
            difficulty: normalizedOptional(difficulty),
            category: normalizedOptional(category),
            tags: CustomRoutineTagNormalizer.normalizedTags(from: tagsText),
            targetMode: targetMode,
            steps: steps.map(Self.stepDefinition(from:)),
            sets: sets
        )
    }

    private static func stepDraft(from definition: WorkoutStepDefinition) -> CustomRoutineStepDraft {
        let isRest = definition.phase == .rest
        let workSegment = definition.segments.first(where: { $0.kind == .work })
        let targets = isRest ? [] : (workSegment?.contactRequirements ?? definition.workRequirements)
        return CustomRoutineStepDraft(
            id: definition.id,
            title: definition.title,
            instruction: definition.instruction,
            accessory: definition.accessory,
            duration: definition.duration,
            phase: definition.phase,
            targets: targets,
            timing: definition.segments.first?.timing ?? .fixed,
            activeDuration: definition.activeDuration,
            handUse: isRest ? .double : definition.handUse,
            side: isRest ? .both : definition.side,
            action: isRest ? .hang : definition.action,
            repetitions: isRest ? nil : definition.repetitions,
            externalLoadKGF: isRest ? nil : definition.externalLoadKGF
        )
    }

    private static func stepDefinition(from step: CustomRoutineStepDraft) -> WorkoutStepDefinition {
        let timing: WorkoutSegmentTiming = step.isRest ? .fixed : step.timing
        let handUse: WorkoutHandUse = step.isRest ? .double : step.handUse
        let side: WorkoutSide = step.isRest ? .both : step.side
        let action: WorkoutAction = step.isRest ? .hang : step.action
        let segmentDuration: TimeInterval? = timing == .fixed ? step.duration : nil
        let segmentTarget: WorkoutSegmentTarget? = step.isRest
            ? nil
            : (step.targets.isEmpty ? .selfSelected : .fromLegacyTargets(step.targets))
        let segment = WorkoutSegmentDefinition(
            kind: step.isRest ? .rest : .work,
            target: segmentTarget,
            timing: timing,
            duration: segmentDuration
        )
        return WorkoutStepDefinition(
            id: step.id,
            title: step.displayTitle,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            segments: [segment],
            activeDuration: step.activeDuration,
            handUse: handUse,
            side: side,
            action: action,
            repetitions: step.isRest ? nil : step.repetitions,
            externalLoadKGF: step.isRest ? nil : step.externalLoadKGF
        )
    }

    private static func compatibleTargets(
        _ targets: [ContactRequirement],
        for targetMode: CustomRoutineTargetMode,
        from sourceTargetMode: CustomRoutineTargetMode,
        availableBoards: [BoardRevision]
    ) -> [ContactRequirement] {
        switch targetMode {
        case let .boardSpecific(boardID):
            guard availableBoards.contains(where: { $0.id == boardID }) else {
                return []
            }
            if case let .boardSpecific(sourceBoardID) = sourceTargetMode,
               sourceBoardID != boardID {
                return targets.map { $0.strippingExactContactID() }
            }
            return targets
        case .generic:
            return targets.map { $0.strippingExactContactID() }
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

/// Editor choices; persistence continues to use the existing phase and action fields.
enum CustomRoutineExercise: CaseIterable, Hashable {
    case hang, isometricPull, loadedLift, rest

    var label: String {
        switch self {
        case .hang: "Hang"
        case .isometricPull: "Isometric pull"
        case .loadedLift: "Loaded lift"
        case .rest: "Rest"
        }
    }
}

enum CustomRoutineHandChoice: CaseIterable, Hashable {
    case both, left, right, either

    var label: String {
        switch self {
        case .both: "Both hands"
        case .left: "Left hand"
        case .right: "Right hand"
        case .either: "Choose at start"
        }
    }
}
