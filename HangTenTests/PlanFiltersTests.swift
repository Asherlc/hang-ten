import Foundation
import XCTest
@testable import HangTen

final class PlanFiltersTests: XCTestCase {
    private func metadata(
        level: String = "Intermediate",
        provenance: RoutineProvenance = .official,
        category: String = "manufacturer",
        workoutLabels: [String] = [],
        tags: [String] = ["built-in", "manufacturer"]
    ) -> PlanMetadata {
        PlanMetadata(
            title: "Test plan",
            subtitle: "Test subtitle",
            level: level,
            sourceLabel: "Test source",
            sourceURL: URL(string: "https://example.com/source")!,
            provenance: provenance,
            category: category,
            workoutLabels: workoutLabels,
            tags: tags
        )
    }

    func testEmptyFiltersMatchEveryMetadata() {
        let filters = PlanFilters()

        XCTAssertTrue(filters.matches(metadata(level: "Entry")))
        XCTAssertTrue(filters.matches(metadata(level: "Expert", provenance: .adapted)))
    }

    func testMultipleValuesWithinDifficultyUseOrSemantics() {
        var filters = PlanFilters()
        filters.levels = ["Intermediate", "Advanced"]

        XCTAssertTrue(filters.matches(metadata(level: "Intermediate")))
        XCTAssertTrue(filters.matches(metadata(level: "Advanced")))
        XCTAssertFalse(filters.matches(metadata(level: "Entry")))
    }

    func testSelectionsAcrossFacetsUseAndSemantics() {
        var filters = PlanFilters()
        filters.levels = ["Advanced"]
        filters.categories = ["research"]

        XCTAssertTrue(filters.matches(metadata(level: "Advanced", category: "research")))
        XCTAssertFalse(filters.matches(metadata(level: "Advanced", category: "coach")))
        XCTAssertFalse(filters.matches(metadata(level: "Intermediate", category: "research")))
    }

    func testTagsMatchAnySelectedValue() {
        var filters = PlanFilters()
        filters.tags = ["endurance", "strength"]

        XCTAssertTrue(filters.matches(metadata(provenance: .custom, tags: ["strength"])))
        XCTAssertTrue(filters.matches(metadata(provenance: .custom, tags: ["endurance"])))
        XCTAssertFalse(filters.matches(metadata(provenance: .custom, tags: ["mobility"])))
    }

    func testFilterOptionsAreUniqueAndSorted() {
        let options = PlanFilterOptions(metadata: [
            metadata(level: "Advanced", provenance: .adapted, category: "research", workoutLabels: ["strength", "shared"], tags: ["built-in", "research"]),
            metadata(level: "Entry", provenance: .official, category: "manufacturer", workoutLabels: ["shared"], tags: ["built-in", "manufacturer"]),
            metadata(level: "Advanced", provenance: .adapted, category: "research", workoutLabels: ["strength"], tags: ["built-in", "research"])
        ])

        XCTAssertEqual(options.levels, ["Advanced", "Entry"])
        XCTAssertEqual(Set(options.provenances), Set([.official, .adapted]))
        XCTAssertEqual(options.categories, ["manufacturer", "research"])
        XCTAssertEqual(options.tags, ["shared", "strength"])
    }

    func testCustomRoutineTagsRemainFilterableWhileBuiltInTagsAreExcluded() {
        let builtIn = metadata(
            provenance: .official,
            workoutLabels: [],
            tags: ["built-in", "research", "source-only"]
        )
        let custom = metadata(
            provenance: .custom,
            tags: ["research", "coach", "device", "pullups"]
        )

        let options = PlanFilterOptions(metadata: [builtIn, custom])

        XCTAssertEqual(options.tags, ["coach", "device", "pullups", "research"])

        var filters = PlanFilters()
        filters.tags = ["research"]
        XCTAssertFalse(filters.matches(builtIn))
        XCTAssertTrue(filters.matches(custom))
    }

