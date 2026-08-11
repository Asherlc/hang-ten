import XCTest
@testable import HangTen

final class PlanStorageTests: XCTestCase {
    func testGripTypeDecodesLegacyHoldCombinedValuesAsOpenHand() throws {
        for legacyValue in ["sloper", "twoFingerPocket", "threeFingerPocket", "fourFingerPocket"] {
            let decoded = try JSONDecoder().decode(
                GripType.self,
                from: Data("\"\(legacyValue)\"".utf8)
            )
            let reencoded = try JSONEncoder().encode(decoded)
            let reencodedRawValue = try JSONDecoder().decode(String.self, from: reencoded)

            XCTAssertEqual(decoded, .openHand, "Expected \(legacyValue) to migrate to open-hand posture.")
            XCTAssertEqual(reencodedRawValue, "openHand")
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

    func testFingerCueCapacityAccessibilityLabelUsesSingularForOneFinger() {
        XCTAssertEqual(FingerCue.capacity(1).accessibilityLabel, "Up to 1 finger")
        XCTAssertEqual(FingerCue.capacity(2).accessibilityLabel, "Up to 2 fingers")
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

    func testWorkoutStepDefinitionRoundTripsFingerConfigurationWithCurrentPostureVocabulary() throws {
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
              "gripType": "halfCrimp",
              "fingerConfiguration": { "engagedFingers": ["index", "ring"] }
            }
            """#.utf8
        )

        let decoded = try JSONDecoder().decode(WorkoutStepDefinition.self, from: data)
        let encoded = try JSONEncoder().encode(decoded)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        let fingerConfiguration = try XCTUnwrap(object["fingerConfiguration"] as? [String: [String]])

        XCTAssertEqual(decoded.gripType, .halfCrimp)
        XCTAssertEqual(decoded.fingerConfiguration?.orderedFingers, [.index, .ring])
        XCTAssertEqual(object["gripType"] as? String, "halfCrimp")
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

    func testVersionThreeDefinitionsResolveOrderedSegmentTimingModes() throws {
        let fixedWork = WorkoutSegmentDefinition(
            kind: .work,
            target: .feature(.mediumEdge, fallbacks: []),
            timing: .fixed,
            duration: 20
        )
        let fixedRest = WorkoutSegmentDefinition(
            kind: .rest,
            target: nil,
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
                        target: .feature(.roundSloper, fallbacks: []),
                        timing: .stopwatch,
                        duration: nil
                    )
                ]
            ),
            makeStep(
                id: "undefined",
                duration: 60,
                phase: .pull,
                targets: [.feature(.jug, fallbacks: [])],
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        target: .feature(.jug, fallbacks: []),
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
            [WorkoutSegment(kind: .work, target: .feature(.jug), timing: .undefined, duration: nil)]
        )
    }

    func testSegmentTargetFixturesRoundTripMultiTargetAndLegacyTarget() throws {
        let data = Data(
            #"""
            {
              "schemaVersion": 3,
              "metadata": {
                "id": "segment.fixture",
                "version": "3.0.0",
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
                      "target": { "feature": "mediumEdge" },
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
        XCTAssertNotNil(encodedSegments[1]["target"])
        XCTAssertNil(encodedSegments[1]["targets"])
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
        XCTAssertEqual(persistedSegments[1].target, .feature(.mediumEdge, fallbacks: []))
    }

    func testSchemaTwoDefinitionsWithoutSegmentsMigrateWithCompatibilitySegments() throws {
        let data = Data(
            #"""
            {
              "schemaVersion": 2,
              "metadata": {
                "id": "legacy.fixture",
                "version": "2.0.0",
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
                    "targets": []
                  },
                  {
                    "id": "timed",
                    "title": "Timed",
                    "instruction": "Hang",
                    "accessory": "10s",
                    "duration": 30,
                    "phase": "hang",
                    "targets": [{ "kind": "edge" }],
                    "activeDuration": 10
                  },
                  {
                    "id": "untimed",
                    "title": "Untimed",
                    "instruction": "Pull",
                    "accessory": "Repetitions",
                    "duration": 60,
                    "phase": "pull",
                    "targets": [{ "kind": "jug" }]
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

        XCTAssertEqual(store.definition.schemaVersion, PlanDefinitionSchema.currentVersion)
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
            target: .kind(.edge),
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
            target: nil,
            timing: .undefined,
            duration: nil
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].target"
        })
    }

    func testRestSegmentCannotTargetAHold() {
        let segment = WorkoutSegmentDefinition(
            kind: .rest,
            target: .kind(.edge),
            timing: .fixed,
            duration: 30
        )

        XCTAssertTrue(validationIssues(for: segment).contains {
            $0.path == "blocks[0].steps[0].segments[0].target"
        })
    }

    func testRestSegmentRequiresDurationRegardlessOfTiming() {
        let segment = WorkoutSegmentDefinition(
            kind: .rest,
            target: nil,
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
            target: nil,
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
            target: .kind(.edge),
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
            target: .kind(.edge),
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
                target: .kind(.edge),
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
            target: .kind(.edge),
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
                        WorkoutSegmentDefinition(kind: .work, target: .kind(.edge), timing: .fixed, duration: 20),
                        WorkoutSegmentDefinition(kind: .rest, target: nil, timing: .fixed, duration: 5)
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
                        WorkoutSegmentDefinition(kind: .work, target: .kind(.edge), timing: .fixed, duration: 0),
                        WorkoutSegmentDefinition(kind: .rest, target: nil, timing: .fixed, duration: 30)
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
                        WorkoutSegmentDefinition(kind: .work, target: .kind(.edge), timing: .fixed, duration: 5),
                        WorkoutSegmentDefinition(kind: .rest, target: nil, timing: .fixed, duration: 5)
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
                        WorkoutSegmentDefinition(kind: .work, target: .kind(.edge), timing: .fixed, duration: 20),
                        WorkoutSegmentDefinition(kind: .rest, target: nil, timing: .fixed, duration: 10)
                    ]
                ),
                makeStep(
                    id: "foo.segment-1",
                    duration: 10,
                    targets: [.kind(.edge)],
                    segments: [
                        WorkoutSegmentDefinition(kind: .work, target: .kind(.edge), timing: .fixed, duration: 10)
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
                        WorkoutSegmentDefinition(kind: .work, target: .kind(.edge), timing: .stopwatch, duration: nil),
                        WorkoutSegmentDefinition(kind: .rest, target: nil, timing: .fixed, duration: 30)
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
                WorkoutSegmentDefinition(kind: .work, target: .kind(.edge), timing: .undefined, duration: nil)
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
                WorkoutSegmentDefinition(kind: .work, target: .kind(.edge), timing: .undefined, duration: nil)
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
                    target: .feature(.pocket),
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

    func testAbrahangsSecondGripKeepsSourceBackedFrontThreeOpenCue() throws {
        let step = try XCTUnwrap(
            LegacyPlanSeedCatalog.abrahangs.steps.first { $0.id == "abrahangs-grip-2" }
        )

        XCTAssertEqual(step.title, "Abrahang · F3 Open Hang")
        XCTAssertEqual(step.targets, [.ids("edge-19-left", "edge-19-right")])
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
                    target: .ids("edge-19-left", "edge-19-right"),
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

    func testRequestedSourcePlansAreSeededAndResolved() throws {
        let expectedIDs = [
            "lattice.lite-home-adaptations",
            "hoopers-beta.introductory-home-hangboard",
            "method.intermediate-hangboarding.repeaters",
            "method.intermediate-hangboarding.emom",
            "lattice.beginner-climbers-training-guide",
            "rei.hangboard-sample-workout",
            "trango.rock-prodigy-training-center.intermediate"
        ]

        XCTAssertTrue(expectedIDs.allSatisfy { id in
            LegacyPlanSeedCatalog.all.contains { $0.id == id } && PlanCatalog.plan(id: id) != nil
        })
        XCTAssertEqual(
            expectedIDs.map { PlanCatalog.metadata(for: $0)?.category },
            ["coach", "coach", "coach", "coach", "coach", "retailer", "manufacturer"]
        )
    }

    func testRockProdigyMetadataUsesDistinctPinchKindAndDepthFeatures() throws {
        let board = BoardCatalog.rockProdigyTrainingCenter
        let pinchHolds = board.holds.filter { $0.kind == .pinch }

        XCTAssertEqual(pinchHolds.count, 6)
        XCTAssertEqual(
            Set(pinchHolds.flatMap { $0.features }),
            Set([.widePinch, .mediumPinch, .smallPinch])
        )
        XCTAssertEqual(
            board.holds.first { $0.id == "trango.rptc.left.large-open-rail" }?.depthRangeMillimeters,
            20...33
        )
        XCTAssertEqual(
            board.holds.first { $0.id == "trango.rptc.left.small-crimp-rail" }?.depthRangeMillimeters,
            10...24
        )
    }

    func testRockProdigyBoardDesignHoldIDsMatchMetadata() throws {
        let board = BoardCatalog.rockProdigyTrainingCenter
        let design = try XCTUnwrap(BoardDesignCatalog.design(for: board.id))

        XCTAssertEqual(Set(board.holds.map(\.id)), Set(design.holds.map(\.holdID)))
        XCTAssertEqual(design.holds.count, board.holds.count)
    }

    func testRockProdigyPlanIsBoardSpecificAndEveryTargetResolves() throws {
        let plan = LegacyPlanSeedCatalog.rockProdigyIntermediate
        let board = BoardCatalog.rockProdigyTrainingCenter

        XCTAssertEqual(plan.boardID, board.id)
        XCTAssertTrue(plan.steps.flatMap(\.targets).contains { $0.feature == .widePinch })
        XCTAssertFalse(plan.steps.flatMap(\.targets).contains { $0.kind == .edge })
        XCTAssertTrue(
            plan.steps.flatMap(\.targets).allSatisfy {
                !BoardTargetResolver.resolveHoldIDs(for: $0, on: board).isEmpty
            }
        )
    }

    func testCompactIIStillResolvesGenericNonPinchPlans() throws {
        let compact = BoardCatalog.compactII
        let genericPlans = LegacyPlanSeedCatalog.all.filter {
            $0.boardID == nil && $0.id != LegacyPlanSeedCatalog.reiHangboardSample.id
        }

        XCTAssertTrue(
            genericPlans.allSatisfy { plan in
                plan.steps.flatMap(\.targets).allSatisfy {
                    !BoardTargetResolver.resolveHoldIDs(for: $0, on: compact).isEmpty
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
        XCTAssertEqual(BoardTargetResolver.resolveHoldIDs(for: reiMediumPinch, on: BoardCatalog.rockProdigyTrainingCenter), ["trango.rptc.left.medium-pinch", "trango.rptc.right.medium-pinch"])
        XCTAssertFalse(BoardTargetResolver.resolveHoldIDs(for: reiMediumPinch, on: compact).isEmpty)
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

    func testRockProdigyIntermediateKeepsDeadHangOnlyAndSevenThenSixRepStructure() throws {
        let plan = LegacyPlanSeedCatalog.rockProdigyIntermediate
        XCTAssertTrue(plan.steps.dropFirst().filter { $0.phase == .hang }.allSatisfy {
            $0.instruction.contains("Dead hang only") &&
                $0.instruction.contains("do not perform pull-ups or lock-offs")
        })
        XCTAssertEqual(plan.steps.filter { $0.id.contains("-set-1-rep-") }.count, 42)
        XCTAssertEqual(plan.steps.filter { $0.id.contains("-set-2-rep-") }.count, 36)
        XCTAssertEqual(plan.steps.filter { $0.id.contains("-recovery") }.map(\.duration).filter { $0 == 180 }.count, 12)
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

    private func makeLibrary(steps: [WorkoutStepDefinition]) -> PlanLibraryDefinition {
        PlanLibraryDefinition(
            schemaVersion: 3,
            metadata: PlanLibraryMetadata(
                id: "test.library",
                version: "3.0.0",
                title: "Test library",
                generatedAt: "2026-08-02"
            ),
            boardMappings: [],
            blocks: [WorkoutBlockDefinition(id: "test.block", steps: steps)],
            plans: [
                PlanDefinition(
                    id: "test.plan",
                    metadata: PlanMetadata(
                        title: "Test plan",
                        subtitle: "Storage tests",
                        level: "Test",
                        sourceLabel: "Test fixture",
                        sourceURL: URL(string: "https://example.com/test")!,
                        provenance: .adapted
                    ),
                    boardID: nil,
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
        case "research.force-feedback-f100":
            return ["subtitle", "instruction", "count", "interval"]
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
