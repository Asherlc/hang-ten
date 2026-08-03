import Foundation
import HealthKit

private enum HealthWorkoutWriteError: LocalizedError {
    case unavailableAuthorization
    case invalidInterval
    case beginCollection
    case addMetadata
    case endCollection
    case finishWorkout

    var errorDescription: String? {
        switch self {
        case .unavailableAuthorization:
            "Apple Health workout access is not authorized."
        case .invalidInterval:
            "The workout end time must be later than its start time."
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

protocol WorkoutHealthStore: AnyObject {
    var isHealthDataAvailable: Bool { get }
    var authorizationState: HealthAuthorizationState { get }

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    )

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    )

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    )
}

final class HealthKitService: WorkoutHealthStore {
    private let healthStore = HKHealthStore()

    var isHealthDataAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    var authorizationState: HealthAuthorizationState {
        guard isHealthDataAvailable else { return .unavailable }

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
        guard isHealthDataAvailable else {
            completion(.unavailable, nil)
            return
        }

        healthStore.requestAuthorization(
            toShare: [HKObjectType.workoutType()],
            read: [HKObjectType.workoutType()]
        ) { [weak self] _, error in
            completion(self?.authorizationState ?? .unavailable, error)
        }
    }

    static func record(from workout: HKWorkout) -> HealthWorkoutRecord {
        let metadata = workout.metadata ?? [:]
        return HealthWorkoutRecord(
            id: workout.uuid,
            activityTypeRawValue: workout.workoutActivityType.rawValue,
            brandName: metadata[HKMetadataKeyWorkoutBrandName] as? String,
            planTitle: metadata[HangTenHealthMetadata.planNameKey] as? String,
            sessionID: (metadata[HangTenHealthMetadata.sessionIDKey] as? String).flatMap(UUID.init),
            startDate: workout.startDate,
            endDate: workout.endDate
        )
    }

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    ) {
        let query = HKSampleQuery(
            sampleType: HKObjectType.workoutType(),
            predicate: nil,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)]
        ) { _, samples, error in
            if let error {
                completion(.failure(error))
                return
            }

            let records = (samples ?? [])
                .compactMap { $0 as? HKWorkout }
                .map(Self.record(from:))
                .filter(\.isHangTen)
            completion(.success(records))
        }
        healthStore.execute(query)
    }

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        guard authorizationState == .authorized else {
            completion(.failure(HealthWorkoutWriteError.unavailableAuthorization))
            return
        }
        guard endDate > startDate else {
            completion(.failure(HealthWorkoutWriteError.invalidInterval))
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
                completion(.failure(error ?? HealthWorkoutWriteError.beginCollection))
                return
            }

            builder.addMetadata([
                HKMetadataKeyWorkoutBrandName: HangTenHealthMetadata.brandName,
                HangTenHealthMetadata.planNameKey: title,
                HangTenHealthMetadata.sessionIDKey: id.uuidString
            ]) { metadataSaved, error in
                guard metadataSaved else {
                    completion(.failure(error ?? HealthWorkoutWriteError.addMetadata))
                    return
                }

                builder.endCollection(withEnd: endDate) { collectionEnded, error in
                    guard collectionEnded else {
                        completion(.failure(error ?? HealthWorkoutWriteError.endCollection))
                        return
                    }
                    builder.finishWorkout { workout, error in
                        guard let workout else {
                            completion(.failure(error ?? HealthWorkoutWriteError.finishWorkout))
                            return
                        }
                        completion(.success(workout.uuid))
                    }
                }
            }
        }
    }

    func saveCompletedWorkout(
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Error?) -> Void
    ) {
        saveCompletedWorkout(
            id: UUID(),
            title: title,
            startDate: startDate,
            endDate: endDate
        ) { result in
            switch result {
            case .success:
                completion(nil)
            case let .failure(error):
                completion(error)
            }
        }
    }
}