    func testConsumerFilterPresentationShowsOnlyAthleteFacingFacets() {
        let options = PlanFilterOptions(metadata: [
            metadata(
                level: "Advanced",
                provenance: .adapted,
                category: "research",
                workoutLabels: ["strength"],
                tags: ["strength"]
            )
        ])

        XCTAssertEqual(
            PlanFilterPresentationContent.visibleFacets(for: options),
            [.difficulty, .category, .tags]
        )
    }

    func testClearRemovesSelectionsAndActiveFacetCount() {
        var filters = PlanFilters()
        filters.levels = ["Advanced"]
        filters.tags = ["strength"]

        XCTAssertEqual(filters.activeFacetCount, 2)

        filters.clear()

        XCTAssertTrue(filters.isEmpty)
        XCTAssertEqual(filters.activeFacetCount, 0)
    }

    func testCatalogMetadataPreservesBundledFilterFields() {
        let metadata = PlanCatalog.metadata(for: "research.max-hangs")

        XCTAssertEqual(metadata?.level, "Advanced")
        XCTAssertEqual(metadata?.provenance, .adapted)
        XCTAssertEqual(metadata?.category, "research")
        XCTAssertEqual(metadata?.tags, ["built-in", "research"])
    }

    func testBuiltInFilterOptionsExposeCuratedWorkoutLabelsInsteadOfSourceTags() throws {
        let maxHangs = try XCTUnwrap(PlanCatalog.metadata(for: "research.max-hangs"))
        let repeaters = try XCTUnwrap(PlanCatalog.metadata(for: "research.seven-three-repeaters"))

        let options = PlanFilterOptions(metadata: [maxHangs, repeaters])

        XCTAssertEqual(options.tags, ["max-effort", "repeaters"])

        var filters = PlanFilters()
        filters.tags = ["max-effort"]
        XCTAssertTrue(filters.matches(maxHangs))
        XCTAssertFalse(filters.matches(repeaters))
    }

    func testWorkoutLabelPresentationUsesDisplayLabelsForVisualAndAccessibilityContent() {
        XCTAssertEqual(
            WorkoutLabelPresentationContent.displayLabels(for: ["max-effort", "repeaters"]),
            ["Max Effort", "Repeaters"]
        )
    }

    func testMetadataLookupMapPreservesFirstEntryForDuplicateIDs() {
        let first = metadata(level: "Entry")
        let second = metadata(level: "Advanced")
        let lookup = PlanLibraryStore.metadataByPlanID([
            PlanDefinition(id: "duplicate", metadata: first, boardID: nil, blocks: []),
            PlanDefinition(id: "duplicate", metadata: second, boardID: nil, blocks: [])
        ])

        XCTAssertEqual(lookup["duplicate"], first)
    }

    private func workout(
        title: String = "Test workout",
        duration: TimeInterval = 600,
        phase: WorkoutPhase = .hang,
        stepTitle: String = "Hang",
        timing: WorkoutSegmentTiming = .fixed,
        instruction: String = "Complete this task."
    ) -> TrainingPlan {
        TrainingPlan(
            id: "test", title: title, subtitle: "Source-backed description",
            level: "Intermediate", sourceLabel: "Test", sourceURL: nil,
            provenance: .custom, boardID: nil,
            steps: [WorkoutStep(
                id: "step", number: 1, title: stepTitle, instruction: instruction,
                accessory: "", duration: duration, phase: phase,
                segments: [WorkoutSegment(kind: .work, target: .selfSelected, timing: timing, duration: timing == .fixed ? duration : nil)]
            )]
        )
    }

