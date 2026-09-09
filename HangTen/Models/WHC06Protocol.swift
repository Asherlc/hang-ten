import Foundation

struct WHC06ProtocolAdapter {
    static let companyIdentifier: UInt16 = 0x0100
    static let advertisementLivenessTimeout: TimeInterval = 10

    let profile: ForceSensorProfile

    init?(profile: ForceSensorProfile) {
        guard profile == .whC06 || profile == .genericWHC06 else { return nil }
        self.profile = profile
    }

    var capabilities: Set<ForceSensorCapability> {
        []
    }

    var contract: ForceSensorBLEContract? {
        nil
    }

    var writeCharacteristic: ForceSensorBLECharacteristic? {
        nil
    }

    func matches(_ advertisement: ForceSensorAdvertisement) -> Bool {
        advertisement.manufacturerData.contains(where: accepts)
    }

    func payload(for command: ForceSensorCommand) -> Data? {
        nil
    }

    func decode(_ advertisement: ForceSensorAdvertisement, receivedAt: Date) -> [ForceSensorSample]? {
        guard let manufacturerData = advertisement.manufacturerData.first(where: accepts) else {
            return nil
        }

        return decode(manufacturerData.payload, receivedAt: receivedAt)
    }

    private func decode(_ payload: Data, receivedAt: Date) -> [ForceSensorSample]? {
        guard payload.count >= 15 else { return nil }

        let highByteIndex = payload.index(payload.startIndex, offsetBy: 10)
        let lowByteIndex = payload.index(after: highByteIndex)
        let hundredthsOfSourceUnit = UInt16(payload[highByteIndex]) << 8
            | UInt16(payload[lowByteIndex])
        let unitByteIndex = payload.index(payload.startIndex, offsetBy: 14)
        let sourceUnit: ForceSensorSourceUnit
        switch payload[unitByteIndex] & 0x0F {
        case 1:
            sourceUnit = .kilogramsForce
        case 2:
            sourceUnit = .poundsForce
        default:
            return nil
        }

        guard let sample = ForceSensorSample(
            value: Double(hundredthsOfSourceUnit) / 100,
            unit: sourceUnit,
            receivedAt: receivedAt
        ) else {
            return nil
        }

        return [sample]
    }

    private func accepts(_ manufacturerData: ForceSensorManufacturerData) -> Bool {
        guard manufacturerData.companyIdentifier == Self.companyIdentifier else { return false }
        guard profile == .whC06 else { return true }
        return Self.isNamedWHC06Payload(manufacturerData.payload)
    }

    private static func isNamedWHC06Payload(_ payload: Data) -> Bool {
        guard payload.count == 17 else { return false }
        let firstByteIndex = payload.startIndex
        let secondByteIndex = payload.index(after: firstByteIndex)
        return payload[firstByteIndex] == 0x02 && payload[secondByteIndex] == 0x03
    }
}
