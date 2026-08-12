import Foundation

struct EntralpiProtocolAdapter {
    static let deviceInfoServiceUUID = UUID(uuidString: "0000180A-0000-1000-8000-00805F9B34FB")!
    static let batteryServiceUUID = UUID(uuidString: "0000180F-0000-1000-8000-00805F9B34FB")!
    static let vendorGenericAttributeServiceUUID = UUID(uuidString: "F000FFC0-0451-4000-B000-000000000000")!
    static let uartServiceUUID = UUID(uuidString: "0000FFF0-0000-1000-8000-00805F9B34FB")!
    static let weightScaleServiceUUID = UUID(uuidString: "0000181D-0000-1000-8000-00805F9B34FB")!
    static let uartNotificationUUID = UUID(uuidString: "0000FFF4-0000-1000-8000-00805F9B34FB")!
    static let weightScaleNotificationUUID = UUID(uuidString: "0000FFF1-0000-1000-8000-00805F9B34FB")!
    static let batteryLevelUUID = UUID(uuidString: "00002A19-0000-1000-8000-00805F9B34FB")!

    let profile: ForceSensorProfile

    init?(profile: ForceSensorProfile) {
        guard profile == .entralpi else { return nil }
        self.profile = profile
    }

    var capabilities: Set<ForceSensorCapability> {
        [.batteryLevel]
    }

    var contract: ForceSensorBLEContract {
        ForceSensorBLEContract(
            serviceUUIDs: [
                Self.deviceInfoServiceUUID,
                Self.batteryServiceUUID,
                Self.vendorGenericAttributeServiceUUID,
                Self.uartServiceUUID,
                Self.weightScaleServiceUUID
            ],
            notificationCharacteristics: [
                ForceSensorBLECharacteristic(
                    serviceUUID: Self.uartServiceUUID,
                    characteristicUUID: Self.uartNotificationUUID
                ),
                ForceSensorBLECharacteristic(
                    serviceUUID: Self.weightScaleServiceUUID,
                    characteristicUUID: Self.weightScaleNotificationUUID
                )
            ]
        )
    }

    var batteryCharacteristic: ForceSensorBLECharacteristic {
        ForceSensorBLECharacteristic(
            serviceUUID: Self.batteryServiceUUID,
            characteristicUUID: Self.batteryLevelUUID
        )
    }

    var writeCharacteristic: ForceSensorBLECharacteristic? {
        nil
    }

    func matches(_ advertisement: ForceSensorAdvertisement) -> Bool {
        advertisement.name == "ENTRALPI"
    }

    func payload(for command: ForceSensorCommand) -> Data? {
        nil
    }

    func decode(_ frame: Data, receivedAt: Date) -> [ForceSensorSample]? {
        guard frame.count >= 2 else { return nil }

        let highByteIndex = frame.startIndex
        let lowByteIndex = frame.index(after: highByteIndex)
        let hundredthsOfKilogram = UInt16(frame[highByteIndex]) << 8
            | UInt16(frame[lowByteIndex])
        let kilograms = (Double(hundredthsOfKilogram) / 100 * 10).rounded() / 10

        // Adaptation: upstream exposes kg; Hang Ten stores force samples as kgf pending vendor confirmation.
        guard let sample = ForceSensorSample(
            value: kilograms,
            unit: .kilogramsForce,
            receivedAt: receivedAt
        ) else {
            return nil
        }

        return [sample]
    }
}