    func testWorkoutDurationBoundariesDoNotOverlap() {
        for duration in [0.0, 599, 600, 1199, 1200, 1800] {
            let matches = WorkoutDurationFilter.allCases.filter { $0 != .any && $0.matches(duration) }
            XCTAssertEqual(matches.count, 1, "Duration \(duration) belongs to exactly one range")
        }
        XCTAssertTrue(WorkoutDurationFilter.underTenMinutes.matches(599))
        XCTAssertTrue(WorkoutDurationFilter.tenToTwentyMinutes.matches(600))
        XCTAssertFalse(WorkoutDurationFilter.tenToTwentyMinutes.matches(1200))
        XCTAssertTrue(WorkoutDurationFilter.twentyMinutesOrMore.matches(1200))
    }

    func testExerciseDetectionDistinguishesCoreFromPullUpsInPullPhase() {
        XCTAssertEqual(workout(phase: .pull, stepTitle: "Jug knee raises").workoutExercises, [.core])
        XCTAssertEqual(workout(phase: .pull, stepTitle: "Hangboard pull-ups").workoutExercises, [.pullUps])
        XCTAssertEqual(workout(phase: .conditioning, stepTitle: "Warm-up · normal pull-ups").workoutExercises, [.pullUps])
        XCTAssertEqual(workout(phase: .conditioning, stepTitle: "Side plank").workoutExercises, [.core])
        XCTAssertEqual(workout(phase: .conditioning, stepTitle: "Push-ups").workoutExercises, [])
        XCTAssertEqual(workout(phase: .hang, stepTitle: "20mm hang + jug knee raises").workoutExercises, [.hangs, .core])
    }

    func testExerciseDetectionReadsSourceTasksWithGenericMinuteTitlesAndExcludesNegativeCues() throws {
        let definitions = BuiltInPlanLibraryDefinition.document
        let store = try PlanLibraryStore(definition: definitions)
        let contact = try XCTUnwrap(store.plan(id: "metolius.contact.entry"))
        let rings = try XCTUnwrap(store.plan(id: "metolius.rock-rings.ten-minute"))
        XCTAssertTrue(contact.workoutExercises.contains(.pullUps))
        XCTAssertTrue(contact.workoutExercises.contains(.core))
        XCTAssertTrue(rings.workoutExercises.contains(.pullUps))
        XCTAssertTrue(rings.workoutExercises.contains(.core))
        XCTAssertEqual(workout(phase: .conditioning, stepTitle: "Choose one: front lever or straight-arm hang").workoutExercises, [.hangs, .core])
        XCTAssertEqual(workout(instruction: "Dead-hang. Do not pull up or lock off.").workoutExercises, [.hangs])
        XCTAssertEqual(workout(instruction: "Dead-hang. Don’t pull up or lock off.").workoutExercises, [.hangs])
        XCTAssertEqual(workout(phase: .conditioning, stepTitle: "Task", instruction: "No pull-ups today. Perform a plank.").workoutExercises, [.core])
    }

    func testExerciseDetectionRetainsAffirmativeClausesAfterNegation() {
        XCTAssertEqual(
            workout(phase: .conditioning, stepTitle: "Task", instruction: "Hang 20 mm; no rest, then 5 pull-ups.").workoutExercises,
            [.hangs, .pullUps]
        )
        XCTAssertEqual(
            workout(phase: .conditioning, stepTitle: "Task", instruction: "No swings today; hold a plank.").workoutExercises,
            [.core]
        )
        XCTAssertEqual(
            workout(phase: .conditioning, stepTitle: "Task", instruction: "Don't do pull-ups, but hold a plank.").workoutExercises,
            [.core]
        )
        XCTAssertEqual(
            workout(phase: .conditioning, stepTitle: "Task", instruction: "No plank today, instead do 5 pull-ups.").workoutExercises,
            [.pullUps]
        )
        XCTAssertEqual(
            workout(phase: .conditioning, stepTitle: "Task", instruction: "No hangs, pull-ups or core today.").workoutExercises,
            []
        )
    }

