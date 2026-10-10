import Foundation

struct PlanHoldSubstitutionOption: Identifiable, Hashable {
    let id: String
    let label: String
    let target: WorkoutSegmentTarget
}

struct PlanHoldSubstitutionRequest: Identifiable, Hashable {
    struct ID: Hashable {
        let planID: String
        let boardID: String
        let revisionID: String
        let target: WorkoutSegmentTarget
        let gripType: GripType?
        let fingerConfiguration: FingerConfiguration?
        let handUse: WorkoutHandUse
        let side: WorkoutSide
    }

    let id: ID
    let requiredHoldLabel: String
    var stepTitles: [String]
    let options: [PlanHoldSubstitutionOption]
}

enum PlanHoldSubstitutions {
    /// Retains resolved choices with the complete prescription and board that
    /// produced them. Only `prepare` can create a snapshot; matching IDs alone
    /// do not authorize reusing choices after either value changes.
    struct PreparedRequests: Hashable {
        fileprivate let plan: TrainingPlan
        fileprivate let board: BoardRevision
        let requests: [PlanHoldSubstitutionRequest]

        fileprivate init(plan: TrainingPlan, board: BoardRevision, requests: [PlanHoldSubstitutionRequest]) {
            self.plan = plan
            self.board = board
            self.requests = requests
        }
    }

    /// Resolve once when the prescription or board changes, then retain this
    /// snapshot while the athlete makes explicit substitution choices.
    static func prepare(for plan: TrainingPlan, on board: BoardRevision) -> PreparedRequests {
        PreparedRequests(plan: plan, board: board, requests: requests(for: plan, on: board))
    }

    /// Groups identical missing simultaneous tasks and resolves their available
    /// alternatives. Supported tasks do not request a substitution.
    static func requests(for plan: TrainingPlan, on board: BoardRevision) -> [PlanHoldSubstitutionRequest] {
        var requests: [PlanHoldSubstitutionRequest] = []
        var indices: [PlanHoldSubstitutionRequest.ID: Int] = [:]
        for step in plan.steps {
            for segment in step.segments where segment.kind == .work {
                guard let target = segment.target else { continue }
                for unit in units(in: target) where resolution(of: unit, step: step, board: board) == nil {
                    let id = requestID(for: unit, step: step, plan: plan, board: board)
                    if let index = indices[id] {
                        if !requests[index].stepTitles.contains(step.title) {
                            requests[index].stepTitles.append(step.title)
                        }
                    } else {
                        indices[id] = requests.count
                        requests.append(PlanHoldSubstitutionRequest(id: id,
                            requiredHoldLabel: requestLabel(for: unit, step: step), stepTitles: [step.title],
                            options: options(for: unit, step: step, board: board)))
                    }
                }
            }
        }
        return requests
    }

