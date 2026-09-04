import Foundation

struct BoardEditableDocument: Equatable, Decodable {
    var id: String
    var manufacturer: String
    var name: String
    var subtitle: String
    var productURL: URL
    var dimensions: String?
    var aspectRatio: Double
    var equipmentObjects: [EquipmentObject]
    var holds: [BoardEditableHold]
    var presentations: [BoardEditablePresentation]
    var positions: [BoardPosition]?
    var positionTransitions: [BoardPositionTransition]?

    private enum CodingKeys: String, CodingKey {
        case id
        case manufacturer
        case name
        case subtitle
        case productURL
        case dimensions
        case aspectRatio
        case equipmentObjects
        case holds
        case presentations
        case positions
        case positionTransitions
    }

    init(
        id: String,
        manufacturer: String,
        name: String,
        subtitle: String,
        productURL: URL,
        dimensions: String?,
        aspectRatio: Double,
        equipmentObjects: [EquipmentObject] = [
            .init(id: "primary", missingHandCapacityPolicy: .unavailable)
        ],
        holds: [BoardEditableHold],
        presentations: [BoardEditablePresentation],
        positions: [BoardPosition]? = nil,
        positionTransitions: [BoardPositionTransition]? = nil
    ) {
        self.id = id
        self.manufacturer = manufacturer
        self.name = name
        self.subtitle = subtitle
        self.productURL = productURL
        self.dimensions = dimensions
        self.aspectRatio = aspectRatio
        self.equipmentObjects = equipmentObjects
        self.holds = holds
        self.presentations = presentations
        self.positions = positions
        self.positionTransitions = positionTransitions
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "id", "manufacturer", "name", "subtitle", "productURL",
            "dimensions", "aspectRatio", "equipmentObjects", "holds", "presentations",
            "positions", "positionTransitions"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        manufacturer = try container.decode(String.self, forKey: .manufacturer)
        name = try container.decode(String.self, forKey: .name)
        subtitle = try container.decode(String.self, forKey: .subtitle)
        productURL = try container.decode(URL.self, forKey: .productURL)
        dimensions = try container.decodeIfPresent(String.self, forKey: .dimensions)
        aspectRatio = try container.decode(Double.self, forKey: .aspectRatio)
        equipmentObjects = container.contains(.equipmentObjects)
            ? try container.decode(
                [BoardEditableEquipmentObjectDocument].self,
                forKey: .equipmentObjects
            ).map(\.equipmentObject)
            : [.init(id: "primary")]
        holds = try container.decode([BoardEditableHold].self, forKey: .holds)
        presentations = try container.decode([BoardEditablePresentation].self, forKey: .presentations)
        positions = container.contains(.positions)
            ? try container.decode(
                [BoardEditablePositionDocument].self,
                forKey: .positions
            ).map(\.position)
            : nil
        positionTransitions = container.contains(.positionTransitions)
            ? try container.decode(
                [BoardEditablePositionTransitionDocument].self,
                forKey: .positionTransitions
            ).map(\.transition)
            : nil
    }

    init(data: Data) throws {
        self = try JSONDecoder().decode(BoardEditableDocument.self, from: data)
    }
}

private struct BoardEditablePositionDocument: Decodable {
    let id: String
    let presentationID: String

    private enum CodingKeys: String, CodingKey {
        case id
        case presentationID
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["id", "presentationID"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        presentationID = try container.decode(String.self, forKey: .presentationID)
    }

    var position: BoardPosition {
        BoardPosition(id: id, presentationID: presentationID)
    }
}

private struct BoardEditablePositionTransitionDocument: Decodable {
    let fromPositionID: String
    let toPositionID: String
    let kind: BoardPositionTransitionKind

    private enum CodingKeys: String, CodingKey {
        case fromPositionID
        case toPositionID
        case kind
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "fromPositionID", "toPositionID", "kind"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        fromPositionID = try container.decode(String.self, forKey: .fromPositionID)
        toPositionID = try container.decode(String.self, forKey: .toPositionID)
        kind = try container.decode(BoardPositionTransitionKind.self, forKey: .kind)
    }

    var transition: BoardPositionTransition {
        BoardPositionTransition(
            fromPositionID: fromPositionID,
            toPositionID: toPositionID,
            kind: kind
        )
    }
}

private struct BoardEditableEquipmentObjectDocument: Decodable {
    let id: String
    let missingHandCapacityPolicy: MissingHandCapacityPolicy

    private enum CodingKeys: String, CodingKey {
        case id
        case missingHandCapacityPolicy
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["id", "missingHandCapacityPolicy"])
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

struct BoardEditablePresentation: Equatable, Decodable {
    var id: String
    var name: String
    var assetPath: String
    var aspectRatio: Double
    var isDefault: Bool
    /// An alternate rendering of a canonical presentation, such as an
    /// upside-down mounting. Holds remain owned by the canonical source.
    var sourcePresentationID: String?
    var availableHoldIDs: [String]?
    var isInverted: Bool
    var rotationDegrees: Double?
    var geometryRotationAnchor: BoardGeometryRotationAnchor?
    var cordRig: BoardCordRig?

    fileprivate var declaresIsInverted: Bool

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case assetPath
        case aspectRatio
        case isDefault = "default"
        case sourcePresentationID
        case availableHoldIDs
        case isInverted
        case rotationDegrees
        case geometryRotationAnchor
        case cordRig
    }

    init(
        id: String,
        name: String,
        assetPath: String,
        aspectRatio: Double,
        isDefault: Bool,
        sourcePresentationID: String? = nil,
        availableHoldIDs: [String]? = nil,
        isInverted: Bool = false,
        rotationDegrees: Double? = nil,
        geometryRotationAnchor: BoardGeometryRotationAnchor? = nil,
        cordRig: BoardCordRig? = nil
    ) {
        self.id = id
        self.name = name
        self.assetPath = assetPath
        self.aspectRatio = aspectRatio
        self.isDefault = isDefault
        self.sourcePresentationID = sourcePresentationID
        self.availableHoldIDs = availableHoldIDs
        self.isInverted = isInverted
        self.rotationDegrees = rotationDegrees
        self.geometryRotationAnchor = geometryRotationAnchor
        self.cordRig = cordRig
        self.declaresIsInverted = isInverted
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "id", "name", "assetPath", "aspectRatio", "default",
            "sourcePresentationID", "availableHoldIDs", "isInverted", "rotationDegrees",
            "geometryRotationAnchor", "cordRig"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        assetPath = try container.decode(String.self, forKey: .assetPath)
        aspectRatio = try container.decode(Double.self, forKey: .aspectRatio)
        isDefault = try container.decode(Bool.self, forKey: .isDefault)
        sourcePresentationID = try container.decodeIfPresent(
            String.self,
            forKey: .sourcePresentationID
        )
        availableHoldIDs = container.contains(.availableHoldIDs)
            ? try container.decode([String].self, forKey: .availableHoldIDs)
            : nil
        declaresIsInverted = container.contains(.isInverted)
        isInverted = try container.decodeIfPresent(Bool.self, forKey: .isInverted) ?? false
        rotationDegrees = try container.decodeIfPresent(
            Double.self,
            forKey: .rotationDegrees
        )
        geometryRotationAnchor = container.contains(.geometryRotationAnchor)
            ? try container.decode(
                BoardEditableGeometryRotationAnchorDocument.self,
                forKey: .geometryRotationAnchor
            ).rotationAnchor
            : nil
        cordRig = container.contains(.cordRig)
            ? try container.decode(
                BoardEditableCordRigDocument.self,
                forKey: .cordRig
            ).cordRig
            : nil
    }

