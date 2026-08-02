import Foundation
import Combine

@MainActor
final class AppStore: ObservableObject {
    @Published var selectedBoard: TrainingBoard = BoardCatalog.compactII
    @Published var sessionsCompleted = 0
    @Published var lastSessionTitle: String?
	@Published private(set) var sessionHistory: [WorkoutSessionRecord]
	@Published private(set) var healthAuthorizationState: HealthAuthorizationState
	@Published private(set) var healthAuthorizationError: String?

	private let motherboardBluetoothService: MotherboardBluetoothService
	private let motherboardSettingsStore: MotherboardSettingsStore
	private let workoutSessionStore: WorkoutSessionStoring
	private let healthKitService: HealthKitService

	init(
		healthKitService: HealthKitService = HealthKitService(),
		motherboardBluetoothService: MotherboardBluetoothService? = nil,
		motherboardSettingsStore: MotherboardSettingsStore = MotherboardSettingsStore(),
		workoutSessionStore: WorkoutSessionStoring = WorkoutSessionStore()
	) {
		self.healthKitService = healthKitService
		self.motherboardBluetoothService = motherboardBluetoothService ?? MotherboardBluetoothService(
			transport: CoreBluetoothMotherboardTransport()
		)
		self.motherboardSettingsStore = motherboardSettingsStore
		self.workoutSessionStore = workoutSessionStore
		let loadedSessions = workoutSessionStore.sessions
		sessionHistory = loadedSessions
		sessionsCompleted = loadedSessions.count
		lastSessionTitle = loadedSessions.first?.planTitle
		healthAuthorizationState = healthKitService.authorizationState
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

    func markSessionComplete(
		_ plan: TrainingPlan,
		startDate: Date,
		endDate: Date,
		session: WorkoutSessionRecord? = nil
	) {
		if let session {
			workoutSessionStore.append(session)
			sessionHistory = workoutSessionStore.sessions
		}
        sessionsCompleted += 1
        lastSessionTitle = plan.title
		healthAuthorizationError = nil
        healthKitService.saveCompletedWorkout(
			title: plan.title,
			startDate: startDate,
			endDate: endDate
		) { [weak self] error in
			guard let error else { return }
			DispatchQueue.main.async {
				self?.healthAuthorizationError = "Session logged in Hang Ten, but \(error.localizedDescription)"
			}
		}
    }

	func refreshHealthAuthorization() {
		healthAuthorizationState = healthKitService.authorizationState
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
}
