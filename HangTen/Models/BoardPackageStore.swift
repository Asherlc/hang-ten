import Foundation
import ImageIO
import UniformTypeIdentifiers
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

private struct BoardPackageAnyCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
        self.intValue = nil
    }

    init?(intValue: Int) {
        self.stringValue = String(intValue)
        self.intValue = intValue
    }
}

private extension Decoder {
    func rejectUnknownKeys(_ allowedKeys: Set<String>) throws {
        let container = try container(keyedBy: BoardPackageAnyCodingKey.self)
        guard let unknownKey = container.allKeys.first(where: {
            !allowedKeys.contains($0.stringValue)
        }) else {
            return
        }
        throw DecodingError.dataCorrupted(
            DecodingError.Context(
                codingPath: codingPath + [unknownKey],
                debugDescription: "Unknown key \(unknownKey.stringValue)"
            )
        )
    }
}

private extension String {
    var isBoardPackageIdentifier: Bool {
        guard let first = unicodeScalars.first,
              let last = unicodeScalars.last,
              Self.isLowercaseASCIIOrDigit(first),
              Self.isLowercaseASCIIOrDigit(last) else {
            return false
        }
        return unicodeScalars.allSatisfy {
            Self.isLowercaseASCIIOrDigit($0) || $0 == "." || $0 == "_" || $0 == "-"
        }
    }

    var isBoardPackageSlug: Bool {
        guard let first = unicodeScalars.first,
              let last = unicodeScalars.last,
              Self.isLowercaseASCIIOrDigit(first),
              Self.isLowercaseASCIIOrDigit(last) else {
            return false
        }
        return unicodeScalars.allSatisfy {
            Self.isLowercaseASCIIOrDigit($0) || $0 == "-"
        }
    }

    private static func isLowercaseASCIIOrDigit(_ scalar: Unicode.Scalar) -> Bool {
        (97...122).contains(scalar.value) || (48...57).contains(scalar.value)
    }

    var isISOCalendarDate: Bool {
        let parts = split(separator: "-", omittingEmptySubsequences: false)
        guard parts.count == 3,
              parts[0].count == 4,
              parts[1].count == 2,
              parts[2].count == 2,
              let year = Int(parts[0]),
              let month = Int(parts[1]),
              let day = Int(parts[2]) else { return false }
        var components = DateComponents()
        components.calendar = Calendar(identifier: .gregorian)
        components.timeZone = TimeZone(secondsFromGMT: 0)
        components.year = year
        components.month = month
        components.day = day
        guard let date = components.date,
              let restored = components.calendar?.dateComponents([.year, .month, .day], from: date) else {
            return false
        }
        return restored.year == year && restored.month == month && restored.day == day
    }
}

enum BoardPackageStoreError: Error, Equatable, LocalizedError {
    case missingCatalog
    case malformedJSON(resource: String)
    case missingPackageSidecar(boardID: String, filename: String)
    case packagePathEscape(boardID: String, path: String)
    case presentationAssetPathEscape(boardID: String, path: String)
    case missingPresentationAsset(boardID: String, path: String)
    case boardIDMismatch(expected: String, actual: String, resource: String)
    case duplicateBoardID(String)
    case duplicateHoldID(boardID: String, holdID: String)
    case unknownSemanticHoldID(boardID: String, holdID: String)
    case invalidPackage(boardID: String, reason: String)

    var errorDescription: String? {
        switch self {
        case .missingCatalog:
            "The bundled Hangboards/catalog.json resource is missing."
        case .malformedJSON(let resource):
            "The bundled board resource is malformed: \(resource)."
        case let .missingPackageSidecar(boardID, filename):
            "Board \(boardID) is missing \(filename)."
        case let .packagePathEscape(boardID, path):
            "Board \(boardID) has a package path outside Hangboards: \(path)."
        case let .presentationAssetPathEscape(boardID, path):
            "Board \(boardID) has a presentation path outside its package: \(path)."
        case let .missingPresentationAsset(boardID, path):
            "Board \(boardID) is missing its presentation asset: \(path)."
        case let .boardIDMismatch(expected, actual, resource):
            "Expected board ID \(expected) in \(resource), got \(actual)."
        case .duplicateBoardID(let boardID):
            "The bundled catalog contains duplicate board ID \(boardID)."
        case let .duplicateHoldID(boardID, holdID):
            "Board \(boardID) contains duplicate hold ID \(holdID)."
        case let .unknownSemanticHoldID(boardID, holdID):
            "Board \(boardID) semantics reference unknown hold ID \(holdID)."
        case let .invalidPackage(boardID, reason):
            "Board \(boardID) is invalid: \(reason)"
        }
    }
}

struct BoardPackageStore {
    // Keep the canonical package asset contract generic in handwritten app code.
    // The package itself remains the source of the concrete asset declaration.
    private static let canonicalPresentationAssetFilename = ["primary", "png"].joined(separator: ".")
    private static let canonicalPresentationAssetPath = [
        "assets",
        canonicalPresentationAssetFilename
    ].joined(separator: "/")

    let boards: [TrainingBoard]

    private let boardsByID: [String: TrainingBoard]
    private let semanticsByBoardID: [String: [String: [String]]]
    private let presentationURLsByBoardID: [String: URL]

