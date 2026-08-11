import Foundation

enum ForceSensorCapability: Hashable {
    case hardwareTare
    case explicitStartStop
    case batteryLevel
}

struct ForceSensorBLEContract: Equatable {
    let serviceUUID: UUID?
    let notifyCharacteristicUUID: UUID?
    let writeServiceUUID: UUID?
    let writeCharacteristicUUID: UUID?
    let tareCharacteristicUUID: UUID?
    let batteryServiceUUID: UUID?
    let batteryCharacteristicUUID: UUID?
    let commands: [ForceSensorCommand: Data]

    static let none = ForceSensorBLEContract(
        serviceUUID: nil,
        notifyCharacteristicUUID: nil,
        writeServiceUUID: nil,
        writeCharacteristicUUID: nil,
        tareCharacteristicUUID: nil,
        batteryServiceUUID: nil,
        batteryCharacteristicUUID: nil,
        commands: [:]
    )
}

enum ForceSensorCommand: Hashable {
    case tare
    case start
    case stop
}

struct ForceSensorAdvertisement: Equatable {
    let name: String?
    let manufacturerData: Data?
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

    var id: String { rawValue }

    var capabilities: Set<ForceSensorCapability> {
        switch self {
        case .progressor, .genericProgressor, .pitchSix:
            [.hardwareTare, .explicitStartStop]
        case .entralpi, .climbro:
            [.batteryLevel]
        case .automatic, .motherboard, .whC06, .genericWHC06:
            []
        }
    }

    var bleContract: ForceSensorBLEContract {
        switch self {
        case .progressor, .genericProgressor:
            ForceSensorBLEContract(
                serviceUUID: ForceSensorProfile.uuid("7E4E1701-1EA6-40C9-9DCC-13D34FFEAD57"),
                notifyCharacteristicUUID: ForceSensorProfile.uuid("7E4E1702-1EA6-40C9-9DCC-13D34FFEAD57"),
                writeServiceUUID: ForceSensorProfile.uuid("7E4E1701-1EA6-40C9-9DCC-13D34FFEAD57"),
                writeCharacteristicUUID: ForceSensorProfile.uuid("7E4E1703-1EA6-40C9-9DCC-13D34FFEAD57"),
                tareCharacteristicUUID: nil,
                batteryServiceUUID: nil,
                batteryCharacteristicUUID: nil,
                commands: [.tare: Data([0x64]), .start: Data([0x65]), .stop: Data([0x66])]
            )
        case .pitchSix:
            ForceSensorBLEContract(
                serviceUUID: ForceSensorProfile.uuid("9A88D67F-8DF2-4AFE-9E0D-C2BBBE773DD0"),
                notifyCharacteristicUUID: ForceSensorProfile.uuid("9A88D682-8DF2-4AFE-9E0D-C2BBBE773DD0"),
                writeServiceUUID: ForceSensorProfile.uuid("467A8516-6E39-11EB-9439-0242AC130002"),
                writeCharacteristicUUID: ForceSensorProfile.uuid("467A8517-6E39-11EB-9439-0242AC130002"),
                tareCharacteristicUUID: ForceSensorProfile.uuid("9A88D683-8DF2-4AFE-9E0D-C2BBBE773DD0"),
                batteryServiceUUID: nil,
                batteryCharacteristicUUID: nil,
                commands: [.start: Data([0x04]), .tare: Data([0x05]), .stop: Data([0x07])]
            )
        case .entralpi:
            ForceSensorBLEContract(
                serviceUUID: ForceSensorProfile.uuid("0000FFF0-0000-1000-8000-00805F9B34FB"),
                notifyCharacteristicUUID: ForceSensorProfile.uuid("0000FFF1-0000-1000-8000-00805F9B34FB"),
                writeServiceUUID: nil,
                writeCharacteristicUUID: nil,
                tareCharacteristicUUID: nil,
                batteryServiceUUID: ForceSensorProfile.uuid("0000180F-0000-1000-8000-00805F9B34FB"),
                batteryCharacteristicUUID: ForceSensorProfile.uuid("00002A19-0000-1000-8000-00805F9B34FB"),
                commands: [:]
            )
        case .climbro:
            ForceSensorBLEContract(
                serviceUUID: ForceSensorProfile.uuid("49535343-FE7D-4AE5-8FA9-9FAFD205E455"),
                notifyCharacteristicUUID: ForceSensorProfile.uuid("49535343-1E4D-4BD9-BA61-23C647249616"),
                writeServiceUUID: nil,
                writeCharacteristicUUID: nil,
                tareCharacteristicUUID: nil,
                batteryServiceUUID: nil,
                batteryCharacteristicUUID: nil,
                commands: [:]
            )
        case .automatic, .motherboard, .whC06, .genericWHC06:
            .none
        }
    }

    static func automaticMatch(name: String?, manufacturerData: Data?) -> ForceSensorProfile? {
        let advertisement = ForceSensorAdvertisement(name: name, manufacturerData: manufacturerData)
        if advertisement.name?.hasPrefix("Progressor") == true { return .progressor }
        if advertisement.name == "Force Board" { return .pitchSix }
        if advertisement.name == "ENTRALPI" { return .entralpi }
        if advertisement.name?.hasPrefix("Climbro") == true { return .climbro }
        if advertisement.manufacturerData?.starts(with: [0x00, 0x01]) == true { return .whC06 }
        return nil
    }