    var resolvedRotationDegrees: Double {
        rotationDegrees ?? (isInverted ? 180 : 0)
    }
}

private struct BoardEditableCordPointDocument: Decodable {
    let x: Double
    let y: Double

    private enum CodingKeys: String, CodingKey {
        case x
        case y
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["x", "y"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        x = try container.decode(Double.self, forKey: .x)
        y = try container.decode(Double.self, forKey: .y)
    }

    var cordPoint: BoardCordPoint {
        BoardCordPoint(x: CGFloat(x), y: CGFloat(y))
    }
}

private struct BoardEditableCordSizeDocument: Decodable {
    let width: Double
    let height: Double

    private enum CodingKeys: String, CodingKey {
        case width
        case height
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["width", "height"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        width = try container.decode(Double.self, forKey: .width)
        height = try container.decode(Double.self, forKey: .height)
    }

    var cordSize: BoardCordSize {
        BoardCordSize(width: CGFloat(width), height: CGFloat(height))
    }
}

private struct BoardEditableCordRectDocument: Decodable {
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
        try decoder.rejectUnknownEditorKeys(["x", "y", "width", "height"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        x = try container.decode(Double.self, forKey: .x)
        y = try container.decode(Double.self, forKey: .y)
        width = try container.decode(Double.self, forKey: .width)
        height = try container.decode(Double.self, forKey: .height)
    }

    var cordRect: BoardCordRect {
        BoardCordRect(
            x: CGFloat(x),
            y: CGFloat(y),
            width: CGFloat(width),
            height: CGFloat(height)
        )
    }
}

private struct BoardEditableCordRigDocument: Decodable {
    let sceneSize: BoardEditableCordSizeDocument
    let sourceFrame: BoardEditableCordRectDocument
    let innerFaceFrame: BoardEditableCordRectDocument
    let attachmentPoints: [BoardEditableCordPointDocument]
    let pullPoint: BoardEditableCordPointDocument
    let eyeletRadius: Double

    private enum CodingKeys: String, CodingKey {
        case type
        case sceneSize
        case sourceFrame
        case innerFaceFrame
        case attachmentPoints
        case pullPoint
        case eyeletRadius
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "type", "sceneSize", "sourceFrame", "innerFaceFrame",
            "attachmentPoints", "pullPoint", "eyeletRadius",
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)
        guard type == "directTwoAnchor" else {
            throw DecodingError.dataCorruptedError(
                forKey: .type,
                in: container,
                debugDescription: "Unsupported cord rig type \(type)"
            )
        }
        sceneSize = try container.decode(
            BoardEditableCordSizeDocument.self,
            forKey: .sceneSize
        )
        sourceFrame = try container.decode(
            BoardEditableCordRectDocument.self,
            forKey: .sourceFrame
        )
        innerFaceFrame = try container.decode(
            BoardEditableCordRectDocument.self,
            forKey: .innerFaceFrame
        )
        attachmentPoints = try container.decode(
            [BoardEditableCordPointDocument].self,
            forKey: .attachmentPoints
        )
        pullPoint = try container.decode(
            BoardEditableCordPointDocument.self,
            forKey: .pullPoint
        )
        eyeletRadius = try container.decode(Double.self, forKey: .eyeletRadius)
    }

    var cordRig: BoardCordRig {
        .directTwoAnchor(
            BoardDirectTwoAnchorCordRig(
                sceneSize: sceneSize.cordSize,
                sourceFrame: sourceFrame.cordRect,
                innerFaceFrame: innerFaceFrame.cordRect,
                attachmentPoints: attachmentPoints.map(\.cordPoint),
                pullPoint: pullPoint.cordPoint,
                eyeletRadius: CGFloat(eyeletRadius)
            )
        )
    }
}

private struct BoardEditableGeometryRotationAnchorDocument: Decodable {
    let x: Double
    let y: Double

    private enum CodingKeys: String, CodingKey {
        case x
        case y
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["x", "y"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        x = try container.decode(Double.self, forKey: .x)
        y = try container.decode(Double.self, forKey: .y)
    }

    var rotationAnchor: BoardGeometryRotationAnchor {
        BoardGeometryRotationAnchor(x: x, y: y)
    }
}

struct BoardEditableHold: Equatable, Decodable {
    var id: String
    var name: String
    /// Editor packages may omit `kind` while metadata is being completed.
    /// Training-board decoding remains strict in `BoardPackageStore`.
    var kind: HoldKind?
    var sloper: SloperMetadata?
    var sizeMillimeters: Double?
    var depthRangeMillimeters: BoardEditableMillimeterRange?
    var gripType: GripType?
    var fingerCapacity: Int?
    var handCapacity: Int?
    var features: [HoldFeature]?
    var pairedHoldID: String?
    var declaresPairedHoldID: Bool
    var equipmentObjectID: String
    var presentationID: String
    var geometry: [BoardEditablePiece]

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case kind
        case sloper
        case geometry
        case sizeMillimeters
        case depthRangeMillimeters
        case gripType
        case fingerCapacity
        case handCapacity
        case features
        case pairedHoldID
        case equipmentObjectID
        case presentationID
    }

    init(
        id: String,
        name: String,
        kind: HoldKind?,
        sloper: SloperMetadata? = nil,
        sizeMillimeters: Double? = nil,
        depthRangeMillimeters: BoardEditableMillimeterRange? = nil,
        gripType: GripType? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        features: [HoldFeature]? = nil,
        pairedHoldID: String? = nil,
        equipmentObjectID: String = "primary",
        presentationID: String,
        geometry: [BoardEditablePiece]
    ) {
        self.id = id
        self.name = name
        self.kind = kind
        self.sloper = sloper
        self.sizeMillimeters = sizeMillimeters
        self.depthRangeMillimeters = depthRangeMillimeters
        self.gripType = gripType
        self.fingerCapacity = fingerCapacity
        self.handCapacity = handCapacity
        self.features = features
        self.pairedHoldID = pairedHoldID
        declaresPairedHoldID = pairedHoldID != nil
        self.equipmentObjectID = equipmentObjectID
        self.presentationID = presentationID
        self.geometry = geometry
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "id", "name", "kind", "geometry", "sizeMillimeters",
            "depthRangeMillimeters", "gripType", "fingerCapacity", "handCapacity",
            "features", "pairedHoldID", "equipmentObjectID", "presentationID", "sloper"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        kind = container.contains(.kind)
            ? try container.decode(HoldKind.self, forKey: .kind)
            : nil
        sloper = container.contains(.sloper)
            ? try container.decode(SloperMetadata.self, forKey: .sloper)
            : nil
        if sloper != nil, kind != .sloper {
            throw DecodingError.dataCorruptedError(
                forKey: .sloper,
                in: container,
                debugDescription: "Sloper metadata is only valid for sloper holds."
            )
        }
        geometry = try container.decode([BoardEditablePiece].self, forKey: .geometry)
        sizeMillimeters = try container.decodeIfPresent(Double.self, forKey: .sizeMillimeters)
        depthRangeMillimeters = try container.decodeIfPresent(
            BoardEditableMillimeterRange.self,
            forKey: .depthRangeMillimeters
        )
        gripType = try container.decodeIfPresent(GripType.self, forKey: .gripType)
        fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        handCapacity = try container.decodeIfPresent(Int.self, forKey: .handCapacity)
        features = try container.decodeIfPresent([HoldFeature].self, forKey: .features)
        declaresPairedHoldID = container.contains(.pairedHoldID)
        pairedHoldID = declaresPairedHoldID
            ? try container.decode(String.self, forKey: .pairedHoldID)
            : nil
        equipmentObjectID = container.contains(.equipmentObjectID)
            ? try container.decode(String.self, forKey: .equipmentObjectID)
            : "primary"
        presentationID = try container.decode(String.self, forKey: .presentationID)
    }
}

struct BoardEditableMillimeterRange: Equatable, Decodable {
    var lowerBound: Double
    var upperBound: Double