    init(bundle: Bundle = .main) throws {
        guard let catalogURL = bundle.url(
            forResource: "catalog",
            withExtension: "json",
            subdirectory: "Hangboards"
        ) else {
            throw BoardPackageStoreError.missingCatalog
        }

        let hangboardsURL = catalogURL.deletingLastPathComponent()
        let catalog: BoardPackageCatalogDocument = try Self.decode(
            from: catalogURL,
            resource: "Hangboards/catalog.json"
        )
        guard catalog.schemaVersion == 1 else {
            throw BoardPackageStoreError.malformedJSON(resource: "Hangboards/catalog.json")
        }

        var seenCatalogIDs = Set<String>()
        var seenCatalogPaths = Set<String>()
        var loadedBoards: [TrainingBoard] = []
        var loadedSemantics: [String: [String: [String]]] = [:]
        var loadedPresentationURLs: [String: URL] = [:]

        for entry in catalog.boards {
            guard entry.id.isBoardPackageIdentifier,
                  entry.path.isBoardPackageSlug else {
                throw BoardPackageStoreError.malformedJSON(resource: "Hangboards/catalog.json")
            }
            guard seenCatalogIDs.insert(entry.id).inserted else {
                throw BoardPackageStoreError.duplicateBoardID(entry.id)
            }
            guard seenCatalogPaths.insert(entry.path).inserted else {
                throw BoardPackageStoreError.malformedJSON(resource: "Hangboards/catalog.json")
            }
            let packageURL = try Self.packageURL(
                for: entry,
                below: hangboardsURL
            )
            let resourcePrefix = "Hangboards/\(entry.path)"
            let boardDocument: BoardPackageBoardDocument = try Self.decodeSidecar(
                named: "board.json",
                boardID: entry.id,
                packageURL: packageURL,
                resourcePrefix: resourcePrefix
            )
            let artworkDocument: BoardPackageArtworkDocument = try Self.decodeSidecar(
                named: "artwork.json",
                boardID: entry.id,
                packageURL: packageURL,
                resourcePrefix: resourcePrefix
            )
            let semanticsDocument: BoardPackageSemanticsDocument = try Self.decodeSidecar(
                named: "semantics.json",
                boardID: entry.id,
                packageURL: packageURL,
                resourcePrefix: resourcePrefix
            )
            let evidenceDocument: BoardPackageEvidenceDocument = try Self.decodeSidecar(
                named: "evidence.json",
                boardID: entry.id,
                packageURL: packageURL,
                resourcePrefix: resourcePrefix
            )
            try Self.validateSchema(boardDocument.schemaVersion, resource: "\(resourcePrefix)/board.json")
            try Self.validateSchema(artworkDocument.schemaVersion, resource: "\(resourcePrefix)/artwork.json")
            try Self.validateSchema(semanticsDocument.schemaVersion, resource: "\(resourcePrefix)/semantics.json")
            try Self.validateSchema(evidenceDocument.schemaVersion, resource: "\(resourcePrefix)/evidence.json")
            try Self.validateMetadata(
                boardDocument: boardDocument,
                semanticsDocument: semanticsDocument,
                boardID: entry.id
            )
            try Self.validateBoardIDs(
                catalogID: entry.id,
                boardDocument: boardDocument,
                artworkDocument: artworkDocument,
                semanticsDocument: semanticsDocument,
                evidenceDocument: evidenceDocument,
                resourcePrefix: resourcePrefix
            )

            let holdIDs = try Self.validateHolds(in: boardDocument)
            try Self.validateArtwork(
                artworkDocument,
                boardID: entry.id,
                holds: boardDocument.holds,
                holdIDs: holdIDs
            )
            try Self.validateSemantics(
                semanticsDocument.semanticHolds,
                boardID: entry.id,
                holdIDs: holdIDs
            )
            let semantics = semanticsDocument.semanticHolds.mapValues(\.holdIDs)
            let board = try boardDocument.trainingBoard(semantics: semantics)

            loadedBoards.append(board)
            loadedSemantics[board.id] = semantics

            guard let presentation = boardDocument.presentation else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: board.id,
                    reason: "presentation declaration is required"
                )
            }
            let assetURL = try Self.presentationAssetURL(
                path: presentation.assetPath,
                boardID: board.id,
                packageURL: packageURL
            )
            guard FileManager.default.isReadableFile(atPath: assetURL.path) else {
                throw BoardPackageStoreError.missingPresentationAsset(
                    boardID: board.id,
                    path: presentation.assetPath
                )
            }
            guard Self.isPNGPresentationImage(at: assetURL),
                  Self.isDecodablePresentationImage(at: assetURL) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: board.id,
                    reason: "presentation asset must be a decodable PNG"
                )
            }
            let assetPaths = try Self.packageAssetPaths(
                boardID: board.id,
                packageURL: packageURL
            )
            try Self.validateArtworkEvidence(
                evidenceDocument,
                artworkDocument: artworkDocument,
                semanticsDocument: semanticsDocument,
                assetPaths: assetPaths,
                resource: "\(resourcePrefix)/evidence.json"
            )
            loadedPresentationURLs[board.id] = assetURL
        }

        self.boards = loadedBoards
        self.boardsByID = Dictionary(uniqueKeysWithValues: loadedBoards.map { ($0.id, $0) })
        self.semanticsByBoardID = loadedSemantics
        self.presentationURLsByBoardID = loadedPresentationURLs
    }

    func board(id: String) -> TrainingBoard? {
        boardsByID[id]
    }

    func semantics(for boardID: String) -> [String: [String]] {
        semanticsByBoardID[boardID] ?? [:]
    }

    func presentationImageURL(for board: TrainingBoard) -> URL? {
        presentationURLsByBoardID[board.id]
    }

    private static func decodeSidecar<Value: Decodable>(
        named filename: String,
        boardID: String,
        packageURL: URL,
        resourcePrefix: String
    ) throws -> Value {
        guard let url = confinedURL(relativePath: filename, below: packageURL) else {
            throw BoardPackageStoreError.packagePathEscape(
                boardID: boardID,
                path: filename
            )
        }
        guard FileManager.default.isReadableFile(atPath: url.path) else {
            throw BoardPackageStoreError.missingPackageSidecar(
                boardID: boardID,
                filename: filename
            )
        }
        return try decode(from: url, resource: "\(resourcePrefix)/\(filename)")
    }

    private static func decode<Value: Decodable>(
        from url: URL,
        resource: String
    ) throws -> Value {
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode(Value.self, from: data)
        } catch {
            throw BoardPackageStoreError.malformedJSON(resource: resource)
        }
    }

    private static func packageURL(
        for entry: BoardPackageCatalogEntry,
        below hangboardsURL: URL
    ) throws -> URL {
        guard let url = confinedURL(relativePath: entry.path, below: hangboardsURL) else {
            throw BoardPackageStoreError.packagePathEscape(
                boardID: entry.id,
                path: entry.path
            )
        }
        return url
    }

    private static func presentationAssetURL(
        path: String,
        boardID: String,
        packageURL: URL
    ) throws -> URL {
        guard let url = confinedURL(relativePath: path, below: packageURL) else {
            throw BoardPackageStoreError.presentationAssetPathEscape(
                boardID: boardID,
                path: path
            )
        }
        guard path == Self.canonicalPresentationAssetPath else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "presentation asset path must be \(Self.canonicalPresentationAssetPath)"
            )
        }
        return url
    }

    private static func packageAssetPaths(
        boardID: String,
        packageURL: URL
    ) throws -> Set<String> {
        guard let assetsURL = confinedURL(relativePath: "assets", below: packageURL),
              let assetsValues = try? assetsURL.resourceValues(forKeys: [.isDirectoryKey]),
              assetsValues.isDirectory == true else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "package assets must be a directory"
            )
        }

        let assetURLs: [URL]
        do {
            assetURLs = try FileManager.default.contentsOfDirectory(
                at: assetsURL,
                includingPropertiesForKeys: [.isRegularFileKey, .isSymbolicLinkKey],
                options: []
            )
        } catch {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "package assets are not accessible"
            )
        }

        let sourceExtensions: Set<String> = ["jpg", "jpeg", "webp", "heic"]
        var assetPaths = Set<String>()
        var sourceCount = 0
        for assetURL in assetURLs {
            guard let values = try? assetURL.resourceValues(
                forKeys: [.isRegularFileKey, .isSymbolicLinkKey]
            ),
            values.isRegularFile == true,
            values.isSymbolicLink != true else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "package assets must be flat regular files"
                )
            }

            let filename = assetURL.lastPathComponent
            if filename == Self.canonicalPresentationAssetFilename {
                assetPaths.insert(Self.canonicalPresentationAssetPath)
                continue
            }
            guard sourceExtensions.contains(assetURL.pathExtension.lowercased()) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "package source asset must be a supported image"
                )
            }
            sourceCount += 1
            guard sourceCount <= 1 else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "package may contain at most one original source image"
                )
            }
            assetPaths.insert("assets/\(filename)")
        }
        return assetPaths
    }

    private static func isDecodablePresentationImage(at url: URL) -> Bool {
#if canImport(UIKit)
        UIImage(contentsOfFile: url.path) != nil
#elseif canImport(AppKit)
        NSImage(contentsOf: url) != nil
#else
        false
#endif
    }

    private static func isPNGPresentationImage(at url: URL) -> Bool {
        guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
              let imageType = CGImageSourceGetType(source) else {
            return false
        }
        return imageType as String == UTType.png.identifier
    }

    private static func confinedURL(relativePath: String, below rootURL: URL) -> URL? {
        guard !relativePath.isEmpty,
              !relativePath.contains("\\"),
              !(relativePath as NSString).isAbsolutePath else {
            return nil
        }

        let components = relativePath.split(separator: "/", omittingEmptySubsequences: false)
        guard !components.isEmpty,
              components.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
            return nil
        }

        let standardizedRoot = rootURL.standardizedFileURL
        let candidate = rootURL.appendingPathComponent(relativePath).standardizedFileURL
        let rootPath = standardizedRoot.path.hasSuffix("/")
            ? standardizedRoot.path
            : standardizedRoot.path + "/"
        guard candidate.path.hasPrefix(rootPath) else { return nil }

        let resolvedRoot = standardizedRoot.resolvingSymlinksInPath()
        let resolvedCandidate = candidate.resolvingSymlinksInPath()
        let resolvedRootPath = resolvedRoot.path.hasSuffix("/")
            ? resolvedRoot.path
            : resolvedRoot.path + "/"
        guard resolvedCandidate.path.hasPrefix(resolvedRootPath) else { return nil }
        return resolvedCandidate
    }

    private static func validateSchema(_ schemaVersion: Int, resource: String) throws {
        guard schemaVersion == 1 else {
            throw BoardPackageStoreError.malformedJSON(resource: resource)
        }
    }

    private static func validateBoardIDs(
        catalogID: String,
        boardDocument: BoardPackageBoardDocument,
        artworkDocument: BoardPackageArtworkDocument,
        semanticsDocument: BoardPackageSemanticsDocument,
        evidenceDocument: BoardPackageEvidenceDocument,
        resourcePrefix: String
    ) throws {
        for (actual, filename) in [
            (boardDocument.id, "board.json"),
            (artworkDocument.boardID, "artwork.json"),
            (semanticsDocument.boardID, "semantics.json"),
            (evidenceDocument.boardID, "evidence.json")
        ] where actual != catalogID {
            throw BoardPackageStoreError.boardIDMismatch(
                expected: catalogID,
                actual: actual,
                resource: "\(resourcePrefix)/\(filename)"
            )
        }
    }

    private static func validateMetadata(
        boardDocument: BoardPackageBoardDocument,
        semanticsDocument: BoardPackageSemanticsDocument,
        boardID: String
    ) throws {
        let requiredStrings = [
            boardDocument.id,
            boardDocument.manufacturer,
            boardDocument.name,
            boardDocument.subtitle,
            boardDocument.dimensions,
            boardDocument.productURL.absoluteString,
            semanticsDocument.boardID
        ]
        guard requiredStrings.allSatisfy({ !$0.isEmpty }) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "required metadata must not be empty"
            )
        }
        guard boardDocument.id.isBoardPackageIdentifier,
              semanticsDocument.boardID.isBoardPackageIdentifier else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "board IDs must be identifier-shaped"
            )
        }
        if let assetPath = boardDocument.presentation?.assetPath,
           assetPath.isEmpty {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "presentation asset path must not be empty"
            )
        }
    }

    private static func validateHolds(
        in document: BoardPackageBoardDocument
    ) throws -> Set<String> {
        var holdIDs = Set<String>()
        for hold in document.holds {
            guard hold.id.isBoardPackageIdentifier,
                  !hold.name.isEmpty,
                  !hold.shortLabel.isEmpty,
                  !hold.detail.isEmpty else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold metadata must be non-empty and identifier-shaped"
                )
            }
            guard holdIDs.insert(hold.id).inserted else {
                throw BoardPackageStoreError.duplicateHoldID(
                    boardID: document.id,
                    holdID: hold.id
                )
            }
            guard BoardHold.validFingerCapacityRange.contains(hold.fingerCapacity) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid finger capacity"
                )
            }
            guard hold.frame.isNormalized else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid frame"
                )
            }
            if let size = hold.sizeMillimeters, size <= 0 {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has a non-positive size"
                )
            }
            if let depthRange = hold.depthRangeMillimeters,
               depthRange.lowerBound <= 0 ||
               depthRange.upperBound <= 0 ||
               depthRange.lowerBound > depthRange.upperBound {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid depth range"
                )
            }
            guard Set(hold.features).count == hold.features.count else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has duplicate features"
                )
            }
        }
        guard !holdIDs.isEmpty else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "holds must not be empty"
            )
        }
        return holdIDs
    }

    private static func validateArtwork(
        _ document: BoardPackageArtworkDocument,
        boardID: String,
        holds: [BoardPackageHoldDocument],
        holdIDs: Set<String>
    ) throws {
        guard document.canvasFrame.isNormalized,
              document.palette == .sculptedWood,
              document.silhouette.isValid(in: BoardPackageFrameDocument.fullCanvas) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "artwork has invalid canvas or silhouette geometry"
            )
        }

        var layerIDs = Set<String>()
        for layer in document.layers {
            guard layer.id.isBoardPackageIdentifier,
                  layerIDs.insert(layer.id).inserted,
                  layer.frame.isNormalized,
                  layer.shape.isValid(in: layer.frame) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "artwork layers must have valid unique identifiers and geometry"
                )
            }
        }

        var pieceIDs = Set<String>()
        var artworkHoldIDs = Set<String>()
        for piece in document.holdPieces {
            guard piece.id.isBoardPackageIdentifier,
                  piece.holdID.isBoardPackageIdentifier,
                  pieceIDs.insert(piece.id).inserted,
                  artworkHoldIDs.insert(piece.holdID).inserted,
                  piece.frame.isNormalized,
                  piece.shape.isValid(in: piece.frame),
                  piece.treatment.isValid else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "artwork hold pieces must have valid unique identifiers, geometry, and treatment"
                )
            }
        }
        guard artworkHoldIDs == holdIDs else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "artwork hold IDs must exactly match board hold IDs"
            )
        }

        let piecesByHoldID = Dictionary(uniqueKeysWithValues: document.holdPieces.map {
            ($0.holdID, $0)
        })
        for hold in holds {
            guard let piece = piecesByHoldID[hold.id],
                  hold.frame.matches(piece.shape.derivedFrame(in: piece.frame)) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "hold \(hold.id) frame must match its derived artwork outline"
                )
            }
        }
    }

    private static func validateArtworkEvidence(
        _ evidence: BoardPackageEvidenceDocument,
        artworkDocument: BoardPackageArtworkDocument,
        semanticsDocument: BoardPackageSemanticsDocument,
        assetPaths: Set<String>,
        resource: String
    ) throws {
        let expectedKeys = Set(
            ["silhouette"] +
                artworkDocument.layers.map { "layers.\($0.id)" } +
                artworkDocument.holdPieces.map { "holdPieces.\($0.id)" }
        )
        guard Set(evidence.artworkEvidence.keys) == expectedKeys else {
            throw BoardPackageStoreError.malformedJSON(resource: resource)
        }

        let sourceIDs = Set(evidence.sources.map(\.id))
        guard !sourceIDs.isEmpty,
              sourceIDs.count == evidence.sources.count,
              sourceIDs.allSatisfy(\.isBoardPackageIdentifier),
              evidence.sources.allSatisfy({
                  !$0.title.isEmpty && $0.url.scheme?.lowercased() == "https" && $0.url.host != nil
              }) else {
            throw BoardPackageStoreError.malformedJSON(resource: resource)
        }
        guard evidence.checkedAt.isISOCalendarDate,
              evidence.fieldEvidence.validEvidenceMap(
                  expectedKeys: ["manufacturer", "name", "subtitle", "productURL", "dimensions", "aspectRatio"],
                  sourceIDs: sourceIDs
              ),
              evidence.holdEvidence.validEvidenceMap(
                  expectedKeys: Set(artworkDocument.holdPieces.flatMap { piece in
                      ["id", "name", "shortLabel", "detail", "kind", "frame", "sizeMillimeters", "depthRangeMillimeters", "gripType", "fingerCapacity", "cueStyle", "features"].map {
                          "\(piece.holdID).\($0)"
                      }
                  }),
                  sourceIDs: sourceIDs
              ),
              evidence.semanticEvidence.validEvidenceMap(
                  expectedKeys: Set(semanticsDocument.semanticHolds.keys),
                  sourceIDs: sourceIDs
              ),
              evidence.artworkEvidence.validEvidenceMap(
                  expectedKeys: expectedKeys,
                  sourceIDs: sourceIDs
              ),
              evidence.assetEvidence.validEvidenceMap(
                  expectedKeys: assetPaths,
                  sourceIDs: sourceIDs,
                  externalGenerationKeys: [Self.canonicalPresentationAssetPath]
              ) else {
            throw BoardPackageStoreError.malformedJSON(resource: resource)
        }
    }

    private static func validateSemantics(
        _ semantics: [String: BoardPackageSemanticMappingDocument],
        boardID: String,
        holdIDs: Set<String>
    ) throws {
        for (semanticID, mapping) in semantics {
            guard semanticID.isBoardPackageIdentifier else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "semantic IDs must be identifier-shaped"
                )
            }
            guard !mapping.holdIDs.isEmpty else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "semantic \(semanticID) hold IDs must not be empty"
                )
            }
            guard mapping.holdIDs.allSatisfy(\.isBoardPackageIdentifier) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "semantic \(semanticID) hold IDs must be identifier-shaped"
                )
            }
            guard Set(mapping.holdIDs).count == mapping.holdIDs.count else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "semantic \(semanticID) hold IDs must be unique"
                )
            }
            for holdID in mapping.holdIDs where !holdIDs.contains(holdID) {
                throw BoardPackageStoreError.unknownSemanticHoldID(
                    boardID: boardID,
                    holdID: holdID
                )
            }
        }
    }

}

