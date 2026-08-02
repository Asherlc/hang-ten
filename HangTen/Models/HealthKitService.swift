import Foundation
import HealthKit

enum HealthAuthorizationState: String, Hashable {
    case unavailable
    case notDetermined
    case denied
    case authorized

    var statusLabel: String {
        switch self {
        case .unavailable: "Unavailable"
        case .notDetermined: "Not connected"
        case .denied: "Access denied"
        case .authorized: "Connected"
        }
    }

    var detail: String {
        switch self {
        case .unavailable:
            "Apple Health is not available on this device."
        case .notDetermined:
            "Connect once to save completed routines as functional strength workouts."
        case .denied:
            "Workout access is off. You can enable it for Hang Ten in Settings."
        case .authorized:
            "Completed routines will be saved automatically to Apple Health."
        }
    }
}

final class HealthKitService {
    private let healthStore = HKHealthStore()

    var authorizationState: HealthAuthorizationState {
        guard HKHealthStore.isHealthDataAvailable() else { return .unavailable }

        switch healthStore.authorizationStatus(for: HKObjectType.workoutType()) {
        case .notDetermined:
            return .notDetermined
        case .sharingDenied:
            return .denied
        case .sharingAuthorized:
            return .authorized
        @unknown default:
            return .unavailable
        }
    }

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        guard HKHealthStore.isHealthDataAvailable() else {
            completion(.unavailable, nil)
            return
        }

        healthStore.requestAuthorization(
            toShare: [HKObjectType.workoutType()],
            read: []
        ) { [weak self] _, error in
            completion(self?.authorizationState ?? .unavailable, error)
        }
    }

    func saveCompletedWorkout(title: String, startDate: Date, endDate: Date) {
        guard authorizationState == .authorized, endDate > startDate else { return }

        let workout = HKWorkout(
            activityType: .functionalStrengthTraining,
            start: startDate,
            end: endDate,
            duration: endDate.timeIntervalSince(startDate),
            totalEnergyBurned: nil,
            totalDistance: nil,
            device: nil,
            metadata: [
                HKMetadataKeyWorkoutBrandName: "Hang Ten",
                "HangTen.PlanName": title
            ]
        )

        healthStore.save(workout) { _, _ in }
    }
}
