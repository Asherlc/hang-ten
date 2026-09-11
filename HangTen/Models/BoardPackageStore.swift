import Foundation
import ImageIO
import UniformTypeIdentifiers
import CryptoKit

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
    private let presentationURLsByBoardID: [String: [String: URL]]
    private let descriptorURLsByBoardID: [String: [String: URL]]

    init(bundle: Bundle = .main) throws {
        guard let resourceURL = bundle.resourceURL else {
            throw BoardPackageStoreError.missingLibrary
        }
        let hangboardsURL = resourceURL.appendingPathComponent("Hangboards", isDirectory: true)
        try Self.validateHangboardsRoot(hangboardsURL)
        var loadedBoards: [TrainingBoard] = []
        var loadedPresentationURLs: [String: [String: URL]] = [:]
        var loadedDescriptorURLs: [String: [String: URL]] = [:]
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
            try Self.validatePackageContainer(packageURL, boardID: slug)
            let resourcePrefix = "Hangboards/\(slug)"
            let loaded = try Self.loadV2Package(
                at: packageURL,
                resource: "\(resourcePrefix)/board.json"
            )
            guard seenBoardIDs.insert(loaded.board.id).inserted else {
                throw BoardPackageStoreError.duplicateBoardID(loaded.board.id)
            }
            loadedBoards.append(loaded.board)
            loadedPresentationURLs[loaded.board.id] = loaded.presentationURLs
            loadedDescriptorURLs[loaded.board.id] = loaded.descriptorURLs
        }

        loadedBoards.sort(by: Self.boardComesBefore)
        self.boards = loadedBoards
        self.boardsByID = Dictionary(uniqueKeysWithValues: loadedBoards.map { ($0.id, $0) })
        self.presentationURLsByBoardID = loadedPresentationURLs
        self.descriptorURLsByBoardID = loadedDescriptorURLs
    }

    func board(id: String) -> TrainingBoard? {
        boardsByID[id]
    }

    func semantics(for _: String) -> [String: [String]] {
        [:]
    }

    func presentationImageURL(
        for board: TrainingBoard,
        presentationID: String? = nil
    ) -> URL? {
        let resolvedID = presentationID ?? board.defaultPresentation.id
        guard case .raster = board.presentation(id: resolvedID)?.media else { return nil }
        return presentationURLsByBoardID[board.id]?[resolvedID]
    }

    func presentationAssetURL(
        for board: TrainingBoard,
        presentationID: String? = nil
    ) -> URL? {
        let resolvedID = presentationID ?? board.defaultPresentation.id
        return presentationURLsByBoardID[board.id]?[resolvedID]
    }

    func presentationDescriptorURL(
        for board: TrainingBoard,
        presentationID: String? = nil
    ) -> URL? {
        let resolvedID = presentationID ?? board.defaultPresentation.id
        return descriptorURLsByBoardID[board.id]?[resolvedID]
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

    private static func validatePackageContainer(
        _ packageURL: URL,
        boardID: String
    ) throws {
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
    }

    private static func regularFilePaths(
        below rootURL: URL,
        relativeTo packageURL: URL,
        boardID: String
    ) throws -> Set<String> {
        guard let enumerator = FileManager.default.enumerator(
            at: rootURL,
            includingPropertiesForKeys: [.isRegularFileKey, .isDirectoryKey, .isSymbolicLinkKey],
            options: []
        ) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "assets cannot be enumerated"
            )
        }
        let packagePrefix = packageURL.standardizedFileURL.path + "/"
        var paths = Set<String>()
        for case let itemURL as URL in enumerator {
            let values = try itemURL.resourceValues(
                forKeys: [.isRegularFileKey, .isDirectoryKey, .isSymbolicLinkKey]
            )
            guard values.isSymbolicLink != true else {
                throw BoardPackageStoreError.packagePathEscape(
                    boardID: boardID,
                    path: itemURL.path
                )
            }
            if values.isDirectory == true { continue }
            guard values.isRegularFile == true,
                  itemURL.standardizedFileURL.path.hasPrefix(packagePrefix) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: boardID,
                    reason: "assets must contain only regular files and directories"
                )
            }
            paths.insert(String(itemURL.standardizedFileURL.path.dropFirst(packagePrefix.count)))
        }
        return paths
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

    private static func loadV2Package(
        at packageURL: URL,
        resource: String
    ) throws -> (
        board: TrainingBoard,
        presentationURLs: [String: URL],
        descriptorURLs: [String: URL]
    ) {
        let boardURL = packageURL.appendingPathComponent("board.json")
        let document: BoardPackageV2BoardDocument
        let rawRasterGeometryByPresentationID: [String: BoardPackageRawJSONValue]
        do {
            let data = try Data(contentsOf: boardURL)
            document = try JSONDecoder().decode(BoardPackageV2BoardDocument.self, from: data)
            var rawParser = BoardPackageRawJSONParser(data: data)
            let rawDocument = try rawParser.parseDocument()
            try rawDocument.validateTwoBranchSuspensionMemberOrder()
            rawRasterGeometryByPresentationID = try rawDocument.rasterGeometryByPresentationID()
        } catch {
            throw BoardPackageStoreError.malformedJSON(resource: resource)
        }
        guard document.schemaVersion == 2 else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "schemaVersion must be 2"
            )
        }
        guard document.id.isBoardPackageIdentifier,
              !document.manufacturer.isEmpty,
              !document.name.isEmpty,
              !document.subtitle.isEmpty,
              document.productURL.scheme == "https",
              document.productURL.host != nil,
              document.aspectRatio.isFinite,
              document.aspectRatio > 0 else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "required metadata must be valid"
            )
        }
        if let dimensions = document.dimensions, dimensions.isEmpty {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "dimensions must not be empty when present"
            )
        }
        guard !document.equipmentObjects.isEmpty else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "equipmentObjects must not be empty"
            )
        }
        var equipmentObjectIDs = Set<String>()
        for object in document.equipmentObjects {
            guard object.id.isBoardPackageIdentifier,
                  equipmentObjectIDs.insert(object.id).inserted else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "equipment object IDs must be unique and identifier-shaped"
                )
            }
        }

        guard !document.holds.isEmpty else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "holds must not be empty"
            )
        }
        var holdIDs = Set<String>()
        var holds: [BoardHold] = []
        for hold in document.holds {
            guard hold.id.isBoardPackageIdentifier,
                  !hold.name.isEmpty,
                  holdIDs.insert(hold.id).inserted else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "logical hold IDs must be unique and identifier-shaped"
                )
            }
            guard equipmentObjectIDs.contains(hold.equipmentObjectID) else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) references unknown equipment object \(hold.equipmentObjectID)"
                )
            }
            if hold.sloper != nil && hold.kind != .sloper {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has sloper metadata but is not a sloper"
                )
            }
            if hold.sizeMillimeters != nil && hold.depthRangeMillimeters != nil {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) must not specify both a size and depth range"
                )
            }
            if let size = hold.sizeMillimeters, !size.isFinite || size <= 0 {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has a non-positive size"
                )
            }
            if let range = hold.depthRangeMillimeters,
               !range.lowerBound.isFinite || !range.upperBound.isFinite ||
               range.lowerBound <= 0 || range.upperBound <= 0 ||
               range.lowerBound > range.upperBound {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid depth range"
                )
            }
            if let capacity = hold.fingerCapacity,
               !BoardHold.validFingerCapacityRange.contains(capacity) {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid finger capacity"
                )
            }
            if let capacity = hold.handCapacity,
               !BoardHold.validHandCapacityRange.contains(capacity) {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has an invalid hand capacity"
                )
            }
            if let features = hold.features, Set(features).count != features.count {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "hold \(hold.id) has duplicate features"
                )
            }
            if hold.kind == .gaston {
                guard let pairedHoldID = hold.pairedHoldID,
                      pairedHoldID.isBoardPackageIdentifier else {
                    throw BoardPackageStoreError.invalidPackage(
                        boardID: document.id,
                        reason: "gaston hold \(hold.id) must declare a pairedHoldID"
                    )
                }
            } else if hold.declaresPairedHoldID {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "non-gaston hold \(hold.id) must not declare pairedHoldID"
                )
            }
            holds.append(
                BoardHold(
                    id: hold.id,
                    equipmentObjectID: hold.equipmentObjectID,
                    name: hold.name,
                    kind: hold.kind,
                    sloper: hold.sloper,
                    sizeMillimeters: hold.sizeMillimeters,
                    gripType: hold.gripType,
                    fingerCapacity: hold.fingerCapacity,
                    handCapacity: hold.handCapacity,
                    depthRangeMillimeters: hold.depthRangeMillimeters.map {
                        $0.lowerBound...$0.upperBound
                    },
                    features: hold.features.map(Set.init),
                    pairedHoldID: hold.pairedHoldID
                )
            )
        }
        let holdDocumentsByID = Dictionary(uniqueKeysWithValues: document.holds.map { ($0.id, $0) })
        for hold in document.holds where hold.kind == .gaston {
            guard let pairedID = hold.pairedHoldID,
                  pairedID != hold.id,
                  let paired = holdDocumentsByID[pairedID],
                  paired.kind == .gaston,
                  paired.pairedHoldID == hold.id else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "gaston hold \(hold.id) must have a reciprocal gaston pair"
                )
            }
        }
        for objectID in equipmentObjectIDs where !holds.contains(where: { $0.equipmentObjectID == objectID }) {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "equipment object \(objectID) must own at least one hold"
            )
        }

        guard !document.presentations.isEmpty else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "presentations must not be empty"
            )
        }
        var presentationIDs = Set<String>()
        var defaultCount = 0
        var hasRaster = false
        var hasModel = false
        var declaredAssetPaths = Set<String>()
        for presentation in document.presentations {
            guard presentation.id.isBoardPackageIdentifier,
                  !presentation.name.isEmpty,
                  presentation.aspectRatio.isFinite,
                  presentation.aspectRatio > 0,
                  presentationIDs.insert(presentation.id).inserted else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "presentation metadata must be unique and valid"
                )
            }
            if presentation.isDefault { defaultCount += 1 }
            switch presentation.media {
            case .raster(let assetPath, _):
                hasRaster = true
                try validateV2AssetPath(assetPath, suffix: ".png", boardID: document.id, packageURL: packageURL)
                declaredAssetPaths.insert(assetPath)
            case .model(let assetPath, let descriptorPath, let display, _):
                hasModel = true
                guard case .original = presentation.derivation else {
                    throw BoardPackageStoreError.invalidPackage(
                        boardID: document.id,
                        reason: "model media may not be derived or inverted"
                    )
                }
                try validateV2AssetPath(assetPath, suffix: ".usdz", boardID: document.id, packageURL: packageURL)
                try validateV2AssetPath(descriptorPath, suffix: ".model.json", boardID: document.id, packageURL: packageURL)
                try validateModelDisplay(display, boardID: document.id)
                declaredAssetPaths.formUnion([assetPath, descriptorPath])
            }
        }
        guard defaultCount == 1 else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "presentations must contain exactly one default"
            )
        }
        guard !(hasRaster && hasModel) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "v2 packages may not mix model and raster presentations"
            )
        }
        guard document.presentations.filter({
            if case .model = $0.media { return true }
            return false
        }).count <= 1 else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "v2 packages may contain only one model presentation"
            )
        }
        let documentsByPresentationID = Dictionary(
            uniqueKeysWithValues: document.presentations.map { ($0.id, $0) }
        )
        var derivedRasterSources: [(derivedID: String, sourceID: String)] = []
        for presentation in document.presentations {
            guard case .derived(let sourceID, _) = presentation.derivation else { continue }
            guard sourceID != presentation.id,
                  sourceID.isBoardPackageIdentifier,
                  let source = documentsByPresentationID[sourceID],
                  case .original = source.derivation,
                  case .raster = presentation.media,
                  case .raster = source.media else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "derived presentation relationships must be raster to raster"
                )
            }
            derivedRasterSources.append((presentation.id, sourceID))
        }

        let assetsURL = packageURL.appendingPathComponent("assets", isDirectory: true)
        let actualAssetPaths = try regularFilePaths(
            below: assetsURL,
            relativeTo: packageURL,
            boardID: document.id
        )
        guard actualAssetPaths == declaredAssetPaths else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "assets must contain exactly the declared presentation assets"
            )
        }
        for path in declaredAssetPaths {
            let url = packageURL.appendingPathComponent(path)
            guard try isRegularFile(url), FileManager.default.isReadableFile(atPath: url.path) else {
                throw BoardPackageStoreError.missingPresentationAsset(boardID: document.id, path: path)
            }
        }

        var presentations: [BoardPresentation] = []
        var presentationURLs: [String: URL] = [:]
        var descriptorURLs: [String: URL] = [:]
        var originalRasterOwnershipCounts = Dictionary(
            uniqueKeysWithValues: holdIDs.map { ($0, 0) }
        )
        let declaredPositionIDs = Set(
            (document.positions?.map(\.id) ?? document.presentations.map(\.id))
        )
        for presentation in document.presentations {
            let media: BoardPresentationMedia
            switch presentation.media {
            case .raster(let assetPath, let geometryDocuments):
                let presentationHoldIDs = Set(geometryDocuments.keys)
                guard !presentationHoldIDs.isEmpty else {
                    throw BoardPackageStoreError.invalidPackage(
                        boardID: document.id,
                        reason: "presentation \(presentation.id) media.holdGeometry must own at least one logical hold"
                    )
                }
                guard presentationHoldIDs.isSubset(of: holdIDs) else {
                    throw BoardPackageStoreError.invalidPackage(
                        boardID: document.id,
                        reason: "presentation \(presentation.id) media.holdGeometry must own only logical holds"
                    )
                }
                if case .original = presentation.derivation {
                    for holdID in presentationHoldIDs {
                        originalRasterOwnershipCounts[holdID, default: 0] += 1
                    }
                }
                var holdGeometry: [String: [BoardHoldPiece]] = [:]
                for holdID in presentationHoldIDs.sorted() {
                    let geometry = geometryDocuments[holdID] ?? []
                    let validation = BoardHoldGeometryValidator.validate(
                        geometry.map(\.holdPieceDocument),
                        holdID: holdID,
                        pieceID: { "\(holdID)-piece-\($0)" }
                    )
                    guard !validation.isEmpty,
                          validation.pieces.allSatisfy({ $0.packageFailureReason == nil }),
                          validation.pieces.compactMap(\.piece).count == validation.pieces.count else {
                        let failures = validation.pieces.compactMap(\.packageFailureReason).joined(separator: "; ")
                        throw BoardPackageStoreError.invalidPackage(
                            boardID: document.id,
                            reason: "presentation \(presentation.id) has invalid holdGeometry for \(holdID): \(failures)"
                        )
                    }
                    holdGeometry[holdID] = validation.pieces.compactMap(\.piece)
                }
                let imageSize = try validatePNG(
                    at: packageURL.appendingPathComponent(assetPath),
                    boardID: document.id,
                    label: assetPath
                )
                try validatePresentationAspectRatio(
                    presentation.aspectRatio,
                    imageWidth: imageSize.width,
                    imageHeight: imageSize.height,
                    boardID: document.id
                )
                if presentation.isDefault {
                    try validatePresentationAspectRatio(
                        document.aspectRatio,
                        imageWidth: imageSize.width,
                        imageHeight: imageSize.height,
                        boardID: document.id
                    )
                }
                media = .raster(BoardRasterMedia(assetPath: assetPath, holdGeometry: holdGeometry))
            case .model(let assetPath, let descriptorPath, let displayDocument, let suspensionDocument):
                let descriptor = try loadModelDescriptor(
                    at: packageURL.appendingPathComponent(descriptorPath),
                    modelURL: packageURL.appendingPathComponent(assetPath),
                    logicalHoldIDs: holdIDs,
                    boardID: document.id,
                    resource: descriptorPath,
                    suspensionDocument: suspensionDocument
                )
                let suspension = try suspensionDocument.map {
                    try makeModelSuspension(
                        $0,
                        descriptor: descriptor,
                        positionIDs: declaredPositionIDs,
                        boardID: document.id
                    )
                }
                let camera = displayDocument.camera
                media = .model(
                    BoardModelMedia(
                        assetPath: assetPath,
                        descriptorPath: descriptorPath,
                        descriptor: descriptor,
                        display: BoardModelDisplay(
                            camera: BoardModelCamera(
                                type: camera.type,
                                viewDirection: camera.viewDirection,
                                up: camera.up,
                                fitPadding: camera.fitPadding
                            )
                        ),
                        suspension: suspension
                    )
                )
                descriptorURLs[presentation.id] = packageURL.appendingPathComponent(descriptorPath)
            }
            let sourceID: String?
            let inverted: Bool
            switch presentation.derivation {
            case .original:
                sourceID = nil
                inverted = false
            case .derived(let value, let isInverted):
                sourceID = value
                inverted = isInverted
            }
            presentations.append(
                BoardPresentation(
                    id: presentation.id,
                    name: presentation.name,
                    aspectRatio: presentation.aspectRatio,
                    isDefault: presentation.isDefault,
                    sourcePresentationID: sourceID,
                    isInverted: inverted,
                    media: media
                )
            )
            presentationURLs[presentation.id] = packageURL.appendingPathComponent(presentation.media.assetPath)
        }

        if hasRaster && originalRasterOwnershipCounts.values.contains(where: { $0 != 1 }) {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "v2 original raster media.holdGeometry must own every logical hold exactly once"
            )
        }
        for relationship in derivedRasterSources {
            guard rawRasterGeometryByPresentationID[relationship.derivedID]
                    == rawRasterGeometryByPresentationID[relationship.sourceID] else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "derived presentation \(relationship.derivedID) media.holdGeometry must exactly equal its source geometry"
                )
            }
        }

        let positions = document.positions?.map(\.boardPosition) ?? presentations.map {
            BoardPosition(id: $0.id, presentationID: $0.id)
        }
        guard !positions.isEmpty,
              Set(positions.map(\.id)).count == positions.count,
              positions.allSatisfy({ $0.id.isBoardPackageIdentifier && presentationIDs.contains($0.presentationID) }) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: document.id,
                reason: "positions must be unique and reference presentations"
            )
        }
        let transitions = document.positionTransitions?.map(\.boardPositionTransition) ?? []
        let positionIDs = Set(positions.map(\.id))
        var transitionPairs = Set<[String]>()
        for transition in transitions {
            guard positionIDs.contains(transition.fromPositionID),
                  positionIDs.contains(transition.toPositionID),
                  transition.fromPositionID != transition.toPositionID,
                  transitionPairs.insert([transition.fromPositionID, transition.toPositionID]).inserted else {
                throw BoardPackageStoreError.invalidPackage(
                    boardID: document.id,
                    reason: "position transitions must be unique non-self edges"
                )
            }
        }
        let board = TrainingBoard(
            id: document.id,
            manufacturer: document.manufacturer,
            name: document.name,
            subtitle: document.subtitle,
            dimensions: document.dimensions,
            aspectRatio: document.aspectRatio,
            equipmentObjects: document.equipmentObjects.map(\.equipmentObject),
            holds: holds,
            semanticHolds: [:],
            productURL: document.productURL,
            photoAssetName: nil,
            presentations: presentations,
            positions: positions,
            positionTransitions: transitions
        )
        return (board, presentationURLs, descriptorURLs)
    }

    private static func validateV2AssetPath(
        _ path: String,
        suffix: String,
        boardID: String,
        packageURL: URL
    ) throws {
        let components = path.split(separator: "/", omittingEmptySubsequences: false)
        let valid = components.count >= 2 && components.first == "assets" &&
            !path.hasPrefix("/") && !path.contains("\\") &&
            !components.contains(where: { $0.isEmpty || $0 == "." || $0 == ".." }) &&
            path.hasSuffix(suffix)
        guard valid else {
            let resolved = packageURL.appendingPathComponent(path).standardizedFileURL.path
            if !resolved.hasPrefix(packageURL.standardizedFileURL.path + "/") {
                throw BoardPackageStoreError.presentationAssetPathEscape(boardID: boardID, path: path)
            }
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "typed presentation asset path is invalid"
            )
        }
    }

    private static func validateModelDisplay(
        _ display: BoardPackageModelDisplayDocument,
        boardID: String
    ) throws {
        let camera = display.camera
        guard camera.type == "orthographic",
              camera.viewDirection.count == 3,
              camera.up.count == 3,
              camera.viewDirection.allSatisfy(\.isFinite),
              camera.up.allSatisfy(\.isFinite),
              camera.viewDirection.contains(where: { $0 != 0 }),
              camera.up.contains(where: { $0 != 0 }),
              camera.fitPadding.isFinite,
              camera.fitPadding > 0 else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "model camera must be finite, orthographic, non-zero, and positively padded"
            )
        }
    }

    private static func loadModelDescriptor(
        at url: URL,
        modelURL: URL,
        logicalHoldIDs: Set<String>,
        boardID: String,
        resource: String,
        suspensionDocument: BoardPackageSuspensionDocument?
    ) throws -> BoardModelDescriptor {
        let data: Data
        let modelData: Data
        let document: BoardPackageModelDescriptorDocument
        let orderedHoldIDs: [String]
        do {
            data = try Data(contentsOf: url)
            modelData = try Data(contentsOf: modelURL)
            var rawDescriptorParser = BoardPackageRawJSONParser(data: data)
            _ = try rawDescriptorParser.parseDocument()
            var memberOrder = BoardPackageJSONMemberOrder(data: data)
            orderedHoldIDs = try memberOrder.memberNames(inRootObjectNamed: "holds")
            document = try JSONDecoder().decode(BoardPackageModelDescriptorDocument.self, from: data)
        } catch {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "model descriptor is missing or malformed: \(resource)"
            )
        }
        guard document.schemaVersion == 1,
              document.coordinateFrame == "hang-ten-board-v1",
              document.modelSHA256.count == 64,
              document.modelSHA256.allSatisfy({ ("0"..."9").contains(String($0)) || ("a"..."f").contains(String($0)) }) else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor header is invalid")
        }
        let actualHash = SHA256.hash(data: modelData).map { String(format: "%02x", $0) }.joined()
        guard actualHash == document.modelSHA256 else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor SHA-256 does not match USDZ bytes")
        }
        try validateDescriptorVector(document.modelBounds.minimum, length: 3, boardID: boardID)
        try validateDescriptorVector(document.modelBounds.maximum, length: 3, boardID: boardID)
        guard zip(document.modelBounds.minimum, document.modelBounds.maximum).allSatisfy({ $0 <= $1 }) else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model bounds minimum exceeds maximum")
        }
        let spans = zip(document.modelBounds.minimum.prefix(2), document.modelBounds.maximum.prefix(2)).map { $1 - $0 }
        guard spans.allSatisfy({ $0.isFinite && $0 > 0 }) else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model bounds face span must be finite and positive")
        }
        guard !document.nodes.isEmpty,
              document.nodes.map(\.nodeID) == document.nodes.map(\.nodeID).sorted(),
              Set(document.nodes.map(\.nodeID)).count == document.nodes.count else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor node IDs must be unique and sorted")
        }
        var nodes: [BoardModelNodeDescriptor] = []
        var bodyCount = 0
        var attachmentCount = 0
        var nodeIDsByHold: [String: [String]] = [:]
        for node in document.nodes {
            guard !node.nodeID.isEmpty else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor nodeID must not be empty")
            }
            switch node.role {
            case "body":
                bodyCount += 1
                nodes.append(.init(nodeID: node.nodeID, role: .body, holdID: nil))
            case "hold":
                guard let holdID = node.holdID,
                      holdID.isBoardPackageIdentifier else {
                    throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor hold node has invalid holdID")
                }
                nodeIDsByHold[holdID, default: []].append(node.nodeID)
                nodes.append(.init(nodeID: node.nodeID, role: .hold, holdID: holdID))
            case "attachment":
                guard node.holdID == nil else {
                    throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor attachment node may not declare holdID")
                }
                let maximumAttachmentCount: Int = {
                    guard let suspension = suspensionDocument else { return 1 }
                    if case .twoBranchCord = suspension { return 4 }
                    return 1
                }()
                attachmentCount += 1
                guard attachmentCount <= maximumAttachmentCount else {
                    throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor has too many attachment nodes")
                }
                nodes.append(.init(nodeID: node.nodeID, role: .attachment, holdID: nil))
            default:
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor role must be body, hold, or attachment")
            }
        }
        guard bodyCount == 1, Set(nodeIDsByHold.keys) == logicalHoldIDs,
              Set(document.holds.keys) == logicalHoldIDs else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor inventory must equal logical holds")
        }
        guard orderedHoldIDs == orderedHoldIDs.sorted() else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "model descriptor hold IDs must be sorted"
            )
        }
        var holds: [String: BoardModelHoldDescriptor] = [:]
        for holdID in logicalHoldIDs.sorted() {
            guard let hold = document.holds[holdID] else { continue }
            let expectedNodes = (nodeIDsByHold[holdID] ?? []).sorted()
            guard !hold.nodeIDs.isEmpty, hold.nodeIDs == expectedNodes else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor hold nodeIDs do not match bound nodes")
            }
            try validateDescriptorVector(hold.facePlaneAABB.minimum, length: 2, boardID: boardID)
            try validateDescriptorVector(hold.facePlaneAABB.maximum, length: 2, boardID: boardID)
            try validateDescriptorVector(hold.center, length: 2, boardID: boardID)
            guard zip(hold.facePlaneAABB.minimum, hold.facePlaneAABB.maximum).allSatisfy({
                $0 >= 0 && $0 <= $1 && $1 <= 1
            }) else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor facePlaneAABB must be normalized")
            }
            let expectedCenter = zip(hold.facePlaneAABB.minimum, hold.facePlaneAABB.maximum).map {
                boardDescriptorRoundedToNinePlaces($0 + ($1 - $0) / 2)
            }
            guard hold.center == expectedCenter else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "model descriptor center must derive from facePlaneAABB")
            }
            holds[holdID] = BoardModelHoldDescriptor(
                nodeIDs: hold.nodeIDs,
                facePlaneAABB: BoardModelFacePlaneAABB(
                    minimum: hold.facePlaneAABB.minimum,
                    maximum: hold.facePlaneAABB.maximum
                ),
                center: hold.center
            )
        }
        return BoardModelDescriptor(
            schemaVersion: document.schemaVersion,
            coordinateFrame: document.coordinateFrame,
            modelSHA256: document.modelSHA256,
            modelBounds: BoardModelBounds(
                minimum: document.modelBounds.minimum,
                maximum: document.modelBounds.maximum
            ),
            nodes: nodes,
            holds: holds
        )
    }

    private static func validateDescriptorVector(
        _ vector: [Double],
        length: Int,
        boardID: String
    ) throws {
        guard vector.count == length,
              vector.allSatisfy({ $0.isFinite && boardDescriptorRoundedToNinePlaces($0) == $0 }) else {
            throw BoardPackageStoreError.invalidPackage(
                boardID: boardID,
                reason: "model descriptor vectors must be finite, fixed-size, and rounded to nine decimals"
            )
        }
    }

    private static func makeModelSuspension(
        _ document: BoardPackageSuspensionDocument,
        descriptor: BoardModelDescriptor,
        positionIDs: Set<String>,
        boardID: String
    ) throws -> BoardModelSuspension {
        switch document {
        case .singleCord(let single):
            return try makeSingleCordSuspension(single, descriptor: descriptor, positionIDs: positionIDs, boardID: boardID)
        case .twoBranchCord(let twoBranch):
            return try makeTwoBranchSuspension(twoBranch, descriptor: descriptor, positionIDs: positionIDs, boardID: boardID)
        case .unsupported(let type):
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "suspension type must be singleCord or twoBranchCord: \(type)")
        case .shapeMismatch(let type):
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "suspension type \(type) does not match its members")
        }
    }

    private static func makeSingleCordSuspension(
        _ document: BoardPackageSingleCordSuspensionDocument,
        descriptor: BoardModelDescriptor,
        positionIDs: Set<String>,
        boardID: String
    ) throws -> BoardModelSuspension {
        guard document.attachment.nodeID.isEmpty == false,
              document.attachment.pointInModel.count == 3,
              document.attachment.pointInModel.allSatisfy(\.isFinite),
              zip(document.attachment.pointInModel, descriptor.modelBounds.minimum).allSatisfy({ $0 >= $1 }),
              zip(document.attachment.pointInModel, descriptor.modelBounds.maximum).allSatisfy({ $0 <= $1 }) else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "suspension attachment point must be finite and inside model bounds")
        }
        let nodeRole = descriptor.nodes.first(where: { $0.nodeID == document.attachment.nodeID })?.role
        guard nodeRole == .body || nodeRole == .attachment else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "suspension attachment node must be a body or attachment node")
        }
        guard document.anchor.offsetFromBoardBounds.count == 3,
              document.anchor.offsetFromBoardBounds.allSatisfy(\.isFinite),
              document.anchor.visibility == "invisible",
              document.cord.restLength.isFinite, document.cord.restLength > 0,
              document.cord.radius.isFinite, document.cord.radius > 0,
              document.canonicalPoses.count == positionIDs.count,
              Set(document.canonicalPoses.keys) == positionIDs else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "invalid suspension anchor, cord, or canonical pose set")
        }
        let bounds = descriptor.modelBounds
        let offset = document.anchor.offsetFromBoardBounds
        let anchorPosition = [
            (bounds.minimum[0] + bounds.maximum[0]) / 2 + offset[0],
            bounds.maximum[1] + offset[1],
            (bounds.minimum[2] + bounds.maximum[2]) / 2 + offset[2]
        ]
        guard anchorPosition.allSatisfy(\.isFinite) else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "suspension anchor must be finite")
        }
        var poses: [String: BoardModelCanonicalPose] = [:]
        for (positionID, pose) in document.canonicalPoses {
            guard pose.rotation.count == 4,
                  pose.rotation.allSatisfy(\.isFinite),
                  pose.translation.count == 3,
                  pose.translation.allSatisfy(\.isFinite),
                  pose.camera.viewDirection.count == 3,
                  pose.camera.viewDirection.allSatisfy(\.isFinite),
                  pose.camera.viewDirection.contains(where: { $0 != 0 }),
                  pose.camera.fitPadding.isFinite,
                  pose.camera.fitPadding > 0 else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "canonical pose \(positionID) is not finite")
            }
            let norm = sqrt(pose.rotation.reduce(0) { $0 + $1 * $1 })
            guard abs(norm - 1) <= 1e-6 else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "canonical pose \(positionID) rotation must be normalized")
            }
            let qx = pose.rotation[0], qy = pose.rotation[1], qz = pose.rotation[2], qw = pose.rotation[3]
            let p = document.attachment.pointInModel
            let tx = 2 * (qy * p[2] - qz * p[1])
            let ty = 2 * (qz * p[0] - qx * p[2])
            let tz = 2 * (qx * p[1] - qy * p[0])
            let transformed = [
                p[0] + qw * tx + (qy * tz - qz * ty) + pose.translation[0],
                p[1] + qw * ty + (qz * tx - qx * tz) + pose.translation[1],
                p[2] + qw * tz + (qx * ty - qy * tx) + pose.translation[2]
            ]
            let endpointDistance = zip(transformed, anchorPosition).reduce(0) { partial, pair in
                partial + (pair.0 - pair.1) * (pair.0 - pair.1)
            }.squareRoot()
            guard endpointDistance.isFinite,
                  document.cord.restLength >= endpointDistance - 1e-5 else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "suspension pose \(positionID) restLength is shorter than endpoint distance")
            }
            poses[positionID] = BoardModelCanonicalPose(
                rotation: pose.rotation,
                translation: pose.translation,
                camera: BoardModelCanonicalCamera(
                    viewDirection: pose.camera.viewDirection,
                    fitPadding: pose.camera.fitPadding
                )
            )
        }
        return .singleCord(BoardModelSingleCordSuspension(
            attachment: BoardModelAttachment(
                nodeID: document.attachment.nodeID,
                pointInModel: document.attachment.pointInModel,
                provenance: document.attachment.provenance
            ),
            anchor: BoardModelInvisibleAnchor(
                offsetFromBoardBounds: document.anchor.offsetFromBoardBounds,
                visibility: document.anchor.visibility,
                provenance: document.anchor.provenance,
                position: anchorPosition
            ),
            cord: BoardModelCord(
                restLength: document.cord.restLength,
                radius: document.cord.radius,
                material: document.cord.material,
                provenance: document.cord.provenance
            ),
            canonicalPoses: poses
        ))
    }

    private static func makeTwoBranchSuspension(
        _ document: BoardPackageTwoBranchSuspensionDocument,
        descriptor: BoardModelDescriptor,
        positionIDs: Set<String>,
        boardID: String
    ) throws -> BoardModelSuspension {
        guard document.passages.left.count == 2,
              document.passages.right.count == 2 else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord suspension requires exactly two passages per side")
        }
        let passages = document.passages.left + document.passages.right
        guard Set(passages.map(\.id)).count == passages.count else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord passage IDs must be distinct")
        }
        guard Set(passages.map(\.nodeID)).count == passages.count else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord passage node IDs must be distinct")
        }
        let nodesByID = Dictionary(uniqueKeysWithValues: descriptor.nodes.map { ($0.nodeID, $0) })
        for passage in passages {
            guard let node = nodesByID[passage.nodeID], node.role == .body || node.role == .attachment else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord passage node must be a body or attachment node")
            }
            guard passage.pointInModel.count == 3,
                  passage.pointInModel.allSatisfy(\.isFinite),
                  zip(passage.pointInModel, descriptor.modelBounds.minimum).allSatisfy({ $0 >= $1 }),
                  zip(passage.pointInModel, descriptor.modelBounds.maximum).allSatisfy({ $0 <= $1 }) else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord passage point must be finite and inside model bounds")
            }
        }
        guard document.branches.count == 2,
              document.branches[0].passageIDs == document.passages.left.map(\.id),
              document.branches[1].passageIDs == document.passages.right.map(\.id),
              Set(document.branches.map(\.id)).count == document.branches.count else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord branches must be two distinct ordered passage pairs")
        }
        guard document.branches.allSatisfy({
            $0.passageIDs.count == 2 && $0.restLength.isFinite && $0.restLength > 0 &&
            $0.radius.isFinite && $0.radius > 0 && !$0.material.isEmpty
        }) else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord branches have invalid cord parameters")
        }
        guard document.anchor.offsetFromBoardBounds.count == 3,
              document.anchor.offsetFromBoardBounds.allSatisfy(\.isFinite),
              document.anchor.visibility == "invisible",
              document.canonicalPoses.count == positionIDs.count,
              Set(document.canonicalPoses.keys) == positionIDs else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "invalid twoBranchCord anchor or canonical pose set")
        }
        let bounds = descriptor.modelBounds
        let offset = document.anchor.offsetFromBoardBounds
        let anchorPosition = [
            (bounds.minimum[0] + bounds.maximum[0]) / 2 + offset[0],
            bounds.maximum[1] + offset[1],
            (bounds.minimum[2] + bounds.maximum[2]) / 2 + offset[2]
        ]
        guard anchorPosition.allSatisfy(\.isFinite) else {
            throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord anchor must be finite")
        }
        for (positionID, pose) in document.canonicalPoses {
            guard pose.rotation.count == 4, pose.rotation.allSatisfy(\.isFinite),
                  pose.translation.count == 3, pose.translation.allSatisfy(\.isFinite),
                  pose.camera.viewDirection.count == 3, pose.camera.viewDirection.allSatisfy(\.isFinite),
                  pose.camera.viewDirection.contains(where: { $0 != 0 }),
                  pose.camera.fitPadding.isFinite, pose.camera.fitPadding > 0 else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "canonical pose \(positionID) is not finite")
            }
            let norm = sqrt(pose.rotation.reduce(0) { $0 + $1 * $1 })
            guard abs(norm - 1) <= 1e-6 else {
                throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "canonical pose \(positionID) rotation must be normalized")
            }
            for (branchIndex, branch) in document.branches.enumerated() {
                let side = branchIndex == 0 ? document.passages.left : document.passages.right
                var transformedEndpoints: [[Double]] = []
                for passage in side {
                    let p = passage.pointInModel
                    let qx = pose.rotation[0], qy = pose.rotation[1], qz = pose.rotation[2], qw = pose.rotation[3]
                    let tx = 2 * (qy * p[2] - qz * p[1])
                    let ty = 2 * (qz * p[0] - qx * p[2])
                    let tz = 2 * (qx * p[1] - qy * p[0])
                    let transformed = [
                        p[0] + qw * tx + (qy * tz - qz * ty) + pose.translation[0],
                        p[1] + qw * ty + (qz * tx - qx * tz) + pose.translation[1],
                        p[2] + qw * tz + (qx * ty - qy * tx) + pose.translation[2]
                    ]
                    transformedEndpoints.append(transformed)
                }
                let firstEndpointDistance = zip(transformedEndpoints[0], anchorPosition)
                    .reduce(0) { $0 + ($1.0 - $1.1) * ($1.0 - $1.1) }.squareRoot()
                let secondEndpointDistance = zip(transformedEndpoints[1], anchorPosition)
                    .reduce(0) { $0 + ($1.0 - $1.1) * ($1.0 - $1.1) }.squareRoot()
                let passageDistance = zip(transformedEndpoints[0], transformedEndpoints[1])
                    .reduce(0) { $0 + ($1.0 - $1.1) * ($1.0 - $1.1) }
                    .squareRoot()
                let minimumRouteLength = firstEndpointDistance + passageDistance + secondEndpointDistance
                guard firstEndpointDistance.isFinite, secondEndpointDistance.isFinite,
                      passageDistance.isFinite, minimumRouteLength.isFinite,
                      firstEndpointDistance > 1e-7, secondEndpointDistance > 1e-7,
                      passageDistance > 1e-7,
                      branch.restLength >= minimumRouteLength - 1e-5 else {
                    throw BoardPackageStoreError.invalidPackage(boardID: boardID, reason: "twoBranchCord pose \(positionID) branch \(branch.id) must have distinct passage and anchor endpoints with a feasible closed route")
                }
            }
        }
        let poseValues = document.canonicalPoses.mapValues {
            BoardModelCanonicalPose(rotation: $0.rotation, translation: $0.translation, camera: BoardModelCanonicalCamera(viewDirection: $0.camera.viewDirection, fitPadding: $0.camera.fitPadding))
        }
        return .twoBranchCord(BoardModelTwoBranchSuspension(
            passages: BoardModelPassagePairs(
                left: document.passages.left.map { BoardModelPassage(id: $0.id, nodeID: $0.nodeID, pointInModel: $0.pointInModel, provenance: $0.provenance) },
                right: document.passages.right.map { BoardModelPassage(id: $0.id, nodeID: $0.nodeID, pointInModel: $0.pointInModel, provenance: $0.provenance) }
            ),
            branches: document.branches.map { BoardModelCordBranch(id: $0.id, passageIDs: $0.passageIDs, restLength: $0.restLength, radius: $0.radius, material: $0.material, provenance: $0.provenance) },
            anchor: BoardModelInvisibleAnchor(offsetFromBoardBounds: document.anchor.offsetFromBoardBounds, visibility: document.anchor.visibility, provenance: document.anchor.provenance, position: anchorPosition),
            canonicalPoses: poseValues
        ))

}
}

