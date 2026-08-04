import Foundation
import Combine

@MainActor
final class AppStore: ObservableObject {
    private static let healthAuthorizationRequestedKey = "HangTen.healthAuthorizationRequested.v1"
    private static let favoritePlanIDsKey = "favoritePlanIDs"

    @Published var selectedBoard: TrainingBoard = BoardCatalog.compactII
    @Published private(set) var workoutHistory: WorkoutHistorySnapshot
    @Published var lastSessionTitle: String?
    @Published private(set) var sessionHistory: [WorkoutSessionRecord]
    @Published private(set) var sessionPersistenceError: String?
    @Published private(set) var favoritePlanIDs: Set<String>
    @Published private(set) var healthAuthorizationState: HealthAuthorizationState
    @Published private(set) var healthAuthorizationError: String?
    @Published private(set) var hasRequestedHealthAuthorization: Bool

    private let defaults: UserDefaults
    private let healthKitService: any WorkoutHealthStore
    private let workoutHistoryService: WorkoutHistoryService
    private let motherboardBluetoothService: MotherboardBluetoothService
    private let motherboardSettingsStore: MotherboardSettingsStore
    private let workoutSessionStore: WorkoutSessionStoring
    private var preservesCompletionError = false
    private var healthAuthorizationErrorKind: HealthErrorKind?

    init(
        healthKitService: any WorkoutHealthStore = HealthKitService(),
        motherboardBluetoothService: MotherboardBluetoothService? = nil,
        motherboardSettingsStore: MotherboardSettingsStore? = nil,
        workoutSessionStore: WorkoutSessionStoring? = nil,
        workoutHistoryStore: (any WorkoutHistoryPersistence)? = nil,
        defaults: UserDefaults = .standard
    ) {
        self.defaults = defaults
        self.healthKitService = healthKitService
        self.motherboardBluetoothService = motherboardBluetoothService ?? MotherboardBluetoothService(
            transport: CoreBluetoothMotherboardTransport()
        )
        self.motherboardSettingsStore = motherboardSettingsStore ?? MotherboardSettingsStore(
            defaults: defaults
        )

        let resolvedSessionStore = workoutSessionStore ?? WorkoutSessionStore(defaults: defaults)
        self.workoutSessionStore = resolvedSessionStore
        let loadedSessions = resolvedSessionStore.sessions
        sessionHistory = loadedSessions
        sessionPersistenceError = resolvedSessionStore.persistenceError

        favoritePlanIDs = Set(defaults.stringArray(forKey: Self.favoritePlanIDsKey) ?? [])
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
    }

    deinit {}

    convenience init(
        healthKitService: any HealthWorkoutSaving,
        defaults: UserDefaults = .standard
    ) {
        self.init(
            healthKitService: HealthWorkoutStoreAdapter(healthKitService),
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
        guard healthAuthorizationState != .unavailable,
              healthAuthorizationState != .denied else { return false }
        return healthAuthorizationState == .notDetermined ||
            !hasRequestedHealthAuthorization ||
            (workoutHistory.source == .healthKit && workoutHistory.entries.isEmpty)
    }

    var plans: [TrainingPlan] {
        PlanCatalog.all.filter { plan in
            isCompatible(plan, with: selectedBoard)
        }
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

    var featuredPlan: TrainingPlan? {
        #if DEBUG
        if let reviewPlanID = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_PLAN_ID"],
           let reviewPlan = plans.first(where: { $0.id == reviewPlanID }) {
            return reviewPlan
        }
        #endif
        return plans.first
    }

    func board(for plan: TrainingPlan) -> TrainingBoard {
        BoardCatalog.board(for: plan.boardID ?? selectedBoard.id)
    }

    func holdIDs(for step: WorkoutStep, on board: TrainingBoard) -> Set<String> {
        let ids = step.targets.flatMap { BoardTargetResolver.resolveHoldIDs(for: $0, on: board) }
        return Set(ids)
    }

    func usesFallbackMapping(_ plan: TrainingPlan, on board: TrainingBoard) -> Bool {
        plan.steps.flatMap(\.targets).contains { target in
            guard let feature = target.feature,
                  !target.fallbackFeatures.isEmpty else { return false }
            let hasExactMatch = board.holds.contains { $0.features.contains(feature) }
            return !hasExactMatch && !BoardTargetResolver.resolveHoldIDs(for: target, on: board).isEmpty
        }
    }

    private func isCompatible(_ plan: TrainingPlan, with board: TrainingBoard) -> Bool {
        guard plan.boardID == nil || plan.boardID == board.id else { return false }

        return plan.steps
            .flatMap(\.targets)
            .allSatisfy { !BoardTargetResolver.resolveHoldIDs(for: $0, on: board).isEmpty }
    }

    func markSessionComplete(
        _ plan: TrainingPlan,
        board: TrainingBoard,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval],
        startDate: Date,
        endDate: Date,
        session: WorkoutSessionRecord? = nil
    ) {
        if let session {
            workoutSessionStore.append(session) { [weak self] result in
                Task { @MainActor [weak self] in
                    self?.recordSessionPersistence(result)
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
            let activitySegments = try WorkoutActivityRecorder().segments(
                for: plan,
                on: board,
                stopwatchDurations: stopwatchDurations
            )
            if hasRequestedHealthAuthorization {
                activityContext = PendingWorkoutActivityContext(
                    boardID: board.id,
                    boardName: board.name,
                    activitySegments: activitySegments
                )
            } else {
                activityContext = nil
            }
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
        session: WorkoutSessionRecord? = nil
    ) {
        markSessionComplete(
            plan,
            board: selectedBoard,
            stopwatchDurations: [:],
            startDate: startDate,
            endDate: endDate,
            session: session
        )
    }

    func refreshHealthAuthorization() {
        healthAuthorizationState = healthKitService.authorizationState
        refreshWorkoutHistory()
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
        healthKitService.requestAuthorization { [weak self] state, error in
            DispatchQueue.main.async {
                guard let self else { return }
                self.healthAuthorizationState = state
                self.setHealthAuthorizationError(
                    error?.localizedDescription,
                    kind: error == nil ? nil : .authorization
                )
                self.refreshWorkoutHistory()
            }
        }
    }

    private func publishWorkoutHistory(
        errorContext: HistoryErrorContext,
        recordingErrorMessage: String?
    ) {
        workoutHistory = workoutHistoryService.snapshot
        if workoutHistory.source == .healthKit || workoutHistory.latestSessionTitle != nil {
            lastSessionTitle = workoutHistory.latestSessionTitle
        }
        guard workoutHistoryService.lastError != nil else {
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
            activitySegments: []
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
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        savingService.saveCompletedWorkout(
            title: title,
            startDate: startDate,
            endDate: endDate,
            boardID: boardID,
            boardName: boardName,
            activitySegments: activitySegments
        ) { error in
            if let error {
                completion(.failure(error))
            } else {
                completion(.success(id))
            }
        }
    }
}
