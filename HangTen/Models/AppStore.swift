import Foundation
import Combine

final class AppStore: ObservableObject {
    private static let healthAuthorizationRequestedKey = "HangTen.healthAuthorizationRequested.v1"

    @Published var selectedBoard: TrainingBoard = BoardCatalog.compactII
	@Published private(set) var workoutHistory = WorkoutHistorySnapshot.empty
	@Published private(set) var healthAuthorizationState: HealthAuthorizationState
	@Published private(set) var healthAuthorizationError: String?
	@Published private(set) var hasRequestedHealthAuthorization: Bool

	private let healthKitService: WorkoutHealthStore
	private let workoutHistoryService: WorkoutHistoryService
	private let defaults: UserDefaults

	init(
		healthKitService: any WorkoutHealthStore = HealthKitService(),
		workoutHistoryStore: any WorkoutHistoryPersistence = LocalWorkoutHistoryStore(),
		defaults: UserDefaults = .standard
	) {
		self.healthKitService = healthKitService
		workoutHistoryService = WorkoutHistoryService(
			healthStore: healthKitService,
			persistence: workoutHistoryStore
		)
		self.defaults = defaults
		healthAuthorizationState = healthKitService.authorizationState
		hasRequestedHealthAuthorization = defaults.bool(forKey: Self.healthAuthorizationRequestedKey)
	}

	var sessionsCompleted: Int { workoutHistory.sessionCount }
	var lastSessionTitle: String? { workoutHistory.latestSessionTitle }

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
        let ids = step.targets.flatMap { resolvedHoldIDs(for: $0, on: board) }
        return Set(ids)
    }

    func usesFallbackMapping(_ plan: TrainingPlan, on board: TrainingBoard) -> Bool {
        plan.steps.flatMap(\.targets).contains { target in
            guard let feature = target.feature,
                  !target.fallbackFeatures.isEmpty else { return false }
            let hasExactMatch = board.holds.contains { $0.features.contains(feature) }
            return !hasExactMatch && !resolvedHoldIDs(for: target, on: board).isEmpty
        }
    }

    private func isCompatible(_ plan: TrainingPlan, with board: TrainingBoard) -> Bool {
        guard plan.boardID == nil || plan.boardID == board.id else { return false }

        return plan.steps
            .flatMap(\.targets)
            .allSatisfy { !resolvedHoldIDs(for: $0, on: board).isEmpty }
    }

    private func resolvedHoldIDs(for target: HoldTarget, on board: TrainingBoard) -> [String] {
        if !target.holdIDs.isEmpty {
            let availableIDs = Set(board.holds.map(\.id))
            return target.holdIDs.filter(availableIDs.contains)
        }
        if let feature = target.feature {
            let exactMatches = board.holds
                .filter { $0.features.contains(feature) }
                .map(\.id)
            if !exactMatches.isEmpty {
                return exactMatches
            }
            for fallback in target.fallbackFeatures {
                let fallbackMatches = board.holds
                    .filter { $0.features.contains(fallback) }
                    .map(\.id)
                if !fallbackMatches.isEmpty {
                    return fallbackMatches
                }
            }
            return []
        }
        guard let kind = target.kind else { return [] }
        return board.holds.filter { $0.kind == kind }.map(\.id)
    }

    func markSessionComplete(_ plan: TrainingPlan, startDate: Date, endDate: Date) {
		healthAuthorizationError = nil
		workoutHistory = WorkoutHistorySnapshot(
			entries: workoutHistory.entries,
			source: .syncing
		)
		workoutHistoryService.recordCompletion(
			planTitle: plan.title,
			startDate: startDate,
			endDate: endDate
		) { [weak self] in
			self?.publishWorkoutHistory(errorContext: .completion)
		}
    }

	func refreshHealthAuthorization() {
		healthAuthorizationState = healthKitService.authorizationState
		refreshWorkoutHistory()
	}

	func refreshWorkoutHistory() {
		workoutHistory = WorkoutHistorySnapshot(
			entries: workoutHistory.entries,
			source: .syncing
		)
		workoutHistoryService.refresh { [weak self] in
			self?.publishWorkoutHistory(errorContext: .refresh)
		}
	}

	func requestHealthAuthorization() {
		healthAuthorizationError = nil
		hasRequestedHealthAuthorization = true
		defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
		healthKitService.requestAuthorization { [weak self] state, error in
			DispatchQueue.main.async {
				guard let self else { return }
				self.healthAuthorizationState = state
				self.healthAuthorizationError = error?.localizedDescription
				self.refreshWorkoutHistory()
			}
		}
	}

	private func publishWorkoutHistory(errorContext: HistoryErrorContext) {
		workoutHistory = workoutHistoryService.snapshot
		guard workoutHistoryService.lastError != nil else {
			healthAuthorizationError = nil
			return
		}
		switch errorContext {
		case .completion:
			healthAuthorizationError = "Session was saved locally and will retry Apple Health sync."
		case .refresh:
			healthAuthorizationError = "Apple Health history could not sync. Local history remains available."
		}
	}

	private enum HistoryErrorContext {
		case completion
		case refresh
	}
}
