import Foundation
import Combine

final class AppStore: ObservableObject {
    private static let healthAuthorizationRequestedKey = "HangTen.healthAuthorizationRequested.v1"
    private static let favoritePlanIDsKey = "favoritePlanIDs"

    @Published var selectedBoard: TrainingBoard = BoardCatalog.compactII
	@Published private(set) var workoutHistory = WorkoutHistorySnapshot.empty
	@Published private(set) var favoritePlanIDs: Set<String>
	@Published private(set) var healthAuthorizationState: HealthAuthorizationState
	@Published private(set) var healthAuthorizationError: String?
	@Published private(set) var hasRequestedHealthAuthorization: Bool

	private let healthKitService: any WorkoutHealthStore
	private let workoutHistoryService: WorkoutHistoryService
	private let defaults: UserDefaults
	private var preservesCompletionError = false

	init(
		healthKitService: any WorkoutHealthStore = HealthKitService(),
		workoutHistoryStore: any WorkoutHistoryPersistence = LocalWorkoutHistoryStore(),
		defaults: UserDefaults = .standard
	) {
		self.healthKitService = healthKitService
		self.defaults = defaults
		favoritePlanIDs = Set(defaults.stringArray(forKey: Self.favoritePlanIDsKey) ?? [])
		let hasRequestedHealthAuthorization = defaults.bool(forKey: Self.healthAuthorizationRequestedKey)
		workoutHistoryService = WorkoutHistoryService(
			healthStore: healthKitService,
			persistence: workoutHistoryStore,
			healthKitSyncEnabled: hasRequestedHealthAuthorization
		)
		healthAuthorizationState = healthKitService.authorizationState
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
			workoutHistoryStore: LocalWorkoutHistoryStore(),
			defaults: userDefaults
		)
	}

	convenience init(userDefaults: UserDefaults) {
		self.init(defaults: userDefaults)
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
        endDate: Date
    ) {
		healthAuthorizationError = nil
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
