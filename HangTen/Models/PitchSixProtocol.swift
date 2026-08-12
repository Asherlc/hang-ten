import Foundation

struct PitchSixProtocolAdapter {
    static let forceServiceUUID = UUID(uuidString: "9A88D67F-8DF2-4AFE-9E0D-C2BBBE773DD0")!
    static let forceNotificationUUID = UUID(uuidString: "9A88D682-8DF2-4AFE-9E0D-C2BBBE773DD0")!
    static let modeServiceUUID = UUID(uuidString: "467A8516-6E39-11EB-9439-0242AC130002")!
    static let modeWriteUUID = UUID(uuidString: "467A8517-6E39-11EB-9439-0242AC130002")!

    let profile: ForceSensorProfile

    init?(profile: ForceSensorProfile) {
        guard profile == .pitchSix else { return nil }
        self.profile = profile
    }

    var capabilities: Set<ForceSensorCapability> {
        [.hardwareTare, .explicitStartStop]
    }

    var contract: ForceSensorBLEContract {
        ForceSensorBLEContract(
            serviceUUIDs: [Self.forceServiceUUID, Self.modeServiceUUID],
            notificationCharacteristics: [
                ForceSensorBLECharacteristic(
                    serviceUUID: Self.forceServiceUUID,
                    characteristicUUID: Self.forceNotificationUUID
                )
            ]
        )
    }

    var writeCharacteristic: ForceSensorBLECharacteristic {
        ForceSensorBLECharacteristic(
            serviceUUID: Self.modeServiceUUID,
            characteristicUUID: Self.modeWriteUUID
        )
    }

    func matches(_ advertisement: ForceSensorAdvertisement) -> Bool {
        advertisement.name == "Force Board"
    }

    func payload(for command: ForceSensorCommand) -> Data {
        switch command {
        case .start: Data([0x04])
        case .tare: Data([0x05])
        case .stop: Data([0x07])
        }
    }

    func decode(_ frame: Data, receivedAt: Date) -> [ForceSensorSample]? {
        guard frame.count >= 2 else { return nil }

        let headerStartIndex = frame.startIndex
        let sampleCount = Int(frame[headerStartIndex]) << 8
            | Int(frame[frame.index(after: headerStartIndex)])
        let (payloadByteCount, payloadLengthOverflowed) = sampleCount.multipliedReportingOverflow(by: 3)
        let (expectedFrameByteCount, frameLengthOverflowed) = payloadByteCount.addingReportingOverflow(2)
        guard sampleCount > 0,
              !payloadLengthOverflowed,
              !frameLengthOverflowed,
              frame.count == expectedFrameByteCount
        else {
            return nil
        }

        var samples: [ForceSensorSample] = []
        samples.reserveCapacity(sampleCount)

        for sampleIndex in 0..<sampleCount {
            let sampleStartIndex = frame.index(
                frame.startIndex,
                offsetBy: 2 + sampleIndex * 3
            )
            let sampleMiddleIndex = frame.index(after: sampleStartIndex)
            let sampleEndIndex = frame.index(after: sampleMiddleIndex)
            let pounds = Double(frame[sampleStartIndex]) * 32_768
                + Double(frame[sampleMiddleIndex]) * 256
                + Double(frame[sampleEndIndex])
            guard let sample = ForceSensorSample(
                value: pounds,
                unit: .poundsForce,
                receivedAt: receivedAt
            ) else {
                return nil
            }
            samples.append(sample)
        }

        return samples
    }
}
