import Foundation
import Combine

enum MotherboardForceUnit: String, CaseIterable, Codable, Identifiable {
    case kgf
    case lbf
    case newtons

    var id: String { rawValue }

    var label: String {
        switch self {
        case .kgf: "kgf"
        case .lbf: "lbf"
        case .newtons: "N"
        }
    }

    func value(fromKilogramsForce kgf: Double) -> Double {
        switch self {
        case .kgf: kgf
        case .lbf: kgf * 2.20462262185
        case .newtons: kgf * 9.80665
        }
    }
}

struct MotherboardMeasurement: Codable, Equatable {
    let timestamp: Date
    let sampleNumber: UInt16
    let batteryValue: UInt16
    let sensorLoadsKGF: [Double]
    let aggregateLoadKGF: Double
}

enum MotherboardConnectionState: Equatable {
    case bluetoothUnavailable
    case unauthorized
    case idle
    case scanning
    case connecting
    case calibrating
    case streaming
    case disconnected
    case failed
}

struct MotherboardDetectionConfiguration: Codable, Equatable {
    var thresholdKGF: Double = 2.5
    var releaseRatio: Double = 0.8
    var debounceDuration: TimeInterval = 0.10
    var mergeGapDuration: TimeInterval = 0.15
}

struct LoadInterval: Codable, Equatable {
    let start: TimeInterval
    let end: TimeInterval

    var duration: TimeInterval { max(0, end - start) }
}

struct WorkoutStepMeasurement: Codable, Equatable {
    let stepID: String
    let plannedActiveDuration: TimeInterval
    let intervals: [LoadInterval]
    let peakLoadKGF: Double?
    let sampleCount: Int
    let status: Status

    enum Status: String, Codable {
        case measured
        case unmeasured
        case interrupted
    }

    var actualLoadedDuration: TimeInterval {
        intervals.reduce(0) { $0 + $1.duration }
    }
}

struct WorkoutSessionRecord: Codable, Equatable, Identifiable {
    let id: UUID
    let planID: String
    let planTitle: String
    let recordedAt: Date
    let startDate: Date
    let endDate: Date
    let motherboardIdentifier: String?
    let batteryValue: UInt16?
    let steps: [WorkoutStepMeasurement]
}

final class MotherboardSettingsStore: ObservableObject {
    private enum Key {
        static let forceUnit = "motherboard.forceUnit"
        static let thresholdKGF = "motherboard.thresholdKGF"
    }

    private let defaults: UserDefaults

    @Published var forceUnit: MotherboardForceUnit {
        didSet { defaults.set(forceUnit.rawValue, forKey: Key.forceUnit) }
    }

    @Published var thresholdKGF: Double {
        didSet {
            let normalized = Self.normalizedThreshold(thresholdKGF)
            if thresholdKGF != normalized {
                thresholdKGF = normalized
            }
            defaults.set(normalized, forKey: Key.thresholdKGF)
        }
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults

        if let rawValue = defaults.string(forKey: Key.forceUnit),
           let storedForceUnit = MotherboardForceUnit(rawValue: rawValue) {
            forceUnit = storedForceUnit
        } else {
            forceUnit = .kgf
        }

        let storedThreshold = defaults.object(forKey: Key.thresholdKGF) as? Double
        thresholdKGF = Self.normalizedThreshold(storedThreshold ?? 2.5)
        defaults.set(thresholdKGF, forKey: Key.thresholdKGF)
    }

    private static func normalizedThreshold(_ value: Double) -> Double {
        guard value.isFinite, value >= 0.1 else { return 2.5 }
        return min(value, 50)
    }
}
