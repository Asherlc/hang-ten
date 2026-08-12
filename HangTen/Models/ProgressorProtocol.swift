import Foundation

enum ForceSensorCommand: CaseIterable {
    case tare
    case start
    case stop
}

struct ProgressorDecodedSample: Equatable {
    let sample: ForceSensorSample
    let deviceTimestampMicroseconds: UInt32
}

struct ProgressorProtocolAdapter {
    static let serviceUUID = UUID(uuidString: "7E4E1701-1EA6-40C9-9DCC-13D34FFEAD57")!
    static let notificationUUID = UUID(uuidString: "7E4E1702-1EA6-40C9-9DCC-13D34FFEAD57")!
    static let writeUUID = UUID(uuidString: "7E4E1703-1EA6-40C9-9DCC-13D34FFEAD57")!

    let profile: ForceSensorProfile

    init?(profile: ForceSensorProfile) {
        guard profile == .progressor || profile == .genericProgressor else { return nil }
        self.profile = profile
    }

    var capabilities: Set<ForceSensorCapability> {
        [.hardwareTare, .explicitStartStop]
    }

    var contract: ForceSensorBLEContract {
        ForceSensorBLEContract(
            serviceUUIDs: [Self.serviceUUID],
            notificationCharacteristics: [
                ForceSensorBLECharacteristic(
                    serviceUUID: Self.serviceUUID,
                    characteristicUUID: Self.notificationUUID
                )
            ]
        )
    }

    var writeCharacteristic: ForceSensorBLECharacteristic {
        ForceSensorBLECharacteristic(
            serviceUUID: Self.serviceUUID,
            characteristicUUID: Self.writeUUID
        )
    }

    func matches(_ advertisement: ForceSensorAdvertisement) -> Bool {
        switch profile {
        case .progressor:
            advertisement.name?.hasPrefix("Progressor") == true
        case .genericProgressor:
            advertisement.serviceUUIDs.contains(Self.serviceUUID)
        default:
            false
        }
    }

    func payload(for command: ForceSensorCommand) -> Data {
        switch command {
        case .tare: Data([0x64])
        case .start: Data([0x65])
        case .stop: Data([0x66])
        }
    }

    func decode(_ frame: Data, receivedAt: Date) -> [ProgressorDecodedSample]? {
        guard frame.count >= 2, frame[frame.startIndex] == 0x01 else { return nil }

        let payloadLength = Int(frame[frame.index(after: frame.startIndex)])
        let payload = frame.dropFirst(2)
        guard payload.count == payloadLength else { return nil }
        guard payload.count.isMultiple(of: 8) else { return nil }

        var samples: [ProgressorDecodedSample] = []
        samples.reserveCapacity(payload.count / 8)

        for offset in stride(from: 0, to: payload.count, by: 8) {
            let forceBits = UInt32(payload[offset])
                | UInt32(payload[offset + 1]) << 8
                | UInt32(payload[offset + 2]) << 16
                | UInt32(payload[offset + 3]) << 24
            let timestamp = UInt32(payload[offset + 4])
                | UInt32(payload[offset + 5]) << 8
                | UInt32(payload[offset + 6]) << 16
                | UInt32(payload[offset + 7]) << 24
            let force = Double(Float(bitPattern: forceBits))

            guard let sample = ForceSensorSample(
                value: force,
                unit: .kilogramsForce,
                receivedAt: receivedAt
            ) else {
                return nil
            }

            samples.append(
                ProgressorDecodedSample(
                    sample: sample,
                    deviceTimestampMicroseconds: timestamp
                )
            )
        }

        return samples
    }
}
