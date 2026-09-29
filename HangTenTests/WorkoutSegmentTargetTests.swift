import XCTest
@testable import HangTen

final class WorkoutSegmentTargetTests: XCTestCase {
    func testPerHandTasksRoundTripWithExactAndCategoricalDepth() throws {
        let json = Data(#"{"tasks":[[{"target":{"kind":"edge","depth":{"minMM":20,"maxMM":20}}},{"target":{"kind":"sloper","shape":"round","depth":{"category":"large"}},"side":"right"}],[{"target":{"kind":"edge","depth":{"minMM":20,"maxMM":35}}}]]}"#.utf8)
        let target = try JSONDecoder().decode(WorkoutSegmentTarget.self, from: json)
        let encoded = try JSONEncoder().encode(target)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        let tasks = try XCTUnwrap(object["tasks"] as? [[[String: Any]]])
        XCTAssertEqual(tasks.map(\.count), [2, 1])
        let exact = try XCTUnwrap((tasks[0][0]["target"] as? [String: Any])?["depth"] as? [String: Double])
        XCTAssertEqual(exact, ["minMM": 20, "maxMM": 20])
        let category = try XCTUnwrap((tasks[0][1]["target"] as? [String: Any])?["depth"] as? [String: String])
        XCTAssertEqual(category, ["category": "large"])
        XCTAssertEqual(tasks[0][1]["side"] as? String, "right")
        XCTAssertEqual(try JSONDecoder().decode(WorkoutSegmentTarget.self, from: encoded), target)
    }

    func testAnyTargetKeepsTheHandCountExplicit() throws {
        let mixed = try JSONDecoder().decode(
            WorkoutSegmentTarget.self,
            from: Data(#"{"tasks":[[{"target":"any"},{"target":"any"}],[{"target":{"kind":"edge"}},{"target":{"kind":"edge"}}]]}"#.utf8)
        )
        XCTAssertEqual(mixed.planTasks?.map(\.count), [2, 2])
        XCTAssertNil(mixed.planTasks?[0][0].target)
        XCTAssertFalse(mixed.isSelfSelected)
        let chosenOnly = try JSONDecoder().decode(
            WorkoutSegmentTarget.self,
            from: Data(#"{"tasks":[[{"target":"any"},{"target":"any"}]]}"#.utf8)
        )
        XCTAssertTrue(chosenOnly.isSelfSelected)
        XCTAssertThrowsError(try JSONDecoder().decode(
            WorkoutSegmentTarget.self, from: Data(#"{"tasks":[]}"#.utf8)
        ))
    }

    func testPerHandTasksRejectMalformedShapes() {
        let invalid = [
            #"{"tasks":[]}"#,
            #"{"tasks":[[{"target":"all"}]]}"#,
            #"{"tasks":[[{"target":{"kind":"edge"}},{"target":{"kind":"edge"}},{"target":{"kind":"edge"}}]]}"#,
            #"{"tasks":[[{"target":{"kind":"edge","depth":{"minMM":35,"maxMM":20}}}]]}"#,
            #"{"tasks":[[{"target":{"kind":"edge","depth":{"minMM":-1,"maxMM":20}}}]]}"#,
            #"{"tasks":[[{"target":{"kind":"edge","depth":{"category":"medium","minMM":20}}}]]}"#,
            #"{"tasks":[[{"target":{"kind":"edge","depth":{"minMM":20,"maxMM":20,"unit":"mm"}}}]]}"#,
            #"{"tasks":[[{"target":{"kind":"edge"},"side":"both"}]]}"#,
            #"{"tasks":[[{"target":{"kind":"edge","unknown":true}}]]}"#,
            #"{"tasks":[[{"target":{}}]]}"#
        ]
        for input in invalid {
            XCTAssertThrowsError(try JSONDecoder().decode(WorkoutSegmentTarget.self, from: Data(input.utf8)), input)
        }
    }

    func testPerHandStepDerivesHandUseWithoutEncodingRedundantFields() throws {
        let target = WorkoutSegmentTarget.tasks([[
            PlanHandTarget(target: .init(kind: .edge), side: .left)
        ]])
        let step = WorkoutStepDefinition(
            id: "left-hang", title: "Left hang", instruction: "", accessory: "",
            duration: 7, phase: .hang,
            segments: [WorkoutSegmentDefinition(
                kind: .work, target: target, timing: .fixed, duration: 7
            )],
            handUse: .single, side: .left
        )
        let encoded = try JSONEncoder().encode(step)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        XCTAssertNil(object["handUse"])
        XCTAssertNil(object["side"])
        let decoded = try JSONDecoder().decode(WorkoutStepDefinition.self, from: encoded)
        XCTAssertEqual(decoded.handUse, .single)
        XCTAssertEqual(decoded.side, .left)
        XCTAssertEqual(decoded.segments[0].target, target)
    }

    func testLegacyCustomTargetKeepsItsExactContactPin() throws {
        let pinned = ContactRequirement(
            contactID: "my-board-left-edge", kind: .edge, selection: .single
        )
        let step = WorkoutStepDefinition(
            id: "custom", title: "Custom", instruction: "", accessory: "",
            duration: 7, phase: .hang,
            segments: [WorkoutSegmentDefinition(
                kind: .work, target: .requirements([pinned]),
                timing: .fixed, duration: 7
            )],
            handUse: .single, side: .left
        )
        let encoded = try JSONEncoder().encode(step)
        let decoded = try JSONDecoder().decode(WorkoutStepDefinition.self, from: encoded)
        XCTAssertEqual(decoded.segments[0].target, .requirements([pinned]))
        XCTAssertEqual(decoded.handUse, .single)
        XCTAssertEqual(decoded.side, .left)
    }

    func testRequirementsRejectsEmptyArrayOnDecode() throws {
        let json = Data(#"{"kind":"requirements","requirements":[]}"#.utf8)
        XCTAssertThrowsError(try JSONDecoder().decode(WorkoutSegmentTarget.self, from: json))
    }

    func testSelfSelectedRoundTrips() throws {
        let encoded = try JSONEncoder().encode(WorkoutSegmentTarget.selfSelected)
        let decoded = try JSONDecoder().decode(WorkoutSegmentTarget.self, from: encoded)
        XCTAssertEqual(decoded, .selfSelected)

        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )
        XCTAssertEqual(object["kind"] as? String, "selfSelected")
        XCTAssertNil(object["requirements"])
    }

    func testRequirementsRoundTrips() throws {
        let target = WorkoutSegmentTarget.fromLegacyTargets([.kind(.edge)])
        let encoded = try JSONEncoder().encode(target)
        let decoded = try JSONDecoder().decode(WorkoutSegmentTarget.self, from: encoded)
        XCTAssertEqual(decoded, .requirements([.kind(.edge)]))
    }

    func testWorkSegmentDefinitionRequiresTarget() throws {
        let json = Data(#"{"kind":"work","timing":"fixed","duration":10}"#.utf8)
        XCTAssertThrowsError(
            try JSONDecoder().decode(WorkoutSegmentDefinition.self, from: json)
        )
    }

    func testRestSegmentDefinitionRejectsTarget() throws {
        let json = Data(
            #"{"kind":"rest","timing":"fixed","duration":10,"target":{"kind":"selfSelected"}}"#.utf8
        )
        XCTAssertThrowsError(
            try JSONDecoder().decode(WorkoutSegmentDefinition.self, from: json)
        )
    }

    func testLegacyEmptyWorkTargetsDecodeAsSelfSelected() throws {
        let json = Data(
            #"{"kind":"work","timing":"fixed","duration":10,"targets":[]}"#.utf8
        )
        let decoded = try JSONDecoder().decode(WorkoutSegmentDefinition.self, from: json)
        XCTAssertEqual(decoded.target, .selfSelected)
    }

    func testLegacyRestEmptyTargetsDecodeWithoutTarget() throws {
        let json = Data(
            #"{"kind":"rest","timing":"fixed","duration":10,"targets":[]}"#.utf8
        )
        let decoded = try JSONDecoder().decode(WorkoutSegmentDefinition.self, from: json)
        XCTAssertNil(decoded.target)
    }

    func testWorkSegmentDefinitionEncodesTaggedTargetNotLegacyArray() throws {
        let segment = WorkoutSegmentDefinition(
            kind: .work,
            target: .selfSelected,
            timing: .fixed,
            duration: 7
        )
        let encoded = try JSONEncoder().encode(segment)
        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded) as? [String: Any]
        )
        XCTAssertNotNil(object["target"])
        XCTAssertNil(object["targets"])
    }

    func testPlanValidationRejectsEmptyRequirementsViaSelfSelectedOnBoardBoundPlan() {
        let step = WorkoutStepDefinition(
            id: "hang",
            title: "Hang",
            instruction: "Hang.",
            accessory: "7s",
            duration: 7,
            phase: .hang,
            segments: [
                WorkoutSegmentDefinition(
                    kind: .work,
                    target: .selfSelected,
                    timing: .fixed,
                    duration: 7
                )
            ],
            activeDuration: 7
        )
        let library = PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "test.library",
                title: "Test library",
                generatedAt: "2026-09-19"
            ),
            blocks: [WorkoutBlockDefinition(id: "block", steps: [step])],
            plans: [
                PlanDefinition(
                    id: "test.plan",
                    metadata: PlanMetadata(
                        title: "Test",
                        subtitle: "Test",
                        level: "Test",
                        sourceLabel: "Test",
                        sourceURL: URL(string: "https://example.com"),
                        provenance: .official
                    ),
                    boardID: BoardCatalog.defaultBoard.id,
                    blocks: [WorkoutBlockReference(blockID: "block")]
                )
            ]
        )
        let issues = library.validationIssues(availableBoards: BoardCatalog.all)
        XCTAssertTrue(issues.contains {
            $0.path == "blocks[0].steps[0].segments[0].target" &&
                $0.message == "Work segments require a target."
        })
    }
}
