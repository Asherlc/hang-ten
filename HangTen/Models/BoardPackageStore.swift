import Foundation
import ImageIO
import UniformTypeIdentifiers

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
    case missingLibrary
    case malformedJSON(resource: String)
    case missingBoardDocument(slug: String)
    case packagePathEscape(boardID: String, path: String)
    case presentationAssetPathEscape(boardID: String, path: String)
    case missingPresentationAsset(boardID: String, path: String)
    case boardIDMismatch(expected: String, actual: String, resource: String)
    case duplicateBoardID(String)
    case duplicateHoldID(boardID: String, holdID: String)
    case invalidPackage(boardID: String, reason: String)

    var errorDescription: String? {
        switch self {
        case .missingLibrary:
            "The bundled Hangboards resource directory is missing."
        case .malformedJSON(let resource):
            "The bundled board resource is malformed: \(resource)."
        case .missingBoardDocument(let slug):
            "Board package \(slug) is missing board.json."
        case let .packagePathEscape(boardID, path):
            "Board \(boardID) has a package path outside Hangboards: \(path)."
        case let .presentationAssetPathEscape(boardID, path):
            "Board \(boardID) has a presentation path outside its package: \(path)."
        case let .missingPresentationAsset(boardID, path):
            "Board \(boardID) is missing its presentation asset: \(path)."
        case let .boardIDMismatch(expected, actual, resource):
            "Expected board ID \(expected) in \(resource), got \(actual)."
        case .duplicateBoardID(let boardID):
            "The bundled board packages contain duplicate board ID \(boardID)."
        case let .duplicateHoldID(boardID, holdID):
            "Board \(boardID) contains duplicate hold ID \(holdID)."
        case let .invalidPackage(boardID, reason):
            "Board \(boardID) is invalid: \(reason)"
        }
    }
}

struct BoardPackageStore {
    private static let presentationAspectRatioRelativeTolerance = 0.001

    let boards: [TrainingBoard]

    private let boardsByID: [String: TrainingBoard]
    private let presentationURLsByBoardID: [String: URL]

