import Foundation
import XCTest
@testable import HangTen

final class ForceSensorModelsTests: XCTestCase {
    func testProfilesExposeStableIdentifiersLabelsAndSelectableOrder() {
        let expectedProfiles: [(ForceSensorProfile, String, String)] = [
            (.automatic, "automatic", "Automatic"),
            (.motherboard, "motherboard", "Motherboard"),
            (.progressor, "progressor", "Tindeq Progressor"),
            (.pitchSix, "pitchSix", "PitchSix Force Board"),
            (.whC06, "whC06", "WH-C06"),
            (.entralpi, "entralpi", "Entralpi"),
            (.climbro, "climbro", "Climbro"),
            (.genericProgressor, "genericProgressor", "Generic Progressor-compatible"),
            (.genericWHC06, "genericWHC06", "Generic WH-C06-compatible")
        ]

        XCTAssertEqual(ForceSensorProfile.selectableCases, expectedProfiles.map(\.0))
        for (profile, identifier, label) in expectedProfiles {
            XCTAssertEqual(profile.rawValue, identifier)
            XCTAssertEqual(profile.id, identifier)
            XCTAssertEqual(profile.label, label)
        }
    }

    func testConnectableProfilesIncludeOnlyImplementedBLEAdapters() {
        XCTAssertEqual(
            ForceSensorProfile.connectableCases,
            [.automatic, .motherboard, .progressor, .pitchSix, .genericProgressor]
        )
    }

    func testRegistryResolvesBLEAdaptersAndKeepsAdvertisementOnlyProfilesOutOfConnectionFlow() throws {
        let progressor = try XCTUnwrap(ForceSensorAdapterRegistry.adapter(for: .progressor))
        let pitchSix = try XCTUnwrap(ForceSensorAdapterRegistry.adapter(for: .pitchSix))
        let genericProgressor = try XCTUnwrap(ForceSensorAdapterRegistry.adapter(for: .genericProgressor))

        XCTAssertEqual(progressor.profile, .progressor)
        XCTAssertEqual(pitchSix.profile, .pitchSix)
        XCTAssertEqual(genericProgressor.profile, .genericProgressor)
        XCTAssertNil(ForceSensorAdapterRegistry.adapter(for: .whC06))
        XCTAssertNil(ForceSensorAdapterRegistry.adapter(for: .genericWHC06))
        XCTAssertEqual(
            ForceSensorAdapterRegistry.automaticProfiles,
            [.motherboard, .progressor, .pitchSix]
        )
    }

    func testMatchingPolicyKeepsGenericAndAdvertisementOnlyProfilesOutOfAutomaticSelection() {
        XCTAssertEqual(ForceSensorProfile.automatic.matchingPolicy, .automatic)

        let namedProfiles: [ForceSensorProfile] = [
            .motherboard,
            .progressor,
            .pitchSix,
            .entralpi,
            .climbro
        ]
        XCTAssertTrue(namedProfiles.allSatisfy { $0.matchingPolicy == .named })
        XCTAssertTrue(namedProfiles.allSatisfy { $0.matchingPolicy.permitsAutomaticSelection })

        let genericProfiles: [ForceSensorProfile] = [.whC06, .genericProgressor, .genericWHC06]
        XCTAssertTrue(genericProfiles.allSatisfy { $0.matchingPolicy == .generic })
        XCTAssertTrue(genericProfiles.allSatisfy { !$0.matchingPolicy.permitsAutomaticSelection })
    }

    func testSampleNormalizesSupportedSourceUnitsAndRejectsInvalidValues() throws {
        let timestamp = Date(timeIntervalSince1970: 123)
        let kilograms = try XCTUnwrap(
            ForceSensorSample(value: 10, unit: .kilogramsForce, receivedAt: timestamp)
        )
        let pounds = try XCTUnwrap(
            ForceSensorSample(value: 22.0462262185, unit: .poundsForce, receivedAt: timestamp)
        )
        let newtons = try XCTUnwrap(
            ForceSensorSample(value: 98.0665, unit: .newtons, receivedAt: timestamp)
        )
        let zero = try XCTUnwrap(
            ForceSensorSample(value: 0, unit: .kilogramsForce, receivedAt: timestamp)
        )

        XCTAssertEqual(kilograms.kilogramsForce, 10, accuracy: 0.000_001)
        XCTAssertEqual(pounds.kilogramsForce, 10, accuracy: 0.000_001)
        XCTAssertEqual(newtons.kilogramsForce, 10, accuracy: 0.000_001)
        XCTAssertEqual(zero.kilogramsForce, 0)
        XCTAssertEqual(kilograms.receivedAt, timestamp)
        XCTAssertNil(ForceSensorSample(value: -0.1, unit: .kilogramsForce, receivedAt: timestamp))
        XCTAssertNil(ForceSensorSample(value: .nan, unit: .kilogramsForce, receivedAt: timestamp))
        XCTAssertNil(ForceSensorSample(value: .infinity, unit: .kilogramsForce, receivedAt: timestamp))
    }

    func testBLEContractAndAdvertisementCarryServiceMetadata() throws {
        let service = try XCTUnwrap(UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"))
        let notify = try XCTUnwrap(UUID(uuidString: "11111111-2222-3333-4444-555555555555"))
        let notification = ForceSensorBLECharacteristic(
            serviceUUID: service,
            characteristicUUID: notify
        )
        let contract = ForceSensorBLEContract(
            serviceUUIDs: [service],
            notificationCharacteristics: [notification]
        )
        let advertisement = ForceSensorAdvertisement(
            name: "Synthetic sensor",
            serviceUUIDs: [service],
            manufacturerData: [
                ForceSensorManufacturerData(companyIdentifier: 0x0100, payload: Data([0x01]))
            ]
        )

        XCTAssertEqual(contract.serviceUUIDs, [service])
        XCTAssertEqual(contract.notificationCharacteristics, [notification])
        XCTAssertEqual(advertisement.name, "Synthetic sensor")
        XCTAssertEqual(advertisement.serviceUUIDs, [service])
        XCTAssertEqual(advertisement.manufacturerData, [
            ForceSensorManufacturerData(companyIdentifier: 0x0100, payload: Data([0x01]))
        ])
    }
}
