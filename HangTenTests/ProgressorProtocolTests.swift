import Foundation
import XCTest
@testable import HangTen

final class ProgressorProtocolTests: XCTestCase {
    private let receivedAt = Date(timeIntervalSince1970: 1_234)

    func testDecoderEmitsEveryRecordWithDeviceTimestamp() throws {
        let adapter = try XCTUnwrap(ProgressorProtocolAdapter(profile: .progressor))
        let frame = Data([
            0x01, 0x10,
            0x00, 0x00, 0x48, 0x41, 0x40, 0x42, 0x0F, 0x00,
            0x00, 0x00, 0x00, 0x3F, 0xD0, 0x12, 0x13, 0x00
        ])

        let decoded = try XCTUnwrap(adapter.decode(frame, receivedAt: receivedAt))

        XCTAssertEqual(decoded.count, 2)
        XCTAssertEqual(decoded[0].sample.kilogramsForce, 12.5, accuracy: 0.000_001)
        XCTAssertEqual(decoded[0].sample.receivedAt, receivedAt)
        XCTAssertEqual(decoded[0].deviceTimestampMicroseconds, 1_000_000)
        XCTAssertEqual(decoded[1].sample.kilogramsForce, 0.5, accuracy: 0.000_001)
        XCTAssertEqual(decoded[1].sample.receivedAt, receivedAt)
        XCTAssertEqual(decoded[1].deviceTimestampMicroseconds, 1_250_000)
    }

    func testDecoderRejectsMalformedHeaderAndPayloads() throws {
        let adapter = try XCTUnwrap(ProgressorProtocolAdapter(profile: .progressor))
        let wrongHeader = Data([
            0x02, 0x08,
            0x00, 0x00, 0x80, 0x3F, 0x01, 0x00, 0x00, 0x00
        ])
        let oddPayload = Data([
            0x01, 0x09,
            0x00, 0x00, 0x80, 0x3F, 0x01, 0x00, 0x00, 0x00, 0xFF
        ])

        XCTAssertNil(adapter.decode(wrongHeader, receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(oddPayload, receivedAt: receivedAt))
    }

    func testDecoderRejectsTypeOneFrameWithMismatchedTLVPayloadLength() throws {
        let adapter = try XCTUnwrap(ProgressorProtocolAdapter(profile: .progressor))
        let frame = Data([
            0x01, 0x08,
            0x00, 0x00, 0x80, 0x3F, 0x01, 0x00, 0x00
        ])

        XCTAssertNil(adapter.decode(frame, receivedAt: receivedAt))
    }

    func testDecoderRejectsNonfiniteAndNegativeForce() throws {
        let adapter = try XCTUnwrap(ProgressorProtocolAdapter(profile: .progressor))
        let nanFrame = Data([
            0x01, 0x08,
            0x00, 0x00, 0xC0, 0x7F, 0x01, 0x00, 0x00, 0x00
        ])
        let negativeFrame = Data([
            0x01, 0x08,
            0x00, 0x00, 0x80, 0xBF, 0x01, 0x00, 0x00, 0x00
        ])

        XCTAssertNil(adapter.decode(nanFrame, receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(negativeFrame, receivedAt: receivedAt))
    }

    func testDecoderRejectsEntireMultiRecordFrameWhenLaterForceIsInvalid() throws {
        let adapter = try XCTUnwrap(ProgressorProtocolAdapter(profile: .progressor))
        let validThenNonfinite = Data([
            0x01, 0x10,
            0x00, 0x00, 0x80, 0x3F, 0x01, 0x00, 0x00, 0x00,
            0x00, 0x00, 0xC0, 0x7F, 0x02, 0x00, 0x00, 0x00
        ])
        let validThenNegative = Data([
            0x01, 0x10,
            0x00, 0x00, 0x80, 0x3F, 0x01, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x80, 0xBF, 0x02, 0x00, 0x00, 0x00
        ])

        XCTAssertNil(adapter.decode(validThenNonfinite, receivedAt: receivedAt))
        XCTAssertNil(adapter.decode(validThenNegative, receivedAt: receivedAt))
    }

    func testCommandsUseExactProgressorBytes() throws {
        let adapter = try XCTUnwrap(ProgressorProtocolAdapter(profile: .progressor))

        XCTAssertEqual(adapter.payload(for: .tare), Data([0x64]))
        XCTAssertEqual(adapter.payload(for: .start), Data([0x65]))
        XCTAssertEqual(adapter.payload(for: .stop), Data([0x66]))
    }

    func testContractUsesProgressorServiceAndCharacteristics() throws {
        let adapter = try XCTUnwrap(ProgressorProtocolAdapter(profile: .progressor))
        let service = try XCTUnwrap(UUID(uuidString: "7E4E1701-1EA6-40C9-9DCC-13D34FFEAD57"))
        let notify = try XCTUnwrap(UUID(uuidString: "7E4E1702-1EA6-40C9-9DCC-13D34FFEAD57"))
        let write = try XCTUnwrap(UUID(uuidString: "7E4E1703-1EA6-40C9-9DCC-13D34FFEAD57"))

        XCTAssertEqual(adapter.contract.serviceUUIDs, [service])
        XCTAssertEqual(adapter.contract.notificationCharacteristics, [
            ForceSensorBLECharacteristic(serviceUUID: service, characteristicUUID: notify)
        ])
        XCTAssertEqual(
            adapter.writeCharacteristic,
            ForceSensorBLECharacteristic(serviceUUID: service, characteristicUUID: write)
        )
    }

    func testNamedAndGenericProfilesUseDistinctMatchingRulesWithSameProtocolBehavior() throws {
        let named = try XCTUnwrap(ProgressorProtocolAdapter(profile: .progressor))
        let generic = try XCTUnwrap(ProgressorProtocolAdapter(profile: .genericProgressor))
        let service = try XCTUnwrap(UUID(uuidString: "7E4E1701-1EA6-40C9-9DCC-13D34FFEAD57"))
        let unrelatedService = try XCTUnwrap(UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"))
        let namedAdvertisement = ForceSensorAdvertisement(name: "Progressor 123", serviceUUIDs: [service])
        let arbitraryNameAdvertisement = ForceSensorAdvertisement(name: "Compatible Clone", serviceUUIDs: [service])
        let wrongServiceAdvertisement = ForceSensorAdvertisement(name: "Progressor 123", serviceUUIDs: [unrelatedService])
        let frame = Data([
            0x01, 0x08,
            0x00, 0x00, 0x20, 0x41, 0x2A, 0x00, 0x00, 0x00
        ])

        XCTAssertTrue(named.matches(namedAdvertisement))
        XCTAssertFalse(named.matches(arbitraryNameAdvertisement))
        XCTAssertTrue(named.matches(wrongServiceAdvertisement))
        XCTAssertTrue(generic.matches(namedAdvertisement))
        XCTAssertTrue(generic.matches(arbitraryNameAdvertisement))
        XCTAssertFalse(generic.matches(wrongServiceAdvertisement))
        XCTAssertEqual(named.capabilities, generic.capabilities)
        XCTAssertEqual(named.decode(frame, receivedAt: receivedAt), generic.decode(frame, receivedAt: receivedAt))
        XCTAssertEqual(named.payload(for: .tare), generic.payload(for: .tare))
        XCTAssertNil(ProgressorProtocolAdapter(profile: .climbro))
    }
}
