import Foundation

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
    case unknownArtworkHoldID(boardID: String, holdID: String)
    case missingArtworkHoldID(boardID: String, holdID: String)
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
        case let .unknownArtworkHoldID(boardID, holdID):
            "Board \(boardID) artwork references unknown hold ID \(holdID)."
        case let .missingArtworkHoldID(boardID, holdID):
            "Board \(boardID) artwork is missing hold ID \(holdID)."
        case let .invalidPackage(boardID, reason):
            "Board \(boardID) is invalid: \(reason)"
        }
    }
}

struct BoardPackageStore {
    let boards: [TrainingBoard]

    private let boardsByID: [String: TrainingBoard]
    private let semanticsByBoardID: [String: [String: [String]]]
    private let designsByBoardID: [String: BoardDesign]
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
        var loadedDesigns: [String: BoardDesign] = [:]
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
            let artworkDocument: BoardArtworkDocument = try Self.decodeSidecar(
                named: "artwork.json",
                boardID: entry.id,
                packageURL: packageURL,
                resourcePrefix: resourcePrefix
            )

            try Self.validateSchema(boardDocument.schemaVersion, resource: "\(resourcePrefix)/board.json")
            try Self.validateSchema(semanticsDocument.schemaVersion, resource: "\(resourcePrefix)/semantics.json")
            try Self.validateSchema(artworkDocument.schemaVersion, resource: "\(resourcePrefix)/artwork.json")
            try Self.validateMetadata(
                boardDocument: boardDocument,
                semanticsDocument: semanticsDocument,
                artworkDocument: artworkDocument,
                boardID: entry.id
            )
            try Self.validateBoardIDs(
                catalogID: entry.id,
                boardDocument: boardDocument,
                semanticsDocument: semanticsDocument,
                artworkDocument: artworkDocument,
                resourcePrefix: resourcePrefix
            )

            let holdIDs = try Self.validateHolds(in: boardDocument)
            try Self.validateSemantics(
                semanticsDocument.semanticHolds,
                boardID: entry.id,
                holdIDs: holdIDs
            )
            try Self.validateArtwork(
                artworkDocument,
                boardID: entry.id,
                holdIDs: holdIDs
            )

