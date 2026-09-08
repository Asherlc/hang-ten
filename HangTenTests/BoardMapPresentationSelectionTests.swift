import CoreGraphics
import XCTest
@testable import HangTen

final class BoardMapPresentationSelectionTests: XCTestCase {
    func testSelectionUsesPresentationContainingEveryHighlightedHold() {
        let board = pivotAvailabilityBoard()

        let selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: "primary",
            activeHoldID: "shared",
            highlightedHoldIDs: ["shared", "rotation-only"]
        )

        XCTAssertEqual(selection.presentationID, "rotated")
    }

    func testSelectionPrefersCurrentPresentationWhenEveryHighlightStillFits() {
        let board = pivotAvailabilityBoard()
        var selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: "rotated",
            activeHoldID: nil,
            highlightedHoldIDs: ["shared", "rotation-only"]
        )

        selection.updateHighlights(
            from: ["shared", "rotation-only"],
            to: ["shared"],
            activeHoldID: nil,
            on: board
        )

        XCTAssertEqual(selection.presentationID, "rotated")
    }

    func testHighlightUpdateMovesToPresentationContainingEveryHighlightedHold() {
        let board = pivotAvailabilityBoard()
        var selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: "primary",
            activeHoldID: "shared",
            highlightedHoldIDs: ["shared"]
        )

        selection.updateHighlights(
            from: ["shared"],
            to: ["shared", "rotation-only"],
            activeHoldID: "shared",
            on: board
        )

        XCTAssertEqual(selection.presentationID, "rotated")
    }

    func testActiveHoldChangeCannotMoveAwayFromCompleteHighlightedSet() {
        let board = pivotAvailabilityBoard()
        var selection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: "primary",
            activeHoldID: nil,
            highlightedHoldIDs: []
        )

        selection.activateHold(
            id: "shared",
            highlightedHoldIDs: ["shared", "rotation-only"],
            on: board
        )

        XCTAssertEqual(selection.presentationID, "rotated")
    }

    private func pivotAvailabilityBoard() -> TrainingBoard {
        TrainingBoard(
            id: "pivot-fixture",
            manufacturer: "Example",
            name: "Pivot fixture",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            holds: [
                hold(id: "shared"),
                hold(id: "rotation-only"),
            ],
            productURL: URL(string: "https://example.com/pivot-fixture")!,
            photoAssetName: nil,
            presentations: [
                BoardPresentation(
                    id: "primary",
                    name: "Primary",
                    aspectRatio: 1,
                    isDefault: true,
                    availableHoldIDs: ["shared"]
                ),
                BoardPresentation(
                    id: "rotated",
                    name: "Rotated",
                    aspectRatio: 1,
                    isDefault: false,
                    sourcePresentationID: "primary",
                    availableHoldIDs: ["shared", "rotation-only"],
                    rotationDegrees: 90
                ),
            ]
        )
    }

    private func hold(id: String) -> BoardHold {
        BoardHold(
            id: id,
            name: id,
            kind: .edge,
            geometry: [
                BoardHoldPiece(
                    id: "\(id)-piece",
                    holdID: id,
                    frame: CGRect(x: 0.1, y: 0.1, width: 0.2, height: 0.2),
                    shape: .roundedRect(cornerRadiusFraction: 0),
                    treatment: .surface
                )
            ],
            presentationID: "primary"
        )
    }
}
