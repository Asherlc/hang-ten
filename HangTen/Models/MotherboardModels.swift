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
    let rawADCValues: [Int32]
    let sensorLoadsKGF: [Double]
    let aggregateLoadKGF: Double

    private enum CodingKeys: String, CodingKey {
        case timestamp, sampleNumber, batteryValue, rawADCValues, sensorLoadsKGF, aggregateLoadKGF
    }

    init(
        timestamp: Date,
        sampleNumber: UInt16,
        batteryValue: UInt16,
        rawADCValues: [Int32] = [],
        sensorLoadsKGF: [Double],
        aggregateLoadKGF: Double
    ) {
        self.timestamp = timestamp
        self.sampleNumber = sampleNumber
        self.batteryValue = batteryValue
        self.rawADCValues = rawADCValues
        self.sensorLoadsKGF = sensorLoadsKGF
        self.aggregateLoadKGF = aggregateLoadKGF
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        timestamp = try container.decode(Date.self, forKey: .timestamp)
        sampleNumber = try container.decode(UInt16.self, forKey: .sampleNumber)
        batteryValue = try container.decode(UInt16.self, forKey: .batteryValue)
        rawADCValues = try container.decodeIfPresent([Int32].self, forKey: .rawADCValues) ?? []
        sensorLoadsKGF = try container.decode([Double].self, forKey: .sensorLoadsKGF)
        aggregateLoadKGF = try container.decode(Double.self, forKey: .aggregateLoadKGF)
    }

    private enum Side {
        static let leftChannels = [0, 2]
        static let rightChannels = [1, 3]
    }

    var leftLoadKGF: Double { load(for: Side.leftChannels) }

    var rightLoadKGF: Double { load(for: Side.rightChannels) }

    var leftShare: Double { share(for: leftLoadKGF) }

    var rightShare: Double { share(for: rightLoadKGF) }

    func bodyweightPercentage(for bodyweightKGF: Double) -> Double {
        guard bodyweightKGF.isFinite, bodyweightKGF > 0,
              aggregateLoadKGF.isFinite, aggregateLoadKGF > 0 else { return 0 }
        let ratio = aggregateLoadKGF / bodyweightKGF
        guard ratio.isFinite else { return .greatestFiniteMagnitude }

        let percentage = ratio * 100
        return percentage.isFinite ? percentage : .greatestFiniteMagnitude
    }

    private func load(for channels: [Int]) -> Double {
        channels.reduce(0) { total, index in
            guard sensorLoadsKGF.indices.contains(index), sensorLoadsKGF[index].isFinite else { return total }
            let load = max(0, sensorLoadsKGF[index])
            let sum = total + load
            return sum.isFinite ? sum : .greatestFiniteMagnitude
        }
    }

    private func share(for load: Double) -> Double {
        let left = leftLoadKGF
        let right = rightLoadKGF
        let scale = max(left, right)
        guard scale.isFinite, scale > 0, load.isFinite else { return 0 }

        let normalizedTotal = left / scale + right / scale
        guard normalizedTotal.isFinite, normalizedTotal > 0 else { return 0 }
        return min(max(0, load / scale / normalizedTotal), 1)
    }
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

    var showsWorkoutMeter: Bool {
        self == .streaming
    }
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
    let bodyweightKGF: Double?
    let motherboardMeasurements: [MotherboardMeasurement]
    let motherboardMeasurementsTruncated: Bool

    private enum CodingKeys: String, CodingKey {
        case id, planID, planTitle, recordedAt, startDate, endDate
        case motherboardIdentifier, batteryValue, steps, bodyweightKGF, motherboardMeasurements, motherboardMeasurementsTruncated
    }

    init(
        id: UUID,
        planID: String,
        planTitle: String,
        recordedAt: Date,
        startDate: Date,
        endDate: Date,
        motherboardIdentifier: String?,
        batteryValue: UInt16?,
        steps: [WorkoutStepMeasurement],
        bodyweightKGF: Double? = nil,
        motherboardMeasurements: [MotherboardMeasurement] = [],
        motherboardMeasurementsTruncated: Bool = false
    ) {
        self.id = id
        self.planID = planID
        self.planTitle = planTitle
        self.recordedAt = recordedAt
        self.startDate = startDate
        self.endDate = endDate
        self.motherboardIdentifier = motherboardIdentifier
        self.batteryValue = batteryValue
        self.steps = steps
        self.bodyweightKGF = bodyweightKGF
        self.motherboardMeasurements = motherboardMeasurements
        self.motherboardMeasurementsTruncated = motherboardMeasurementsTruncated
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        planID = try container.decode(String.self, forKey: .planID)
        planTitle = try container.decode(String.self, forKey: .planTitle)
        recordedAt = try container.decode(Date.self, forKey: .recordedAt)
        startDate = try container.decode(Date.self, forKey: .startDate)
        endDate = try container.decode(Date.self, forKey: .endDate)
        motherboardIdentifier = try container.decodeIfPresent(String.self, forKey: .motherboardIdentifier)
        batteryValue = try container.decodeIfPresent(UInt16.self, forKey: .batteryValue)
        steps = try container.decode([WorkoutStepMeasurement].self, forKey: .steps)
        bodyweightKGF = try container.decodeIfPresent(Double.self, forKey: .bodyweightKGF)
        motherboardMeasurements = try container.decodeIfPresent([MotherboardMeasurement].self, forKey: .motherboardMeasurements) ?? []
        motherboardMeasurementsTruncated = try container.decodeIfPresent(Bool.self, forKey: .motherboardMeasurementsTruncated) ?? false
    }
}

final class MotherboardSettingsStore: ObservableObject {
    private enum Key {
        static let forceUnit = "motherboard.forceUnit"
        static let thresholdKGF = "motherboard.thresholdKGF"
        static let bodyweightCaptureDuration = "motherboard.bodyweightCaptureDuration"
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

    @Published var bodyweightCaptureDuration: TimeInterval {
        didSet {
            let normalized = Self.normalizedBodyweightCaptureDuration(bodyweightCaptureDuration)
            if bodyweightCaptureDuration != normalized {
                bodyweightCaptureDuration = normalized
            }
            defaults.set(normalized, forKey: Key.bodyweightCaptureDuration)
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

        let normalizedThreshold = Self.normalizedThreshold(defaults.object(forKey: Key.thresholdKGF) as? Double ?? 2.5)
        let normalizedBodyweightDuration = Self.normalizedBodyweightCaptureDuration(
            defaults.object(forKey: Key.bodyweightCaptureDuration) as? Double ?? 5
        )
        thresholdKGF = normalizedThreshold
        bodyweightCaptureDuration = normalizedBodyweightDuration
        defaults.set(normalizedThreshold, forKey: Key.thresholdKGF)
        defaults.set(normalizedBodyweightDuration, forKey: Key.bodyweightCaptureDuration)
    }

    private static func normalizedThreshold(_ value: Double) -> Double {
        guard value.isFinite, value >= 0.1 else { return 2.5 }
        return min(value, 50)
    }

    private static func normalizedBodyweightCaptureDuration(_ value: TimeInterval) -> TimeInterval {
        guard value.isFinite else { return 5 }
        return min(max(value.rounded(), 3), 10)
    }
}