    private static func uuid(_ value: String) -> UUID {
        UUID(uuidString: value)!
    }
}

enum ForceSensorSourceUnit: Equatable {
    case kilogramsForce
    case poundsForce
    case batteryPercent
}

struct ForceSensorDecodedSample: Equatable {
    let value: Double
    let unit: ForceSensorSourceUnit
    let receivedAt: Date
}

enum ForceSensorDecoderError: Error, Equatable {
    case malformedPacket
}

struct ForceSensorDecoder {
    private enum ClimbroMarker {
        case battery
        case force
    }

    private var climbroMarker: ClimbroMarker?

    static func decode(_ data: Data, profile: ForceSensorProfile, receivedAt: Date) throws -> [ForceSensorDecodedSample] {
        var decoder = ForceSensorDecoder()
        return try decoder.decode(data, profile: profile, receivedAt: receivedAt)
    }

    static func decode(
        _ data: Data,
        profile: ForceSensorProfile,
        receivedAt: Date,
        using decoder: inout ForceSensorDecoder
    ) throws -> [ForceSensorDecodedSample] {
        try decoder.decode(data, profile: profile, receivedAt: receivedAt)
    }

    mutating func decode(_ data: Data, profile: ForceSensorProfile, receivedAt: Date) throws -> [ForceSensorDecodedSample] {
        switch profile {
        case .progressor, .genericProgressor:
            return try decodeProgressor(data, receivedAt: receivedAt)
        case .pitchSix:
            return try decodePitchSix(data, receivedAt: receivedAt)
        case .whC06, .genericWHC06:
            return try decodeWHC06(data, receivedAt: receivedAt)
        case .entralpi:
            return try decodeEntralpi(data, receivedAt: receivedAt)
        case .climbro:
            return decodeClimbro(data, receivedAt: receivedAt)
        case .automatic, .motherboard:
            return []
        }
    }

    private func decodeProgressor(_ data: Data, receivedAt: Date) throws -> [ForceSensorDecodedSample] {
        guard data.count >= 2, data[0] == 1 else { throw ForceSensorDecoderError.malformedPacket }
        let payloadLength = Int(data[1])
        guard payloadLength % 8 == 0, data.count == payloadLength + 2 else { throw ForceSensorDecoderError.malformedPacket }

        return try stride(from: 2, to: data.count, by: 8).map { index in
            let bits = UInt32(data[index])
                | UInt32(data[index + 1]) << 8
                | UInt32(data[index + 2]) << 16
                | UInt32(data[index + 3]) << 24
            let value = Double(Float32(bitPattern: bits))
            guard value.isFinite, value >= 0 else { throw ForceSensorDecoderError.malformedPacket }
            return ForceSensorDecodedSample(value: value, unit: .kilogramsForce, receivedAt: receivedAt)
        }
    }

    private func decodePitchSix(_ data: Data, receivedAt: Date) throws -> [ForceSensorDecodedSample] {
        guard data.count >= 2 else { throw ForceSensorDecoderError.malformedPacket }
        let count = Int(data[0]) << 8 | Int(data[1])
        guard data.count == 2 + count * 3 else { throw ForceSensorDecoderError.malformedPacket }

        return stride(from: 2, to: data.count, by: 3).map { index in
            let value = Double(Int(data[index]) << 16 | Int(data[index + 1]) << 8 | Int(data[index + 2]))
            return ForceSensorDecodedSample(value: value, unit: .poundsForce, receivedAt: receivedAt)
        }
    }

    private func decodeWHC06(_ data: Data, receivedAt: Date) throws -> [ForceSensorDecodedSample] {
        guard data.count >= 12 else { throw ForceSensorDecoderError.malformedPacket }
        let value = Double(Int(data[10]) << 8 | Int(data[11])) / 100
        return [ForceSensorDecodedSample(value: value, unit: .kilogramsForce, receivedAt: receivedAt)]
    }

    private func decodeEntralpi(_ data: Data, receivedAt: Date) throws -> [ForceSensorDecodedSample] {
        guard data.count >= 2 else { throw ForceSensorDecoderError.malformedPacket }
        let value = Double(Int(data[0]) << 8 | Int(data[1])) / 100
        return [ForceSensorDecodedSample(value: value, unit: .kilogramsForce, receivedAt: receivedAt)]
    }

    private mutating func decodeClimbro(_ data: Data, receivedAt: Date) -> [ForceSensorDecodedSample] {
        data.reduce(into: []) { samples, byte in
            switch byte {
            case 0xF0:
                climbroMarker = .battery
            case 0xF5:
                climbroMarker = .force
            default:
                switch climbroMarker {
                case .force:
                    let value = byte == 0xF6 ? 36 : Double(byte)
                    samples.append(ForceSensorDecodedSample(value: value, unit: .kilogramsForce, receivedAt: receivedAt))
                case .battery:
                    let value = min(max((Double(byte) - 112) * 100 / 118, 0), 100)
                    samples.append(ForceSensorDecodedSample(value: value, unit: .batteryPercent, receivedAt: receivedAt))
                case nil:
                    return
                }
            }
        }
    }
}