    private enum CodingKeys: String, CodingKey {
        case lowerBound
        case upperBound
    }

    init(lowerBound: Double, upperBound: Double) {
        self.lowerBound = lowerBound
        self.upperBound = upperBound
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["lowerBound", "upperBound"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        lowerBound = try container.decode(Double.self, forKey: .lowerBound)
        upperBound = try container.decode(Double.self, forKey: .upperBound)
    }
}

struct BoardEditablePiece: Equatable, Decodable {
    var frame: BoardPackageFrameDocument
    var shape: BoardGeometryShapeDocument
    var shapeConstraint: ShapeConstraint?
    var treatment: BoardGeometryTreatmentDocument?

    private enum CodingKeys: String, CodingKey {
        case frame
        case shape
        case shapeConstraint
        case treatment
    }

    init(
        frame: BoardPackageFrameDocument,
        shape: BoardGeometryShapeDocument,
        shapeConstraint: ShapeConstraint?,
        treatment: BoardGeometryTreatmentDocument?
    ) {
        self.frame = frame
        self.shape = shape
        self.shapeConstraint = shapeConstraint
        self.treatment = treatment
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["frame", "shape", "shapeConstraint", "treatment"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        frame = try container.decode(BoardPackageFrameDocument.self, forKey: .frame)
        shape = try container.decode(BoardGeometryShapeDocument.self, forKey: .shape)
        shapeConstraint = try container.decodeIfPresent(ShapeConstraint.self, forKey: .shapeConstraint)
        treatment = try container.decodeIfPresent(BoardGeometryTreatmentDocument.self, forKey: .treatment)
    }
}

extension ShapeConstraint: Decodable {
    private enum ConstraintCodingKeys: String, CodingKey {
        case shape
        case rotationDegrees
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["shape", "rotationDegrees"])
        let container = try decoder.container(keyedBy: ConstraintCodingKeys.self)
        let rawShape = try container.decode(String.self, forKey: .shape)
        guard let shape = ShapeConstraintShape(rawValue: rawShape) else {
            throw DecodingError.dataCorruptedError(
                forKey: .shape,
                in: container,
                debugDescription: "invalid shape constraint shape \(rawShape)"
            )
        }
        let rotationDegrees = try container.decode(Double.self, forKey: .rotationDegrees)
        guard rotationDegrees.isFinite, (-180.0..<180.0).contains(rotationDegrees) else {
            throw DecodingError.dataCorruptedError(
                forKey: .rotationDegrees,
                in: container,
                debugDescription: "rotationDegrees must be finite and in [-180, 180)"
            )
        }
        self.init(shape: shape, rotationDegrees: rotationDegrees)
    }
}

private struct EditorCodingKey: CodingKey {
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
    func rejectUnknownEditorKeys(_ allowedKeys: Set<String>) throws {
        let container = try container(keyedBy: EditorCodingKey.self)
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

enum BoardPackageWriterError: Error, Equatable, LocalizedError {
    case invalid(String)

    var errorDescription: String? {
        switch self {
        case .invalid(let reason): reason
        }
    }
}

enum BoardPackageWriter {
    private static let presentationAspectRatioRelativeTolerance = 0.001

    static func data(for document: BoardEditableDocument) throws -> Data {
        try validate(document)
        return CanonicalJSONSerializer.data(canonicalValue(document))
    }

    static func validate(_ document: BoardEditableDocument) throws {
        guard document.id.isEditorBoardIdentifier else {
            throw invalid("board ID must be identifier-shaped", document)
        }
        let requiredStrings = [
            document.manufacturer,
            document.name,
            document.subtitle
        ]
        guard requiredStrings.allSatisfy({ !$0.isEmpty }) else {
            throw invalid("required metadata must not be empty", document)
        }
        if let dimensions = document.dimensions, dimensions.isEmpty {
            throw invalid("dimensions must not be empty when present", document)
        }
        guard document.productURL.scheme == "https", document.productURL.host != nil else {
            throw invalid("product URL must be absolute HTTPS", document)
        }
        guard document.aspectRatio.isFinite, document.aspectRatio > 0 else {
            throw invalid("aspect ratio must be positive", document)
        }
        guard !document.presentations.isEmpty else {
            throw invalid("presentations must not be empty", document)
        }
        let equipmentObjectIDs = try validateEquipmentObjects(in: document)
        var presentationIDs = Set<String>()
        var defaultPresentationCount = 0
        for presentation in document.presentations {
            guard presentation.id.isEditorBoardIdentifier, !presentation.name.isEmpty else {
                throw invalid("presentation \(presentation.id) metadata must be non-empty and identifier-shaped", document)
            }
            guard presentationIDs.insert(presentation.id).inserted else {
                throw invalid("presentation ID \(presentation.id) is duplicated", document)
            }
            guard presentation.assetPath.hasPrefix("assets/"),
                  !presentation.assetPath.hasSuffix("/"),
                  !presentation.assetPath.contains("..") else {
                throw invalid("presentation \(presentation.id) assetPath must stay inside the package assets directory", document)
            }
            guard presentation.aspectRatio.isFinite, presentation.aspectRatio > 0 else {
                throw invalid("presentation \(presentation.id) aspect ratio must be positive", document)
            }
            if let cordRig = presentation.cordRig {
                guard presentation.sourcePresentationID == nil,
                      presentation.resolvedRotationDegrees == 0 else {
                    throw invalid(
                        "presentation \(presentation.id).cordRig must be owned "
                            + "by a canonical non-inverted presentation",
                        document
                    )
                }
                try validateCordRig(
                    cordRig,
                    presentation: presentation,
                    in: document
                )
            }
            if presentation.declaresIsInverted,
               presentation.rotationDegrees != nil {
                throw invalid(
                    "presentation \(presentation.id) must not declare both isInverted and rotationDegrees",
                    document
                )
            }
            if let rotationDegrees = presentation.rotationDegrees {
                guard rotationDegrees.isFinite,
                      (0..<360).contains(rotationDegrees) else {
                    throw invalid(
                        "presentation \(presentation.id).rotationDegrees must be finite and normalized to [0, 360)",
                        document
                    )
                }
                guard presentation.sourcePresentationID != nil else {
                    throw invalid(
                        "presentation \(presentation.id).rotationDegrees requires sourcePresentationID",
                        document
                    )
                }
            }
            if let anchor = presentation.geometryRotationAnchor {
                guard anchor.hasFiniteNormalizedCoordinates else {
                    throw invalid(
                        "presentation \(presentation.id).geometryRotationAnchor must contain finite normalized coordinates",
                        document
                    )
                }
                guard presentation.sourcePresentationID != nil else {
                    throw invalid(
                        "presentation \(presentation.id).geometryRotationAnchor requires sourcePresentationID",
                        document
                    )
                }
                guard presentation.resolvedRotationDegrees != 0 else {
                    throw invalid(
                        "presentation \(presentation.id).geometryRotationAnchor requires isInverted true or nonzero rotationDegrees",
                        document
                    )
                }
            }
            if presentation.isDefault {
                defaultPresentationCount += 1
            }
            if let availableHoldIDs = presentation.availableHoldIDs {
                guard !availableHoldIDs.isEmpty else {
                    throw invalid(
                        "presentation \(presentation.id).availableHoldIDs must not be empty",
                        document
                    )
                }
                guard Set(availableHoldIDs).count == availableHoldIDs.count else {
                    throw invalid(
                        "presentation \(presentation.id).availableHoldIDs must be unique",
                        document
                    )
                }
                guard availableHoldIDs.allSatisfy(\.isEditorBoardIdentifier) else {
                    throw invalid(
                        "presentation \(presentation.id).availableHoldIDs must be identifier-shaped",
                        document
                    )
                }
            }
        }
        guard defaultPresentationCount == 1 else {
            throw invalid("presentations must declare exactly one default", document)
        }

        let presentationsByID = Dictionary(
            uniqueKeysWithValues: document.presentations.map { ($0.id, $0) }
        )
        for presentation in document.presentations {
            if let sourcePresentationID = presentation.sourcePresentationID {
                guard sourcePresentationID != presentation.id,
                      let sourcePresentation = presentationsByID[sourcePresentationID],
                      sourcePresentation.sourcePresentationID == nil else {
                    throw invalid(
                        "presentation \(presentation.id) must reference a canonical presentation",
                        document
                    )
                }
                guard BoardAliasGeometryValidation.aspectRatiosMatch(
                    presentation.aspectRatio,
                    sourcePresentation.aspectRatio
                ) else {
                    throw invalid(
                        "presentation \(presentation.id).aspectRatio must match source presentation aspectRatio",
                        document
                    )
                }
                if let rotationDegrees = presentation.rotationDegrees {
                    guard presentation.assetPath == sourcePresentation.assetPath else {
                        throw invalid(
                            "presentation \(presentation.id).assetPath must reuse source presentation assetPath for an explicit rotation",
                            document
                        )
                    }
                    guard rotationDegrees == 0 || rotationDegrees == 180
                            || sourcePresentation.cordRig != nil else {
                        throw invalid(
                            "presentation \(presentation.id) non-180 rotation requires a canonical cordRig to prevent artwork clipping",
                            document
                        )
                    }
                }
            }
            let resolvedCordRig = presentation.sourcePresentationID.flatMap {
                presentationsByID[$0]?.cordRig
            } ?? presentation.cordRig
            if case .directTwoAnchor(let rig) = resolvedCordRig {
                try validateCordPresentation(
                    rig,
                    presentation: presentation,
                    in: document
                )
            }
        }

        guard !document.holds.isEmpty else {
            throw invalid("holds must not be empty", document)
        }
        let positions = document.positions ?? document.presentations.map {
            BoardPosition(id: $0.id, presentationID: $0.id)
        }
        if document.positions != nil, positions.isEmpty {
            throw invalid("positions must not be empty", document)
        }
        var positionIDs = Set<String>()
        for position in positions {
            guard position.id.isEditorBoardIdentifier else {
                throw invalid("position ID must be identifier-shaped", document)
            }
            guard positionIDs.insert(position.id).inserted else {
                throw invalid("duplicate position id", document)
            }
            guard let presentation = presentationsByID[position.presentationID] else {
                throw invalid("position \(position.id) references unknown presentationID", document)
            }
            let canonicalPresentationID = presentation.sourcePresentationID ?? presentation.id
            guard document.holds.contains(where: { $0.presentationID == canonicalPresentationID }) else {
                throw invalid("position \(position.id) must own at least one hold", document)
            }
        }
        if let transitions = document.positionTransitions {
            var transitionPairs = Set<[String]>()
            for transition in transitions {
                guard positionIDs.contains(transition.fromPositionID) else {
                    throw invalid("position transition references unknown fromPositionID", document)
                }
                guard positionIDs.contains(transition.toPositionID) else {
                    throw invalid("position transition references unknown toPositionID", document)
                }
                guard transition.fromPositionID != transition.toPositionID else {
                    throw invalid("position transition must not be self-edge", document)
                }
                let pair = [transition.fromPositionID, transition.toPositionID]
                guard transitionPairs.insert(pair).inserted else {
                    throw invalid("duplicate position transition", document)
                }
            }
        }
        var holdIDs = Set<String>()
        for hold in document.holds {
            guard hold.id.isEditorBoardIdentifier, !hold.name.isEmpty else {
                throw invalid("hold \(hold.id) metadata must be non-empty and identifier-shaped", document)
            }
            guard holdIDs.insert(hold.id).inserted else {
                throw invalid("hold ID \(hold.id) is duplicated", document)
            }
            try validateEquipmentObjectReference(
                for: hold,
                validIDs: equipmentObjectIDs,
                in: document
            )
            guard presentationIDs.contains(hold.presentationID) else {
                throw invalid("hold \(hold.id) references unknown presentation \(hold.presentationID)", document)
            }
            guard presentationsByID[hold.presentationID]?.sourcePresentationID == nil else {
                throw invalid(
                    "hold \(hold.id) must be owned by a canonical presentation",
                    document
                )
            }
            if hold.sizeMillimeters != nil && hold.depthRangeMillimeters != nil {
                throw invalid("hold \(hold.id) must not specify both a size and depth range", document)
            }
            if let sloper = hold.sloper {
                guard hold.kind == .sloper else {
                    throw invalid("hold \(hold.id) has sloper metadata but is not a sloper", document)
                }
                guard sloper.isValid else {
                    throw invalid("hold \(hold.id) has invalid sloper metadata", document)
                }
            }
            if hold.kind == .gaston {
                guard let pairedHoldID = hold.pairedHoldID,
                      pairedHoldID.isEditorBoardIdentifier else {
                    throw invalid(
                        "gaston hold \(hold.id) must declare an identifier-shaped pairedHoldID",
                        document
                    )
                }
            } else if hold.declaresPairedHoldID {
                throw invalid("non-gaston hold \(hold.id) must not declare pairedHoldID", document)
            }
            if let fingerCapacity = hold.fingerCapacity,
               !BoardHold.validFingerCapacityRange.contains(fingerCapacity) {
                throw invalid("hold \(hold.id) has an invalid finger capacity", document)
            }
            if let handCapacity = hold.handCapacity,
               !BoardHold.validHandCapacityRange.contains(handCapacity) {
                throw invalid("hold \(hold.id) has an invalid hand capacity", document)
            }
            if let size = hold.sizeMillimeters, !size.isFinite || size <= 0 {
                throw invalid("hold \(hold.id) has a non-positive size", document)
            }
            if let depthRange = hold.depthRangeMillimeters,
               !depthRange.lowerBound.isFinite ||
               !depthRange.upperBound.isFinite ||
               depthRange.lowerBound <= 0 ||
               depthRange.upperBound <= 0 ||
               depthRange.lowerBound > depthRange.upperBound {
                throw invalid("hold \(hold.id) has an invalid depth range", document)
            }
            if let features = hold.features, Set(features).count != features.count {
                throw invalid("hold \(hold.id) has duplicate features", document)
            }
            guard !hold.geometry.isEmpty else {
                throw invalid("hold \(hold.id) geometry must include at least one piece", document)
            }
            for (pieceIndex, piece) in hold.geometry.enumerated() {
                try validatePiece(piece, holdID: hold.id, pieceIndex: pieceIndex)
            }
        }
        guard !document.holds.isEmpty else {
            throw invalid("holds must not be empty", document)
        }
        try validateEquipmentObjectOwnership(in: document)
        let holdsByID = Dictionary(uniqueKeysWithValues: document.holds.map { ($0.id, $0) })
        for presentation in document.presentations {
            guard let availableHoldIDs = presentation.availableHoldIDs else { continue }
            let canonicalPresentationID = presentation.sourcePresentationID ?? presentation.id
            for holdID in availableHoldIDs {
                guard let hold = holdsByID[holdID] else {
                    throw invalid(
                        "presentation \(presentation.id).availableHoldIDs references unknown hold \(holdID)",
                        document
                    )
                }
                guard hold.presentationID == canonicalPresentationID else {
                    throw invalid(
                        "presentation \(presentation.id).availableHoldIDs hold \(holdID) "
                            + "must belong to canonical presentation \(canonicalPresentationID)",
                        document
                    )
                }
            }
        }
        for hold in document.holds where hold.kind == .gaston {
            let pairedHoldID = hold.pairedHoldID!
            guard pairedHoldID != hold.id,
                  let pairedHold = holdsByID[pairedHoldID] else {
                throw invalid("gaston hold \(hold.id) must pair with a distinct existing hold", document)
            }
            guard pairedHold.kind == .gaston,
                  pairedHold.pairedHoldID == hold.id else {
                throw invalid("gaston hold \(hold.id) must have a reciprocal gaston pair", document)
            }
        }
        try validateAliasProjections(in: document)
    }

    private static func validateCordRig(
        _ cordRig: BoardCordRig,
        presentation: BoardEditablePresentation,
        in document: BoardEditableDocument
    ) throws {
        let rig: BoardDirectTwoAnchorCordRig
        switch cordRig {
        case .directTwoAnchor(let value):
            rig = value
        }

        let sceneSizeIsValid = rig.sceneSize.width.isFinite
            && rig.sceneSize.height.isFinite
            && rig.sceneSize.width > 0
            && rig.sceneSize.height > 0
        let sourceFrameIsValid = rig.sourceFrame.x.isFinite
            && rig.sourceFrame.y.isFinite
            && rig.sourceFrame.width.isFinite
            && rig.sourceFrame.height.isFinite
            && rig.sourceFrame.width > 0
            && rig.sourceFrame.height > 0
        let innerFaceFrameIsValid = rig.innerFaceFrame.x.isFinite
            && rig.innerFaceFrame.y.isFinite
            && rig.innerFaceFrame.width.isFinite
            && rig.innerFaceFrame.height.isFinite
            && rig.innerFaceFrame.width > 0
            && rig.innerFaceFrame.height > 0
        guard sceneSizeIsValid, sourceFrameIsValid, innerFaceFrameIsValid else {
            throw invalid(
                "presentation \(presentation.id).cordRig must contain finite positive sizes",
                document
            )
        }
        guard rig.attachmentPoints.count == 2,
              rig.attachmentPoints.allSatisfy({ $0.x.isFinite && $0.y.isFinite }),
              rig.attachmentPoints[0] != rig.attachmentPoints[1] else {
            throw invalid(
                "presentation \(presentation.id).cordRig must contain two distinct finite attachment points",
                document
            )
        }
        guard rig.pullPoint.x.isFinite,
              rig.pullPoint.y.isFinite,
              rig.eyeletRadius.isFinite,
              rig.eyeletRadius > 0 else {
            throw invalid(
                "presentation \(presentation.id).cordRig pull point must be finite "
                    + "and eyelet radius must be finite and positive",
                document
            )
        }
        let sceneAspectRatio = Double(rig.sceneSize.width / rig.sceneSize.height)
        let relativeError = abs(presentation.aspectRatio - sceneAspectRatio) / sceneAspectRatio
        guard relativeError <= presentationAspectRatioRelativeTolerance else {
            throw invalid(
                "presentation \(presentation.id).aspectRatio must match cordRig.sceneSize within 0.1%",
                document
            )
        }
    }

    private static func validateCordPresentation(
        _ rig: BoardDirectTwoAnchorCordRig,
        presentation: BoardEditablePresentation,
        in document: BoardEditableDocument
    ) throws {
        let failure = BoardCordRigPresentationValidation.failure(
            for: rig,
            rotationDegrees: presentation.resolvedRotationDegrees,
            rotationAnchor: presentation.geometryRotationAnchor ?? .center
        )
        switch failure {
        case .drawingOutsideScene:
            throw invalid(
                "presentation \(presentation.id) cord drawing must remain inside sceneSize",
                document
            )
        case .pullExitsNotAboveAttachments:
            throw invalid(
                "presentation \(presentation.id) cord pull exits must remain above both attachment points",
                document
            )
        case nil:
            return
        }
    }

    private static func validateAliasProjections(in document: BoardEditableDocument) throws {
        let presentationsByID = Dictionary(
            uniqueKeysWithValues: document.presentations.map { ($0.id, $0) }
        )
        for presentation in document.presentations where presentation.resolvedRotationDegrees != 0 {
            guard let sourcePresentationID = presentation.sourcePresentationID else {
                continue
            }
            let anchor = presentation.geometryRotationAnchor ?? .center
            let resolvedCordRig = presentationsByID[sourcePresentationID]?.cordRig
            let availableHoldIDs = presentation.availableHoldIDs.map(Set.init)
            for hold in document.holds where hold.presentationID == sourcePresentationID {
                if let availableHoldIDs, !availableHoldIDs.contains(hold.id) { continue }
                for piece in hold.geometry {
                    let frame = piece.frame
                    let isInsideCanvas: Bool
                    if case .directTwoAnchor(let rig) = resolvedCordRig {
                        isInsideCanvas = riggedAliasFrameIsInsideCanvas(
                            frame,
                            rig: rig,
                            anchor: anchor,
                            rotationDegrees: presentation.resolvedRotationDegrees
                        )
                    } else {
                        isInsideCanvas = BoardAliasGeometryValidation.projectedFrameIsInsideCanvas(
                            x: frame.x,
                            y: frame.y,
                            width: frame.width,
                            height: frame.height,
                            anchor: anchor,
                            rotationDegrees: presentation.resolvedRotationDegrees
                        )
                    }
                    guard isInsideCanvas else {
                        throw invalid(
                            "presentation \(presentation.id) projects source hold "
                                + "geometry outside the normalized canvas",
                            document
                        )
                    }
                }
            }
        }
    }

    private static func riggedAliasFrameIsInsideCanvas(
        _ frame: BoardPackageFrameDocument,
        rig: BoardDirectTwoAnchorCordRig,
        anchor: BoardGeometryRotationAnchor,
        rotationDegrees: Double
    ) -> Bool {
        let sceneRect = CGRect(origin: .zero, size: rig.sceneSize.cgSize)
        let faceRect = CGRect(
            x: rig.sourceFrame.x + rig.innerFaceFrame.x,
            y: rig.sourceFrame.y + rig.innerFaceFrame.y,
            width: rig.innerFaceFrame.width,
            height: rig.innerFaceFrame.height
        )
        let transform = BoardPresentationGeometryProjection(
            rotationDegrees: CGFloat(rotationDegrees),
            rotationAnchor: anchor
        ).affineTransform(in: sceneRect)
        let corners = [
            CGPoint(x: CGFloat(frame.x), y: CGFloat(frame.y)),
            CGPoint(x: CGFloat(frame.x + frame.width), y: CGFloat(frame.y)),
            CGPoint(x: CGFloat(frame.x), y: CGFloat(frame.y + frame.height)),
            CGPoint(
                x: CGFloat(frame.x + frame.width),
                y: CGFloat(frame.y + frame.height)
            ),
        ].map { normalizedPoint in
            CGPoint(
                x: faceRect.minX + faceRect.width * normalizedPoint.x,
                y: faceRect.minY + faceRect.height * normalizedPoint.y
            ).applying(transform)
        }
        let tolerance = max(sceneRect.width, sceneRect.height) * 1e-12
        return corners.allSatisfy { point in
            point.x >= sceneRect.minX - tolerance
                && point.y >= sceneRect.minY - tolerance
                && point.x <= sceneRect.maxX + tolerance
                && point.y <= sceneRect.maxY + tolerance
        }
    }

    private static func validateEquipmentObjects(
        in document: BoardEditableDocument
    ) throws -> Set<String> {
        guard !document.equipmentObjects.isEmpty else {
            throw invalid("equipmentObjects must not be empty", document)
        }
        var equipmentObjectIDs = Set<String>()
        for object in document.equipmentObjects {
            guard object.id.isEditorBoardIdentifier else {
                throw invalid("equipment object ID must be identifier-shaped", document)
            }
            guard equipmentObjectIDs.insert(object.id).inserted else {
                throw invalid("equipment object ID \(object.id) is duplicated", document)
            }
        }
        return equipmentObjectIDs
    }

    private static func validateEquipmentObjectReference(
        for hold: BoardEditableHold,
        validIDs: Set<String>,
        in document: BoardEditableDocument
    ) throws {
        guard validIDs.contains(hold.equipmentObjectID) else {
            throw invalid(
                "hold \(hold.id) references unknown equipment object \(hold.equipmentObjectID)",
                document
            )
        }
    }

    private static func validateEquipmentObjectOwnership(
        in document: BoardEditableDocument
    ) throws {
        let ownedEquipmentObjectIDs = Set(document.holds.map(\.equipmentObjectID))
        for object in document.equipmentObjects where !ownedEquipmentObjectIDs.contains(object.id) {
            throw invalid("equipment object \(object.id) must own at least one hold", document)
        }
    }

    private static func validatePiece(
        _ piece: BoardEditablePiece,
        holdID: String,
        pieceIndex: Int
    ) throws {
        guard piece.frame.isValid else {
            throw invalid("hold \(holdID) geometry[\(pieceIndex)] has an invalid frame")
        }
        switch piece.shape.type {
        case "roundedRect":
            guard piece.shape.commands == nil,
                  let cornerRadiusFraction = piece.shape.cornerRadiusFraction,
                  cornerRadiusFraction.isFinite,
                  (0.0...0.5).contains(cornerRadiusFraction) else {
                throw invalid("rounded rectangle shape is invalid")
            }
        case "path":
            guard piece.shape.cornerRadiusFraction == nil,
                  let commands = piece.shape.commands,
                  !commands.isEmpty,
                  commands.first?.command == "move",
                  commands.last?.command == "close",
                  commands.filter({ $0.command == "move" }).count == 1,
                  commands.filter({ $0.command == "close" }).count == 1 else {
                throw invalid("path must contain exactly one closed contour")
            }
            do {
                try HoldPathEngine.validateEditableContour(try commands.holdPathCommands())
            } catch let error as BoardGeometryAdaptationError {
                throw invalid(error.description)
            }
        default:
            throw invalid("unsupported shape type \(piece.shape.type)")
        }
        if let shapeConstraint = piece.shapeConstraint {
            do {
                _ = try shapeConstraint.validated()
            } catch {
                throw invalid("shape constraint rotation must be finite and normalized to [-180, 180)")
            }
        }
        if let treatment = piece.treatment {
            switch treatment.type {
            case "surface":
                guard treatment.rimInsetFraction == nil, treatment.depth == nil else {
                    throw invalid("invalid surface treatment")
                }
            case "shelf":
                guard treatment.depth == nil,
                      let inset = treatment.rimInsetFraction,
                      inset.isFinite, (0.0...0.5).contains(inset) else {
                    throw invalid("invalid shelf treatment")
                }
            case "recess":
                guard let inset = treatment.rimInsetFraction,
                      inset.isFinite, (0.0...0.5).contains(inset),
                      treatment.depth == "deep" || treatment.depth == "shallow" else {
                    throw invalid("invalid recess treatment")
                }
            default:
                throw invalid("unsupported treatment type \(treatment.type)")
            }
        }
    }

    private static func invalid(
        _ reason: String,
        _ document: BoardEditableDocument? = nil
    ) -> BoardPackageWriterError {
        guard let document else { return .invalid(reason) }
        return .invalid("board \(document.id): \(reason)")
    }

    private static func canonicalValue(_ document: BoardEditableDocument) -> CanonicalJSONValue {
        var entries: [(String, CanonicalJSONValue)] = [
            ("id", .string(document.id)),
            ("manufacturer", .string(document.manufacturer)),
            ("name", .string(document.name)),
            ("subtitle", .string(document.subtitle)),
            ("productURL", .string(document.productURL.absoluteString)),
            ("aspectRatio", .double(document.aspectRatio)),
            ("equipmentObjects", .array(document.equipmentObjects.map { object in
                var entries: [(String, CanonicalJSONValue)] = [
                    ("id", .string(object.id))
                ]
                if object.missingHandCapacityPolicy != .legacyBilateral {
                    entries.append((
                        "missingHandCapacityPolicy",
                        .string(object.missingHandCapacityPolicy.rawValue)
                    ))
                }
                return .object(entries)
            })),
            ("holds", .array(document.holds.map(canonicalHoldValue))),
            ("presentations", .array(document.presentations.map(canonicalPresentationValue))),
        ]
        if let positions = document.positions {
            entries.append(("positions", .array(positions.map(canonicalPositionValue))))
        }
        if let positionTransitions = document.positionTransitions {
            entries.append((
                "positionTransitions",
                .array(positionTransitions.map(canonicalPositionTransitionValue))
            ))
        }
        if let dimensions = document.dimensions {
            entries.insert(("dimensions", .string(dimensions)), at: 5)
        }
        return .object(entries)
    }

    private static func canonicalHoldValue(_ hold: BoardEditableHold) -> CanonicalJSONValue {
        var entries: [(String, CanonicalJSONValue)] = [
            ("id", .string(hold.id)),
            ("name", .string(hold.name)),
        ]
        if let kind = hold.kind {
            entries.append(("kind", .string(kind.rawValue)))
        }
        if let pairedHoldID = hold.pairedHoldID {
            entries.append(("pairedHoldID", .string(pairedHoldID)))
        }
        if let sloper = hold.sloper {
            var sloperEntries: [(String, CanonicalJSONValue)] = [
                ("type", .string(sloper.type.rawValue)),
            ]
            if let angleDegrees = sloper.angleDegrees {
                sloperEntries.append(("angleDegrees", .double(angleDegrees)))
            }
            entries.append(("sloper", .object(sloperEntries)))
        }
        if let sizeMillimeters = hold.sizeMillimeters {
            entries.append(("sizeMillimeters", .double(sizeMillimeters)))
        }
        if let depthRange = hold.depthRangeMillimeters {
            entries.append(("depthRangeMillimeters", .object([
                ("lowerBound", .double(depthRange.lowerBound)),
                ("upperBound", .double(depthRange.upperBound)),
            ])))
        }
        if let gripType = hold.gripType {
            entries.append(("gripType", .string(gripType.rawValue)))
        }
        if let fingerCapacity = hold.fingerCapacity {
            entries.append(("fingerCapacity", .int(fingerCapacity)))
        }
        if let handCapacity = hold.handCapacity {
            entries.append(("handCapacity", .int(handCapacity)))
        }
        if let features = hold.features {
            entries.append(("features", .array(features.map { .string($0.rawValue) })))
        }
        entries.append(("equipmentObjectID", .string(hold.equipmentObjectID)))
        entries.append(("presentationID", .string(hold.presentationID)))
        entries.append(("geometry", .array(hold.geometry.map(canonicalPieceValue))))
        return .object(entries)
    }

    private static func canonicalPresentationValue(
        _ presentation: BoardEditablePresentation
    ) -> CanonicalJSONValue {
        var entries: [(String, CanonicalJSONValue)] = [
            ("id", .string(presentation.id)),
            ("name", .string(presentation.name)),
            ("assetPath", .string(presentation.assetPath)),
            ("aspectRatio", .double(presentation.aspectRatio)),
            ("default", .bool(presentation.isDefault)),
        ]
        if let sourcePresentationID = presentation.sourcePresentationID {
            entries.append(("sourcePresentationID", .string(sourcePresentationID)))
        }
        if let availableHoldIDs = presentation.availableHoldIDs {
            entries.append((
                "availableHoldIDs",
                .array(availableHoldIDs.map(CanonicalJSONValue.string))
            ))
        }
        if presentation.isInverted {
            entries.append(("isInverted", .bool(true)))
        }
        if let rotationDegrees = presentation.rotationDegrees {
            entries.append(("rotationDegrees", .double(rotationDegrees)))
        }
        if let anchor = presentation.geometryRotationAnchor {
            entries.append(("geometryRotationAnchor", .object([
                ("x", .double(anchor.x)),
                ("y", .double(anchor.y)),
            ])))
        }
        if let cordRig = presentation.cordRig {
            entries.append(("cordRig", canonicalCordRigValue(cordRig)))
        }
        return .object(entries)
    }

    private static func canonicalCordRigValue(
        _ cordRig: BoardCordRig
    ) -> CanonicalJSONValue {
        let rig: BoardDirectTwoAnchorCordRig
        switch cordRig {
        case .directTwoAnchor(let value):
            rig = value
        }
        return .object([
            ("type", .string("directTwoAnchor")),
            ("sceneSize", .object([
                ("width", .double(Double(rig.sceneSize.width))),
                ("height", .double(Double(rig.sceneSize.height))),
            ])),
            ("sourceFrame", .object([
                ("x", .double(Double(rig.sourceFrame.x))),
                ("y", .double(Double(rig.sourceFrame.y))),
                ("width", .double(Double(rig.sourceFrame.width))),
                ("height", .double(Double(rig.sourceFrame.height))),
            ])),
            ("innerFaceFrame", .object([
                ("x", .double(Double(rig.innerFaceFrame.x))),
                ("y", .double(Double(rig.innerFaceFrame.y))),
                ("width", .double(Double(rig.innerFaceFrame.width))),
                ("height", .double(Double(rig.innerFaceFrame.height))),
            ])),
            ("attachmentPoints", .array(rig.attachmentPoints.map { point in
                .object([
                    ("x", .double(Double(point.x))),
                    ("y", .double(Double(point.y))),
                ])
            })),
            ("pullPoint", .object([
                ("x", .double(Double(rig.pullPoint.x))),
                ("y", .double(Double(rig.pullPoint.y))),
            ])),
            ("eyeletRadius", .double(Double(rig.eyeletRadius))),
        ])
    }

    private static func canonicalPositionValue(_ position: BoardPosition) -> CanonicalJSONValue {
        .object([
            ("id", .string(position.id)),
            ("presentationID", .string(position.presentationID)),
        ])
    }

    private static func canonicalPositionTransitionValue(
        _ transition: BoardPositionTransition
    ) -> CanonicalJSONValue {
        .object([
            ("fromPositionID", .string(transition.fromPositionID)),
            ("toPositionID", .string(transition.toPositionID)),
            ("kind", .string(transition.kind.rawValue)),
        ])
    }

    private static func canonicalPieceValue(_ piece: BoardEditablePiece) -> CanonicalJSONValue {
        var entries: [(String, CanonicalJSONValue)] = [
            ("frame", .object([
                ("x", .double(piece.frame.x)),
                ("y", .double(piece.frame.y)),
                ("width", .double(piece.frame.width)),
                ("height", .double(piece.frame.height)),
            ])),
        ]
        if piece.shape.type == "roundedRect" {
            entries.append(("shape", .object([
                ("type", .string("roundedRect")),
                ("cornerRadiusFraction", .double(piece.shape.cornerRadiusFraction ?? 0)),
            ])))
        } else {
            entries.append(("shape", .object([
                ("type", .string("path")),
                ("commands", .array((piece.shape.commands ?? []).map(canonicalCommandValue))),
            ])))
        }
        if let shapeConstraint = piece.shapeConstraint {
            entries.append(("shapeConstraint", .object([
                ("shape", .string(shapeConstraint.shape.rawValue)),
                ("rotationDegrees", .double(shapeConstraint.rotationDegrees)),
            ])))
        }
        if let treatment = piece.treatment {
            var treatmentEntries: [(String, CanonicalJSONValue)] = [("type", .string(treatment.type))]
            if let rimInsetFraction = treatment.rimInsetFraction {
                treatmentEntries.append(("rimInsetFraction", .double(rimInsetFraction)))
            }
            if let depth = treatment.depth {
                treatmentEntries.append(("depth", .string(depth)))
            }
            entries.append(("treatment", .object(treatmentEntries)))
        }
        return .object(entries)
    }

    private static func canonicalCommandValue(
        _ command: BoardGeometryPathCommandDocument
    ) -> CanonicalJSONValue {
        var entries: [(String, CanonicalJSONValue)] = [("command", .string(command.command))]
        if let control1 = command.control1 {
            entries.append(("control1", pointValue(control1)))
        }
        if let control2 = command.control2 {
            entries.append(("control2", pointValue(control2)))
        }
        if let control = command.control {
            entries.append(("control", pointValue(control)))
        }
        if let to = command.to {
            entries.append(("to", pointValue(to)))
        }
        if command.bendable == true {
            entries.append(("bendable", .bool(true)))
        }
        if command.smooth == true {
            entries.append(("smooth", .bool(true)))
        }
        return .object(entries)
    }

    private static func pointValue(_ coordinates: [Double]) -> CanonicalJSONValue {
        .array(coordinates.map { .double($0) })
    }
}

private enum CanonicalJSONValue {
    case null
    case bool(Bool)
    case int(Int)
    case double(Double)
    case string(String)
    case array([CanonicalJSONValue])
    case object([(String, CanonicalJSONValue)])
}

private enum CanonicalJSONSerializer {
    static func data(_ value: CanonicalJSONValue) -> Data {
        var output = ""
        render(value, indent: "", to: &output)
        output += "\n"
        return Data(output.utf8)
    }

    private static func render(
        _ value: CanonicalJSONValue,
        indent: String,
        to output: inout String
    ) {
        switch value {
        case .null:
            output += "null"
        case .bool(let bool):
            output += bool ? "true" : "false"
        case .int(let int):
            output += String(int)
        case .double(let double):
            output += pythonNumberString(double)
        case .string(let string):
            output += escapedString(string)
        case .array(let items):
            guard !items.isEmpty else {
                output += "[]"
                return
            }
            output += "[\n"
            let innerIndent = indent + "  "
            for (index, item) in items.enumerated() {
                if index > 0 { output += ",\n" }
                output += innerIndent
                render(item, indent: innerIndent, to: &output)
            }
            output += "\n" + indent + "]"
        case .object(let entries):
            guard !entries.isEmpty else {
                output += "{}"
                return
            }
            output += "{\n"
            let innerIndent = indent + "  "
            for (index, entry) in entries.enumerated() {
                if index > 0 { output += ",\n" }
                output += innerIndent
                output += escapedString(entry.0)
                output += ": "
                render(entry.1, indent: innerIndent, to: &output)
            }
            output += "\n" + indent + "}"
        }
    }

    private static func escapedString(_ string: String) -> String {
        var result = "\""
        for scalar in string.unicodeScalars {
            switch scalar {
            case "\"": result += "\\\""
            case "\\": result += "\\\\"
            case "\n": result += "\\n"
            case "\r": result += "\\r"
            case "\t": result += "\\t"
            case Unicode.Scalar(0x08): result += "\\b"
            case Unicode.Scalar(0x0C): result += "\\f"
            default:
                if scalar.value < 0x20 || scalar.value > 0x7E {
                    appendEscapedScalar(scalar, to: &result)
                } else {
                    result.unicodeScalars.append(scalar)
                }
            }
        }
        result += "\""
        return result
    }

    private static func appendEscapedScalar(_ scalar: Unicode.Scalar, to result: inout String) {
        func hex(_ value: UInt32) -> String {
            String(format: "\\u%04x", value)
        }
        if scalar.value > 0xFFFF {
            let offset = scalar.value - 0x10000
            let high = 0xD800 + (offset >> 10)
            let low = 0xDC00 + (offset & 0x3FF)
            result += hex(high) + hex(low)
        } else {
            result += hex(scalar.value)
        }
    }

    /// Formats doubles the way Python's json module prints floats: shortest
    /// round-trip digits, fixed notation within [-4, 17) decimal magnitude,
    /// and ".0" on integral values.
    private static func pythonNumberString(_ value: Double) -> String {
        precondition(value.isFinite, "board package numbers must be finite")
        if value == 0 {
            return value.sign == .minus ? "-0.0" : "0.0"
        }
        var description = value.description
        var isNegative = false
        if description.hasPrefix("-") {
            isNegative = true
            description.removeFirst()
        }
        var mantissa = description
        var exponent = 0
        if let eIndex = mantissa.firstIndex(of: "e") {
            exponent = Int(mantissa[mantissa.index(after: eIndex)...]) ?? 0
            mantissa = String(mantissa[..<eIndex])
        }
        let dotIndex = mantissa.firstIndex(of: ".")
        let integerCount = dotIndex.map { mantissa.distance(from: mantissa.startIndex, to: $0) }
            ?? mantissa.count
        var digits = mantissa.filter { $0.isASCII && $0.isNumber }
        var decimalPoint = integerCount + exponent
        while digits.first == "0" {
            digits.removeFirst()
            decimalPoint -= 1
        }
        while digits.last == "0" {
            digits.removeLast()
        }
        precondition(!digits.isEmpty, "board package numbers must be finite")

        let count = digits.count
        var formatted: String
        if decimalPoint < -3 || decimalPoint > 16 {
            formatted = String(digits.first!)
            if count > 1 {
                formatted += "." + digits.dropFirst()
            }
            let printedExponent = decimalPoint - 1
            let sign = printedExponent < 0 ? "-" : "+"
            formatted += "e" + sign + String(format: "%02d", abs(printedExponent))
        } else if decimalPoint <= 0 {
            formatted = "0." + String(repeating: "0", count: -decimalPoint) + digits
        } else if decimalPoint >= count {
            formatted = digits + String(repeating: "0", count: decimalPoint - count) + ".0"
        } else {
            let splitIndex = digits.index(digits.startIndex, offsetBy: decimalPoint)
            formatted = digits[..<splitIndex] + "." + digits[splitIndex...]
        }
        return isNegative ? "-" + formatted : formatted
    }
}

private extension String {
    var isEditorBoardIdentifier: Bool {
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

    private static func isLowercaseASCIIOrDigit(_ scalar: Unicode.Scalar) -> Bool {
        (97...122).contains(scalar.value) || (48...57).contains(scalar.value)
    }
}
