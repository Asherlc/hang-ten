import Foundation
import Combine

final class AppStore: ObservableObject {
    private static let healthAuthorizationRequestedKey = "HangTen.healthAuthorizationRequested.v1"

    @Published var selectedBoard: TrainingBoard = BoardCatalog.compactII
	@Published private(set) var workoutHistory = WorkoutHistorySnapshot.empty
	@Published private(set) var healthAuthorizationState: HealthAuthorizationState
	@Published private(set) var healthAuthorizationError: String?
	@Published private(set) var hasRequestedHealthAuthorization: Bool

	private let healthKitService: ContextualWorkoutHealthStore
	private let workoutHistoryService: WorkoutHistoryService
	private let defaults: UserDefaults
	private var preservesCompletionError = false

	init(
		healthKitService: any WorkoutHealthStore = HealthKitService(),
		workoutHistoryStore: any WorkoutHistoryPersistence = LocalWorkoutHistoryStore(),
		defaults: UserDefaults = .standard
	) {
		let contextualHealthStore = ContextualWorkoutHealthStore(healthKitService)
		self.healthKitService = contextualHealthStore
		self.defaults = defaults
		let hasRequestedHealthAuthorization = defaults.bool(forKey: Self.healthAuthorizationRequestedKey)
		workoutHistoryService = WorkoutHistoryService(
			healthStore: contextualHealthStore,
			persistence: workoutHistoryStore,
			healthKitSyncEnabled: hasRequestedHealthAuthorization
		)
		healthAuthorizationState = contextualHealthStore.authorizationState
		self.hasRequestedHealthAuthorization = hasRequestedHealthAuthorization
		workoutHistory = workoutHistoryService.snapshot
	}

	convenience init(
		healthKitService: any HealthWorkoutSaving,
		defaults: UserDefaults = .standard
	) {
		self.init(
			healthKitService: HealthWorkoutStoreAdapter(healthKitService),
			workoutHistoryStore: LocalWorkoutHistoryStore(),
			defaults: defaults
		)
	}

	var sessionsCompleted: Int { workoutHistory.sessionCount }
	var lastSessionTitle: String? { workoutHistory.latestSessionTitle }

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
        endDate: Date
    ) {
		healthAuthorizationError = nil
		preservesCompletionError = false

		let recordingErrorMessage: String?
        do {
            let activitySegments = try WorkoutActivityRecorder().segments(
                for: plan,
                on: board,
                stopwatchDurations: stopwatchDurations
            )
			healthKitService.recordActivityContext(
				planTitle: plan.title,
				startDate: startDate,
				endDate: endDate,
				boardID: board.id,
				boardName: board.name,
				activitySegments: activitySegments
			)
			recordingErrorMessage = nil
        } catch {
			recordingErrorMessage = "Session logged in Hang Ten, but \(error.localizedDescription)"
			healthAuthorizationError = recordingErrorMessage
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
			endDate: endDate
		) { [weak self] in
			self?.publishWorkoutHistory(
				errorContext: .completion,
				recordingErrorMessage: recordingErrorMessage
			)
		}
    }

    func markSessionComplete(_ plan: TrainingPlan, startDate: Date, endDate: Date) {
        markSessionComplete(
            plan,
            board: selectedBoard,
            stopwatchDurations: [:],
            startDate: startDate,
            endDate: endDate
        )
    }

	func refreshHealthAuthorization() {
		healthAuthorizationState = healthKitService.authorizationState
		refreshWorkoutHistory()
	}

	func refreshWorkoutHistory() {
		if healthAuthorizationError == Self.completionSyncError {
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

	func requestHealthAuthorization() {
		healthAuthorizationError = nil
		preservesCompletionError = false
		hasRequestedHealthAuthorization = true
		defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
		workoutHistoryService.enableHealthKitSync()
		healthKitService.requestAuthorization { [weak self] state, error in
			DispatchQueue.main.async {
				guard let self else { return }
				self.healthAuthorizationState = state
				self.healthAuthorizationError = error?.localizedDescription
				self.refreshWorkoutHistory()
			}
		}
	}

	private func publishWorkoutHistory(
		errorContext: HistoryErrorContext,
		recordingErrorMessage: String?
	) {
		workoutHistory = workoutHistoryService.snapshot
		guard workoutHistoryService.lastError != nil else {
			healthAuthorizationError = recordingErrorMessage
			preservesCompletionError = recordingErrorMessage != nil
			return
		}
		guard recordingErrorMessage == nil else {
			healthAuthorizationError = recordingErrorMessage
			preservesCompletionError = true
			return
		}
		switch errorContext {
		case .completion:
			healthAuthorizationError = Self.completionSyncError
			preservesCompletionError = true
		case .refresh:
			guard !preservesCompletionError else { return }
			healthAuthorizationError = Self.historySyncError
		}
	}

	private static let completionSyncError = "Session was saved locally and will retry Apple Health sync."
	private static let historySyncError = "Apple Health history could not sync. Local history remains available."

	private enum HistoryErrorContext {
		case completion
		case refresh
	}
}

private final class ContextualWorkoutHealthStore: WorkoutHealthStore {
	private struct ActivityContext {
		let planTitle: String
		let startDate: Date
		let endDate: Date
		let boardID: String
		let boardName: String
		let activitySegments: [RecordedActivitySegment]
	}

	private let base: any WorkoutHealthStore
	private var activityContexts: [ActivityContext] = []

	init(_ base: any WorkoutHealthStore) {
		self.base = base
	}

	var isHealthDataAvailable: Bool {
		base.isHealthDataAvailable
	}

	var authorizationState: HealthAuthorizationState {
		base.authorizationState
	}

	func requestAuthorization(
		completion: @escaping (HealthAuthorizationState, Error?) -> Void
	) {
		base.requestAuthorization(completion: completion)
	}

	func fetchHangTenWorkouts(
		completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
	) {
		base.fetchHangTenWorkouts(completion: completion)
	}

	func recordActivityContext(
		planTitle: String,
		startDate: Date,
		endDate: Date,
		boardID: String,
		boardName: String,
		activitySegments: [RecordedActivitySegment]
	) {
		activityContexts.append(
			ActivityContext(
				planTitle: planTitle,
				startDate: startDate,
				endDate: endDate,
				boardID: boardID,
				boardName: boardName,
				activitySegments: activitySegments
			)
		)
	}

	func saveCompletedWorkout(
		id: UUID,
		title: String,
		startDate: Date,
		endDate: Date,
		completion: @escaping (Result<UUID, Error>) -> Void
	) {
		guard let contextIndex = activityContexts.firstIndex(where: {
			$0.planTitle == title &&
				$0.startDate == startDate &&
				$0.endDate == endDate
		}) else {
			base.saveCompletedWorkout(
				id: id,
				title: title,
				startDate: startDate,
				endDate: endDate,
				completion: completion
			)
			return
		}

		let context = activityContexts.remove(at: contextIndex)
		base.saveCompletedWorkout(
			id: id,
			title: title,
			startDate: startDate,
			endDate: endDate,
			boardID: context.boardID,
			boardName: context.boardName,
			activitySegments: context.activitySegments,
			completion: completion
		)
	}
}

private final class HealthWorkoutStoreAdapter: WorkoutHealthStore {
	private let savingService: any HealthWorkoutSaving

	init(_ savingService: any HealthWorkoutSaving) {
		self.savingService = savingService
	}

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
		completion(.success([]))
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
