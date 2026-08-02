import XCTest
@testable import HangTen

final class MotherboardProtocolTests: XCTestCase {
    func testParserBuffersFragmentsAndEmitsCompleteRawPacket() {
        let date = Date(timeIntervalSince1970: 42)
        var parser = MotherboardProtocolParser()
        XCTAssertEqual(parser.append(Data("34126400020100fe".utf8), receivedAt: date), [])

        let events = parser.append(Data("ffff030201000000\r\n".utf8), receivedAt: date)
        XCTAssertEqual(events, [.rawPacket(
            MotherboardRawPacket(sampleNumber: 0x1234, batteryValue: 0x0064, adcValues: [0x000102, -2, 0x010203, 0]),
            timestamp: date
        )])
    }

    func testParserHandlesCalibrationStreamAndDeviceErrors() {
        var parser = MotherboardProtocolParser()
        let data = Data("0,1,2.5,100\r\nStream:30\r\nError VAL\r\n".utf8)
        XCTAssertEqual(parser.append(data, receivedAt: Date(timeIntervalSince1970: 1)), [
            .calibration(MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: 2.5, adc: 100)),
            .streamStarted(rate: 30),
            .error("Error VAL")
        ])
    }

    func testCalibrationInterpolatesAndSubtractsPerSensorTare() {
        let calibration = MotherboardCalibration(rows: [
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 0, massKGF: 0, adc: 0),
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: 10, adc: 100)
        ])
        let packet = MotherboardRawPacket(sampleNumber: 1, batteryValue: 2, adcValues: [50, 0, 0, 0])
        let result = MotherboardProtocol.decode(
            packet,
            timestamp: Date(timeIntervalSince1970: 1),
            calibration: calibration,
            tareKGF: [1, 0, 0, 0]
        )
        XCTAssertEqual(result.sensorLoadsKGF[0], 4, accuracy: 0.0001)
        XCTAssertEqual(result.aggregateLoadKGF, 4, accuracy: 0.0001)
    }

    func testCalibrationSortsPointsAndExtrapolatesAtBothEnds() {
        let calibration = MotherboardCalibration(rows: [
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: 10, adc: 100),
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 0, massKGF: 0, adc: 0)
        ])

        XCTAssertEqual(calibration.massKGF(sensor: 0, adc: -50), -5)
        XCTAssertEqual(calibration.massKGF(sensor: 0, adc: 150), 15)
    }

    func testDecodeKeepsNegativeSensorLoadsButClampsAggregateToZero() {
        let calibration = MotherboardCalibration(rows: [
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 0, massKGF: 0, adc: 0),
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: 10, adc: 100)
        ])
        let packet = MotherboardRawPacket(sampleNumber: 1, batteryValue: 2, adcValues: [0, 0, 0, 0])
        let result = MotherboardProtocol.decode(
            packet,
            timestamp: Date(timeIntervalSince1970: 1),
            calibration: calibration,
            tareKGF: [1, 0, 0, 0]
        )

        XCTAssertEqual(result.sensorLoadsKGF, [-1, 0, 0, 0])
        XCTAssertEqual(result.aggregateLoadKGF, 0, accuracy: 0.0001)
    }

    func testProtocolUsesNordicUartUUIDsAndBuildsClampedStreamCommands() {
        XCTAssertEqual(MotherboardProtocol.serviceUUID.uuidString, "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        XCTAssertEqual(MotherboardProtocol.rxUUID.uuidString, "6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
        XCTAssertEqual(MotherboardProtocol.txUUID.uuidString, "6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
        XCTAssertEqual(MotherboardProtocol.command("C"), Data("C".utf8))
        XCTAssertEqual(MotherboardProtocol.streamCommand(rate: 30), Data("S30".utf8))
        XCTAssertEqual(MotherboardProtocol.streamCommand(rate: 0), Data("S1".utf8))
    }

    func testParserRejectsInvalidSensorAndMalformedHexFrames() {
        var parser = MotherboardProtocolParser()
        let data = Data("4,0,1,2\r\n34126400020100feffff0302010000000\r\n".utf8)

        XCTAssertEqual(parser.append(data, receivedAt: Date(timeIntervalSince1970: 1)), [])
    }
}