    init(bundle: Bundle = .main) throws {
        guard let resourceURL = bundle.resourceURL else {
            throw BoardPackageStoreError.missingLibrary
        }
        let hangboardsURL = resourceURL.appendingPathComponent("Hangboards", isDirectory: true)
        try Self.validateHangboardsRoot(hangboardsURL)
        var loadedBoards: [TrainingBoard] = []
        var loadedPresentationURLs: [String: URL] = [:]
        var seenBoardIDs = Set<String>()

        for packageURL in try Self.directChildDirectories(of: hangboardsURL) {
            let slug = packageURL.lastPathComponent
            guard slug.isBoardPackageSlug else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: slug,
                    reason: "directory name must be a package slug"
                )
            }
            let boardURL = packageURL.appendingPathComponent("board.json")
            if !FileManager.default.fileExists(atPath: boardURL.path) {
                if try Self.isPrimaryOnlyDraft(packageURL) {
                    continue
                }
                throw BoardPackageStoreError.missingBoardDocument(slug: slug)
            }
            let presentationSize = try Self.validateFinishedPackage(
                packageURL,
                boardID: slug
            )
            let resourcePrefix = "Hangboards/\(slug)"
            let boardDocument: BoardPackageBoardDocument = try Self.decode(
                from: boardURL,
                resource: "\(resourcePrefix)/board.json"
            )
            try Self.validateSchema(boardDocument.schemaVersion, resource: "\(resourcePrefix)/board.json")
            try Self.validateMetadata(boardDocument: boardDocument)
            try Self.validatePresentationAssetPath(
                boardDocument.presentation.assetPath,
                boardID: boardDocument.id,
                in: packageURL
            )
            try Self.validatePresentationAspectRatio(
                boardDocument.aspectRatio,
                imageWidth: presentationSize.width,
                imageHeight: presentationSize.height,
                boardID: boardDocument.id
            )
            let holds = try Self.validateHolds(in: boardDocument)
            guard seenBoardIDs.insert(boardDocument.id).inserted else {
                throw BoardPackageStoreError.duplicateBoardID(boardDocument.id)
            }
            let board = try boardDocument.trainingBoard(holds: holds)
            loadedBoards.append(board)
            let assetURL = packageURL.appendingPathComponent("assets/primary.png")
            loadedPresentationURLs[board.id] = assetURL
        }

        loadedBoards.sort(by: Self.boardComesBefore)
        self.boards = loadedBoards
        self.boardsByID = Dictionary(uniqueKeysWithValues: loadedBoards.map { ($0.id, $0) })
        self.presentationURLsByBoardID = loadedPresentationURLs
    }

    func board(id: String) -> TrainingBoard? {
        boardsByID[id]
    }

    func semantics(for _: String) -> [String: [String]] {
        [:]
    }

    func presentationImageURL(for board: TrainingBoard) -> URL? {
        presentationURLsByBoardID[board.id]
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

    private static func validateHangboardsRoot(_ url: URL) throws {
        let values = try url.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
        guard values.isDirectory == true, values.isSymbolicLink != true else {
            throw BoardPackageStoreError.missingLibrary
        }
    }

    private static func directChildDirectories(of rootURL: URL) throws -> [URL] {
        let children = try FileManager.default.contentsOfDirectory(
            at: rootURL,
            includingPropertiesForKeys: [.isDirectoryKey, .isSymbolicLinkKey],
            options: []
        )
        var directories: [URL] = []
        for child in children {
            let values = try child.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
            if values.isSymbolicLink == true {
                throw BoardPackageStoreError.packagePathEscape(
                    boardID: child.lastPathComponent,
                    path: child.lastPathComponent
                )
            }
            if values.isDirectory == true {
                directories.append(child)
            } else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: child.lastPathComponent,
                    reason: "Hangboards must contain only direct child directories"
                )
            }
        }
        return directories.sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    private static func validateFinishedPackage(
        _ packageURL: URL,
        boardID: String
    ) throws -> (width: Int, height: Int) {
        try validateNoSymlinks(below: packageURL, boardID: boardID)
        let entries = try entryNames(in: packageURL)
        guard entries == ["assets", "board.json"] else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "finished package must contain exactly board.json and assets"
            )
        }
        let boardURL = packageURL.appendingPathComponent("board.json")
        let assetsURL = packageURL.appendingPathComponent("assets", isDirectory: true)
        guard try isRegularFile(boardURL), try isRegularDirectory(assetsURL) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "board.json and assets must be regular non-symlink paths"
            )
        }
        guard try entryNames(in: assetsURL) == ["primary.png"] else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "assets must contain exactly primary.png"
            )
        }
        let primaryURL = assetsURL.appendingPathComponent("primary.png")
        guard try isRegularFile(primaryURL),
              FileManager.default.isReadableFile(atPath: primaryURL.path) else {
            throw BoardPackageStoreError.missingPresentationAsset(
                boardID: boardID,
                path: "assets/primary.png"
            )
        }
        return try validatePNG(
            at: primaryURL,
            boardID: boardID,
            label: "assets/primary.png"
        )
    }

    private static func isPrimaryOnlyDraft(_ packageURL: URL) throws -> Bool {
        try validateNoSymlinks(below: packageURL, boardID: packageURL.lastPathComponent)
        guard try entryNames(in: packageURL) == ["assets"] else { return false }
        let assetsURL = packageURL.appendingPathComponent("assets", isDirectory: true)
        guard try isRegularDirectory(assetsURL),
              try entryNames(in: assetsURL) == ["primary.png"] else { return false }
        let primaryURL = assetsURL.appendingPathComponent("primary.png")
        guard try isRegularFile(primaryURL) else { return false }
        _ = try validatePNG(
            at: primaryURL,
            boardID: packageURL.lastPathComponent,
            label: "draft assets/primary.png"
        )
        return true
    }

    private static func validatePNG(
        at url: URL,
        boardID: String,
        label: String
    ) throws -> (width: Int, height: Int) {
        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "\(label) must be a decodable PNG"
            )
        }
        guard data.starts(with: [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
              let source = CGImageSourceCreateWithData(
                  data as CFData,
                  [kCGImageSourceShouldCache: false] as CFDictionary
              ),
              CGImageSourceGetType(source) as String? == UTType.png.identifier,
              CGImageSourceGetCount(source) == 1,
              CGImageSourceGetStatus(source) == .statusComplete,
              CGImageSourceGetStatusAtIndex(source, 0) == .statusComplete,
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any] else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "\(label) must be a decodable PNG"
            )
        }
        guard let width = properties[kCGImagePropertyPixelWidth] as? NSNumber,
              let height = properties[kCGImagePropertyPixelHeight] as? NSNumber else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "\(label) must be a decodable PNG"
            )
        }
        return (width.intValue, height.intValue)
    }

    private static func validatePresentationAspectRatio(
        _ declaredRatio: Double,
        imageWidth: Int,
        imageHeight: Int,
        boardID: String
    ) throws {
        guard declaredRatio.isFinite, declaredRatio > 0 else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "aspect ratio must be positive"
            )
        }
        let imageRatio = Double(imageWidth) / Double(imageHeight)
        let relativeError = abs(declaredRatio - imageRatio) / imageRatio
        guard relativeError <= presentationAspectRatioRelativeTolerance else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "aspect ratio must match presentation image width/height within 0.1%"
            )
        }
    }

    private static func validateNoSymlinks(below rootURL: URL, boardID: String) throws {
        guard let enumerator = FileManager.default.enumerator(
            at: rootURL,
            includingPropertiesForKeys: [.isSymbolicLinkKey],
            options: []
        ) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "package cannot be enumerated"
            )
        }
        for case let itemURL as URL in enumerator {
            if try itemURL.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink == true {
                throw BoardPackageStoreError.packagePathEscape(
                    boardID: boardID,
                    path: itemURL.path
                )
            }
        }
    }

    private static func entryNames(in directoryURL: URL) throws -> Set<String> {
        Set(
            try FileManager.default.contentsOfDirectory(
                at: directoryURL,
                includingPropertiesForKeys: nil,
                options: []
            ).map(\.lastPathComponent)
        )
    }

    private static func isRegularFile(_ url: URL) throws -> Bool {
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
        return values.isRegularFile == true && values.isSymbolicLink != true
    }

    private static func isRegularDirectory(_ url: URL) throws -> Bool {
        let values = try url.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
        return values.isDirectory == true && values.isSymbolicLink != true
    }

    private static func boardComesBefore(_ lhs: TrainingBoard, _ rhs: TrainingBoard) -> Bool {
        let lhsKey = [lhs.manufacturer.lowercased(), lhs.manufacturer, lhs.name.lowercased(), lhs.name, lhs.id]
        let rhsKey = [rhs.manufacturer.lowercased(), rhs.manufacturer, rhs.name.lowercased(), rhs.name, rhs.id]
        for (left, right) in zip(lhsKey, rhsKey) where left != right {
            return left < right
        }
        return false
    }

    private static func validateSchema(_ schemaVersion: Int, resource: String) throws {
        guard schemaVersion == 1 else {
            throw BoardPackageStoreError.malformedJSON(resource: resource)
        }
    }

    private static func validateMetadata(
        boardDocument: BoardPackageBoardDocument
    ) throws {
        let requiredStrings = [
            boardDocument.id,
            boardDocument.manufacturer,
            boardDocument.name,
            boardDocument.subtitle,
            boardDocument.dimensions,
            boardDocument.productURL.absoluteString
        ]
        guard requiredStrings.allSatisfy({ !$0.isEmpty }) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardDocument.id,
                reason: "required metadata must not be empty"
            )
        }
        guard boardDocument.id.isBoardPackageIdentifier else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardDocument.id,
                reason: "board ID must be identifier-shaped"
            )
        }
        guard boardDocument.productURL.scheme == "https",
              boardDocument.productURL.host != nil else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardDocument.id,
                reason: "product URL must be absolute HTTPS"
            )
        }
        if boardDocument.presentation.assetPath.isEmpty {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardDocument.id,
                reason: "presentation asset path must not be empty"
            )
        }
    }

    private static func validatePresentationAssetPath(
        _ assetPath: String,
        boardID: String,
        in packageURL: URL
    ) throws {
        guard assetPath == "assets/primary.png" else {
            let resolvedPath = packageURL
                .appendingPathComponent(assetPath)
                .standardized
            let packageBase = packageURL.standardized.path
            if resolvedPath.path.hasPrefix("\(packageBase)/") {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "presentation.assetPath must be assets/primary.png"
                )
            }
            throw BoardPackageStoreError.presentationAssetPathEscape(
                boardID: boardID,
                path: assetPath
            )
        }
    }

    private static func validateHolds(
        in document: BoardPackageBoardDocument
    ) throws -> [BoardHold] {
        var holdIDs = Set<String>()
        var holds: [BoardHold] = []
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
            if let handCapacity = hold.handCapacity,
               !BoardHold.validHandCapacityRange.contains(handCapacity) {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid hand capacity"
                )
            }
            let geometryValidation = BoardHoldGeometryValidator.validate(
                hold.geometry.map(\.holdPieceDocument),
                holdID: hold.id,
                pieceID: { "\(hold.id)-piece-\($0)" }
            )
            guard !geometryValidation.isEmpty else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) geometry must include at least one piece"
                )
            }
            for (pieceIndex, pieceValidation) in geometryValidation.pieces.enumerated() {
                if let failureReason = pieceValidation.packageFailureReason {
                    throw BoardPackageStoreError.invalidPackage(
                        boardID: document.id,
                        reason: "hold \(hold.id) geometry[\(pieceIndex)] \(failureReason)"
                    )
                }
            }
            let geometryPieces = geometryValidation.pieces.compactMap(\.piece)
            guard geometryPieces.count == geometryValidation.pieces.count else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid geometry"
                )
            }
            holds.append(
                try hold.trainingBoardHold(geometryPieces: geometryPieces)
            )
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
        return holds
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
    let presentation: BoardPackagePresentationDocument
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
        presentation = try container.decode(
            BoardPackagePresentationDocument.self,
            forKey: .presentation
        )
        holds = try container.decode([BoardPackageHoldDocument].self, forKey: .holds)
    }

    func trainingBoard(holds: [BoardHold]) throws -> TrainingBoard {
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
            holds: holds,
            semanticHolds: [:],
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
    let geometry: [BoardPackageGeometryDocument]
    let sizeMillimeters: Int?
    let depthRangeMillimeters: BoardPackageMillimeterRangeDocument?
    let gripType: GripType?
    let fingerCapacity: Int?
    let handCapacity: Int?
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
        case handCapacity
        case features
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "id", "name", "kind", "geometry", "sizeMillimeters",
            "depthRangeMillimeters", "gripType", "fingerCapacity", "handCapacity", "features"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        kind = try container.decode(HoldKind.self, forKey: .kind)
        geometry = try container.decode([BoardPackageGeometryDocument].self, forKey: .geometry)
        sizeMillimeters = try container.decodeIfPresent(Int.self, forKey: .sizeMillimeters)
        depthRangeMillimeters = try container.decodeIfPresent(
            BoardPackageMillimeterRangeDocument.self,
            forKey: .depthRangeMillimeters
        )
        gripType = try container.decodeIfPresent(GripType.self, forKey: .gripType)
        fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        handCapacity = try container.decodeIfPresent(Int.self, forKey: .handCapacity)
        features = try container.decodeIfPresent([HoldFeature].self, forKey: .features)
    }

    func trainingBoardHold() throws -> BoardHold {
        guard !geometry.isEmpty else {
            throw BoardGeometryAdaptationError.invalid(
                "hold \(id) geometry must include at least one piece"
            )
        }
        return try trainingBoardHold(
            geometryPieces: geometry.enumerated().map { index, document in
                try document.boardHoldPiece(id: "\(id)-piece-\(index)", holdID: id)
            }
        )
    }

    func trainingBoardHold(geometryPieces: [BoardHoldPiece]) throws -> BoardHold {
        guard !geometryPieces.isEmpty else {
            throw BoardGeometryAdaptationError.invalid(
                "hold \(id) geometry must include at least one piece"
            )
        }
        return BoardHold(
            id: id,
            name: name,
            kind: kind,
            geometry: geometryPieces,
            sizeMillimeters: sizeMillimeters,
            gripType: gripType,
            fingerCapacity: fingerCapacity,
            handCapacity: handCapacity,
            depthRangeMillimeters: depthRangeMillimeters.map {
                $0.lowerBound...$0.upperBound
            },
            features: features.map(Set.init)
        )
    }
}