private enum BoardPackageRawJSONError: Error {
    case invalid
}

private struct BoardPackageRawJSONMember: Equatable {
    let name: String
    let value: BoardPackageRawJSONValue
}

private enum BoardPackageRawJSONNumberKind: Equatable {
    case integer
    case floating
}

private enum BoardPackageRawJSONNumberValue: Equatable {
    case integer(String)
    case floating(Double)
}

private indirect enum BoardPackageRawJSONValue: Equatable {
    case object([BoardPackageRawJSONMember])
    case array([BoardPackageRawJSONValue])
    case string(String)
    case number(kind: BoardPackageRawJSONNumberKind, value: BoardPackageRawJSONNumberValue)
    case boolean(Bool)
    case null

    func rasterGeometryByPresentationID() throws -> [String: BoardPackageRawJSONValue] {
        guard case .object(let rootMembers) = self,
              case .array(let presentations)? = rootMembers.value(named: "presentations") else {
            throw BoardPackageRawJSONError.invalid
        }
        var result: [String: BoardPackageRawJSONValue] = [:]
        for presentation in presentations {
            guard case .object(let presentationMembers) = presentation,
                  case .string(let presentationID)? = presentationMembers.value(named: "id"),
                  case .object(let mediaMembers)? = presentationMembers.value(named: "media"),
                  case .string(let mediaType)? = mediaMembers.value(named: "type") else {
                throw BoardPackageRawJSONError.invalid
            }
            guard mediaType == "raster" else { continue }
            guard let geometry = mediaMembers.value(named: "holdGeometry"),
                  result.updateValue(geometry, forKey: presentationID) == nil else {
                throw BoardPackageRawJSONError.invalid
            }
        }
        return result
    }

    func validateTwoBranchSuspensionMemberOrder() throws {
        guard case .object(let rootMembers) = self,
              case .array(let presentations)? = rootMembers.value(named: "presentations") else {
            throw BoardPackageRawJSONError.invalid
        }
        for presentation in presentations {
            guard case .object(let presentationMembers) = presentation,
                  case .object(let mediaMembers)? = presentationMembers.value(named: "media"),
                  case .string(let mediaType)? = mediaMembers.value(named: "type") else {
                throw BoardPackageRawJSONError.invalid
            }
            guard mediaType == "model",
                  case .object(let suspensionMembers)? = mediaMembers.value(named: "suspension"),
                  case .string(let suspensionType)? = suspensionMembers.value(named: "type") else {
                continue
            }
            guard suspensionType == "twoBranchCord" else { continue }
            try suspensionMembers.requireCanonicalOrder(["type", "passages", "branches", "anchor", "canonicalPoses"])
            guard case .object(let passagesMembers)? = suspensionMembers.value(named: "passages"),
                  case .array(let leftPassages)? = passagesMembers.value(named: "left"),
                  case .array(let rightPassages)? = passagesMembers.value(named: "right"),
                  case .array(let branches)? = suspensionMembers.value(named: "branches"),
                  case .object(let anchorMembers)? = suspensionMembers.value(named: "anchor"),
                  case .object(let poseMembers)? = suspensionMembers.value(named: "canonicalPoses") else {
                throw BoardPackageRawJSONError.invalid
            }
            try passagesMembers.requireCanonicalOrder(["left", "right"])
            for passage in leftPassages + rightPassages {
                guard case .object(let members) = passage else { throw BoardPackageRawJSONError.invalid }
                try members.requireCanonicalOrder(["id", "nodeID", "pointInModel", "provenance"])
            }
            for branch in branches {
                guard case .object(let members) = branch else { throw BoardPackageRawJSONError.invalid }
                try members.requireCanonicalOrder(["id", "passageIDs", "restLength", "radius", "material", "provenance"])
            }
            try anchorMembers.requireCanonicalOrder(["offsetFromBoardBounds", "visibility", "provenance"])
            for pose in poseMembers.mapValues() {
                guard case .object(let poseObject) = pose,
                      case .object(let camera)? = poseObject.value(named: "camera") else {
                    throw BoardPackageRawJSONError.invalid
                }
                try poseObject.requireCanonicalOrder(["rotation", "translation", "camera"])
                try camera.requireCanonicalOrder(["viewDirection", "fitPadding"])
            }
        }
    }
}