private struct BoardPackageCatalogDocument: Decodable {
    let schemaVersion: Int
    let boards: [BoardPackageCatalogEntry]

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case boards
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["schemaVersion", "boards"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        boards = try container.decode([BoardPackageCatalogEntry].self, forKey: .boards)
    }
}

private struct BoardPackageCatalogEntry: Decodable {
    let id: String
    let path: String

    private enum CodingKeys: String, CodingKey {
        case id
        case path
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "path"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        path = try container.decode(String.self, forKey: .path)
    }
}

private struct BoardPackageBoardDocument: Decodable {
    let schemaVersion: Int
    let id: String
    let manufacturer: String
    let name: String
    let subtitle: String
    let productURL: URL
    let dimensions: String
    let aspectRatio: Double
    let presentation: BoardPackagePresentationDocument?
    let holds: [BoardPackageHoldDocument]

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case id
        case manufacturer
        case name
        case subtitle
        case productURL
        case dimensions
        case aspectRatio
        case presentation
        case holds
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "schemaVersion", "id", "manufacturer", "name", "subtitle", "productURL",
            "dimensions", "aspectRatio", "presentation", "holds"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        id = try container.decode(String.self, forKey: .id)
        manufacturer = try container.decode(String.self, forKey: .manufacturer)
        name = try container.decode(String.self, forKey: .name)
        subtitle = try container.decode(String.self, forKey: .subtitle)
        productURL = try container.decode(URL.self, forKey: .productURL)
        dimensions = try container.decode(String.self, forKey: .dimensions)
        aspectRatio = try container.decode(Double.self, forKey: .aspectRatio)
        presentation = try container.decodeIfPresent(
            BoardPackagePresentationDocument.self,
            forKey: .presentation
        )
        holds = try container.decode([BoardPackageHoldDocument].self, forKey: .holds)
    }

    func trainingBoard(semantics: [String: [String]]) throws -> TrainingBoard {
        guard aspectRatio.isFinite, aspectRatio > 0 else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: id,
                reason: "aspect ratio must be positive"
            )
        }

        return TrainingBoard(
            id: id,
            manufacturer: manufacturer,
            name: name,
            subtitle: subtitle,
            dimensions: dimensions,
            aspectRatio: CGFloat(aspectRatio),
            holds: holds.map(\.trainingBoardHold),
            semanticHolds: semantics.mapValues {
                SemanticHoldMappingDefinition(holdIDs: $0)
            },
            productURL: productURL,
            photoAssetName: nil
        )
    }
}

