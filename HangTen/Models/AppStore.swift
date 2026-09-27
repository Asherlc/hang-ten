import Foundation
import Combine

@MainActor
final class AppStore: ObservableObject {
    private static let healthAuthorizationRequestedKey = "HangTen.healthAuthorizationRequested.v1"
    private static let selectedBoardIDKey = "HangTen.selectedBoardID.v1"
    private static let favoritePlanIDsKey = "favoritePlanIDs"
    private static let favoriteBoardIDsKey = "favoriteBoardIDs"

    @Published private(set) var selectedBoard: BoardRevision
    @Published private(set) var workoutHistory: WorkoutHistorySnapshot
    @Published var lastSessionTitle: String?
    @Published private(set) var sessionHistory: [WorkoutSessionRecord]
    @Published private(set) var sessionPersistenceError: String?
    @Published private(set) var customPlans: [TrainingPlan]
    @Published private(set) var customRoutinePersistenceError: String?
    @Published private(set) var favoritePlanIDs: Set<String>
    @Published private(set) var favoriteBoardIDs: Set<String>
    @Published private(set) var healthAuthorizationState: HealthAuthorizationState
    @Published private(set) var healthAuthorizationError: String?
    @Published private(set) var hasRequestedHealthAuthorization: Bool

    private let defaults: UserDefaults
    private let healthKitService: any WorkoutHealthStore
    private let workoutHistoryService: WorkoutHistoryService
    private let motherboardBluetoothService: MotherboardBluetoothService
    private let motherboardSettingsStore: MotherboardSettingsStore
    private let workoutSessionStore: WorkoutSessionStoring
    private let customRoutineStore: CustomRoutineStoring
    private let workoutAccessStore: WorkoutAccessStore
    private let telemetry: TelemetryDependencies
    let purchaseManager: PurchaseManager
    private var customDefinitions: [CustomRoutineDefinition]
    private var preservesCompletionError = false
    private var healthAuthorizationErrorKind: HealthErrorKind?