private extension Array where Element == BoardPackageRawJSONMember {
    func value(named name: String) -> BoardPackageRawJSONValue? {
        first(where: { $0.name == name })?.value
    }

    var names: [String] { map(\.name) }

    func mapValues() -> [BoardPackageRawJSONValue] { map(\.value) }

    func requireCanonicalOrder(_ expected: [String]) throws {
        guard names == expected else { throw BoardPackageRawJSONError.invalid }
    }
}

private struct BoardPackageRawJSONParser {
    private static let maximumNestingDepth = 128

    private let bytes: [UInt8]
    private var index = 0

    init(data: Data) {
        bytes = Array(data)
    }

    mutating func parseDocument() throws -> BoardPackageRawJSONValue {
        skipWhitespace()
        let result = try value(depth: 0)
        skipWhitespace()
        guard index == bytes.count else { throw BoardPackageRawJSONError.invalid }
        return result
    }

    private mutating func value(depth: Int) throws -> BoardPackageRawJSONValue {
        guard depth < Self.maximumNestingDepth, let byte = peek else {
            throw BoardPackageRawJSONError.invalid
        }
        switch byte {
        case 123:
            return try object(depth: depth + 1)
        case 91:
            return try array(depth: depth + 1)
        case 34:
            return .string(try string())
        case 45, 48...57:
            return try number()
        case 116:
            try consumeLiteral("true")
            return .boolean(true)
        case 102:
            try consumeLiteral("false")
            return .boolean(false)
        case 110:
            try consumeLiteral("null")
            return .null
        default:
            throw BoardPackageRawJSONError.invalid
        }
    }