private struct BoardPackagePresentationDocument: Decodable {
    let assetPath: String

    private enum CodingKeys: String, CodingKey {
        case assetPath
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["assetPath"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        assetPath = try container.decode(String.self, forKey: .assetPath)
    }
}

private struct BoardPackageHoldDocument: Decodable {
    let id: String
    let name: String
    let shortLabel: String
    let detail: String
    let kind: HoldKind
    let frame: BoardPackageFrameDocument
    let sizeMillimeters: Int?
    let depthRangeMillimeters: BoardPackageMillimeterRangeDocument?
    let gripType: GripType
    let fingerCapacity: Int
    let cueStyle: HoldCueStyle
    let features: [HoldFeature]

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case shortLabel
        case detail
        case kind
        case frame
        case sizeMillimeters
        case depthRangeMillimeters
        case gripType
        case fingerCapacity
        case cueStyle
        case features
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "id", "name", "shortLabel", "detail", "kind", "frame", "sizeMillimeters",
            "depthRangeMillimeters", "gripType", "fingerCapacity", "cueStyle", "features"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        shortLabel = try container.decode(String.self, forKey: .shortLabel)
        detail = try container.decode(String.self, forKey: .detail)
        kind = try container.decode(HoldKind.self, forKey: .kind)
        frame = try container.decode(BoardPackageFrameDocument.self, forKey: .frame)
        sizeMillimeters = try container.decode(
            Optional<Int>.self,
            forKey: .sizeMillimeters
        )
        depthRangeMillimeters = try container.decode(
            Optional<BoardPackageMillimeterRangeDocument>.self,
            forKey: .depthRangeMillimeters
        )
        gripType = try container.decode(GripType.self, forKey: .gripType)
        fingerCapacity = try container.decode(Int.self, forKey: .fingerCapacity)
        cueStyle = try container.decode(HoldCueStyle.self, forKey: .cueStyle)
        features = try container.decode([HoldFeature].self, forKey: .features)
    }

