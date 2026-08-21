import Foundation

enum BoardDefinitionSchema {
    static let currentVersion = 1
}

struct BoardLibraryMetadata: Codable, Hashable {
    let id: String
    let version: String
    let title: String
    let generatedAt: String
    let defaultBoardID: String?
    let notes: [String]

    init(
        id: String,
        version: String,
        title: String,
        generatedAt: String,
        defaultBoardID: String? = nil,
        notes: [String] = []
    ) {
        self.id = id
        self.version = version
        self.title = title
        self.generatedAt = generatedAt
        self.defaultBoardID = defaultBoardID
        self.notes = notes
    }
}

struct BoardHoldPieceDocument: Codable, Hashable {
    let frame: BoardPackageFrameDocument
    let shape: BoardGeometryShapeDocument
    let treatment: BoardGeometryTreatmentDocument?
}

enum BoardHoldFrameComponent: CaseIterable, Hashable {
    case x
    case y
    case width
    case height
}

struct BoardHoldPieceValidationResult {
    let invalidFrameComponents: Set<BoardHoldFrameComponent>
    let conversionFailureReason: String?
    let usesDeclaredFrame: Bool
    let piece: BoardHoldPiece?

    var packageFailureReason: String? {
        if !invalidFrameComponents.isEmpty {
            return "has an invalid frame"
        }
        if let conversionFailureReason {
            return "is invalid: \(conversionFailureReason)"
        }
        if !usesDeclaredFrame {
            return "frame must match its shape bounds"
        }
        return nil
    }
}

struct BoardHoldGeometryValidationResult {
    let isEmpty: Bool
    let pieces: [BoardHoldPieceValidationResult]
}

enum BoardHoldGeometryValidator {
    static func validate(
        _ geometry: [BoardHoldPieceDocument],
        holdID: String,
        pieceID: (Int) -> String
    ) -> BoardHoldGeometryValidationResult {
        BoardHoldGeometryValidationResult(
            isEmpty: geometry.isEmpty,
            pieces: geometry.enumerated().map { index, piece in
                var invalidFrameComponents = Set<BoardHoldFrameComponent>()
                let frame = piece.frame
                if !frame.x.isFinite {
                    invalidFrameComponents.insert(.x)
                }
                if !frame.y.isFinite {
                    invalidFrameComponents.insert(.y)
                }
                if !frame.width.isFinite || frame.width <= 0 {
                    invalidFrameComponents.insert(.width)
                }
                if !frame.height.isFinite || frame.height <= 0 {
                    invalidFrameComponents.insert(.height)
                }

                var conversionFailureReason: String?
                var validatedPiece: BoardHoldPiece?
                do {
                    validatedPiece = try piece.boardHoldPiece(id: pieceID(index), holdID: holdID)
                    conversionFailureReason = nil
                } catch {
                    conversionFailureReason = String(describing: error)
                }

                return BoardHoldPieceValidationResult(
                    invalidFrameComponents: invalidFrameComponents,
                    conversionFailureReason: conversionFailureReason,
                    usesDeclaredFrame: piece.shape.usesDeclaredFrame,
                    piece: validatedPiece
                )
            }
        )
    }
}

struct BoardHoldDefinition: Codable, Hashable {
    struct MillimeterRange: Codable, Hashable {
        let lowerBound: Int
        let upperBound: Int
    }

    let id: String
    let name: String
    let kind: HoldKind
    let geometry: [BoardHoldPieceDocument]
    let sizeMillimeters: Int?
    let depthRangeMillimeters: MillimeterRange?
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
        case frame
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        kind = try container.decode(HoldKind.self, forKey: .kind)

        if let pieces = try container.decodeIfPresent(
            [BoardHoldPieceDocument].self,
            forKey: .geometry
        ) {
            if container.contains(.frame) {
                throw DecodingError.dataCorrupted(
                    .init(
                        codingPath: container.codingPath + [CodingKeys.geometry],
                        debugDescription: "hold \(id) declares both geometry and legacy frame"
                    )
                )
            }
            geometry = pieces
        } else {
            // Temporary compatibility for frame-only generated-library and
            // hand-built fixtures. Canonical package documents require
            // geometry and use their own closed decoder.
            let frame = try container.decode(BoardPackageFrameDocument.self, forKey: .frame)
            geometry = [
                BoardHoldPieceDocument(
                    frame: frame,
                    shape: BoardGeometryShapeDocument(
                        type: "roundedRect",
                        commands: nil,
                        cornerRadiusFraction: 0
                    ),
                    treatment: nil
                )
            ]
        }