    private mutating func object(depth: Int) throws -> BoardPackageRawJSONValue {
        try consume(123)
        skipWhitespace()
        var members: [BoardPackageRawJSONMember] = []
        var names = Set<String>()
        if peek == 125 {
            index += 1
            return .object(members)
        }
        while true {
            let name = try string()
            guard names.insert(name).inserted else { throw BoardPackageRawJSONError.invalid }
            skipWhitespace()
            try consume(58)
            skipWhitespace()
            members.append(.init(name: name, value: try value(depth: depth)))
            skipWhitespace()
            if peek == 125 {
                index += 1
                return .object(members)
            }
            try consume(44)
            skipWhitespace()
        }
    }

    private mutating func array(depth: Int) throws -> BoardPackageRawJSONValue {
        try consume(91)
        skipWhitespace()
        var values: [BoardPackageRawJSONValue] = []
        if peek == 93 {
            index += 1
            return .array(values)
        }
        while true {
            values.append(try value(depth: depth))
            skipWhitespace()
            if peek == 93 {
                index += 1
                return .array(values)
            }
            try consume(44)
            skipWhitespace()
        }
    }

    private mutating func number() throws -> BoardPackageRawJSONValue {
        let start = index
        if peek == 45 { index += 1 }
        if peek == 48 {
            index += 1
            if let byte = peek, (48...57).contains(byte) {
                throw BoardPackageRawJSONError.invalid
            }
        } else {
            try consumeDigits(firstMayBeZero: false)
        }
        var kind = BoardPackageRawJSONNumberKind.integer
        if peek == 46 {
            kind = .floating
            index += 1
            try consumeDigits(firstMayBeZero: true)
        }
        if peek == 101 || peek == 69 {
            kind = .floating
            index += 1
            if peek == 43 || peek == 45 { index += 1 }
            try consumeDigits(firstMayBeZero: true)
        }
        let token = String(decoding: bytes[start..<index], as: UTF8.self)
        switch kind {
        case .integer:
            let normalizedToken = token == "-0" ? "0" : token
            return .number(kind: kind, value: .integer(normalizedToken))
        case .floating:
            guard let value = Double(token), value.isFinite else {
                throw BoardPackageRawJSONError.invalid
            }
            return .number(kind: kind, value: .floating(value))
        }
    }

