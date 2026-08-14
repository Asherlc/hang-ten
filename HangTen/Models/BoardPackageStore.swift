import Foundation
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
            let semanticsDocument: BoardPackageSemanticsDocument = try Self.decodeSidecar(
                named: "semantics.json",
                boardID: entry.id,
                packageURL: packageURL,
                resourcePrefix: resourcePrefix
            )
            try Self.validateSchema(boardDocument.schemaVersion, resource: "\(resourcePrefix)/board.json")
            try Self.validateSchema(semanticsDocument.schemaVersion, resource: "\(resourcePrefix)/semantics.json")
            try Self.validateMetadata(
                boardDocument: boardDocument,
                semanticsDocument: semanticsDocument,
                boardID: entry.id
            )
            try Self.validateBoardIDs(
                catalogID: entry.id,
                boardDocument: boardDocument,
                semanticsDocument: semanticsDocument,
                resourcePrefix: resourcePrefix
            )

            let holdIDs = try Self.validateHolds(in: boardDocument)
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
            guard Self.isDecodablePresentationImage(at: assetURL) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: board.id,
                    reason: "presentation asset must be a decodable PNG"
                )
            }
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
        guard path == "assets/primary.png" else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "presentation asset path must be assets/primary.png"
            )
        }
        return url
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
        semanticsDocument: BoardPackageSemanticsDocument,
        resourcePrefix: String
    ) throws {
        for (actual, filename) in [
            (boardDocument.id, "board.json"),
            (semanticsDocument.boardID, "semantics.json")
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