        sizeMillimeters = try container.decodeIfPresent(Int.self, forKey: .sizeMillimeters)
        depthRangeMillimeters = try container.decodeIfPresent(
            MillimeterRange.self,
            forKey: .depthRangeMillimeters
        )
        gripType = try container.decodeIfPresent(GripType.self, forKey: .gripType)
        fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        features = try container.decodeIfPresent([HoldFeature].self, forKey: .features)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(kind, forKey: .kind)
        try container.encode(geometry, forKey: .geometry)
        try container.encodeIfPresent(sizeMillimeters, forKey: .sizeMillimeters)
        try container.encodeIfPresent(depthRangeMillimeters, forKey: .depthRangeMillimeters)
        try container.encodeIfPresent(gripType, forKey: .gripType)
        try container.encodeIfPresent(fingerCapacity, forKey: .fingerCapacity)
        try container.encodeIfPresent(features, forKey: .features)
    }

    func trainingBoardHold(
        presentationID: String = BoardPresentation.legacyPrimaryID
    ) throws -> BoardHold {
        if let fingerCapacity,
           !BoardHold.validFingerCapacityRange.contains(fingerCapacity) {
            throw BoardGeometryAdaptationError.invalid(
                "hold \(id) has an invalid finger capacity"
            )
        }
        guard !geometry.isEmpty else {
            throw BoardGeometryAdaptationError.invalid(
                "hold \(id) geometry must include at least one piece"
            )
        }
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
            features: features.map(Set.init),
            presentationID: presentationID
        )
    }
}

struct BoardDefinition: Codable, Hashable {
    let id: String
    let manufacturer: String
    let name: String
    let subtitle: String
    let dimensions: String
    let aspectRatio: Double
    let holds: [BoardHoldDefinition]
    let semanticHolds: [String: SemanticHoldMappingDefinition]
    let productURL: URL
    let photoAssetName: String?

    init(
        id: String,
        manufacturer: String,
        name: String,
        subtitle: String,
        dimensions: String,
        aspectRatio: Double,
        holds: [BoardHoldDefinition],
        semanticHolds: [String: SemanticHoldMappingDefinition] = [:],
        productURL: URL,
        photoAssetName: String? = nil
    ) {
        self.id = id
        self.manufacturer = manufacturer
        self.name = name
        self.subtitle = subtitle
        self.dimensions = dimensions
        self.aspectRatio = aspectRatio
        self.holds = holds
        self.semanticHolds = semanticHolds
        self.productURL = productURL
        self.photoAssetName = photoAssetName
    }

    func trainingBoard() throws -> TrainingBoard {
        TrainingBoard(
            id: id,
            manufacturer: manufacturer,
            name: name,
            subtitle: subtitle,
            dimensions: dimensions,
            aspectRatio: CGFloat(aspectRatio),
            holds: try holds.map {
                try $0.trainingBoardHold(presentationID: BoardPresentation.legacyPrimaryID)
            },
            semanticHolds: semanticHolds,
            productURL: productURL,
            photoAssetName: photoAssetName,
            presentations: [
                BoardPresentation(
                    id: BoardPresentation.legacyPrimaryID,
                    name: "Primary",
                    aspectRatio: CGFloat(aspectRatio),
                    isDefault: true
                )
            ]
        )
    }
}

struct BoardLibraryDefinition: Codable, Hashable {
    let schemaVersion: Int
    let metadata: BoardLibraryMetadata
    let boards: [BoardDefinition]

    init(schemaVersion: Int, metadata: BoardLibraryMetadata, boards: [BoardDefinition]) {
        self.schemaVersion = schemaVersion
        self.metadata = metadata
        self.boards = boards
    }

    func validationIssues() -> [BoardLibraryValidationIssue] {
        BoardLibraryValidator.issues(for: self)
    }
}

struct BoardLibraryValidationIssue: Codable, Hashable, CustomStringConvertible {
    let path: String
    let message: String

    var description: String {
        "\(path): \(message)"
    }
}

enum BoardLibraryStoreError: LocalizedError {
    case reading(Error)
    case decoding(Error)
    case validationFailed([BoardLibraryValidationIssue])

