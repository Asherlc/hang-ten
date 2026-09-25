import Foundation

/// Resolves an athlete's pre-start hand choice at the presentation boundary.
/// The original definition remains visible until a valid side has been chosen.
enum WorkoutLiveStepResolver {
    static func materialized(
        _ step: WorkoutStep,
        selectedHandSide: WorkoutSide?,
        boardIsOneHanded: Bool = false
    ) -> WorkoutStep {
        step.resolvingEitherHand(selectedHandSide: selectedHandSide, boardIsOneHanded: boardIsOneHanded) ?? step
    }

    /// Preference-aware materialization for a single step. Alternate expansion is
    /// handled by `WorkoutSessionHandResolver.sessionSteps`; after that, steps are
    /// already concrete singles and this is an identity for them.
    static func materialized(
        _ step: WorkoutStep,
        preference: WorkoutSessionHandPreference,
        boardIsOneHanded: Bool = false
    ) -> WorkoutStep {
        WorkoutSessionHandResolver.materialized(
            step,
            preference: preference,
            boardIsOneHanded: boardIsOneHanded
        )
    }
}

/// Central start-of-session hand preference: gating, left/right/both materialization,
/// and alternate (L then R) expansion.
enum WorkoutSessionHandResolver {
    static func needsHandChoice(plan: TrainingPlan, board: BoardRevision) -> Bool {
        needsHandChoice(steps: plan.steps, boardIsOneHanded: board.isOneHanded)
    }

    static func needsHandChoice(steps: [WorkoutStep], boardIsOneHanded: Bool) -> Bool {
        steps.contains { stepNeedsHandResolution($0, boardIsOneHanded: boardIsOneHanded) }
    }

    /// True when a non-rest step must resolve to a concrete hand side for this board.
    /// Rest steps default to `.double` and must never force a hand choice.
    static func stepNeedsHandResolution(_ step: WorkoutStep, boardIsOneHanded: Bool) -> Bool {
        guard !step.isRestStep else { return false }
        return step.handUse == .either || (step.handUse == .double && boardIsOneHanded)
    }

    static func sessionSteps(
        from steps: [WorkoutStep],
        preference: WorkoutSessionHandPreference,
        boardIsOneHanded: Bool
    ) -> [WorkoutStep] {
        let resolved: [WorkoutStep]
        switch preference {
        case .left, .right, .both:
            resolved = steps.map {
                materialized($0, preference: preference, boardIsOneHanded: boardIsOneHanded)
            }
        case .alternate:
            resolved = steps.flatMap { step in
                expandAlternate(step, boardIsOneHanded: boardIsOneHanded)
            }
        }
        return renumbered(resolved)
    }

    static func materialized(
        _ step: WorkoutStep,
        preference: WorkoutSessionHandPreference,
        boardIsOneHanded: Bool = false
    ) -> WorkoutStep {
        // Rests pass through unchanged for every preference — never rewrite to
        // `.single` or retarget, even on one-handed boards.
        guard !step.isRestStep else { return step }

        switch preference {
        case .left, .right:
            return WorkoutLiveStepResolver.materialized(
                step,
                selectedHandSide: preference.selectedHandSide,
                boardIsOneHanded: boardIsOneHanded
            )
        case .both:
            return materializeBoth(step, boardIsOneHanded: boardIsOneHanded)
        case .alternate:
            // Alternate is expanded in `sessionSteps`. Concrete singles pass through.
            return step
        }
    }

    private static func materializeBoth(
        _ step: WorkoutStep,
        boardIsOneHanded: Bool
    ) -> WorkoutStep {
        guard stepNeedsHandResolution(step, boardIsOneHanded: boardIsOneHanded) else {
            return step
        }
        // A two-hand-capable board holds both hands on its paired left/right
        // holds; a one-hand board resolves one hold, performed on two boards.
        let transform: (ContactRequirement) -> ContactRequirement = boardIsOneHanded
            ? { $0.singleHandSelection }
            : { $0.bilateralSelection }
        let bothHandedSegments = step.segments.map { segment in
            segment.mappingRequirements(transform)
        }
        return WorkoutStep(
            id: step.id,
            number: step.number,
            title: step.title,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            segments: bothHandedSegments,
            gripType: step.gripType,
            fingerConfiguration: step.fingerConfiguration,
            handUse: .double,
            side: .both,
            action: step.action,
            repetitions: step.repetitions,
            externalLoadKGF: step.externalLoadKGF,
            timedWorkDuration: step.timedWorkDuration
        )
    }

