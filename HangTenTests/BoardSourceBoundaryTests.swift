import XCTest
@testable import HangTen

final class BoardSourceBoundaryTests: XCTestCase {
    private enum PackageDiscoveryError: Error {
        case invalidRootChild(String)
    }

    func testCatalogContainsExactlyRegisteredPackageBoards() {
        let expectedIDs = [
            "beastmaker-1000",
            "beastmaker-2000",
            "dewoodstok-woodbord",
            "escape-beta-22",
            "evolv-kilter-basic-long",
            "lattice-triple-rung",
            "metolius.wood-grips-compact-ii",
            "trango.rock-prodigy-pivot",
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
        XCTAssertTrue(source.contains(".contentShape(.interaction, shape)"))
        XCTAssertTrue(source.contains(".contentShape(.accessibility, shape)"))
        XCTAssertTrue(source.contains(".accessibilityElement(children: .combine)"))
        XCTAssertFalse(source.contains("contentShape(Rectangle())"))
        XCTAssertFalse(source.contains("Canvas("))
        XCTAssertFalse(source.contains("BoardDesign"))
    }

    func testHandwrittenAppSourcesAndResourcesContainNoBoardDeliveryArtifacts() throws {
        let repositoryRoot = repositoryRootURL()
        let packageOwnedLiterals = try packageOwnedLiterals(at: repositoryRoot)
        let sourceURLs = try appSourceAndResourceURLs(at: repositoryRoot)

        var findings: [String] = []
        for sourceURL in sourceURLs {
            let relativePath = sourceURL.path.replacingOccurrences(
                of: repositoryRoot.path + "/",
                with: ""
            )
            let source = (try? String(contentsOf: sourceURL, encoding: .utf8)) ?? ""
            findings.append(
                contentsOf: BoardSourceBoundaryAudit.findings(
                    relativePath: relativePath,
                    source: source,
                    packageOwnedLiterals: packageOwnedLiterals
                )
            )
        }

        XCTAssertEqual(
            findings.sorted(),
            [],
            "Board metadata, mappings, assets, and concrete geometry belong only in approved Hangboards packages."
        )
    }

    func testBoundaryAuditAllowsPlanMappingsOnlyInDedicatedOwner() {
        let mapping = """
        enum LegacyPlanSeedBoardMappings {
            static let all = [BoardMappingDefinition(
                boardID: "metolius.wood-grips-compact-ii",
                semanticHolds: [
                    "edge-19": SemanticHoldMappingDefinition(
                        holdIDs: ["edge-19-left", "edge-19-right"]
                    )
                ]
            )]
        }
        """
        let packageOwnedLiterals: Set<String> = [
            "metolius.wood-grips-compact-ii",
            "edge-19-left",
            "edge-19-right"
        ]

        XCTAssertEqual(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/TrainingModels.swift",
                source: mapping,
                packageOwnedLiterals: packageOwnedLiterals
            ),
            []
        )
        XCTAssertFalse(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/UnauthorizedMappings.swift",
                source: mapping,
                packageOwnedLiterals: packageOwnedLiterals
            ).isEmpty
        )
        XCTAssertFalse(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/TrainingModels.swift",
                source: mapping + "\n" + mapping.replacingOccurrences(
                    of: "LegacyPlanSeedBoardMappings",
                    with: "UnauthorizedPlanMappings"
                ),
                packageOwnedLiterals: packageOwnedLiterals
            ).isEmpty
        )
        XCTAssertFalse(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/TrainingModels.swift",
                source: #"let image = BoardPresentation(assetPath: "assets/primary.png")"#,
                packageOwnedLiterals: ["assets/primary.png"]
            ).isEmpty
        )
        XCTAssertFalse(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/UnauthorizedGeometry.swift",
                source: "let frame = HoldFrame(x: 0, y: 0, width: 1, height: 1)",
                packageOwnedLiterals: []
            ).isEmpty
        )
    }

    func testBoundaryAuditAllowsCanonicalPresentationVocabularyOnlyInGenericLoader() {
        let canonicalPresentationVocabulary: Set<String> = [
            "assets/primary.png",
            "primary.png",
            "primary"
        ]
        let genericLoaderSource = """
        let assetPath = "assets/primary.png"
        let filename = "primary.png"
        let stem = "primary"
        """

        XCTAssertEqual(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/BoardPackageStore.swift",
                source: genericLoaderSource,
                packageOwnedLiterals: canonicalPresentationVocabulary
            ),
            []
        )
        XCTAssertFalse(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/UnauthorizedLoader.swift",
                source: genericLoaderSource,
                packageOwnedLiterals: canonicalPresentationVocabulary
            ).isEmpty
        )
        XCTAssertFalse(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/BoardPackageStore.swift",
                source: #"let mapping = BoardPresentation(assetPath: "assets/primary.png")"#,
                packageOwnedLiterals: canonicalPresentationVocabulary
            ).isEmpty
        )
        XCTAssertFalse(
            BoardSourceBoundaryAudit.findings(
                relativePath: "HangTen/Models/BoardPackageStore.swift",
                source: #"let packageID = "fixture.package-specific""#,
                packageOwnedLiterals: ["fixture.package-specific"]
            ).isEmpty
        )
    }

    func testPackageDiscoveryAllowsOnlySafeWorkbenchLockOperationalFile() throws {
        let repositoryRoot = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let hangboardsURL = repositoryRoot.appendingPathComponent("Hangboards", isDirectory: true)
        let packageURL = hangboardsURL.appendingPathComponent("fixture-board", isDirectory: true)
        let lockURL = hangboardsURL.appendingPathComponent(".workbench.lock")
        let unexpectedFileURL = hangboardsURL.appendingPathComponent("unexpected.txt")
        let outsideLockURL = repositoryRoot.appendingPathComponent("outside-lock")
        try FileManager.default.createDirectory(at: packageURL, withIntermediateDirectories: true)
        try Data(#"{"id":"fixture.board"}"#.utf8).write(
            to: packageURL.appendingPathComponent("board.json")
        )
        defer { try? FileManager.default.removeItem(at: repositoryRoot) }

        try Data().write(to: lockURL)
        XCTAssertEqual(
            try discoveredPackagePaths(at: repositoryRoot),
            ["fixture.board": "fixture-board"]
        )

        try FileManager.default.removeItem(at: lockURL)
        try Data().write(to: outsideLockURL)
        try FileManager.default.createSymbolicLink(
            at: lockURL,
            withDestinationURL: outsideLockURL
        )
        XCTAssertThrowsError(try discoveredPackagePaths(at: repositoryRoot))

        try FileManager.default.removeItem(at: lockURL)
        try FileManager.default.createDirectory(at: lockURL, withIntermediateDirectories: false)
        XCTAssertThrowsError(try discoveredPackagePaths(at: repositoryRoot))

        try FileManager.default.removeItem(at: lockURL)
        try Data().write(to: unexpectedFileURL)
        XCTAssertThrowsError(try discoveredPackagePaths(at: repositoryRoot))
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
            includingPropertiesForKeys: [
                .isDirectoryKey,
                .isRegularFileKey,
                .isSymbolicLinkKey
            ]
        )
        var paths: [String: String] = [:]
        for child in children {
            let values = try child.resourceValues(forKeys: [
                .isDirectoryKey,
                .isRegularFileKey,
                .isSymbolicLinkKey
            ])
            if child.lastPathComponent == ".workbench.lock" {
                guard values.isRegularFile == true, values.isSymbolicLink != true else {
                    throw PackageDiscoveryError.invalidRootChild(child.lastPathComponent)
                }
                continue
            }
            guard values.isDirectory == true, values.isSymbolicLink != true else {
                throw PackageDiscoveryError.invalidRootChild(child.lastPathComponent)
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
