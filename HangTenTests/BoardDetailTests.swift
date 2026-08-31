import XCTest
@testable import HangTen

final class BoardDetailTests: XCTestCase {
    func testReportURLUsesTheSelectedPhysicalPresentation() throws {
        let url = try XCTUnwrap(BoardDetailIssueReportDestination.make(
            formURL: URL(string: "https://tally.so/r/XxbJG4")!,
            board: fixtureBoard(),
            selectedPresentationID: "face-b",
            appVersion: "1.2.3",
            build: "456"
        ))
        let items = try XCTUnwrap(
            URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems
        )
        let values = try Dictionary(uniqueKeysWithValues: items.map { item in
            (item.name, try XCTUnwrap(item.value))
        })

        XCTAssertEqual(values["presentation_id"], "face-b")
        XCTAssertEqual(values["presentation_name"], "Face B — deep slopers")
    }

    func testReportURLRejectsAnUnknownPresentationInsteadOfFallingBack() {
        XCTAssertNil(BoardDetailIssueReportDestination.make(
            formURL: URL(string: "https://tally.so/r/XxbJG4")!,
            board: fixtureBoard(),
            selectedPresentationID: "missing",
            appVersion: "1.2.3",
            build: "456"
        ))
    }

    private func fixtureBoard() -> TrainingBoard {
        TrainingBoard(
            id: "test.pocket-edge",
            manufacturer: "Test Climbing",
            name: "Pocket & Edge",
            subtitle: "Test board",
            dimensions: nil,
            aspectRatio: 2,
            holds: [],
            productURL: URL(string: "https://example.com/board")!,
            photoAssetName: nil,
            presentations: [
                BoardPresentation(
                    id: "face-a",
                    name: "Face A",
                    aspectRatio: 2,
                    isDefault: true
                ),
                BoardPresentation(
                    id: "face-b",
                    name: "Face B — deep slopers",
                    aspectRatio: 2,
                    isDefault: false
                )
            ]
        )
    }
}
