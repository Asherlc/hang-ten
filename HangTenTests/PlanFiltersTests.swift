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

    func testConsumerFilterPresentationExcludesEquipmentAndProvenance() {
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
}
