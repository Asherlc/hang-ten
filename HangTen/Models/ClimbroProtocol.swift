import Foundation

struct ClimbroProtocolAdapter {
    static let uartServiceUUID = UUID(uuidString: "49535343-FE7D-4AE5-8FA9-9FAFD205E455")!
    static let notificationUUID = UUID(uuidString: "49535343-1E4D-4BD9-BA61-23C647249616")!
    static let txUUID = UUID(uuidString: "49535343-8841-43F4-A8D4-ECBE34729BB3")!
    static let controlPointUUID = UUID(uuidString: "49535343-4C8A-39B3-2F49-511CFF073B7E")!

    let profile: ForceSensorProfile

    init?(profile: ForceSensorProfile) {
        guard profile == .climbro else { return nil }
        self.profile = profile
    }

    var capabilities: Set<ForceSensorCapability> {
        []
    }

    var contract: ForceSensorBLEContract {
        ForceSensorBLEContract(
            serviceUUIDs: [Self.uartServiceUUID],
            notificationCharacteristics: [
                ForceSensorBLECharacteristic(
                    serviceUUID: Self.uartServiceUUID,
                    characteristicUUID: Self.notificationUUID
                )
            ]
        )
    }

    func matches(_ advertisement: ForceSensorAdvertisement) -> Bool {
        advertisement.name?.hasPrefix("Climbro") == true
    }

    var writeCharacteristic: ForceSensorBLECharacteristic? {
        nil
    }

    func payload(for command: ForceSensorCommand) -> Data? {
        nil
    }
}

struct ClimbroProtocolParser {
    enum State: Equatable {
        case waitingForMarker
        case battery
        case sensor
    }

    private(set) var state: State = .waitingForMarker
    private(set) var batteryPercentage: Double?

    mutating func decode(_ frame: Data, receivedAt: Date) -> [ForceSensorSample] {
        var samples: [ForceSensorSample] = []

        for byte in frame {
            switch byte {
            case 0xF0:
                state = .battery
            case 0xF5:
                state = .sensor
            default:
                switch state {
                case .waitingForMarker:
                    break
                case .battery:
                    batteryPercentage = 100 * (Double(byte) - 112) / 118
                case .sensor:
                    let value = byte == 0xF6 ? 36 : Double(byte)
                    if let sample = ForceSensorSample(
                        value: value,
                        unit: .kilogramsForce,
                        receivedAt: receivedAt
                    ) {
                        samples.append(sample)
                    }
                }
            }
        }

        return samples
    }
}
