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

    func testHandwrittenAppSourcesAndResourcesContainNoBoardDeliveryArtifacts() throws {
        let repositoryRoot = repositoryRootURL()
        let packageOwnedLiterals = try approvedPackageOwnedLiterals(at: repositoryRoot)
        let sourceURLs = try appSourceAndResourceURLs(at: repositoryRoot)
        let legacyArtifactTokens = [
            "GeneratedBoardCatalog",
            "BoardLibrary.json",
            "MetoliusCompactIIDesign",
            "RockProdigyTrainingCenterDesign",
            "CompactBoard.imageset",
            "CompactBoardIllustration"
        ]
        let hardcodedMappingPatterns = [
            #"semanticHolds\s*:\s*\[\s*\""#,
            #"(?:assetPath|photoAssetName)\s*:\s*\""#
        ]
        let boardSpecificGeometryConstructs = [
            "TrainingBoard(",
            "BoardHold(",
            "HoldFrame(",
            "BoardDesign(",
            "BoardNormalizedPath(commands:"
        ]
        let genericGeometryOwners: Set<String> = [
            "HangTen/Models/BoardPackageStore.swift",
            "HangTen/Models/BoardStorage.swift",
            "HangTen/Views/BoardDesignLanguage.swift"
        ]

        var findings: [String] = []
        for sourceURL in sourceURLs {
            let relativePath = sourceURL.path.replacingOccurrences(
                of: repositoryRoot.path + "/",
                with: ""
            )
            for token in legacyArtifactTokens where relativePath.contains(token) {
                findings.append("\(relativePath): legacy artifact path \(token)")
            }
            for literal in packageOwnedLiterals where relativePath.contains(literal) {
                findings.append("\(relativePath): package-owned path literal \(literal)")
            }

            guard let source = try? String(contentsOf: sourceURL, encoding: .utf8) else {
                continue
            }
            for token in legacyArtifactTokens where source.contains(token) {
                findings.append("\(relativePath): legacy artifact token \(token)")
            }
            for literal in packageOwnedLiterals where source.contains("\"\(literal)\"") {
                findings.append("\(relativePath): package-owned literal \(literal)")
            }
            for pattern in hardcodedMappingPatterns where source.range(
                of: pattern,
                options: .regularExpression
            ) != nil {
                findings.append("\(relativePath): hardcoded mapping matching \(pattern)")
            }
            if !genericGeometryOwners.contains(relativePath) {
                for construct in boardSpecificGeometryConstructs where source.contains(construct) {
                    findings.append("\(relativePath): board geometry construct \(construct)")
                }
            }
        }

        XCTAssertEqual(
            findings.sorted(),
            [],
            "Board metadata, mappings, assets, and concrete geometry belong only in approved Hangboards packages."
        )
    }

    private func repositoryRootURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    private func approvedPackageOwnedLiterals(at repositoryRoot: URL) throws -> Set<String> {
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

            let packageURL = hangboardsRoot.appendingPathComponent(packagePath, isDirectory: true)
            let boardURL = packageURL.appendingPathComponent("board.json")
            let boardObject = try XCTUnwrap(
                JSONSerialization.jsonObject(with: Data(contentsOf: boardURL)) as? [String: Any]
            )
            let holds = try XCTUnwrap(boardObject["holds"] as? [[String: Any]])
            identifiers.formUnion(try holds.map { try XCTUnwrap($0["id"] as? String) })

            if let presentation = boardObject["presentation"] as? [String: Any],
               let assetPath = presentation["assetPath"] as? String {
                let assetURL = URL(fileURLWithPath: assetPath)
                identifiers.insert(assetPath)
                identifiers.insert(assetURL.lastPathComponent)
                identifiers.insert(assetURL.deletingPathExtension().lastPathComponent)
            }

            let artworkURL = packageURL.appendingPathComponent("artwork.json")
            let artworkObject = try JSONSerialization.jsonObject(
                with: Data(contentsOf: artworkURL)
            )
            collectArtifactIdentifiers(from: artworkObject, into: &identifiers)
        }

        return identifiers
    }

    private func collectArtifactIdentifiers(from value: Any, into identifiers: inout Set<String>) {
        if let dictionary = value as? [String: Any] {
            for key in ["id", "holdID"] {
                if let identifier = dictionary[key] as? String {
                    identifiers.insert(identifier)
                }
            }
            for child in dictionary.values {
                collectArtifactIdentifiers(from: child, into: &identifiers)
            }
        } else if let array = value as? [Any] {
            for child in array {
                collectArtifactIdentifiers(from: child, into: &identifiers)
            }
        }
    }

    private func appSourceAndResourceURLs(at repositoryRoot: URL) throws -> [URL] {
        let resourceKeys: [URLResourceKey] = [.isDirectoryKey, .isRegularFileKey]
        let enumerator = try XCTUnwrap(
            FileManager.default.enumerator(
                at: repositoryRoot,
                includingPropertiesForKeys: resourceKeys,
                options: [.skipsHiddenFiles]
            )
        )
        var urls: [URL] = []

        while let url = enumerator.nextObject() as? URL {
            let relativePath = url.path.replacingOccurrences(
                of: repositoryRoot.path + "/",
                with: ""
            )
            let values = try url.resourceValues(forKeys: Set(resourceKeys))

            if exclusionReason(for: relativePath) != nil {
                if values.isDirectory == true {
                    enumerator.skipDescendants()
                }
                continue
            }

            let isAppBoundaryPath = relativePath.hasPrefix("HangTen/") ||
                relativePath == "HangTen.xcodeproj/project.pbxproj"
            if isAppBoundaryPath, values.isRegularFile == true {
                urls.append(url)
            }
        }
        return urls
    }

    private func exclusionReason(for relativePath: String) -> String? {
        // Canonical package data is the authority this boundary protects.
        if relativePath == "Hangboards" || relativePath.hasPrefix("Hangboards/") {
            return "approved Hangboards package authority"
        }
        // Tests intentionally contain divergent fixtures and package literals.
        if relativePath == "HangTenTests" || relativePath.hasPrefix("HangTenTests/") {
            return "test fixtures"
        }
        // The plan export is generated and runtime-replaces its legacy mappings.
        if relativePath == "HangTen/Resources/PlanLibrary.json" {
            return "generated canonical plan resource"
        }
        // Workspace products and indexes are not checked-in handwritten app inputs.
        for prefix in [".context/", ".codegraph/", "build/", "DerivedData/"]
            where relativePath.hasPrefix(prefix) {
            return "generated or built workspace resource"
        }
        // Historical design/audit prose may name artifacts without delivering them.
        for prefix in ["docs/", ".superpowers/"] where relativePath.hasPrefix(prefix) {
            return "historical documentation"
        }
        return nil
    }
}