    /// Returns a session copy only when every missing task has a valid explicit
    /// choice. A supplied snapshot avoids resolving alternatives again and is
    /// rejected if the complete prescription or board differs from its context.
    /// Omitting it prepares current requests for callers that do not retain one.
    static func applying(_ selections: [PlanHoldSubstitutionRequest.ID: PlanHoldSubstitutionOption.ID],
                         to plan: TrainingPlan, on board: BoardRevision,
                         prepared: PreparedRequests? = nil) -> TrainingPlan? {
        let prepared = prepared ?? prepare(for: plan, on: board)
        guard prepared.plan == plan, prepared.board == board else { return nil }
        let requests = prepared.requests
        let requestIDs = Set(requests.map(\.id))
        guard selections.keys.allSatisfy(requestIDs.contains) else { return nil }
        guard !requests.isEmpty else { return plan }
        var chosen: [PlanHoldSubstitutionRequest.ID: PlanHoldSubstitutionOption] = [:]
        for request in requests {
            guard let optionID = selections[request.id],
                  let option = request.options.first(where: { $0.id == optionID }) else { return nil }
            chosen[request.id] = option
        }
        let steps = plan.steps.map { step in
            var notices: [String] = []
            let segments = step.segments.map { segment -> WorkoutSegment in
                guard segment.kind == .work, let target = segment.target else { return segment }
                let replacement: WorkoutSegmentTarget
                switch target {
                case .selfSelected:
                    return segment
                case .tasks(let tasks):
                    replacement = .tasks(tasks.map { task in
                        let unit = WorkoutSegmentTarget.tasks([task])
                        let id = requestID(for: unit, step: step, plan: plan, board: board)
                        guard let option = chosen[id], case .tasks(let alternatives) = option.target,
                              let substitute = alternatives.first else { return task }
                        let notice = "Session substitution: \(label(for: unit)) → \(option.label)."
                        if !notices.contains(notice) { notices.append(notice) }
                        return substitute
                    })
                case .requirements:
                    let id = requestID(for: target, step: step, plan: plan, board: board)
                    guard let option = chosen[id] else { return segment }
                    replacement = option.target
                    let notice = "Session substitution: \(label(for: target)) → \(option.label)."
                    if !notices.contains(notice) { notices.append(notice) }
                }
                return WorkoutSegment(kind: segment.kind, target: replacement,
                    timing: segment.timing, duration: segment.duration)
            }
            guard !notices.isEmpty else { return step }
            return replacing(step, segments: segments,
                instruction: notices.joined(separator: "\n") + "\nOriginal plan instruction: " + step.instruction)
        }
        var result = TrainingPlan(id: plan.id, title: plan.title, subtitle: plan.subtitle,
            level: plan.level, sourceLabel: plan.sourceLabel, sourceURL: plan.sourceURL,
            provenance: plan.provenance == .custom ? .custom : .adapted, boardID: board.id, steps: steps)
        result.stepRepeats = plan.stepRepeats
        result.isFreeWorkout = plan.isFreeWorkout
        return result
    }

    private static func requestID(for target: WorkoutSegmentTarget, step: WorkoutStep,
                                  plan: TrainingPlan, board: BoardRevision) -> PlanHoldSubstitutionRequest.ID {
        .init(planID: plan.id, boardID: board.id, revisionID: board.revisionID,
              target: target, gripType: step.gripType, fingerConfiguration: step.fingerConfiguration,
              handUse: step.handUse, side: step.side)
    }

    /// Successive tasks remain separate; an athlete chooses once for identical
    /// missing simultaneous tasks repeated throughout the source plan.
    private static func units(in target: WorkoutSegmentTarget) -> [WorkoutSegmentTarget] {
        switch target {
        case .selfSelected: []
        case .requirements: [target]
        case .tasks(let tasks): tasks.map { .tasks([$0]) }
        }
    }

    private struct Resolution {
        let contacts: [PhysicalContact]
        let positionIDs: [String]
    }

    /// Follow the same start-of-session hand alternatives used by AppStore.
    /// A bilateral legacy requirement on a one-hand board is resolved after
    /// materialization, so it does not incorrectly require a physical pair.
    private static func resolution(of target: WorkoutSegmentTarget, step: WorkoutStep,
                                   board: BoardRevision) -> Resolution? {
        if case .tasks(let tasks) = target {
            let selections = tasks.compactMap { try? ContactResolver.resolveSelection($0, step: step, board: board) }
            guard selections.count == tasks.count else { return nil }
            return Resolution(contacts: selections.flatMap(\.contacts),
                positionIDs: selections.compactMap(\.positionID))
        }
        guard case .requirements = target else { return Resolution(contacts: [], positionIDs: []) }
        let candidate = replacing(step, segments: [WorkoutSegment(kind: .work, target: target,
            timing: .fixed, duration: step.activeDuration)])
        func resolve(_ materialized: WorkoutStep) -> Resolution? {
            guard let selection = try? ContactResolver.resolveSelection(materialized.workRequirements,
                step: materialized, board: board), !selection.contacts.isEmpty else { return nil }
            return Resolution(contacts: selection.contacts, positionIDs: selection.positionID.map { [$0] } ?? [])
        }
        guard WorkoutSessionHandResolver.stepNeedsHandResolution(candidate, boardIsOneHanded: board.isOneHanded) else {
            return resolve(candidate)
        }
        if let both = resolve(WorkoutSessionHandResolver.materialized(candidate, preference: .both,
            boardIsOneHanded: board.isOneHanded)) { return both }
        guard let left = resolve(WorkoutSessionHandResolver.materialized(candidate, preference: .left,
                  boardIsOneHanded: board.isOneHanded)),
              let right = resolve(WorkoutSessionHandResolver.materialized(candidate, preference: .right,
                  boardIsOneHanded: board.isOneHanded)) else { return nil }
        return Resolution(contacts: left.contacts + right.contacts, positionIDs: left.positionIDs + right.positionIDs)
    }

