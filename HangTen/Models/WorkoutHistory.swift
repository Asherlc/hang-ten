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
    var activityContext: PendingWorkoutActivityContext?
    var shouldUploadToHealthKit: Bool

    init(
        id: UUID,
        planTitle: String,
        startDate: Date,
        endDate: Date,
        healthUploadAttempted: Bool,
        healthWorkoutUUID: UUID?,
        activityContext: PendingWorkoutActivityContext? = nil,
        shouldUploadToHealthKit: Bool = true
    ) {
        self.id = id
        self.planTitle = planTitle
        self.startDate = startDate
        self.endDate = endDate
        self.healthUploadAttempted = healthUploadAttempted
        self.healthWorkoutUUID = healthWorkoutUUID
        self.activityContext = activityContext
        self.shouldUploadToHealthKit = shouldUploadToHealthKit
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case planTitle
        case startDate
        case endDate
        case healthUploadAttempted
        case healthWorkoutUUID
        case activityContext
        case shouldUploadToHealthKit
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        planTitle = try container.decode(String.self, forKey: .planTitle)
        startDate = try container.decode(Date.self, forKey: .startDate)
        endDate = try container.decode(Date.self, forKey: .endDate)
        healthUploadAttempted = try container.decode(Bool.self, forKey: .healthUploadAttempted)
        healthWorkoutUUID = try container.decodeIfPresent(UUID.self, forKey: .healthWorkoutUUID)
        activityContext = try container.decodeIfPresent(
            PendingWorkoutActivityContext.self,
            forKey: .activityContext
        )
        shouldUploadToHealthKit = try container.decodeIfPresent(
            Bool.self,
            forKey: .shouldUploadToHealthKit
        ) ?? true
    }
}

struct PendingWorkoutActivityContext: Codable, Equatable {
    let boardID: String
    let boardName: String
    let activitySegments: [RecordedActivitySegment]
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
        var seenSessionIDs = Set<UUID>()
        let uniqueHealthRecords = sortedHealthRecords.filter { record in
            guard seenHealthIDs.insert(record.id).inserted else { return false }
            if let sessionID = record.sessionID {
                guard seenSessionIDs.insert(sessionID).inserted else { return false }
            }
            return true
        }
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
        if healthQuerySucceeded {
            if acceptedHealthRecords.isEmpty && !unmatchedLocalEntries.isEmpty {
                source = .localFallback
            } else {
                source = .healthKit
            }
        } else if !unmatchedLocalEntries.isEmpty {
            source = .localFallback
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
