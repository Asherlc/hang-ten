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

    func testParserAcceptsOneEmptyTrailingCalibrationField() {
        var parser = MotherboardProtocolParser()
        let date = Date(timeIntervalSince1970: 1)
        let data = Data("0,0,1,0,\r\n0,0,1,0,extra\r\n0,0,1,0,,\r\n".utf8)

        XCTAssertEqual(parser.append(data, receivedAt: date), [
            .calibration(MotherboardCalibrationRow(sensor: 0, calibrationPoint: 0, massKGF: 1, adc: 0))
        ])
    }

    func testCalibrationInterpolatesAndSubtractsPerSensorTare() {
        let calibration = MotherboardCalibration(rows: [
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 0, massKGF: 0, adc: 0),
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: 10, adc: 100),
            MotherboardCalibrationRow(sensor: 1, calibrationPoint: 0, massKGF: 0, adc: 0),
            MotherboardCalibrationRow(sensor: 1, calibrationPoint: 1, massKGF: 10, adc: 100),
            MotherboardCalibrationRow(sensor: 2, calibrationPoint: 0, massKGF: 0, adc: 0),
            MotherboardCalibrationRow(sensor: 2, calibrationPoint: 1, massKGF: 10, adc: 100),
            MotherboardCalibrationRow(sensor: 3, calibrationPoint: 0, massKGF: 0, adc: 0),
            MotherboardCalibrationRow(sensor: 3, calibrationPoint: 1, massKGF: 10, adc: 100)
        ])
        let timestamp = Date(timeIntervalSince1970: 1)
        let packet = MotherboardRawPacket(sampleNumber: 1, batteryValue: 2, adcValues: [50, -12, 100, 0])
        let result = MotherboardProtocol.decode(
            packet,
            timestamp: timestamp,
            calibration: calibration,
            tareKGF: [1, 0, 0, 0]
        )
        XCTAssertEqual(result.timestamp, timestamp)
        XCTAssertEqual(result.sampleNumber, packet.sampleNumber)
        XCTAssertEqual(result.batteryValue, packet.batteryValue)
        XCTAssertEqual(result.rawADCValues, packet.adcValues)
        XCTAssertEqual(result.sensorLoadsKGF, [4, 0, 10, 0])
        XCTAssertEqual(result.aggregateLoadKGF, 14, accuracy: 0.0001)
    }

    func testCalibrationSortsPointsAndClampsAtBothEndpoints() {
        let calibration = MotherboardCalibration(rows: [
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: 10, adc: 100),
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 0, massKGF: 0, adc: 0)
        ])

        XCTAssertEqual(calibration.massKGF(sensor: 0, adc: -50), 0)
        XCTAssertEqual(calibration.massKGF(sensor: 0, adc: 150), 10)
    }

    func testParserRejectsAndResetsAnOversizedUnterminatedFrame() {
        var parser = MotherboardProtocolParser(maximumBufferSize: 8)
        let date = Date(timeIntervalSince1970: 1)

        XCTAssertEqual(parser.append(Data("123456789".utf8), receivedAt: date), [
            .error("Motherboard response exceeded the receive buffer limit.")
        ])
        XCTAssertEqual(parser.append(Data("Stream:30\r\n".utf8), receivedAt: date), [
            .streamStarted(rate: 30)
        ])
    }

    func testParserRejectsOversizedTerminatedFrameAndPreservesFollowingFrame() {
        var parser = MotherboardProtocolParser(maximumBufferSize: 9)
        let date = Date(timeIntervalSince1970: 1)

        let events = parser.append(Data("1234567890\r\nStream:30\r\n".utf8), receivedAt: date)

        XCTAssertEqual(events, [
            .error("Motherboard response exceeded the receive buffer limit."),
            .streamStarted(rate: 30)
        ])
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

    func testDecodeSaturatesOverflowingFiniteCalibrationAndRemainsJSONEncodable() throws {
        let calibration = MotherboardCalibration(rows: [
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 0, massKGF: .greatestFiniteMagnitude, adc: 0),
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: -.greatestFiniteMagnitude, adc: 2)
        ])
        let packet = MotherboardRawPacket(sampleNumber: 1, batteryValue: 2, adcValues: [1, 0, 0, 0])

        let result = MotherboardProtocol.decode(
            packet,
            timestamp: Date(timeIntervalSince1970: 1),
            calibration: calibration,
            tareKGF: []
        )

        XCTAssertEqual(result.rawADCValues, [1, 0, 0, 0])
        XCTAssertTrue(result.sensorLoadsKGF.allSatisfy(\.isFinite))
        XCTAssertTrue(result.aggregateLoadKGF.isFinite)
        XCTAssertNoThrow(try JSONEncoder().encode(result))
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
