import Foundation

enum ForceSensorCapability: String, CaseIterable, Codable, Hashable {
    case hardwareTare
    case explicitStartStop
    case batteryLevel
}

enum ForceSensorMatchingPolicy: Equatable {
    case automatic
    case named
    case generic

    var permitsAutomaticSelection: Bool {
        self == .named
    }
}

enum ForceSensorProfile: String, CaseIterable, Codable, Identifiable {
    case automatic
    case motherboard
    case progressor
    case pitchSix
    case whC06
    case entralpi
    case climbro
    case genericProgressor
    case genericWHC06

    static let selectableCases: [ForceSensorProfile] = [
        .automatic,
        .motherboard,
        .progressor,
        .pitchSix,
        .whC06,
        .entralpi,
        .climbro,
        .genericProgressor,
        .genericWHC06
    ]

    var id: String { rawValue }

    var label: String {
        switch self {
        case .automatic: "Automatic"
        case .motherboard: "Motherboard"
        case .progressor: "Tindeq Progressor"
        case .pitchSix: "PitchSix Force Board"
        case .whC06: "WH-C06"
        case .entralpi: "Entralpi"
        case .climbro: "Climbro"
        case .genericProgressor: "Generic Progressor-compatible"
        case .genericWHC06: "Generic WH-C06-compatible"
        }
    }

    var matchingPolicy: ForceSensorMatchingPolicy {
        switch self {
        case .automatic:
            .automatic
        case .genericProgressor, .genericWHC06:
            .generic
        case .motherboard, .progressor, .pitchSix, .whC06, .entralpi, .climbro:
            .named
        }
    }
}

enum ForceSensorSourceUnit: String, CaseIterable, Codable {
    case kilogramsForce
    case poundsForce
    case newtons

    fileprivate func kilogramsForce(from value: Double) -> Double {
        switch self {
        case .kilogramsForce: value
        case .poundsForce: value / 2.20462262185
        case .newtons: value / 9.80665
        }
    }
}

struct ForceSensorSample: Equatable {
    let kilogramsForce: Double
    let receivedAt: Date

    init?(value: Double, unit: ForceSensorSourceUnit, receivedAt: Date) {
        guard value.isFinite, value >= 0 else { return nil }
        let kilogramsForce = unit.kilogramsForce(from: value)
        guard kilogramsForce.isFinite, kilogramsForce >= 0 else { return nil }

        self.kilogramsForce = kilogramsForce
        self.receivedAt = receivedAt
    }
}

enum ForceSensorCommand: String, CaseIterable, Codable, Hashable {
    case tare
    case start
    case stop
}

struct ForceSensorBLECharacteristic: Equatable, Hashable {
    let serviceUUID: UUID
    let characteristicUUID: UUID
}

struct ForceSensorBLECommand: Equatable {
    let characteristic: ForceSensorBLECharacteristic
    let payload: Data
}

struct ForceSensorBLEContract: Equatable {
    let serviceUUIDs: Set<UUID>
    let notificationCharacteristics: Set<ForceSensorBLECharacteristic>
    let commands: [ForceSensorCommand: ForceSensorBLECommand]
}

struct ForceSensorAdvertisement: Equatable {
    let name: String?
    let serviceUUIDs: Set<UUID>
    let manufacturerData: Data?
}