    private mutating func consumeDigits(firstMayBeZero: Bool) throws {
        guard let first = peek,
              (firstMayBeZero ? (48...57).contains(first) : (49...57).contains(first)) else {
            throw BoardPackageRawJSONError.invalid
        }
        repeat { index += 1 } while peek.map({ (48...57).contains($0) }) == true
    }

    private mutating func string() throws -> String {
        let start = index
        try consume(34)
        var escaped = false
        while let byte = peek {
            index += 1
            if escaped {
                escaped = false
            } else if byte == 92 {
                escaped = true
            } else if byte == 34 {
                return try JSONDecoder().decode(
                    String.self,
                    from: Data(bytes[start..<index])
                )
            }
        }
        throw BoardPackageRawJSONError.invalid
    }

    private mutating func consumeLiteral(_ literal: String) throws {
        let expected = Array(literal.utf8)
        guard index + expected.count <= bytes.count,
              Array(bytes[index..<(index + expected.count)]) == expected else {
            throw BoardPackageRawJSONError.invalid
        }
        index += expected.count
    }

    private mutating func skipWhitespace() {
        while let byte = peek, [9, 10, 13, 32].contains(byte) { index += 1 }
    }

    private mutating func consume(_ byte: UInt8) throws {
        guard peek == byte else { throw BoardPackageRawJSONError.invalid }
        index += 1
    }

    private var peek: UInt8? {
        index < bytes.count ? bytes[index] : nil
    }
}

/// Reads JSON object member order before `JSONDecoder` converts objects into
/// dictionaries. JSON decoding intentionally does not preserve this order.
struct BoardPackageJSONMemberOrder {
    static let maximumNestingDepth = 128

    private let bytes: [UInt8]
    private var index = 0

    init(data: Data) {
        bytes = Array(data)
    }

    mutating func memberNames(inRootObjectNamed target: String) throws -> [String] {
        skipWhitespace()
        try consume(123)
        skipWhitespace()
        while peek != 125 {
            let name = try string()
            skipWhitespace()
            try consume(58)
            skipWhitespace()
            if name == target { return try objectMemberNames(depth: 1) }
            try skipValue(depth: 1)
            skipWhitespace()
            if peek == 44 { index += 1; skipWhitespace() } else { break }
        }
        throw ParseError.invalid
    }

    private mutating func objectMemberNames(depth: Int) throws -> [String] {
        guard depth < Self.maximumNestingDepth else { throw ParseError.invalid }
        try consume(123)
        skipWhitespace()
        var result: [String] = []
        while peek != 125 {
            result.append(try string())
            skipWhitespace()
            try consume(58)
            skipWhitespace()
            try skipValue(depth: depth + 1)
            skipWhitespace()
            if peek == 44 { index += 1; skipWhitespace() } else { break }
        }
        try consume(125)
        return result
    }

    private mutating func skipValue(depth: Int) throws {
        skipWhitespace()
        switch peek {
        case 34: _ = try string()
        case 123:
            guard depth < Self.maximumNestingDepth else { throw ParseError.invalid }
            try consume(123); skipWhitespace()
            while peek != 125 {
                _ = try string(); skipWhitespace(); try consume(58)
                try skipValue(depth: depth + 1); skipWhitespace()
                if peek == 44 { index += 1; skipWhitespace() } else { break }
            }
            try consume(125)
        case 91:
            guard depth < Self.maximumNestingDepth else { throw ParseError.invalid }
            try consume(91); skipWhitespace()
            while peek != 93 {
                try skipValue(depth: depth + 1); skipWhitespace()
                if peek == 44 { index += 1; skipWhitespace() } else { break }
            }
            try consume(93)
        default:
            let start = index
            while let byte = peek, ![9, 10, 13, 32, 44, 93, 125].contains(byte) { index += 1 }
            guard index > start else { throw ParseError.invalid }
        }
    }

    private mutating func string() throws -> String {
        let start = index
        try consume(34)
        var escaped = false
        while let byte = peek {
            index += 1
            if escaped { escaped = false; continue }
            if byte == 92 { escaped = true; continue }
            if byte == 34 {
                let data = Data(bytes[start..<index])
                return try JSONDecoder().decode(String.self, from: data)
            }
        }
        throw ParseError.invalid
    }

    private mutating func skipWhitespace() {
        while let byte = peek, [9, 10, 13, 32].contains(byte) { index += 1 }
    }

    private mutating func consume(_ byte: UInt8) throws {
        guard peek == byte else { throw ParseError.invalid }
        index += 1
    }

    private var peek: UInt8? { index < bytes.count ? bytes[index] : nil }
    private enum ParseError: Error { case invalid }
}

private struct BoardPackageV2BoardDocument: Decodable {
    let schemaVersion: Int
    let id: String
    let manufacturer: String
    let name: String
    let subtitle: String
    let productURL: URL
    let dimensions: String?
    let aspectRatio: Double
    let equipmentObjects: [BoardPackageEquipmentObjectDocument]
    let presentations: [BoardPackageV2PresentationDocument]
    let positions: [BoardPackagePositionDocument]?
    let positionTransitions: [BoardPackagePositionTransitionDocument]?
    let holds: [BoardPackageV2HoldDocument]

    private enum CodingKeys: String, CodingKey {
        case schemaVersion, id, manufacturer, name, subtitle, productURL, dimensions
        case aspectRatio, equipmentObjects, presentations, positions, positionTransitions, holds
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "schemaVersion", "id", "manufacturer", "name", "subtitle", "productURL",
            "dimensions", "aspectRatio", "equipmentObjects", "presentations", "positions",
            "positionTransitions", "holds"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        id = try container.decode(String.self, forKey: .id)
        manufacturer = try container.decode(String.self, forKey: .manufacturer)
        name = try container.decode(String.self, forKey: .name)
        subtitle = try container.decode(String.self, forKey: .subtitle)
        productURL = try container.decode(URL.self, forKey: .productURL)
        dimensions = container.contains(.dimensions)
            ? try container.decode(String.self, forKey: .dimensions)
            : nil
        aspectRatio = try container.decode(Double.self, forKey: .aspectRatio)
        equipmentObjects = container.contains(.equipmentObjects)
            ? try container.decode([BoardPackageEquipmentObjectDocument].self, forKey: .equipmentObjects)
            : [.init(id: "primary")]
        presentations = try container.decode([BoardPackageV2PresentationDocument].self, forKey: .presentations)
        positions = container.contains(.positions)
            ? try container.decode([BoardPackagePositionDocument].self, forKey: .positions)
            : nil
        positionTransitions = container.contains(.positionTransitions)
            ? try container.decode([BoardPackagePositionTransitionDocument].self, forKey: .positionTransitions)
            : nil
        holds = try container.decode([BoardPackageV2HoldDocument].self, forKey: .holds)
    }
}

