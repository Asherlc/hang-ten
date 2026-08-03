import Foundation
import Combine

@MainActor
final class AppStore: ObservableObject {
	private static let favoritePlanIDsKey = "favoritePlanIDs"
	private let userDefaults: UserDefaults

	@Published var selectedBoard: TrainingBoard = BoardCatalog.compactII
	var sessionsCompleted: Int { sessionHistory.count }
	@Published var lastSessionTitle: String?
	@Published private(set) var sessionHistory: [WorkoutSessionRecord]
	@Published private(set) var sessionPersistenceError: String?
	@Published private(set) var favoritePlanIDs: Set<String>
	@Published private(set) var healthAuthorizationState: HealthAuthorizationState
	@Published private(set) var healthAuthorizationError: String?

	private let motherboardBluetoothService: MotherboardBluetoothService
	private let motherboardSettingsStore: MotherboardSettingsStore
	private let workoutSessionStore: WorkoutSessionStoring
	private let healthKitService: HealthWorkoutSaving

	init(
		healthKitService: HealthWorkoutSaving = HealthKitService(),
		motherboardBluetoothService: MotherboardBluetoothService? = nil,
		motherboardSettingsStore: MotherboardSettingsStore = MotherboardSettingsStore(),
		workoutSessionStore: WorkoutSessionStoring = WorkoutSessionStore(),
		userDefaults: UserDefaults = .standard
	) {
		self.healthKitService = healthKitService
		self.userDefaults = userDefaults
		self.motherboardBluetoothService = motherboardBluetoothService ?? MotherboardBluetoothService(
			transport: CoreBluetoothMotherboardTransport()
		)
		self.motherboardSettingsStore = motherboardSettingsStore
		self.workoutSessionStore = workoutSessionStore
		let loadedSessions = workoutSessionStore.sessions
		sessionHistory = loadedSessions
		lastSessionTitle = loadedSessions.first?.planTitle
		sessionPersistenceError = workoutSessionStore.persistenceError
		favoritePlanIDs = Set(userDefaults.stringArray(forKey: Self.favoritePlanIDsKey) ?? [])
		healthAuthorizationState = healthKitService.authorizationState

		workoutSessionStore.load { [weak self] result in
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
		userDefaults.set(favoritePlanIDs.sorted(), forKey: Self.favoritePlanIDsKey)
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
			 sessionHistory = workoutSessionStore.sessions
		}

        lastSessionTitle = plan.title
		healthAuthorizationError = nil

        let activitySegments: [RecordedActivitySegment]
        do {
            activitySegments = try WorkoutActivityRecorder().segments(
                for: plan,
                on: board,
                stopwatchDurations: stopwatchDurations
            )
        } catch {
            DispatchQueue.main.async { [weak self] in
                self?.healthAuthorizationError = "Session logged in Hang Ten, but \(error.localizedDescription)"
            }
            return
        }

        healthKitService.saveCompletedWorkout(
			title: plan.title,
			startDate: startDate,
			endDate: endDate,
			boardID: board.id,
			boardName: board.name,
			activitySegments: activitySegments
		) { [weak self] error in
			guard let error else { return }
			DispatchQueue.main.async {
				self?.healthAuthorizationError = "Session logged in Hang Ten, but \(error.localizedDescription)"
			}
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
		healthAuthorizationError = nil
		healthKitService.requestAuthorization { [weak self] state, error in
			DispatchQueue.main.async {
				self?.healthAuthorizationState = state
				self?.healthAuthorizationError = error?.localizedDescription
			}
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

	private struct SessionPersistenceFailure: LocalizedError {
		let message: String

		var errorDescription: String? { message }
	}
}