    private static func expandAlternate(
        _ step: WorkoutStep,
        boardIsOneHanded: Bool
    ) -> [WorkoutStep] {
        // Rest and already-fixed `.single` steps pass through unchanged.
        guard stepNeedsHandResolution(step, boardIsOneHanded: boardIsOneHanded) else {
            return [step]
        }

        let left = WorkoutLiveStepResolver.materialized(
            step,
            selectedHandSide: .left,
            boardIsOneHanded: boardIsOneHanded
        )
        let right = WorkoutLiveStepResolver.materialized(
            step,
            selectedHandSide: .right,
            boardIsOneHanded: boardIsOneHanded
        )
        return [
            replacingID(left, with: "\(step.id).left"),
            replacingID(right, with: "\(step.id).right")
        ]
    }

    private static func replacingID(_ step: WorkoutStep, with id: String) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: step.number,
            title: step.title,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            segments: step.segments,
            gripType: step.gripType,
            fingerConfiguration: step.fingerConfiguration,
            handUse: step.handUse,
            side: step.side,
            action: step.action,
            repetitions: step.repetitions,
            externalLoadKGF: step.externalLoadKGF,
            timedWorkDuration: step.timedWorkDuration
        )
    }

    private static func renumbered(_ steps: [WorkoutStep]) -> [WorkoutStep] {
        steps.enumerated().map { index, step in
            step.withNumber(index + 1)
        }
    }
}

struct WorkoutClock {
    static var monotonicTime: TimeInterval {
        ProcessInfo.processInfo.systemUptime
    }

    private let now: () -> TimeInterval
    private var pausedElapsed: TimeInterval = 0
    private var activeStart: TimeInterval?

    init(now: @escaping () -> TimeInterval = { WorkoutClock.monotonicTime }) {
        self.now = now
    }

    var isRunning: Bool {
        activeStart != nil
    }

    var elapsed: TimeInterval {
        let activeElapsed = activeStart.map { max(0, now() - $0) } ?? 0
        return pausedElapsed + activeElapsed
    }

    var countdownRemaining: Int {
        guard let activeStart else {
            return 0
        }

        let remaining = activeStart - now()
        guard remaining > 0 else {
            return 0
        }
        return max(1, Int(ceil(remaining)))
    }

    mutating func start(initialCountdown: TimeInterval) {
        guard activeStart == nil else {
            return
        }
        activeStart = now() + max(0, initialCountdown)
    }

    mutating func pause() {
        pausedElapsed = elapsed
        activeStart = nil
    }

    mutating func reset() {
        pausedElapsed = 0
        activeStart = nil
    }

    mutating func seek(to elapsed: TimeInterval) {
        pausedElapsed = max(0, elapsed)
        if activeStart != nil {
            activeStart = now()
        }
    }
}

enum BoardHighlightMode: Hashable {
    case active
    case preview
}

struct WorkoutBoardCue: Equatable {
    let step: WorkoutStep?
    let mode: BoardHighlightMode
    let isResting: Bool
    let isSuppressed: Bool
}

struct WorkoutHoldCue: Equatable {
    let hold: PhysicalContact?
    let gripType: GripType?
    let fingerConfiguration: FingerConfiguration?

    init(
        hold: PhysicalContact? = nil,
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil
    ) {
        self.hold = hold
        self.gripType = gripType
        self.fingerConfiguration = fingerConfiguration
    }
}

enum WorkoutHoldCueVisibilityPolicy {
    static func showsCue(
        holdCue: WorkoutHoldCue?,
        countdown: Int,
        isComplete: Bool,
        isSkipCountdown: Bool = false
    ) -> Bool {
        holdCue != nil
            && !isComplete
            && (countdown == 0 || (countdown > 0 && isSkipCountdown))
    }