private struct BoardPackageV2PresentationDocument: Decodable {
    let id: String
    let name: String
    let aspectRatio: Double
    let isDefault: Bool
    let derivation: BoardPackageV2DerivationDocument
    let media: BoardPackageV2MediaDocument

    private enum CodingKeys: String, CodingKey {
        case id, name, aspectRatio, isDefault, derivation, media
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "name", "aspectRatio", "isDefault", "derivation", "media"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        aspectRatio = try container.decode(Double.self, forKey: .aspectRatio)
        isDefault = try container.decode(Bool.self, forKey: .isDefault)
        derivation = try container.decode(BoardPackageV2DerivationDocument.self, forKey: .derivation)
        media = try container.decode(BoardPackageV2MediaDocument.self, forKey: .media)
    }
}

private enum BoardPackageV2DerivationDocument: Decodable {
    case original
    case derived(sourcePresentationID: String, isInverted: Bool)

    private enum CodingKeys: String, CodingKey { case type, sourcePresentationID, isInverted }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)
        switch type {
        case "original":
            try decoder.rejectUnknownKeys(["type"])
            self = .original
        case "derived":
            try decoder.rejectUnknownKeys(["type", "sourcePresentationID", "isInverted"])
            self = .derived(
                sourcePresentationID: try container.decode(String.self, forKey: .sourcePresentationID),
                isInverted: try container.decode(Bool.self, forKey: .isInverted)
            )
        default:
            throw DecodingError.dataCorruptedError(
                forKey: .type,
                in: container,
                debugDescription: "derivation type must be original or derived"
            )
        }
    }
}

private enum BoardPackageV2MediaDocument: Decodable {
    case raster(assetPath: String, holdGeometry: [String: [BoardPackageGeometryDocument]])
    case model(assetPath: String, descriptorPath: String, display: BoardPackageModelDisplayDocument, suspension: BoardPackageSuspensionDocument?)

    private enum CodingKeys: String, CodingKey {
        case type, assetPath, holdGeometry, descriptorPath, display, suspension
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)
        switch type {
        case "raster":
            try decoder.rejectUnknownKeys(["type", "assetPath", "holdGeometry"])
            self = .raster(
                assetPath: try container.decode(String.self, forKey: .assetPath),
                holdGeometry: try container.decode(
                    [String: [BoardPackageGeometryDocument]].self,
                    forKey: .holdGeometry
                )
            )
        case "model":
            try decoder.rejectUnknownKeys(["type", "assetPath", "descriptorPath", "display", "suspension"])
            self = .model(
                assetPath: try container.decode(String.self, forKey: .assetPath),
                descriptorPath: try container.decode(String.self, forKey: .descriptorPath),
                display: try container.decode(BoardPackageModelDisplayDocument.self, forKey: .display),
                suspension: container.contains(.suspension)
                    ? try container.decode(BoardPackageSuspensionDocument.self, forKey: .suspension)
                    : nil
            )
        default:
            throw DecodingError.dataCorruptedError(
                forKey: .type,
                in: container,
                debugDescription: "media type must be raster or model"
            )
        }
    }

    var assetPath: String {
        switch self {
        case .raster(let assetPath, _), .model(let assetPath, _, _, _): assetPath
        }
    }
}

private enum BoardPackageSuspensionDocument: Decodable {
    case singleCord(BoardPackageSingleCordSuspensionDocument)
    case twoBranchCord(BoardPackageTwoBranchSuspensionDocument)
    case unsupported(String)
    case shapeMismatch(String)

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: SuspensionCodingKey.self)
        let type = try container.decode(String.self, forKey: .type)
        switch type {
        case "singleCord":
            if container.allKeys.contains(where: { $0.stringValue == "passages" || $0.stringValue == "branches" }) {
                self = .shapeMismatch(type)
            } else {
                self = .singleCord(try BoardPackageSingleCordSuspensionDocument(from: decoder))
            }
        case "twoBranchCord":
            if container.allKeys.contains(where: { $0.stringValue == "attachment" || $0.stringValue == "cord" }) {
                self = .shapeMismatch(type)
            } else {
                self = .twoBranchCord(try BoardPackageTwoBranchSuspensionDocument(from: decoder))
            }
        default:
            self = .unsupported(type)
        }
    }

    private enum SuspensionCodingKey: String, CodingKey {
        case type, attachment, anchor, cord, canonicalPoses, passages, branches
    }
}

private struct BoardPackageSingleCordSuspensionDocument: Decodable {
    let type: String
    let attachment: BoardPackageAttachmentDocument
    let anchor: BoardPackageAnchorDocument
    let cord: BoardPackageCordDocument
    let canonicalPoses: [String: BoardPackageCanonicalPoseDocument]

    private enum CodingKeys: String, CodingKey {
        case type, attachment, anchor, cord, canonicalPoses
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["type", "attachment", "anchor", "cord", "canonicalPoses"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(String.self, forKey: .type)
        attachment = try container.decode(BoardPackageAttachmentDocument.self, forKey: .attachment)
        anchor = try container.decode(BoardPackageAnchorDocument.self, forKey: .anchor)
        cord = try container.decode(BoardPackageCordDocument.self, forKey: .cord)
        canonicalPoses = try container.decode([String: BoardPackageCanonicalPoseDocument].self, forKey: .canonicalPoses)
    }
}

private struct BoardPackagePassageDocument: Decodable {
    let id: String
    let nodeID: String
    let pointInModel: [Double]
    let provenance: String

    private enum CodingKeys: String, CodingKey { case id, nodeID, pointInModel, provenance }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "nodeID", "pointInModel", "provenance"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        nodeID = try container.decode(String.self, forKey: .nodeID)
        pointInModel = try container.decode([Double].self, forKey: .pointInModel)
        provenance = try container.decode(String.self, forKey: .provenance)
    }
}

private struct BoardPackagePassagePairsDocument: Decodable {
    let left: [BoardPackagePassageDocument]
    let right: [BoardPackagePassageDocument]

    private enum CodingKeys: String, CodingKey { case left, right }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["left", "right"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        left = try container.decode([BoardPackagePassageDocument].self, forKey: .left)
        right = try container.decode([BoardPackagePassageDocument].self, forKey: .right)
    }
}

private struct BoardPackageCordBranchDocument: Decodable {
    let id: String
    let passageIDs: [String]
    let restLength: Double
    let radius: Double
    let material: String
    let provenance: String

    private enum CodingKeys: String, CodingKey { case id, passageIDs, restLength, radius, material, provenance }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "passageIDs", "restLength", "radius", "material", "provenance"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        passageIDs = try container.decode([String].self, forKey: .passageIDs)
        restLength = try container.decode(Double.self, forKey: .restLength)
        radius = try container.decode(Double.self, forKey: .radius)
        material = try container.decode(String.self, forKey: .material)
        provenance = try container.decode(String.self, forKey: .provenance)
    }
}

private struct BoardPackageTwoBranchSuspensionDocument: Decodable {
    let passages: BoardPackagePassagePairsDocument
    let branches: [BoardPackageCordBranchDocument]
    let anchor: BoardPackageAnchorDocument
    let canonicalPoses: [String: BoardPackageCanonicalPoseDocument]

    private enum CodingKeys: String, CodingKey { case type, passages, branches, anchor, canonicalPoses }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["type", "passages", "branches", "anchor", "canonicalPoses"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        _ = try container.decode(String.self, forKey: .type)
        passages = try container.decode(BoardPackagePassagePairsDocument.self, forKey: .passages)
        branches = try container.decode([BoardPackageCordBranchDocument].self, forKey: .branches)
        anchor = try container.decode(BoardPackageAnchorDocument.self, forKey: .anchor)
        canonicalPoses = try container.decode([String: BoardPackageCanonicalPoseDocument].self, forKey: .canonicalPoses)
    }
}

private struct BoardPackageAttachmentDocument: Decodable {
    let nodeID: String
    let pointInModel: [Double]
    let provenance: String

    private enum CodingKeys: String, CodingKey { case nodeID, pointInModel, provenance }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["nodeID", "pointInModel", "provenance"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        nodeID = try container.decode(String.self, forKey: .nodeID)
        pointInModel = try container.decode([Double].self, forKey: .pointInModel)
        provenance = try container.decode(String.self, forKey: .provenance)
    }
}

private struct BoardPackageAnchorDocument: Decodable {
    let offsetFromBoardBounds: [Double]
    let visibility: String
    let provenance: String

    private enum CodingKeys: String, CodingKey { case offsetFromBoardBounds, visibility, provenance }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["offsetFromBoardBounds", "visibility", "provenance"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        offsetFromBoardBounds = try container.decode([Double].self, forKey: .offsetFromBoardBounds)
        visibility = try container.decode(String.self, forKey: .visibility)
        provenance = try container.decode(String.self, forKey: .provenance)
    }
}

private struct BoardPackageCordDocument: Decodable {
    let restLength: Double
    let radius: Double
    let material: String
    let provenance: String

    private enum CodingKeys: String, CodingKey { case restLength, radius, material, provenance }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["restLength", "radius", "material", "provenance"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        restLength = try container.decode(Double.self, forKey: .restLength)
        radius = try container.decode(Double.self, forKey: .radius)
        material = try container.decode(String.self, forKey: .material)
        provenance = try container.decode(String.self, forKey: .provenance)
    }
}

private struct BoardPackageCanonicalPoseDocument: Decodable {
    let rotation: [Double]
    let translation: [Double]
    let camera: BoardPackageCanonicalCameraDocument

    private enum CodingKeys: String, CodingKey { case rotation, translation, camera }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["rotation", "translation", "camera"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        rotation = try container.decode([Double].self, forKey: .rotation)
        translation = try container.decode([Double].self, forKey: .translation)
        camera = try container.decode(BoardPackageCanonicalCameraDocument.self, forKey: .camera)
    }
}

private struct BoardPackageCanonicalCameraDocument: Decodable {
    let viewDirection: [Double]
    let fitPadding: Double

    private enum CodingKeys: String, CodingKey { case viewDirection, fitPadding }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["viewDirection", "fitPadding"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        viewDirection = try container.decode([Double].self, forKey: .viewDirection)
        fitPadding = try container.decode(Double.self, forKey: .fitPadding)
    }
}

