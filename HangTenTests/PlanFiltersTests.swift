import Foundation
import XCTest
@testable import HangTen

final class PlanFiltersTests: XCTestCase {
    private func metadata(
        level: String = "Intermediate",
        provenance: RoutineProvenance = .official,
        category: String = "manufacturer",
        tags: [String] = ["built-in", "manufacturer"],
        equipment: [String] = ["hangboard"]
    ) -> PlanMetadata {
        PlanMetadata(
            title: "Test plan",
            subtitle: "Test subtitle",
            level: level,
            sourceLabel: "Test source",
            sourceURL: URL(string: "https://example.com/source")!,
            provenance: provenance,
            category: category,
            tags: tags,
            equipment: equipment
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

    func testTagsAndEquipmentMatchAnySelectedValue() {
        var filters = PlanFilters()
        filters.tags = ["endurance", "strength"]
        filters.equipment = ["hangboard", "weights"]

        XCTAssertTrue(filters.matches(metadata(tags: ["built-in", "strength"], equipment: ["hangboard"])))
        XCTAssertTrue(filters.matches(metadata(tags: ["endurance"], equipment: ["weights"])))
        XCTAssertFalse(filters.matches(metadata(tags: ["mobility"], equipment: ["hangboard"])))
    }

    func testFilterOptionsAreUniqueAndSorted() {
        let options = PlanFilterOptions(metadata: [
            metadata(level: "Advanced", provenance: .adapted, category: "research", tags: ["strength", "shared"], equipment: ["hangboard"]),
            metadata(level: "Entry", provenance: .official, category: "manufacturer", tags: ["shared", "built-in"], equipment: ["weights"]),
            metadata(level: "Advanced", provenance: .adapted, category: "research", tags: ["strength"], equipment: ["hangboard"])
        ])

        XCTAssertEqual(options.levels, ["Advanced", "Entry"])
        XCTAssertEqual(Set(options.provenances), Set([.official, .adapted]))
        XCTAssertEqual(options.categories, ["manufacturer", "research"])
        XCTAssertEqual(options.tags, ["built-in", "shared", "strength"])
        XCTAssertEqual(options.equipment, ["hangboard", "weights"])
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
        XCTAssertEqual(metadata?.equipment, ["hangboard"])
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
