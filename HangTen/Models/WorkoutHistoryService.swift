import Foundation

final class WorkoutHistoryService {
    struct State {
        let snapshot: WorkoutHistorySnapshot
        let lastError: Error?
    }

    private let healthStore: any WorkoutHealthStore
    private let persistence: any WorkoutHistoryPersistence
    private let synchronizationQueue = DispatchQueue(label: "com.hangten.workout-history")

    private var storedSnapshot: WorkoutHistorySnapshot
    private var storedLastError: Error?

    private var healthKitSyncEnabled: Bool
    private var isSynchronizing = false
    private var needsResync = false
    private var completions: [() -> Void] = []

    init(
        healthStore: any WorkoutHealthStore,
        persistence: any WorkoutHistoryPersistence,
        healthKitSyncEnabled: Bool = true
    ) {
        self.healthStore = healthStore
        self.persistence = persistence
        self.healthKitSyncEnabled = healthKitSyncEnabled
        storedSnapshot = Self.localFallbackSnapshot(for: persistence.load())
        storedLastError = nil
    }

    deinit {}

    var snapshot: WorkoutHistorySnapshot {
        synchronizationQueue.sync { storedSnapshot }
    }

    var lastError: Error? {
        synchronizationQueue.sync { storedLastError }
    }

    var state: State {
        synchronizationQueue.sync {
            State(snapshot: storedSnapshot, lastError: storedLastError)
        }
    }

    func enableHealthKitSync() {
        synchronizationQueue.sync {
            healthKitSyncEnabled = true
        }
    }

    func refresh(completion: @escaping () -> Void) {
        synchronizationQueue.async { [weak self] in
            self?.enqueueRefresh(completion: completion)
        }
    }

    func recordCompletion(
        planTitle: String,
        startDate: Date,
        endDate: Date,
        activityContext: PendingWorkoutActivityContext? = nil,
        shouldUploadToHealthKit: Bool = true,
        completion: @escaping () -> Void
    ) {
        synchronizationQueue.async { [weak self] in
            guard let self else { return }
            var records = persistence.load()
            records.append(
                PendingWorkoutRecord(
                    id: UUID(),
                    planTitle: planTitle,
                    startDate: startDate,
                    endDate: endDate,
                    healthUploadAttempted: false,
                    healthWorkoutUUID: nil,
                    activityContext: activityContext,
                    shouldUploadToHealthKit: shouldUploadToHealthKit
                )
            )
            persistence.replace(records)
            if isSynchronizing {
                needsResync = true
            }
            enqueueRefresh(completion: completion)
        }
    }

    private func enqueueRefresh(completion: @escaping () -> Void) {
        completions.append(completion)
        guard !isSynchronizing else { return }

        isSynchronizing = true
        storedLastError = nil
        if healthKitSyncEnabled {
            storedSnapshot = WorkoutHistorySnapshot(entries: storedSnapshot.entries, source: .syncing)
        }
        synchronize()
    }

    private func synchronize() {
        guard healthKitSyncEnabled else {
            finish(with: Self.localFallbackSnapshot(for: persistence.load()))
            return
        }

        guard healthStore.isHealthDataAvailable else {
            finish(with: Self.localFallbackSnapshot(for: persistence.load()))
            return
        }

        healthStore.fetchHangTenWorkouts { [weak self] result in
            self?.synchronizationQueue.async {
                self?.handleInitialFetch(result)
            }
        }
    }

    private func handleInitialFetch(_ result: Result<[HealthWorkoutRecord], Error>) {
        let localRecords = persistence.load()
        switch result {
        case let .failure(error):
            storedLastError = error
            if let readError = error as? HealthWorkoutReadError, readError == .readNotSupported {
                uploadUnattemptedRecords(
                    healthRecords: [],
                    shouldRefetchAfterUploads: false
                )
                return
            }
            finish(with: Self.localFallbackSnapshot(for: localRecords))

        case let .success(healthRecords):
            let unresolvedRecords = localRecords.filter {
                WorkoutHistoryMatcher.matchingHealthWorkout(for: $0, in: healthRecords) == nil
            }
            persistence.replace(unresolvedRecords)
            uploadUnattemptedRecords(healthRecords: healthRecords)
        }
    }