    init(
        healthKitService: any WorkoutHealthStore = HealthKitService(),
        motherboardBluetoothService: MotherboardBluetoothService? = nil,
        motherboardSettingsStore: MotherboardSettingsStore? = nil,
        workoutSessionStore: WorkoutSessionStoring? = nil,
        workoutHistoryStore: (any WorkoutHistoryPersistence)? = nil,
        customRoutineStore: CustomRoutineStoring? = nil,
        defaults: UserDefaults = .standard,
        workoutAccessStore: WorkoutAccessStore? = nil,
        purchaseManager: PurchaseManager? = nil,
        telemetry: TelemetryDependencies = .noOp()
    ) {
        self.defaults = defaults
        CustomRoutineStore.removeLegacyPersistence(
            from: defaults,
            newKey: CustomRoutineStore.defaultKey
        )
        self.workoutAccessStore = workoutAccessStore ?? WorkoutAccessStore(defaults: defaults)
        self.purchaseManager = purchaseManager ?? PurchaseManager()
        let persistedBoardID = defaults.string(forKey: Self.selectedBoardIDKey)
        selectedBoard = BoardCatalog.all.first { $0.id == persistedBoardID }
            ?? BoardCatalog.defaultBoard
        #if DEBUG
        if let reviewBoardID = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_ID"],
           let reviewBoard = BoardCatalog.all.first(where: { $0.id == reviewBoardID }) {
            selectedBoard = reviewBoard
        }
        #endif
        self.healthKitService = healthKitService
        self.motherboardBluetoothService = motherboardBluetoothService ?? MotherboardBluetoothService(
            transport: CoreBluetoothMotherboardTransport()
        )
        self.motherboardSettingsStore = motherboardSettingsStore ?? MotherboardSettingsStore(
            defaults: defaults
        )
        self.telemetry = telemetry

        let resolvedCustomRoutineStore = customRoutineStore ?? CustomRoutineStore(defaults: defaults)
        self.customRoutineStore = resolvedCustomRoutineStore
        customDefinitions = resolvedCustomRoutineStore.routines
        customPlans = []
        customRoutinePersistenceError = resolvedCustomRoutineStore.persistenceError

        let resolvedSessionStore = workoutSessionStore ?? WorkoutSessionStore(defaults: defaults)
        self.workoutSessionStore = resolvedSessionStore
        let loadedSessions = resolvedSessionStore.sessions
        sessionHistory = loadedSessions
        sessionPersistenceError = resolvedSessionStore.persistenceError

        favoritePlanIDs = Set(defaults.stringArray(forKey: Self.favoritePlanIDsKey) ?? [])
        favoriteBoardIDs = Set(defaults.stringArray(forKey: Self.favoriteBoardIDsKey) ?? [])
        let hasRequestedHealthAuthorization = defaults.bool(
            forKey: Self.healthAuthorizationRequestedKey
        )
        self.hasRequestedHealthAuthorization = hasRequestedHealthAuthorization
        healthAuthorizationState = healthKitService.authorizationState
        workoutHistoryService = WorkoutHistoryService(
            healthStore: healthKitService,
            persistence: workoutHistoryStore ?? LocalWorkoutHistoryStore(defaults: defaults),
            healthKitSyncEnabled: hasRequestedHealthAuthorization
        )
        workoutHistory = workoutHistoryService.snapshot
        lastSessionTitle = workoutHistory.latestSessionTitle ?? loadedSessions.first?.planTitle

        resolvedSessionStore.load { [weak self] result in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.sessionHistory = self.workoutSessionStore.sessions
                if self.lastSessionTitle == nil {
                    self.lastSessionTitle = self.sessionHistory.first?.planTitle
                }
                self.recordSessionPersistence(result)
            }
        }
        reloadCustomRoutines()
    }

    var workoutLaunchDecision: WorkoutLaunchDecision {
        workoutAccessStore.launchDecision(
            hasLifetimeEntitlement: purchaseManager.hasLifetimeEntitlement
        )
    }

    func recordSavedWorkoutAccess() {
        workoutAccessStore.recordSavedFreeWorkout(
            hasLifetimeEntitlement: purchaseManager.hasLifetimeEntitlement
        )
    }

    deinit {}

    convenience init(
        healthKitService: any HealthWorkoutSaving,
        workoutSessionStore: WorkoutSessionStoring? = nil,
        defaults: UserDefaults = .standard
    ) {
        self.init(
            healthKitService: HealthWorkoutStoreAdapter(healthKitService),
            workoutSessionStore: workoutSessionStore,
            defaults: defaults
        )
    }

    convenience init(
        healthKitService: any HealthWorkoutSaving,
        workoutHistoryStore: any WorkoutHistoryPersistence,
        defaults: UserDefaults = .standard
    ) {
        self.init(
            healthKitService: HealthWorkoutStoreAdapter(healthKitService),
            workoutHistoryStore: workoutHistoryStore,
            defaults: defaults
        )
    }

    convenience init(
        healthKitService: any HealthWorkoutSaving,
        userDefaults: UserDefaults
    ) {
        self.init(
            healthKitService: HealthWorkoutStoreAdapter(healthKitService),
            defaults: userDefaults
        )
    }

    convenience init(
        healthKitService: any HealthWorkoutSaving,
        workoutSessionStore: any WorkoutSessionStoring,
        userDefaults: UserDefaults
    ) {
        self.init(
            healthKitService: HealthWorkoutStoreAdapter(healthKitService),
            workoutSessionStore: workoutSessionStore,
            defaults: userDefaults
        )
    }

    convenience init(userDefaults: UserDefaults) {
        self.init(defaults: userDefaults)
    }

    /// The dashboard count follows Apple Health after the user has connected it.
    /// Before then, either local history representation can provide the count.
    var sessionsCompleted: Int {
        if hasRequestedHealthAuthorization {
            return workoutHistory.sessionCount
        }
        return max(workoutHistory.sessionCount, sessionHistory.count)
    }

    var shouldShowConnectAppleHealth: Bool {
        healthAuthorizationState == .notDetermined
    }

    var mostRecentSavedLoadAdjustmentKGF: Double {
        sessionHistory.max { lhs, rhs in
            lhs.recordedAt < rhs.recordedAt
        }?.loadAdjustmentKGF ?? 0
    }

    var mostRecentSavedLoadAdjustmentDisplayUnit: WorkoutLoadAdjustmentDisplayUnit {
        sessionHistory.max { lhs, rhs in
            lhs.recordedAt < rhs.recordedAt
        }?.loadAdjustmentDisplayUnit ?? .kilograms
    }

    var plans: [TrainingPlan] {
        (PlanCatalog.all + customPlans).filter { plan in
            plan.boardID == nil || plan.boardID == selectedBoard.id
        }
    }

    func metadata(for plan: TrainingPlan) -> PlanMetadata {
        if let definition = customDefinition(for: plan.id) {
            return customMetadata(for: definition)
        }
        guard let metadata = PlanCatalog.metadata(for: plan.id) else {
            preconditionFailure("Missing metadata for plan \(plan.id)")
        }
        return metadata
    }

    func isCustom(_ plan: TrainingPlan) -> Bool {
        customDefinition(for: plan.id) != nil
    }

    func selectBoard(_ board: BoardRevision) {
        selectedBoard = board
        defaults.set(board.id, forKey: Self.selectedBoardIDKey)
        guard let family = telemetryBoardFamily(for: board) else { return }
        telemetry.tracking.track(.boardSelected(family: family))
    }

    func submitUserReport(_ report: HangTenUserReport) {
        guard !report.message.isEmpty else { return }
        telemetry.userReports.submit(report)
    }

    func customDefinition(for id: String) -> CustomRoutineDefinition? {
        customDefinitions.first { $0.id == id }
    }

    func saveCustomRoutine(_ definition: CustomRoutineDefinition) throws {
        do {
            try customRoutineStore.save(definition)
            reloadCustomRoutines()
            telemetry.tracking.track(.customRoutineSaved)
        } catch {
            customRoutinePersistenceError = error.localizedDescription
            telemetry.diagnostics.record(
                .init(category: .persistence, operation: .save, error: error)
            )
            throw error
        }
    }

    func deleteCustomRoutine(id: String) throws {
        do {
            try customRoutineStore.delete(id: id)
            reloadCustomRoutines()
        } catch {
            customRoutinePersistenceError = error.localizedDescription
            throw error
        }
    }

    func duplicateRoutine(_ plan: TrainingPlan) throws -> CustomRoutineDefinition {
        let metadata = metadata(for: plan)
        let normalizedSteps = try plan.steps.flatMap(WorkoutStepNormalizer.expand)
        let normalizedPlan = TrainingPlan(
            id: plan.id,
            title: plan.title,
            subtitle: plan.subtitle,
            level: plan.level,
            sourceLabel: plan.sourceLabel,
            sourceURL: plan.sourceURL,
            provenance: plan.provenance,
            boardID: plan.boardID,
            steps: normalizedSteps
        )
        return try CustomRoutineStore.definition(
            from: normalizedPlan,
            metadata: metadata,
            id: "custom.\(UUID().uuidString)"
        )
    }

    var favoritePlans: [TrainingPlan] {
        plans.filter { favoritePlanIDs.contains($0.id) }
    }

    func isFavorite(_ plan: TrainingPlan) -> Bool {
        favoritePlanIDs.contains(plan.id)
    }

    func toggleFavorite(_ plan: TrainingPlan) {
        if favoritePlanIDs.contains(plan.id) {
            favoritePlanIDs.remove(plan.id)
        } else {
            favoritePlanIDs.insert(plan.id)
        }
        defaults.set(favoritePlanIDs.sorted(), forKey: Self.favoritePlanIDsKey)
    }

    func isFavorite(_ board: BoardRevision) -> Bool {
        favoriteBoardIDs.contains(board.id)
    }

    func toggleFavorite(_ board: BoardRevision) {
        if favoriteBoardIDs.contains(board.id) {
            favoriteBoardIDs.remove(board.id)
        } else {
            favoriteBoardIDs.insert(board.id)
        }
        defaults.set(favoriteBoardIDs.sorted(), forKey: Self.favoriteBoardIDsKey)
    }

    var featuredPlan: TrainingPlan? {
        #if DEBUG
        if let reviewPlanID = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_PLAN_ID"],
           let reviewPlan = plans.first(where: { $0.id == reviewPlanID }) {
            return reviewPlan
        }
        #endif
        return plans.first
    }

    func board(for plan: TrainingPlan) -> BoardRevision {
        BoardCatalog.board(for: plan.boardID ?? selectedBoard.id)
    }

    func contactIDs(for step: WorkoutStep, on board: BoardRevision) -> Set<String> {
        let candidates = handResolutionCandidates(for: step, on: board)
        return Set(candidates.flatMap {
            (try? ContactResolver.resolve($0.workRequirements, step: $0, board: board).map(\.id)) ?? []
        })
    }

    func isIncompatible(_ plan: TrainingPlan, on board: BoardRevision) -> Bool {
        plan.steps.contains { step in
            if WorkoutSessionHandResolver.stepNeedsHandResolution(
                step,
                boardIsOneHanded: board.isOneHanded
            ) {
                // Alternate / left / right need both unilateral sides independently
                // resolvable. Both hands is also compatible when its materialization
                // yields at least one contact (paired holds on a two-hand board, one
                // hold on a one-hand board).
                let sidesResolve = [WorkoutSide.left, .right].allSatisfy { side in
                    guard let resolved = step.resolvingEitherHand(
                        selectedHandSide: side,
                        boardIsOneHanded: board.isOneHanded
                    ) else {
                        return false
                    }
                    return resolved.workRequirements.allSatisfy { target in
                        (try? ContactResolver.resolve(target, step: resolved, board: board)) != nil
                    }
                }
                let both = WorkoutSessionHandResolver.materialized(
                    step,
                    preference: .both,
                    boardIsOneHanded: board.isOneHanded
                )
                let bothResolves = !((try? ContactResolver.resolve(
                    both.workRequirements,
                    step: both,
                    board: board
                )) ?? []).isEmpty
                return !(sidesResolve || bothResolves)
            }
            return step.workRequirements.contains { target in
                (try? ContactResolver.resolve(target, step: step, board: board)) == nil
            }
        }
    }

    /// Left/right unilateral materializations plus the both-mode
    /// materialization (paired holds on two-hand boards, one hold on one-hand
    /// boards) when the step still needs a start-of-session hand preference on
    /// this board.
    private func handResolutionCandidates(
        for step: WorkoutStep,
        on board: BoardRevision
    ) -> [WorkoutStep] {
        guard WorkoutSessionHandResolver.stepNeedsHandResolution(
            step,
            boardIsOneHanded: board.isOneHanded
        ) else {
            return [step]
        }
        let leftRight = [WorkoutSide.left, .right].compactMap {
            step.resolvingEitherHand(selectedHandSide: $0, boardIsOneHanded: board.isOneHanded)
        }
        let both = WorkoutSessionHandResolver.materialized(
            step,
            preference: .both,
            boardIsOneHanded: board.isOneHanded
        )
        return leftRight + [both]
    }

    private func reloadCustomRoutines() {
        let definitions = customRoutineStore.routines
        var plans: [TrainingPlan] = []
        var resolvedDefinitions: [CustomRoutineDefinition] = []
        var resolutionError: String?

        for definition in definitions {
            guard CustomRoutineValidator.idIssues(for: definition.id).isEmpty else {
                resolutionError = "Some custom routines could not be loaded."
                continue
            }
            do {
                plans.append(try customRoutineStore.plan(for: definition))
                resolvedDefinitions.append(definition)
            } catch {
                resolutionError = error.localizedDescription
            }
        }

        customDefinitions = resolvedDefinitions
        customPlans = plans
        customRoutinePersistenceError = customRoutineStore.persistenceError ?? resolutionError
    }

    private func customMetadata(for definition: CustomRoutineDefinition) -> PlanMetadata {
        CustomRoutineStore.metadata(for: definition)
    }

    func markSessionComplete(
        _ plan: TrainingPlan,
        board: BoardRevision,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval],
        startDate: Date,
        endDate: Date,
        selectedHandSide: WorkoutSide? = nil,
        handPreference: WorkoutSessionHandPreference? = nil,
        sessionSteps: [WorkoutStep]? = nil,
        session: WorkoutSessionRecord? = nil
    ) {
        if let session {
            workoutSessionStore.append(session) { [weak self] result in
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    self.recordSessionPersistence(result)
                    if case .success = result {
                        self.recordSavedWorkoutAccess()
                    }
                }
            }
        }
        sessionHistory = workoutSessionStore.sessions
        lastSessionTitle = plan.title
        setHealthAuthorizationError(nil, kind: nil)
        preservesCompletionError = false

        let recordingErrorMessage: String?
        let activityContext: PendingWorkoutActivityContext?
        do {
            let activityMetadata = try WorkoutActivityRecorder().metadata(
                for: plan,
                on: board,
                stopwatchDurations: stopwatchDurations,
                selectedHandSide: selectedHandSide,
                handPreference: handPreference,
                sessionSteps: sessionSteps,
                stepMeasurements: session?.steps ?? []
            )
            activityContext = PendingWorkoutActivityContext(
                boardID: board.id,
                boardName: board.name,
                activityMetadata: activityMetadata
            )
            recordingErrorMessage = nil
        } catch {
            activityContext = nil
            recordingErrorMessage = "Session logged in Hang Ten, but \(error.localizedDescription)"
            setHealthAuthorizationError(recordingErrorMessage, kind: .recording)
        }

        if hasRequestedHealthAuthorization {
            workoutHistory = WorkoutHistorySnapshot(
                entries: workoutHistory.entries,
                source: .syncing
            )
        }
        workoutHistoryService.recordCompletion(
            planTitle: plan.title,
            startDate: startDate,
            endDate: endDate,
            activityContext: activityContext,
            shouldUploadToHealthKit: recordingErrorMessage == nil
        ) { [weak self] in
            self?.publishWorkoutHistory(
                errorContext: .completion,
                recordingErrorMessage: recordingErrorMessage
            )
        }
    }

    func markSessionComplete(
        _ plan: TrainingPlan,
        startDate: Date,
        endDate: Date,
        selectedHandSide: WorkoutSide? = nil,
        handPreference: WorkoutSessionHandPreference? = nil,
        sessionSteps: [WorkoutStep]? = nil,
        session: WorkoutSessionRecord? = nil
    ) {
        markSessionComplete(
            plan,
            board: selectedBoard,
            stopwatchDurations: [:],
            startDate: startDate,
            endDate: endDate,
            selectedHandSide: selectedHandSide,
            handPreference: handPreference,
            sessionSteps: sessionSteps,
            session: session
        )
    }

    func refreshHealthAuthorization() {
        healthAuthorizationState = healthKitService.authorizationState
        reconcileAuthorizedHealthKitStateIfNeeded()
        refreshWorkoutHistory()
    }

    private func reconcileAuthorizedHealthKitStateIfNeeded() {
        guard healthAuthorizationState == .authorized,
              !hasRequestedHealthAuthorization else { return }
        hasRequestedHealthAuthorization = true
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
        workoutHistoryService.enableHealthKitSync()
    }

    func refreshWorkoutHistory() {
        if healthAuthorizationErrorKind == .completionSync {
            preservesCompletionError = false
        }
        if hasRequestedHealthAuthorization {
            workoutHistory = WorkoutHistorySnapshot(
                entries: workoutHistory.entries,
                source: .syncing
            )
        }
        workoutHistoryService.refresh { [weak self] in
            self?.publishWorkoutHistory(errorContext: .refresh, recordingErrorMessage: nil)
        }
    }

    func flushSessionPersistence(completion: (() -> Void)? = nil) {
        workoutSessionStore.flush { [weak self] result in
            Task { @MainActor [weak self] in
                self?.recordSessionPersistence(result)
                completion?()
            }
        }
    }

    func flushSessionPersistenceSynchronously() {
        workoutSessionStore.flush()
        let result: Result<Void, Error>
        if let persistenceError = workoutSessionStore.persistenceError {
            result = .failure(SessionPersistenceFailure(message: persistenceError))
        } else {
            result = .success(())
        }
        recordSessionPersistence(result)
    }

    func requestHealthAuthorization() {
        setHealthAuthorizationError(nil, kind: nil)
        preservesCompletionError = false
        hasRequestedHealthAuthorization = true
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
        workoutHistoryService.enableHealthKitSync()
        telemetry.replay.stop()
        healthKitService.requestAuthorization { [weak self] state, error in
            DispatchQueue.main.async {
                guard let self else { return }
                self.healthAuthorizationState = state
                self.setHealthAuthorizationError(
                    error?.localizedDescription,
                    kind: error == nil ? nil : .authorization
                )
                if let outcome = self.telemetryHealthAuthorizationOutcome(state: state, error: error) {
                    self.telemetry.tracking.track(.healthAuthorizationFinished(outcome: outcome))
                }
                self.refreshWorkoutHistory()
                self.telemetry.replay.start()
            }
        }
    }

    private func publishWorkoutHistory(
        errorContext: HistoryErrorContext,
        recordingErrorMessage: String?
    ) {
        let state = workoutHistoryService.state
        workoutHistory = state.snapshot
        if workoutHistory.source == .healthKit || workoutHistory.latestSessionTitle != nil {
            lastSessionTitle = workoutHistory.latestSessionTitle
        }
        guard state.lastError != nil else {
            setHealthAuthorizationError(
                recordingErrorMessage,
                kind: recordingErrorMessage == nil ? nil : .recording
            )
            preservesCompletionError = recordingErrorMessage != nil
            return
        }
        guard recordingErrorMessage == nil else {
            setHealthAuthorizationError(recordingErrorMessage, kind: .recording)
            preservesCompletionError = true
            return
        }
        switch errorContext {
        case .completion:
            setHealthAuthorizationError(Self.completionSyncError, kind: .completionSync)
            preservesCompletionError = true
        case .refresh:
            guard !preservesCompletionError else { return }
            setHealthAuthorizationError(Self.historySyncError, kind: .historySync)
        }
    }

    private func recordSessionPersistence(_ result: Result<Void, Error>) {
        switch result {
        case .success:
            sessionPersistenceError = nil
        case .failure(let error):
            sessionPersistenceError = "Session history could not be saved: \(error.localizedDescription)"
        }
    }

    private func setHealthAuthorizationError(_ message: String?, kind: HealthErrorKind?) {
        healthAuthorizationError = message
        healthAuthorizationErrorKind = kind
    }

    private func telemetryBoardFamily(
        for board: BoardRevision
    ) -> HangTenTelemetryEvent.BoardFamily? {
        let normalizedBoardID = board.id.replacingOccurrences(of: "-", with: "_")

        if normalizedBoardID.hasSuffix(HangTenTelemetryEvent.BoardFamily.compactII.rawValue) {
            return .compactII
        }
        if normalizedBoardID.hasSuffix(
            HangTenTelemetryEvent.BoardFamily.rockProdigyTrainingCenter.rawValue
        ) {
            return .rockProdigyTrainingCenter
        }
        return nil
    }

    private func telemetryHealthAuthorizationOutcome(
        state: HealthAuthorizationState,
        error: Error?
    ) -> HangTenTelemetryEvent.HealthAuthorizationOutcome? {
        guard state != .notDetermined else {
            return nil
        }

        if error != nil {
            return .error
        }

        switch state {
        case .authorized:
            return .granted
        case .denied:
            return .denied
        case .unavailable:
            return .unavailable
        case .notDetermined:
            return nil
        }
    }

    private static let completionSyncError = "Session was saved locally and will retry Apple Health sync."
    private static let historySyncError = "Apple Health history could not sync. Local history remains available."

    private enum HistoryErrorContext {
        case completion
        case refresh
    }

    private enum HealthErrorKind {
        case recording
        case completionSync
        case historySync
        case authorization
    }

    private struct SessionPersistenceFailure: LocalizedError {
        let message: String

        var errorDescription: String? { message }
    }
}

