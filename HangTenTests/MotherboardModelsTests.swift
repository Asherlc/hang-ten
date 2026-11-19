import Combine
import SwiftUI
import UIKit
import XCTest
@testable import HangTen

final class MotherboardModelsTests: XCTestCase {
    func testUntrackedInitialWeightConfigurationCarriesNoWeightData() {
        let configuration = WorkoutInitialWeightConfiguration.untracked

        XCTAssertEqual(configuration.source, .untracked)
        XCTAssertNil(configuration.manualWeightKGF)
        XCTAssertFalse(configuration.manualWeightIncludesBodyweight)
    }

    func testSensorSessionIgnoresStaleManualValuesWhenDecoding() throws {
        let record = WorkoutSessionRecord(
            id: UUID(), planID: "plan", planTitle: "Test plan",
            recordedAt: Date(), startDate: Date(), endDate: Date(),
            motherboardIdentifier: nil, batteryValue: nil, steps: [], initialWeight: .sensor
        )
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(record)) as? [String: Any])
        XCTAssertNil(object["manualWeightKGF"])
        object["manualWeightKGF"] = 42
        object["manualWeightIncludesBodyweight"] = true
        let decoded = try JSONDecoder().decode(WorkoutSessionRecord.self, from: JSONSerialization.data(withJSONObject: object))
        XCTAssertNil(decoded.manualWeightKGF)
        XCTAssertFalse(decoded.manualWeightIncludesBodyweight)
        XCTAssertEqual(decoded.initialWeight, .sensor)
        XCTAssertEqual(decoded.loadAdjustmentKGF, 0)
    }

    func testInitialWeightConfigurationKeepsManualWeightSeparateFromSensorMode() {
        let sensor = WorkoutInitialWeightConfiguration.sensor
        XCTAssertEqual(sensor.source, .sensor)
        XCTAssertNil(sensor.manualWeightKGF)
        XCTAssertFalse(sensor.manualWeightIncludesBodyweight)

        let manual = WorkoutInitialWeightConfiguration.manual(
            weightKGF: 12.5,
            includesBodyweight: true
        )
        XCTAssertEqual(manual.source, .manual)
        XCTAssertEqual(manual.manualWeightKGF, 12.5)
        XCTAssertTrue(manual.manualWeightIncludesBodyweight)
    }

    func testSessionRecordDefaultsToUntrackedAndRoundTripsItExactly() throws {
        let record = WorkoutSessionRecord(
            id: UUID(),
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )

        let decoded = try JSONDecoder().decode(
            WorkoutSessionRecord.self,
            from: JSONEncoder().encode(record)
        )

        XCTAssertEqual(record.initialWeight, .untracked)
        XCTAssertEqual(decoded.initialWeight, .untracked)
        XCTAssertNil(decoded.manualWeightKGF)
        XCTAssertFalse(decoded.manualWeightIncludesBodyweight)
    }

    func testSessionRecordRoundTripsManualInitialWeightDetails() throws {
        let record = WorkoutSessionRecord(
            id: UUID(),
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [],
            initialWeight: .manual(weightKGF: 12.5, includesBodyweight: true)
        )

        let decoded = try JSONDecoder().decode(
            WorkoutSessionRecord.self,
            from: JSONEncoder().encode(record)
        )

        XCTAssertEqual(decoded.initialWeight, record.initialWeight)
        XCTAssertEqual(decoded.loadAdjustmentKGF, 0)
    }

    func testSessionRecordDecodesLegacyRecordAsSensorWeightSource() throws {
        let record = WorkoutSessionRecord(
            id: UUID(),
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )
        let data = try JSONEncoder().encode(record)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object.removeValue(forKey: "initialWeightSource")
        object.removeValue(forKey: "manualWeightKGF")
        object.removeValue(forKey: "manualWeightIncludesBodyweight")

        let decoded = try JSONDecoder().decode(
            WorkoutSessionRecord.self,
            from: JSONSerialization.data(withJSONObject: object)
        )

        XCTAssertEqual(decoded.initialWeight, .sensor)
    }

    func testMalformedManualSessionWithoutWeightFallsBackToSensorConfiguration() throws {
        let record = WorkoutSessionRecord(
            id: UUID(),
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [],
            initialWeight: .manual(weightKGF: 12.5, includesBodyweight: true)
        )
        var object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: JSONEncoder().encode(record)) as? [String: Any]
        )
        object.removeValue(forKey: "manualWeightKGF")

        let decoded = try JSONDecoder().decode(
            WorkoutSessionRecord.self,
            from: JSONSerialization.data(withJSONObject: object)
        )

        XCTAssertEqual(decoded.initialWeight, .sensor)
    }

    func testBalanceRockerLevelsForSymmetricalHighLoad() {
        let state = MotherboardBalanceRocker.state(
            measurement: measurement(sensorLoads: [60, 60, 60, 60], aggregate: 180),
            thresholdKGF: 2.5
        )

        XCTAssertEqual(state, .available(tiltFraction: 0))
        XCTAssertEqual(state.tiltFraction, 0, accuracy: 0.0001)
        XCTAssertEqual(state.accessibilityValue, "Balanced")
        XCTAssertEqual(MotherboardBalanceRocker.accessibilityLabel, "Left/right load balance")
    }

    func testBalanceRockerTiltsTowardTheHeavierSide() {
        let rightHeavy = MotherboardBalanceRocker.state(
            measurement: measurement(sensorLoads: [4, 8, 12, 0], aggregate: 24),
            thresholdKGF: 2.5
        )
        let leftHeavy = MotherboardBalanceRocker.state(
            measurement: measurement(sensorLoads: [12, 8, 4, 0], aggregate: 24),
            thresholdKGF: 2.5
        )

        XCTAssertGreaterThan(rightHeavy.tiltFraction, 0)
        XCTAssertEqual(rightHeavy.accessibilityValue, "Right side lower")
        XCTAssertLessThan(leftHeavy.tiltFraction, 0)
        XCTAssertEqual(leftHeavy.accessibilityValue, "Left side lower")
    }

    func testBalanceRockerTiltFollowsShareRatherThanAbsoluteLoad() {
        let light = MotherboardBalanceRocker.state(
            measurement: measurement(sensorLoads: [4, 6, 10, 0], aggregate: 20),
            thresholdKGF: 2.5
        )
        let heavy = MotherboardBalanceRocker.state(
            measurement: measurement(sensorLoads: [40, 60, 100, 0], aggregate: 200),
            thresholdKGF: 2.5
        )

        XCTAssertEqual(light.tiltFraction, heavy.tiltFraction, accuracy: 0.0001)
    }

    func testBalanceRockerIgnoresTheFourthChannel() {
        let baseline = MotherboardBalanceRocker.state(
            measurement: measurement(sensorLoads: [4, 6, 10, 0], aggregate: 20),
            thresholdKGF: 2.5
        )
        let changed = MotherboardBalanceRocker.state(
            measurement: measurement(sensorLoads: [4, 6, 10, 1000], aggregate: 20),
            thresholdKGF: 2.5
        )

        XCTAssertEqual(baseline, changed)
    }

    func testBalanceRockerIsUnavailableWithoutLoadOrBelowThreshold() {
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: [4, 4, 4, 4], aggregate: 2.4),
                thresholdKGF: 2.5
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: [0, 0, 0, 0], aggregate: 30),
                thresholdKGF: 2.5
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(measurement: nil, thresholdKGF: 2.5),
            .unavailable
        )
    }

    func testBalanceRockerIsUnavailableForInvalidThresholdAggregateOrChannels() {
        let validLoads = [4.0, 4.0, 4.0, 4.0]

        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: validLoads, aggregate: 30),
                thresholdKGF: 0
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: validLoads, aggregate: 30),
                thresholdKGF: .nan
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: validLoads, aggregate: 30),
                thresholdKGF: .infinity
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: validLoads, aggregate: .nan),
                thresholdKGF: 2.5
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: validLoads, aggregate: .infinity),
                thresholdKGF: 2.5
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: [4, .nan, 4, 4], aggregate: 30),
                thresholdKGF: 2.5
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: [4, 4, .infinity, 4], aggregate: 30),
                thresholdKGF: 2.5
            ),
            .unavailable
        )
        XCTAssertEqual(
            MotherboardBalanceRocker.state(
                measurement: measurement(sensorLoads: [4, 4], aggregate: 30),
                thresholdKGF: 2.5
            ),
            .unavailable
        )
    }

    func testBalanceRockerStaysLevelForTotalForceOnlySensors() {
        let state = MotherboardBalanceRocker.state(
            measurement: measurement(sensorLoads: [], aggregate: 100),
            thresholdKGF: 2.5
        )

        XCTAssertEqual(state, .unavailable)
        XCTAssertEqual(state.tiltFraction, 0)
    }

    func testBalanceRockerIgnoresRapidThresholdOscillation() {
        var rocker = MotherboardBalanceRocker()
        var time = 0.0

        for _ in 0..<12 {
            rocker.consume(
                measurement: measurement(sensorLoads: [0.83, 0.83, 0.83, 0], aggregate: 2.49),
                thresholdKGF: 2.5,
                at: time
            )
            time += 0.033
            rocker.consume(
                measurement: measurement(sensorLoads: [0.84, 0.84, 0.84, 0], aggregate: 2.51),
                thresholdKGF: 2.5,
                at: time
            )
            time += 0.033
        }

        XCTAssertEqual(rocker.displayedState, .unavailable)
    }

    func testBalanceRockerIgnoresSingleAboveThresholdSpike() {
        var rocker = MotherboardBalanceRocker()

        rocker.consume(
            measurement: measurement(sensorLoads: [1, 1, 1, 0], aggregate: 3),
            thresholdKGF: 2.5,
            at: 0
        )
        rocker.consume(
            measurement: measurement(sensorLoads: [0.8, 0.8, 0.8, 0], aggregate: 2.4),
            thresholdKGF: 2.5,
            at: 0.033
        )

        XCTAssertEqual(rocker.displayedState, .unavailable)
    }

    func testBalanceRockerIgnoresDipThatRecoversInSameSampleBatch() {
        var rocker = MotherboardBalanceRocker()
        let loaded = measurement(sensorLoads: [1, 1, 1, 0], aggregate: 3)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0)
        XCTAssertEqual(rocker.displayedState, .unavailable)

        rocker.consume(
            measurement: measurement(sensorLoads: [0.6, 0.6, 0.6, 0], aggregate: 1.8),
            thresholdKGF: 2.5,
            at: 0.11
        )
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0.11)
        XCTAssertEqual(rocker.displayedState, .unavailable)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0.22)
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))
    }

    func testBalanceRockerActivatesOnlyAfterSustainedThresholdCrossing() {
        var rocker = MotherboardBalanceRocker()
        let loaded = measurement(sensorLoads: [1, 1, 1, 0], aggregate: 3)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0)
        XCTAssertEqual(rocker.displayedState, .unavailable)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0.05)
        XCTAssertEqual(rocker.displayedState, .unavailable)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0.11)
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))
    }

    func testBalanceRockerStaysAvailableAcrossOscillationAboveReleaseThreshold() {
        var rocker = MotherboardBalanceRocker()
        let loaded = measurement(sensorLoads: [1, 1, 1, 0], aggregate: 3)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0.11)
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))

        rocker.consume(
            measurement: measurement(sensorLoads: [0.4, 0.8, 1.2, 0], aggregate: 2.4),
            thresholdKGF: 2.5,
            at: 0.15
        )
        XCTAssertEqual(rocker.displayedState.tiltFraction, 1.0 / 3.0, accuracy: 0.0001)
        rocker.consume(
            measurement: measurement(sensorLoads: [1.2, 0.8, 0.4, 0], aggregate: 2.6),
            thresholdKGF: 2.5,
            at: 0.19
        )
        XCTAssertEqual(rocker.displayedState.tiltFraction, -1.0 / 3.0, accuracy: 0.0001)
    }

    func testBalanceRockerHoldsLastValidStateUntilSustainedRelease() {
        var rocker = MotherboardBalanceRocker()
        let loaded = measurement(sensorLoads: [1, 1, 1, 0], aggregate: 3)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0.11)
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))

        let unloaded = measurement(sensorLoads: [0.6, 0.6, 0.6, 0], aggregate: 1.8)
        rocker.consume(measurement: unloaded, thresholdKGF: 2.5, at: 0.2)
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))
        rocker.consume(measurement: unloaded, thresholdKGF: 2.5, at: 0.25)
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))
        rocker.consume(measurement: unloaded, thresholdKGF: 2.5, at: 0.32)
        XCTAssertEqual(rocker.displayedState, .unavailable)
    }

    func testBalanceRockerBriefDipCancelsPendingRelease() {
        var rocker = MotherboardBalanceRocker()
        let loaded = measurement(sensorLoads: [1, 1, 1, 0], aggregate: 3)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 0.11)
        rocker.consume(
            measurement: measurement(sensorLoads: [0.6, 0.6, 0.6, 0], aggregate: 1.8),
            thresholdKGF: 2.5,
            at: 0.2
        )
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))

        rocker.consume(
            measurement: measurement(sensorLoads: [0.4, 0.8, 1.2, 0], aggregate: 2.4),
            thresholdKGF: 2.5,
            at: 0.25
        )
        XCTAssertEqual(rocker.displayedState.tiltFraction, 1.0 / 3.0, accuracy: 0.0001)
        rocker.consume(
            measurement: measurement(sensorLoads: [0.6, 0.6, 0.6, 0], aggregate: 1.8),
            thresholdKGF: 2.5,
            at: 0.3
        )
        XCTAssertEqual(rocker.displayedState.tiltFraction, 1.0 / 3.0, accuracy: 0.0001)
    }

    func testBalanceRockerReportsSingleSidedTiltAfterDebounce() {
        var rocker = MotherboardBalanceRocker()
        let rightHeavy = measurement(sensorLoads: [4, 8, 12, 0], aggregate: 24)

        rocker.consume(measurement: rightHeavy, thresholdKGF: 2.5, at: 0)
        rocker.consume(measurement: rightHeavy, thresholdKGF: 2.5, at: 0.11)
        XCTAssertGreaterThan(rocker.displayedState.tiltFraction, 0)
        XCTAssertEqual(rocker.displayedState.accessibilityValue, "Right side lower")

        let leftHeavy = measurement(sensorLoads: [12, 8, 4, 0], aggregate: 24)
        rocker.consume(measurement: leftHeavy, thresholdKGF: 2.5, at: 0.15)
        XCTAssertLessThan(rocker.displayedState.tiltFraction, 0)
        XCTAssertEqual(rocker.displayedState.accessibilityValue, "Left side lower")
    }

    func testBalanceRockerResetsOnThresholdChangeAndDisconnect() {
        var rocker = MotherboardBalanceRocker()
        let loaded = measurement(sensorLoads: [1, 1, 1, 0], aggregate: 3)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.11)
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))

        rocker.consume(measurement: loaded, thresholdKGF: 2.6, at: 1.15)
        XCTAssertEqual(rocker.displayedState, .unavailable)

        rocker.consume(measurement: loaded, thresholdKGF: 2.6, at: 1.2)
        rocker.consume(measurement: loaded, thresholdKGF: 2.6, at: 1.31)
        XCTAssertEqual(rocker.displayedState, .available(tiltFraction: 0))

        rocker.consume(measurement: nil, thresholdKGF: 2.6, at: 1.35)
        XCTAssertEqual(rocker.displayedState, .unavailable)
    }

    func testBalanceRockerResetsOnMalformedInputBackwardTimeAndExplicitReset() {
        var rocker = MotherboardBalanceRocker()
        let loaded = measurement(sensorLoads: [1, 1, 1, 0], aggregate: 3)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.11)
        rocker.consume(
            measurement: measurement(sensorLoads: [1, .nan, 1, 0], aggregate: 3),
            thresholdKGF: 2.5,
            at: 1.15
        )
        XCTAssertEqual(rocker.displayedState, .unavailable)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.2)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.31)
        rocker.consume(measurement: loaded, thresholdKGF: .nan, at: 1.35)
        XCTAssertEqual(rocker.displayedState, .unavailable)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.4)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.51)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.0)
        XCTAssertEqual(rocker.displayedState, .unavailable)

        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.6)
        rocker.consume(measurement: loaded, thresholdKGF: 2.5, at: 1.71)
        rocker.reset()
        XCTAssertEqual(rocker.displayedState, .unavailable)
    }

    func testBalancePresentationExplainsWhenOnlyAggregateForceIsAvailable() {
        let aggregateOnly = measurement(sensorLoads: [], aggregate: 10)
        let multiChannel = measurement(sensorLoads: [3, 4, 5], aggregate: 12)

        XCTAssertEqual(MotherboardBalancePresentation(for: aggregateOnly), .aggregateOnly)
        XCTAssertEqual(
            MotherboardBalancePresentation(for: aggregateOnly).unavailableCopy,
            "Balance unavailable — this sensor provides total force only."
        )
        XCTAssertEqual(MotherboardBalancePresentation(for: multiChannel), .available)
        XCTAssertEqual(MotherboardBalancePresentation(for: nil), .unavailable)
    }

    @MainActor
    func testMeterHeightStaysStableAcrossLoadTransitions() async {
        func meterHeight(
            sensorLoads: [Double],
            aggregate: Double,
            width: CGFloat,
            dynamicType: DynamicTypeSize,
            bodyweight: Double?
        ) async -> CGFloat {
            await withActivatedMeter(
                measurement: measurement(sensorLoads: sensorLoads, aggregate: aggregate),
                width: width,
                dynamicType: dynamicType,
                bodyweight: bodyweight,
                showsBodyweightFeedback: true
            ) { _, size in
                size.height
            }
        }

        for width in [CGFloat(320), CGFloat(393)] {
            for dynamicType in [DynamicTypeSize.large, .accessibility3] {
                for bodyweight in [nil, Double(70)] {
                    let zeroLoadHeight = await meterHeight(
                        sensorLoads: [0, 0, 0, 0],
                        aggregate: 0,
                        width: width,
                        dynamicType: dynamicType,
                        bodyweight: bodyweight
                    )
                    let loadedHeight = await meterHeight(
                        sensorLoads: [20, 20, 20, 0],
                        aggregate: 60,
                        width: width,
                        dynamicType: dynamicType,
                        bodyweight: bodyweight
                    )
                    XCTAssertGreaterThan(zeroLoadHeight, 0)
                    XCTAssertEqual(
                        zeroLoadHeight,
                        loadedHeight,
                        accuracy: 0.5,
                        "Zero-load vs loaded height differed at width \(width), dynamic type \(dynamicType), bodyweight \(String(describing: bodyweight))"
                    )

                    let balancedHeight = await meterHeight(
                        sensorLoads: [20, 20, 20, 0],
                        aggregate: 60,
                        width: width,
                        dynamicType: dynamicType,
                        bodyweight: bodyweight
                    )
                    let asymmetricHeight = await meterHeight(
                        sensorLoads: [4, 8, 12, 0],
                        aggregate: 24,
                        width: width,
                        dynamicType: dynamicType,
                        bodyweight: bodyweight
                    )
                    XCTAssertEqual(
                        balancedHeight,
                        asymmetricHeight,
                        accuracy: 0.5,
                        "Balanced vs asymmetric height differed at width \(width), dynamic type \(dynamicType), bodyweight \(String(describing: bodyweight))"
                    )
                }
            }
        }

        let snapshots: [(String, [Double], Double)] = [
            ("zero", [0, 0, 0, 0], 0),
            ("balanced", [20, 20, 20, 0], 60),
            ("asymmetric", [4, 8, 12, 0], 24)
        ]
        for (name, sensorLoads, aggregate) in snapshots {
            await withActivatedMeter(
                measurement: measurement(sensorLoads: sensorLoads, aggregate: aggregate),
                width: 393,
                dynamicType: .large,
                bodyweight: nil,
                showsBodyweightFeedback: false
            ) { view, size in
                let image = UIGraphicsImageRenderer(size: size).image { _ in
                    view.drawHierarchy(
                        in: CGRect(origin: .zero, size: size),
                        afterScreenUpdates: true
                    )
                }
                let attachment = XCTAttachment(image: image)
                attachment.name = "meter-\(name)-aggregate-\(Int(aggregate))-channels-\(sensorLoads.map { String(Int($0)) }.joined(separator: "-"))"
                attachment.lifetime = .keepAlways
                add(attachment)
            }
        }
    }

    /// Mounts the real meter and publishes a second, distinct sample past the display
    /// debounce so the rocker's gated state is live before measurement or snapshot capture.
    @MainActor
    private func withActivatedMeter<Result>(
        measurement: MotherboardMeasurement,
        width: CGFloat,
        dynamicType: DynamicTypeSize,
        bodyweight: Double?,
        showsBodyweightFeedback: Bool,
        perform: (UIView, CGSize) -> Result
    ) async -> Result {
        let updates = PassthroughSubject<MotherboardMeasurement?, Never>()
        let view = MotherboardMeterView(
            measurement: measurement,
            measurementUpdates: updates.eraseToAnyPublisher(),
            peakLoadKGF: nil,
            actualLoadedTime: 0,
            plannedActiveDuration: 0,
            bodyweightKGF: bodyweight,
            unit: .kgf,
            state: .streaming,
            thresholdKGF: 2.5,
            showsConnectionStatus: false,
            showsBodyweightFeedback: showsBodyweightFeedback
        )
        .environment(\.dynamicTypeSize, dynamicType)

        let scene = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .first
        let previousKeyWindow = scene?.windows.first(where: \.isKeyWindow)
        let controller = UIHostingController(rootView: view)
        let window = UIWindow(frame: CGRect(x: 0, y: 0, width: width, height: 600))
        if let scene { window.windowScene = scene }
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer {
            window.isHidden = true
            previousKeyWindow?.makeKeyAndVisible()
        }

        controller.view.layoutIfNeeded()
        await Task.yield()
        updates.send(measurement)
        try? await Task.sleep(nanoseconds: 120_000_000)
        let secondSample = MotherboardMeasurement(
            timestamp: measurement.timestamp.addingTimeInterval(1),
            sampleNumber: measurement.sampleNumber &+ 1,
            batteryValue: measurement.batteryValue,
            rawADCValues: measurement.rawADCValues,
            sensorLoadsKGF: measurement.sensorLoadsKGF,
            aggregateLoadKGF: measurement.aggregateLoadKGF
        )
        updates.send(secondSample)
        try? await Task.sleep(nanoseconds: 20_000_000)

        let size = controller.sizeThatFits(
            in: CGSize(width: width, height: UIView.layoutFittingExpandedSize.height)
        )
        controller.view.frame = CGRect(origin: .zero, size: size)
        controller.view.layoutIfNeeded()
        return perform(controller.view, size)
    }

    func testConnectionStateShowsWorkoutMeterOnlyWhileStreaming() {
        XCTAssertTrue(MotherboardConnectionState.streaming.showsWorkoutMeter)

        let hiddenStates: [MotherboardConnectionState] = [
            .bluetoothUnavailable,
            .unauthorized,
            .idle,
            .scanning,
            .connecting,
            .calibrating,
            .disconnected,
            .failed
        ]

        XCTAssertTrue(hiddenStates.allSatisfy { !$0.showsWorkoutMeter })
    }

    func testConnectionStateDisablesManualLoadAdjustmentOnlyWhileStreaming() {
        XCTAssertTrue(MotherboardConnectionState.streaming.disablesManualLoadAdjustment)

        let enabledStates: [MotherboardConnectionState] = [
            .bluetoothUnavailable,
            .unauthorized,
            .idle,
            .scanning,
            .connecting,
            .calibrating,
            .disconnected,
            .failed
        ]

        XCTAssertTrue(enabledStates.allSatisfy { !$0.disablesManualLoadAdjustment })
    }

    func testForceUnitConversionUsesKilogramsForceAsCanonicalValue() {
        XCTAssertEqual(MotherboardForceUnit.kgf.value(fromKilogramsForce: 2), 2, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.lbf.value(fromKilogramsForce: 2), 4.40925, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.newtons.value(fromKilogramsForce: 2), 19.6133, accuracy: 0.0001)
    }

    func testForceUnitConvertsSignedDisplayedAdjustmentBackToCanonicalKilogramsForce() {
        XCTAssertEqual(
            MotherboardForceUnit.lbf.kilogramsForce(fromDisplayedForce: -22.0462262185),
            -10,
            accuracy: 0.0001
        )
        XCTAssertEqual(
            MotherboardForceUnit.newtons.kilogramsForce(fromDisplayedForce: 98.0665),
            10,
            accuracy: 0.0001
        )
    }

    func testMeasurementSplitsCenterLoadNeutrallyAcrossDisplayedSides() {
        let measurement = measurement(sensorLoads: [3, 4, 5, 100], aggregate: 12)

        XCTAssertEqual(measurement.leftLoadKGF, 5, accuracy: 0.0001)
        XCTAssertEqual(measurement.rightLoadKGF, 7, accuracy: 0.0001)
        XCTAssertEqual(measurement.leftShare, 5.0 / 12.0, accuracy: 0.0001)
        XCTAssertEqual(measurement.rightShare, 7.0 / 12.0, accuracy: 0.0001)
    }

    func testMeasurementIgnoresFourthChannelWhenCalculatingBalance() {
        let baseline = measurement(sensorLoads: [3, 4, 5, 0], aggregate: 12)
        let changed = measurement(sensorLoads: [3, 4, 5, 100], aggregate: 12)

        XCTAssertEqual(baseline.leftLoadKGF, changed.leftLoadKGF, accuracy: 0.0001)
        XCTAssertEqual(baseline.rightLoadKGF, changed.rightLoadKGF, accuracy: 0.0001)
        XCTAssertEqual(baseline.leftShare, changed.leftShare, accuracy: 0.0001)
        XCTAssertEqual(baseline.rightShare, changed.rightShare, accuracy: 0.0001)
    }

    func testMeasurementBodyweightPercentageUsesAggregateLoad() {
        let measurement = measurement(sensorLoads: [2.5, 2.5, 2.5, 2.5], aggregate: 10)
        XCTAssertEqual(measurement.bodyweightPercentage(for: 20), 50, accuracy: 0.0001)
    }

    func testMeasurementIgnoresNonFiniteAndNegativeReferenceZoneLoads() {
        let measurement = measurement(sensorLoads: [.nan, -1, 2, .infinity], aggregate: 2)

        XCTAssertEqual(measurement.leftLoadKGF, 0, accuracy: 0.0001)
        XCTAssertEqual(measurement.rightLoadKGF, 2, accuracy: 0.0001)
        XCTAssertEqual(measurement.leftShare, 0, accuracy: 0.0001)
        XCTAssertEqual(measurement.rightShare, 1, accuracy: 0.0001)
    }

    func testMeasurementSideLoadsSaturateFiniteOverflow() {
        let largestFinite = Double.greatestFiniteMagnitude
        let measurement = measurement(
            sensorLoads: [largestFinite, largestFinite, largestFinite, largestFinite],
            aggregate: largestFinite
        )

        XCTAssertEqual(measurement.leftLoadKGF, largestFinite)
        XCTAssertEqual(measurement.rightLoadKGF, largestFinite)
        XCTAssertTrue(measurement.leftLoadKGF.isFinite)
        XCTAssertTrue(measurement.rightLoadKGF.isFinite)
        XCTAssertEqual(measurement.leftShare, 0.5, accuracy: 0.0001)
        XCTAssertEqual(measurement.rightShare, 0.5, accuracy: 0.0001)
    }

    func testMeasurementBodyweightPercentageReturnsZeroForInvalidBaseline() {
        let measurement = measurement(sensorLoads: [2.5, 2.5, 2.5, 2.5], aggregate: 10)

        XCTAssertEqual(measurement.bodyweightPercentage(for: 0), 0, accuracy: 0.0001)
        XCTAssertEqual(measurement.bodyweightPercentage(for: .nan), 0, accuracy: 0.0001)
        XCTAssertEqual(measurement.bodyweightPercentage(for: .infinity), 0, accuracy: 0.0001)
    }

    func testMeasurementBodyweightPercentageSaturatesFiniteOverflow() {
        let largestFinite = Double.greatestFiniteMagnitude
        let measurement = measurement(sensorLoads: [], aggregate: largestFinite)

        XCTAssertEqual(measurement.bodyweightPercentage(for: 1), largestFinite)
        XCTAssertTrue(measurement.bodyweightPercentage(for: 1).isFinite)
    }

    func testBodyweightCaptureDurationDefaultsClampsAndPersists() {
        let suite = "MotherboardModelsBodyweightDurationTests"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)

        let initial = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(initial.bodyweightCaptureDuration, 5, accuracy: 0.0001)

        defaults.set(1, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 3, accuracy: 0.0001)
        defaults.set(20, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 10, accuracy: 0.0001)
        defaults.set(Double.nan, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 5, accuracy: 0.0001)
        defaults.set(Double.infinity, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 5, accuracy: 0.0001)
        defaults.set(7.6, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 8, accuracy: 0.0001)

        initial.bodyweightCaptureDuration = 1
        XCTAssertEqual(initial.bodyweightCaptureDuration, 3, accuracy: 0.0001)
        initial.bodyweightCaptureDuration = 7.4
        XCTAssertEqual(initial.bodyweightCaptureDuration, 7, accuracy: 0.0001)
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 7, accuracy: 0.0001)
    }

    func testMeasurementRoundTripsRawADCValuesThroughCodable() throws {
        let measurement = MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: 123),
            sampleNumber: 42,
            batteryValue: 88,
            rawADCValues: [0x000102, -2, 0x7FFFFF, -0x800000],
            sensorLoadsKGF: [1.25, -0.5, 3.75, 0],
            aggregateLoadKGF: 4.5
        )

        let decoded = try JSONDecoder().decode(
            MotherboardMeasurement.self,
            from: JSONEncoder().encode(measurement)
        )

        XCTAssertEqual(decoded, measurement)
    }

    func testMeasurementDecodesWithoutRawADCValues() throws {
        let measurement = MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: 123),
            sampleNumber: 42,
            batteryValue: 88,
            rawADCValues: [1, 2, 3, 4],
            sensorLoadsKGF: [1.25, -0.5, 3.75, 0],
            aggregateLoadKGF: 4.5
        )
        let data = try JSONEncoder().encode(measurement)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object.removeValue(forKey: "rawADCValues")

        let decoded = try JSONDecoder().decode(
            MotherboardMeasurement.self,
            from: JSONSerialization.data(withJSONObject: object)
        )

        XCTAssertEqual(decoded.timestamp, measurement.timestamp)
        XCTAssertEqual(decoded.sampleNumber, measurement.sampleNumber)
        XCTAssertEqual(decoded.batteryValue, measurement.batteryValue)
        XCTAssertEqual(decoded.rawADCValues, [])
        XCTAssertEqual(decoded.sensorLoadsKGF, measurement.sensorLoadsKGF)
        XCTAssertEqual(decoded.aggregateLoadKGF, measurement.aggregateLoadKGF)
    }

    func testSessionRecordRejectsMissingV2CollectionsAndStepTitles() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )
        let data = try JSONEncoder().encode(record)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object.removeValue(forKey: "motherboardMeasurements")
        object.removeValue(forKey: "motherboardMeasurementsTruncated")
        object.removeValue(forKey: "stepTitles")

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutSessionRecord.self,
                from: JSONSerialization.data(withJSONObject: object)
            )
        )
    }

    func testSessionRecordRejectsMissingV2LoadAdjustment() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )
        let data = try JSONEncoder().encode(record)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object.removeValue(forKey: "loadAdjustmentKGF")

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutSessionRecord.self,
                from: JSONSerialization.data(withJSONObject: object)
            )
        )
    }

    func testSessionRecordRoundTripsSignedLoadAdjustmentInKilogramsForce() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [],
            loadAdjustmentKGF: -12.5
        )

        let decoded = try JSONDecoder().decode(
            WorkoutSessionRecord.self,
            from: JSONEncoder().encode(record)
        )

        XCTAssertEqual(decoded.loadAdjustmentKGF, -12.5, accuracy: 0.0001)
    }

    func testSessionRecordRoundTripsLoadAdjustmentDisplayUnit() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [],
            loadAdjustmentKGF: 10,
            loadAdjustmentDisplayUnit: .pounds
        )

        let decoded = try JSONDecoder().decode(
            WorkoutSessionRecord.self,
            from: JSONEncoder().encode(record)
        )

        XCTAssertEqual(decoded.loadAdjustmentKGF, 10, accuracy: 0.0001)
        XCTAssertEqual(decoded.loadAdjustmentDisplayUnit, .pounds)
    }

    func testSessionRecordRejectsMissingV2LoadAdjustmentDisplayUnit() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )
        let data = try JSONEncoder().encode(record)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object.removeValue(forKey: "loadAdjustmentDisplayUnit")

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutSessionRecord.self,
                from: JSONSerialization.data(withJSONObject: object)
            )
        )
    }

    func testSessionRecordRoundTripsRecordedStepTitles() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [],
            stepTitles: ["Maximum hang"]
        )
        let data = try JSONEncoder().encode(record)
        let decoded = try JSONDecoder().decode(
            WorkoutSessionRecord.self,
            from: data
        )
        let roundTrippedObject = try XCTUnwrap(
            JSONSerialization.jsonObject(with: JSONEncoder().encode(decoded)) as? [String: Any]
        )

        XCTAssertEqual(roundTrippedObject["stepTitles"] as? [String], ["Maximum hang"])
        XCTAssertEqual(decoded.stepTitle(at: 0), "Maximum hang")
    }

    func testSettingsUseDefaultsAndRoundTripThroughUserDefaults() {
        let defaults = UserDefaults(suiteName: "MotherboardModelsTests")!
        defaults.removePersistentDomain(forName: "MotherboardModelsTests")
        let first = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(first.forceUnit, .kgf)
        XCTAssertEqual(first.thresholdKGF, 2.5, accuracy: 0.0001)

        first.forceUnit = .newtons
        first.thresholdKGF = 4.25
        let second = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(second.forceUnit, .newtons)
        XCTAssertEqual(second.thresholdKGF, 4.25, accuracy: 0.0001)
    }

    func testLoadAdjustmentUnitDefaultsToKilogramsAndRoundTripsIndependentlyOfForceUnit() {
        let suite = "MotherboardModelsLoadAdjustmentUnitTests"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)

        let first = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(first.loadAdjustmentUnit, .kilograms)

        first.loadAdjustmentUnit = .pounds
        first.forceUnit = .newtons

        let second = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(second.loadAdjustmentUnit, .pounds)
        XCTAssertEqual(second.forceUnit, .newtons)
    }

    func testForceSensorProfileDefaultsToAutomaticAndRoundTripsThroughUserDefaults() {
        let suite = "MotherboardModelsForceSensorProfileTests"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)

        let first = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(first.forceSensorProfile, .automatic)

        first.forceSensorProfile = .genericProgressor
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).forceSensorProfile, .genericProgressor)

        defaults.set("unsupported-profile", forKey: "motherboard.forceSensorProfile")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).forceSensorProfile, .automatic)
    }

    func testSessionRecordRejectsMissingV2ForceSensorProfile() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "legacy-plan",
            planTitle: "Legacy plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 60),
            motherboardIdentifier: "Motherboard-1",
            batteryValue: 80,
            steps: []
        )
        let data = try JSONEncoder().encode(record)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object.removeValue(forKey: "forceSensorProfile")

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutSessionRecord.self,
                from: JSONSerialization.data(withJSONObject: object)
            )
        )
    }

    func testSessionRecordRejectsUnsupportedV2ForceSensorProfile() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "future-profile-plan",
            planTitle: "Future profile plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 60),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )
        let data = try JSONEncoder().encode(record)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object["forceSensorProfile"] = "future-force-sensor"

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutSessionRecord.self,
                from: JSONSerialization.data(withJSONObject: object)
            )
        )
    }

    func testSessionRecordRoundTripsForceSensorProfileThroughCodable() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 60),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [],
            forceSensorProfile: .genericWHC06
        )

        let decoded = try JSONDecoder().decode(
            WorkoutSessionRecord.self,
            from: JSONEncoder().encode(record)
        )

        XCTAssertEqual(decoded.forceSensorProfile, .genericWHC06)
    }

    func testThresholdNormalizesPersistedAndAssignedValuesToUIRange() {
        let suite = "MotherboardModelsThresholdTests"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        defaults.set(75.0, forKey: "motherboard.thresholdKGF")

        let store = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(store.thresholdKGF, 50, accuracy: 0.0001)

        store.thresholdKGF = 0
        XCTAssertEqual(store.thresholdKGF, 2.5, accuracy: 0.0001)
        store.thresholdKGF = 75
        XCTAssertEqual(store.thresholdKGF, 50, accuracy: 0.0001)
        store.thresholdKGF = .infinity
        XCTAssertEqual(store.thresholdKGF, 2.5, accuracy: 0.0001)
        XCTAssertEqual(defaults.double(forKey: "motherboard.thresholdKGF"), 2.5, accuracy: 0.0001)
    }

    func testSessionRecordRoundTripsMultipleGranularMeasurementsThroughCodable() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: "Motherboard-1",
            batteryValue: 80,
            steps: [WorkoutStepMeasurement(
                stepID: "step-1",
                plannedActiveDuration: 7,
                intervals: [LoadInterval(start: 1, end: 6)],
                peakLoadKGF: 12,
                sampleCount: 150,
                status: .measured
            )],
            motherboardMeasurements: [
                MotherboardMeasurement(
                    timestamp: Date(timeIntervalSince1970: 120),
                    sampleNumber: 101,
                    batteryValue: 79,
                    rawADCValues: [120, -121, 122, -123],
                    sensorLoadsKGF: [1.5, 2.5, 3.5, 4.5],
                    aggregateLoadKGF: 12
                ),
                MotherboardMeasurement(
                    timestamp: Date(timeIntervalSince1970: 121),
                    sampleNumber: 102,
                    batteryValue: 78,
                    rawADCValues: [220, -221, 222, -223],
                    sensorLoadsKGF: [5.5, 6.5, 7.5, 8.5],
                    aggregateLoadKGF: 28
                )
            ],
            motherboardMeasurementsTruncated: true
        )
        let data = try JSONEncoder().encode(record)
        XCTAssertEqual(try JSONDecoder().decode(WorkoutSessionRecord.self, from: data), record)
        XCTAssertTrue(try JSONDecoder().decode(WorkoutSessionRecord.self, from: data).motherboardMeasurementsTruncated)
    }

    func testGranularMeasurementCollectorExcludesSetupAndPausedSamples() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let measurement = granularMeasurement(sampleNumber: 1, at: 100, load: 8)

        collector.capture(
            measurement,
            startedAt: nil,
            countdownRemaining: 0,
            workoutElapsed: 0,
            planDuration: 10
        )

        XCTAssertTrue(collector.measurements.isEmpty)
    }

    func testGranularMeasurementCollectorExcludesPreCountdownSamples() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)

        collector.capture(
            granularMeasurement(sampleNumber: 1, at: 99, load: 8),
            startedAt: startedAt,
            countdownRemaining: 1,
            workoutElapsed: 0,
            planDuration: 10
        )

        XCTAssertTrue(collector.measurements.isEmpty)
    }

    func testGranularMeasurementCollectorIncludesActiveAndRestIntervalSamples() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)
        let activeSample = granularMeasurement(sampleNumber: 1, at: 102, load: 8)
        let restSample = granularMeasurement(sampleNumber: 2, at: 106, load: 0)

        collector.capture(
            activeSample,
            startedAt: startedAt,
            countdownRemaining: 0,
            workoutElapsed: 2,
            planDuration: 10
        )
        collector.capture(
            restSample,
            startedAt: startedAt,
            countdownRemaining: 0,
            workoutElapsed: 6,
            planDuration: 10
        )

        XCTAssertEqual(collector.measurements, [activeSample, restSample])
    }

    func testGranularMeasurementCollectorExcludesSamplesAfterPlanDuration() {
        var collector = MotherboardWorkoutMeasurementCollector()

        collector.capture(
            granularMeasurement(sampleNumber: 1, at: 110, load: 8),
            startedAt: Date(timeIntervalSince1970: 100),
            countdownRemaining: 0,
            workoutElapsed: 10,
            planDuration: 10
        )

        XCTAssertTrue(collector.measurements.isEmpty)
    }

    func testGranularMeasurementCollectorCapsEligibleSamplesAndReportsTruncation() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)

        for sampleNumber in 0...20_000 {
            collector.capture(
                granularMeasurement(sampleNumber: UInt16(sampleNumber), at: 101, load: 1),
                startedAt: startedAt,
                countdownRemaining: 0,
                workoutElapsed: 1,
                planDuration: 10
            )
        }

        XCTAssertEqual(collector.measurements.count, 20_000)
        XCTAssertTrue(collector.didTruncate)
        XCTAssertEqual(collector.measurements.last?.sampleNumber, 19_999)
    }

    func testGranularMeasurementCollectorResetClearsMeasurementsAndTruncation() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)

        for sampleNumber in 0...20_000 {
            collector.capture(
                granularMeasurement(sampleNumber: UInt16(sampleNumber), at: 101, load: 1),
                startedAt: startedAt,
                countdownRemaining: 0,
                workoutElapsed: 1,
                planDuration: 10
            )
        }

        collector.reset()

        XCTAssertTrue(collector.measurements.isEmpty)
        XCTAssertFalse(collector.didTruncate)
    }

    func testGranularMeasurementCollectorAppendsEveryEligiblePublicationWithoutLoadFiltering() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)
        let samples = [
            granularMeasurement(sampleNumber: 1, at: 101, load: 0),
            granularMeasurement(sampleNumber: 2, at: 102, load: 0.1),
            granularMeasurement(sampleNumber: 3, at: 103, load: 80)
        ]

        for (elapsed, sample) in zip([1.0, 2.0, 3.0], samples) {
            collector.capture(
                sample,
                startedAt: startedAt,
                countdownRemaining: 0,
                workoutElapsed: elapsed,
                planDuration: 10
            )
        }

        XCTAssertEqual(collector.measurements, samples)
    }

    func testRestStepsAreDistinctFromActiveStepsWhenTheirFullDurationIsRest() {
        let rest = WorkoutStep(
            id: "rest",
            number: 1,
            title: "Rest",
            instruction: "Shake out.",
            accessory: "Recovery",
            duration: 10,
            phase: .rest)
        let hang = WorkoutStep(
            id: "hang",
            number: 2,
            title: "Hang",
            instruction: "Hang on.",
            accessory: "Active",
            duration: 10,
            phase: .hang)

        XCTAssertEqual(rest.activeDuration, rest.duration)
        XCTAssertTrue(rest.isRestStep)
        XCTAssertFalse(hang.isRestStep)
    }

    func testSessionStepMeasurementDefaultsAndRoundTripsUnilateralSemantics() throws {
        let measurement = WorkoutStepMeasurement(
            stepID: "left-lift",
            plannedActiveDuration: 10,
            intervals: [],
            peakLoadKGF: nil,
            sampleCount: 0,
            status: .unmeasured,
            handUse: .single,
            side: .left,
            action: .loadedLift,
            repetitions: 7,
            externalLoadKGF: -8,
            isRest: false
        )
        let data = try JSONEncoder().encode(measurement)
        var legacyObject = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        legacyObject.removeValue(forKey: "handUse")
        legacyObject.removeValue(forKey: "side")
        legacyObject.removeValue(forKey: "action")
        legacyObject.removeValue(forKey: "repetitions")
        legacyObject.removeValue(forKey: "externalLoadKGF")
        legacyObject.removeValue(forKey: "isRest")

        let decoded = try JSONDecoder().decode(WorkoutStepMeasurement.self, from: data)
        let legacy = try JSONDecoder().decode(
            WorkoutStepMeasurement.self,
            from: JSONSerialization.data(withJSONObject: legacyObject)
        )

        XCTAssertEqual(decoded, measurement)
        XCTAssertEqual(legacy.handUse, .double)
        XCTAssertEqual(legacy.side, .both)
        XCTAssertEqual(legacy.action, .hang)
        XCTAssertNil(legacy.repetitions)
        XCTAssertNil(legacy.externalLoadKGF)
        XCTAssertFalse(legacy.isRest)
    }

    private func measurement(sensorLoads: [Double], aggregate: Double) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: 0),
            sampleNumber: 1,
            batteryValue: 100,
            sensorLoadsKGF: sensorLoads,
            aggregateLoadKGF: aggregate
        )
    }

    private func granularMeasurement(
        sampleNumber: UInt16,
        at time: TimeInterval,
        load: Double
    ) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: time),
            sampleNumber: sampleNumber,
            batteryValue: 80,
            rawADCValues: [1, -2, 3, -4],
            sensorLoadsKGF: [load, 0, 0, 0],
            aggregateLoadKGF: load
        )
    }
}
