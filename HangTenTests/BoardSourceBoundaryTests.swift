import XCTest
@testable import HangTen

final class BoardSourceBoundaryTests: XCTestCase {
    func testCatalogContainsExactlyRegisteredPackageBoards() {
        let expectedIDs = [
            "metolius.wood-grips-compact-ii"
        ]

        XCTAssertEqual(
            BoardCatalog.all.map(\.id).sorted(),
            expectedIDs
        )
    }

    func testEveryCatalogBoardUsesItsPackagePrimaryPNG() throws {
        let repositoryRoot = repositoryRootURL()
        let packagePaths = try discoveredPackagePaths(at: repositoryRoot)

        for board in BoardCatalog.all {
            let packagePath = try XCTUnwrap(packagePaths[board.id])
            let imageURL = try XCTUnwrap(
                BoardCatalog.packageStore.presentationImageURL(for: board)
            )
            let expectedAssetsURL = Bundle.main.resourceURL!
                .appendingPathComponent("Hangboards", isDirectory: true)
                .appendingPathComponent(packagePath, isDirectory: true)
                .appendingPathComponent("assets", isDirectory: true)
                .standardizedFileURL

            XCTAssertEqual(imageURL.lastPathComponent, "primary.png")
            XCTAssertTrue(
                imageURL.standardizedFileURL.path.hasPrefix(expectedAssetsURL.path + "/"),
                "Expected \(board.id) presentation image below \(expectedAssetsURL.path), got \(imageURL.path)."
            )
        }
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
            "HangTen/Resources/Assets.xcassets/CompactBoardIllustration.imageset",
            "HangTen/Views/BoardDesignLanguage.swift"
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
            "RockProdigyTrainingCenterDesign.swift",
            "BoardDesignLanguage.swift"
        ] {
            XCTAssertFalse(
                project?.contains(artifactName) == true,
                "Remove the stale Xcode project reference to \(artifactName)."
            )
        }
    }

    func testEveryCatalogPackageEmbedsPhysicalGeometryInBoardJSON() throws {
        let repositoryRoot = repositoryRootURL()
        let packagePaths = try discoveredPackagePaths(at: repositoryRoot)
        let hangboardsURL = repositoryRoot.appendingPathComponent("Hangboards", isDirectory: true)

        XCTAssertFalse(
            FileManager.default.fileExists(
                atPath: hangboardsURL.appendingPathComponent("catalog.json").path
            )
        )

        for board in BoardCatalog.all {
            let packagePath = try XCTUnwrap(packagePaths[board.id])
            let packageURL = hangboardsURL
                .appendingPathComponent(packagePath, isDirectory: true)
            let boardDocument = try XCTUnwrap(
                JSONSerialization.jsonObject(
                    with: Data(contentsOf: packageURL.appendingPathComponent("board.json"))
                ) as? [String: Any]
            )
            let holds = try XCTUnwrap(boardDocument["holds"] as? [[String: Any]])
            let packageEntries = try Set(
                FileManager.default.contentsOfDirectory(atPath: packageURL.path)
            )
            let assetEntries = try Set(
                FileManager.default.contentsOfDirectory(
                    atPath: packageURL.appendingPathComponent("assets").path
                )
            )

            XCTAssertEqual(packageEntries, ["assets", "board.json"])
            XCTAssertEqual(assetEntries, ["primary.png"])
            XCTAssertEqual(boardDocument["schemaVersion"] as? Int, 1)
            XCTAssertEqual(boardDocument["id"] as? String, board.id)
            XCTAssertFalse(holds.isEmpty)
            XCTAssertTrue(holds.allSatisfy { !($0["geometry"] as? [[String: Any]] ?? []).isEmpty })
            XCTAssertTrue(holds.allSatisfy { $0["cueStyle"] == nil })
        }
    }

    func testBoardMapUsesOnePhysicalPathForHighlightingAndHitTesting() throws {
        let repositoryRoot = repositoryRootURL()
        let sourceURL = repositoryRoot
            .appendingPathComponent("HangTen/Views/BoardMapView.swift")
        let source = try String(contentsOf: sourceURL, encoding: .utf8)

        XCTAssertTrue(source.contains("BoardPresentationImage"))
        XCTAssertTrue(source.contains("BoardHoldPathShape(pieces: hold.geometry)"))
        XCTAssertTrue(source.contains(".contentShape(shape)"))
        XCTAssertFalse(source.contains("contentShape(Rectangle())"))
        XCTAssertFalse(source.contains("Canvas("))
        XCTAssertFalse(source.contains("BoardDesign"))
    }

    func testHandwrittenAppSourcesAndResourcesContainNoBoardDeliveryArtifacts() throws {
        let repositoryRoot = repositoryRootURL()
        let packageOwnedLiterals = try packageOwnedLiterals(at: repositoryRoot)
        let genericCanonicalAssetPaths: Set<String> = [
            "assets/primary.png"
        ]
        let sourceURLs = try appSourceAndResourceURLs(at: repositoryRoot)
        let legacyArtifactTokens = [
            "GeneratedBoardCatalog",
            "BoardLibrary.json",
            "MetoliusCompactIIDesign",
            "RockProdigyTrainingCenterDesign",
            "CompactBoard.imageset",
            "CompactBoardIllustration",
            "BoardDesignLanguage"
        ]
        let hardcodedMappingPatterns = [
            #"semanticHolds\s*:\s*\[\s*\""#,
            #"(?:assetPath|photoAssetName)\s*:\s*\""#
        ]
        let boardSpecificGeometryConstructs = [
            "TrainingBoard(",
            "BoardHold(",
            "HoldFrame(",
            "BoardNormalizedPath(commands:"
        ]
        let genericGeometryOwners: Set<String> = [
            "HangTen/Models/BoardPackageStore.swift",
            "HangTen/Models/BoardStorage.swift",
            "HangTen/Models/TrainingModels.swift"
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
            for literal in packageOwnedLiterals
            where !genericCanonicalAssetPaths.contains(literal)
                && source.contains("\"\(literal)\"") {
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

    func testBoundaryAuditIgnoresUntrackedAppScratchFiles() throws {
        let repositoryRoot = repositoryRootURL()
        let scratchRelativePath = "HangTen/BoundaryAuditUntrackedScratch.swift"
        let scratchURL = repositoryRoot.appendingPathComponent(scratchRelativePath)
        try "let artifact = \"GeneratedBoardCatalog\"".write(to: scratchURL, atomically: true, encoding: .utf8)
        defer { try? FileManager.default.removeItem(at: scratchURL) }

        let sourcePaths = try appSourceAndResourceURLs(at: repositoryRoot).map {
            $0.path.replacingOccurrences(of: repositoryRoot.path + "/", with: "")
        }

        XCTAssertTrue(
            sourcePaths.contains("HangTen/HangTenApp.swift"),
            "A tracked handwritten app source should remain a boundary-audit candidate."
        )
        XCTAssertFalse(
            sourcePaths.contains(scratchRelativePath),
            "An untracked scratch file with a prohibited token must not affect the boundary audit."
        )
    }

    private func repositoryRootURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    private func packageOwnedLiterals(at repositoryRoot: URL) throws -> Set<String> {
        let hangboardsRoot = repositoryRoot.appendingPathComponent("Hangboards", isDirectory: true)
        var identifiers = Set<String>()

        for (boardID, packagePath) in try discoveredPackagePaths(at: repositoryRoot) {
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

        }

        return identifiers
    }

    private func discoveredPackagePaths(at repositoryRoot: URL) throws -> [String: String] {
        let hangboardsURL = repositoryRoot.appendingPathComponent("Hangboards", isDirectory: true)
        let children = try FileManager.default.contentsOfDirectory(
            at: hangboardsURL,
            includingPropertiesForKeys: [.isDirectoryKey, .isSymbolicLinkKey]
        )
        var paths: [String: String] = [:]
        for child in children {
            let values = try child.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
            guard values.isDirectory == true, values.isSymbolicLink != true else {
                XCTFail("Hangboards must contain only non-symlinked direct child directories")
                continue
            }
            let boardURL = child.appendingPathComponent("board.json")
            guard FileManager.default.fileExists(atPath: boardURL.path) else { continue }
            let document = try XCTUnwrap(
                JSONSerialization.jsonObject(with: Data(contentsOf: boardURL)) as? [String: Any]
            )
            let boardID = try XCTUnwrap(document["id"] as? String)
            XCTAssertNil(paths[boardID], "Duplicate discovered board ID \(boardID)")
            paths[boardID] = child.lastPathComponent
        }
        return paths
    }

    private func appSourceAndResourceURLs(at repositoryRoot: URL) throws -> [URL] {
        // The test target's manifest build phase keeps this checked-in list equal
        // to `git ls-files`, which the iOS simulator itself cannot invoke.
        return try trackedAppBoundaryPaths(at: repositoryRoot)
            .filter { relativePath in
                exclusionReason(for: relativePath) == nil &&
                    (relativePath.hasPrefix("HangTen/") ||
                        relativePath == "HangTen.xcodeproj/project.pbxproj")
            }
            .map { repositoryRoot.appendingPathComponent($0) }
    }

    private func trackedAppBoundaryPaths(at repositoryRoot: URL) throws -> [String] {
        let manifestURL = repositoryRoot
            .appendingPathComponent("HangTenTests", isDirectory: true)
            .appendingPathComponent("BoardSourceBoundaryTrackedPaths.txt")
        return try String(contentsOf: manifestURL, encoding: .utf8)
            .split(separator: "\n")
            .map(String.init)
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
