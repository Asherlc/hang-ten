import Foundation
import Combine

final class AppStore: ObservableObject {
    @Published var selectedBoard: TrainingBoard = BoardCatalog.compactII
    @Published var sessionsCompleted = 0
    @Published var lastSessionTitle: String?
	@Published private(set) var healthAuthorizationState: HealthAuthorizationState
	@Published private(set) var healthAuthorizationError: String?

	private let healthKitService: HealthWorkoutSaving

	init(healthKitService: HealthWorkoutSaving = HealthKitService()) {
		self.healthKitService = healthKitService
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
        sessionsCompleted += 1
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