    private static func options(for target: WorkoutSegmentTarget, step: WorkoutStep,
                                board: BoardRevision) -> [PlanHoldSubstitutionOption] {
        // Include the factual effective depths of authored positions, rather
        // than deriving a training prescription from their visual geometry.
        let contacts = board.contacts + board.positions.flatMap { board.contacts(inPosition: $0.id) }
        var alternatives: [WorkoutSegmentTarget] = []
        switch target {
        case .selfSelected:
            return []
        case .tasks(let tasks):
            guard let task = tasks.first else { return [] }
            if task.count == 2, task[0].target == task[1].target, let predicate = task[0].target {
                // A source-prescribed matching pair remains a matching pair.
                // Do not offer a cross product of different edge depths.
                let minimum = max(predicate.fingerCapacity ?? 0, step.fingerConfiguration?.count ?? 0)
                let predicates = unique(contacts.filter { hasRoom($0, for: minimum) }.map(factualPredicate))
                alternatives = predicates.map { predicate in
                    .tasks([task.map { PlanHandTarget(target: predicate, side: $0.side) }])
                }
            } else {
                let choices = task.map { hand -> [PlanHandTarget] in
                    guard let predicate = hand.target else { return [hand] }
                    let minimum = max(predicate.fingerCapacity ?? 0, step.fingerConfiguration?.count ?? 0)
                    return unique([hand] + contacts.filter { hasRoom($0, for: minimum) }.map {
                        PlanHandTarget(target: factualPredicate(for: $0), side: hand.side)
                    })
                }
                alternatives = combinations(choices).map { .tasks([$0]) }
            }
        case .requirements(let requirements):
            let choices = requirements.map { required -> [ContactRequirement] in
                let minimum = max(required.fingerCapacity ?? 0, step.fingerConfiguration?.count ?? 0)
                let candidates = contacts.filter { hasRoom($0, for: minimum) }.map { contact in
                    ContactRequirement(kind: contact.kind, shape: contact.shape, depth: contact.depth,
                        fingerCapacity: contact.fingerCapacity, handCapacity: required.handCapacity,
                        selection: required.selection)
                }
                // Keep already-resolving legacy requirements within this
                // ordered target instead of changing unrelated holds.
                if resolution(of: .requirements([required]), step: step, board: board) != nil {
                    return [required]
                }
                return unique(candidates)
            }
            alternatives = combinations(choices).map { .requirements($0) }
        }
        var options: [PlanHoldSubstitutionOption] = []
        var seen: Set<String> = []
        var mostUnchangedHands = -1
        for alternative in alternatives {
            guard let resolved = resolution(of: alternative, step: step, board: board),
                  !resolved.contacts.isEmpty,
                  preservesFingerRoom(of: target, alternative: alternative, resolved: resolved,
                    step: step, board: board) else { continue }
            let unchangedHands = unchangedHandCount(in: alternative, from: target)
            guard unchangedHands >= mostUnchangedHands else { continue }
            if unchangedHands > mostUnchangedHands {
                mostUnchangedHands = unchangedHands
                options.removeAll()
                seen.removeAll()
            }
            let components = unique(resolved.positionIDs).sorted() + ["contacts"] + unique(resolved.contacts.map(\.id)).sorted()
            let id = components.map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
            guard seen.insert(id).inserted else { continue }
            let hasEffectiveDepth = resolved.positionIDs.contains {
                !(board.position(id: $0)?.effectiveDepths.isEmpty ?? true)
            }
            let names = unique(resolved.contacts.map { contact in
                guard hasEffectiveDepth, let depth = contact.depth else { return contact.name }
                return "\(contact.name) (\(label(for: ContactRequirement(depth: depth), includingMeasuredRanges: true)))"
            }).joined(separator: ", ")
            options.append(PlanHoldSubstitutionOption(id: id, label: names, target: alternative))
        }
        return options.sorted { $0.label == $1.label ? $0.id < $1.id : $0.label.localizedStandardCompare($1.label) == .orderedAscending }
    }