private struct BoardPackageGeometryDocument: Decodable {
    let frame: BoardPackageFrameDocument
    let shape: BoardGeometryShapeDocument
    let treatment: BoardGeometryTreatmentDocument?

    private enum CodingKeys: String, CodingKey {
        case frame
        case shape
        case treatment
        case shapeConstraint
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["frame", "shape", "treatment", "shapeConstraint"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        frame = try container.decode(BoardPackageFrameDocument.self, forKey: .frame)
        shape = try container.decode(BoardGeometryShapeDocument.self, forKey: .shape)
        treatment = try container.decodeIfPresent(
            BoardGeometryTreatmentDocument.self,
            forKey: .treatment
        )
        if container.contains(.shapeConstraint) {
            _ = try container.decode(
                BoardPackageShapeConstraintDocument.self,
                forKey: .shapeConstraint
            )
        }
    }

    func boardHoldPiece(id: String, holdID: String) throws -> BoardHoldPiece {
        try holdPieceDocument.boardHoldPiece(id: id, holdID: holdID)
    }

    var holdPieceDocument: BoardHoldPieceDocument {
        BoardHoldPieceDocument(
            frame: frame,
            shape: shape,
            treatment: treatment
        )
    }
}

private struct BoardPackageShapeConstraintDocument: Decodable {
    private enum Shape: String, Decodable {
        case oval
        case circle
        case pill
        case roundedRectangle
        case rectangle
    }

