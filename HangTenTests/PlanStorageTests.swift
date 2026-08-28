import XCTest
@testable import HangTen

final class PlanStorageTests: XCTestCase {
    func testPlanLibraryStoreRejectsFormerSchemaVersionField() throws {
        let data = Data(
            #"""
            {
              "schemaVersion": 3,
              "metadata": {
                "id": "legacy.plan-library",
                "title": "Legacy plan library",
                "generatedAt": "2026-08-24",
                "notes": []
              },
              "boardMappings": [],
              "blocks": [],
              "plans": []
            }
            """#.utf8
        )

        XCTAssertThrowsError(try PlanLibraryStore(data: data))
    }

    func testPlanLibraryStoreRejectsFormerMetadataVersionField() throws {
        let data = Data(
            #"""
            {
              "metadata": {
                "id": "legacy.plan-library",
                "version": "3.0.0",
                "title": "Legacy plan library",
                "generatedAt": "2026-08-24",
                "notes": []
              },
              "boardMappings": [],
              "blocks": [],
              "plans": []
            }
            """#.utf8
        )

        XCTAssertThrowsError(try PlanLibraryStore(data: data))
    }

    func testPlanLibraryStoreEncodingOmitsFormerVersionFields() throws {
        let store = try PlanLibraryStore(
            definition: makeLibrary(
                steps: [
                    makeStep(
                        id: "conditioning",
                        duration: 30,
                        phase: .conditioning,
                        targets: [],
                        segments: []
                    )
                ]
            )
        )
        let document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: try store.encodedData()) as? [String: Any]
        )
        let metadata = try XCTUnwrap(document["metadata"] as? [String: Any])

        XCTAssertNil(document["schemaVersion"])
        XCTAssertNil(metadata["version"])
    }

    func testBundledPlanLibraryLoadsWithoutFormerFeatureAliases() throws {
        let data = try bundledPlanLibraryData()
        let document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
        let metadata = try XCTUnwrap(document["metadata"] as? [String: Any])

        XCTAssertNil(document["schemaVersion"])
        XCTAssertNil(metadata["version"])
        XCTAssertEqual(fallbackFeatureAliases(in: document), [])
        XCTAssertNoThrow(
            try PlanLibraryStore(
                builtInData: data,
                packageStore: BoardCatalog.packageStore
            )
        )
    }

    func testBuiltInPlanPresentationFieldsUseAthleteFacingCopy() throws {
        let store = try PlanLibraryStore(
            builtInData: bundledPlanLibraryData(),
            packageStore: BoardCatalog.packageStore
        )
        let visibleFields = store.plans.flatMap { plan in
            [plan.subtitle] + plan.steps.flatMap { [$0.instruction, $0.accessory] }
        }
        let auditNarration = [
            "app timer",
            "app default",
            "app-guided",
            "app recovery",
            "source range",
            "no source count",
            "source's",
            "source does not prescribe",
            "source gives no",
            "guided default",
            "adaptation",
            "semantic",
            "app choices",
            "app uses"
        ]

        XCTAssertEqual(
            visibleFields.filter { field in
                let normalized = field.lowercased()
                return auditNarration.contains { normalized.contains($0) }
            },
            [],
            "Built-in plan fields must state the workout, not its audit history."
        )
    }

    func testInstructionAccessoryContentPreservesSourceBackedPlanText() {
        let rows = InstructionAccessoryCardContent.rows(
            instruction: "Nice work on the prescribed 7-second hang.",
            accessory: "Step off and shake out for the prescribed 3-minute recovery."
        )

        XCTAssertEqual(
            rows,
            [
                InstructionAccessoryCardRow(kind: .instruction, text: "Nice work on the prescribed 7-second hang."),
                InstructionAccessoryCardRow(kind: .accessory, text: "Step off and shake out for the prescribed 3-minute recovery.")
            ]
        )
    }

    func testBundledF80PreservesForceFeedbackAndStopRule() throws {
        let store = try PlanLibraryStore(
            builtInData: bundledPlanLibraryData(),
            packageStore: BoardCatalog.packageStore
        )
        let plan = try XCTUnwrap(store.plan(id: "research.force-feedback-f80"))
        let hangSteps = plan.steps.filter {
            $0.id.hasPrefix("f80-set-") && $0.phase == .hang
        }

        XCTAssertEqual(hangSteps.count, 36)
        XCTAssertTrue(hangSteps.allSatisfy { $0.activeDuration == 10 })
        XCTAssertTrue(plan.subtitle.lowercased().contains("three sets"))
        XCTAssertTrue(plan.subtitle.contains("12"))
        XCTAssertTrue(plan.subtitle.contains("80% MFSi"))
        XCTAssertTrue(hangSteps.allSatisfy { $0.instruction.contains("real-time force feedback") })
        XCTAssertTrue(hangSteps.allSatisfy { $0.instruction.contains("instrumented 12 mm edge") })
        XCTAssertTrue(hangSteps.allSatisfy { $0.instruction.contains("Stop the set if force falls below 70% MFSi.") })
    }

    func testBundledF100PreservesForceFeedbackProtocolFacts() throws {
        let store = try PlanLibraryStore(
            builtInData: bundledPlanLibraryData(),
            packageStore: BoardCatalog.packageStore
        )
        let plan = try XCTUnwrap(store.plan(id: "research.force-feedback-f100"))
        let hangSteps = plan.steps.filter {
            $0.id.hasPrefix("f100-set-") && $0.phase == .hang
        }

        XCTAssertEqual(hangSteps.count, 24)
        XCTAssertTrue(hangSteps.allSatisfy { $0.activeDuration == 6 })
        XCTAssertTrue(plan.subtitle.lowercased().contains("two sets"))
        XCTAssertTrue(plan.subtitle.contains("six 6-second hangs per hand"))
        XCTAssertTrue(plan.subtitle.contains("6-second"))
        XCTAssertTrue(hangSteps.allSatisfy { $0.instruction.contains("real-time force feedback") })
        XCTAssertTrue(hangSteps.allSatisfy { $0.instruction.contains("instrumented 12 mm edge") })
    }

    func testWorkoutCueCardShowsSourceInstructionDuringCountdown() {
        let step = WorkoutStep(id: "step", number: 1, title: "Source title", instruction: "Source instruction", accessory: "Source accessory", duration: 10, phase: .hang, targets: [])

        XCTAssertEqual(WorkoutPresentationContent.title(step: step, isComplete: false), "Source title")
        XCTAssertEqual(
            WorkoutPresentationContent.cueCardRows(step: step, countdown: 3, isComplete: false),
            [
                InstructionAccessoryCardRow(kind: .instruction, text: "Source instruction")
            ]
        )
    }

    func testWorkoutCueCardIsOmittedAfterCompletion() {
        let step = WorkoutStep(id: "step", number: 1, title: "Source title", instruction: "Source instruction", accessory: "Source accessory", duration: 10, phase: .hang, targets: [])

        XCTAssertEqual(WorkoutPresentationContent.title(step: step, isComplete: true), "Session complete")
        XCTAssertNil(WorkoutPresentationContent.cueCardRows(step: step, countdown: 0, isComplete: true))
    }

    func testForceFeedbackPlansAreUnavailableUntilInstrumentedEdgeSetupCanBeVerified() {
        for plan in [LegacyPlanSeedCatalog.forceF80, LegacyPlanSeedCatalog.forceF100] {
            XCTAssertEqual(
                PlanStartAvailabilityPolicy.availability(for: plan),
                .unavailable(requirement: "Requires real-time force feedback from an instrumented 12 mm edge.")
            )
        }
    }

    func testOrdinaryPlanRemainsAvailableToStart() {
        XCTAssertEqual(
            PlanStartAvailabilityPolicy.availability(for: LegacyPlanSeedCatalog.maxHangs),
            .available
        )
    }

    func testPlanSourcePresentationContainsOnlySourceName() {
        let plan = LegacyPlanSeedCatalog.maxHangs
        XCTAssertEqual(PlanSourcePresentationContent.label(for: plan), "Source: Lattice max hang protocol")
    }

    func testBuiltInPlanDataPreservesPlanOwnedMappingsAndResolvesEdge19() throws {
        let packageStore = BoardCatalog.packageStore
        let store = try PlanLibraryStore(
            builtInData: bundledPlanLibraryData(),
            packageStore: packageStore
        )
        let compactMapping = try XCTUnwrap(
            store.definition.boardMappings.first {
                $0.boardID == "metolius.wood-grips-compact-ii"
            }
        )
        let expectedHoldIDs = ["edge-19-left", "edge-19-right"]

        XCTAssertEqual(
            compactMapping.semanticHolds["edge-19"]?.holdIDs,
            expectedHoldIDs
        )
        XCTAssertEqual(packageStore.semantics(for: compactMapping.boardID), [:])
        XCTAssertEqual(
            store.plan(id: "research.max-hangs")?.steps.first?.targets,
            [.feature(.mediumEdge, fallback: .largeEdge)]
        )
    }

    func testBuiltInMigrationDefinitionKeepsThePlanOwnedFallbackMapping() throws {
        let generated = BuiltInPlanLibraryDefinition.document
        let bundled = try JSONDecoder().decode(
            PlanLibraryDefinition.self,
            from: bundledPlanLibraryData()
        )

        XCTAssertEqual(generated.boardMappings, bundled.boardMappings)
        XCTAssertNoThrow(
            try PlanLibraryStore(
                builtInDefinition: generated,
                packageStore: BoardCatalog.packageStore
            )
        )
    }

    func testGripTypeRoundTripsDistinctCurrentRawValues() throws {
        for gripType in GripType.allCases {
            let encoded = try JSONEncoder().encode(gripType)
            let encodedRawValue = try JSONDecoder().decode(String.self, from: encoded)
            let decoded = try JSONDecoder().decode(GripType.self, from: encoded)

            XCTAssertEqual(encodedRawValue, gripType.rawValue)
            XCTAssertEqual(decoded, gripType)
        }
    }

    func testGripTypeRejectsUnknownRawValues() {
        XCTAssertThrowsError(
            try JSONDecoder().decode(GripType.self, from: Data(#""campusing""#.utf8))
        )
    }

    func testLegacyPocketFeatureTargetDecodesAndReencodesAsKindTarget() throws {
        let legacy = Data(#"{ "feature": "pocket", "fingerCapacity": 3 }"#.utf8)

        let target = try JSONDecoder().decode(WorkoutTargetDefinition.self, from: legacy)
        let encoded = try JSONEncoder().encode(target)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["kind"] as? String, "pocket")
        XCTAssertEqual(object["fingerCapacity"] as? Int, 3)
        XCTAssertNil(object["feature"])
    }

    func testJugFeatureTargetEncodesAsCanonicalKindTarget() throws {
        let target = WorkoutTargetDefinition.feature(.jug, fallbacks: [])
        let encoded = try JSONEncoder().encode(target)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["kind"] as? String, "jug")
        XCTAssertNil(object["feature"])
    }

    func testLegacyDuplicateFallbackFeaturesAreDroppedWhenEncodingKindTarget() throws {
        let legacy = Data(
            #"{ "feature": "pocket", "fingerCapacity": 3, "fallbackFeatures": ["jug", "pocket"] }"#.utf8
        )

        let target = try JSONDecoder().decode(WorkoutTargetDefinition.self, from: legacy)
        let encoded = try JSONEncoder().encode(target)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["kind"] as? String, "pocket")
        XCTAssertEqual(object["fingerCapacity"] as? Int, 3)
        XCTAssertNil(object["fallbackFeatures"])
    }

    func testLegacyDuplicateFallbackFeaturesAreDroppedWhileValidFeatureFallbacksRemain() throws {
        let legacy = Data(
            #"{ "feature": "mediumEdge", "fallbackFeatures": ["jug", "largeEdge", "pocket"] }"#.utf8
        )

        let target = try JSONDecoder().decode(WorkoutTargetDefinition.self, from: legacy)
        let encoded = try JSONEncoder().encode(target)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["feature"] as? String, "mediumEdge")
        XCTAssertEqual(object["fallbackFeatures"] as? [String], ["largeEdge"])
    }

    func testUnknownFallbackFeatureIsRejected() {
        let invalid = Data(#"{ "feature": "mediumEdge", "fallbackFeatures": ["unknownFeature"] }"#.utf8)

        XCTAssertThrowsError(
            try JSONDecoder().decode(WorkoutTargetDefinition.self, from: invalid)
        )
    }

    func testCanonicalPocketKindTargetRetainsFingerCapacityWhenEncoded() throws {
        let canonical = Data(#"{ "kind": "pocket", "fingerCapacity": 3 }"#.utf8)

        let target = try JSONDecoder().decode(WorkoutTargetDefinition.self, from: canonical)
        let encoded = try JSONEncoder().encode(target)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["kind"] as? String, "pocket")
        XCTAssertEqual(object["fingerCapacity"] as? Int, 3)
    }

    func testWorkoutTargetDefinitionRejectsOutOfRangeDecodedFingerCapacities() {
        for invalidCapacity in [0, 5] {
            let payload = Data(#"{ "kind": "pocket", "fingerCapacity": \#(invalidCapacity) }"#.utf8)

            XCTAssertThrowsError(
                try JSONDecoder().decode(WorkoutTargetDefinition.self, from: payload)
            ) { error in
                guard case let DecodingError.dataCorrupted(context) = error else {
                    return XCTFail("Expected invalid finger capacity to produce a data-corrupted decoding error, got: \(error)")
                }

                XCTAssertEqual(context.codingPath.last?.stringValue, "fingerCapacity")
            }
        }
    }

    func testWorkoutTargetDefinitionAcceptsValidAndAbsentDecodedFingerCapacities() throws {
        let cases: [(Data, WorkoutTargetDefinition)] = [
            (Data(#"{ "kind": "pocket", "fingerCapacity": 1 }"#.utf8), .kind(.pocket, fingerCapacity: 1)),
            (Data(#"{ "kind": "pocket", "fingerCapacity": 4 }"#.utf8), .kind(.pocket, fingerCapacity: 4)),
            (Data(#"{ "kind": "pocket" }"#.utf8), .kind(.pocket))
        ]

        for (payload, expectedTarget) in cases {
            XCTAssertEqual(
                try JSONDecoder().decode(WorkoutTargetDefinition.self, from: payload),
                expectedTarget
            )
        }
    }

    func testFingerConfigurationRejectsEmptyConstructionAndDecodedPayloads() throws {
        XCTAssertNil(FingerConfiguration(engagedFingers: []))

        let emptyPayload = Data(#"{ "engagedFingers": [] }"#.utf8)
        XCTAssertThrowsError(try JSONDecoder().decode(FingerConfiguration.self, from: emptyPayload))
    }

    func testFingerConfigurationRejectsDuplicateEngagedFingersInDecodedPayload() throws {
        let duplicatePayload = Data(#"{ "engagedFingers": ["index", "index"] }"#.utf8)

        XCTAssertThrowsError(try JSONDecoder().decode(FingerConfiguration.self, from: duplicatePayload)) { error in
            guard case let DecodingError.dataCorrupted(context) = error else {
                return XCTFail("Expected duplicate fingers to produce a data-corrupted decoding error, got: \(error)")
            }

            XCTAssertEqual(context.codingPath.last?.stringValue, "engagedFingers")
            XCTAssertEqual(context.debugDescription, "Finger configuration cannot include duplicate fingers.")
        }
    }

    func testFingerConfigurationRoundTripsExactFingerSetsInSlotOrder() throws {
        let configurations = [
            try XCTUnwrap(FingerConfiguration(engagedFingers: [.pinky])),
            try XCTUnwrap(FingerConfiguration(engagedFingers: [.index, .ring]))
        ]

        let data = try JSONEncoder().encode(configurations)
        let decoded = try JSONDecoder().decode([FingerConfiguration].self, from: data)

        XCTAssertEqual(decoded, configurations)
        XCTAssertEqual(decoded[0].count, 1)
        XCTAssertEqual(decoded[0].orderedFingers, [.pinky])
        XCTAssertEqual(decoded[1].count, 2)
        XCTAssertEqual(decoded[1].orderedFingers, [.index, .ring])
        XCTAssertEqual(
            try JSONSerialization.jsonObject(with: data) as? [[String: [String]]],
            [
                ["engagedFingers": ["pinky"]],
                ["engagedFingers": ["index", "ring"]]
            ]
        )
    }

    func testWorkoutStepDefinitionRoundTripsFingerConfigurationWithDistinctPocketGripVocabulary() throws {
        let data = Data(
            #"""
            {
              "id": "exact-fingers",
              "title": "Exact fingers",
              "instruction": "Use index and ring.",
              "accessory": "Test fixture",
              "duration": 10,
              "phase": "hang",
              "targets": [],
              "gripType": "threeFingerPocket",
              "fingerConfiguration": { "engagedFingers": ["index", "ring"] }
            }
            """#.utf8
        )

        let decoded = try JSONDecoder().decode(WorkoutStepDefinition.self, from: data)
        let encoded = try JSONEncoder().encode(decoded)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        let fingerConfiguration = try XCTUnwrap(object["fingerConfiguration"] as? [String: [String]])

        XCTAssertEqual(decoded.gripType, .threeFingerPocket)
        XCTAssertEqual(decoded.fingerConfiguration?.orderedFingers, [.index, .ring])
        XCTAssertEqual(object["gripType"] as? String, "threeFingerPocket")
        XCTAssertEqual(fingerConfiguration["engagedFingers"], ["index", "ring"])
    }

    func testInstructionAccessoryCardRowsOmitTrimmedEmptyFieldsWithoutChangingSourceText() {
        XCTAssertEqual(
            InstructionAccessoryCardContent.rows(
                instruction: " \n\t ",
                accessory: "  "
            ),
            []
        )
        XCTAssertEqual(
            InstructionAccessoryCardContent.rows(
                instruction: "Keep shoulders engaged.",
                accessory: "7 seconds on / 3 seconds off"
            ),
            [
                .init(kind: .instruction, text: "Keep shoulders engaged."),
                .init(kind: .accessory, text: "7 seconds on / 3 seconds off")
            ]
        )
    }

    func testUnversionedDefinitionsResolveOrderedSegmentTimingModes() throws {
        let fixedWork = WorkoutSegmentDefinition(
            kind: .work,
            targets: [.feature(.mediumEdge, fallbacks: [])],
            timing: .fixed,
            duration: 20
        )
        let fixedRest = WorkoutSegmentDefinition(
            kind: .rest,
            targets: [],
            timing: .fixed,
            duration: 40
        )
        let steps = [
            makeStep(
                id: "fixed",
                duration: 60,
                targets: [.feature(.mediumEdge, fallbacks: [])],
                segments: [fixedWork, fixedRest]
            ),
            makeStep(
                id: "stopwatch",
                duration: 60,
                targets: [.feature(.roundSloper, fallbacks: [])],
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        targets: [.feature(.roundSloper, fallbacks: [])],
                        timing: .stopwatch,
                        duration: nil
                    )
                ]
            ),
            makeStep(
                id: "undefined",
                duration: 60,
                phase: .pull,
                targets: [.kind(.jug)],
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        targets: [.kind(.jug)],
                        timing: .undefined,
                        duration: nil
                    )
                ]
            )
        ]

        let store = try PlanLibraryStore(definition: makeLibrary(steps: steps))
        let resolvedSteps = try XCTUnwrap(store.plan(id: "test.plan")).steps

        XCTAssertEqual(resolvedSteps.map(\.id), [
            "fixed.segment-1", "fixed.segment-2", "stopwatch", "undefined"
        ])
        XCTAssertEqual(resolvedSteps.map(\.number), [1, 2, 3, 4])
        XCTAssertEqual(
            resolvedSteps[0].segments,
            [WorkoutSegment(kind: .work, target: .feature(.mediumEdge), timing: .fixed, duration: 20)]
        )
        XCTAssertEqual(
            resolvedSteps[1].segments,
            [WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 40)]
        )
        XCTAssertEqual(
            resolvedSteps[2].segments,
            [WorkoutSegment(kind: .work, target: .feature(.roundSloper), timing: .stopwatch, duration: nil)]
        )
        XCTAssertEqual(
            resolvedSteps[3].segments,
            [WorkoutSegment(kind: .work, target: .kind(.jug), timing: .undefined, duration: nil)]
        )
    }

    func testSegmentTargetFixturesRoundTripOnlyPluralTargets() throws {
        let data = Data(
            #"""
            {
              "metadata": {
                "id": "segment.fixture",
                "title": "Segment fixture",
                "generatedAt": "2026-08-03",
                "notes": []
              },
              "boardMappings": [],
              "blocks": [{
                "id": "segment.block",
                "title": "Segment fixture",
                "steps": [{
                  "id": "segment.step",
                  "title": "Segment step",
                  "instruction": "Use both holds.",
                  "accessory": "10s",
                  "duration": 20,
                  "phase": "hang",
                  "targets": [{ "feature": "mediumEdge" }, { "kind": "jug" }],
                  "segments": [
                    {
                      "kind": "work",
                      "targets": [{ "feature": "mediumEdge" }, { "kind": "jug" }],
                      "timing": "fixed",
                      "duration": 10
                    },
                    {
                      "kind": "work",
                      "targets": [{ "feature": "mediumEdge" }],
                      "timing": "fixed",
                      "duration": 10
                    }
                  ]
                }]
              }],
              "plans": [{
                "id": "segment.plan",
                "metadata": {
                  "title": "Segment plan",
                  "subtitle": "Segment fixture",
                  "level": "Test",
                  "sourceLabel": "Test fixture",
                  "sourceURL": "https://example.com/segment",
                  "provenance": "adapted",
                  "category": "test",
                  "tags": [],
                  "equipment": [],
                  "notes": []
                },
                "blocks": [{ "blockID": "segment.block" }]
              }]
            }
            """#.utf8
        )

        let store = try PlanLibraryStore(data: data)
        let resolvedSteps = try XCTUnwrap(store.plan(id: "segment.plan")).steps
        let resolvedSegments = resolvedSteps.flatMap(\.segments)
        XCTAssertEqual(resolvedSteps.map(\.id), ["segment.step.segment-1", "segment.step.segment-2"])
        XCTAssertEqual(resolvedSteps.map(\.number), [1, 2])
        let encoded = try store.encodedData()
        let encodedObject = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        let encodedBlocks = try XCTUnwrap(encodedObject["blocks"] as? [[String: Any]])
        let encodedSteps = try XCTUnwrap(encodedBlocks[0]["steps"] as? [[String: Any]])
        let encodedSegments = try XCTUnwrap(encodedSteps[0]["segments"] as? [[String: Any]])
        let roundTripped = try JSONDecoder().decode(PlanLibraryDefinition.self, from: encoded)
        let persistedSegments = roundTripped.blocks[0].steps[0].segments

        XCTAssertNotNil(encodedSegments[0]["targets"])
        XCTAssertNil(encodedSegments[0]["target"])
        XCTAssertNotNil(encodedSegments[1]["targets"])
        XCTAssertNil(encodedSegments[1]["target"])
        XCTAssertEqual(
            resolvedSegments[0].targets,
            [.feature(.mediumEdge), .kind(.jug)]
        )
        XCTAssertEqual(resolvedSegments[0].target, .feature(.mediumEdge))
        XCTAssertEqual(resolvedSegments[1].targets, [.feature(.mediumEdge)])
        XCTAssertEqual(resolvedSegments[1].target, .feature(.mediumEdge))
        XCTAssertEqual(
            persistedSegments[0].targets,
            [.feature(.mediumEdge, fallbacks: []), .kind(.jug)]
        )
        XCTAssertEqual(persistedSegments[1].targets, [.feature(.mediumEdge, fallbacks: [])])
    }

    func testPlanLibraryStoreRejectsFormerSingularSegmentTarget() {
        let data = Data(
            #"""
            {
              "metadata": {
                "id": "segment.fixture",
                "title": "Segment fixture",
                "generatedAt": "2026-08-24",
                "notes": []
              },
              "boardMappings": [],
              "blocks": [{
                "id": "segment.block",
                "title": "Segment block",
                "steps": [{
                  "id": "segment.step",
                  "title": "Segment step",
                  "instruction": "Hang.",
                  "accessory": "10s",
                  "duration": 10,
                  "phase": "hang",
                  "targets": [{ "kind": "edge" }],
                  "segments": [{
                    "kind": "work",
                    "target": { "kind": "edge" },
                    "timing": "fixed",
                    "duration": 10
                  }]
                }]
              }],
              "plans": []
            }
            """#.utf8
        )

        XCTAssertThrowsError(try PlanLibraryStore(data: data))
    }

    func testUnversionedDefinitionsWithExplicitSegmentsResolveCompatibilityTiming() throws {
        let data = Data(
            #"""
            {
              "metadata": {
                "id": "legacy.fixture",
                "title": "Legacy fixture",
                "generatedAt": "2026-08-02",
                "notes": []
              },
              "boardMappings": [],
              "blocks": [{
                "id": "legacy.block",
                "title": "Legacy",
                "steps": [
                  {
                    "id": "rest",
                    "title": "Rest",
                    "instruction": "Rest",
                    "accessory": "30s",
                    "duration": 30,
                    "phase": "rest",
                    "targets": [],
                    "segments": [{
                      "kind": "rest",
                      "targets": [],
                      "timing": "fixed",
                      "duration": 30
                    }]
                  },
                  {
                    "id": "timed",
                    "title": "Timed",
                    "instruction": "Hang",
                    "accessory": "10s",
                    "duration": 30,
                    "phase": "hang",
                    "targets": [{ "kind": "edge" }],
                    "segments": [
                      {
                        "kind": "work",
                        "targets": [{ "kind": "edge" }],
                        "timing": "fixed",
                        "duration": 10
                      },
                      {
                        "kind": "rest",
                        "targets": [],
                        "timing": "fixed",
                        "duration": 20
                      }
                    ]
                  },
                  {
                    "id": "untimed",
                    "title": "Untimed",
                    "instruction": "Pull",
                    "accessory": "Repetitions",
                    "duration": 60,
                    "phase": "pull",
                    "targets": [{ "kind": "jug" }],
                    "segments": [{
                      "kind": "work",
                        "targets": [{ "kind": "jug" }],
                      "timing": "undefined"
                    }]
                  }
                ]
              }],
              "plans": [{
                "id": "legacy.plan",
                "metadata": {
                  "title": "Legacy plan",
                  "subtitle": "Compatibility fixture",
                  "level": "Test",
                  "sourceLabel": "Test fixture",
                  "sourceURL": "https://example.com/legacy",
                  "provenance": "adapted",
                  "category": "test",
                  "tags": [],
                  "equipment": [],
                  "notes": []
                },
                "blocks": [{ "blockID": "legacy.block" }]
              }]
            }
            """#.utf8
        )

        let store = try PlanLibraryStore(data: data)
        let steps = try XCTUnwrap(store.plan(id: "legacy.plan")).steps

        XCTAssertEqual(steps.map(\.id), ["rest", "timed.segment-1", "timed.segment-2", "untimed"])
        XCTAssertEqual(steps.map(\.number), [1, 2, 3, 4])
        XCTAssertEqual(
            steps[0].segments,
            [WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 30)]
        )
        XCTAssertEqual(
            steps[1].segments,
            [WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: 10)]
        )
        XCTAssertEqual(
            steps[2].segments,
            [WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 20)]
        )
        XCTAssertEqual(
            steps[3].segments,
            [WorkoutSegment(kind: .work, target: .kind(.jug), timing: .undefined, duration: nil)]
        )
    }

    func testFixedSegmentRequiresDuration() {
        let segment = WorkoutSegmentDefinition(
            kind: .work,
            targets: [.kind(.edge)],
            timing: .fixed,
            duration: nil
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].duration"
        })
    }

    func testWorkSegmentRequiresTarget() {
        let segment = WorkoutSegmentDefinition(
            kind: .work,
            targets: [],
            timing: .undefined,
            duration: nil
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].targets"
        })
    }

    func testRestSegmentCannotTargetAHold() {
        let segment = WorkoutSegmentDefinition(
            kind: .rest,
            targets: [.kind(.edge)],
            timing: .fixed,
            duration: 30
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].targets"
        })
    }

    func testRestSegmentRequiresDurationRegardlessOfTiming() {
        let segment = WorkoutSegmentDefinition(
            kind: .rest,
            targets: [],
            timing: .undefined,
            duration: nil
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].duration"
        })
    }

    func testRestSegmentRequiresFixedTiming() {
        let segment = WorkoutSegmentDefinition(
            kind: .rest,
            targets: [],
            timing: .undefined,
            duration: 30
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].timing"
        })
    }

    func testStopwatchSegmentCannotHaveDuration() {
        let segment = WorkoutSegmentDefinition(
            kind: .work,
            targets: [.kind(.edge)],
            timing: .stopwatch,
            duration: 10
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].duration"
        })
    }

    func testUndefinedSegmentCannotHaveDuration() {
        let segment = WorkoutSegmentDefinition(
            kind: .work,
            targets: [.kind(.edge)],
            timing: .undefined,
            duration: 10
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].duration"
        })
    }

    func testSegmentDurationMustBeFiniteAndNonnegative() {
        for invalidDuration in [-1.0, .infinity] {
            let segment = WorkoutSegmentDefinition(
                kind: .work,
                targets: [.kind(.edge)],
                timing: .fixed,
                duration: invalidDuration
            )

            XCTAssertTrue(validationIssues(for: segment).contains {
                $0.path == "blocks[0].steps[0].segments[0].duration"
            })
        }
    }

    func testActiveDurationMustBeFiniteAndGreaterThanZero() {
        for invalidDuration in [0.0, -1.0, .infinity] {
            let step = WorkoutStepDefinition(
                id: "active",
                title: "Active",
                instruction: "Hang.",
                accessory: "Test fixture",
                duration: 30,
                phase: .hang,
                targets: [.kind(.edge)],
                activeDuration: invalidDuration
            )

            XCTAssertTrue(makeLibrary(steps: [step]).validationIssues(availableBoards: BoardCatalog.all).contains {
                $0.path == "blocks[0].steps[0].activeDuration" &&
                    $0.message == "Active duration must be finite and greater than zero."
            })
        }
    }

    func testSegmentDurationCannotExceedEnclosingStep() {
        let segment = WorkoutSegmentDefinition(
            kind: .work,
            targets: [.kind(.edge)],
            timing: .fixed,
            duration: 31
        )

        XCTAssertTrue(validationIssues(for: segment, stepDuration: 30).contains {
            $0.path == "blocks[0].steps[0].segments[0].duration"
        })
    }

    func testCompoundSegmentsMustSumToTheEnclosingStepDuration() {
        let issues = makeLibrary(
            steps: [
                makeStep(
                    id: "compound",
                    duration: 30,
                    targets: [.kind(.edge)],
                    segments: [
                        WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .fixed, duration: 20),
                        WorkoutSegmentDefinition(kind: .rest, targets: [], timing: .fixed, duration: 5)
                    ]
                )
            ]
        ).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "blocks[0].steps[0].duration" &&
                $0.message == "Compound segment durations must equal the total step duration."
        })
    }

    func testCompoundSegmentDurationMustBeGreaterThanZero() {
        let issues = makeLibrary(
            steps: [
                makeStep(
                    id: "compound",
                    duration: 30,
                    targets: [.kind(.edge)],
                    segments: [
                        WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .fixed, duration: 0),
                        WorkoutSegmentDefinition(kind: .rest, targets: [], timing: .fixed, duration: 30)
                    ]
                )
            ]
        ).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "blocks[0].steps[0].segments[0].duration" &&
                $0.message == "Segment duration must be finite and greater than zero."
        })
    }

    func testCompoundEnclosingDurationMustBeGreaterThanZero() {
        let issues = makeLibrary(
            steps: [
                makeStep(
                    id: "compound",
                    duration: 0,
                    targets: [.kind(.edge)],
                    segments: [
                        WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .fixed, duration: 5),
                        WorkoutSegmentDefinition(kind: .rest, targets: [], timing: .fixed, duration: 5)
                    ]
                )
            ]
        ).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "blocks[0].steps[0].duration" &&
                $0.message == "Duration must be finite and greater than zero."
        })
    }

    func testPlanValidationDetectsGeneratedSegmentIDCollisionWithFlatStep() {
        let issues = makeLibrary(
            steps: [
                makeStep(
                    id: "foo",
                    duration: 30,
                    targets: [.kind(.edge)],
                    segments: [
                        WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .fixed, duration: 20),
                        WorkoutSegmentDefinition(kind: .rest, targets: [], timing: .fixed, duration: 10)
                    ]
                ),
                makeStep(
                    id: "foo.segment-1",
                    duration: 10,
                    targets: [.kind(.edge)],
                    segments: [
                        WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .fixed, duration: 10)
                    ]
                )
            ]
        ).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "plans[0].blocks[0]" &&
            $0.message == "Expanded step ID \"foo.segment-1\" is repeated in the plan."
        })
    }

    func testCompoundSegmentWithNonFixedTimingReportsTheTimingPath() {
        let issues = makeLibrary(
            steps: [
                makeStep(
                    id: "compound",
                    duration: 30,
                    targets: [.kind(.edge)],
                    segments: [
                        WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .stopwatch, duration: nil),
                        WorkoutSegmentDefinition(kind: .rest, targets: [], timing: .fixed, duration: 30)
                    ]
                )
            ]
        ).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "blocks[0].steps[0].segments[0].timing" &&
                $0.message == "Compound segments must use fixed timing."
        })
    }

    func testPlanDuplicateValidationUsesActiveDurationGeneratedSegmentIDs() {
        let timed = WorkoutStepDefinition(
            id: "timed",
            title: "Timed",
            instruction: "Hang.",
            accessory: "Test fixture",
            duration: 30,
            phase: .hang,
            targets: [.kind(.edge)],
            activeDuration: 10
        )
        let flat = makeStep(
            id: "timed.segment-2",
            duration: 30,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .undefined, duration: nil)
            ]
        )

        let issues = makeLibrary(steps: [timed, flat]).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "plans[0].blocks[0]" &&
                $0.message == "Expanded step ID \"timed.segment-2\" is repeated in the plan."
        })
    }

    func testPlanDuplicateValidationKeepsActiveDurationCollisionDiagnosticAtPlanBlockPath() {
        let timed = WorkoutStepDefinition(
            id: "active-collision",
            title: "Timed",
            instruction: "Hang.",
            accessory: "Test fixture",
            duration: 30,
            phase: .hang,
            targets: [.kind(.edge)],
            activeDuration: 10
        )
        let flat = makeStep(
            id: "active-collision.segment-1",
            duration: 30,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .undefined, duration: nil)
            ]
        )

        let issues = makeLibrary(steps: [timed, flat]).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "plans[0].blocks[0]" &&
                $0.message == "Expanded step ID \"active-collision.segment-1\" is repeated in the plan."
        })
    }

    func testBundledSourceSeedsClassifyTimedUntimedAndStopwatchActivities() throws {
        let entrySteps = LegacyPlanSeedCatalog.metoliusEntry.steps
        let entryMinuteSixTaskOne = try XCTUnwrap(
            entrySteps.first { $0.id == "entry.minute-6.task-1" }
        )
        let entryMinuteSixTaskTwo = try XCTUnwrap(
            entrySteps.first { $0.id == "entry.minute-6.task-2" }
        )
        let entryMinuteTenTaskOne = try XCTUnwrap(
            entrySteps.first { $0.id == "entry.minute-10.task-1" }
        )

        XCTAssertEqual(
            entryMinuteSixTaskOne.segments,
            [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.roundSloper),
                    timing: .fixed,
                    duration: 10
                )
            ]
        )
        XCTAssertEqual(
            entryMinuteSixTaskTwo.segments,
            [
                WorkoutSegment(
                    kind: .work,
                    target: .kind(.pocket),
                    timing: .fixed,
                    duration: 5
                )
            ]
        )
        XCTAssertEqual(
            entryMinuteTenTaskOne.segments,
            [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.roundSloper),
                    timing: .stopwatch,
                    duration: nil
                )
            ]
        )
    }

    func testUnsupportedSharedWarmUpsAndCooldownsAreAbsent() {
        let unsupportedPhases: Set<WorkoutPhase> = [.warmUp, .coolDown]

        XCTAssertTrue(
            LegacyPlanSeedCatalog.all
                .flatMap(\.steps)
                .allSatisfy { !unsupportedPhases.contains($0.phase) }
        )
    }

    func testSourceBackedAndExplicitlyAdaptedRecoveriesKeepTheirDurations() {
        let recoveryIDs = [
            "horst-753-grip-1-recovery",
            "ladders-round-1-recovery",
            "density-hold-1-set-1-recovery",
            "density-hold-1-recovery"
        ]
        let recoverySteps = LegacyPlanSeedCatalog.all.flatMap(\.steps).filter {
            recoveryIDs.contains($0.id)
        }

        XCTAssertEqual(recoverySteps.map(\.id), recoveryIDs)
        XCTAssertEqual(recoverySteps.map(\.duration), Array(repeating: 180, count: recoveryIDs.count))
    }

    func testBuiltInPlansDoNotEndWithCooldownSteps() throws {
        let data = try bundledPlanLibraryData()
        let definition = try JSONDecoder().decode(PlanLibraryDefinition.self, from: data)
        let store = try PlanLibraryStore(data: data)

        XCTAssertFalse(
            definition.blocks.contains { $0.id == "shared.cool-down" }
        )
        XCTAssertFalse(
            definition.blocks.contains { $0.id == "shared.progressive-warm-up" }
        )
        XCTAssertTrue(
            store.plans.flatMap(\.steps).allSatisfy { $0.phase != .warmUp }
        )
        XCTAssertTrue(
            store.plans.allSatisfy { $0.steps.last?.phase != .coolDown }
        )
    }

    func testPlanLibraryRejectsPlanWhoseImplicitNormalizedStepsEndInRest() {
        let timedWork = WorkoutStepDefinition(
            id: "timed-work",
            title: "Timed work",
            instruction: "Perform the activity.",
            accessory: "8s work · 4s rest",
            duration: 12,
            phase: .hang,
            targets: [.kind(.edge)],
            activeDuration: 8
        )

        let issues = makeLibrary(steps: [timedWork]).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "plans[0].blocks[0].steps[0]" &&
                $0.message == "A plan cannot end in a rest step."
        })
    }

    func testPlanLibraryRejectsPlanWhoseCompoundStepEndsInRest() {
        let compound = makeStep(
            id: "compound-trailing-rest",
            duration: 12,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegmentDefinition(kind: .work, targets: [.kind(.edge)], timing: .fixed, duration: 8),
                WorkoutSegmentDefinition(kind: .rest, targets: [], timing: .fixed, duration: 4)
            ]
        )

        let issues = makeLibrary(steps: [compound]).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "plans[0].blocks[0].steps[0]" &&
                $0.message == "A plan cannot end in a rest step."
        })
    }

    func testPlanLibraryRejectsUntargetedTimedHangOutsideOfficialRPTCImporter() {
        let selfSelectedHang = WorkoutStepDefinition(
            id: "self-selected-hang",
            title: "Self-selected hang",
            instruction: "Hang on a self-selected grip.",
            accessory: "7s hang",
            duration: 7,
            phase: .hang,
            targets: [],
            activeDuration: 7
        )

        let issues = makeLibrary(
            steps: [selfSelectedHang],
            provenance: .official
        ).validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "blocks[0].steps[0].targets" &&
                $0.message == "Non-rest steps need at least one target."
        })
    }

    func testPlanLibraryRejectsUntargetedActiveStepInUnreferencedBlock() {
        let untargetedHang = WorkoutStepDefinition(
            id: "unreferenced-self-selected-hang",
            title: "Self-selected hang",
            instruction: "Hang on a self-selected grip.",
            accessory: "7s hang",
            duration: 7,
            phase: .hang,
            targets: [],
            activeDuration: 7
        )
        var library = makeLibrary(
            steps: [
                makeStep(
                    id: "referenced-step",
                    duration: 7,
                    targets: [.kind(.edge)],
                    segments: []
                )
            ]
        )
        library = PlanLibraryDefinition(
            metadata: library.metadata,
            boardMappings: library.boardMappings,
            blocks: library.blocks + [
                WorkoutBlockDefinition(id: "unreferenced.block", steps: [untargetedHang])
            ],
            plans: library.plans
        )

        let issues = library.validationIssues(availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains {
            $0.path == "blocks[1].steps[0].targets" &&
                $0.message == "Non-rest steps need at least one target."
        })
    }

    func testOfficialRPTCImporterRejectsUntargetedRepeaterWithUnknownIDOrTiming() {
        let cases = [
            (id: "rptc-repeaters-set-rep-extra", duration: 10.0, activeDuration: 7.0),
            (id: "rptc-repeaters-set-rep-1", duration: 11.0, activeDuration: 7.0),
            (id: "rptc-repeaters-set-rep-1", duration: 10.0, activeDuration: 6.0)
        ]

        for testCase in cases {
            let step = WorkoutStepDefinition(
                id: testCase.id,
                title: "RPTC repeater",
                instruction: "Hang on the grip you selected.",
                accessory: "7s hang",
                duration: testCase.duration,
                phase: .hang,
                targets: [],
                activeDuration: testCase.activeDuration
            )
            let issues = makeLibrary(
                steps: [step],
                provenance: .official,
                planID: "rptc.seven-three-repeaters",
                sourceURL: URL(string: "https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155")
            ).validationIssues(availableBoards: BoardCatalog.all)

            XCTAssertTrue(issues.contains {
                $0.path == "blocks[0].steps[0].targets" &&
                    $0.message == "Non-rest steps need at least one target."
            }, "Expected \(testCase.id) with timing \(testCase.activeDuration)s/\(testCase.duration)s to be rejected.")
        }
    }

    func testRPTCRepeatersPreserveTheSourceSetTimingWithoutInventedGripTargets() {
        let plan = LegacyPlanSeedCatalog.rptcRepeaters

        XCTAssertEqual(plan.provenance, .official)
        XCTAssertNil(plan.boardID)
        XCTAssertEqual(plan.duration, 420)
        XCTAssertEqual(plan.steps.count, 8)
        XCTAssertTrue(plan.steps.dropLast().allSatisfy { $0.targets.isEmpty })
        XCTAssertEqual(plan.steps.prefix(6).map(\.duration), Array(repeating: 10, count: 6))
        XCTAssertEqual(plan.steps.prefix(7).map(\.timedWorkDuration), Array(repeating: 7, count: 7))
        XCTAssertEqual(plan.steps[6].duration, 180)
        XCTAssertTrue(plan.steps[6].instruction.contains("2:53"))
        XCTAssertTrue(plan.steps[6].instruction.contains("not the between-set rest"))
        XCTAssertEqual(plan.steps[7].phase, .rest)
        XCTAssertEqual(plan.steps[7].duration, 180)
        XCTAssertTrue(plan.steps[7].instruction.contains("3-minute rest period between sets"))
    }

    func testRoutineCatalogIncludesRPTCAsAnOfficialPlan() throws {
        let plan = try XCTUnwrap(
            LegacyPlanSeedCatalog.all.first { $0.id == "rptc.seven-three-repeaters" }
        )

        XCTAssertEqual(plan.provenance, .official)
    }

    func testShippedRoutineSeedsExceptRPTCExpandToTerminalWorkSteps() throws {
        let terminalSteps = try LegacyPlanSeedCatalog.all
            .filter { $0.id != LegacyPlanSeedCatalog.rptcRepeaters.id }
            .map { plan in
                try XCTUnwrap(plan.steps.flatMap(WorkoutStepNormalizer.expand).last)
            }

        XCTAssertTrue(terminalSteps.allSatisfy { $0.phase != .rest })
    }

    func testAbrahangsSecondGripKeepsSourceBackedFrontThreeOpenCue() throws {
        let step = try XCTUnwrap(
            LegacyPlanSeedCatalog.abrahangs.steps.first { $0.id == "abrahangs-grip-2" }
        )

        XCTAssertEqual(step.title, "Abrahang · F3 Open Hang")
        XCTAssertEqual(
            step.targets,
            [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail)]
        )
        XCTAssertEqual(step.gripType, .openHand)
        XCTAssertEqual(
            step.fingerConfiguration,
            FingerConfiguration(engagedFingers: [.index, .middle, .ring])
        )
    }

    func testAbrahangsFourthGripKeepsSourceBackedFrontTwoOpenCue() throws {
        let store = try PlanLibraryStore(definition: BuiltInPlanLibraryDefinition.document)
        let step = try XCTUnwrap(
            store.plan(id: LegacyPlanSeedCatalog.abrahangs.id)?.steps.first {
                $0.id == "abrahangs-grip-4.segment-1"
            }
        )

        XCTAssertEqual(step.title, "Abrahang · F2 Open Hang")
        XCTAssertEqual(step.gripType, .openHand)
        XCTAssertEqual(
            step.fingerConfiguration,
            FingerConfiguration(engagedFingers: [.index, .middle])
        )
        XCTAssertEqual(step.fingerConfiguration?.orderedFingers, [.index, .middle])
    }

    func testMaxHangsWorkStepsKeepSourceBackedFourFingerCue() {
        let workSteps = PlanCatalog.maxHangs.steps.filter {
            $0.id.hasPrefix("max-hangs-")
                && $0.segments.contains { $0.kind == .work }
        }

        XCTAssertEqual(workSteps.count, 5)
        XCTAssertTrue(workSteps.allSatisfy {
            $0.fingerConfiguration?.orderedFingers == [.index, .middle, .ring, .pinky]
        })
    }

    func testUnsupportedBuiltInGripAndFingerOverridesAreAbsent() throws {
        let plansWithoutSourceBackedCues = [
            LegacyPlanSeedCatalog.metoliusEntry,
            LegacyPlanSeedCatalog.metoliusIntermediate,
            LegacyPlanSeedCatalog.metoliusAdvanced,
            LegacyPlanSeedCatalog.forceF80,
            LegacyPlanSeedCatalog.forceF100,
            LegacyPlanSeedCatalog.evaIntHangs,
            LegacyPlanSeedCatalog.ladders,
            LegacyPlanSeedCatalog.densityHangs,
            LegacyPlanSeedCatalog.zlagboardEndurance
        ]

        XCTAssertTrue(
            plansWithoutSourceBackedCues
                .flatMap(\.steps)
                .allSatisfy { $0.gripType == nil && $0.fingerConfiguration == nil }
        )

        let zlagboardStep = try XCTUnwrap(LegacyPlanSeedCatalog.zlagboardEndurance.steps.first)
        XCTAssertEqual(zlagboardStep.instruction, "Hang for 60 seconds, then rest for 60 seconds.")
        XCTAssertEqual(zlagboardStep.accessory, "60s hang · 60s rest")
    }

    func testMetoliusAdvancedMinuteEightKeepsAlternativeDurationUndefined() throws {
        let minuteEightTaskOne = try XCTUnwrap(
            LegacyPlanSeedCatalog.metoliusAdvanced.steps.first {
                $0.id == "advanced.minute-8.task-1"
            }
        )
        let minuteEightTaskTwo = try XCTUnwrap(
            LegacyPlanSeedCatalog.metoliusAdvanced.steps.first {
                $0.id == "advanced.minute-8.task-2"
            }
        )

        XCTAssertEqual(
            minuteEightTaskOne.segments,
            [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.largeSlope),
                    timing: .fixed,
                    duration: 15
                )
            ]
        )
        XCTAssertEqual(
            minuteEightTaskTwo.segments,
            [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.largeSlope),
                    timing: .undefined,
                    duration: nil
                )
            ]
        )
    }

    @MainActor
    func testBoardSpecificMetoliusPlansAreOfficialAndVisibleOnlyOnTheirSourceBoard() throws {
        let expectedPlans = [
            ("metolius.contact.entry", "metolius.contact", "https://www.metoliusclimbing.com/pages/contact-training-guide"),
            ("metolius.contact.intermediate", "metolius.contact", "https://www.metoliusclimbing.com/pages/contact-training-guide"),
            ("metolius.contact.advanced", "metolius.contact", "https://www.metoliusclimbing.com/pages/contact-training-guide"),
            ("metolius.simulator-3d.entry", "metolius.simulator-3d", "https://www.metoliusclimbing.com/pages/simulator-3d-training-guide"),
            ("metolius.simulator-3d.intermediate", "metolius.simulator-3d", "https://www.metoliusclimbing.com/pages/simulator-3d-training-guide"),
            ("metolius.simulator-3d.advanced", "metolius.simulator-3d", "https://www.metoliusclimbing.com/pages/simulator-3d-training-guide")
        ]
        let expectedIDs = Set(expectedPlans.map(\.0))
        let plans = PlanCatalog.all.filter { expectedIDs.contains($0.id) }
        let boardSpecificFamilyPlans = PlanCatalog.all.filter {
            $0.id.hasPrefix("metolius.contact.") || $0.id.hasPrefix("metolius.simulator-3d.")
        }

        // Detects a missing, cross-board, non-resolvable, or wrong-duration source cycle.
        XCTAssertEqual(Set(plans.map(\.id)), expectedIDs)
        XCTAssertEqual(plans.count, expectedPlans.count)
        XCTAssertEqual(Set(boardSpecificFamilyPlans.map(\.id)), expectedIDs)
        XCTAssertEqual(boardSpecificFamilyPlans.count, 6)

        for (planID, boardID, sourceURL) in expectedPlans {
            let plan = try XCTUnwrap(plans.first { $0.id == planID })
            let board = try XCTUnwrap(BoardCatalog.all.first { $0.id == boardID })

            XCTAssertEqual(plan.boardID, boardID)
            XCTAssertEqual(plan.provenance, .official)
            XCTAssertEqual(plan.sourceURL?.absoluteString, sourceURL)
            if planID == "metolius.simulator-3d.entry" {
                XCTAssertTrue(plan.subtitle.contains("Feet on a chair may lower resistance"))
                XCTAssertTrue(plan.subtitle.contains("1'–3' behind the board plane"))
            }
            XCTAssertEqual(plan.steps.count, 10)
            XCTAssertEqual(plan.duration, 600)
            XCTAssertTrue(plan.steps.allSatisfy { $0.duration == 60 })
            XCTAssertTrue(plan.steps.allSatisfy { $0.timedWorkDuration == nil })
            let numberedTargets = plan.steps.flatMap(\.targets)
            XCTAssertFalse(numberedTargets.isEmpty)
            XCTAssertTrue(numberedTargets.allSatisfy {
                !$0.holdIDs.isEmpty && Set($0.holdIDs).isSubset(of: Set(board.holds.map(\.id)))
            })
            for otherBoard in BoardCatalog.all where otherBoard.id != boardID {
                XCTAssertFalse(
                    plan.boardID == nil || plan.boardID == otherBoard.id,
                    "\(planID) must not be available on \(otherBoard.id)."
                )
            }
        }

        let suiteName = "PlanStorageTests.boardSpecificMetoliusPlans.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        for board in BoardCatalog.all {
            store.selectBoard(board)
            let visiblePlanIDs = Set(store.plans.map(\.id)).intersection(expectedIDs)
            let expectedVisibleIDs = Set(expectedPlans.compactMap { plan in
                plan.1 == board.id ? plan.0 : nil
            })
            XCTAssertEqual(
                visiblePlanIDs,
                expectedVisibleIDs,
                "AppStore must expose only the matching board-specific Metolius plans on \(board.id)."
            )
        }
    }

    func testBoardSpecificMetoliusCompoundCyclesKeepEverySourceTarget() throws {
        // This catches a regression where a compound any-hold, bump, or campus
        // source task loses its later numbered destination from the active holds.
        let expectedNumberedTargets: [(String, Set<String>)] = [
            ("metolius.contact.entry.minute-4", ["pocket-11-left", "pocket-11-right"]),
            ("metolius.contact.entry.minute-10", ["edge-17-center"]),
            ("metolius.contact.intermediate.minute-4", ["pocket-11-left", "pocket-11-right"]),
            ("metolius.contact.intermediate.minute-10", ["flat-sloper-center", "round-sloper-3-left", "round-sloper-3-right"]),
            ("metolius.contact.advanced.minute-4", ["pocket-11-left", "pocket-11-right"]),
            ("metolius.contact.advanced.minute-5", ["pocket-13-left", "pocket-13-right", "pocket-9-left", "pocket-9-right", "jug-left", "jug-right"]),
            ("metolius.contact.advanced.minute-9", ["pocket-7-left", "pocket-7-right", "round-sloper-3-left", "round-sloper-3-right"]),
            ("metolius.contact.advanced.minute-10", ["round-sloper-3-left", "round-sloper-3-right"]),
            ("metolius.simulator-3d.intermediate.minute-10", ["edge-7-left", "edge-7-right", "round-sloper-3-left", "round-sloper-3-right"]),
            ("metolius.simulator-3d.advanced.minute-5", ["edge-11-left", "edge-11-right", "pocket-9-left", "pocket-9-right", "edge-6-left", "edge-6-right", "round-sloper-3-left", "round-sloper-3-right"]),
            ("metolius.simulator-3d.advanced.minute-8", ["pocket-8-left", "pocket-8-right", "pocket-9-left", "pocket-9-right"])
        ]
        let anyHoldCycles = [
            "metolius.contact.entry.minute-4",
            "metolius.contact.entry.minute-10",
            "metolius.contact.intermediate.minute-4",
            "metolius.contact.intermediate.minute-7",
            "metolius.contact.advanced.minute-4",
            "metolius.simulator-3d.entry.minute-10",
            "metolius.simulator-3d.intermediate.minute-7"
        ]

        for (stepID, expectedTargets) in expectedNumberedTargets {
            let step = try XCTUnwrap(PlanCatalog.all.lazy.flatMap(\.steps).first { $0.id == stepID })
            XCTAssertTrue(
                expectedTargets.isSubset(of: Set(step.targets.flatMap(\.holdIDs))),
                "\(stepID) must retain every numbered target in its compound source task."
            )
        }

        for stepID in anyHoldCycles {
            let step = try XCTUnwrap(PlanCatalog.all.lazy.flatMap(\.steps).first { $0.id == stepID })
            let plan = try XCTUnwrap(PlanCatalog.all.first { stepID.hasPrefix($0.id) })
            let board = try XCTUnwrap(BoardCatalog.all.first { $0.id == plan.boardID })

            XCTAssertEqual(
                Set(step.targets.flatMap(\.holdIDs)),
                Set(board.holds.map(\.id)),
                "\(stepID) must keep the source's any-hold option unconstrained."
            )
        }
    }

    func testBundledSourceSeedsClassifyExplicitWorkRestAndRecovery() throws {
        let maxHang = try XCTUnwrap(
            LegacyPlanSeedCatalog.maxHangs.steps.first { $0.id == "max-hangs-1" }
        )
        let recovery = try XCTUnwrap(
            LegacyPlanSeedCatalog.forceF80.steps.first { $0.id == "f80-set-1-recovery" }
        )

        XCTAssertEqual(
            maxHang.segments,
            [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.mediumEdge, fallback: .largeEdge),
                    timing: .fixed,
                    duration: 7
                ),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 180)
            ]
        )
        XCTAssertEqual(
            recovery.segments,
            [WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 480)]
        )
    }

    func testPlanCatalogMatchesLiteralizedLegacyPlanSeeds() throws {
        let expectedPlans = try LegacyPlanSeedCatalog.all.map { seedPlan in
            let literalSteps = try seedPlan.steps
                .flatMap(WorkoutStepNormalizer.expand)
                .enumerated()
                .map { index, step in
                    step.withNumber(index + 1)
                }

            return TrainingPlan(
                id: seedPlan.id,
                title: seedPlan.title,
                subtitle: seedPlan.subtitle,
                level: seedPlan.level,
                sourceLabel: seedPlan.sourceLabel,
                sourceURL: seedPlan.sourceURL,
                provenance: seedPlan.provenance,
                boardID: seedPlan.boardID,
                steps: literalSteps
            )
        }

        XCTAssertEqual(PlanLibraryStore.builtIn.plans, expectedPlans)
        XCTAssertEqual(PlanCatalog.all, expectedPlans)
    }

    func testBuiltInPlanLibraryVisibleCueFieldsHaveSourceAuditCoverage() throws {
        let audit = try loadPlanCueAudit()
        let library = BuiltInPlanLibraryDefinition.document
        let store = try PlanLibraryStore(definition: library)

        let sourcesByPlanID = Dictionary(grouping: audit.planSources, by: \.planID)
        let builtInPlanIDs = Set(library.plans.map(\.id))

        XCTAssertEqual(
            Set(audit.planSources.map(\.planID)),
            builtInPlanIDs,
            "The source manifest must cover exactly the built-in plans."
        )
        for plan in library.plans {
            let source = try XCTUnwrap(
                sourcesByPlanID[plan.id]?.only,
                "Expected exactly one source-manifest entry for \(plan.id)."
            )
            let sourceURL = try XCTUnwrap(
                plan.metadata.sourceURL,
                "Expected a source URL for \(plan.id)."
            )
            XCTAssertEqual(source.sourceType, plan.metadata.category)
            XCTAssertEqual(source.sourceLabel, plan.metadata.sourceLabel)
            XCTAssertEqual(source.sourceURL, sourceURL.absoluteString)
        }

        let expectedPlanFieldKeys = Set(
            library.plans.flatMap { plan in
                auditedPlanFields.map { field in
                    CueAuditKey(planID: plan.id, stepID: nil, field: field)
                }
            }
        )
        let expectedRetainedPlanFieldKeys = expectedPlanCueAuditKeys(in: store)
        let planRulesByKey = Dictionary(grouping: audit.planFieldRules.flatMap { rule in
            rule.fields.map { field in
                (CueAuditKey(planID: rule.planID, stepID: nil, field: field), rule)
            }
        }, by: { $0.0 })
        let missingPlanFields = expectedRetainedPlanFieldKeys.filter { key in
            !audit.planFieldRules.contains { rule in
                rule.matches(key) && rule.isRetained
            }
        }
        let retainedPlanFieldsWithRemoveRules = expectedRetainedPlanFieldKeys.filter { key in
            audit.planFieldRules.contains { rule in
                rule.matches(key) && rule.decision == "remove"
            }
        }
        let uncategorizedPlanFields = expectedPlanFieldKeys.filter { planRulesByKey[$0] == nil }
        let multiplyCoveredPlanFields = expectedPlanFieldKeys.filter {
            planRulesByKey[$0, default: []].count != 1
        }

        XCTAssertTrue(
            missingPlanFields.isEmpty,
            "Missing retained plan-level cue audit coverage:\n\(missingPlanFields.sorted().map(\.description).joined(separator: "\n"))"
        )
        XCTAssertTrue(
            retainedPlanFieldsWithRemoveRules.isEmpty,
            "Retained plan-level fields must not have remove rules:\n\(retainedPlanFieldsWithRemoveRules.sorted().map(\.description).joined(separator: "\n"))"
        )
        XCTAssertTrue(
            uncategorizedPlanFields.isEmpty,
            "Missing plan-level cue audit decisions:\n\(uncategorizedPlanFields.sorted().map(\.description).joined(separator: "\n"))"
        )
        XCTAssertTrue(
            multiplyCoveredPlanFields.isEmpty,
            "Plan-level fields must have exactly one audit decision:\n\(multiplyCoveredPlanFields.sorted().map(\.description).joined(separator: "\n"))"
        )

        let retainedPlanFieldKeys: Set<CueAuditKey> = Set(planRulesByKey.compactMap { key, entries in
            guard let entry = entries.only else { return nil }
            return entry.1.isRetained ? key : nil
        })
        let removedPlanFieldKeys: Set<CueAuditKey> = Set(planRulesByKey.compactMap { key, entries in
            guard let entry = entries.only else { return nil }
            return entry.1.decision == "remove" ? key : nil
        })
        XCTAssertTrue(
            retainedPlanFieldKeys.isDisjoint(with: removedPlanFieldKeys),
            "Removed plan fields must not be represented as retained."
        )
        XCTAssertEqual(
            retainedPlanFieldKeys.union(removedPlanFieldKeys),
            expectedPlanFieldKeys,
            "Every plan field must be classified as retained (keep/adapt) or removed."
        )

        let expectedStepFieldKeys = try expectedStepCueAuditKeys(in: library)
        let missingStepFields = expectedStepFieldKeys.filter { key in
            !audit.stepFieldRules.contains { rule in
                rule.matches(key) && rule.isRetained
            }
        }
        let retainedStepFieldsWithRemoveRules = expectedStepFieldKeys.filter { key in
            audit.stepFieldRules.contains { rule in
                rule.matches(key) && rule.decision == "remove"
            }
        }

        XCTAssertTrue(
            missingStepFields.isEmpty,
            "Missing step-level cue audit coverage:\n\(missingStepFields.sorted().map(\.description).joined(separator: "\n"))"
        )
        XCTAssertTrue(
            retainedStepFieldsWithRemoveRules.isEmpty,
            "Retained step fields must not have remove rules:\n\(retainedStepFieldsWithRemoveRules.sorted().map(\.description).joined(separator: "\n"))"
        )

        let auditedAdaptations = audit.planFieldRules.map(AnyCueAuditDecision.init) +
            audit.stepFieldRules.map(AnyCueAuditDecision.init)
        let timerOrRangeAdaptationDecisions = auditedAdaptations.filter {
            $0.adaptationType == "timer" || $0.adaptationType == "range"
        }

        XCTAssertFalse(
            timerOrRangeAdaptationDecisions.isEmpty,
            "Expected the cue audit to label app timer/range adaptations explicitly."
        )
        XCTAssertTrue(
            timerOrRangeAdaptationDecisions.allSatisfy { decision in
                decision.decision == "adapt" && decision.sourcePrescription == false
            },
            "Timer/range adaptations must be marked as adapt and not source-prescribed."
        )

        let retainedTimerOrRangeStepRules = expectedStepFieldKeys.flatMap { key in
            audit.stepFieldRules.filter { rule in
                rule.matches(key) && (rule.adaptationType == "timer" || rule.adaptationType == "range")
            }
        }
        XCTAssertTrue(
            retainedTimerOrRangeStepRules.allSatisfy {
                $0.decision == "adapt" && $0.sourcePrescription == false
            },
            "Retained step timer/range adaptations must be adapt rules and not source-prescribed."
        )

        let actualTimerOrRangePlanKeys = expectedRetainedPlanFieldKeys.filter { key in
            audit.planFieldRules.contains { rule in
                rule.matches(key) && rule.isTimerOrRangeAdaptation
            }
        }
        XCTAssertEqual(
            actualTimerOrRangePlanKeys,
            expectedTimerOrRangePlanCueAuditKeys(in: store),
            "Timer/range plan adaptations must match the built-in library's actual retained adaptations."
        )

        let actualTimerOrRangeStepKeys = expectedStepFieldKeys.filter { key in
            audit.stepFieldRules.contains { rule in
                rule.matches(key) && rule.isTimerOrRangeAdaptation
            }
        }
        XCTAssertEqual(
            actualTimerOrRangeStepKeys,
            try expectedTimerOrRangeStepCueAuditKeys(in: library),
            "Timer/range step adaptations must match the built-in library's actual retained adaptations."
        )

        for planID in [
            LegacyPlanSeedCatalog.metoliusEntry.id,
            LegacyPlanSeedCatalog.metoliusIntermediate.id,
            LegacyPlanSeedCatalog.metoliusAdvanced.id
        ] {
            XCTAssertTrue(
                audit.planFieldRules.contains {
                    $0.planID == planID &&
                        $0.fields.contains("interval") &&
                        $0.decision == "adapt" &&
                        $0.adaptationType == "timer" &&
                        $0.sourcePrescription == false
                },
                "Expected \(planID) to record its app-guided interval expansion as a timer adaptation."
            )
        }
    }

    func testLatticeBeginnerGuideIsNotAvailableFromBuiltInCatalog() {
        let removedPlanID = "lattice.beginner-climbers-training-guide"

        XCTAssertFalse(LegacyPlanSeedCatalog.all.contains { $0.id == removedPlanID })
        XCTAssertNil(PlanCatalog.plan(id: removedPlanID))
    }

    func testLatticeLiteHomeAdaptationsIsNotAvailableFromBuiltInCatalog() {
        let removedPlanID = "lattice.lite-home-adaptations"

        XCTAssertFalse(LegacyPlanSeedCatalog.all.contains { $0.id == removedPlanID })
        XCTAssertNil(PlanCatalog.plan(id: removedPlanID))
    }

    func testRequestedSourcePlansAreSeededAndResolved() throws {
        let expectedIDs = [
            "hoopers-beta.introductory-home-hangboard",
            "method.intermediate-hangboarding.repeaters",
            "method.intermediate-hangboarding.emom",
            "rei.hangboard-sample-workout"
        ]

        XCTAssertTrue(expectedIDs.allSatisfy { id in
            LegacyPlanSeedCatalog.all.contains { $0.id == id } && PlanCatalog.plan(id: id) != nil
        })
        XCTAssertEqual(
            expectedIDs.map { PlanCatalog.metadata(for: $0)?.category },
            ["coach", "coach", "coach", "retailer"]
        )
    }

    func testCompactIIStillSubstitutesGenericNonPinchPlans() throws {
        let compact = BoardCatalog.defaultBoard
        let genericPlans = LegacyPlanSeedCatalog.all.filter {
            $0.boardID == nil && $0.id != LegacyPlanSeedCatalog.reiHangboardSample.id
        }

        XCTAssertTrue(
            genericPlans.allSatisfy { plan in
                plan.steps.flatMap(\.targets).allSatisfy {
                    !BoardTargetResolver.substituteHoldIDs(for: $0, on: compact).isEmpty
                }
            }
        )
        XCTAssertTrue(
            LegacyPlanSeedCatalog.reiHangboardSample.steps.flatMap(\.targets).contains {
                $0.feature == .mediumPinch
            }
        )
        let reiMediumPinch = try XCTUnwrap(
            LegacyPlanSeedCatalog.reiHangboardSample.steps
                .flatMap(\.targets)
                .first { $0.feature == .mediumPinch }
        )
        XCTAssertFalse(BoardTargetResolver.substituteHoldIDs(for: reiMediumPinch, on: compact).isEmpty)
    }

    @MainActor
    func testCapacityQualifiedPocketPlansRetainTheirAvailabilityFallbacks() throws {
        let expectedFallbacks: [HoldFeature] = [.mediumEdge, .largeEdge, .largeOpenHandRail]
        let pocketTargets = [
            (planID: "coach.horst-seven-fifty-three", fingerCapacity: 2, capacitySourceBacked: true),
            (planID: "coach.density-hangs", fingerCapacity: 4, capacitySourceBacked: false)
        ]
        let audit = try loadPlanCueAudit()

        for expected in pocketTargets {
            let plan = try XCTUnwrap(LegacyPlanSeedCatalog.all.first { $0.id == expected.planID })
            let target = try XCTUnwrap(
                plan.steps
                    .flatMap(\.targets)
                    .first { $0.kind == .pocket && $0.fingerCapacity == expected.fingerCapacity }
            )

            XCTAssertEqual(target.fallbackFeatures, expectedFallbacks)

            let fallbackAudit = try XCTUnwrap(
                audit.targetFallbackRules.filter { rule in
                    rule.planID == expected.planID &&
                        rule.primaryKind == .pocket &&
                        rule.fingerCapacity == expected.fingerCapacity
                }.only,
                "Expected one explicit fallback audit mapping for \(expected.planID)."
            )
            XCTAssertEqual(fallbackAudit.fallbackFeatures, expectedFallbacks)
            XCTAssertEqual(fallbackAudit.decision, "adapt")
            XCTAssertFalse(fallbackAudit.sourcePrescription)
            XCTAssertEqual(
                fallbackAudit.fingerCapacitySourcePrescription,
                expected.capacitySourceBacked,
                "The capacity provenance must be distinct from the fallback availability adaptation."
            )
            XCTAssertEqual(fallbackAudit.adaptationType, "availability")
            XCTAssertTrue(fallbackAudit.sourceBasis.contains("app availability adaptation"))
            XCTAssertEqual(
                fallbackAudit.sourceURL,
                try XCTUnwrap(audit.planSources.first { $0.planID == expected.planID }).sourceURL
            )

            let edgeOnlyBoard = TrainingBoard(
                id: "fixture.edge-only.\(expected.fingerCapacity)",
                manufacturer: "Fixture Maker",
                name: "Edge-only Board",
                subtitle: "A test board without pockets.",
                dimensions: "10 × 5",
                aspectRatio: 2,
                holds: [
                    BoardHold(
                        id: "fixture.large-edge",
                        name: "Large edge",
                        shortLabel: "E",
                        detail: "A fixture large edge.",
                        kind: .edge,
                        frame: .init(x: 0.1, y: 0.1, width: 0.2, height: 0.1),
                        features: [.largeEdge]
                    )
                ],
                productURL: URL(string: "https://example.com/edge-only")!,
                photoAssetName: nil
            )
            XCTAssertEqual(
                BoardTargetResolver.substituteHoldIDs(for: target, on: edgeOnlyBoard),
                ["fixture.large-edge"]
            )
        }
    }

    @MainActor
    func testAuditedPlansAreBoardFlexibleAndSubstituteOnEveryRegisteredBoard() throws {
        let auditedPlanIDs: Set<String> = [
            "research.force-feedback-f80",
            "research.force-feedback-f100",
            "research.eva-int-hangs",
            "research.seven-three-repeaters",
            "research.abrahangs",
            "coach.horst-seven-fifty-three",
            "coach.bechtel-three-six-nine",
            "coach.density-hangs",
            "device.zlagboard-sixty-sixty"
        ]
        let auditedPlans = LegacyPlanSeedCatalog.all.filter { auditedPlanIDs.contains($0.id) }

        XCTAssertEqual(auditedPlans.map(\.id).count, auditedPlanIDs.count)
        XCTAssertTrue(auditedPlans.allSatisfy { $0.boardID == nil })
        XCTAssertTrue(auditedPlans.allSatisfy { plan in
            plan.steps.flatMap(\.targets).allSatisfy(\.holdIDs.isEmpty)
        })

        let suiteName = "PlanStorageTests.boardFlexiblePlans.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        let nonCompactBoard = try XCTUnwrap(
            BoardCatalog.all.first { $0.id != BoardCatalog.defaultBoard.id }
        )
        store.selectBoard(nonCompactBoard)

        XCTAssertTrue(auditedPlanIDs.isSubset(of: Set(store.plans.map(\.id))))

        for board in BoardCatalog.all {
            for plan in auditedPlans {
                let workTargets = plan.steps.flatMap { step in
                    step.segments
                        .filter { $0.kind == .work }
                        .flatMap(\.targets)
                }
                XCTAssertFalse(workTargets.isEmpty, "\(plan.id) must include work targets")
                XCTAssertTrue(
                    workTargets.allSatisfy {
                        !BoardTargetResolver.substituteHoldIDs(for: $0, on: board).isEmpty
                    },
                    "\(plan.id) must substitute every work target on \(board.id)"
                )
            }
        }
    }

    func testHoopersRoundTwoKeepsFiveRecruitmentRepsPerHandAcrossThreeSets() throws {
        let steps = LegacyPlanSeedCatalog.hoopersBetaIntroductory.steps
        let recruitment = steps.filter { $0.id.contains("hoopers-intro-round-2-set-") && $0.id.contains("-rep-") }
        XCTAssertEqual(recruitment.count, 30)
        XCTAssertEqual(recruitment.filter { $0.id.hasSuffix("-left") }.count, 15)
        XCTAssertEqual(recruitment.filter { $0.id.hasSuffix("-right") }.count, 15)
        XCTAssertEqual(steps.filter { $0.id.contains("round-2-set-") && $0.id.hasSuffix("-kicks") }.count, 3)
    }

    func testHoopersOptionalRoundFiveIsFourPossiblePairedSetsNotEightIndependentSets() throws {
        let steps = LegacyPlanSeedCatalog.hoopersBetaIntroductory.steps
        let pullUps = steps.filter { $0.id.contains("hoopers-intro-round-5-set-") && $0.id.hasSuffix("-pull-ups") }
        let hollow = steps.filter { $0.id.contains("hoopers-intro-round-5-set-") && $0.id.hasSuffix("-hollow") }
        XCTAssertEqual(pullUps.count, 4)
        XCTAssertEqual(hollow.count, 4)
        XCTAssertTrue(pullUps.allSatisfy { $0.instruction.contains("2–4 total") })
        XCTAssertTrue(hollow.allSatisfy { $0.instruction.contains("2–4 total paired sets") })
    }

    func testFeatureTargetValidationAcceptsRuntimeResolvableUntaggedSameKindHold() {
        let board = TrainingBoard(
            id: "fixture.untagged-edge",
            manufacturer: "Fixture Maker",
            name: "Untagged Edge",
            subtitle: "A test board whose edge has no feature metadata.",
            dimensions: "10 × 5",
            aspectRatio: 2,
            holds: [
                BoardHold(
                    id: "fixture.edge",
                    name: "Fixture edge",
                    kind: .edge,
                    geometry: [
                        BoardHoldPiece(
                            id: "fixture.edge-piece",
                            holdID: "fixture.edge",
                            frame: CGRect(x: 0.1, y: 0.2, width: 0.2, height: 0.4),
                            shape: .roundedRect(cornerRadiusFraction: 0),
                            treatment: .surface
                        )
                    ]
                )
            ],
            productURL: URL(string: "https://example.com/untagged-edge")!,
            photoAssetName: nil
        )
        let target = HoldTarget.feature(.mediumEdge)
        let step = makeStep(
            id: "feature-target",
            duration: 10,
            targets: [.feature(.mediumEdge, fallbacks: [])],
            segments: []
        )

        XCTAssertEqual(
            BoardTargetResolver.substituteHoldIDs(for: target, on: board),
            ["fixture.edge"]
        )
        XCTAssertFalse(
            makeLibrary(steps: [step], boardID: board.id)
                .validationIssues(availableBoards: [board])
                .contains {
                    $0.path == "plans[0].blocks[0].steps[0].targets[0]" &&
                        $0.message == "No compatible board exposes feature \"mediumEdge\" or its fallbacks."
                }
        )
    }

    func testFeatureTargetValidationRejectsTargetRuntimeCannotResolve() {
        let board = TrainingBoard(
            id: "fixture.jug-only",
            manufacturer: "Fixture Maker",
            name: "Jug Only",
            subtitle: "A test board with no edge or pocket holds.",
            dimensions: "10 × 5",
            aspectRatio: 2,
            holds: [
                BoardHold(
                    id: "fixture.jug",
                    name: "Fixture jug",
                    kind: .jug,
                    geometry: [
                        BoardHoldPiece(
                            id: "fixture.jug-piece",
                            holdID: "fixture.jug",
                            frame: CGRect(x: 0.1, y: 0.2, width: 0.2, height: 0.4),
                            shape: .roundedRect(cornerRadiusFraction: 0),
                            treatment: .surface
                        )
                    ]
                )
            ],
            productURL: URL(string: "https://example.com/jug-only")!,
            photoAssetName: nil
        )
        let step = makeStep(
            id: "feature-target",
            duration: 10,
            targets: [.feature(.mediumEdge, fallbacks: [])],
            segments: []
        )

        XCTAssertTrue(
            makeLibrary(steps: [step], boardID: board.id)
                .validationIssues(availableBoards: [board])
                .contains {
                    $0.path == "plans[0].blocks[0].steps[0].targets[0]" &&
                        $0.message == "No compatible board exposes feature \"mediumEdge\" or its fallbacks."
                }
        )
    }

    func testPlanSemanticMappingsRemainAuthoritativeDuringValidation() {
        let edgeOnlyBoard = TrainingBoard(
            id: "fixture.edge-only",
            manufacturer: "Fixture Maker",
            name: "Edge Only",
            subtitle: "A test board with only an edge.",
            dimensions: "10 × 5",
            aspectRatio: 2,
            holds: [
                BoardHold(
                    id: "fixture.edge",
                    name: "Fixture edge",
                    shortLabel: "E",
                    detail: "A fixture edge.",
                    kind: .edge,
                    frame: HoldFrame(x: 0.1, y: 0.2, width: 0.2, height: 0.4)
                )
            ],
            semanticHolds: [
                "fixture-board-owned": SemanticHoldMappingDefinition(kind: .pinch),
                "fixture-overridden": SemanticHoldMappingDefinition(kind: .pinch)
            ],
            productURL: URL(string: "https://example.com/edge-only")!,
            photoAssetName: nil
        )
        let step = makeStep(
            id: "semantic-target",
            duration: 10,
            targets: [.semantic("fixture-overridden")],
            segments: []
        )

        let library = makeLibrary(
            steps: [step],
            boardID: edgeOnlyBoard.id,
            boardMappings: [
                BoardMappingDefinition(
                    boardID: edgeOnlyBoard.id,
                    semanticHolds: [
                        "fixture-plan": SemanticHoldMappingDefinition(kind: .pinch),
                        "fixture-overridden": SemanticHoldMappingDefinition(kind: .edge)
                    ]
                )
            ]
        )
        let issues = library.validationIssues(availableBoards: [edgeOnlyBoard])

        XCTAssertFalse(issues.contains { $0.path.hasPrefix("boards[0].semanticHolds") })
        XCTAssertTrue(issues.contains {
            $0.path == "boardMappings[0].semanticHolds.fixture-plan" &&
                $0.message == "Hold kind \"pinch\" has no matching hold on board \"fixture.edge-only\"."
        })
        XCTAssertFalse(issues.contains { $0.message.contains("fixture-overridden") })
    }

    func testPlanMappingsOverrideBoardLoadedSemanticMappings() throws {
        func hold(id: String, name: String, kind: HoldKind, x: CGFloat) -> BoardHold {
            BoardHold(
                id: id,
                name: name,
                kind: kind,
                geometry: [
                    BoardHoldPiece(
                        id: "\(id)-piece",
                        holdID: id,
                        frame: CGRect(x: x, y: 0.2, width: 0.2, height: 0.4),
                        shape: .roundedRect(cornerRadiusFraction: 0),
                        treatment: .surface
                    )
                ]
            )
        }
        let board = TrainingBoard(
            id: "fixture.board",
            manufacturer: "Fixture Maker",
            name: "Fixture Board",
            subtitle: "A test board.",
            dimensions: "10 × 5",
            aspectRatio: 2,
            holds: [
                hold(id: "fixture.edge", name: "Fixture edge", kind: .edge, x: 0.1),
                hold(id: "fixture.pinch", name: "Fixture pinch", kind: .pinch, x: 0.4),
                hold(id: "fixture.jug", name: "Fixture jug", kind: .jug, x: 0.7)
            ],
            semanticHolds: [
                "fixture-target": SemanticHoldMappingDefinition(holdIDs: ["fixture.edge"]),
                "fixture-fallback": SemanticHoldMappingDefinition(kind: .pinch)
            ],
            productURL: URL(string: "https://example.com/fixture-board")!,
            photoAssetName: nil
        )
        let step = makeStep(
            id: "semantic-target",
            duration: 10,
            targets: [.semantics(["fixture-target", "fixture-fallback"])],
            segments: []
        )
        let boardOnlyLibrary = makeLibrary(steps: [step], boardID: "fixture.board")

        XCTAssertEqual(
            board.semanticHolds["fixture-target"],
            SemanticHoldMappingDefinition(holdIDs: ["fixture.edge"])
        )
        XCTAssertEqual(
            board.semanticHolds["fixture-fallback"],
            SemanticHoldMappingDefinition(kind: .pinch)
        )
        XCTAssertTrue(
            boardOnlyLibrary.validationIssues(availableBoards: [board]).contains {
                $0.message == "Missing board mapping for \"fixture.board\"."
            }
        )

        let planMappingLibrary = makeLibrary(
            steps: [step],
            boardID: "fixture.board",
            boardMappings: [
                BoardMappingDefinition(
                    boardID: "fixture.board",
                    semanticHolds: [
                        "fixture-target": SemanticHoldMappingDefinition(kind: .jug),
                        "fixture-fallback": SemanticHoldMappingDefinition(kind: .edge)
                    ]
                )
            ]
        )

        XCTAssertEqual(planMappingLibrary.validationIssues(availableBoards: [board]), [])

        let planMappingStore = try PlanLibraryStore(
            definition: planMappingLibrary,
            availableBoards: [board]
        )
        let planMappingTargets = try XCTUnwrap(
            planMappingStore.plan(id: "test.plan")?.steps.first?.targets
        )

        XCTAssertEqual(planMappingTargets, [.kind(.jug), .kind(.edge)])
        XCTAssertEqual(
            BoardTargetResolver.resolveHoldIDs(for: planMappingTargets[0], on: board),
            ["fixture.jug"]
        )
        XCTAssertEqual(
            BoardTargetResolver.resolveHoldIDs(for: planMappingTargets[1], on: board),
            ["fixture.edge"]
        )
    }

    private func validationIssues(
        for segment: WorkoutSegmentDefinition,
        stepDuration: TimeInterval = 30
    ) -> [PlanValidationIssue] {
        makeLibrary(
            steps: [
                makeStep(
                    id: "validation",
                    duration: stepDuration,
                    targets: [.kind(.edge)],
                    segments: [segment]
                )
            ]
        ).validationIssues(availableBoards: BoardCatalog.all)
    }

    private func makeStep(
        id: String,
        duration: TimeInterval,
        phase: WorkoutPhase = .hang,
        targets: [WorkoutTargetDefinition],
        segments: [WorkoutSegmentDefinition]
    ) -> WorkoutStepDefinition {
        WorkoutStepDefinition(
            id: id,
            title: id.capitalized,
            instruction: "Perform the activity.",
            accessory: "Test fixture",
            duration: duration,
            phase: phase,
            targets: targets,
            segments: segments
        )
    }

    private func makeLibrary(
        steps: [WorkoutStepDefinition],
        boardID: String? = nil,
        boardMappings: [BoardMappingDefinition] = [],
        provenance: RoutineProvenance = .adapted,
        planID: String = "test.plan",
        sourceURL: URL? = URL(string: "https://example.com/test")
    ) -> PlanLibraryDefinition {
        PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "test.library",
                title: "Test library",
                generatedAt: "2026-08-02"
            ),
            boardMappings: boardMappings,
            blocks: [WorkoutBlockDefinition(id: "test.block", steps: steps)],
            plans: [
                PlanDefinition(
                    id: planID,
                    metadata: PlanMetadata(
                        title: "Test plan",
                        subtitle: "Storage tests",
                        level: "Test",
                        sourceLabel: "Test fixture",
                        sourceURL: sourceURL,
                        provenance: provenance
                    ),
                    boardID: boardID,
                    blocks: [WorkoutBlockReference(blockID: "test.block")]
                )
            ]
        )
    }

    private var auditedPlanFields: [String] {
        [
            "title",
            "subtitle",
            "instruction",
            "accessory",
            "target",
            "count",
            "duration",
            "interval",
            "warmUp",
            "cooldown",
            "gripType",
            "fingerConfiguration"
        ]
    }

    private func expectedPlanCueAuditKeys(in store: PlanLibraryStore) -> Set<CueAuditKey> {
        Set(store.plans.flatMap { plan in
            var keys: [CueAuditKey] = []
            if plan.title.hasVisibleText {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "title"))
            }
            if plan.subtitle.hasVisibleText {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "subtitle"))
            }
            if plan.steps.contains(where: { $0.instruction.hasVisibleText }) {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "instruction"))
            }
            if plan.steps.contains(where: { $0.accessory.hasVisibleText }) {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "accessory"))
            }
            if plan.steps.contains(where: { !$0.targets.isEmpty }) {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "target"))
            }
            if !plan.steps.isEmpty {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "count"))
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "interval"))
            }
            if plan.duration > 0 {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "duration"))
            }
            if plan.steps.contains(where: { $0.phase == .warmUp }) {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "warmUp"))
            }
            if plan.steps.contains(where: { $0.phase == .coolDown }) {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "cooldown"))
            }
            if plan.steps.contains(where: { $0.gripType != nil }) {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "gripType"))
            }
            if plan.steps.contains(where: { $0.fingerConfiguration != nil }) {
                keys.append(CueAuditKey(planID: plan.id, stepID: nil, field: "fingerConfiguration"))
            }
            return keys
        })
    }

    private func expectedTimerOrRangePlanCueAuditKeys(in store: PlanLibraryStore) -> Set<CueAuditKey> {
        Set(store.plans.flatMap { plan in
            timerOrRangePlanFields(for: plan.id).map {
                CueAuditKey(planID: plan.id, stepID: nil, field: $0)
            }
        })
    }

    private func expectedTimerOrRangeStepCueAuditKeys(in library: PlanLibraryDefinition) throws -> Set<CueAuditKey> {
        let blocksByID = Dictionary(uniqueKeysWithValues: library.blocks.map { ($0.id, $0) })

        return try Set(library.plans.flatMap { plan in
            try plan.blocks.flatMap { reference in
                let block = try XCTUnwrap(
                    blocksByID[reference.blockID],
                    "Missing block \(reference.blockID) while building timer/range audit expectations."
                )

                return block.steps.flatMap { step in
                    timerOrRangeStepFields(for: plan.id, step: step).map {
                        CueAuditKey(planID: plan.id, stepID: step.id, field: $0)
                    }
                }
            }
        })
    }

    private func timerOrRangePlanFields(for planID: String) -> [String] {
        switch planID {
        case LegacyPlanSeedCatalog.metoliusEntry.id,
            LegacyPlanSeedCatalog.metoliusIntermediate.id,
            LegacyPlanSeedCatalog.metoliusAdvanced.id:
            return ["subtitle", "accessory", "duration", "interval"]
        case "research.max-hangs":
            return ["subtitle", "accessory", "count", "duration", "interval"]
        case "research.eva-int-hangs":
            return ["subtitle", "instruction", "accessory", "count", "duration", "interval"]
        case "research.abrahangs":
            return ["subtitle", "accessory", "duration", "interval"]
        case "coach.horst-seven-fifty-three":
            return ["subtitle", "count", "interval"]
        case "coach.bechtel-three-six-nine":
            return ["subtitle", "accessory", "count", "interval"]
        case "coach.density-hangs":
            return ["subtitle", "accessory", "count", "duration", "interval"]
        default:
            return []
        }
    }

    private func timerOrRangeStepFields(for planID: String, step: WorkoutStepDefinition) -> [String] {
        switch planID {
        case LegacyPlanSeedCatalog.metoliusEntry.id,
            LegacyPlanSeedCatalog.metoliusIntermediate.id,
            LegacyPlanSeedCatalog.metoliusAdvanced.id:
            guard step.phase == .rest else { return [] }
            return visibleCueFields(
                instruction: step.instruction,
                accessory: step.accessory
            )
        case "research.max-hangs":
            return visibleCueFields(accessory: step.accessory)
        case "research.eva-int-hangs":
            return visibleCueFields(
                instruction: step.instruction,
                accessory: step.accessory
            )
        case "research.abrahangs",
            "coach.horst-seven-fifty-three",
            "coach.bechtel-three-six-nine",
            "coach.density-hangs":
            return visibleCueFields(accessory: step.accessory)
        default:
            return []
        }
    }

    private func visibleCueFields(
        instruction: String? = nil,
        accessory: String? = nil
    ) -> [String] {
        var fields: [String] = []
        if instruction?.hasVisibleText == true {
            fields.append("instruction")
        }
        if accessory?.hasVisibleText == true {
            fields.append("accessory")
        }
        return fields
    }

    private func expectedStepCueAuditKeys(in library: PlanLibraryDefinition) throws -> Set<CueAuditKey> {
        let blocksByID = Dictionary(uniqueKeysWithValues: library.blocks.map { ($0.id, $0) })

        return try Set(library.plans.flatMap { plan in
            try plan.blocks.flatMap { reference in
                let block = try XCTUnwrap(
                    blocksByID[reference.blockID],
                    "Missing block \(reference.blockID) while building source-audit expectations."
                )

                return block.steps.flatMap { step in
                    var keys: [CueAuditKey] = []
                    if step.instruction.hasVisibleText {
                        keys.append(CueAuditKey(planID: plan.id, stepID: step.id, field: "instruction"))
                    }
                    if step.accessory.hasVisibleText {
                        keys.append(CueAuditKey(planID: plan.id, stepID: step.id, field: "accessory"))
                    }
                    if step.gripType != nil {
                        keys.append(CueAuditKey(planID: plan.id, stepID: step.id, field: "gripType"))
                    }
                    if step.fingerConfiguration != nil {
                        keys.append(CueAuditKey(planID: plan.id, stepID: step.id, field: "fingerConfiguration"))
                    }
                    return keys
                }
            }
        })
    }

    private func loadPlanCueAudit() throws -> CueAuditDocument {
        let fileURL = try planCueAuditURL()
        let markdown = try String(contentsOf: fileURL, encoding: .utf8)
        let jsonFence = try XCTUnwrap(
            markdown.range(
                of: #"```json\s*(\{[\s\S]*?\})\s*```"#,
                options: .regularExpression
            ),
            "Expected a fenced JSON audit block in \(fileURL.path)."
        )
        let fencedText = String(markdown[jsonFence])
        let jsonText = fencedText
            .replacingOccurrences(
                of: #"^```json\s*"#,
                with: "",
                options: .regularExpression
            )
            .replacingOccurrences(
                of: #"\s*```$"#,
                with: "",
                options: .regularExpression
            )

        return try JSONDecoder().decode(CueAuditDocument.self, from: Data(jsonText.utf8))
    }

    private func planCueAuditURL() throws -> URL {
        let testsDirectory = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        let repoRoot = testsDirectory.deletingLastPathComponent()
        let auditURL = repoRoot
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("source-audits", isDirectory: true)
            .appendingPathComponent("2026-08-10-plan-cue-provenance.md")

        XCTAssertTrue(
            FileManager.default.fileExists(atPath: auditURL.path),
            "Expected cue audit at \(auditURL.path)."
        )

        return auditURL
    }

    private func bundledPlanLibraryData() throws -> Data {
        let bundle = Bundle(for: PlanStorageTests.self)
        let url = try XCTUnwrap(
            bundle.url(forResource: "PlanLibrary", withExtension: "json"),
            "Expected PlanLibrary.json in the HangTenTests bundle."
        )
        return try Data(contentsOf: url)
    }

    private func fallbackFeatureAliases(in value: Any) -> [String] {
        if let object = value as? [String: Any] {
            let aliases = (object["fallbackFeatures"] as? [String] ?? [])
                .filter { $0 == "jug" || $0 == "pocket" }
            return aliases + object.values.flatMap(fallbackFeatureAliases)
        }
        if let array = value as? [Any] {
            return array.flatMap(fallbackFeatureAliases)
        }
        return []
    }
}

private struct CueAuditKey: Hashable, Comparable, CustomStringConvertible {
    let planID: String
    let stepID: String?
    let field: String

    var description: String {
        if let stepID {
            return "\(planID) :: \(stepID) :: \(field)"
        }
        return "\(planID) :: \(field)"
    }

    static func < (lhs: CueAuditKey, rhs: CueAuditKey) -> Bool {
        lhs.description < rhs.description
    }
}

private protocol CueAuditDecision {
    var planID: String { get }
    var field: String { get }
    var decision: String { get }
    var sourcePrescription: Bool { get }
    var adaptationType: String? { get }
}

private extension CueAuditDecision {
    var isRetained: Bool {
        decision == "keep" || decision == "adapt"
    }

    var isTimerOrRangeAdaptation: Bool {
        adaptationType == "timer" || adaptationType == "range"
    }
}

private struct AnyCueAuditDecision: CueAuditDecision {
    let planID: String
    let field: String
    let decision: String
    let sourcePrescription: Bool
    let adaptationType: String?

    init(_ base: some CueAuditDecision) {
        planID = base.planID
        field = base.field
        decision = base.decision
        sourcePrescription = base.sourcePrescription
        adaptationType = base.adaptationType
    }
}

private struct CueAuditDocument: Decodable {
    let planSources: [PlanSourceManifestEntry]
    let planFieldRules: [PlanFieldRule]
    let stepFieldRules: [StepFieldRule]
    let targetFallbackRules: [TargetFallbackAuditRule]
}

private struct TargetFallbackAuditRule: Decodable {
    let planID: String
    let primaryKind: HoldKind
    let fingerCapacity: Int
    let fallbackFeatures: [HoldFeature]
    let decision: String
    let sourcePrescription: Bool
    let fingerCapacitySourcePrescription: Bool
    let adaptationType: String
    let sourceURL: String
    let sourceBasis: String
}

private struct PlanSourceManifestEntry: Decodable {
    let planID: String
    let sourceType: String
    let sourceLabel: String
    let sourceURL: String
}

private extension Collection {
    var only: Element? {
        count == 1 ? first : nil
    }
}

private extension String {
    var hasVisibleText: Bool {
        !trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}

private struct PlanFieldRule: Decodable, CueAuditDecision {
    let planID: String
    let fields: [String]
    let decision: String
    let sourcePrescription: Bool
    let adaptationType: String?

    var field: String {
        fields.first ?? ""
    }

    func matches(_ key: CueAuditKey) -> Bool {
        key.planID == planID && key.stepID == nil && fields.contains(key.field)
    }
}

private struct StepFieldRule: Decodable, CueAuditDecision {
    let planID: String
    let stepID: String?
    let stepIDPattern: String?
    let field: String
    let decision: String
    let sourcePrescription: Bool
    let adaptationType: String?

    func matches(_ key: CueAuditKey) -> Bool {
        guard key.planID == planID, key.field == field else {
            return false
        }
        if let stepID {
            return key.stepID == stepID
        }
        guard let stepIDPattern, let actualStepID = key.stepID else {
            return false
        }
        return actualStepID.range(of: stepIDPattern, options: .regularExpression) != nil
    }

}