    private static func unchangedHandCount(in alternative: WorkoutSegmentTarget, from original: WorkoutSegmentTarget) -> Int {
        guard case .tasks(let originalTasks) = original, case .tasks(let selectedTasks) = alternative,
              let source = originalTasks.first, let selected = selectedTasks.first else { return 0 }
        return zip(source, selected).filter { pair in pair.0 == pair.1 }.count
    }

    private static func preservesFingerRoom(of original: WorkoutSegmentTarget, alternative: WorkoutSegmentTarget,
                                            resolved: Resolution, step: WorkoutStep, board: BoardRevision) -> Bool {
        let stepCount = step.fingerConfiguration?.count ?? 0
        guard resolved.contacts.allSatisfy({ hasRoom($0, for: stepCount) }) else { return false }
        switch (original, alternative) {
        case (.tasks(let tasks), .tasks(let alternatives)):
            guard let task = tasks.first, let selected = alternatives.first,
                  task.count == resolved.contacts.count, selected.count == task.count else { return false }
            if task.count == 2, task[0].target == task[1].target {
                let first = resolved.contacts[0], second = resolved.contacts[1]
                guard first.kind == second.kind, first.shape == second.shape, first.depth == second.depth else { return false }
            }
            return task.indices.allSatisfy { index in
                let hand = task[index], contact = resolved.contacts[index]
                guard hasRoom(contact, for: max(hand.target?.fingerCapacity ?? 0, stepCount)) else { return false }
                guard selected[index] != hand, let predicate = selected[index].target else { return true }
                return matchesFactualFields(predicate, contact: contact)
            }
        case (.requirements(let source), .requirements(let selected)):
            guard source.count == selected.count else { return false }
            return zip(source, selected).allSatisfy { originalRequirement, selectedRequirement in
                guard let selection = resolution(of: .requirements([selectedRequirement]), step: step, board: board) else { return false }
                return selection.contacts.allSatisfy {
                    hasRoom($0, for: max(originalRequirement.fingerCapacity ?? 0, stepCount))
                        && (originalRequirement == selectedRequirement || (
                            selectedRequirement.kind == $0.kind && selectedRequirement.shape == $0.shape
                                && selectedRequirement.depth == $0.depth))
                }
            }
        default:
            return false
        }
    }

    /// Prescription resolution may tolerate nearby measured depths. A generated
    /// substitute must describe the resolved contact's exact facts so its label
    /// and recorded target cannot claim the neighboring candidate's depth.
    private static func matchesFactualFields(_ predicate: PlanContactPredicate, contact: PhysicalContact) -> Bool {
        let factual = factualPredicate(for: contact)
        return predicate.kind == factual.kind && predicate.shape == factual.shape && predicate.depth == factual.depth
    }