    static func showsCue(
        for cueSide: WorkoutSide,
        step: WorkoutStep?
    ) -> Bool {
        guard let step, step.handUse == .single else { return true }
        return step.side == cueSide
    }
}

/// Landscape lays the two hand cues out as fixed left/right slots beside the
/// board, so each slot has to follow the step the cue actually describes. That
/// is the upcoming work step while the athlete rests, not the resting step.
enum WorkoutLandscapeHandCuePolicy {
    static func showsHandCue(
        for cueSide: WorkoutSide,
        holdCue: WorkoutHoldCue?,
        cueStep: WorkoutStep?,
        countdown: Int,
        isComplete: Bool,
        isSkipCountdown: Bool
    ) -> Bool {
        WorkoutHoldCueVisibilityPolicy.showsCue(
            holdCue: holdCue,
            countdown: countdown,
            isComplete: isComplete,
            isSkipCountdown: isSkipCountdown
        ) && WorkoutHoldCueVisibilityPolicy.showsCue(for: cueSide, step: cueStep)
    }
}

enum WorkoutHoldCuePolicy {
    static func resolve(
        step: WorkoutStep?,
        hold: PhysicalContact?,
        on board: BoardRevision
    ) -> WorkoutHoldCue? {
        guard let step,
              step.gripType != nil || step.fingerConfiguration != nil else {
            return nil
        }
        let requirements = step.workRequirements
        if requirements.isEmpty {
            return WorkoutHoldCue(
                gripType: step.gripType,
                fingerConfiguration: step.fingerConfiguration
            )
        }
        // Attach the highlighted hold only when it satisfies the single work
        // requirement. Source grip/finger cues still show when the active board
        // cannot resolve the requirement (board-agnostic soft-fall) or when no
        // hold is highlighted yet (e.g. either-hand before selection).
        if requirements.count == 1,
           let target = requirements.first,
           let hold,
           (try? ContactResolver.resolve(target, step: step, board: board))?
             .contains(where: { $0.id == hold.id }) == true {
            return WorkoutHoldCue(
                hold: hold,
                gripType: step.gripType,
                fingerConfiguration: step.fingerConfiguration
            )
        }
        if hold != nil {
            return nil
        }
        return WorkoutHoldCue(
            gripType: step.gripType,
            fingerConfiguration: step.fingerConfiguration
        )
    }
}

struct FreeWorkoutStepUpdates: Equatable {
    var duration: TimeInterval?
    var timedWorkDuration: TimeInterval?
    var externalLoadKGF: Double?
    var repetitions: Int?

    init(
        duration: TimeInterval? = nil,
        timedWorkDuration: TimeInterval? = nil,
        externalLoadKGF: Double? = nil,
        repetitions: Int? = nil
    ) {
        self.duration = duration
        self.timedWorkDuration = timedWorkDuration
        self.externalLoadKGF = externalLoadKGF
        self.repetitions = repetitions
    }
}

struct WorkoutTimeline {
    private var steps: [WorkoutStep]
    private var startOffsets: [TimeInterval]

    init(steps: [WorkoutStep]) {
        self.steps = steps

        var cursor: TimeInterval = 0
        self.startOffsets = steps.map { step in
            defer { cursor += step.duration }
            return cursor
        }
        self.duration = cursor
    }

    private(set) var duration: TimeInterval

    var currentSteps: [WorkoutStep] {
        steps
    }