    var errorDescription: String? {
        switch self {
        case .reading(let error):
            return "The board library could not be read: \(error.localizedDescription)"
        case .decoding(let error):
            return "The board library could not be decoded: \(error.localizedDescription)"
        case .validationFailed(let issues):
            return issues.map(\.description).joined(separator: "\n")
        }
    }
}

enum BoardLibraryValidator {
    static func issues(for library: BoardLibraryDefinition) -> [BoardLibraryValidationIssue] {
        var issues: [BoardLibraryValidationIssue] = []

        if library.schemaVersion != BoardDefinitionSchema.currentVersion {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "schemaVersion",
                    message: "Expected \(BoardDefinitionSchema.currentVersion), got \(library.schemaVersion)."
                )
            )
        }

        validateMetadata(library.metadata, issues: &issues)

        var boardIDs = Set<String>()
        for (boardIndex, board) in library.boards.enumerated() {
            let path = "boards[\(boardIndex)]"
            if !boardIDs.insert(board.id).inserted {
                issues.append(
                    BoardLibraryValidationIssue(
                        path: "\(path).id",
                        message: "Duplicate board ID \"\(board.id)\"."
                    )
                )
            }
            validate(board, path: path, issues: &issues)
        }

        if let defaultBoardID = library.metadata.defaultBoardID,
           !boardIDs.contains(defaultBoardID) {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "metadata.defaultBoardID",
                    message: "Unknown board ID \"\(defaultBoardID)\"."
                )
            )
        }

        return issues
    }

    private static func validateMetadata(
        _ metadata: BoardLibraryMetadata,
        issues: inout [BoardLibraryValidationIssue]
    ) {
        validateNonEmpty(metadata.id, path: "metadata.id", label: "Library ID", issues: &issues)
        validateNonEmpty(metadata.version, path: "metadata.version", label: "Library version", issues: &issues)
        validateNonEmpty(metadata.title, path: "metadata.title", label: "Library title", issues: &issues)
    }

    private static func validate(
        _ board: BoardDefinition,
        path: String,
        issues: inout [BoardLibraryValidationIssue]
    ) {
        validateNonEmpty(board.id, path: "\(path).id", label: "Board ID", issues: &issues)
        validateNonEmpty(board.manufacturer, path: "\(path).manufacturer", label: "Manufacturer", issues: &issues)
        validateNonEmpty(board.name, path: "\(path).name", label: "Board name", issues: &issues)

        if !board.aspectRatio.isFinite || board.aspectRatio <= 0 {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "\(path).aspectRatio",
                    message: "Aspect ratio must be positive."
                )
            )
        }

        var holdIDs = Set<String>()
        for (holdIndex, hold) in board.holds.enumerated() {
            let holdPath = "\(path).holds[\(holdIndex)]"
            if !holdIDs.insert(hold.id).inserted {
                issues.append(
                    BoardLibraryValidationIssue(
                        path: "\(holdPath).id",
                        message: "Duplicate hold ID \"\(hold.id)\"."
                    )
                )
            }
            validate(hold, path: holdPath, issues: &issues)
        }

        for (semanticID, target) in board.semanticHolds {
            let semanticPath = "\(path).semanticHolds.\(semanticID)"
            validateNonEmpty(semanticID, path: semanticPath, label: "Semantic ID", issues: &issues)

            if target.holdIDs.isEmpty && target.kind == nil {
                issues.append(
                    BoardLibraryValidationIssue(
                        path: semanticPath,
                        message: "A semantic mapping needs hold IDs or a hold kind."
                    )
                )
            }
            if target.kind != nil && !target.holdIDs.isEmpty {
                issues.append(
                    BoardLibraryValidationIssue(
                        path: semanticPath,
                        message: "A semantic mapping cannot contain both hold IDs and a hold kind."
                    )
                )
            }
            if Set(target.holdIDs).count != target.holdIDs.count {
                issues.append(
                    BoardLibraryValidationIssue(
                        path: "\(semanticPath).holdIDs",
                        message: "Hold IDs must be unique."
                    )
                )
            }
            for (holdIndex, holdID) in target.holdIDs.enumerated() where !holdIDs.contains(holdID) {
                issues.append(
                    BoardLibraryValidationIssue(
                        path: "\(semanticPath).holdIDs[\(holdIndex)]",
                        message: "Unknown hold ID \"\(holdID)\" for board \"\(board.id)\"."
                    )
                )
            }
        }
    }

    private static func validate(
        _ hold: BoardHoldDefinition,
        path: String,
        issues: inout [BoardLibraryValidationIssue]
    ) {
        validateNonEmpty(hold.id, path: "\(path).id", label: "Hold ID", issues: &issues)
        validateNonEmpty(hold.name, path: "\(path).name", label: "Hold name", issues: &issues)

        let geometryValidation = BoardHoldGeometryValidator.validate(
            hold.geometry,
            holdID: hold.id,
            pieceID: { "\(hold.id)-piece-\($0)" }
        )
        if geometryValidation.isEmpty {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "\(path).geometry",
                    message: "Hold geometry must include at least one piece."
                )
            )
        }

        for (pieceIndex, pieceValidation) in geometryValidation.pieces.enumerated() {
            let piecePath = "\(path).geometry[\(pieceIndex)]"
            if pieceValidation.invalidFrameComponents.contains(.x) {
                issues.append(BoardLibraryValidationIssue(path: "\(piecePath).frame.x", message: "Frame x must be finite."))
            }
            if pieceValidation.invalidFrameComponents.contains(.y) {
                issues.append(BoardLibraryValidationIssue(path: "\(piecePath).frame.y", message: "Frame y must be finite."))
            }
            if pieceValidation.invalidFrameComponents.contains(.width) {
                issues.append(BoardLibraryValidationIssue(path: "\(piecePath).frame.width", message: "Frame width must be finite and positive."))
            }
            if pieceValidation.invalidFrameComponents.contains(.height) {
                issues.append(BoardLibraryValidationIssue(path: "\(piecePath).frame.height", message: "Frame height must be finite and positive."))
            }
            if let conversionFailureReason = pieceValidation.conversionFailureReason {
                issues.append(
                    BoardLibraryValidationIssue(
                        path: piecePath,
                        message: "Invalid hold geometry: \(conversionFailureReason)"
                    )
                )
            }
            if !pieceValidation.usesDeclaredFrame {
                issues.append(
                    BoardLibraryValidationIssue(
                        path: piecePath,
                        message: "Hold geometry frame must match its shape bounds."
                    )
                )
            }
        }

        if let fingerCapacity = hold.fingerCapacity,
           !BoardHold.validFingerCapacityRange.contains(fingerCapacity) {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "\(path).fingerCapacity",
                    message: "Finger capacity must be in \(BoardHold.validFingerCapacityRange)."
                )
            )
        }

        if let size = hold.sizeMillimeters, size <= 0 {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "\(path).sizeMillimeters",
                    message: "Hold size must be positive."
                )
            )
        }

        if let depth = hold.depthRangeMillimeters,
           depth.lowerBound <= 0 || depth.upperBound <= 0 ||
           depth.lowerBound > depth.upperBound {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "\(path).depthRangeMillimeters",
                    message: "Hold depth range must be positive and ordered."
                )
            )
        }

        if let features = hold.features, Set(features).count != features.count {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "\(path).features",
                    message: "Hold features must be unique."
                )
            )
        }
    }

    private static func validateNonEmpty(
        _ value: String,
        path: String,
        label: String,
        issues: inout [BoardLibraryValidationIssue]
    ) {
        if value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(BoardLibraryValidationIssue(path: path, message: "\(label) cannot be empty."))
        }
    }
}

struct BoardLibraryStore {
    let definition: BoardLibraryDefinition
    let boards: [TrainingBoard]

    init(definition: BoardLibraryDefinition) throws {
        let issues = definition.validationIssues()
        guard issues.isEmpty else {
            throw BoardLibraryStoreError.validationFailed(issues)
        }

        self.definition = definition
        self.boards = try definition.boards.map { try $0.trainingBoard() }
    }

    init(data: Data, decoder: JSONDecoder = JSONDecoder()) throws {
        let definition: BoardLibraryDefinition
        do {
            definition = try decoder.decode(BoardLibraryDefinition.self, from: data)
        } catch {
            throw BoardLibraryStoreError.decoding(error)
        }
        try self.init(definition: definition)
    }

    init(contentsOf url: URL, decoder: JSONDecoder = JSONDecoder()) throws {
        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            throw BoardLibraryStoreError.reading(error)
        }
        try self.init(data: data, decoder: decoder)
    }

    func encodedData(prettyPrinted: Bool = false) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = prettyPrinted ? [.prettyPrinted, .sortedKeys] : [.sortedKeys]
        return try encoder.encode(definition)
    }
}
