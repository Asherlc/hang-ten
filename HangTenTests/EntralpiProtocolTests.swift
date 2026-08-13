import Foundation
import XCTest
@testable import HangTen

final class EntralpiProtocolTests: XCTestCase {
    private let receivedAt = Date(timeIntervalSince1970: 4_680)

    func testExactCaseSensitiveNameMatchingHasNoServiceRequirement() throws {
        let adapter = try XCTUnwrap(EntralpiProtocolAdapter(profile: .entralpi))
        let unrelatedService = try XCTUnwrap(UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"))

        XCTAssertTrue(adapter.matches(ForceSensorAdvertisement(name: "ENTRALPI", serviceUUIDs: [])))
        XCTAssertTrue(adapter.matches(ForceSensorAdvertisement(name: "ENTRALPI", serviceUUIDs: [unrelatedService])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: "entralpi", serviceUUIDs: [])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: "Entralpi", serviceUUIDs: [])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: "ENTRALPI ", serviceUUIDs: [])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: nil, serviceUUIDs: [])))
        XCTAssertNil(EntralpiProtocolAdapter(profile: .progressor))
    }

    func testContractDeclaresServiceScopedNotificationsAndBatteryCapabilityOnly() throws {
        let adapter = try XCTUnwrap(EntralpiProtocolAdapter(profile: .entralpi))
        let deviceInfo = try XCTUnwrap(UUID(uuidString: "0000180A-0000-1000-8000-00805F9B34FB"))
        let battery = try XCTUnwrap(UUID(uuidString: "0000180F-0000-1000-8000-00805F9B34FB"))
        let vendorAttribute = try XCTUnwrap(UUID(uuidString: "F000FFC0-0451-4000-B000-000000000000"))
        let uart = try XCTUnwrap(UUID(uuidString: "0000FFF0-0000-1000-8000-00805F9B34FB"))
        let weightScale = try XCTUnwrap(UUID(uuidString: "0000181D-0000-1000-8000-00805F9B34FB"))
        let uartNotify = try XCTUnwrap(UUID(uuidString: "0000FFF4-0000-1000-8000-00805F9B34FB"))
        let overlappingFFF1 = try XCTUnwrap(UUID(uuidString: "0000FFF1-0000-1000-8000-00805F9B34FB"))
        let batteryLevel = try XCTUnwrap(UUID(uuidString: "00002A19-0000-1000-8000-00805F9B34FB"))

        XCTAssertEqual(adapter.contract.serviceUUIDs, [deviceInfo, battery, vendorAttribute, uart, weightScale])
        XCTAssertEqual(adapter.contract.notificationCharacteristics, [
            ForceSensorBLECharacteristic(serviceUUID: uart, characteristicUUID: uartNotify),
            ForceSensorBLECharacteristic(serviceUUID: weightScale, characteristicUUID: overlappingFFF1)
        ])
        XCTAssertEqual(
            adapter.batteryCharacteristic,
            ForceSensorBLECharacteristic(serviceUUID: battery, characteristicUUID: batteryLevel)
        )
        XCTAssertNil(adapter.writeCharacteristic)
        XCTAssertEqual(adapter.capabilities, [.batteryLevel])
    }

    func testDecoderReadsBigEndianHundredthsAndRoundsToOneDecimal() throws {
        let adapter = try XCTUnwrap(EntralpiProtocolAdapter(profile: .entralpi))

        let exact = try XCTUnwrap(adapter.decode(Data([0x04, 0xD2]), receivedAt: receivedAt))
        let roundsDown = try XCTUnwrap(adapter.decode(Data([0x00, 0x7B]), receivedAt: receivedAt))
        let roundsUp = try XCTUnwrap(adapter.decode(Data([0x00, 0x7D]), receivedAt: receivedAt))

        XCTAssertEqual(exact, [ForceSensorSample(value: 12.3, unit: .kilogramsForce, receivedAt: receivedAt)])
        XCTAssertEqual(roundsDown, [ForceSensorSample(value: 1.2, unit: .kilogramsForce, receivedAt: receivedAt)])
        XCTAssertEqual(roundsUp, [ForceSensorSample(value: 1.3, unit: .kilogramsForce, receivedAt: receivedAt)])
    }

    func testDecoderRejectsTruncatedPayloadsAndNeverEmitsPartialForce() throws {
        let adapter = try XCTUnwrap(EntralpiProtocolAdapter(profile: .entralpi))

        XCTAssertNil(adapter.decode(Data(), receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(Data([0x04]), receivedAt: receivedAt))
    }

    func testDecoderReadsBytesFromANonzeroIndexDataSlice() throws {
        let adapter = try XCTUnwrap(EntralpiProtocolAdapter(profile: .entralpi))
        let packet = Data([0xFF, 0xFF, 0x04, 0xD2])
        let frame = packet[packet.index(packet.startIndex, offsetBy: 2)...]

        let decoded = try XCTUnwrap(adapter.decode(frame, receivedAt: receivedAt))

        XCTAssertEqual(decoded, [ForceSensorSample(value: 12.3, unit: .kilogramsForce, receivedAt: receivedAt)])
    }

    func testAdapterHasNoDeviceCommands() throws {
        let adapter = try XCTUnwrap(EntralpiProtocolAdapter(profile: .entralpi))

        XCTAssertNil(adapter.payload(for: .tare))
        XCTAssertNil(adapter.payload(for: .start))
        XCTAssertNil(adapter.payload(for: .stop))
    }
}
