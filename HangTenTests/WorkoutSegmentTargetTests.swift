import XCTest
@testable import HangTen

final class WorkoutSegmentTargetTests: XCTestCase {
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