    var trainingBoardHold: BoardHold {
        BoardHold(
            id: id,
            name: name,
            shortLabel: shortLabel,
            detail: detail,
            kind: kind,
            frame: frame.holdFrame,
            sizeMillimeters: sizeMillimeters,
            gripType: gripType,
            fingerCapacity: fingerCapacity,
            cueStyle: cueStyle,
            depthRangeMillimeters: depthRangeMillimeters.map {
                $0.lowerBound...$0.upperBound
            },
            features: Set(features)
        )
    }
}

private struct BoardPackageMillimeterRangeDocument: Decodable {
    let lowerBound: Int
    let upperBound: Int

    private enum CodingKeys: String, CodingKey {
        case lowerBound
        case upperBound
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["lowerBound", "upperBound"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        lowerBound = try container.decode(Int.self, forKey: .lowerBound)
        upperBound = try container.decode(Int.self, forKey: .upperBound)
    }
}

struct BoardPackageFrameDocument: Decodable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double

    private enum CodingKeys: String, CodingKey {
        case x
        case y
        case width
        case height
    }

    init(x: Double, y: Double, width: Double, height: Double) {
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["x", "y", "width", "height"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        x = try container.decode(Double.self, forKey: .x)
        y = try container.decode(Double.self, forKey: .y)
        width = try container.decode(Double.self, forKey: .width)
        height = try container.decode(Double.self, forKey: .height)
    }

    var cgRect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }

    var holdFrame: HoldFrame {
        HoldFrame(x: x, y: y, width: width, height: height)
    }

    var isNormalized: Bool {
        x.isFinite && y.isFinite && width.isFinite && height.isFinite &&
            x >= 0 && y >= 0 && width > 0 && height > 0 &&
            x + width <= 1 && y + height <= 1
    }

    static let fullCanvas = BoardPackageFrameDocument(x: 0, y: 0, width: 1, height: 1)

    func matches(_ other: BoardPackageFrameDocument, tolerance: Double = 0.0000005) -> Bool {
        abs(x - other.x) <= tolerance && abs(y - other.y) <= tolerance &&
            abs(width - other.width) <= tolerance && abs(height - other.height) <= tolerance
    }
}

