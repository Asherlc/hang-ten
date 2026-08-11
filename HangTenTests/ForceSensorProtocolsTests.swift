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
}
