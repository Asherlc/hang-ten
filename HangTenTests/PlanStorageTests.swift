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

    func testSharedWarmUpIsSixtySecondBoardPrimer() throws {
        let seedPlan = LegacyPlanSeedCatalog.maxHangs
        let seedStep = try XCTUnwrap(seedPlan.steps.first)

        XCTAssertEqual(seedStep.title, "Progressive warm-up")
        XCTAssertEqual(seedStep.duration, 60)
        XCTAssertEqual(
            seedStep.instruction,
            "Start with easy 5-, 10-, and 20-second hangs on the outer jugs. Step off between hangs, keep an open grip, and stop if anything hurts. Do a broader warm-up before training."
        )
        XCTAssertEqual(seedStep.accessory, "Board primer · warm up generally first")
        XCTAssertEqual(seedStep.gripType, .openHand)
        XCTAssertEqual(seedStep.targets, [.ids("jug-left", "jug-right")])

        let store = try PlanLibraryStore(definition: BuiltInPlanLibraryDefinition.document)
        let resolvedStep = try XCTUnwrap(
            store.plan(id: seedPlan.id)?.steps.first
        )
        XCTAssertEqual(resolvedStep.duration, 60)
        XCTAssertEqual(resolvedStep.instruction, seedStep.instruction)
    }

    func testBuiltInPlansDoNotEndWithCooldownSteps() {
        XCTAssertTrue(
            LegacyPlanSeedCatalog.all.allSatisfy { $0.steps.last?.phase != .coolDown }
        )
        XCTAssertFalse(
            BuiltInPlanLibraryDefinition.document.blocks.contains { $0.id == "shared.cool-down" }
        )
        XCTAssertTrue(
            PlanLibraryStore.builtIn.plans.allSatisfy { $0.steps.last?.phase != .coolDown }
        )
    }

    func testAbrahangsWarmUpAndThreeMinuteRecoveriesKeepTheirDurations() throws {
        let abrahangsWarmUp = try XCTUnwrap(
            LegacyPlanSeedCatalog.abrahangs.steps.first { $0.id == "abrahangs-warm-up" }
        )
        XCTAssertEqual(abrahangsWarmUp.duration, 120)

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

    func testAbrahangsSecondGripUsesMatchedNineteenMillimeterHalfCrimpEdges() throws {
        let step = try XCTUnwrap(
            LegacyPlanSeedCatalog.abrahangs.steps.first { $0.id == "abrahangs-grip-2" }
        )

        XCTAssertEqual(step.title, "Abrahang · 19 mm half crimp")
        XCTAssertEqual(step.targets, [.ids("edge-19-left", "edge-19-right")])
        XCTAssertEqual(step.gripType, .halfCrimp)
    }

    func testAbrahangsFourthGripUsesExactThreeFingerPocketConfiguration() throws {
        let store = try PlanLibraryStore(definition: BuiltInPlanLibraryDefinition.document)
        let step = try XCTUnwrap(
            store.plan(id: LegacyPlanSeedCatalog.abrahangs.id)?.steps.first {
                $0.id == "abrahangs-grip-4.segment-1"
            }
        )

        XCTAssertEqual(step.title, "Abrahang · Three-finger pocket")
        XCTAssertEqual(
            step.fingerConfiguration,
            FingerConfiguration(engagedFingers: [.index, .middle, .ring])
        )
        XCTAssertEqual(step.fingerConfiguration?.orderedFingers, [.index, .middle, .ring])
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
}