    /// Applies Strong-style live edits to the current or a future step.
    /// Past steps must never be edited by callers. Returns false when no
    /// step matches `id`, leaving the timeline untouched.
    @discardableResult
    mutating func updateStep(id: String, _ updates: FreeWorkoutStepUpdates) -> Bool {
        guard let index = steps.firstIndex(where: { $0.id == id }) else {
            return false
        }
        let old = steps[index]
        let newDuration = max(1, updates.duration ?? old.duration)
        let requestedTimedWork = updates.timedWorkDuration ?? old.timedWorkDuration
        let newTimedWork = requestedTimedWork.map { min(max($0, 0), newDuration) }
        steps[index] = WorkoutStep(
            id: old.id,
            number: old.number,
            title: old.title,
            instruction: old.instruction,
            accessory: old.accessory,
            duration: newDuration,
            phase: old.phase,
            segments: Self.remappedSegments(
                old,
                workDuration: newTimedWork ?? newDuration,
                totalDuration: newDuration
            ),
            gripType: old.gripType,
            fingerConfiguration: old.fingerConfiguration,
            handUse: old.handUse,
            side: old.side,
            action: old.action,
            repetitions: updates.repetitions ?? old.repetitions,
            externalLoadKGF: updates.externalLoadKGF.map { $0 <= 0 ? nil : $0 } ?? old.externalLoadKGF,
            timedWorkDuration: newTimedWork
        )
        var cursor: TimeInterval = 0
        startOffsets = steps.map { step in
            defer { cursor += step.duration }
            return cursor
        }
        duration = cursor
        return true
    }

    /// Keeps fixed work/rest segment durations summing to the step's edited
    /// duration. Non-fixed segments (undefined / stopwatch) carry no duration
    /// and pass through unchanged.
    private static func remappedSegments(
        _ step: WorkoutStep,
        workDuration: TimeInterval,
        totalDuration: TimeInterval
    ) -> [WorkoutSegment] {
        let restDuration = max(0, totalDuration - workDuration)
        return step.segments.map { segment in
            guard segment.timing == .fixed else { return segment }
            switch segment.kind {
            case .work:
                return WorkoutSegment(
                    kind: .work,
                    target: segment.target,
                    timing: .fixed,
                    duration: workDuration
                )
            case .rest:
                return WorkoutSegment(
                    kind: .rest,
                    target: segment.target,
                    timing: .fixed,
                    duration: restDuration
                )
            }
        }
    }

    static func labels(for step: WorkoutStep) -> [String] {
        guard !step.isRestStep else { return ["Rest"] }
        let actionLabel: String
        switch step.action {
        case .hang: actionLabel = "Hang"
        case .isometricPull: actionLabel = "Isometric pull"
        case .loadedLift: actionLabel = "Loaded lift"
        }
        var labels = [actionLabel]
        switch step.side {
        case .left: labels.append("Left hand")
        case .right: labels.append("Right hand")
        case .both: labels.append("Both hands")
        }
        if let repetitions = step.repetitions {
            labels.append("\(repetitions) \(repetitions == 1 ? "lift" : "lifts")")
        }
        return labels
    }

    func step(at elapsed: TimeInterval) -> WorkoutStep? {
        guard let location = location(at: elapsed) else {
            return nil
        }
        return steps[location.index]
    }

    func elapsedInStep(at elapsed: TimeInterval) -> TimeInterval {
        guard let location = location(at: elapsed) else {
            return 0
        }

        let stepDuration = steps[location.index].duration
        return min(max(0, clampedElapsed(elapsed) - location.start), stepDuration)
    }

    func startOffset(for stepID: String) -> TimeInterval? {
        guard let index = steps.firstIndex(where: { $0.id == stepID }) else {
            return nil
        }
        return startOffsets[index]
    }

    func selectionTarget(for stepID: String, at elapsed: TimeInterval) -> TimeInterval? {
        guard step(at: elapsed)?.id != stepID else {
            return nil
        }
        return startOffset(for: stepID)
    }

    func skipTarget(from elapsed: TimeInterval) -> TimeInterval? {
        guard let location = location(at: elapsed) else {
            return nil
        }

        let stepEnd = location.start + steps[location.index].duration
        return min(stepEnd, duration)
    }

    func nextWorkStep(after stepID: String) -> WorkoutStep? {
        guard let index = steps.firstIndex(where: { $0.id == stepID }) else {
            return nil
        }

        return steps.dropFirst(index + 1).first { $0.phase != .rest }
    }

    func holdPreviewStep(at elapsed: TimeInterval) -> WorkoutStep? {
        guard let currentStep = step(at: elapsed) else {
            return nil
        }

        return holdPreviewStep(
            currentStep: currentStep,
            stepElapsed: elapsedInStep(at: elapsed)
        )
    }