    private enum CodingKeys: String, CodingKey {
        case shape
        case rotationDegrees
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["shape", "rotationDegrees"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        _ = try container.decode(Shape.self, forKey: .shape)
        let rotationDegrees = try container.decode(Double.self, forKey: .rotationDegrees)
        guard rotationDegrees.isFinite, (-180..<180).contains(rotationDegrees) else {
            throw DecodingError.dataCorruptedError(
                forKey: .rotationDegrees,
                in: container,
                debugDescription: "rotationDegrees must be finite and in [-180, 180)"
            )
        }
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

    var isValid: Bool {
        x.isFinite && y.isFinite && width.isFinite && height.isFinite &&
            width > 0 && height > 0
    }
}

struct BoardGeometryShapeDocument: Codable, Hashable {
    let type: String
    let commands: [BoardGeometryPathCommandDocument]?
    let cornerRadiusFraction: Double?

    private enum CodingKeys: String, CodingKey {
        case type
        case commands
        case cornerRadiusFraction
    }

    init(
        type: String,
        commands: [BoardGeometryPathCommandDocument]?,
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
            commands = try container.decode([BoardGeometryPathCommandDocument].self, forKey: .commands)
            cornerRadiusFraction = nil
        default:
            try decoder.rejectUnknownKeys(["type", "commands", "cornerRadiusFraction"])
            commands = try container.decodeIfPresent(
                [BoardGeometryPathCommandDocument].self,
                forKey: .commands
            )
            cornerRadiusFraction = try container.decodeIfPresent(
                Double.self,
                forKey: .cornerRadiusFraction
            )
        }
    }

