import Foundation
import HealthKit

enum HangTenHealthMetadata {
    static let brandName = "Hang Ten"
    static let planNameKey = "HangTen.PlanName"
    static let sessionIDKey = "HangTen.SessionID"
}

struct PendingWorkoutRecord: Codable, Equatable, Identifiable {
    let id: UUID
    let planTitle: String
    let startDate: Date
    let endDate: Date
    var healthUploadAttempted: Bool
    var healthWorkoutUUID: UUID?
}

struct HealthWorkoutRecord: Equatable, Identifiable {
    let id: UUID
    let activityTypeRawValue: UInt
    let brandName: String?
    let planTitle: String?
    let sessionID: UUID?
    let startDate: Date
    let endDate: Date

    var isHangTen: Bool {
        activityTypeRawValue == HKWorkoutActivityType.functionalStrengthTraining.rawValue &&
            brandName == HangTenHealthMetadata.brandName &&
            !(planTitle?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true)
    }
}

struct WorkoutHistoryEntry: Equatable, Identifiable {
    let id: UUID
    let planTitle: String
    let startDate: Date
    let endDate: Date
    let isPendingLocalRecord: Bool
}

enum WorkoutHistorySource: Equatable {
    case healthKit
    case localFallback
    case syncing
    case unavailable
}

struct WorkoutHistorySnapshot: Equatable {
    static let empty = WorkoutHistorySnapshot(entries: [], source: .unavailable)

    let entries: [WorkoutHistoryEntry]
    let source: WorkoutHistorySource

    var sessionCount: Int { entries.count }
    var latestSessionTitle: String? { entries.first?.planTitle }
}

enum WorkoutHistoryMatcher {
    static func entry(from record: HealthWorkoutRecord) -> WorkoutHistoryEntry {
        WorkoutHistoryEntry(
            id: record.id,
            planTitle: record.planTitle?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "",
            startDate: record.startDate,
            endDate: record.endDate,
            isPendingLocalRecord: false
        )
    }

    static func matchingHealthWorkout(
        for localRecord: PendingWorkoutRecord,
        in healthRecords: [HealthWorkoutRecord]
    ) -> HealthWorkoutRecord? {
        healthRecords.first { record in
            record.isHangTen && (
                record.sessionID == localRecord.id ||
                record.id == localRecord.healthWorkoutUUID ||
                (record.planTitle?.trimmingCharacters(in: .whitespacesAndNewlines) ==
                    localRecord.planTitle.trimmingCharacters(in: .whitespacesAndNewlines) &&
                    record.startDate == localRecord.startDate &&
                    record.endDate == localRecord.endDate)
            )
        }
    }

    static func snapshot(
        healthRecords: [HealthWorkoutRecord],
        localRecords: [PendingWorkoutRecord],
        healthQuerySucceeded: Bool,
        healthDataAvailable: Bool
    ) -> WorkoutHistorySnapshot {
        let acceptedHealthRecords = healthRecords.filter(\.isHangTen)
        let sortedHealthRecords = acceptedHealthRecords.sorted(by: newestFirst)
        var seenHealthIDs = Set<UUID>()
        let uniqueHealthRecords = sortedHealthRecords.filter { seenHealthIDs.insert($0.id).inserted }
        let healthEntries = uniqueHealthRecords.map(entry(from:))

        let unmatchedLocalEntries = localRecords
            .filter { matchingHealthWorkout(for: $0, in: acceptedHealthRecords) == nil }
            .map { record in
                WorkoutHistoryEntry(
                    id: record.id,
                    planTitle: record.planTitle,
                    startDate: record.startDate,
                    endDate: record.endDate,
                    isPendingLocalRecord: true
                )
            }

        let entries = (healthEntries + unmatchedLocalEntries).sorted(by: newestFirst)
        let source: WorkoutHistorySource
        if healthQuerySucceeded && !acceptedHealthRecords.isEmpty {
            source = .healthKit
        } else if !unmatchedLocalEntries.isEmpty {
            source = .localFallback
        } else if !healthDataAvailable {
            source = .unavailable
        } else {
            source = .unavailable
        }

        return WorkoutHistorySnapshot(entries: entries, source: source)
    }

    private static func newestFirst(
        _ lhs: WorkoutHistoryEntry,
        _ rhs: WorkoutHistoryEntry
    ) -> Bool {
        if lhs.startDate != rhs.startDate { return lhs.startDate > rhs.startDate }
        return lhs.id.uuidString < rhs.id.uuidString
    }

    private static func newestFirst(
        _ lhs: HealthWorkoutRecord,
        _ rhs: HealthWorkoutRecord
    ) -> Bool {
        if lhs.startDate != rhs.startDate { return lhs.startDate > rhs.startDate }
        return lhs.id.uuidString < rhs.id.uuidString
    }
}
