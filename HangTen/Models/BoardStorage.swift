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

struct BoardHoldDefinition: Codable, Hashable {
    struct Frame: Codable, Hashable {
        let x: Double
        let y: Double
        let width: Double
        let height: Double

        init(x: Double, y: Double, width: Double, height: Double) {
            self.x = x
            self.y = y
            self.width = width
            self.height = height
        }

        var holdFrame: HoldFrame {
            HoldFrame(
                x: CGFloat(x),
                y: CGFloat(y),
                width: CGFloat(width),
                height: CGFloat(height)
            )
        }
    }

    let id: String
    let name: String
    let shortLabel: String
    let detail: String
    let kind: HoldKind
    let frame: Frame
    let sizeMillimeters: Int?
    let gripType: GripType?
    let fingerCapacity: Int?
    let cueStyle: String?
    let features: [HoldFeature]?

    init(
        id: String,
        name: String,
        shortLabel: String,
        detail: String,
        kind: HoldKind,
        frame: Frame,
        sizeMillimeters: Int? = nil,
        gripType: GripType? = nil,
        fingerCapacity: Int? = nil,
        cueStyle: String? = nil,
        features: [HoldFeature]? = nil
    ) {
        self.id = id
        self.name = name
        self.shortLabel = shortLabel
        self.detail = detail
        self.kind = kind
        self.frame = frame
        self.sizeMillimeters = sizeMillimeters
        self.gripType = gripType
        self.fingerCapacity = fingerCapacity
        self.cueStyle = cueStyle
        self.features = features
    }

    func trainingBoardHold() -> BoardHold {
        BoardHold(
            id: id,
            name: name,
            shortLabel: shortLabel,
            detail: detail,
            kind: kind,
            frame: frame.holdFrame,
            sizeMillimeters: sizeMillimeters,
            gripType: gripType ?? .openHand,
            fingerCapacity: fingerCapacity ?? 4,
            cueStyle: cueStyle.flatMap(HoldCueStyle.init(rawValue:)),
            features: features.map(Set.init)
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

    func trainingBoard() -> TrainingBoard {
        TrainingBoard(
            id: id,
            manufacturer: manufacturer,
            name: name,
            subtitle: subtitle,
            dimensions: dimensions,
            aspectRatio: CGFloat(aspectRatio),
            holds: holds.map { $0.trainingBoardHold() },
            semanticHolds: semanticHolds,
            productURL: productURL,
            photoAssetName: photoAssetName
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
        validateNonEmpty(hold.shortLabel, path: "\(path).shortLabel", label: "Hold short label", issues: &issues)

        let frame = hold.frame
        if !frame.x.isFinite || !(0...1).contains(frame.x) {
            issues.append(BoardLibraryValidationIssue(path: "\(path).frame.x", message: "Frame x must be between 0 and 1."))
        }
        if !frame.y.isFinite || !(0...1).contains(frame.y) {
            issues.append(BoardLibraryValidationIssue(path: "\(path).frame.y", message: "Frame y must be between 0 and 1."))
        }
        if !frame.width.isFinite || frame.width <= 0 || frame.x + frame.width > 1 {
            issues.append(BoardLibraryValidationIssue(path: "\(path).frame.width", message: "Frame width must fit within normalized bounds."))
        }
        if !frame.height.isFinite || frame.height <= 0 || frame.y + frame.height > 1 {
            issues.append(BoardLibraryValidationIssue(path: "\(path).frame.height", message: "Frame height must fit within normalized bounds."))
        }

        let fingerCapacity = hold.fingerCapacity ?? 4
        if !BoardHold.validFingerCapacityRange.contains(fingerCapacity) {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "\(path).fingerCapacity",
                    message: "Finger capacity must be in \(BoardHold.validFingerCapacityRange)."
                )
            )
        }

        if let cueStyle = hold.cueStyle, HoldCueStyle(rawValue: cueStyle) == nil {
            issues.append(
                BoardLibraryValidationIssue(
                    path: "\(path).cueStyle",
                    message: "Unknown hold cue style \"\(cueStyle)\"."
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
        self.boards = definition.boards.map { $0.trainingBoard() }
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
