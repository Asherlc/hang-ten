import Foundation
import XCTest
@testable import HangTen

final class WHC06ProtocolTests: XCTestCase {
    private let receivedAt = Date(timeIntervalSince1970: 3_579)

    func testBothWHC06ProfilesAreExplicitSelectionOnlyAndMatchCompanyIdentifier() throws {
        let named = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let generic = try XCTUnwrap(WHC06ProtocolAdapter(profile: .genericWHC06))
        let advertisement = ForceSensorAdvertisement(
            name: "Scale",
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(companyIdentifier: 0x0100, payload: Data(repeating: 0, count: 12))
            ]
        )
        let unrelatedCompany = ForceSensorAdvertisement(
            name: "Scale",
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(companyIdentifier: 0x0101, payload: Data(repeating: 0, count: 12))
            ]
        )

        XCTAssertEqual(named.profile.matchingPolicy, .generic)
        XCTAssertEqual(generic.profile.matchingPolicy, .generic)
        XCTAssertFalse(named.profile.matchingPolicy.permitsAutomaticSelection)
        XCTAssertFalse(generic.profile.matchingPolicy.permitsAutomaticSelection)
        XCTAssertTrue(named.matches(advertisement))
        XCTAssertTrue(generic.matches(advertisement))
        XCTAssertFalse(named.matches(unrelatedCompany))
        XCTAssertFalse(generic.matches(unrelatedCompany))
        XCTAssertNil(WHC06ProtocolAdapter(profile: .automatic))
        XCTAssertNil(WHC06ProtocolAdapter(profile: .progressor))
    }

    func testDecoderReadsBigEndianHundredthsOfKilogramForce() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0x04, 0xD2])
                )
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded.count, 1)
        XCTAssertEqual(decoded[0].kilogramsForce, 12.34, accuracy: 0.000_001)
        XCTAssertEqual(decoded[0].receivedAt, receivedAt)
    }

    func testDecoderRejectsShortManufacturerPayloads() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0x04])
                )
            ]
        )

        XCTAssertNil(adapter.decode(advertisement, receivedAt: receivedAt))
    }

    func testDecoderReadsPayloadBytesFromANonzeroIndexDataSlice() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .genericWHC06))
        let fullPayload = Data([0xFF, 0xFF, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0x00, 0x7B])
        let payload = fullPayload[fullPayload.index(fullPayload.startIndex, offsetBy: 2)...]
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(companyIdentifier: 0x0100, payload: payload)
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded.count, 1)
        XCTAssertEqual(decoded[0].kilogramsForce, 1.23, accuracy: 0.000_001)
    }

    func testAdvertisementOnlyAdapterHasNoBLEContractCommandsOrCapabilities() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))

        XCTAssertEqual(adapter.capabilities, [])
        XCTAssertNil(adapter.contract)
        XCTAssertNil(adapter.writeCharacteristic)
        XCTAssertNil(adapter.payload(for: .tare))
        XCTAssertNil(adapter.payload(for: .start))
        XCTAssertNil(adapter.payload(for: .stop))
    }
}