    var usesDeclaredFrame: Bool {
        guard type == "path", let commands else { return type == "roundedRect" }
        guard let pathCommands = try? commands.map({ try $0.boardPathCommand() }) else {
            return false
        }
        guard let points = try? pathCommands.flattenedContour() else { return false }
        let xValues = points.map { point in point.x }
        let yValues = points.map { point in point.y }
        let tolerance = 0.0000005
        return abs(xValues.min()!) <= tolerance && abs(yValues.min()!) <= tolerance &&
            abs(xValues.max()! - 1) <= tolerance &&
            abs(yValues.max()! - 1) <= tolerance
    }
}

struct BoardGeometryPathCommandDocument: Codable, Hashable {
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

struct BoardGeometryTreatmentDocument: Codable, Hashable {
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

enum BoardGeometryAdaptationError: Error, CustomStringConvertible {
    case invalid(String)

    var description: String {
        switch self {
        case .invalid(let reason): reason
        }
    }
}

extension BoardHoldPieceDocument {
    func boardHoldPiece(id: String, holdID: String) throws -> BoardHoldPiece {
        guard frame.isValid else {
            throw BoardGeometryAdaptationError.invalid(
                "hold piece \(id) has an invalid frame"
            )
        }
        return try BoardHoldPiece(
            id: id,
            holdID: holdID,
            frame: frame.cgRect,
            shape: shape.boardShape(),
            treatment: treatment.map {
                try $0.boardHoldTreatment(pieceID: id)
            } ?? .surface
        )
    }
}

private extension BoardGeometryShapeDocument {
    func boardShape() throws -> BoardShape {
        switch type {
        case "roundedRect":
            guard commands == nil,
                  let cornerRadiusFraction,
                  cornerRadiusFraction.isFinite,
                  (0...0.5).contains(cornerRadiusFraction) else {
                throw BoardGeometryAdaptationError.invalid(
                    "rounded rectangle shape is invalid"
                )
            }
            return .roundedRect(cornerRadiusFraction: CGFloat(cornerRadiusFraction))

        case "path":
            guard cornerRadiusFraction == nil,
                  let commands,
                  !commands.isEmpty,
                  commands.first?.command == "move",
                  commands.last?.command == "close",
                  commands.filter({ $0.command == "move" }).count == 1,
                  commands.filter({ $0.command == "close" }).count == 1 else {
                throw BoardGeometryAdaptationError.invalid(
                    "path must contain exactly one closed contour"
                )
            }
            let pathCommands = try commands.map { try $0.boardPathCommand() }
            try pathCommands.validateSimpleContour()
            return .path(
                BoardNormalizedPath(commands: pathCommands)
            )

        default:
            throw BoardGeometryAdaptationError.invalid("unsupported shape type \(type)")
        }
    }
}

private extension BoardGeometryPathCommandDocument {
    func boardPathCommand() throws -> BoardPathCommand {
        switch command {
        case "move":
            guard control == nil, control1 == nil, control2 == nil else {
                throw invalidCommand()
            }
            return .move(try point(to))
        case "line":
            guard control == nil, control1 == nil, control2 == nil else {
                throw invalidCommand()
            }
            return .line(try point(to))
        case "quad":
            guard control1 == nil, control2 == nil else { throw invalidCommand() }
            return .quad(to: try point(to), control: try controlPoint(control))
        case "curve":
            guard control == nil else { throw invalidCommand() }
            return .curve(
                to: try point(to),
                control1: try controlPoint(control1),
                control2: try controlPoint(control2)
            )
        case "close":
            guard to == nil, control == nil, control1 == nil, control2 == nil else {
                throw invalidCommand()
            }
            return .close
        default:
            throw invalidCommand()
        }
    }

