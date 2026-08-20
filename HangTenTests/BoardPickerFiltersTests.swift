import Foundation
import XCTest
@testable import HangTen

final class BoardPickerFiltersTests: XCTestCase {
    func testTextSearchMatchesNameManufacturerAndSubtitleIgnoringCaseAndDiacritics() {
        let boards = [
            board(id: "name", manufacturer: "Other", name: "Rëactor", subtitle: "Other"),
            board(id: "manufacturer", manufacturer: "MÉTOLIUS", name: "Other", subtitle: "Other"),
            board(id: "subtitle", manufacturer: "Other", name: "Other", subtitle: "Climbér training")
        ]
        var filters = BoardPickerFilters()
        filters.searchText = "metolius"

        XCTAssertEqual(filters.filteredBoards(from: boards).map(\.id), ["manufacturer"])

        filters.searchText = "reactor"
        XCTAssertEqual(filters.filteredBoards(from: boards).map(\.id), ["name"])

        filters.searchText = "climber"
        XCTAssertEqual(filters.filteredBoards(from: boards).map(\.id), ["subtitle"])
    }

    func testManufacturerOptionsAreUniqueAndSortedCaseInsensitively() {
        let boards = [
            board(id: "one", manufacturer: "zeta", name: "One", subtitle: ""),
            board(id: "two", manufacturer: "Alpha", name: "Two", subtitle: ""),
            board(id: "three", manufacturer: "alpha", name: "Three", subtitle: ""),
            board(id: "four", manufacturer: "Alpha", name: "Four", subtitle: "")
        ]

        XCTAssertEqual(
            BoardPickerFilters.manufacturerOptions(from: boards),
            ["Alpha", "zeta"]
        )
    }

    func testManufacturerSelectionMatchesOnlyThatManufacturer() {
        let boards = [
            board(id: "one", manufacturer: "Metolius", name: "One", subtitle: ""),
            board(id: "two", manufacturer: "Trango", name: "Two", subtitle: "")
        ]
        var filters = BoardPickerFilters()
        filters.manufacturer = "metolius"

        XCTAssertEqual(filters.filteredBoards(from: boards).map(\.id), ["one"])
    }

    func testTextSearchAndManufacturerSelectionUseAndLogic() {
        let boards = [
            board(id: "match", manufacturer: "Metolius", name: "Compact", subtitle: ""),
            board(id: "wrong-manufacturer", manufacturer: "Trango", name: "Compact", subtitle: ""),
            board(id: "wrong-search", manufacturer: "Metolius", name: "Wood Grips", subtitle: "")
        ]
        var filters = BoardPickerFilters()
        filters.searchText = "compact"
        filters.manufacturer = "Metolius"

        XCTAssertEqual(filters.filteredBoards(from: boards).map(\.id), ["match"])
    }

    func testDefaultFiltersReturnEveryBoardAndClearRestoresDefault() {
        let boards = [
            board(id: "one", manufacturer: "Metolius", name: "Compact", subtitle: ""),
            board(id: "two", manufacturer: "Trango", name: "Pivot", subtitle: "")
        ]
        var filters = BoardPickerFilters()

        XCTAssertTrue(filters.isEmpty)
        XCTAssertEqual(filters.filteredBoards(from: boards).map(\.id), ["one", "two"])

        filters.searchText = "no match"
        filters.manufacturer = "Metolius"
        XCTAssertTrue(filters.filteredBoards(from: boards).isEmpty)

        filters.clear()

        XCTAssertTrue(filters.isEmpty)
        XCTAssertEqual(filters.filteredBoards(from: boards).map(\.id), ["one", "two"])
    }

    private func board(id: String, manufacturer: String, name: String, subtitle: String) -> TrainingBoard {
        TrainingBoard(
            id: id,
            manufacturer: manufacturer,
            name: name,
            subtitle: subtitle,
            dimensions: "10 in × 5 in",
            aspectRatio: 2,
            holds: [],
            productURL: URL(string: "https://example.com/\(id)")!,
            photoAssetName: nil
        )
    }
}