private struct BoardPackageModelDisplayDocument: Decodable {
    let camera: BoardPackageModelCameraDocument

    private enum CodingKeys: String, CodingKey { case camera }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["camera"])
        camera = try decoder.container(keyedBy: CodingKeys.self)
            .decode(BoardPackageModelCameraDocument.self, forKey: .camera)
    }
}

private struct BoardPackageModelCameraDocument: Decodable {
    let type: String
    let viewDirection: [Double]
    let up: [Double]
    let fitPadding: Double

    private enum CodingKeys: String, CodingKey { case type, viewDirection, up, fitPadding }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["type", "viewDirection", "up", "fitPadding"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(String.self, forKey: .type)
        viewDirection = try container.decode([Double].self, forKey: .viewDirection)
        up = try container.decode([Double].self, forKey: .up)
        fitPadding = try container.decode(Double.self, forKey: .fitPadding)
    }
}

private struct BoardPackageV2HoldDocument: Decodable {
    let id: String
    let equipmentObjectID: String
    let name: String
    let kind: HoldKind
    let sloper: SloperMetadata?
    let sizeMillimeters: Double?
    let depthRangeMillimeters: BoardPackageMillimeterRangeDocument?
    let gripType: GripType?
    let fingerCapacity: Int?
    let handCapacity: Int?
    let features: [HoldFeature]?
    let pairedHoldID: String?
    let declaresPairedHoldID: Bool

    private enum CodingKeys: String, CodingKey {
        case id, equipmentObjectID, name, kind, sloper, sizeMillimeters, depthRangeMillimeters
        case gripType, fingerCapacity, handCapacity, features, pairedHoldID
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "id", "equipmentObjectID", "name", "kind", "sloper", "sizeMillimeters",
            "depthRangeMillimeters", "gripType", "fingerCapacity", "handCapacity",
            "features", "pairedHoldID"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        equipmentObjectID = container.contains(.equipmentObjectID)
            ? try container.decode(String.self, forKey: .equipmentObjectID)
            : "primary"
        name = try container.decode(String.self, forKey: .name)
        kind = try container.decode(HoldKind.self, forKey: .kind)
        sloper = container.contains(.sloper)
            ? try container.decode(SloperMetadata.self, forKey: .sloper)
            : nil
        sizeMillimeters = container.contains(.sizeMillimeters)
            ? try container.decode(Double.self, forKey: .sizeMillimeters)
            : nil
        depthRangeMillimeters = container.contains(.depthRangeMillimeters)
            ? try container.decode(
                BoardPackageMillimeterRangeDocument.self,
                forKey: .depthRangeMillimeters
            )
            : nil
        gripType = container.contains(.gripType)
            ? try container.decode(GripType.self, forKey: .gripType)
            : nil
        fingerCapacity = container.contains(.fingerCapacity)
            ? try container.decode(Int.self, forKey: .fingerCapacity)
            : nil
        handCapacity = container.contains(.handCapacity)
            ? try container.decode(Int.self, forKey: .handCapacity)
            : nil
        features = container.contains(.features)
            ? try container.decode([HoldFeature].self, forKey: .features)
            : nil
        declaresPairedHoldID = container.contains(.pairedHoldID)
        pairedHoldID = try container.decodeIfPresent(String.self, forKey: .pairedHoldID)
    }
}

private struct BoardPackageModelDescriptorDocument: Decodable {
    let schemaVersion: Int
    let coordinateFrame: String
    let modelSHA256: String
    let modelBounds: BoardPackageModelBoundsDocument
    let nodes: [BoardPackageModelNodeDocument]
    let holds: [String: BoardPackageModelHoldDocument]

    private enum CodingKeys: String, CodingKey {
        case schemaVersion, coordinateFrame, modelSHA256, modelBounds, nodes, holds
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys([
            "schemaVersion", "coordinateFrame", "modelSHA256", "modelBounds", "nodes", "holds"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        coordinateFrame = try container.decode(String.self, forKey: .coordinateFrame)
        modelSHA256 = try container.decode(String.self, forKey: .modelSHA256)
        modelBounds = try container.decode(BoardPackageModelBoundsDocument.self, forKey: .modelBounds)
        nodes = try container.decode([BoardPackageModelNodeDocument].self, forKey: .nodes)
        holds = try container.decode([String: BoardPackageModelHoldDocument].self, forKey: .holds)
    }
}

private struct BoardPackageModelBoundsDocument: Decodable {
    let minimum: [Double]
    let maximum: [Double]
    private enum CodingKeys: String, CodingKey { case minimum = "min", maximum = "max" }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["min", "max"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        minimum = try container.decode([Double].self, forKey: .minimum)
        maximum = try container.decode([Double].self, forKey: .maximum)
    }
}

private struct BoardPackageModelNodeDocument: Decodable {
    let nodeID: String
    let role: String
    let holdID: String?
    private enum CodingKeys: String, CodingKey { case nodeID, role, holdID }
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        role = try container.decode(String.self, forKey: .role)
        if role == "hold" {
            try decoder.rejectUnknownKeys(["nodeID", "role", "holdID"])
            holdID = try container.decode(String.self, forKey: .holdID)
        } else {
            try decoder.rejectUnknownKeys(["nodeID", "role"])
            holdID = nil
        }
        nodeID = try container.decode(String.self, forKey: .nodeID)
    }
}

private struct BoardPackageModelHoldDocument: Decodable {
    let nodeIDs: [String]
    let facePlaneAABB: BoardPackageModelBoundsDocument
    let center: [Double]
    private enum CodingKeys: String, CodingKey { case nodeIDs, facePlaneAABB, center }
    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["nodeIDs", "facePlaneAABB", "center"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        nodeIDs = try container.decode([String].self, forKey: .nodeIDs)
        facePlaneAABB = try container.decode(BoardPackageModelBoundsDocument.self, forKey: .facePlaneAABB)
        center = try container.decode([Double].self, forKey: .center)
    }
}

private struct BoardPackagePositionDocument: Decodable {
    let id: String
    let presentationID: String

    private enum CodingKeys: String, CodingKey {
        case id
        case presentationID
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "presentationID"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        presentationID = try container.decode(String.self, forKey: .presentationID)
    }

    var boardPosition: BoardPosition {
        BoardPosition(id: id, presentationID: presentationID)
    }
}

private struct BoardPackagePositionTransitionDocument: Decodable {
    let fromPositionID: String
    let toPositionID: String
    let kind: BoardPositionTransitionKind

    private enum CodingKeys: String, CodingKey {
        case fromPositionID
        case toPositionID
        case kind
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["fromPositionID", "toPositionID", "kind"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        fromPositionID = try container.decode(String.self, forKey: .fromPositionID)
        toPositionID = try container.decode(String.self, forKey: .toPositionID)
        kind = try container.decode(BoardPositionTransitionKind.self, forKey: .kind)
    }

    var boardPositionTransition: BoardPositionTransition {
        BoardPositionTransition(
            fromPositionID: fromPositionID,
            toPositionID: toPositionID,
            kind: kind
        )
    }
}

private struct BoardPackageEquipmentObjectDocument: Decodable {
    let id: String
    let missingHandCapacityPolicy: MissingHandCapacityPolicy

    private enum CodingKeys: String, CodingKey {
        case id
        case missingHandCapacityPolicy
    }

