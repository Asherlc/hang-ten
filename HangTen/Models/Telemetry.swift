import Foundation

protocol TelemetryTracking: AnyObject {
    func track(_ event: HangTenTelemetryEvent)
}

protocol DiagnosticReporting: AnyObject {
    func record(_ diagnostic: HangTenDiagnostic)
}

protocol FeatureFlagProviding: AnyObject {
    func isEnabled(_ key: String, default defaultValue: Bool) -> Bool
}

protocol SessionReplayControlling: AnyObject {
    func start()
    func stop()
}

enum HangTenTelemetryEvent: Equatable {
    enum AppTab: String, Equatable {
        case train
        case plans
        case history
    }

    enum PlanSource: String, Equatable {
        case catalog
        case favorite
        case custom
    }

    enum WorkoutOutcome: String, Equatable {
        case completed
        case abandoned
    }

    enum BoardFamily: String, Equatable {
        case compactII = "compact_ii"
        case rockProdigyTrainingCenter = "rock_prodigy_training_center"
    }

    enum HealthAuthorizationOutcome: String, Equatable {
        case granted
        case denied
        case unavailable
        case error
    }

    enum MotherboardConnectionOutcome: String, Equatable {
        case connected
        case failed
        case disconnected
    }

    case appTabSelected(tab: AppTab)
    case planBrowsed(source: PlanSource)
    case workoutStarted(source: PlanSource)
    case workoutFinished(outcome: WorkoutOutcome, elapsed: TimeInterval)
    case boardSelected(family: BoardFamily)
    case customRoutineSaved
    case healthAuthorizationFinished(outcome: HealthAuthorizationOutcome)
    case motherboardConnectionFinished(outcome: MotherboardConnectionOutcome)
    case appDiagnosticRecorded(HangTenDiagnostic)

    var name: String {
        switch self {
        case .appTabSelected:
            "app tab selected"
        case .planBrowsed:
            "plan browsed"
        case .workoutStarted:
            "workout started"
        case .workoutFinished:
            "workout finished"
        case .boardSelected:
            "board selected"
        case .customRoutineSaved:
            "custom routine saved"
        case .healthAuthorizationFinished:
            "health authorization finished"
        case .motherboardConnectionFinished:
            "motherboard connection finished"
        case .appDiagnosticRecorded:
            "app diagnostic recorded"
        }
    }

    var properties: [String: String] {
        switch self {
        case let .appTabSelected(tab):
            ["tab": tab.rawValue]
        case let .planBrowsed(source), let .workoutStarted(source):
            ["source": source.rawValue]
        case let .workoutFinished(outcome, elapsed):
            [
                "outcome": outcome.rawValue,
                "duration_bucket": DurationBucket(elapsed: elapsed).rawValue
            ]
        case let .boardSelected(family):
            ["board_family": family.rawValue]
        case .customRoutineSaved:
            [:]
        case let .healthAuthorizationFinished(outcome):
            ["outcome": outcome.rawValue]
        case let .motherboardConnectionFinished(outcome):
            ["outcome": outcome.rawValue]
        case let .appDiagnosticRecorded(diagnostic):
            [
                "category": diagnostic.category.rawValue,
                "operation": diagnostic.operation.rawValue,
                "error_kind": diagnostic.errorKind.rawValue
            ]
        }
    }

    private enum DurationBucket: String {
        case under5Minutes = "under_5_minutes"
        case fiveTo10Minutes = "5_to_10_minutes"
        case tenTo15Minutes = "10_to_15_minutes"
        case fifteenPlusMinutes = "15_plus_minutes"

        init(elapsed: TimeInterval) {
            switch elapsed {
            case ..<300:
                self = .under5Minutes
            case ..<600:
                self = .fiveTo10Minutes
            case ..<900:
                self = .tenTo15Minutes
            default:
                self = .fifteenPlusMinutes
            }
        }
    }
}

struct HangTenDiagnostic: Equatable {
    enum Category: String, Equatable {
        case persistence
    }

    enum Operation: String, Equatable {
        case save
    }

    enum ErrorKind: String, Equatable {
        case cancellation
        case other
    }

    let category: Category
    let operation: Operation
    let errorKind: ErrorKind

    init(category: Category, operation: Operation, error: Error) {
        self.category = category
        self.operation = operation
        self.errorKind = error is CancellationError ? .cancellation : .other
    }
}

final class NoOpTelemetry: TelemetryTracking, DiagnosticReporting, FeatureFlagProviding, SessionReplayControlling {
    func track(_ event: HangTenTelemetryEvent) {}

    func record(_ diagnostic: HangTenDiagnostic) {}

    func isEnabled(_ key: String, default defaultValue: Bool) -> Bool {
        defaultValue
    }

    func start() {}

    func stop() {}
}
