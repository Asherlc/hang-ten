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

        let sampleCount = Int(frame[frame.startIndex]) << 8
            | Int(frame[frame.index(after: frame.startIndex)])
        guard (1...6).contains(sampleCount), frame.count == 2 + sampleCount * 3 else {
            return nil
        }

        var samples: [ForceSensorSample] = []
        samples.reserveCapacity(sampleCount)

        for sampleIndex in 0..<sampleCount {
            let offset = 2 + sampleIndex * 3
            let pounds = Double(frame[offset]) * 32_768
                + Double(frame[offset + 1]) * 256
                + Double(frame[offset + 2])
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