    /// A point the curve actually passes through (move/line/quad-to/curve-to)
    /// must lie within the piece's own normalized frame.
    func point(_ coordinates: [Double]?) throws -> CGPoint {
        guard let coordinates,
              coordinates.count == 2,
              coordinates.allSatisfy({ $0.isFinite && (0...1).contains($0) }) else {
            throw invalidCommand()
        }
        return CGPoint(x: coordinates[0], y: coordinates[1])
    }

    /// A Bezier control point only shapes the curve between two points the
    /// curve passes through; it routinely falls outside the frame that
    /// tightly bounds the rendered curve, so only finiteness is required.
    func controlPoint(_ coordinates: [Double]?) throws -> CGPoint {
        guard let coordinates,
              coordinates.count == 2,
              coordinates.allSatisfy({ $0.isFinite }) else {
            throw invalidCommand()
        }
        return CGPoint(x: coordinates[0], y: coordinates[1])
    }

    func invalidCommand() -> BoardGeometryAdaptationError {
        .invalid("invalid \(command) path command")
    }
}

extension Array where Element == BoardPathCommand {
    func validateSimpleContour() throws {
        let points = try flattenedContour()
        guard points.count >= 4, points.first == points.last else {
            throw BoardGeometryAdaptationError.invalid("path must be a closed contour")
        }
        let quantizedPoints = try points.dropLast().map { point -> QuantizedBoardPoint in
            guard let quantized = QuantizedBoardPoint(point) else {
                throw BoardGeometryAdaptationError.invalid(
                    "path coordinates are too large to represent"
                )
            }
            return quantized
        }
        let uniquePoints = Set(quantizedPoints)
        guard uniquePoints.count >= 3 else {
            throw BoardGeometryAdaptationError.invalid(
                "path must contain at least three unique points"
            )
        }
        let segmentCount = points.count - 1
        for firstIndex in 0..<segmentCount {
            let first = points[firstIndex]
            let second = points[firstIndex + 1]
            guard !Self.samePoint(first, second) else {
                throw BoardGeometryAdaptationError.invalid(
                    "path contains a zero-length segment"
                )
            }
            for otherIndex in (firstIndex + 1)..<segmentCount {
                if otherIndex == firstIndex + 1 ||
                    (firstIndex == 0 && otherIndex == segmentCount - 1) {
                    continue
                }
                if Self.segmentsIntersect(
                    first,
                    second,
                    points[otherIndex],
                    points[otherIndex + 1]
                ) {
                    throw BoardGeometryAdaptationError.invalid(
                        "path must not self-intersect"
                    )
                }
            }
        }
        let signedArea = zip(points, points.dropFirst()).reduce(CGFloat.zero) {
            $0 + $1.0.x * $1.1.y - $1.1.x * $1.0.y
        } / 2
        guard abs(signedArea) > Self.contourEpsilon else {
            throw BoardGeometryAdaptationError.invalid("path must enclose area")
        }
    }

