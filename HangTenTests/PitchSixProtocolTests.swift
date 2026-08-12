import Foundation
import XCTest
@testable import HangTen

final class PitchSixProtocolTests: XCTestCase {
    private let receivedAt = Date(timeIntervalSince1970: 2_468)

    func testDecoderSupportsEveryDocumentedSampleCount() throws {
        let adapter = try XCTUnwrap(PitchSixProtocolAdapter(profile: .pitchSix))
        let frames = [
            Data([0x00, 0x01, 0x00, 0x00, 0x01]),
            Data([0x00, 0x02, 0x00, 0x00, 0x01, 0x00, 0x00, 0x02]),
            Data([0x00, 0x03, 0x00, 0x00, 0x01, 0x00, 0x00, 0x02, 0x00, 0x00, 0x03]),
            Data([0x00, 0x04, 0x00, 0x00, 0x01, 0x00, 0x00, 0x02, 0x00, 0x00, 0x03, 0x00, 0x00, 0x04]),
            Data([0x00, 0x05, 0x00, 0x00, 0x01, 0x00, 0x00, 0x02, 0x00, 0x00, 0x03, 0x00, 0x00, 0x04, 0x00, 0x00, 0x05]),
            Data([0x00, 0x06, 0x00, 0x00, 0x01, 0x00, 0x00, 0x02, 0x00, 0x00, 0x03, 0x00, 0x00, 0x04, 0x00, 0x00, 0x05, 0x00, 0x00, 0x06])
        ]

        for (index, frame) in frames.enumerated() {
            let decoded = try XCTUnwrap(adapter.decode(frame, receivedAt: receivedAt))

            XCTAssertEqual(decoded.count, index + 1)
            XCTAssertEqual(decoded.last?.kilogramsForce ?? -1, Double(index + 1) / 2.20462262185, accuracy: 0.000_001)
            XCTAssertEqual(decoded.last?.receivedAt, receivedAt)
        }
    }

    func testDecoderUsesPublishedMostSignificantByteWeightingAndPoundConversion() throws {
        let adapter = try XCTUnwrap(PitchSixProtocolAdapter(profile: .pitchSix))
        let frame = Data([0x00, 0x02, 0x01, 0x00, 0x00, 0x00, 0x01, 0x02])

        let decoded = try XCTUnwrap(adapter.decode(frame, receivedAt: receivedAt))

        XCTAssertEqual(decoded[0].kilogramsForce, 32_768 / 2.20462262185, accuracy: 0.000_001)
        XCTAssertEqual(decoded[1].kilogramsForce, 258 / 2.20462262185, accuracy: 0.000_001)
    }

    func testDecoderRejectsMalformedCountsAndLengths() throws {
        let adapter = try XCTUnwrap(PitchSixProtocolAdapter(profile: .pitchSix))

        XCTAssertNil(adapter.decode(Data(), receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(Data([0x00]), receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(Data([0x00, 0x00]), receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(Data([0x00, 0x07]), receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(Data([0x00, 0x01, 0x00, 0x00]), receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(Data([0x00, 0x01, 0x00, 0x00, 0x01, 0xFF]), receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(Data([0x00, 0x02, 0x00, 0x00, 0x01]), receivedAt: receivedAt))
    }

    func testDecoderRejectsEntireFrameWhenLaterRecordIsTruncated() throws {
        let adapter = try XCTUnwrap(PitchSixProtocolAdapter(profile: .pitchSix))
        let validFirstTruncatedSecond = Data([
            0x00, 0x02,
            0x00, 0x00, 0x01,
            0x00, 0x02
        ])

        XCTAssertNil(adapter.decode(validFirstTruncatedSecond, receivedAt: receivedAt))
    }

    func testPoundNormalizationBoundaryRejectsNonfiniteAndNegativeValues() {
        XCTAssertNil(ForceSensorSample(value: -0.1, unit: .poundsForce, receivedAt: receivedAt))
        XCTAssertNil(ForceSensorSample(value: .nan, unit: .poundsForce, receivedAt: receivedAt))
        XCTAssertNil(ForceSensorSample(value: .infinity, unit: .poundsForce, receivedAt: receivedAt))
    }

    func testCommandsUsePublishedModeCharacteristicAndBytes() throws {
        let adapter = try XCTUnwrap(PitchSixProtocolAdapter(profile: .pitchSix))
        let modeService = try XCTUnwrap(UUID(uuidString: "467A8516-6E39-11EB-9439-0242AC130002"))
        let mode = try XCTUnwrap(UUID(uuidString: "467A8517-6E39-11EB-9439-0242AC130002"))

        XCTAssertEqual(
            adapter.writeCharacteristic,
            ForceSensorBLECharacteristic(serviceUUID: modeService, characteristicUUID: mode)
        )
        XCTAssertEqual(adapter.payload(for: .start), Data([0x04]))
        XCTAssertEqual(adapter.payload(for: .tare), Data([0x05]))
        XCTAssertEqual(adapter.payload(for: .stop), Data([0x07]))
    }

    func testContractAndExactNameMatchingUsePitchSixProtocol() throws {
        let adapter = try XCTUnwrap(PitchSixProtocolAdapter(profile: .pitchSix))
        let forceService = try XCTUnwrap(UUID(uuidString: "9A88D67F-8DF2-4AFE-9E0D-C2BBBE773DD0"))
        let force = try XCTUnwrap(UUID(uuidString: "9A88D682-8DF2-4AFE-9E0D-C2BBBE773DD0"))
        let modeService = try XCTUnwrap(UUID(uuidString: "467A8516-6E39-11EB-9439-0242AC130002"))

        XCTAssertEqual(adapter.contract.serviceUUIDs, [forceService, modeService])
        XCTAssertEqual(adapter.contract.notificationCharacteristics, [
            ForceSensorBLECharacteristic(serviceUUID: forceService, characteristicUUID: force)
        ])
        XCTAssertEqual(adapter.capabilities, [.hardwareTare, .explicitStartStop])
        XCTAssertTrue(adapter.matches(ForceSensorAdvertisement(name: "Force Board", serviceUUIDs: [])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: "Force Board Portable", serviceUUIDs: [forceService])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: nil, serviceUUIDs: [forceService])))
        XCTAssertNil(PitchSixProtocolAdapter(profile: .progressor))
    }
}
