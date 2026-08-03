import Foundation

final class WorkoutHistoryService {
    private(set) var snapshot: WorkoutHistorySnapshot
    private(set) var lastError: Error?

    private let healthStore: any WorkoutHealthStore
    private let persistence: any WorkoutHistoryPersistence
    private let synchronizationQueue = DispatchQueue(label: "com.hangten.workout-history")

    private var healthKitSyncEnabled: Bool
    private var isSynchronizing = false
    private var completions: [() -> Void] = []

    init(
        healthStore: any WorkoutHealthStore,
        persistence: any WorkoutHistoryPersistence,
        healthKitSyncEnabled: Bool = true
    ) {
        self.healthStore = healthStore
        self.persistence = persistence
        self.healthKitSyncEnabled = healthKitSyncEnabled
        snapshot = Self.localFallbackSnapshot(for: persistence.load())
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
                    healthWorkoutUUID: nil
                )
            )
            persistence.replace(records)
            enqueueRefresh(completion: completion)
        }
    }

    private func enqueueRefresh(completion: @escaping () -> Void) {
        completions.append(completion)
        guard !isSynchronizing else { return }

        isSynchronizing = true
        lastError = nil
        if healthKitSyncEnabled {
            snapshot = WorkoutHistorySnapshot(entries: snapshot.entries, source: .syncing)
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
            lastError = error
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
        attemptedRecordIDs: Set<UUID> = []
    ) {
        let records = persistence.load()
        guard healthStore.authorizationState == .authorized else {
            refetchAfterUploads()
            return
        }

        guard let index = records.firstIndex(where: {
            $0.healthWorkoutUUID == nil && !attemptedRecordIDs.contains($0.id)
        }) else {
            refetchAfterUploads()
            return
        }

        var uploadRecords = records
        uploadRecords[index].healthUploadAttempted = true
        persistence.replace(uploadRecords)
        let record = uploadRecords[index]

        healthStore.saveCompletedWorkout(
            id: record.id,
            title: record.planTitle,
            startDate: record.startDate,
            endDate: record.endDate
        ) { [weak self] result in
            self?.synchronizationQueue.async {
                guard let self else { return }
                var updatedRecords = self.persistence.load()
                if let updatedIndex = updatedRecords.firstIndex(where: { $0.id == record.id }) {
                    if case let .success(healthWorkoutUUID) = result {
                        updatedRecords[updatedIndex].healthWorkoutUUID = healthWorkoutUUID
                    } else if case let .failure(error) = result {
                        updatedRecords[updatedIndex].healthUploadAttempted = false
                        self.lastError = error
                    }
                    self.persistence.replace(updatedRecords)
                }
                self.uploadUnattemptedRecords(
                    healthRecords: healthRecords,
                    attemptedRecordIDs: attemptedRecordIDs.union([record.id])
                )
            }
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
                    self.lastError = error
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
            healthQuerySucceeded: false,
            healthDataAvailable: false
        )
    }

    private func publishedSnapshot(
        healthRecords: [HealthWorkoutRecord],
        localRecords: [PendingWorkoutRecord],
        healthQuerySucceeded: Bool
    ) -> WorkoutHistorySnapshot {
        let matcherSnapshot = WorkoutHistoryMatcher.snapshot(
            healthRecords: healthRecords,
            localRecords: localRecords,
            healthQuerySucceeded: healthQuerySucceeded,
            healthDataAvailable: healthStore.isHealthDataAvailable
        )
        let hasVisibleHealthRecord = healthRecords.contains { $0.isHangTen }
        let source: WorkoutHistorySource
        if hasVisibleHealthRecord {
            source = .healthKit
        } else if !matcherSnapshot.entries.isEmpty {
            source = .localFallback
        } else if healthQuerySucceeded {
            source = .healthKit
        } else {
            source = .unavailable
        }
        return WorkoutHistorySnapshot(entries: matcherSnapshot.entries, source: source)
    }

    private func finish(with snapshot: WorkoutHistorySnapshot) {
        self.snapshot = snapshot
        isSynchronizing = false
        let completions = self.completions
        self.completions.removeAll()
        DispatchQueue.main.async {
            completions.forEach { $0() }
        }
    }
}
