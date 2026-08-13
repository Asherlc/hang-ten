import Foundation
import XCTest
@testable import HangTen

final class ClimbroProtocolTests: XCTestCase {
    private let receivedAt = Date(timeIntervalSince1970: 3_579)

    func testParserStateTransitionsArePreservedAcrossNotifications() throws {
        var parser = ClimbroProtocolParser()

        XCTAssertEqual(parser.state, .waitingForMarker)
        XCTAssertTrue(parser.decode(Data([0xF5]), receivedAt: receivedAt).isEmpty)
        XCTAssertEqual(parser.state, .sensor)

        XCTAssertEqual(parser.decode(Data([11]), receivedAt: receivedAt), [
            ForceSensorSample(value: 11, unit: .kilogramsForce, receivedAt: receivedAt)
        ])
        XCTAssertTrue(parser.decode(Data([0xF0]), receivedAt: receivedAt).isEmpty)
        XCTAssertEqual(parser.state, .battery)

        XCTAssertTrue(parser.decode(Data([171]), receivedAt: receivedAt).isEmpty)
        XCTAssertEqual(try XCTUnwrap(parser.batteryPercentage), 50, accuracy: 0.000_001)
        XCTAssertEqual(parser.state, .battery)
    }

    func testParserMapsSensorModeF6ToExactly36KilogramsForce() {
        var parser = ClimbroProtocolParser()
        XCTAssertTrue(parser.decode(Data([0xF5]), receivedAt: receivedAt).isEmpty)

        XCTAssertEqual(parser.decode(Data([0xF6]), receivedAt: receivedAt), [
            ForceSensorSample(value: 36, unit: .kilogramsForce, receivedAt: receivedAt)
        ])
    }

    func testParserMapsSensorModeBytesDirectlyAsUnsignedKilogramsForce() {
        var parser = ClimbroProtocolParser()
        XCTAssertTrue(parser.decode(Data([0xF5]), receivedAt: receivedAt).isEmpty)

        XCTAssertEqual(parser.decode(Data([0, 1, 200]), receivedAt: receivedAt), [
            ForceSensorSample(value: 0, unit: .kilogramsForce, receivedAt: receivedAt),
            ForceSensorSample(value: 1, unit: .kilogramsForce, receivedAt: receivedAt),
            ForceSensorSample(value: 200, unit: .kilogramsForce, receivedAt: receivedAt)
        ])
    }

    func testParserUsesRawUnclampedBatteryBytesWithoutApplyingSensorSentinel() throws {
        var parser = ClimbroProtocolParser()

        XCTAssertTrue(parser.decode(Data([0xF0, 111]), receivedAt: receivedAt).isEmpty)
        XCTAssertEqual(try XCTUnwrap(parser.batteryPercentage), -0.847_457_627, accuracy: 0.000_001)

        XCTAssertTrue(parser.decode(Data([0xF6]), receivedAt: receivedAt).isEmpty)
        XCTAssertEqual(try XCTUnwrap(parser.batteryPercentage), 113.559_322_034, accuracy: 0.000_001)
    }

    func testParserSuppressesBytesBeforeFirstMarker() {
        var parser = ClimbroProtocolParser()

        XCTAssertTrue(parser.decode(Data([10, 20, 0xF6]), receivedAt: receivedAt).isEmpty)
        XCTAssertEqual(parser.state, .waitingForMarker)
        XCTAssertNil(parser.batteryPercentage)
    }

    func testAdapterUsesAuditedNamePrefixAndUartNotificationContractOnly() throws {
        let adapter = try XCTUnwrap(ClimbroProtocolAdapter(profile: .climbro))
        let uart = try XCTUnwrap(UUID(uuidString: "49535343-FE7D-4AE5-8FA9-9FAFD205E455"))
        let notification = try XCTUnwrap(UUID(uuidString: "49535343-1E4D-4BD9-BA61-23C647249616"))
        let unrelatedService = try XCTUnwrap(UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"))

        XCTAssertEqual(adapter.capabilities, [])
        XCTAssertEqual(adapter.contract.serviceUUIDs, [uart])
        XCTAssertEqual(adapter.contract.notificationCharacteristics, [
            ForceSensorBLECharacteristic(serviceUUID: uart, characteristicUUID: notification)
        ])
        XCTAssertTrue(adapter.matches(ForceSensorAdvertisement(name: "Climbro Mini", serviceUUIDs: [])))
        XCTAssertTrue(adapter.matches(ForceSensorAdvertisement(name: "Climbro", serviceUUIDs: [unrelatedService])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: "CLIMBRO", serviceUUIDs: [uart])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: nil, serviceUUIDs: [])))
        XCTAssertNil(ClimbroProtocolAdapter(profile: .progressor))
    }

    func testAdapterDeclaresTxAndControlPointUUIDsWithoutExposingWritesOrCommands() throws {
        let adapter = try XCTUnwrap(ClimbroProtocolAdapter(profile: .climbro))
        let tx = try XCTUnwrap(UUID(uuidString: "49535343-8841-43F4-A8D4-ECBE34729BB3"))
        let controlPoint = try XCTUnwrap(UUID(uuidString: "49535343-4C8A-39B3-2F49-511CFF073B7E"))

        XCTAssertEqual(ClimbroProtocolAdapter.txUUID, tx)
        XCTAssertEqual(ClimbroProtocolAdapter.controlPointUUID, controlPoint)
        XCTAssertNil(adapter.writeCharacteristic)

        for command in ForceSensorCommand.allCases {
            XCTAssertNil(adapter.payload(for: command))
        }
    }
}