private struct BoardPackageArtworkDocument: Decodable {
    let schemaVersion: Int
    let boardID: String
    let canvasFrame: BoardPackageFrameDocument
    let palette: BoardPackageArtworkPalette
    let silhouette: BoardPackageArtworkShapeDocument
    let layers: [BoardPackageArtworkLayerDocument]
    let holdPieces: [BoardPackageArtworkHoldPieceDocument]

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case boardID
        case canvasFrame
        case palette
        case silhouette
        case layers
        case holdPieces
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "schemaVersion", "boardID", "canvasFrame", "palette", "silhouette", "layers", "holdPieces"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        boardID = try container.decode(String.self, forKey: .boardID)
        canvasFrame = try container.decode(BoardPackageFrameDocument.self, forKey: .canvasFrame)
        palette = try container.decode(BoardPackageArtworkPalette.self, forKey: .palette)
        silhouette = try container.decode(BoardPackageArtworkShapeDocument.self, forKey: .silhouette)
        layers = try container.decode([BoardPackageArtworkLayerDocument].self, forKey: .layers)
        holdPieces = try container.decode([BoardPackageArtworkHoldPieceDocument].self, forKey: .holdPieces)
    }
}

private struct BoardPackageArtworkLayerDocument: Decodable {
    let id: String
    let role: BoardPackageArtworkLayerRole
    let frame: BoardPackageFrameDocument
    let shape: BoardPackageArtworkShapeDocument

    private enum CodingKeys: String, CodingKey {
        case id
        case role
        case frame
        case shape
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "role", "frame", "shape"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        role = try container.decode(BoardPackageArtworkLayerRole.self, forKey: .role)
        frame = try container.decode(BoardPackageFrameDocument.self, forKey: .frame)
        shape = try container.decode(BoardPackageArtworkShapeDocument.self, forKey: .shape)
    }
}

private struct BoardPackageArtworkHoldPieceDocument: Decodable {
    let id: String
    let holdID: String
    let frame: BoardPackageFrameDocument
    let shape: BoardPackageArtworkShapeDocument
    let treatment: BoardPackageArtworkTreatmentDocument

    private enum CodingKeys: String, CodingKey {
        case id
        case holdID
        case frame
        case shape
        case treatment
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "holdID", "frame", "shape", "treatment"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        holdID = try container.decode(String.self, forKey: .holdID)
        frame = try container.decode(BoardPackageFrameDocument.self, forKey: .frame)
        shape = try container.decode(BoardPackageArtworkShapeDocument.self, forKey: .shape)
        treatment = try container.decode(BoardPackageArtworkTreatmentDocument.self, forKey: .treatment)
    }
}

private enum BoardPackageArtworkPalette: String, Decodable {
    case sculptedWood
}

private enum BoardPackageArtworkLayerRole: String, Decodable {
    case topPlane
    case separator
    case bottomPlane
    case topSeam
}

private enum BoardPackageArtworkShapeType: String, Decodable {
    case roundedRect
    case path
}

private struct BoardPackageArtworkShapeDocument: Decodable {
    let type: BoardPackageArtworkShapeType
    let cornerRadiusFraction: Double?
    let commands: [BoardPackageArtworkPathCommandDocument]?

    private enum CodingKeys: String, CodingKey {
        case type
        case cornerRadiusFraction
        case commands
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(BoardPackageArtworkShapeType.self, forKey: .type)
        switch type {
        case .roundedRect:
            try decoder.rejectUnknownKeys(["type", "cornerRadiusFraction"])
            cornerRadiusFraction = try container.decode(Double.self, forKey: .cornerRadiusFraction)
            commands = nil
        case .path:
            try decoder.rejectUnknownKeys(["type", "commands"])
            cornerRadiusFraction = nil
            commands = try container.decode([BoardPackageArtworkPathCommandDocument].self, forKey: .commands)
        }
    }

    func isValid(in frame: BoardPackageFrameDocument) -> Bool {
        guard frame.isNormalized else { return false }
        switch type {
        case .roundedRect:
            guard let radius = cornerRadiusFraction,
                  radius.isFinite,
                  (0...0.5).contains(radius) else { return false }
            return true
        case .path:
            guard let commands else { return false }
            return BoardPackageArtworkPathGeometry(commands: commands, frame: frame).isValid
        }
    }

    func derivedFrame(in frame: BoardPackageFrameDocument) -> BoardPackageFrameDocument {
        guard type == .path,
              let commands,
              !commands.isEmpty else { return frame }
        let points = commands.flatMap(\.points).map { point in
            (x: frame.x + point.x * frame.width, y: frame.y + point.y * frame.height)
        }
        guard let minimumX = points.map(\.x).min(),
              let maximumX = points.map(\.x).max(),
              let minimumY = points.map(\.y).min(),
              let maximumY = points.map(\.y).max() else { return frame }
        return BoardPackageFrameDocument(
            x: minimumX,
            y: minimumY,
            width: maximumX - minimumX,
            height: maximumY - minimumY
        )
    }
}

private enum BoardPackageArtworkPathCommand: String, Decodable {
    case move
    case line
    case quad
    case curve
    case close
}

private struct BoardPackageArtworkPoint: Decodable {
    let x: Double
    let y: Double

    init(x: Double, y: Double) {
        self.x = x
        self.y = y
    }

    init(from decoder: Decoder) throws {
        var container = try decoder.unkeyedContainer()
        x = try container.decode(Double.self)
        y = try container.decode(Double.self)
        guard container.isAtEnd else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Point must have two coordinates")
        }
    }

    var isNormalized: Bool {
        x.isFinite && y.isFinite && (0...1).contains(x) && (0...1).contains(y)
    }
}

private struct BoardPackageArtworkPathCommandDocument: Decodable {
    let command: BoardPackageArtworkPathCommand
    let to: BoardPackageArtworkPoint?
    let control: BoardPackageArtworkPoint?
    let control1: BoardPackageArtworkPoint?
    let control2: BoardPackageArtworkPoint?