    fileprivate func flattenedContour() throws -> [CGPoint] {
        guard case .move(let start)? = first else {
            throw BoardGeometryAdaptationError.invalid("path must begin with move")
        }
        var current = start
        var points = [start]
        for command in dropFirst() {
            switch command {
            case .move:
                throw BoardGeometryAdaptationError.invalid(
                    "path must contain exactly one closed contour"
                )
            case .line(let destination):
                current = destination
                points.append(destination)
            case .quad(let destination, let control):
                let previous = current
                for step in 1...32 {
                    let t = CGFloat(step) / 32
                    let inverse = 1 - t
                    points.append(
                        CGPoint(
                            x: inverse * inverse * previous.x
                                + 2 * inverse * t * control.x
                                + t * t * destination.x,
                            y: inverse * inverse * previous.y
                                + 2 * inverse * t * control.y
                                + t * t * destination.y
                        )
                    )
                }
                current = destination
            case .curve(let destination, let control1, let control2):
                let previous = current
                for step in 1...32 {
                    let t = CGFloat(step) / 32
                    let inverse = 1 - t
                    points.append(
                        CGPoint(
                            x: inverse * inverse * inverse * previous.x
                                + 3 * inverse * inverse * t * control1.x
                                + 3 * inverse * t * t * control2.x
                                + t * t * t * destination.x,
                            y: inverse * inverse * inverse * previous.y
                                + 3 * inverse * inverse * t * control1.y
                                + 3 * inverse * t * t * control2.y
                                + t * t * t * destination.y
                        )
                    )
                }
                current = destination
            case .close:
                if current != start {
                    points.append(start)
                }
                current = start
            }
        }
        return points
    }

    private static let contourEpsilon = CGFloat(1e-9)

    private static func samePoint(_ lhs: CGPoint, _ rhs: CGPoint) -> Bool {
        abs(lhs.x - rhs.x) <= contourEpsilon &&
            abs(lhs.y - rhs.y) <= contourEpsilon
    }