            let semantics = semanticsDocument.semanticHolds.mapValues(\.holdIDs)
            let board = try boardDocument.trainingBoard(semantics: semantics)
            let design: BoardDesign
            do {
                design = try artworkDocument.boardDesign(holds: board.holds)
            } catch {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: entry.id,
                    reason: String(describing: error)
                )
            }

            loadedBoards.append(board)
            loadedSemantics[board.id] = semantics
            loadedDesigns[board.id] = design

            if let assetPath = boardDocument.presentation?.assetPath {
                let assetURL = try Self.presentationAssetURL(
                    path: assetPath,
                    boardID: board.id,
                    packageURL: packageURL
                )
                guard FileManager.default.isReadableFile(atPath: assetURL.path) else {
                    throw BoardPackageStoreError.missingPresentationAsset(
                        boardID: board.id,
                        path: assetPath
                    )
                }
                loadedPresentationURLs[board.id] = assetURL
            }
        }

        self.boards = loadedBoards
        self.boardsByID = Dictionary(uniqueKeysWithValues: loadedBoards.map { ($0.id, $0) })
        self.semanticsByBoardID = loadedSemantics
        self.designsByBoardID = loadedDesigns
        self.presentationURLsByBoardID = loadedPresentationURLs
    }

    func board(id: String) -> TrainingBoard? {
        boardsByID[id]
    }

    func semantics(for boardID: String) -> [String: [String]] {
        semanticsByBoardID[boardID] ?? [:]
    }

    func design(for boardID: String) -> BoardDesign? {
        designsByBoardID[boardID]
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
        return url
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
        artworkDocument: BoardArtworkDocument,
        resourcePrefix: String
    ) throws {
        for (actual, filename) in [
            (boardDocument.id, "board.json"),
            (semanticsDocument.boardID, "semantics.json"),
            (artworkDocument.boardID, "artwork.json")
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
        artworkDocument: BoardArtworkDocument,
        boardID: String
    ) throws {
        let requiredStrings = [
            boardDocument.id,
            boardDocument.manufacturer,
            boardDocument.name,
            boardDocument.subtitle,
            boardDocument.dimensions,
            boardDocument.productURL.absoluteString,
            semanticsDocument.boardID,
            artworkDocument.boardID,
            artworkDocument.palette
        ]
        guard requiredStrings.allSatisfy({ !$0.isEmpty }) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "required metadata must not be empty"
            )
        }
        guard boardDocument.id.isBoardPackageIdentifier,
              semanticsDocument.boardID.isBoardPackageIdentifier,
              artworkDocument.boardID.isBoardPackageIdentifier else {
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
                  !hold.name.isEmpty else {
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
            if let fingerCapacity = hold.fingerCapacity,
               !BoardHold.validFingerCapacityRange.contains(fingerCapacity) {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid finger capacity"
                )
            }
            guard !hold.geometry.isEmpty else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) geometry must include at least one piece"
                )
            }
            for (pieceIndex, piece) in hold.geometry.enumerated() {
                guard piece.frame.isNormalized else {
                    throw BoardPackageStoreError.invalidPackage(
                        boardID: document.id,
                        reason: "hold \(hold.id) geometry[\(pieceIndex)] has an invalid frame"
                    )
                }
                do {
                    _ = try piece.boardHoldPiece(
                        id: "\(hold.id)-piece-\(pieceIndex)",
                        holdID: hold.id
                    )
                } catch {
                    throw BoardPackageStoreError.invalidPackage(
                        boardID: document.id,
                        reason: "hold \(hold.id) geometry[\(pieceIndex)] is invalid: \(error)"
                    )
                }
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
            if let features = hold.features,
               Set(features).count != features.count {
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

    private static func validateArtwork(
        _ artwork: BoardArtworkDocument,
        boardID: String,
        holdIDs: Set<String>
    ) throws {
        guard artwork.layers.allSatisfy({ !$0.id.isEmpty }),
              artwork.holdPieces.allSatisfy({
                  !$0.id.isEmpty && $0.holdID.isBoardPackageIdentifier
              }) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "artwork IDs must not be empty"
            )
        }
        let artworkHoldIDs = Set(artwork.holdPieces.map(\.holdID))
        if let unknownHoldID = artworkHoldIDs.subtracting(holdIDs).sorted().first {
            throw BoardPackageStoreError.unknownArtworkHoldID(
                boardID: boardID,
                holdID: unknownHoldID
            )
        }
        if let missingHoldID = holdIDs.subtracting(artworkHoldIDs).sorted().first {
            throw BoardPackageStoreError.missingArtworkHoldID(
                boardID: boardID,
                holdID: missingHoldID
            )
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
            holds: try holds.map { try $0.trainingBoardHold() },
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
    let kind: HoldKind
    let geometry: [BoardHoldPieceDocument]
    let sizeMillimeters: Int?
    let depthRangeMillimeters: BoardPackageMillimeterRangeDocument?
    let gripType: GripType?
    let fingerCapacity: Int?
    let features: [HoldFeature]?

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case kind
        case geometry
        case sizeMillimeters
        case depthRangeMillimeters
        case gripType
        case fingerCapacity
        case features
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "id", "name", "kind", "geometry", "sizeMillimeters",
            "depthRangeMillimeters", "gripType", "fingerCapacity", "features"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        kind = try container.decode(HoldKind.self, forKey: .kind)
        geometry = try container.decode([BoardHoldPieceDocument].self, forKey: .geometry)
        sizeMillimeters = try container.decodeIfPresent(Int.self, forKey: .sizeMillimeters)
        depthRangeMillimeters = try container.decodeIfPresent(
            BoardPackageMillimeterRangeDocument.self,
            forKey: .depthRangeMillimeters
        )
        gripType = try container.decodeIfPresent(GripType.self, forKey: .gripType)
        fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        features = try container.decodeIfPresent([HoldFeature].self, forKey: .features)
    }

    func trainingBoardHold() throws -> BoardHold {
        let pieces = try geometry.enumerated().map { index, document in
            try document.boardHoldPiece(id: "\(id)-piece-\(index)", holdID: id)
        }
        return BoardHold(
            id: id,
            name: name,
            kind: kind,
            geometry: pieces,
            sizeMillimeters: sizeMillimeters,
            gripType: gripType,
            fingerCapacity: fingerCapacity,
            depthRangeMillimeters: depthRangeMillimeters.map {
                $0.lowerBound...$0.upperBound
            },
            features: features.map(Set.init)
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

struct BoardPackageFrameDocument: Codable, Hashable {
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

struct BoardArtworkDocument: Decodable {
    let schemaVersion: Int
    let boardID: String
    let canvasFrame: BoardPackageFrameDocument
    let palette: String
    let silhouette: BoardArtworkShapeDocument
    let layers: [BoardArtworkLayerDocument]
    let holdPieces: [BoardArtworkHoldPieceDocument]

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
            "schemaVersion", "boardID", "canvasFrame", "palette", "silhouette", "layers",
            "holdPieces"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        boardID = try container.decode(String.self, forKey: .boardID)
        canvasFrame = try container.decode(BoardPackageFrameDocument.self, forKey: .canvasFrame)
        palette = try container.decode(String.self, forKey: .palette)
        silhouette = try container.decode(BoardArtworkShapeDocument.self, forKey: .silhouette)
        layers = try container.decode([BoardArtworkLayerDocument].self, forKey: .layers)
        holdPieces = try container.decode([BoardArtworkHoldPieceDocument].self, forKey: .holdPieces)
    }
}

struct BoardArtworkLayerDocument: Decodable {
    let id: String
    let role: String
    let frame: BoardPackageFrameDocument
    let shape: BoardArtworkShapeDocument

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
        role = try container.decode(String.self, forKey: .role)
        frame = try container.decode(BoardPackageFrameDocument.self, forKey: .frame)
        shape = try container.decode(BoardArtworkShapeDocument.self, forKey: .shape)
    }
}

struct BoardArtworkHoldPieceDocument: Decodable {
    let id: String
    let holdID: String
    let frame: BoardPackageFrameDocument
    let shape: BoardArtworkShapeDocument
    let treatment: BoardArtworkTreatmentDocument

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
        shape = try container.decode(BoardArtworkShapeDocument.self, forKey: .shape)
        treatment = try container.decode(BoardArtworkTreatmentDocument.self, forKey: .treatment)
    }
}

struct BoardArtworkShapeDocument: Codable, Hashable {
    let type: String
    let commands: [BoardArtworkPathCommandDocument]?
    let cornerRadiusFraction: Double?

    private enum CodingKeys: String, CodingKey {
        case type
        case commands
        case cornerRadiusFraction
    }

    init(
        type: String,
        commands: [BoardArtworkPathCommandDocument]?,
        cornerRadiusFraction: Double?
    ) {
        self.type = type
        self.commands = commands
        self.cornerRadiusFraction = cornerRadiusFraction
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(String.self, forKey: .type)
        switch type {
        case "roundedRect":
            try decoder.rejectUnknownKeys(["type", "cornerRadiusFraction"])
            commands = nil
            cornerRadiusFraction = try container.decode(Double.self, forKey: .cornerRadiusFraction)
        case "path":
            try decoder.rejectUnknownKeys(["type", "commands"])
            commands = try container.decode([BoardArtworkPathCommandDocument].self, forKey: .commands)
            cornerRadiusFraction = nil
        default:
            try decoder.rejectUnknownKeys(["type", "commands", "cornerRadiusFraction"])
            commands = try container.decodeIfPresent(
                [BoardArtworkPathCommandDocument].self,
                forKey: .commands
            )
            cornerRadiusFraction = try container.decodeIfPresent(
                Double.self,
                forKey: .cornerRadiusFraction
            )
        }
    }
}

struct BoardArtworkPathCommandDocument: Codable, Hashable {
    let command: String
    let to: [Double]?
    let control: [Double]?
    let control1: [Double]?
    let control2: [Double]?

    private enum CodingKeys: String, CodingKey {
        case command
        case to
        case control
        case control1
        case control2
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        command = try container.decode(String.self, forKey: .command)
        let allowedKeys: Set<String>
        switch command {
        case "move", "line":
            allowedKeys = ["command", "to"]
        case "quad":
            allowedKeys = ["command", "to", "control"]
        case "curve":
            allowedKeys = ["command", "to", "control1", "control2"]
        case "close":
            allowedKeys = ["command"]
        default:
            allowedKeys = ["command", "to", "control", "control1", "control2"]
        }
        try decoder.rejectUnknownKeys(allowedKeys)
        to = try container.decodeIfPresent([Double].self, forKey: .to)
        control = try container.decodeIfPresent([Double].self, forKey: .control)
        control1 = try container.decodeIfPresent([Double].self, forKey: .control1)
        control2 = try container.decodeIfPresent([Double].self, forKey: .control2)
    }
}

struct BoardArtworkTreatmentDocument: Codable, Hashable {
    let type: String
    let rimInsetFraction: Double?
    let depth: String?

    private enum CodingKeys: String, CodingKey {
        case type
        case rimInsetFraction
        case depth
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(String.self, forKey: .type)
        switch type {
        case "surface":
            try decoder.rejectUnknownKeys(["type"])
            rimInsetFraction = nil
            depth = nil
        case "shelf":
            try decoder.rejectUnknownKeys(["type", "rimInsetFraction"])
            rimInsetFraction = try container.decode(Double.self, forKey: .rimInsetFraction)
            depth = nil
        case "recess":
            try decoder.rejectUnknownKeys(["type", "rimInsetFraction", "depth"])
            rimInsetFraction = try container.decode(Double.self, forKey: .rimInsetFraction)
            depth = try container.decode(String.self, forKey: .depth)
        default:
            try decoder.rejectUnknownKeys(["type", "rimInsetFraction", "depth"])
            rimInsetFraction = try container.decodeIfPresent(Double.self, forKey: .rimInsetFraction)
            depth = try container.decodeIfPresent(String.self, forKey: .depth)
        }
    }
}