    func boardCue(
        at elapsed: TimeInterval,
        countdown: Int,
        isComplete: Bool,
        isSkipCountdown: Bool = false
    ) -> WorkoutBoardCue {
        boardCue(
            currentStep: step(at: elapsed),
            stepElapsed: elapsedInStep(at: elapsed),
            countdown: countdown,
            isComplete: isComplete,
            isSkipCountdown: isSkipCountdown
        )
    }

    func boardCue(
        currentStep: WorkoutStep?,
        stepElapsed: TimeInterval,
        countdown: Int,
        isComplete: Bool,
        isSkipCountdown: Bool = false
    ) -> WorkoutBoardCue {
        guard !isComplete,
              (countdown == 0 || (countdown > 0 && isSkipCountdown)),
              let currentStep else {
            return WorkoutBoardCue(
                step: nil,
                mode: .active,
                isResting: false,
                isSuppressed: true
            )
        }

        let resolvedStep = holdPreviewStep(
            currentStep: currentStep,
            stepElapsed: stepElapsed
        )

        if countdown > 0 {
            return WorkoutBoardCue(
                step: resolvedStep,
                mode: .preview,
                isResting: resolvedStep?.phase == .rest,
                isSuppressed: false
            )
        }

        let isResting = currentStep.phase == .rest
            || (currentStep.hasRestInterval && stepElapsed >= currentStep.activeDuration)

        return WorkoutBoardCue(
            step: resolvedStep,
            mode: isResting ? .preview : .active,
            isResting: isResting,
            isSuppressed: false
        )
    }

    func holdPreviewStep(
        currentStep: WorkoutStep,
        stepElapsed: TimeInterval
    ) -> WorkoutStep? {
        let isResting = currentStep.phase == .rest
            || (currentStep.hasRestInterval && stepElapsed >= currentStep.activeDuration)

        return isResting
            ? nextWorkStep(after: currentStep.id)
            : currentStep
    }

    private func clampedElapsed(_ elapsed: TimeInterval) -> TimeInterval {
        min(max(0, elapsed), duration)
    }

    private func location(at elapsed: TimeInterval) -> (index: Int, start: TimeInterval)? {
        guard !steps.isEmpty else {
            return nil
        }

        let clamped = clampedElapsed(elapsed)
        for index in steps.indices {
            let start = startOffsets[index]
            let end = start + steps[index].duration
            if clamped < end {
                return (index, start)
            }
        }

        let finalIndex = steps.index(before: steps.endIndex)
        return (finalIndex, startOffsets[finalIndex])
    }
}

struct WorkoutLiftCompletion: Equatable {
    private var repetitionsByStepID: [String: Int] = [:]
    private var externalLoadKGFByStepID: [String: Double] = [:]

    mutating func completeLift(for step: WorkoutStep) {
        guard step.action == .loadedLift, let prescribed = step.repetitions else { return }
        repetitionsByStepID[step.id] = min(
            prescribed,
            completedRepetitions(for: step) + 1
        )
    }

    func completedRepetitions(for step: WorkoutStep) -> Int {
        repetitionsByStepID[step.id, default: 0]
    }

    mutating func setExternalLoadKGF(_ value: Double, for step: WorkoutStep) {
        guard step.action == .loadedLift, value.isFinite else { return }
        externalLoadKGFByStepID[step.id] = value
    }

    func externalLoadKGF(for step: WorkoutStep) -> Double? {
        externalLoadKGFByStepID[step.id] ?? step.externalLoadKGF
    }
}

enum WorkoutLiftCompletionPolicy {
    static func isEnabled(
        completedRepetitions: Int,
        prescribedRepetitions: Int,
        sessionCanNavigate: Bool
    ) -> Bool {
        sessionCanNavigate && completedRepetitions < prescribedRepetitions
    }
}

enum WorkoutHighlightResolver {
    static func contactIDs(for step: WorkoutStep, on board: BoardRevision) -> [String] {
        (try? ContactResolver.resolve(
            step.workRequirements,
            step: step,
            board: board
        ).map(\.id)) ?? []
    }
}
