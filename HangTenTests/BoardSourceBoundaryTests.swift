import XCTest
@testable import HangTen

final class BoardSourceBoundaryTests: XCTestCase {
    func testCatalogContainsExactlyApprovedPackageBoards() {
        XCTAssertEqual(
            BoardCatalog.all.map(\.id).sorted(),
            [
                "metolius.wood-grips-compact-ii",
                "trango.rock-prodigy-training-center"
            ]
        )
    }

    func testEveryBuiltInPlanTargetResolvesOnItsPackageBoard() {
        for plan in PlanCatalog.all {
            let board = BoardCatalog.board(for: plan.boardID)

            for step in plan.steps {
                for target in step.targets {
                    XCTAssertFalse(
                        BoardTargetResolver.resolveHoldIDs(for: target, on: board).isEmpty,
                        "Expected target in \(plan.id)/\(step.id) to resolve on \(board.id)."
                    )
                }
            }
        }
    }

    func testLegacyBoardDeliveryArtifactsAreAbsent() {
        let repositoryRoot = repositoryRootURL()
        let forbiddenRelativePaths = [
            "HangTen/Models/GeneratedBoardCatalog.swift",
            "HangTen/Resources/BoardLibrary.json",
            "HangTen/Views/MetoliusCompactIIDesign.swift",
            "HangTen/Views/RockProdigyTrainingCenterDesign.swift",
            "HangTen/Resources/Assets.xcassets/CompactBoard.imageset",
            "HangTen/Resources/Assets.xcassets/CompactBoardIllustration.imageset"
        ]

        for relativePath in forbiddenRelativePaths {
            XCTAssertFalse(
                FileManager.default.fileExists(
                    atPath: repositoryRoot.appendingPathComponent(relativePath).path
                ),
                "Remove redundant board delivery artifact \(relativePath)."
            )
        }

        let projectURL = repositoryRoot
            .appendingPathComponent("HangTen.xcodeproj", isDirectory: true)
            .appendingPathComponent("project.pbxproj")
        let project = try? String(contentsOf: projectURL, encoding: .utf8)
        XCTAssertNotNil(project)
        for artifactName in [
            "GeneratedBoardCatalog.swift",
            "BoardLibrary.json",
            "MetoliusCompactIIDesign.swift",
            "RockProdigyTrainingCenterDesign.swift"
        ] {
            XCTAssertFalse(
                project?.contains(artifactName) == true,
                "Remove the stale Xcode project reference to \(artifactName)."
            )
        }
    }

    func testHandwrittenAppSourcesDoNotContainPackageBoardOrHoldIDs() throws {
        let repositoryRoot = repositoryRootURL()
        let forbiddenIDs = try packageBoardAndHoldIDs(at: repositoryRoot)
        let sourceRoot = repositoryRoot.appendingPathComponent("HangTen", isDirectory: true)
        let sourceURLs = try swiftSourceURLs(below: sourceRoot)

        var findings: [String] = []
        for sourceURL in sourceURLs {
            let source = try String(contentsOf: sourceURL, encoding: .utf8)
            let relativePath = sourceURL.path.replacingOccurrences(
                of: repositoryRoot.path + "/",
                with: ""
            )
            for identifier in forbiddenIDs where source.contains("\"\(identifier)\"") {
                findings.append("\(relativePath): \(identifier)")
            }
        }

        XCTAssertEqual(
            findings.sorted(),
            [],
            "Board IDs and physical hold IDs belong only in approved Hangboards packages."
        )
    }

    private func repositoryRootURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    private func packageBoardAndHoldIDs(at repositoryRoot: URL) throws -> Set<String> {
        let hangboardsRoot = repositoryRoot.appendingPathComponent("Hangboards", isDirectory: true)
        let catalogURL = hangboardsRoot.appendingPathComponent("catalog.json")
        let catalogObject = try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: catalogURL)) as? [String: Any]
        )
        let entries = try XCTUnwrap(catalogObject["boards"] as? [[String: Any]])
        var identifiers = Set<String>()

        for entry in entries where entry["status"] as? String == "approved" {
            let boardID = try XCTUnwrap(entry["id"] as? String)
            let packagePath = try XCTUnwrap(entry["path"] as? String)
            identifiers.insert(boardID)

            let boardURL = hangboardsRoot
                .appendingPathComponent(packagePath, isDirectory: true)
                .appendingPathComponent("board.json")
            let boardObject = try XCTUnwrap(
                JSONSerialization.jsonObject(with: Data(contentsOf: boardURL)) as? [String: Any]
            )
            let holds = try XCTUnwrap(boardObject["holds"] as? [[String: Any]])
            identifiers.formUnion(try holds.map { try XCTUnwrap($0["id"] as? String) })
        }

        return identifiers
    }

    private func swiftSourceURLs(below root: URL) throws -> [URL] {
        let resourceKeys: [URLResourceKey] = [.isRegularFileKey]
        let enumerator = try XCTUnwrap(
            FileManager.default.enumerator(
                at: root,
                includingPropertiesForKeys: resourceKeys,
                options: [.skipsHiddenFiles]
            )
        )
        var urls: [URL] = []

        for case let url as URL in enumerator where url.pathExtension == "swift" {
            if try url.resourceValues(forKeys: Set(resourceKeys)).isRegularFile == true {
                urls.append(url)
            }
        }
        return urls
    }
}