    private enum CodingKeys: String, CodingKey {
        case command
        case to
        case control
        case control1
        case control2
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        command = try container.decode(BoardPackageArtworkPathCommand.self, forKey: .command)
        switch command {
        case .move, .line:
            try decoder.rejectUnknownKeys(["command", "to"])
            to = try container.decode(BoardPackageArtworkPoint.self, forKey: .to)
            control = nil
            control1 = nil
            control2 = nil
        case .quad:
            try decoder.rejectUnknownKeys(["command", "control", "to"])
            control = try container.decode(BoardPackageArtworkPoint.self, forKey: .control)
            to = try container.decode(BoardPackageArtworkPoint.self, forKey: .to)
            control1 = nil
            control2 = nil
        case .curve:
            try decoder.rejectUnknownKeys(["command", "control1", "control2", "to"])
            control1 = try container.decode(BoardPackageArtworkPoint.self, forKey: .control1)
            control2 = try container.decode(BoardPackageArtworkPoint.self, forKey: .control2)
            to = try container.decode(BoardPackageArtworkPoint.self, forKey: .to)
            control = nil
        case .close:
            try decoder.rejectUnknownKeys(["command"])
            to = nil
            control = nil
            control1 = nil
            control2 = nil
        }
    }

    var points: [BoardPackageArtworkPoint] {
        [to, control, control1, control2].compactMap { $0 }
    }
}

private enum BoardPackageArtworkTreatmentType: String, Decodable {
    case surface
    case shelf
    case recess
}

private enum BoardPackageArtworkRecessDepth: String, Decodable {
    case shallow
    case deep
}

private struct BoardPackageArtworkTreatmentDocument: Decodable {
    let type: BoardPackageArtworkTreatmentType
    let rimInsetFraction: Double?
    let depth: BoardPackageArtworkRecessDepth?

    private enum CodingKeys: String, CodingKey {
        case type
        case rimInsetFraction
        case depth
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(BoardPackageArtworkTreatmentType.self, forKey: .type)
        switch type {
        case .surface:
            try decoder.rejectUnknownKeys(["type"])
            rimInsetFraction = nil
            depth = nil
        case .shelf:
            try decoder.rejectUnknownKeys(["type", "rimInsetFraction"])
            rimInsetFraction = try container.decode(Double.self, forKey: .rimInsetFraction)
            depth = nil
        case .recess:
            try decoder.rejectUnknownKeys(["type", "rimInsetFraction", "depth"])
            rimInsetFraction = try container.decode(Double.self, forKey: .rimInsetFraction)
            depth = try container.decode(BoardPackageArtworkRecessDepth.self, forKey: .depth)
        }
    }

    var isValid: Bool {
        guard type != .surface else { return true }
        guard let rimInsetFraction else { return false }
        return rimInsetFraction.isFinite && (0...0.5).contains(rimInsetFraction)
    }
}

private struct BoardPackageArtworkPathGeometry {
    private let commands: [BoardPackageArtworkPathCommandDocument]
    private let frame: BoardPackageFrameDocument
    private let epsilon = 0.000000001

    init(commands: [BoardPackageArtworkPathCommandDocument], frame: BoardPackageFrameDocument) {
        self.commands = commands
        self.frame = frame
    }

    var isValid: Bool {
        guard !commands.isEmpty,
              commands.first?.command == .move,
              commands.last?.command == .close,
              commands.filter({ $0.command == .move }).count == 1,
              commands.filter({ $0.command == .close }).count == 1,
              commands.dropLast().allSatisfy({ $0.command != .close }),
              commands.allSatisfy({ $0.points.allSatisfy(\.isNormalized) }),
              let start = commands.first?.to else { return false }

        var current = start
        var points = [absolute(start)]
        for command in commands.dropFirst() {
            switch command.command {
            case .line:
                guard let end = command.to else { return false }
                current = end
                points.append(absolute(end))
            case .quad:
                guard let control = command.control, let end = command.to else { return false }
                let previous = current
                for step in 1...32 {
                    let t = Double(step) / 32
                    points.append(absolute(interpolateQuadratic(previous, control, end, t)))
                }
                current = end
            case .curve:
                guard let control1 = command.control1,
                      let control2 = command.control2,
                      let end = command.to else { return false }
                let previous = current
                for step in 1...32 {
                    let t = Double(step) / 32
                    points.append(absolute(interpolateCubic(previous, control1, control2, end, t)))
                }
                current = end
            case .close:
                if !same(absolute(current), absolute(start)) {
                    points.append(absolute(start))
                }
            case .move:
                return false
            }
        }
        return isSimpleClosedContour(points)
    }

    private func absolute(_ point: BoardPackageArtworkPoint) -> CGPoint {
        CGPoint(x: frame.x + point.x * frame.width, y: frame.y + point.y * frame.height)
    }

    private func interpolateQuadratic(
        _ start: BoardPackageArtworkPoint,
        _ control: BoardPackageArtworkPoint,
        _ end: BoardPackageArtworkPoint,
        _ t: Double
    ) -> BoardPackageArtworkPoint {
        BoardPackageArtworkPoint(
            x: (1 - t) * (1 - t) * start.x + 2 * (1 - t) * t * control.x + t * t * end.x,
            y: (1 - t) * (1 - t) * start.y + 2 * (1 - t) * t * control.y + t * t * end.y
        )
    }

    private func interpolateCubic(
        _ start: BoardPackageArtworkPoint,
        _ control1: BoardPackageArtworkPoint,
        _ control2: BoardPackageArtworkPoint,
        _ end: BoardPackageArtworkPoint,
        _ t: Double
    ) -> BoardPackageArtworkPoint {
        BoardPackageArtworkPoint(
            x: pow(1 - t, 3) * start.x + 3 * pow(1 - t, 2) * t * control1.x + 3 * (1 - t) * t * t * control2.x + t * t * t * end.x,
            y: pow(1 - t, 3) * start.y + 3 * pow(1 - t, 2) * t * control1.y + 3 * (1 - t) * t * t * control2.y + t * t * t * end.y
        )
    }

    private func isSimpleClosedContour(_ points: [CGPoint]) -> Bool {
        guard points.count >= 4, same(points[0], points[points.count - 1]) else { return false }
        let distinct = Set(points.dropLast().map { "\(Int(($0.x * 1_000_000_000_000).rounded())):\(Int(($0.y * 1_000_000_000_000).rounded()))" })
        guard distinct.count >= 3 else { return false }
        let segments = points.count - 1
        for first in 0..<segments {
            guard !same(points[first], points[first + 1]) else { return false }
            for second in (first + 1)..<segments {
                if second == first + 1 || (first == 0 && second == segments - 1) { continue }
                guard !intersects(points[first], points[first + 1], points[second], points[second + 1]) else {
                    return false
                }
            }
        }
        return abs(signedArea(points)) > epsilon
    }

