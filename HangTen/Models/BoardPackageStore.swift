import Foundation

enum BoardPackageStoreError: Error, Equatable, LocalizedError {
    case missingCatalog
    case malformedJSON(resource: String)
    case missingApprovedSidecar(boardID: String, filename: String)
    case approvedPackagePathEscape(boardID: String, path: String)
    case presentationAssetPathEscape(boardID: String, path: String)
    case missingPresentationAsset(boardID: String, path: String)
    case boardIDMismatch(expected: String, actual: String, resource: String)
    case duplicateBoardID(String)
    case duplicateHoldID(boardID: String, holdID: String)
    case unknownSemanticHoldID(boardID: String, holdID: String)
    case unknownArtworkHoldID(boardID: String, holdID: String)
    case invalidPackage(boardID: String, reason: String)

    var errorDescription: String? {
        switch self {
        case .missingCatalog:
            "The bundled Hangboards/catalog.json resource is missing."
        case .malformedJSON(let resource):
            "The bundled board resource is malformed: \(resource)."
        case let .missingApprovedSidecar(boardID, filename):
            "Approved board \(boardID) is missing \(filename)."
        case let .approvedPackagePathEscape(boardID, path):
            "Approved board \(boardID) has a package path outside Hangboards: \(path)."
        case let .presentationAssetPathEscape(boardID, path):
            "Approved board \(boardID) has a presentation path outside its package: \(path)."
        case let .missingPresentationAsset(boardID, path):
            "Approved board \(boardID) is missing its presentation asset: \(path)."
        case let .boardIDMismatch(expected, actual, resource):
            "Expected board ID \(expected) in \(resource), got \(actual)."
        case .duplicateBoardID(let boardID):
            "The bundled catalog contains duplicate board ID \(boardID)."
        case let .duplicateHoldID(boardID, holdID):
            "Approved board \(boardID) contains duplicate hold ID \(holdID)."
        case let .unknownSemanticHoldID(boardID, holdID):
            "Approved board \(boardID) semantics reference unknown hold ID \(holdID)."
        case let .unknownArtworkHoldID(boardID, holdID):
            "Approved board \(boardID) artwork references unknown hold ID \(holdID)."
        case let .invalidPackage(boardID, reason):
            "Approved board \(boardID) is invalid: \(reason)"
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
        var loadedBoards: [TrainingBoard] = []
        var loadedSemantics: [String: [String: [String]]] = [:]
        var loadedDesigns: [String: BoardDesign] = [:]
        var loadedPresentationURLs: [String: URL] = [:]

        for entry in catalog.boards {
            guard seenCatalogIDs.insert(entry.id).inserted else {
                throw BoardPackageStoreError.duplicateBoardID(entry.id)
            }
            guard entry.status == .approved else { continue }

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
                design = try artworkDocument.boardDesign()
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
        let url = packageURL.appendingPathComponent(filename, isDirectory: false)
        guard FileManager.default.isReadableFile(atPath: url.path) else {
            throw BoardPackageStoreError.missingApprovedSidecar(
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
            throw BoardPackageStoreError.approvedPackagePathEscape(
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

    private static func validateHolds(
        in document: BoardPackageBoardDocument
    ) throws -> Set<String> {
        var holdIDs = Set<String>()
        for hold in document.holds {
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
            if let depthRange = hold.depthRangeMillimeters,
               depthRange.lowerBound > depthRange.upperBound {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid depth range"
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
        for mapping in semantics.values {
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
        for piece in artwork.holdPieces where !holdIDs.contains(piece.holdID) {
            throw BoardPackageStoreError.unknownArtworkHoldID(
                boardID: boardID,
                holdID: piece.holdID
            )
        }
    }
}

private struct BoardPackageCatalogDocument: Decodable {
    let schemaVersion: Int
    let boards: [BoardPackageCatalogEntry]
}

private struct BoardPackageCatalogEntry: Decodable {
    enum Status: String, Decodable {
        case draft
        case approved
    }

    let id: String
    let path: String
    let status: Status
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
}

struct BoardPackageFrameDocument: Decodable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double

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
}

private struct BoardPackageSemanticMappingDocument: Decodable {
    let holdIDs: [String]
}

struct BoardArtworkDocument: Decodable {
    let schemaVersion: Int
    let boardID: String
    let canvasFrame: BoardPackageFrameDocument
    let palette: String
    let silhouette: BoardArtworkShapeDocument
    let layers: [BoardArtworkLayerDocument]
    let holdPieces: [BoardArtworkHoldPieceDocument]
}

struct BoardArtworkLayerDocument: Decodable {
    let id: String
    let role: String
    let frame: BoardPackageFrameDocument
    let shape: BoardArtworkShapeDocument
}

struct BoardArtworkHoldPieceDocument: Decodable {
    let id: String
    let holdID: String
    let frame: BoardPackageFrameDocument
    let shape: BoardArtworkShapeDocument
    let treatment: BoardArtworkTreatmentDocument
}

struct BoardArtworkShapeDocument: Decodable {
    let type: String
    let commands: [BoardArtworkPathCommandDocument]?
    let cornerRadiusFraction: Double?
}

struct BoardArtworkPathCommandDocument: Decodable {
    let command: String
    let to: [Double]?
    let control: [Double]?
    let control1: [Double]?
    let control2: [Double]?
}

struct BoardArtworkTreatmentDocument: Decodable {
    let type: String
    let rimInsetFraction: Double?
    let depth: String?
}
