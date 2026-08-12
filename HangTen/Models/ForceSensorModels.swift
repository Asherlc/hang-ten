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

    /// Profiles backed by a reviewed BLE adapter. Keep source-audited adapter
    /// availability separate from the broader catalog of planned profiles.
    static let connectableCases: [ForceSensorProfile] = [
        .automatic,
        .motherboard,
        .progressor,
        .pitchSix,
        .genericProgressor
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
        case .whC06, .genericProgressor, .genericWHC06:
            .generic
        case .motherboard, .progressor, .pitchSix, .entralpi, .climbro:
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

struct ForceSensorBLECharacteristic: Equatable, Hashable {
    let serviceUUID: UUID
    let characteristicUUID: UUID
}

struct ForceSensorBLEContract: Equatable {
    let serviceUUIDs: Set<UUID>
    let notificationCharacteristics: Set<ForceSensorBLECharacteristic>
}

struct ForceSensorManufacturerData: Equatable {
    let companyIdentifier: UInt16
    let payload: Data
}

struct ForceSensorAdvertisement: Equatable {
    let name: String?
    let serviceUUIDs: Set<UUID>
    let manufacturerData: [ForceSensorManufacturerData]

    init(
        name: String?,
        serviceUUIDs: Set<UUID>,
        manufacturerData: [ForceSensorManufacturerData] = []
    ) {
        self.name = name
        self.serviceUUIDs = serviceUUIDs
        self.manufacturerData = manufacturerData
    }
}

enum ForceSensorAdapter {
    case progressor(ProgressorProtocolAdapter)
    case pitchSix(PitchSixProtocolAdapter)

    var profile: ForceSensorProfile {
        switch self {
        case .progressor(let adapter): adapter.profile
        case .pitchSix(let adapter): adapter.profile
        }
    }

    var capabilities: Set<ForceSensorCapability> {
        switch self {
        case .progressor(let adapter): adapter.capabilities
        case .pitchSix(let adapter): adapter.capabilities
        }
    }

    var contract: ForceSensorBLEContract {
        switch self {
        case .progressor(let adapter): adapter.contract
        case .pitchSix(let adapter): adapter.contract
        }
    }

    var writeCharacteristic: ForceSensorBLECharacteristic {
        switch self {
        case .progressor(let adapter): adapter.writeCharacteristic
        case .pitchSix(let adapter): adapter.writeCharacteristic
        }
    }

    func matches(_ advertisement: ForceSensorAdvertisement) -> Bool {
        switch self {
        case .progressor(let adapter): adapter.matches(advertisement)
        case .pitchSix(let adapter): adapter.matches(advertisement)
        }
    }

    func payload(for command: ForceSensorCommand) -> Data {
        switch self {
        case .progressor(let adapter): adapter.payload(for: command)
        case .pitchSix(let adapter): adapter.payload(for: command)
        }
    }

    func decode(_ frame: Data, receivedAt: Date) -> [ForceSensorSample]? {
        switch self {
        case .progressor(let adapter):
            adapter.decode(frame, receivedAt: receivedAt)?.map(\.sample)
        case .pitchSix(let adapter):
            adapter.decode(frame, receivedAt: receivedAt)
        }
    }
}

enum ForceSensorAdapterRegistry {
    static let automaticProfiles: [ForceSensorProfile] = [.motherboard, .progressor, .pitchSix]

    static func adapter(for profile: ForceSensorProfile) -> ForceSensorAdapter? {
        switch profile {
        case .progressor, .genericProgressor:
            ProgressorProtocolAdapter(profile: profile).map(ForceSensorAdapter.progressor)
        case .pitchSix:
            PitchSixProtocolAdapter(profile: profile).map(ForceSensorAdapter.pitchSix)
        case .automatic, .motherboard, .whC06, .entralpi, .climbro, .genericWHC06:
            nil
        }
    }
}