    private static func hasRoom(_ contact: PhysicalContact, for count: Int) -> Bool {
        guard count > 0, let capacity = contact.fingerCapacity else { return true }
        return capacity >= count
    }

    private static func factualPredicate(for contact: PhysicalContact) -> PlanContactPredicate {
        let depth: PlanDepth? = contact.depth.map {
            switch $0 {
            case .category(let size): .category(size)
            case .range(let range): .measured(range)
            }
        }
        return PlanContactPredicate(kind: contact.kind, shape: contact.shape,
            depth: depth, fingerCapacity: contact.fingerCapacity)
    }

    private static func unique<T: Hashable>(_ values: [T]) -> [T] {
        var seen: Set<T> = []
        return values.filter { seen.insert($0).inserted }
    }

    private static func combinations<T>(_ choices: [[T]]) -> [[T]] {
        choices.reduce([[]]) { prefixes, values in
            prefixes.flatMap { prefix in values.map { prefix + [$0] } }
        }
    }

    private static func label(for target: WorkoutSegmentTarget) -> String {
        switch target {
        case .selfSelected: "Athlete-selected hold"
        case .requirements(let requirements): requirements.map { label(for: $0) }.joined(separator: " + ")
        case .tasks(let tasks): tasks.map { task in
            let descriptions = task.map { hand in
                hand.target.map { label(for: $0.legacyRequirement) } ?? "Athlete-selected hold"
            }
            if Set(descriptions).count == 1, let first = descriptions.first {
                return first + (task.count == 2 ? " (2 hands)" : " (1 hand)")
            }
            return descriptions.joined(separator: " + ")
        }.joined(separator: "; ")
        }
    }

    private static func requestLabel(for target: WorkoutSegmentTarget, step: WorkoutStep) -> String {
        var parts = [label(for: target)]
        if let grip = step.gripType { parts.append(grip.label) }
        if let fingers = step.fingerConfiguration {
            if fingers.hasExactFingers {
                parts.append(fingers.orderedFingers.map { $0.rawValue.capitalized }.joined(separator: ", "))
            } else {
                parts.append("\(fingers.count) fingers")
            }
        }
        return parts.joined(separator: " · ")
    }

    private static func label(for requirement: ContactRequirement, includingMeasuredRanges: Bool = false) -> String {
        var parts: [String] = []
        if let depth = requirement.depth {
            switch depth {
            case .category(let size): parts.append(size.label)
            case .range(let range):
                // Some catalog bands compensate for numeric match tolerance
                // or an audited size inference. They are resolution inputs,
                // not source-prescribed ranges. Retain those ranges in the
                // original instruction rather than presenting the internal band.
                if range.minimum == range.maximum {
                    parts.append("\(number(range.minimum)) mm")
                } else if includingMeasuredRanges {
                    parts.append("\(number(range.minimum))–\(number(range.maximum)) mm")
                }
            }
        }
        if let shape = requirement.shape { parts.append(shape.label) }
        if let kind = requirement.kind { parts.append(kind.detailLabel) }
        if let fingers = requirement.fingerCapacity { parts.append("\(fingers) fingers") }
        return parts.isEmpty ? requirement.contactID ?? "Required hold" : parts.joined(separator: " · ")
    }

    private static func number(_ value: Double) -> String {
        value.formatted(.number.precision(.fractionLength(0...2)))
    }

    private static func replacing(_ step: WorkoutStep, segments: [WorkoutSegment], instruction: String? = nil) -> WorkoutStep {
        WorkoutStep(id: step.id, number: step.number, title: step.title,
            instruction: instruction ?? step.instruction, accessory: step.accessory,
            duration: step.duration, phase: step.phase, segments: segments,
            gripType: step.gripType, fingerConfiguration: step.fingerConfiguration,
            handUse: step.handUse, side: step.side, action: step.action,
            repetitions: step.repetitions, externalLoadKGF: step.externalLoadKGF,
            timedWorkDuration: step.timedWorkDuration)
    }
}
