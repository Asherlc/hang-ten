import Foundation
import XCTest
@testable import HangTen

final class WHC06ProtocolTests: XCTestCase {
    private let receivedAt = Date(timeIntervalSince1970: 3_579)

    func testExplicitWHC06ProfilesMatchCompanyIdentifierWithoutCapturedFingerprint() throws {
        let named = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let generic = try XCTUnwrap(WHC06ProtocolAdapter(profile: .genericWHC06))
        let noncapturedWHC06 = ForceSensorAdvertisement(
            name: "Scale",
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([
                        0x99, 0x88, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11,
                        0x00, 0x00, 0x7B
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
        XCTAssertTrue(named.matches(noncapturedWHC06))
        XCTAssertTrue(generic.matches(noncapturedWHC06))
        XCTAssertTrue(named.matches(presenceRadar))
        XCTAssertTrue(generic.matches(presenceRadar))
        XCTAssertFalse(named.matches(unrelatedCompany))
        XCTAssertFalse(generic.matches(unrelatedCompany))
        XCTAssertNil(WHC06ProtocolAdapter(profile: .automatic))
        XCTAssertNil(WHC06ProtocolAdapter(profile: .progressor))
    }

    func testAutomaticSelectionAcceptsCapturedSignatureWithTrailingExtensionBytes() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: "Scale",
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([
                        0x02, 0x03, 0x11, 0x2A, 0xC0, 0x19, 0x11, 0x24, 0x9A,
                        0x01, 0x00, 0x00, 0x01, 0xF4, 0x01, 0x9B, 0x92,
                        0xDE, 0xAD
                    ])
                )
            ]
        )

        XCTAssertTrue(adapter.matchesForAutomaticSelection(advertisement))
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

    func testDecoderConvertsLegacyZeroPoundsStoneAndJinUnitCodes() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let cases: [(unitCode: UInt8, rawCount: UInt16, expectedKilogramsForce: Double)] = [
            (0, 2_000, 9.071_847_4),
            (3, 200, 12.700_586_36),
            (4, 2_600, 13)
        ]

        for testCase in cases {
            let advertisement = ForceSensorAdvertisement(
                name: "IF_B7",
                serviceUUIDs: [],
                manufacturerData: [
                    ForceSensorManufacturerData(
                        companyIdentifier: 0x0100,
                        payload: payload(
                            rawCount: testCase.rawCount,
                            unitCode: testCase.unitCode,
                            prefix: [0x99, 0x88]
                        )
                    )
                ]
            )

            let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

            XCTAssertEqual(
                decoded[0].kilogramsForce,
                testCase.expectedKilogramsForce,
                accuracy: 0.000_000_001,
                "unit code \(testCase.unitCode)"
            )
        }
    }

    func testDecoderAcceptsExactThreeHundredKilogramCapacity() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: payload(rawCount: 30_000, unitCode: 1, prefix: [0x99, 0x88])
                )
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded[0].kilogramsForce, 300, accuracy: 0.000_001)
    }

    func testDecoderRejectsOneHundredthKilogramAboveCapacity() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: payload(rawCount: 30_001, unitCode: 1, prefix: [0x99, 0x88])
                )
            ]
        )

        XCTAssertNil(adapter.decode(advertisement, receivedAt: receivedAt))
    }

    func testDecoderAppliesCapacityGuardAfterConvertingMaximumRepresentablePounds() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: payload(rawCount: .max, unitCode: 2, prefix: [0x99, 0x88])
                )
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        // 655.35 lb is the largest value representable by the two-byte centi-unit field.
        XCTAssertEqual(decoded[0].kilogramsForce, 297.261_759_679_5, accuracy: 0.000_000_001)
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

    func testDecoderTriesEveryMatchingCompanyIdentifierEntryUntilOneDecodes() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([0x00])
                ),
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0101,
                    payload: payload(rawCount: 1_300, unitCode: 1, prefix: [0x99, 0x88])
                ),
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: payload(rawCount: 2_600, unitCode: 1, prefix: [0x99, 0x88])
                )
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded[0].kilogramsForce, 26, accuracy: 0.000_001)
    }

    func testDecoderRejectsThePublishedLD2410BPresenceRadarPacketDespiteLegacyFallback() throws {
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

        XCTAssertTrue(adapter.matches(advertisement))
        XCTAssertNil(adapter.decode(advertisement, receivedAt: receivedAt))
    }

    func testDecoderAcceptsTwelveByteLegacyPayloadWithoutUnitAsKilograms() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0x0A, 0x28])
                )
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded[0].kilogramsForce, 26, accuracy: 0.000_001)
    }

    func testDecoderAcceptsTrailingPayloadBytes() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        var paddedPayload = payload(rawCount: 2_600, unitCode: 1, prefix: [0x99, 0x88])
        paddedPayload.append(contentsOf: [0xDE, 0xAD, 0xBE, 0xEF])
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(companyIdentifier: 0x0100, payload: paddedPayload)
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded[0].kilogramsForce, 26, accuracy: 0.000_001)
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

    func testDecoderFallsBackToKilogramsForUnknownUnitNibble() throws {
        let adapter = try XCTUnwrap(WHC06ProtocolAdapter(profile: .whC06))
        let advertisement = ForceSensorAdvertisement(
            name: nil,
            serviceUUIDs: [],
            manufacturerData: [
                ForceSensorManufacturerData(
                    companyIdentifier: 0x0100,
                    payload: Data([
                        0x02, 0x03, 0x11, 0x2A, 0xC0, 0x19, 0x11, 0x24, 0x9A,
                        0x01, 0x04, 0xD2, 0x01, 0xF4, 0x09, 0x9B, 0x92
                    ])
                )
            ]
        )

        let decoded = try XCTUnwrap(adapter.decode(advertisement, receivedAt: receivedAt))

        XCTAssertEqual(decoded[0].kilogramsForce, 12.34, accuracy: 0.000_001)
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

    private func payload(rawCount: UInt16, unitCode: UInt8, prefix: [UInt8]) -> Data {
        precondition(prefix.count == 2)
        return Data([
            prefix[0], prefix[1], 0x11, 0x2A, 0xC0, 0x19, 0x11, 0x24, 0x9A, 0x01,
            UInt8(rawCount >> 8), UInt8(rawCount & 0x00FF),
            0x01, 0xF4, unitCode
        ])
    }
}