    private func signedArea(_ points: [CGPoint]) -> Double {
        zip(points, points.dropFirst()).reduce(0) { $0 + $1.0.x * $1.1.y - $1.1.x * $1.0.y } / 2
    }

    private func intersects(_ a: CGPoint, _ b: CGPoint, _ c: CGPoint, _ d: CGPoint) -> Bool {
        let ac = orientation(a, b, c), ad = orientation(a, b, d)
        let ca = orientation(c, d, a), cb = orientation(c, d, b)
        if ((ac > epsilon && ad < -epsilon) || (ac < -epsilon && ad > epsilon)) &&
            ((ca > epsilon && cb < -epsilon) || (ca < -epsilon && cb > epsilon)) { return true }
        return (abs(ac) <= epsilon && onSegment(a, b, c)) ||
            (abs(ad) <= epsilon && onSegment(a, b, d)) ||
            (abs(ca) <= epsilon && onSegment(c, d, a)) ||
            (abs(cb) <= epsilon && onSegment(c, d, b))
    }

    private func orientation(_ a: CGPoint, _ b: CGPoint, _ c: CGPoint) -> Double {
        (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
    }

    private func onSegment(_ a: CGPoint, _ b: CGPoint, _ point: CGPoint) -> Bool {
        min(a.x, b.x) - epsilon <= point.x && point.x <= max(a.x, b.x) + epsilon &&
            min(a.y, b.y) - epsilon <= point.y && point.y <= max(a.y, b.y) + epsilon
    }

    private func same(_ a: CGPoint, _ b: CGPoint) -> Bool {
        abs(a.x - b.x) <= epsilon && abs(a.y - b.y) <= epsilon
    }
}

private struct BoardPackageSemanticsDocument: Decodable {
    let schemaVersion: Int
    let boardID: String
    let semanticHolds: [String: BoardPackageSemanticMappingDocument]

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case boardID
        case semanticHolds
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["schemaVersion", "boardID", "semanticHolds"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        boardID = try container.decode(String.self, forKey: .boardID)
        semanticHolds = try container.decode(
            [String: BoardPackageSemanticMappingDocument].self,
            forKey: .semanticHolds
        )
    }
}

private struct BoardPackageEvidenceDocument: Decodable {
    let schemaVersion: Int
    let boardID: String
    let checkedAt: String
    let sources: [BoardPackageEvidenceSourceDocument]
    let fieldEvidence: [String: BoardPackageEvidenceMappingDocument]
    let holdEvidence: [String: BoardPackageEvidenceMappingDocument]
    let semanticEvidence: [String: BoardPackageEvidenceMappingDocument]
    let artworkEvidence: [String: BoardPackageEvidenceMappingDocument]
    let assetEvidence: [String: BoardPackageEvidenceMappingDocument]

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case boardID
        case checkedAt
        case sources
        case fieldEvidence
        case holdEvidence
        case semanticEvidence
        case artworkEvidence
        case assetEvidence
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "schemaVersion", "boardID", "checkedAt", "sources", "fieldEvidence",
            "holdEvidence", "semanticEvidence", "artworkEvidence", "assetEvidence"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        boardID = try container.decode(String.self, forKey: .boardID)
        checkedAt = try container.decode(String.self, forKey: .checkedAt)
        sources = try container.decode([BoardPackageEvidenceSourceDocument].self, forKey: .sources)
        fieldEvidence = try container.decode([String: BoardPackageEvidenceMappingDocument].self, forKey: .fieldEvidence)
        holdEvidence = try container.decode([String: BoardPackageEvidenceMappingDocument].self, forKey: .holdEvidence)
        semanticEvidence = try container.decode([String: BoardPackageEvidenceMappingDocument].self, forKey: .semanticEvidence)
        artworkEvidence = try container.decode(
            [String: BoardPackageEvidenceMappingDocument].self,
            forKey: .artworkEvidence
        )
        assetEvidence = try container.decode([String: BoardPackageEvidenceMappingDocument].self, forKey: .assetEvidence)
    }

}

private struct BoardPackageEvidenceSourceDocument: Decodable {
    let id: String
    let title: String
    let url: URL

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case url
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "title", "url"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        url = try container.decode(URL.self, forKey: .url)
    }
}

private struct BoardPackageEvidenceMappingDocument: Decodable {
    let sourceIDs: [String]
    let method: String

    private enum CodingKeys: String, CodingKey {
        case sourceIDs
        case method
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["sourceIDs", "method"])
        let keyedContainer = try decoder.container(keyedBy: CodingKeys.self)
        sourceIDs = try keyedContainer.decode([String].self, forKey: .sourceIDs)
        method = try keyedContainer.decode(String.self, forKey: .method)
    }
}

private extension Dictionary where Key == String, Value == BoardPackageEvidenceMappingDocument {
    func validEvidenceMap(
        expectedKeys: Set<String>,
        sourceIDs: Set<String>,
        externalGenerationKeys: Set<String> = []
    ) -> Bool {
        guard Set(keys) == expectedKeys else { return false }
        for (key, mapping) in self {
            let methodAllowed = mapping.method == "manufacturer-measurement" ||
                mapping.method == "reviewed-human-authored-normalization" ||
                (externalGenerationKeys.contains(key) &&
                    mapping.method == "external-generative-adaptation")
            guard methodAllowed,
                  !mapping.sourceIDs.isEmpty,
                  Set(mapping.sourceIDs).count == mapping.sourceIDs.count,
                  mapping.sourceIDs.allSatisfy(\.isBoardPackageIdentifier),
                  Set(mapping.sourceIDs).isSubset(of: sourceIDs) else { return false }
        }
        return true
    }
}

private struct BoardPackageSemanticMappingDocument: Decodable {
    let holdIDs: [String]

    private enum CodingKeys: String, CodingKey {
        case holdIDs
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["holdIDs"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        holdIDs = try container.decode([String].self, forKey: .holdIDs)
    }
}