    func testWorkoutFiltersCombineGroupsAndAllowAnySelectedExerciseAndLevel() {
        var filters = WorkoutBrowserFilters()
        filters.duration = .tenToTwentyMinutes
        filters.exercises = [.pullUps, .core]
        filters.levels = ["Intermediate", "Advanced"]
        XCTAssertTrue(filters.matches(workout(phase: .pull, stepTitle: "Pull-ups"), metadata: nil))
        XCTAssertTrue(filters.matches(workout(phase: .pull, stepTitle: "Knee raises"), metadata: nil))
        XCTAssertFalse(filters.matches(workout(), metadata: nil))
        XCTAssertFalse(filters.matches(workout(duration: 599, phase: .pull, stepTitle: "Pull-ups"), metadata: nil))
        XCTAssertFalse(filters.matches(workout(phase: .pull, stepTitle: "Pull-ups"), metadata: metadata(level: "Entry")))
        XCTAssertEqual(filters.activeFacetCount, 3)
        filters.clear()
        XCTAssertTrue(filters.isEmpty)
    }

    func testSearchFindsDescriptionsAndDisplayedLabelsAndPreservesOrder() {
        let routines = [workout(title: "First"), workout(title: "Second")]
        XCTAssertEqual(routines.filter { $0.matchesWorkoutSearch("source description", metadata: nil) }.map(\.title), ["First", "Second"])
        XCTAssertTrue(workout().matchesWorkoutSearch(" HANGS ", metadata: nil))
        XCTAssertTrue(workout().matchesWorkoutSearch("REPEATERS", metadata: metadata(workoutLabels: ["repeaters"])))
        XCTAssertFalse(workout().matchesWorkoutSearch("built-in", metadata: metadata()))
        XCTAssertFalse(workout().matchesWorkoutSearch("missing", metadata: nil))
        XCTAssertTrue(workout().matchesWorkoutSearch("  ", metadata: nil))
    }

    func testVariableAndUntimedDurationIsExplicitlyEstimated() {
        XCTAssertFalse(workout().hasEstimatedDuration)
        XCTAssertEqual(workout().browserDurationLabel, "10 min")
        XCTAssertTrue(workout(timing: .stopwatch).hasEstimatedDuration)
        XCTAssertTrue(workout(timing: .undefined).hasEstimatedDuration)
        XCTAssertTrue(workout(instruction: "Hang for 7–10 seconds.").hasEstimatedDuration)
        XCTAssertTrue(workout(instruction: "This fourth set is optional.").hasEstimatedDuration)
        XCTAssertTrue(workout(timing: .undefined).browserDurationLabel.hasPrefix("Approx."))
    }

    func testOptionalFocusMetadataDecodesLegacyAndRoundTrips() throws {
        let original = metadata()
        let legacy = try JSONEncoder().encode(original)
        XCTAssertNil(try JSONDecoder().decode(PlanMetadata.self, from: legacy).focus)
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: legacy) as? [String: Any])
        json["focus"] = WorkoutFocus.fingerStrength.rawValue
        let classified = try JSONDecoder().decode(PlanMetadata.self, from: JSONSerialization.data(withJSONObject: json))
        XCTAssertEqual(classified.focus, .fingerStrength)
        XCTAssertEqual(try JSONDecoder().decode(PlanMetadata.self, from: JSONEncoder().encode(classified)), classified)
    }

    func testFocusClassificationUsesAuditedGoalsAndLeavesUnsupportedGoalsAbsent() {
        let lookup = PlanLibraryStore.metadataByPlanID(BuiltInPlanLibraryDefinition.document.plans)
        XCTAssertEqual(lookup["research.max-hangs"]?.focus, .fingerStrength)
        XCTAssertEqual(lookup["research.force-feedback-f80"]?.focus, .fingerEndurance)
        XCTAssertEqual(lookup["method.intermediate-hangboarding.emom"]?.focus, .mixed)
        XCTAssertNil(lookup["research.abrahangs"]?.focus)
        XCTAssertFalse(lookup.values.contains { $0.focus == .pullingStrength })
    }

}
