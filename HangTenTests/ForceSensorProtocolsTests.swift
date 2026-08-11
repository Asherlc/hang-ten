import Foundation
import XCTest
@testable import HangTen

final class ForceSensorProtocolsTests: XCTestCase {
    func testAutomaticMatchingRecognizesNamedProfilesButNeverGenericProfiles() {
        XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "Progressor 123", manufacturerData: nil), .progressor)
        XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "Force Board", manufacturerData: nil), .pitchSix)
        XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "ENTRALPI", manufacturerData: nil), .entralpi)
        XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "Climbro 2", manufacturerData: nil), .climbro)
        XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "IF_B7", manufacturerData: Data([0, 1])), .whC06)
        XCTAssertNil(ForceSensorProfile.automaticMatch(name: "Unknown", manufacturerData: nil))
    }

    func testProgressorDecoderReadsLittleEndianFloatKilogramsAndTimestamp() throws {
        let receivedAt = Date(timeIntervalSince1970: 1)
        let data = Data([1, 8, 0, 0, 72, 65, 64, 226, 1, 0])

        let sample = try XCTUnwrap(ForceSensorDecoder.decode(data, profile: .progressor, receivedAt: receivedAt).first)

        XCTAssertEqual(sample.value, 12.5, accuracy: 0.0001)
        XCTAssertEqual(sample.unit, .kilogramsForce)
        XCTAssertEqual(sample.receivedAt, receivedAt)
    }

    func testPitchSixDecoderReadsBigEndianThreeBytePounds() throws {
        let sample = try XCTUnwrap(ForceSensorDecoder.decode(Data([0, 1, 0, 0, 22]), profile: .pitchSix, receivedAt: .now).first)

        XCTAssertEqual(sample.value, 22)
        XCTAssertEqual(sample.unit, .poundsForce)
    }

    func testWHC06DecoderReadsManufacturerBytesTenAndEleven() throws {
        var data = Data(repeating: 0, count: 12)
        data[10] = 0x04
        data[11] = 0xD2

        let sample = try XCTUnwrap(ForceSensorDecoder.decode(data, profile: .whC06, receivedAt: .now).first)

        XCTAssertEqual(sample.value, 12.34, accuracy: 0.0001)
        XCTAssertEqual(sample.unit, .kilogramsForce)
    }

    func testClimbroDecoderPreservesForceMarkerAcrossNotificationsWithPersistentState() throws {
        var decoder = ForceSensorDecoder()
        let receivedAt = Date(timeIntervalSince1970: 1)

        XCTAssertTrue(try ForceSensorDecoder.decode(Data([0xF5]), profile: .climbro, receivedAt: receivedAt, using: &decoder).isEmpty)

        let sample = try XCTUnwrap(ForceSensorDecoder.decode(Data([0xF6]), profile: .climbro, receivedAt: receivedAt, using: &decoder).first)

        XCTAssertEqual(sample.value, 36)
        XCTAssertEqual(sample.unit, .kilogramsForce)
        XCTAssertEqual(sample.receivedAt, receivedAt)
    }

    func testClimbroDecoderReadsBatteryAfterMarkerAcrossNotifications() throws {
        var decoder = ForceSensorDecoder()
        let receivedAt = Date(timeIntervalSince1970: 1)

        XCTAssertTrue(try ForceSensorDecoder.decode(Data([0xF0]), profile: .climbro, receivedAt: receivedAt, using: &decoder).isEmpty)

        let sample = try XCTUnwrap(ForceSensorDecoder.decode(Data([171]), profile: .climbro, receivedAt: receivedAt, using: &decoder).first)

        XCTAssertEqual(sample.value, 50)
        XCTAssertEqual(sample.unit, .batteryPercent)
        XCTAssertEqual(sample.receivedAt, receivedAt)
    }

    func testClimbroDecoderClampsBatteryPercentage() throws {
        var decoder = ForceSensorDecoder()
        let receivedAt = Date(timeIntervalSince1970: 1)

        _ = try ForceSensorDecoder.decode(Data([0xF0]), profile: .climbro, receivedAt: receivedAt, using: &decoder)
        let lowSample = try XCTUnwrap(ForceSensorDecoder.decode(Data([0]), profile: .climbro, receivedAt: receivedAt, using: &decoder).first)
        let highSample = try XCTUnwrap(ForceSensorDecoder.decode(Data([255]), profile: .climbro, receivedAt: receivedAt, using: &decoder).first)

        XCTAssertEqual(lowSample.value, 0)
        XCTAssertEqual(highSample.value, 100)
        XCTAssertEqual(lowSample.unit, .batteryPercent)
        XCTAssertEqual(highSample.unit, .batteryPercent)
    }

    func testProgressorDecoderRejectsNegativeFloatSamples() {
        let data = Data([1, 8, 0, 0, 128, 191, 0, 0, 0, 0])

        XCTAssertThrowsError(try ForceSensorDecoder.decode(data, profile: .progressor, receivedAt: .now)) { error in
            XCTAssertEqual(error as? ForceSensorDecoderError, .malformedPacket)
        }
    }

    func testProgressorDecoderRejectsNaNFloatSamples() {
        let data = Data([1, 8, 0, 0, 192, 127, 0, 0, 0, 0])

        XCTAssertThrowsError(try ForceSensorDecoder.decode(data, profile: .progressor, receivedAt: .now)) { error in
            XCTAssertEqual(error as? ForceSensorDecoderError, .malformedPacket)
        }
    }

    func testProgressorDecoderRejectsInfiniteFloatSamples() {
        let data = Data([1, 8, 0, 0, 128, 127, 0, 0, 0, 0])

        XCTAssertThrowsError(try ForceSensorDecoder.decode(data, profile: .progressor, receivedAt: .now)) { error in
            XCTAssertEqual(error as? ForceSensorDecoderError, .malformedPacket)
        }
    }

    func testProgressorDecoderRejectsMalformedTLVLength() {
        let data = Data([1, 8, 0, 0, 72, 65])

        XCTAssertThrowsError(try ForceSensorDecoder.decode(data, profile: .progressor, receivedAt: .now)) { error in
            XCTAssertEqual(error as? ForceSensorDecoderError, .malformedPacket)
        }
    }

    func testGenericProgressorExposesProgressorHardwareControlCapabilities() {
        XCTAssertEqual(ForceSensorProfile.genericProgressor.capabilities, [.hardwareTare, .explicitStartStop])
    }
}
