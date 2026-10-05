import Foundation

enum BoardSourceBoundaryAudit {
    private static let planRequirementOwnerPath = "HangTen/Models/TrainingModels.swift"
    private static let planRequirementOwnerDeclaration = "enum BundledPlanContactRequirements {"
    private static let genericPresentationVocabularyOwnerPaths: Set<String> = [
        "HangTen/Models/BoardPackageStore.swift",
        "HangTen/Models/TrainingModels.swift"
    ]
    private static let genericCanonicalPresentationLiterals: Set<String> = [
        "assets/primary.png",
        "primary.png",
        "primary"
    ]

    /// The board document of the package at `packageURL` in the checkout: the
    /// checked-in `board.json`, or, for a CAD-backed package (`<slug>.FCStd`,
    /// whose `board.json` is generated at build time and never committed), the
    /// copy the Stage Board Packages build phase generated into the app bundle.
    static func boardDocumentURL(forPackageAt packageURL: URL) -> URL? {
        let checkedInURL = packageURL.appendingPathComponent("board.json")
        if FileManager.default.fileExists(atPath: checkedInURL.path) {
            return checkedInURL
        }
        let slug = packageURL.lastPathComponent
        let authoringSourceURL = packageURL.appendingPathComponent("\(slug).FCStd")
        guard FileManager.default.fileExists(atPath: authoringSourceURL.path),
              let resourceURL = Bundle.main.resourceURL else {
            return nil
        }
        return resourceURL
            .appendingPathComponent("Hangboards", isDirectory: true)
            .appendingPathComponent(slug, isDirectory: true)
            .appendingPathComponent("board.json")
    }

    static func bundledBoardDocumentURLs(at repositoryRoot: URL) throws -> [URL] {
        let hangboardsURL = repositoryRoot.appendingPathComponent("Hangboards", isDirectory: true)
        let packageURLs = try FileManager.default.contentsOfDirectory(
            at: hangboardsURL,
            includingPropertiesForKeys: [.isDirectoryKey, .isSymbolicLinkKey]
        )

        return try packageURLs.compactMap { packageURL in
            let values = try packageURL.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
            guard values.isDirectory == true, values.isSymbolicLink != true else {
                return nil
            }
            return boardDocumentURL(forPackageAt: packageURL)
        }
        .sorted { $0.path < $1.path }
    }

    static func findings(
        relativePath: String,
        source: String,
        packageOwnedLiterals: Set<String>
    ) -> [String] {
        let legacyArtifactTokens = [
            "GeneratedBoardCatalog",
            "BoardLibrary.json",
            "MetoliusCompactIIDesign",
            "RockProdigyTrainingCenterDesign",
            "CompactBoard.imageset",
            "CompactBoardIllustration",
            "BoardDesignLanguage"
        ]
        let semanticMappingPattern = #"semanticHolds\s*:\s*\[\s*\""#
        // A generic empty fixture is not a delivered presentation mapping.
        // Retain the audit for every nonempty source literal.
        let presentationMappingPattern = #"(?:assetPath|photoAssetName)\s*:\s*\"(?!\")"#
        let boardSpecificGeometryConstructs = [
            "BoardRevision(",
            "PhysicalContact(",
            "HoldFrame(",
            "BoardNormalizedPath(commands:"
        ]
        let genericGeometryOwners: Set<String> = [
            "HangTen/Models/BoardPackageStore.swift",
            "HangTen/Models/BoardStorage.swift",
            "HangTen/Models/TrainingModels.swift"
        ]
        var findings: [String] = []
        let sourceWithoutOwnedPlanRequirements = removingLegacyPlateauMigrationIDs(
            from: removingCatalogDefaultBoardID(
                from: removingDisplayModelBoardID(
                    from: removingOwnedDeclaration(
                        from: source,
                        relativePath: relativePath,
                        ownerPath: planRequirementOwnerPath,
                        declaration: planRequirementOwnerDeclaration
                    ),
                    relativePath: relativePath
                ),
                relativePath: relativePath
            ),
            relativePath: relativePath
        )
        let exemptedPresentationLiterals = genericPresentationVocabularyOwnerPaths.contains(relativePath)
            ? genericCanonicalPresentationLiterals
            : []

        for token in legacyArtifactTokens where relativePath.contains(token) {
            findings.append("\(relativePath): legacy artifact path \(token)")
        }
        for literal in packageOwnedLiterals where relativePath.contains(literal) {
            findings.append("\(relativePath): package-owned path literal \(literal)")
        }
        for token in legacyArtifactTokens where source.contains(token) {
            findings.append("\(relativePath): legacy artifact token \(token)")
        }
        // Index all consecutive quote pairs once. Quotes are raw UTF-8 bytes so
        // escaped quotes and quote-adjacent combining marks remain candidates.
        let quotedSegments = Set(sourceWithoutOwnedPlanRequirements.utf8
            .split(separator: 34, omittingEmptySubsequences: false)
            .dropFirst().dropLast()
            .map { String(decoding: $0, as: UTF8.self) })
        for literal in packageOwnedLiterals
        where !exemptedPresentationLiterals.contains(literal)
            && (quotedSegments.contains(literal) || literal.utf8.contains(34))
            // Retain the original search for candidates and quote-bearing
            // literals, including its Unicode/grapheme-boundary semantics.
            && sourceWithoutOwnedPlanRequirements.contains("\"\(literal)\"") {
            findings.append("\(relativePath): package-owned literal \(literal)")
        }
        if sourceWithoutOwnedPlanRequirements.range(
            of: semanticMappingPattern,
            options: .regularExpression
        ) != nil {
            findings.append(
                "\(relativePath): hardcoded mapping matching \(semanticMappingPattern)"
            )
        }
        if source.range(
            of: presentationMappingPattern,
            options: .regularExpression
        ) != nil {
            findings.append(
                "\(relativePath): hardcoded mapping matching \(presentationMappingPattern)"
            )
        }
        if !genericGeometryOwners.contains(relativePath) {
            for construct in boardSpecificGeometryConstructs where source.contains(construct) {
                findings.append("\(relativePath): board geometry construct \(construct)")
            }
        }
        return findings
    }

