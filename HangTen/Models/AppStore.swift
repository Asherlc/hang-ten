import Foundation
import Combine

final class AppStore: ObservableObject {
    @Published var selectedBoard: TrainingBoard = BoardCatalog.compactII
    @Published var sessionsCompleted = 0
    @Published var lastSessionTitle: String?
	@Published private(set) var healthAuthorizationState: HealthAuthorizationState
	@Published private(set) var healthAuthorizationError: String?

	private let healthKitService: HealthKitService
	private let planStore: PlanLibraryStore

	init(
		planStore: PlanLibraryStore = .builtIn,
		healthKitService: HealthKitService = HealthKitService()
	) {
		self.planStore = planStore
		self.healthKitService = healthKitService
		healthAuthorizationState = healthKitService.authorizationState
	}

    var plans: [TrainingPlan] {
        planStore.plans.filter { plan in
            plan.boardID == nil || plan.boardID == selectedBoard.id
        }
    }

    var featuredPlan: TrainingPlan {
        plans.first ?? planStore.plan(id: "metolius.compact-ii.ten-minute") ?? PlanCatalog.metoliusTenMinute
    }

    func board(for plan: TrainingPlan) -> TrainingBoard {
        BoardCatalog.board(for: plan.boardID ?? selectedBoard.id)
    }

    func holdIDs(for step: WorkoutStep, on board: TrainingBoard) -> Set<String> {
        let ids = step.targets.flatMap { target in
            if !target.holdIDs.isEmpty {
                return target.holdIDs
            }
            guard let kind = target.kind else { return [] }
            return board.holds.filter { $0.kind == kind }.map(\.id)
        }
        return Set(ids)
    }

    func markSessionComplete(_ plan: TrainingPlan, startDate: Date, endDate: Date) {
        sessionsCompleted += 1
        lastSessionTitle = plan.title
        healthKitService.saveCompletedWorkout(title: plan.title, startDate: startDate, endDate: endDate)
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
