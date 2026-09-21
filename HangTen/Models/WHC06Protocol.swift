import Foundation

struct WHC06ProtocolAdapter {
    static let companyIdentifier: UInt16 = 0x0100
    static let advertisementLivenessTimeout: TimeInterval = 10

    private static let advertisedName = "IF_B7"
    private static let minimumPayloadLength = 12
    private static let capacityKilogramsForce = 300.0

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

    func matchesForAutomaticSelection(
        _ advertisement: ForceSensorAdvertisement,
        advertisedLocalName: String? = nil
    ) -> Bool {
        guard profile == .whC06 else { return false }
        let hasKnownName = (advertisedLocalName ?? advertisement.name) == Self.advertisedName

        return advertisement.manufacturerData.contains { manufacturerData in
            guard accepts(manufacturerData) else { return false }
            return hasKnownName || Self.hasCapturedSignature(manufacturerData.payload)
        }
    }

    func payload(for command: ForceSensorCommand) -> Data? {
        nil
    }

    func decode(_ advertisement: ForceSensorAdvertisement, receivedAt: Date) -> [ForceSensorSample]? {
        for manufacturerData in advertisement.manufacturerData where accepts(manufacturerData) {
            if let samples = decode(manufacturerData.payload, receivedAt: receivedAt) {
                return samples
            }
        }

        return nil
    }

    private func decode(_ payload: Data, receivedAt: Date) -> [ForceSensorSample]? {
        guard payload.count >= Self.minimumPayloadLength else { return nil }

        let highByteIndex = payload.index(payload.startIndex, offsetBy: 10)
        let lowByteIndex = payload.index(after: highByteIndex)
        let hundredthsOfSourceUnit = UInt16(payload[highByteIndex]) << 8
            | UInt16(payload[lowByteIndex])

        let sourceValue = Double(hundredthsOfSourceUnit) / 100
        let unitCode: UInt8?
        if payload.count > 14 {
            let unitByteIndex = payload.index(payload.startIndex, offsetBy: 14)
            unitCode = payload[unitByteIndex] & 0x0F
        } else {
            unitCode = nil
        }

        let kilogramsForce: Double
        switch unitCode {
        case 0, 2:
            kilogramsForce = sourceValue * 0.453_592_37
        case 3:
            kilogramsForce = sourceValue * 6.350_293_18
        case 4:
            kilogramsForce = sourceValue * 0.5
        default:
            kilogramsForce = sourceValue
        }

        guard kilogramsForce <= Self.capacityKilogramsForce else { return nil }

        guard let sample = ForceSensorSample(
            value: kilogramsForce,
            unit: .kilogramsForce,
            receivedAt: receivedAt
        ) else {
            return nil
        }

        return [sample]
    }

    private func accepts(_ manufacturerData: ForceSensorManufacturerData) -> Bool {
        manufacturerData.companyIdentifier == Self.companyIdentifier
    }

    private static func hasCapturedSignature(_ payload: Data) -> Bool {
        guard payload.count >= 17 else { return false }
        let firstByteIndex = payload.startIndex
        let secondByteIndex = payload.index(after: firstByteIndex)
        return payload[firstByteIndex] == 0x02 && payload[secondByteIndex] == 0x03
    }
}
