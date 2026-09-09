import Foundation
import XCTest
@testable import HangTen

final class WHC06ProtocolTests: XCTestCase {
    private let receivedAt = Date(timeIntervalSince1970: 3_579)

    func testNamedWHC06MatchesOnlyTheCapturedPacketSignatureWhileGenericRemainsManual() throws {
        let named = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let generic = try XCTUnwrap(WHC06ProtocolAdapter(profile: .genericWHC06))
        let capturedWHC06 = ForceSensorAdvertisement(
            name: "Scale",
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([
                        0x02, 0x03, 0x11, 0x2A, 0xC0, 0x19, 0x11, 0x24, 0x9A,
                        0x01, 0x00, 0x00, 0x01, 0xF4, 0x01, 0x9B, 0x92
                    ])
                )
            ]
        )
        let presenceRadar = ForceSensorAdvertisement(
            name: "HLK-LD2410B",
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([0x07, 0x01, 0x16, 0x15, 0x09, 0x22, 0x00, 0xBE, 0x8D, 0xED, 0xEE, 0x56, 0x00])
                )
            ]
        )
        let unrelatedCompany = ForceSensorAdvertisement(
            name: "Scale",
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(companyIdentifier: 0x0101, payload: Data(repeating: 0, count: 12))
            ]
        )

        XCTAssertEqual(named.profile.matchingPolicy, .named)
        XCTAssertEqual(generic.profile.matchingPolicy, .generic)
        XCTAssertTrue(named.profile.matchingPolicy.permitsAutomaticSelection)
        XCTAssertFalse(generic.profile.matchingPolicy.permitsAutomaticSelection)
        XCTAssertTrue(named.matches(capturedWHC06))
        XCTAssertTrue(generic.matches(capturedWHC06))
        XCTAssertFalse(named.matches(presenceRadar))
        XCTAssertTrue(generic.matches(presenceRadar))
        XCTAssertFalse(named.matches(unrelatedCompany))
        XCTAssertFalse(generic.matches(unrelatedCompany))
        XCTAssertNil(WHC06ProtocolAdapter(profile: .automatic))
        XCTAssertNil(WHC06ProtocolAdapter(profile: .progressor))
    }

    func testDecoderReadsBigEndianHundredthsOfKilogramForceWhenUnitNibbleIsOne() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([
                        0x02, 0x03, 0x11, 0x2A, 0xC0, 0x19, 0x11, 0x24, 0x9A,
                        0x01, 0x04, 0xD2, 0x01, 0xF4, 0x01, 0x9B, 0x92
                    ])
                )
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded.count, 1)
        XCTAssertEqual(decoded[0].kilogramsForce, 12.34, accuracy: 0.000_001)
        XCTAssertEqual(decoded[0].receivedAt, receivedAt)
    }

    func testDecoderConvertsPoundsFromUnitNibbleToCanonicalKilogramsForce() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([
                        0x02, 0x03, 0x11, 0x2A, 0xC0, 0x19, 0x11, 0x24, 0x9A,
                        0x01, 0x07, 0xD0, 0x01, 0xF4, 0xA2, 0x9B, 0x92
                    ])
                )
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded[0].kilogramsForce, 9.07184740068, accuracy: 0.000_000_001)
        XCTAssertEqual(
            MotherboardForceUnit.lbf.value(fromKilogramsForce: decoded[0].kilogramsForce),
            20,
            accuracy: 0.000_001
        )
    }

    func testDecoderRejectsShortManufacturerPayloads() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0x04, 0xD2, 0, 0])
                )
            ]
        )

        XCTAssertNil(adapter.decode(advertisement, receivedAt: receivedAt))
    }

    func testNamedDecoderRejectsThePublishedLD2410BPresenceRadarPacket() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: "HLK-LD2410B",
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([0x07, 0x01, 0x16, 0x15, 0x09, 0x22, 0x00, 0xBE, 0x8D, 0xED, 0xEE, 0x56, 0x00])
                )
            ]
        )

        XCTAssertFalse(adapter.matches(advertisement))
        XCTAssertNil(adapter.decode(advertisement, receivedAt: receivedAt))
    }

    func testDecoderReadsPayloadBytesFromANonzeroIndexDataSlice() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .genericWHC06))
        let fullPayload = Data([
            0xFF, 0xFF,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0x00, 0x7B, 0, 0, 0x01
        ])
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

    func testDecoderRejectsUnsupportedUnitNibble() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([
                        0x02, 0x03, 0x11, 0x2A, 0xC0, 0x19, 0x11, 0x24, 0x9A,
                        0x01, 0x04, 0xD2, 0x01, 0xF4, 0x03, 0x9B, 0x92
                    ])
                )
            ]
        )

        XCTAssertNil(adapter.decode(advertisement, receivedAt: receivedAt))
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
