import Foundation

enum BoardSourceBoundaryAudit {
    private static let planMappingOwnerPath = "HangTen/Models/TrainingModels.swift"
    private static let planMappingOwnerDeclaration = "enum LegacyPlanSeedBoardMappings {"
    private static let genericPresentationLoaderPaths: Set<String> = [
        "HangTen/Models/BoardPackageStore.swift"
    ]
    private static let genericCanonicalPresentationLiterals: Set<String> = [
        "assets/primary.png",
        "primary.png",
        "primary"
    ]

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
        let presentationMappingPattern = #"(?:assetPath|photoAssetName)\s*:\s*\""#
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
        let sourceWithoutOwnedPlanMappings = removingOwnedPlanMappings(
            from: source,
            relativePath: relativePath
        )
        let exemptedPresentationLiterals = genericPresentationLoaderPaths.contains(relativePath)
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
        for literal in packageOwnedLiterals
        where !exemptedPresentationLiterals.contains(literal)
            && sourceWithoutOwnedPlanMappings.contains("\"\(literal)\"") {
            findings.append("\(relativePath): package-owned literal \(literal)")
        }
        if sourceWithoutOwnedPlanMappings.range(
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

    private static func removingOwnedPlanMappings(
        from source: String,
        relativePath: String
    ) -> String {
        guard relativePath == planMappingOwnerPath,
              let declarationRange = source.range(of: planMappingOwnerDeclaration) else {
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
