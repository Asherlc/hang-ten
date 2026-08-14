import Foundation
import XCTest
@testable import HangboardWorkbench

final class CheckoutSelectionTests: XCTestCase {
    private var temporaryDirectories: [URL] = []
    private var defaults: UserDefaults!
    private var suiteName: String!

    override func setUp() {
        super.setUp()
        suiteName = "CheckoutSelectionTests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        for directory in temporaryDirectories {
            try? FileManager.default.removeItem(at: directory)
        }
        super.tearDown()
    }

    func testValidatedURLAcceptsTheDirectWorkbenchAndBoardLibraryMarkers() throws {
        let root = try makeCheckout()

        let result = try CheckoutSelection.validatedURL(root.appending(path: "."))

        XCTAssertEqual(result.path, root.resolvingSymlinksInPath().path)
    }

    func testValidatedURLRejectsEachMissingCheckoutMarker() throws {
        for marker in [
            ".git",
            "Hangboards",
            "Tools/HangboardWorkbench/server.py",
            "Tools/HangboardWorkbench/board_package.py",
            "Tools/HangboardWorkbench/board_geometry.py",
        ] {
            let root = try makeCheckout()
            try FileManager.default.removeItem(at: root.appending(path: marker))

            XCTAssertThrowsError(try CheckoutSelection.validatedURL(root), "Accepted checkout missing \(marker)")
        }
    }

    func testValidatedURLRejectsLegacyToolRoots() throws {
        let root = try makeLegacyCheckout()

        XCTAssertThrowsError(try CheckoutSelection.validatedURL(root))
    }

    func testValidatedURLAcceptsAWorktreeGitFile() throws {
        let root = try makeCheckout()
        try FileManager.default.removeItem(at: root.appending(path: ".git"))
        try Data("gitdir: /tmp/example\n".utf8).write(to: root.appending(path: ".git"))

        XCTAssertEqual(try CheckoutSelection.validatedURL(root), root.resolvingSymlinksInPath())
    }

    func testRememberStoresOnlyTheNormalizedCheckoutPath() throws {
        let root = try makeCheckout()
        let selection = CheckoutSelection(defaults: defaults)

        selection.remember(root.appending(path: "."))

        let persisted = try XCTUnwrap(defaults.persistentDomain(forName: suiteName))
        XCTAssertEqual(persisted.count, 1)
        XCTAssertEqual(persisted.values.first as? String, root.resolvingSymlinksInPath().path)
        XCTAssertEqual(selection.lastValidCheckout(), root.resolvingSymlinksInPath())
    }

    func testRememberedCheckoutIsDiscardedWhenMarkersDisappear() throws {
        let root = try makeCheckout()
        let selection = CheckoutSelection(defaults: defaults)
        selection.remember(root)
        try FileManager.default.removeItem(at: root.appending(path: ".git"))

        XCTAssertNil(selection.lastValidCheckout())
        XCTAssertTrue(defaults.persistentDomain(forName: suiteName)?.isEmpty ?? true)
    }

    func testClearRemovesRememberedCheckout() throws {
        let root = try makeCheckout()
        let selection = CheckoutSelection(defaults: defaults)
        selection.remember(root)

        selection.clear()

        XCTAssertNil(selection.lastValidCheckout())
        XCTAssertTrue(defaults.persistentDomain(forName: suiteName)?.isEmpty ?? true)
    }

    private func makeCheckout() throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appending(path: "CheckoutSelectionTests-\(UUID().uuidString)", directoryHint: .isDirectory)
        temporaryDirectories.append(root)
        try FileManager.default.createDirectory(at: root.appending(path: ".git"), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(
            at: root.appending(path: "Hangboards"),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: root.appending(path: "Tools/HangboardWorkbench"),
            withIntermediateDirectories: true
        )
        try Data().write(to: root.appending(path: "Tools/HangboardWorkbench/server.py"))
        try Data().write(to: root.appending(path: "Tools/HangboardWorkbench/board_package.py"))
        try Data().write(to: root.appending(path: "Tools/HangboardWorkbench/board_geometry.py"))
        return root
    }

    private func makeLegacyCheckout() throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appending(path: "CheckoutSelectionTests-legacy-\(UUID().uuidString)", directoryHint: .isDirectory)
        temporaryDirectories.append(root)
        try FileManager.default.createDirectory(at: root.appending(path: ".git"), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(
            at: root.appending(path: "Tools/HangboardOnboarding/boards"),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: root.appending(path: "Tools/hold-highlight-editor"),
            withIntermediateDirectories: true
        )
        return root
    }
}
