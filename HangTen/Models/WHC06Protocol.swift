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
        advertisement.manufacturerData.contains { manufacturerData in
            manufacturerData.companyIdentifier == Self.companyIdentifier
        }
    }

    func payload(for command: ForceSensorCommand) -> Data? {
        nil
    }

    func decode(_ advertisement: ForceSensorAdvertisement, receivedAt: Date) -> [ForceSensorSample]? {
        guard let manufacturerData = advertisement.manufacturerData.first(where: { manufacturerData in
            manufacturerData.companyIdentifier == Self.companyIdentifier
        }) else {
            return nil
        }

        return decode(manufacturerData.payload, receivedAt: receivedAt)
    }

    private func decode(_ payload: Data, receivedAt: Date) -> [ForceSensorSample]? {
        guard payload.count >= 12 else { return nil }

        let highByteIndex = payload.index(payload.startIndex, offsetBy: 10)
        let lowByteIndex = payload.index(after: highByteIndex)
        let hundredthsOfKilogram = UInt16(payload[highByteIndex]) << 8
            | UInt16(payload[lowByteIndex])

        // Adaptation: upstream exposes kg; Hang Ten stores this as kgf pending vendor confirmation.
        guard let sample = ForceSensorSample(
            value: Double(hundredthsOfKilogram) / 100,
            unit: .kilogramsForce,
            receivedAt: receivedAt
        ) else {
            return nil
        }

        return [sample]
    }
}