    private func uploadUnattemptedRecords(
        healthRecords: [HealthWorkoutRecord],
        attemptedRecordIDs: Set<UUID> = [],
        shouldRefetchAfterUploads: Bool = true
    ) {
        guard healthStore.authorizationState == .authorized else {
            finishAfterUploads(shouldRefetchAfterUploads: shouldRefetchAfterUploads)
            return
        }

        let records = persistence.load()

        guard let index = records.firstIndex(where: {
            $0.shouldUploadToHealthKit &&
                $0.healthWorkoutUUID == nil &&
                !attemptedRecordIDs.contains($0.id)
        }) else {
            finishAfterUploads(shouldRefetchAfterUploads: shouldRefetchAfterUploads)
            return
        }

        var uploadRecords = records
        uploadRecords[index].healthUploadAttempted = true
        persistence.replace(uploadRecords)
        let record = uploadRecords[index]

        let uploadCompletion: (Result<UUID, Error>) -> Void = { [weak self] result in
            self?.synchronizationQueue.async {
                guard let self else { return }
                var updatedRecords = self.persistence.load()
                if let updatedIndex = updatedRecords.firstIndex(where: { $0.id == record.id }) {
                    if case let .success(healthWorkoutUUID) = result {
                        updatedRecords[updatedIndex].healthWorkoutUUID = healthWorkoutUUID
                    } else if case let .failure(error) = result {
                        updatedRecords[updatedIndex].healthUploadAttempted = false
                        self.storedLastError = error
                    }
                    self.persistence.replace(updatedRecords)
                }
                self.uploadUnattemptedRecords(
                    healthRecords: healthRecords,
                    attemptedRecordIDs: attemptedRecordIDs.union([record.id]),
                    shouldRefetchAfterUploads: shouldRefetchAfterUploads
                )
            }
        }
        if let activityContext = record.activityContext {
            healthStore.saveCompletedWorkout(
                id: record.id,
                title: record.planTitle,
                startDate: record.startDate,
                endDate: record.endDate,
                boardID: activityContext.boardID,
                boardName: activityContext.boardName,
                activitySegments: activityContext.activitySegments,
                completion: uploadCompletion
            )
        } else {
            healthStore.saveCompletedWorkout(
                id: record.id,
                title: record.planTitle,
                startDate: record.startDate,
                endDate: record.endDate,
                completion: uploadCompletion
            )
        }
    }

    private func finishAfterUploads(shouldRefetchAfterUploads: Bool) {
        if shouldRefetchAfterUploads {
            refetchAfterUploads()
        } else {
            finish(with: Self.localFallbackSnapshot(for: persistence.load()))
        }
    }

    private func refetchAfterUploads() {
        healthStore.fetchHangTenWorkouts { [weak self] result in
            self?.synchronizationQueue.async {
                guard let self else { return }
                let localRecords = self.persistence.load()
                switch result {
                case let .success(healthRecords):
                    let remainingRecords = localRecords.filter {
                        WorkoutHistoryMatcher.matchingHealthWorkout(for: $0, in: healthRecords) == nil
                    }
                    self.persistence.replace(remainingRecords)
                    self.finish(
                        with: self.publishedSnapshot(
                            healthRecords: healthRecords,
                            localRecords: remainingRecords,
                            healthQuerySucceeded: true
                        )
                    )

                case let .failure(error):
                    self.storedLastError = error
                    self.finish(with: Self.localFallbackSnapshot(for: localRecords))
                }
            }
        }
    }

    private static func localFallbackSnapshot(
        for records: [PendingWorkoutRecord]
    ) -> WorkoutHistorySnapshot {
        WorkoutHistoryMatcher.snapshot(
            healthRecords: [],
            localRecords: records,
            healthQuerySucceeded: false
        )
    }

    private func publishedSnapshot(
        healthRecords: [HealthWorkoutRecord],
        localRecords: [PendingWorkoutRecord],
        healthQuerySucceeded: Bool
    ) -> WorkoutHistorySnapshot {
        return WorkoutHistoryMatcher.snapshot(
            healthRecords: healthRecords,
            localRecords: localRecords,
            healthQuerySucceeded: healthQuerySucceeded
        )
    }

    private func finish(with snapshot: WorkoutHistorySnapshot) {
        storedSnapshot = snapshot
        guard !needsResync else {
            needsResync = false
            storedLastError = nil
            if healthKitSyncEnabled {
                storedSnapshot = WorkoutHistorySnapshot(entries: snapshot.entries, source: .syncing)
            }
            synchronize()
            return
        }
        isSynchronizing = false
        let completions = self.completions
        self.completions.removeAll()
        DispatchQueue.main.async {
            completions.forEach { $0() }
        }
    }
}
