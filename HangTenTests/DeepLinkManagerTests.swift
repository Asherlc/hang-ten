import XCTest
@testable import HangTen

@MainActor
final class DeepLinkManagerTests: XCTestCase {
    func testBoardURLSetsPendingBoardID() {
        let boardID = BoardCatalog.all[0].id
        let manager = DeepLinkManager()

        manager.handle(url: URL(string: "hangten://board/\(boardID)")!)

        XCTAssertEqual(manager.pendingBoardID, boardID)
        XCTAssertNil(manager.pendingHoldID)
        XCTAssertNil(manager.pendingWorkoutPlanID)
    }

    func testBoardURLWithNilHostSetsPendingBoardID() {
        let boardID = BoardCatalog.all[0].id
        let manager = DeepLinkManager()

        manager.handle(url: URL(string: "hangten:///board/\(boardID)")!)

        XCTAssertEqual(manager.pendingBoardID, boardID)
        XCTAssertNil(manager.pendingWorkoutPlanID)
    }

    func testUnknownBoardURLIsIgnored() {
        let manager = DeepLinkManager()

        manager.handle(url: URL(string: "hangten://board/not-a-real-board")!)

        XCTAssertNil(manager.pendingBoardID)
        XCTAssertNil(manager.pendingWorkoutPlanID)
    }

    func testPlanWorkoutURLSetsPendingWorkoutPlanID() {
        let manager = DeepLinkManager()

        manager.handle(url: URL(string: "hangten://plan/research.max-hangs/workout")!)

        XCTAssertEqual(manager.pendingWorkoutPlanID, "research.max-hangs")
        XCTAssertNil(manager.pendingBoardID)
        XCTAssertNil(manager.pendingHoldID)
    }

    func testPlanWorkoutURLWithNilHostSetsPendingWorkoutPlanID() {
        let manager = DeepLinkManager()

        manager.handle(url: URL(string: "hangten:///plan/research.max-hangs/workout")!)

        XCTAssertEqual(manager.pendingWorkoutPlanID, "research.max-hangs")
        XCTAssertNil(manager.pendingBoardID)
    }

    func testUnknownPlanWorkoutURLIsIgnored() {
        let manager = DeepLinkManager()

        manager.handle(url: URL(string: "hangten://plan/not-a-real-plan/workout")!)

        XCTAssertNil(manager.pendingWorkoutPlanID)
    }

    func testPlanURLWithoutWorkoutSuffixIsIgnored() {
        let manager = DeepLinkManager()

        manager.handle(url: URL(string: "hangten://plan/research.max-hangs")!)

        XCTAssertNil(manager.pendingWorkoutPlanID)
    }

    func testClearPendingClearsBoardAndWorkoutState() {
        let manager = DeepLinkManager()
        manager.handle(url: URL(string: "hangten://plan/research.max-hangs/workout")!)

        manager.clearPending()

        XCTAssertNil(manager.pendingWorkoutPlanID)
        XCTAssertNil(manager.pendingBoardID)
        XCTAssertNil(manager.pendingHoldID)
    }

    func testPlanWorkoutURLClearsPriorBoardPending() {
        let boardID = BoardCatalog.all[0].id
        let manager = DeepLinkManager()
        manager.handle(url: URL(string: "hangten://board/\(boardID)")!)

        manager.handle(url: URL(string: "hangten://plan/research.max-hangs/workout")!)

        XCTAssertEqual(manager.pendingWorkoutPlanID, "research.max-hangs")
        XCTAssertNil(manager.pendingBoardID)
        XCTAssertNil(manager.pendingHoldID)
    }
}
