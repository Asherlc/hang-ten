import Foundation
import HealthKit

private enum HealthWorkoutWriteError: LocalizedError {
    case beginCollection
    case addMetadata
    case endCollection
    case finishWorkout

    var errorDescription: String? {
        switch self {
        case .beginCollection:
            "Apple Health could not begin recording this workout."
        case .addMetadata:
            "Apple Health could not attach the routine details."
        case .endCollection:
            "Apple Health could not finish collecting this workout."
        case .finishWorkout:
            "Apple Health did not save this workout."
        }
    }
}

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

    func saveCompletedWorkout(
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Error?) -> Void
    ) {
        guard authorizationState == .authorized, endDate > startDate else {
            completion(nil)
            return
        }

        let configuration = HKWorkoutConfiguration()
        configuration.activityType = .functionalStrengthTraining

        let builder = HKWorkoutBuilder(
            healthStore: healthStore,
            configuration: configuration,
            device: .local()
        )

        builder.beginCollection(withStart: startDate) { success, error in
            guard success else {
                completion(error ?? HealthWorkoutWriteError.beginCollection)
                return
            }

            builder.addMetadata([
                HKMetadataKeyWorkoutBrandName: "Hang Ten",
                "HangTen.PlanName": title
            ]) { metadataSaved, error in
                guard metadataSaved else {
                    completion(error ?? HealthWorkoutWriteError.addMetadata)
                    return
                }

                builder.endCollection(withEnd: endDate) { collectionEnded, error in
                    guard collectionEnded else {
                        completion(error ?? HealthWorkoutWriteError.endCollection)
                        return
                    }
                    builder.finishWorkout { workout, error in
                        guard workout != nil else {
                            completion(error ?? HealthWorkoutWriteError.finishWorkout)
                            return
                        }
                        completion(nil)
                    }
                }
            }
        }
    }
}
