import Foundation

struct PlanHoldSubstitutionOption: Identifiable, Hashable {
    let id: String
    let label: String
    let target: WorkoutSegmentTarget
}

struct PlanHoldSubstitutionRequest: Identifiable, Hashable {
    struct ID: Codable, Hashable {
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
    var options: [PlanHoldSubstitutionOption]

    var gripContextLabel: String? {
        var parts: [String] = []
        if let grip = id.gripType { parts.append(grip.label) }
        if let fingers = id.fingerConfiguration {
            parts.append(fingers.hasExactFingers
                ? fingers.orderedFingers.map { $0.rawValue.capitalized }.joined(separator: ", ")
                : "\(fingers.count) fingers")
        }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }
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

    /// Matching single- and two-hand cues share one factual hold choice. Keep
    /// only alternatives usable by every affected hand assignment.
    static func requests(for plan: TrainingPlan, on board: BoardRevision) -> [PlanHoldSubstitutionRequest] {
        var requests: [PlanHoldSubstitutionRequest] = []
        var indices: [PlanHoldSubstitutionRequest.ID: Int] = [:]
        for step in plan.steps {
            for segment in step.segments where segment.kind == .work {
                guard let target = segment.target else { continue }
                for unit in units(in: target) where resolution(of: unit, step: step, board: board) == nil {
                    let id = requestID(for: unit, step: step, plan: plan, board: board)
                    let alternatives = options(for: unit, step: step, board: board,
                        filterPreferences: matchingPredicate(in: unit) == nil).compactMap { option -> PlanHoldSubstitutionOption? in
                        guard matchingPredicate(in: unit) != nil,
                              let replacement = matchingPredicate(in: option.target) else { return option }
                        let encoder = JSONEncoder()
                        encoder.outputFormatting = [.sortedKeys]
                        // Physical left/right contact IDs differ between cues;
                        // the shared choice is the factual replacement predicate.
                        guard let data = try? encoder.encode(replacement) else { return nil }
                        return PlanHoldSubstitutionOption(id: "hold:" + data.base64EncodedString(),
                            label: option.label, target: option.target)
                    }
                    if let index = indices[id] {
                        for option in alternatives {
                            if let existing = requests[index].options.firstIndex(where: { $0.id == option.id }) {
                                if option.label.hasSuffix(" (two boards)") { requests[index].options[existing] = option }
                            } else {
                                requests[index].options.append(option)
                            }
                        }
                        if !requests[index].stepTitles.contains(step.title) {
                            requests[index].stepTitles.append(step.title)
                        }
                    } else {
                        indices[id] = requests.count
                        requests.append(PlanHoldSubstitutionRequest(id: id,
                            requiredHoldLabel: label(for: unit), stepTitles: [step.title],
                            options: alternatives))
                    }
                }
            }
        }
        // Validate the union of candidate predicates against every cue, including
        // originally supported ones. Resolver deduplication on a single side
        // must not discard a predicate needed by the other side.
        var contexts: [PlanHoldSubstitutionRequest.ID: [(WorkoutSegmentTarget, WorkoutStep)]] = [:]
        for step in plan.steps {
            for segment in step.segments where segment.kind == .work {
                guard let target = segment.target else { continue }
                for unit in units(in: target) {
                    let id = requestID(for: unit, step: step, plan: plan, board: board)
                    guard indices[id] != nil else { continue }
                    contexts[id, default: []].append((unit, step))
                }
            }
        }
        // Rank kinds after finding choices shared by every hand assignment.
        // A same-kind hold usable by only one hand cannot hide a shared fallback.
        for index in requests.indices {
            var seen: Set<[ResolutionFingerprint]> = []
            requests[index].options = requests[index].options.filter { option in
                var fingerprint: [ResolutionFingerprint] = []
                for (unit, step) in contexts[requests[index].id] ?? [] {
                    let alternative = replacement(option.target, in: unit)
                    guard let resolved = resolution(of: alternative, step: step, board: board),
                          preservesFingerRoom(of: unit, alternative: alternative, resolved: resolved,
                            step: step, board: board) else { return false }
                    fingerprint.append(.init(positionIDs: resolved.positionIDs, contactIDs: resolved.contacts.map(\.id)))
                }
                return seen.insert(fingerprint).inserted
            }.sorted { $0.label == $1.label ? $0.id < $1.id : $0.label.localizedStandardCompare($1.label) == .orderedAscending }
            guard let kind = matchingPredicate(in: requests[index].id.target)?.kind else { continue }
            let preferred = requests[index].options.filter { matchingPredicate(in: $0.target)?.kind == kind }
            if !preferred.isEmpty { requests[index].options = preferred }
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
                        guard let option = chosen[id], case .tasks(let alternatives) = Self.replacement(option.target, in: unit),
                              let substitute = alternatives.first else { return task }
                        return substitute
                    })
                case .requirements:
                    let id = requestID(for: target, step: step, plan: plan, board: board)
                    guard let option = chosen[id] else { return segment }
                    replacement = option.target
                }
                return WorkoutSegment(kind: segment.kind, target: replacement,
                    timing: segment.timing, duration: segment.duration)
            }
            guard segments != step.segments else { return step }
            return replacing(step, segments: segments)
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
        if let predicate = matchingPredicate(in: target) {
            return .init(planID: plan.id, boardID: board.id, revisionID: board.revisionID,
                target: .tasks([[.init(target: predicate)]]), gripType: step.gripType,
                fingerConfiguration: step.fingerConfiguration, handUse: .double, side: .both)
        }
        return .init(planID: plan.id, boardID: board.id, revisionID: board.revisionID,
              target: target, gripType: step.gripType, fingerConfiguration: step.fingerConfiguration,
              handUse: step.handUse, side: step.side)
    }

    private static func matchingPredicate(in target: WorkoutSegmentTarget) -> PlanContactPredicate? {
        guard case .tasks(let tasks) = target, tasks.count == 1, let task = tasks.first,
              (1...2).contains(task.count), let predicate = task.first?.target,
              task.allSatisfy({ $0.target == predicate }) else { return nil }
        return predicate
    }

    private static func replacement(_ selected: WorkoutSegmentTarget,
                                    in original: WorkoutSegmentTarget) -> WorkoutSegmentTarget {
        guard matchingPredicate(in: original) != nil, let predicate = matchingPredicate(in: selected),
              case .tasks(let tasks) = original else { return selected }
        return .tasks(tasks.map { task in task.map { .init(target: predicate, side: $0.side) } })
    }

    /// Retain ordered task boundaries while grouping matching hold choices.
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

    private struct ResolutionFingerprint: Hashable {
        let positionIDs: [String]
        let contactIDs: [String]
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
                                board: BoardRevision, filterPreferences: Bool = true) -> [PlanHoldSubstitutionOption] {
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
        var hasKindPreservingOption = false
        var mostUnchangedHands = -1
        for alternative in alternatives {
            guard let resolved = resolution(of: alternative, step: step, board: board),
                  !resolved.contacts.isEmpty,
                  preservesFingerRoom(of: target, alternative: alternative, resolved: resolved,
                    step: step, board: board) else { continue }
            if filterPreferences {
                let preservesKinds = preservesRequiredKinds(in: alternative, from: target)
                guard !hasKindPreservingOption || preservesKinds else { continue }
                if preservesKinds && !hasKindPreservingOption {
                    hasKindPreservingOption = true
                    mostUnchangedHands = -1
                    options.removeAll()
                    seen.removeAll()
                }
                let unchangedHands = unchangedHandCount(in: alternative, from: target)
                guard unchangedHands >= mostUnchangedHands else { continue }
                if unchangedHands > mostUnchangedHands {
                    mostUnchangedHands = unchangedHands
                    options.removeAll()
                    seen.removeAll()
                }
            }
            let components = unique(resolved.positionIDs).sorted() + ["contacts"] + unique(resolved.contacts.map(\.id)).sorted()
            let id = components.map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
            guard seen.insert(id).inserted else { continue }
            let descriptions = resolved.contacts.map(replacementHoldLabel)
            let names: String
            if case .tasks(let sourceTasks) = target, let source = sourceTasks.first,
               source.count == 2, source[0].target != source[1].target,
               case .tasks(let alternatives) = alternative, let task = alternatives.first,
               descriptions.count == 2 {
                let firstSide = task[0].side ?? (task[1].side == .left ? .right : .left)
                let secondSide = task[1].side ?? (firstSide == .left ? .right : .left)
                names = "\(firstSide.rawValue.capitalized): \(descriptions[0]) · \(secondSide.rawValue.capitalized): \(descriptions[1])"
            } else {
                names = unique(descriptions).joined(separator: " + ")
            }
            let handContext: String
            if case .tasks(let tasks) = alternative, tasks.first?.count == 2 {
                if board.isOneHanded {
                    handContext = " (two boards)"
                } else {
                    handContext = ""
                }
            } else {
                handContext = ""
            }
            options.append(PlanHoldSubstitutionOption(id: id, label: names + handContext, target: alternative))
        }
        return options.sorted { $0.label == $1.label ? $0.id < $1.id : $0.label.localizedStandardCompare($1.label) == .orderedAscending }
    }

    /// Prefer valid alternatives that keep every authored hold kind. Unspecified
    /// and athlete-selected hand targets add no inferred kind restriction.
    private static func preservesRequiredKinds(in alternative: WorkoutSegmentTarget, from original: WorkoutSegmentTarget) -> Bool {
        switch (original, alternative) {
        case (.tasks(let originalTasks), .tasks(let alternatives)):
            guard let source = originalTasks.first, let selected = alternatives.first,
                  source.count == selected.count else { return false }
            return zip(source, selected).allSatisfy { required, replacement in
                required.target?.kind == nil || required.target?.kind == replacement.target?.kind
            }
        case (.requirements(let source), .requirements(let selected)):
            guard source.count == selected.count else { return false }
            return zip(source, selected).allSatisfy { required, replacement in
                required.kind == nil || required.kind == replacement.kind
            }
        default:
            return false
        }
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

    /// Prescribed intervals may overlap a contact's measured range. A generated
    /// substitute retains the resolved contact's exact facts so its label and
    /// recorded target describe the athlete's selected hold.
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
                return first
            }
            return zip(task, descriptions).map { hand, description in
                hand.side.map { "\($0.rawValue.capitalized): \(description)" } ?? description
            }.joined(separator: " + ")
        }.joined(separator: "; ")
        }
    }

    private static func replacementHoldLabel(_ contact: PhysicalContact) -> String {
        if contact.depth == nil {
            // Keep authored names when the structured facts omit a distinguishing
            // measurement or angle, while removing redundant left/right words.
            let neutralName = contact.name.replacingOccurrences(
                of: #"\b(?:left|right)-\b|-\b(?:left|right)\b|\b(?:left|right)\b"#,
                with: "", options: [.regularExpression, .caseInsensitive]
            )
            let words = neutralName.split(whereSeparator: \.isWhitespace)
            if !words.isEmpty { return words.joined(separator: " ") }
        }
        return label(for: ContactRequirement(kind: contact.kind, shape: contact.shape,
            depth: contact.depth, fingerCapacity: contact.fingerCapacity), includingMeasuredRanges: true)
    }

    private static func label(for requirement: ContactRequirement, includingMeasuredRanges: Bool = false) -> String {
        var parts: [String] = []
        if let depth = requirement.depth {
            switch depth {
            case .category(let size): parts.append(size.label.lowercased())
            case .range(let range):
                // Keep range prescriptions in the original step instruction;
                // substitute labels include the board's measured ranges.
                if range.minimum == range.maximum {
                    parts.append("\(number(range.minimum)) mm")
                } else if includingMeasuredRanges {
                    parts.append("\(number(range.minimum))–\(number(range.maximum)) mm")
                }
            }
        }
        if let shape = requirement.shape { parts.append(shape.label.lowercased()) }
        if requirement.kind == .pocket, let fingers = requirement.fingerCapacity {
            let count = [1: "one", 2: "two", 3: "three", 4: "four"][fingers] ?? String(fingers)
            parts.append("\(count)-finger")
        }
        if let kind = requirement.kind { parts.append(kind.detailLabel.lowercased()) }
        return parts.isEmpty ? requirement.contactID ?? "Required hold" : parts.joined(separator: " ")
    }

    private static func number(_ value: Double) -> String {
        value.formatted(.number.precision(.fractionLength(0...2)))
    }

    private static func replacing(_ step: WorkoutStep, segments: [WorkoutSegment]) -> WorkoutStep {
        WorkoutStep(id: step.id, number: step.number, title: step.title,
            instruction: step.instruction, accessory: step.accessory,
            duration: step.duration, phase: step.phase, segments: segments,
            gripType: step.gripType, fingerConfiguration: step.fingerConfiguration,
            handUse: step.handUse, side: step.side, action: step.action,
            repetitions: step.repetitions, externalLoadKGF: step.externalLoadKGF,
            timedWorkDuration: step.timedWorkDuration)
    }
}