    init(
        id: String,
        missingHandCapacityPolicy: MissingHandCapacityPolicy = .legacyBilateral
    ) {
        self.id = id
        self.missingHandCapacityPolicy = missingHandCapacityPolicy
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["id", "missingHandCapacityPolicy"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        missingHandCapacityPolicy = try container.decodeIfPresent(
            MissingHandCapacityPolicy.self,
            forKey: .missingHandCapacityPolicy
        ) ?? .legacyBilateral
    }

    var equipmentObject: EquipmentObject {
        EquipmentObject(
            id: id,
            missingHandCapacityPolicy: missingHandCapacityPolicy
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
    let lowerBound: Double
    let upperBound: Double

    private enum CodingKeys: String, CodingKey {
        case lowerBound
        case upperBound
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownKeys(["lowerBound", "upperBound"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        lowerBound = try container.decode(Double.self, forKey: .lowerBound)
        upperBound = try container.decode(Double.self, forKey: .upperBound)
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
    var bendable: Bool?
    var smooth: Bool?

    private enum CodingKeys: String, CodingKey {
        case command
        case to
        case control
        case control1
        case control2
        case bendable
        case smooth
    }

    init(
        command: String,
        to: [Double]?,
        control: [Double]?,
        control1: [Double]?,
        control2: [Double]?,
        bendable: Bool? = nil,
        smooth: Bool? = nil
    ) {
        self.command = command
        self.to = to
        self.control = control
        self.control1 = control1
        self.control2 = control2
        self.bendable = bendable
        self.smooth = smooth
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
            allowedKeys = ["command", "to", "control1", "control2", "bendable", "smooth"]
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
        if container.contains(.bendable) {
            guard try container.decode(Bool.self, forKey: .bendable) else {
                throw DecodingError.dataCorruptedError(
                    forKey: .bendable,
                    in: container,
                    debugDescription: "bendable must be true"
                )
            }
            bendable = true
        } else {
            bendable = nil
        }
        if container.contains(.smooth) {
            guard try container.decode(Bool.self, forKey: .smooth) else {
                throw DecodingError.dataCorruptedError(
                    forKey: .smooth,
                    in: container,
                    debugDescription: "smooth must be true"
                )
            }
            smooth = true
        } else {
            smooth = nil
        }
    }

    private func container(
        keyedBy keys: CodingKeys.Type,
        decoder: Decoder
    ) throws -> KeyedDecodingContainer<CodingKeys> {
        try decoder.container(keyedBy: keys)
    }

    /// Runtime encoding drops editor-only bendable and smooth metadata: the training app
    /// never re-delivers it, while the board editor writer reads the stored
    /// property directly when it serializes canonical packages.
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(command, forKey: .command)
        try container.encodeIfPresent(to, forKey: .to)
        try container.encodeIfPresent(control, forKey: .control)
        try container.encodeIfPresent(control1, forKey: .control1)
        try container.encodeIfPresent(control2, forKey: .control2)
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
            let pathCommands = try commands.boardPathCommands()
            try pathCommands.validateContour()
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
        guard coordinates.allSatisfy({ abs($0) <= maximumBoardControlCoordinate }) else {
            throw BoardGeometryAdaptationError.invalid(
                "path coordinates are too large to represent"
            )
        }
        return CGPoint(x: coordinates[0], y: coordinates[1])
    }

    func invalidCommand() -> BoardGeometryAdaptationError {
        .invalid("invalid \(command) path command")
    }
}

private let maximumBoardFlattenedSegments = 1_024
private let maximumBoardControlCoordinate = 1_000_000.0
private let boardContourEpsilon = CGFloat(1e-9)

private func sameBoardContourPoint(_ lhs: CGPoint, _ rhs: CGPoint) -> Bool {
    abs(lhs.x - rhs.x) <= boardContourEpsilon &&
        abs(lhs.y - rhs.y) <= boardContourEpsilon
}

private extension Array where Element == BoardGeometryPathCommandDocument {
    /// Convert commands incrementally so an excessive contour is rejected
    /// before later malformed commands are decoded into path geometry or a
    /// flattened point array is allocated.
    func boardPathCommands() throws -> [BoardPathCommand] {
        var result: [BoardPathCommand] = []
        result.reserveCapacity(Swift.min(count, maximumBoardFlattenedSegments + 1))
        var flattenedSegmentCount = 0
        var start: CGPoint?
        var current: CGPoint?

        for document in self {
            let command = try document.boardPathCommand()
            var additionalSegments = 0
            switch command {
            case .move(let destination):
                if start == nil { start = destination }
                current = destination
            case .line(let destination):
                additionalSegments = 1
                current = destination
            case .quad(let destination, _):
                additionalSegments = 32
                current = destination
            case .curve(let destination, _, _):
                additionalSegments = 32
                current = destination
            case .close:
                if let start, let current, !sameBoardContourPoint(current, start) {
                    additionalSegments = 1
                }
                current = start
            }
            guard flattenedSegmentCount <= maximumBoardFlattenedSegments - additionalSegments else {
                throw BoardGeometryAdaptationError.invalid(
                    "path must contain no more than \(maximumBoardFlattenedSegments) flattened segments"
                )
            }
            flattenedSegmentCount += additionalSegments
            result.append(command)
        }
        return result
    }
}

extension Array where Element == BoardPathCommand {
    func validateContour() throws {
        let points = try flattenedContour()
        guard points.count >= 4, points.first == points.last else {
            throw BoardGeometryAdaptationError.invalid("path must be a closed contour")
        }
        guard points.count - 1 <= maximumBoardFlattenedSegments else {
            throw BoardGeometryAdaptationError.invalid(
                "path must contain no more than \(maximumBoardFlattenedSegments) flattened segments"
            )
        }
        let canonicalPoints = try Self.canonicalContour(points)
        let uniquePoints = Set(canonicalPoints.dropLast().compactMap(QuantizedBoardPoint.init))
        guard uniquePoints.count >= 3 else {
            throw BoardGeometryAdaptationError.invalid(
                "path must contain at least three unique points"
            )
        }
        let segmentCount = canonicalPoints.count - 1
        for firstIndex in 0..<segmentCount {
            let first = canonicalPoints[firstIndex]
            let second = canonicalPoints[firstIndex + 1]
            guard !Self.samePoint(first, second) else {
                throw BoardGeometryAdaptationError.invalid(
                    "path contains a zero-length segment"
                )
            }
        }
        guard Self.hasFilledSpan(canonicalPoints) else {
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
                try Self.ensureFlattenedBudget(points, adding: 1)
                current = destination
                points.append(destination)
            case .quad(let destination, let control):
                try Self.ensureFlattenedBudget(points, adding: 32)
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
                try Self.ensureFlattenedBudget(points, adding: 32)
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
                if !sameBoardContourPoint(current, start) {
                    try Self.ensureFlattenedBudget(points, adding: 1)
                    points.append(start)
                }
                current = start
            }
        }
        return points
    }

    private static func ensureFlattenedBudget(
        _ points: [CGPoint],
        adding additionalSegments: Int
    ) throws {
        guard points.count - 1 <= maximumBoardFlattenedSegments - additionalSegments else {
            throw BoardGeometryAdaptationError.invalid(
                "path must contain no more than \(maximumBoardFlattenedSegments) flattened segments"
            )
        }
    }

    private static func samePoint(_ lhs: CGPoint, _ rhs: CGPoint) -> Bool {
        sameBoardContourPoint(lhs, rhs)
    }

    /// Validation depends on topology, not the coordinate system used to
    /// express it. Canonicalizing both axes keeps the epsilon meaningful and
    /// gives editor-pixel and normalized package contours identical semantics.
    private static func canonicalContour(_ points: [CGPoint]) throws -> [CGPoint] {
        let minimumX = points.map(\.x).min() ?? 0
        let maximumX = points.map(\.x).max() ?? 0
        let minimumY = points.map(\.y).min() ?? 0
        let maximumY = points.map(\.y).max() ?? 0
        let width = maximumX - minimumX
        let height = maximumY - minimumY
        guard width.isFinite, height.isFinite else {
            throw BoardGeometryAdaptationError.invalid(
                "path coordinates are too large to represent"
            )
        }
        let canonical = points.map { point in
            CGPoint(
                x: width > 0 ? (point.x - minimumX) / width : 0,
                y: height > 0 ? (point.y - minimumY) / height : 0
            )
        }
        guard canonical.allSatisfy({ $0.x.isFinite && $0.y.isFinite }) else {
            throw BoardGeometryAdaptationError.invalid(
                "path coordinates are too large to represent"
            )
        }
        return canonical
    }

    /// A self-crossing contour can have zero algebraic shoelace area even
    /// when its lobes visibly enclose a filled region. Scan between every
    /// vertex and segment-intersection height, where crossing order is
    /// stable, and accept any horizontal span with non-zero winding.
    private static func hasFilledSpan(_ points: [CGPoint]) -> Bool {
        let segments = Swift.Array(zip(points, points.dropFirst()))
        if segmentsCancelInReversePairs(segments) { return false }

        let vertexHeights = Set(points.map(\.y)).sorted()
        var intersectionHeights: Set<CGFloat> = []
        for firstIndex in segments.indices {
            for secondIndex in segments.indices.dropFirst(firstIndex + 1) {
                if let intersectionY = segmentIntersectionY(
                    segments[firstIndex].0,
                    segments[firstIndex].1,
                    segments[secondIndex].0,
                    segments[secondIndex].1
                ) {
                    intersectionHeights.insert(intersectionY)
                }
            }
        }

        let sortedIntersections = intersectionHeights.sorted()
        var firstPossibleIntersection = 0
        for (lower, upper) in zip(vertexHeights, vertexHeights.dropFirst()) {
            guard upper - lower > boardContourEpsilon else { continue }
            while firstPossibleIntersection < sortedIntersections.count,
                  sortedIntersections[firstPossibleIntersection] <= lower {
                firstPossibleIntersection += 1
            }

            var eventIndex = firstPossibleIntersection
            var previous = lower
            var widestGap = (lower: lower, upper: lower)
            while eventIndex < sortedIntersections.count,
                  sortedIntersections[eventIndex] < upper {
                let event = sortedIntersections[eventIndex]
                if event - previous > widestGap.upper - widestGap.lower {
                    widestGap = (previous, event)
                }
                previous = event
                eventIndex += 1
            }
            if upper - previous > widestGap.upper - widestGap.lower {
                widestGap = (previous, upper)
            }
            firstPossibleIntersection = eventIndex
            guard widestGap.upper - widestGap.lower > boardContourEpsilon else { continue }
            if hasFilledSpan(at: (widestGap.lower + widestGap.upper) / 2, segments: segments) {
                return true
            }
        }
        return false
    }

    private static func segmentsCancelInReversePairs(
        _ segments: [(CGPoint, CGPoint)]
    ) -> Bool {
        var balances: [QuantizedBoardSegment: Int] = [:]
        for (first, second) in segments {
            guard let quantizedFirst = QuantizedBoardPoint(first),
                  let quantizedSecond = QuantizedBoardPoint(second) else {
                return false
            }
            let key: QuantizedBoardSegment
            let direction: Int
            if quantizedFirst < quantizedSecond {
                key = QuantizedBoardSegment(first: quantizedFirst, second: quantizedSecond)
                direction = 1
            } else {
                key = QuantizedBoardSegment(first: quantizedSecond, second: quantizedFirst)
                direction = -1
            }
            balances[key, default: 0] += direction
        }
        return balances.values.allSatisfy { $0 == 0 }
    }

    private static func hasFilledSpan(
        at scanY: CGFloat,
        segments: [(CGPoint, CGPoint)]
    ) -> Bool {
        var crossings = [(x: CGFloat, winding: Int)]()
        for (first, second) in segments where
            (first.y <= scanY && scanY < second.y) ||
            (second.y <= scanY && scanY < first.y) {
            let verticalOffset = scanY - first.y
            let horizontalDelta = second.x - first.x
            let verticalDelta = second.y - first.y
            let x = first.x + verticalOffset * horizontalDelta / verticalDelta
            crossings.append((x, second.y > first.y ? 1 : -1))
        }
        crossings.sort { $0.x < $1.x }

        var index = 0
        var winding = 0
        while index < crossings.count {
            let x = crossings[index].x
            while index < crossings.count,
                  abs(crossings[index].x - x) <= boardContourEpsilon {
                winding += crossings[index].winding
                index += 1
            }
            if index < crossings.count,
               winding != 0,
               crossings[index].x - x > boardContourEpsilon {
                return true
            }
        }
        return false
    }

    private static func segmentIntersectionY(
        _ first: CGPoint,
        _ second: CGPoint,
        _ third: CGPoint,
        _ fourth: CGPoint
    ) -> CGFloat? {
        let firstDelta = CGPoint(x: second.x - first.x, y: second.y - first.y)
        let secondDelta = CGPoint(x: fourth.x - third.x, y: fourth.y - third.y)
        let denominator = firstDelta.x * secondDelta.y - firstDelta.y * secondDelta.x
        guard abs(denominator) > boardContourEpsilon else { return nil }
        let originDelta = CGPoint(x: third.x - first.x, y: third.y - first.y)
        let firstParameter =
            (originDelta.x * secondDelta.y - originDelta.y * secondDelta.x) / denominator
        let secondParameter =
            (originDelta.x * firstDelta.y - originDelta.y * firstDelta.x) / denominator
        guard (-boardContourEpsilon...1 + boardContourEpsilon).contains(firstParameter),
              (-boardContourEpsilon...1 + boardContourEpsilon).contains(secondParameter) else {
            return nil
        }
        return first.y + firstParameter * firstDelta.y
    }
}

private struct QuantizedBoardSegment: Hashable {
    let first: QuantizedBoardPoint
    let second: QuantizedBoardPoint
}

private struct QuantizedBoardPoint: Hashable, Comparable {
    let x: Int64
    let y: Int64

    init?(_ point: CGPoint) {
        guard let x = Self.quantized(point.x), let y = Self.quantized(point.y) else {
            return nil
        }
        self.x = x
        self.y = y
    }

    static func < (lhs: Self, rhs: Self) -> Bool {
        lhs.x < rhs.x || (lhs.x == rhs.x && lhs.y < rhs.y)
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
