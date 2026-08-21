import Darwin
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

    func testValidatedURLAcceptsLocalRepositoryWithoutWorkbenchSources() throws {
        let root = try makeCheckout()

        let result = try CheckoutSelection.validatedURL(root.appending(path: "."))

        XCTAssertEqual(result.path, root.resolvingSymlinksInPath().path)
    }

    func testValidatedURLRejectsEachMissingRepositoryMarker() throws {
        for marker in [
            ".git",
            "Hangboards",
        ] {
            let root = try makeCheckout()
            try FileManager.default.removeItem(at: root.appending(path: marker))

            XCTAssertThrowsError(try CheckoutSelection.validatedURL(root), "Accepted checkout missing \(marker)")
        }
    }

    func testValidatedURLRejectsRepositoryWithoutBoardLibrary() throws {
        let root = try makeInvalidCheckout()

        XCTAssertThrowsError(try CheckoutSelection.validatedURL(root))
    }

    func testValidatedURLAcceptsAWorktreeGitFile() throws {
        let root = try makeCheckout()
        try FileManager.default.removeItem(at: root.appending(path: ".git"))
        try Data("gitdir: /tmp/example\n".utf8).write(to: root.appending(path: ".git"))

        XCTAssertEqual(try CheckoutSelection.validatedURL(root), root.resolvingSymlinksInPath())
    }

    func testValidatedURLRejectsASymlinkedGitMarker() throws {
        let root = try makeCheckout()
        let gitMarker = root.appending(path: ".git")
        let target = root.appending(path: "git-metadata", directoryHint: .isDirectory)
        try FileManager.default.removeItem(at: gitMarker)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        try FileManager.default.createSymbolicLink(at: gitMarker, withDestinationURL: target)

        XCTAssertThrowsError(try CheckoutSelection.validatedURL(root))
    }

    func testValidatedURLRejectsANonFileOrDirectoryGitMarker() throws {
        let root = try makeCheckout()
        let gitMarker = root.appending(path: ".git")
        try FileManager.default.removeItem(at: gitMarker)
        XCTAssertEqual(gitMarker.path.withCString { mkfifo($0, 0o600) }, 0)

        XCTAssertThrowsError(try CheckoutSelection.validatedURL(root))
    }

    func testValidatedURLRejectsASymlinkedBoardLibrary() throws {
        let root = try makeCheckout()
        let hangboards = root.appending(path: "Hangboards")
        let target = root.appending(path: "linked-hangboards", directoryHint: .isDirectory)
        try FileManager.default.removeItem(at: hangboards)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        try FileManager.default.createSymbolicLink(at: hangboards, withDestinationURL: target)

        XCTAssertThrowsError(try CheckoutSelection.validatedURL(root))
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
        return root
    }

    private func makeInvalidCheckout() throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appending(path: "CheckoutSelectionTests-invalid-\(UUID().uuidString)", directoryHint: .isDirectory)
        temporaryDirectories.append(root)
        try FileManager.default.createDirectory(at: root.appending(path: ".git"), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(
            at: root.appending(path: "Tools/UnrelatedTools/boards"),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: root.appending(path: "Tools/UnrelatedEditor"),
            withIntermediateDirectories: true
        )
        return root
    }
}