    private static func segmentsIntersect(
        _ first: CGPoint,
        _ second: CGPoint,
        _ third: CGPoint,
        _ fourth: CGPoint
    ) -> Bool {
        let firstThird = orientation(first, second, third)
        let firstFourth = orientation(first, second, fourth)
        let thirdFirst = orientation(third, fourth, first)
        let thirdSecond = orientation(third, fourth, second)
        let crosses = ((firstThird > contourEpsilon && firstFourth < -contourEpsilon) ||
            (firstThird < -contourEpsilon && firstFourth > contourEpsilon)) &&
            ((thirdFirst > contourEpsilon && thirdSecond < -contourEpsilon) ||
                (thirdFirst < -contourEpsilon && thirdSecond > contourEpsilon))
        if crosses { return true }
        return [
            (firstThird, first, second, third),
            (firstFourth, first, second, fourth),
            (thirdFirst, third, fourth, first),
            (thirdSecond, third, fourth, second)
        ].contains { value, segmentStart, segmentEnd, point in
            abs(value) <= contourEpsilon &&
                onSegment(segmentStart, segmentEnd, point)
        }
    }

    private static func orientation(_ first: CGPoint, _ second: CGPoint, _ third: CGPoint) -> CGFloat {
        (second.x - first.x) * (third.y - first.y) -
            (second.y - first.y) * (third.x - first.x)
    }

    private static func onSegment(_ first: CGPoint, _ second: CGPoint, _ point: CGPoint) -> Bool {
        point.x >= Swift.min(first.x, second.x) - contourEpsilon &&
            point.x <= Swift.max(first.x, second.x) + contourEpsilon &&
            point.y >= Swift.min(first.y, second.y) - contourEpsilon &&
            point.y <= Swift.max(first.y, second.y) + contourEpsilon
    }
}

private struct QuantizedBoardPoint: Hashable {
    let x: Int64
    let y: Int64

    init?(_ point: CGPoint) {
        guard let x = Self.quantized(point.x), let y = Self.quantized(point.y) else {
            return nil
        }
        self.x = x
        self.y = y
    }

    /// `Int64(Double)` traps for values outside its representable range, and a
    /// Bezier control point (unlike a "to" point) is only required to be
    /// finite, so an oversized-but-finite control can flatten into a
    /// contour point that would otherwise trap here instead of failing
    /// validation.
    private static func quantized(_ value: CGFloat) -> Int64? {
        let scaled = (Double(value) * 1_000_000_000_000).rounded()
        guard scaled.isFinite, scaled >= -0x1p63, scaled < 0x1p63 else {
            return nil
        }
        return Int64(scaled)
    }
}

private extension BoardGeometryTreatmentDocument {
    func boardHoldTreatment(pieceID: String) throws -> BoardHoldTreatment {
        switch type {
        case "surface":
            guard rimInsetFraction == nil, depth == nil else {
                throw invalidTreatment(pieceID: pieceID)
            }
            return .surface
        case "shelf":
            guard depth == nil, let inset = try validatedInset(pieceID: pieceID) else {
                throw invalidTreatment(pieceID: pieceID)
            }
            return .shelf(BoardShelfProfile(rimInsetFraction: inset))
        case "recess":
            guard let inset = try validatedInset(pieceID: pieceID) else {
                throw invalidTreatment(pieceID: pieceID)
            }
            let recessDepth: BoardRecessDepth
            switch depth {
            case "deep": recessDepth = .deep
            case "shallow": recessDepth = .shallow
            default: throw invalidTreatment(pieceID: pieceID)
            }
            return .recess(
                BoardRecessProfile(rimInsetFraction: inset, depth: recessDepth)
            )
        default:
            throw invalidTreatment(pieceID: pieceID)
        }
    }

    func validatedInset(pieceID: String) throws -> CGFloat? {
        guard let rimInsetFraction else { return nil }
        guard rimInsetFraction.isFinite, (0...0.5).contains(rimInsetFraction) else {
            throw invalidTreatment(pieceID: pieceID)
        }
        return CGFloat(rimInsetFraction)
    }

    func invalidTreatment(pieceID: String) -> BoardGeometryAdaptationError {
        .invalid("hold piece \(pieceID) has an invalid \(type) treatment")
    }
}