    /// Only the approved board binding is exempt; hold IDs and asset paths remain audited.
    private static func removingDisplayModelBoardID(
        from source: String,
        relativePath: String
    ) -> String {
        guard relativePath == "HangTen/Views/BoardModelView.swift" else { return source }
        return source.replacingOccurrences(
            of: #"(enum BoardModelIdentity \{\s*)static let boardID = "metolius\.wood-grips-compact-ii""#,
            with: "$1",
            options: .regularExpression
        )
    }

    /// The initial UI selection is an app preference, not a plan target or a
    /// second copy of package content. Only this exact declaration is exempt.
    private static func removingCatalogDefaultBoardID(
        from source: String,
        relativePath: String
    ) -> String {
        guard relativePath == "HangTen/Models/TrainingModels.swift" else { return source }
        return source.replacingOccurrences(
            of: #"(static let defaultBoard: BoardRevision = \{\s*)let boardID = "[^"]+""#,
            with: "$1",
            options: .regularExpression
        )
    }

    /// Persisted pre-native selections need a compatibility binding, not a
    /// second board definition. Exempt only the two exact migration expressions
    /// in their owning methods; every other literal and artifact stays audited.
    private static func removingLegacyPlateauMigrationIDs(
        from source: String,
        relativePath: String
    ) -> String {
        guard relativePath == "HangTen/Models/CustomRoutineStore.swift" else { return source }
        let bindings = [
            (
                declaration: #"private\s+static\s+func\s+normalize\(_ definition: CustomRoutineDefinition\)\s*->\s*CustomRoutineDefinition\s*\{"#,
                expression: #"(if case let \.boardSpecific\(boardID\) = definition\.targetMode,\s*boardID == )"plateau\.lifting-edge"(\s*\{\s*return migratingLegacyPlateauTargets\(in: step\))"#
            ),
            (
                declaration: #"private\s+static\s+func\s+migratingLegacyPlateauRequirement\(\s*_ requirement: ContactRequirement\s*\)\s*->\s*ContactRequirement\s*\{"#,
                expression: #"(return ContactRequirement\(\s*contactID:\s*)"edge-18"(\s*,)"#
            )
        ]
        var auditedSource = source
        for binding in bindings {
            guard let declaration = auditedSource.range(
                of: binding.declaration, options: .regularExpression
            ) else { continue }
            var index = auditedSource.index(before: declaration.upperBound)
            var depth = 0
            var end: String.Index?
            while index < auditedSource.endIndex {
                if auditedSource[index] == "{" { depth += 1 }
                if auditedSource[index] == "}" {
                    depth -= 1
                    if depth == 0 {
                        end = auditedSource.index(after: index)
                        break
                    }
                }
                index = auditedSource.index(after: index)
            }
            guard let end else { continue }
            let methodRange = declaration.lowerBound..<end
            let method = String(auditedSource[methodRange]).replacingOccurrences(
                of: binding.expression, with: "$1$2", options: .regularExpression
            )
            auditedSource.replaceSubrange(methodRange, with: method)
        }
        return auditedSource
    }

    private static func removingOwnedDeclaration(
        from source: String,
        relativePath: String,
        ownerPath: String,
        declaration: String
    ) -> String {
        guard relativePath == ownerPath,
              let declarationRange = source.range(of: declaration) else {
            return source
        }
        let openingBrace = source.index(before: declarationRange.upperBound)
        var index = openingBrace
        var depth = 0
        while index < source.endIndex {
            switch source[index] {
            case "{":
                depth += 1
            case "}":
                depth -= 1
                if depth == 0 {
                    let end = source.index(after: index)
                    var auditedSource = source
                    auditedSource.removeSubrange(declarationRange.lowerBound..<end)
                    return auditedSource
                }
            default:
                break
            }
            index = source.index(after: index)
        }
        return source
    }
}