private final class HealthWorkoutStoreAdapter: WorkoutHealthStore {
    private let savingService: any HealthWorkoutSaving

    init(_ savingService: any HealthWorkoutSaving) {
        self.savingService = savingService
    }

    deinit {}

    var isHealthDataAvailable: Bool {
        savingService.authorizationState != .unavailable
    }

    var authorizationState: HealthAuthorizationState {
        savingService.authorizationState
    }

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        savingService.requestAuthorization(completion: completion)
    }

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    ) {
        completion(.failure(HealthWorkoutReadError.readNotSupported))
    }

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        savingService.saveCompletedWorkout(
            title: title,
            startDate: startDate,
            endDate: endDate,
            boardID: "",
            boardName: "",
            activitySegments: [],
            activityMeasurements: nil
        ) { error in
            if let error {
                completion(.failure(error))
            } else {
                completion(.success(id))
            }
        }
    }

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        boardID: String,
        boardName: String,
        activitySegments: [RecordedActivitySegment],
        activityMeasurements: [RecordedActivityStepMeasurement]?,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        savingService.saveCompletedWorkout(
            title: title,
            startDate: startDate,
            endDate: endDate,
            boardID: boardID,
            boardName: boardName,
            activitySegments: activitySegments,
            activityMeasurements: activityMeasurements
        ) { error in
            if let error {
                completion(.failure(error))
            } else {
                completion(.success(id))
            }
        }
    }
}
