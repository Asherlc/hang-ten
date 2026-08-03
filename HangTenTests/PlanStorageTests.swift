import XCTest
@testable import HangTen

final class PlanStorageTests: XCTestCase {
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

        XCTAssertEqual(
            resolvedSteps[0].segments,
            [
                WorkoutSegment(kind: .work, target: .feature(.mediumEdge), timing: .fixed, duration: 20),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 40)
            ]
        )
        XCTAssertEqual(
            resolvedSteps[1].segments,
            [WorkoutSegment(kind: .work, target: .feature(.roundSloper), timing: .stopwatch, duration: nil)]
        )
        XCTAssertEqual(
            resolvedSteps[2].segments,
            [WorkoutSegment(kind: .work, target: .feature(.jug), timing: .undefined, duration: nil)]
        )
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

    func testBundledSourceSeedsClassifyTimedUntimedAndStopwatchActivities() {
        let entrySteps = LegacyPlanSeedCatalog.metoliusEntry.steps

        XCTAssertEqual(
            entrySteps[5].segments,
            [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.roundSloper),
                    timing: .fixed,
                    duration: 10
                ),
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.pocket),
                    timing: .undefined,
                    duration: nil
                )
            ]
        )
        XCTAssertEqual(
            entrySteps[9].segments,
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

    func testMetoliusAdvancedMinuteEightKeepsAlternativeDurationUndefined() {
        let minuteEight = LegacyPlanSeedCatalog.metoliusAdvanced.steps[7]

        XCTAssertEqual(
            minuteEight.segments,
            [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.largeSlope),
                    timing: .undefined,
                    duration: nil
                ),
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
