import Foundation

struct BoardEditableDocument: Equatable, Decodable {
    var schemaVersion: Int
    var id: String
    var revisionID: String
    var manufacturer: String
    var name: String
    var subtitle: String
    var productURL: URL
    var dimensions: String?
    var aspectRatio: Double
    var equipmentObjects: [EquipmentObject]
    var contacts: [BoardEditableContact]
    var presentations: [BoardEditablePresentation]
    var positions: [BoardPosition]?
    var positionTransitions: [BoardPositionTransition]?

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case id
        case revisionID
        case manufacturer
        case name
        case subtitle
        case productURL
        case dimensions
        case aspectRatio
        case equipmentObjects
        case contacts
        case presentations
        case positions
        case positionTransitions
    }

    init(
        schemaVersion: Int = 3,
        id: String,
        revisionID: String,
        manufacturer: String,
        name: String,
        subtitle: String,
        productURL: URL,
        dimensions: String?,
        aspectRatio: Double,
        equipmentObjects: [EquipmentObject] = [.init(id: "primary")],
        contacts: [BoardEditableContact],
        presentations: [BoardEditablePresentation],
        positions: [BoardPosition]? = nil,
        positionTransitions: [BoardPositionTransition]? = nil
    ) {
        self.schemaVersion = schemaVersion
        self.id = id
        self.revisionID = revisionID
        self.manufacturer = manufacturer
        self.name = name
        self.subtitle = subtitle
        self.productURL = productURL
        self.dimensions = dimensions
        self.aspectRatio = aspectRatio
        self.equipmentObjects = equipmentObjects
        self.contacts = contacts
        self.presentations = presentations
        self.positions = positions
        self.positionTransitions = positionTransitions
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "schemaVersion", "id", "revisionID", "manufacturer", "name", "subtitle", "productURL",
            "dimensions", "aspectRatio", "equipmentObjects", "contacts", "presentations",
            "positions", "positionTransitions"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        guard schemaVersion == 3 else {
            throw DecodingError.dataCorruptedError(
                forKey: .schemaVersion,
                in: container,
                debugDescription: "schemaVersion must be 3"
            )
        }
        id = try container.decode(String.self, forKey: .id)
        revisionID = try container.decode(String.self, forKey: .revisionID)
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
        contacts = try container.decode([BoardEditableContact].self, forKey: .contacts)
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

    func geometry(forContactID contactID: String) -> [BoardEditablePiece]? {
        guard let presentationIndex = defaultRasterPresentationIndex,
              case .raster(_, let contactGeometry) = presentations[presentationIndex].media else {
            return nil
        }
        return contactGeometry[contactID]
    }

    mutating func replaceGeometry(
        forContactID contactID: String,
        with pieces: [BoardEditablePiece]
    ) {
        guard let presentationIndex = originalDefaultRasterPresentationIndex else { return }
        guard case .raster(let assetPath, var contactGeometry) = presentations[presentationIndex].media else {
            return
        }
        guard contactGeometry[contactID] != nil else { return }
        contactGeometry[contactID] = pieces
        presentations[presentationIndex].media = .raster(
            assetPath: assetPath,
            contactGeometry: contactGeometry
        )
    }

    private var defaultRasterPresentationIndex: Int? {
        presentations.firstIndex { presentation in
            guard presentation.isDefault,
                  case .raster = presentation.media else {
                return false
            }
            return true
        }
    }

    private var originalDefaultRasterPresentationIndex: Int? {
        presentations.firstIndex { presentation in
            guard presentation.isDefault,
                  presentation.derivation == .original,
                  case .raster = presentation.media else {
                return false
            }
            return true
        }
    }
}

private struct BoardEditablePositionDocument: Decodable {
    let id: String
    let presentationID: String
    let contactIDs: [String]
    let contactIDsWereExplicitlyAuthored: Bool

    private enum CodingKeys: String, CodingKey {
        case id
        case presentationID
        case contactIDs
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["id", "presentationID", "contactIDs"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        presentationID = try container.decode(String.self, forKey: .presentationID)
        contactIDsWereExplicitlyAuthored = container.contains(.contactIDs)
        contactIDs = contactIDsWereExplicitlyAuthored
            ? try container.decode([String].self, forKey: .contactIDs)
            : []
    }

    var position: BoardPosition {
        contactIDsWereExplicitlyAuthored
            ? BoardPosition(id: id, presentationID: presentationID, contactIDs: contactIDs)
            : BoardPosition(id: id, presentationID: presentationID)
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

    private enum CodingKeys: String, CodingKey {
        case id
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["id"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
    }

    var equipmentObject: EquipmentObject {
        EquipmentObject(id: id)
    }
}

enum BoardEditablePresentationDerivation: Equatable, Decodable {
    case original
    case derived(sourcePresentationID: String, isInverted: Bool)

    private enum CodingKeys: String, CodingKey { case type, sourcePresentationID, isInverted }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)
        switch type {
        case "original":
            try decoder.rejectUnknownEditorKeys(["type"])
            self = .original
        case "derived":
            try decoder.rejectUnknownEditorKeys(["type", "sourcePresentationID", "isInverted"])
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

enum BoardEditablePresentationMedia: Equatable, Decodable {
    case raster(assetPath: String, contactGeometry: [String: [BoardEditablePiece]])
    case model(
        assetPath: String,
        descriptorPath: String,
        display: BoardPackageModelDisplayDocument,
        suspension: BoardPackageSuspensionDocument?,
        orientation: BoardPackageModelOrientationDocument?
    )

    private enum CodingKeys: String, CodingKey {
        case type, assetPath, contactGeometry, descriptorPath, display, suspension, orientation
    }

    var assetPath: String {
        switch self {
        case .raster(let assetPath, _), .model(let assetPath, _, _, _, _): assetPath
        }
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)
        switch type {
        case "raster":
            try decoder.rejectUnknownEditorKeys(["type", "assetPath", "contactGeometry"])
            self = .raster(
                assetPath: try container.decode(String.self, forKey: .assetPath),
                contactGeometry: try container.decode(
                    [String: [BoardEditablePiece]].self,
                    forKey: .contactGeometry
                )
            )
        case "model":
            try decoder.rejectUnknownEditorKeys([
                "type", "assetPath", "descriptorPath", "display", "suspension", "orientation"
            ])
            self = .model(
                assetPath: try container.decode(String.self, forKey: .assetPath),
                descriptorPath: try container.decode(String.self, forKey: .descriptorPath),
                display: try container.decode(
                    BoardPackageModelDisplayDocument.self,
                    forKey: .display
                ),
                suspension: container.contains(.suspension)
                    ? try container.decode(BoardPackageSuspensionDocument.self, forKey: .suspension)
                    : nil,
                orientation: container.contains(.orientation)
                    ? try container.decode(
                        BoardPackageModelOrientationDocument.self,
                        forKey: .orientation
                    )
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
}

struct BoardEditablePresentation: Equatable, Decodable {
    var id: String
    var name: String
    var aspectRatio: Double
    var isDefault: Bool
    var derivation: BoardEditablePresentationDerivation
    var media: BoardEditablePresentationMedia

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case aspectRatio
        case isDefault
        case derivation
        case media
    }

    init(
        id: String,
        name: String,
        aspectRatio: Double,
        isDefault: Bool,
        derivation: BoardEditablePresentationDerivation = .original,
        media: BoardEditablePresentationMedia
    ) {
        self.id = id
        self.name = name
        self.aspectRatio = aspectRatio
        self.isDefault = isDefault
        self.derivation = derivation
        self.media = media
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "id", "name", "aspectRatio", "isDefault", "derivation", "media"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        aspectRatio = try container.decode(Double.self, forKey: .aspectRatio)
        isDefault = try container.decode(Bool.self, forKey: .isDefault)
        derivation = try container.decode(BoardEditablePresentationDerivation.self, forKey: .derivation)
        media = try container.decode(BoardEditablePresentationMedia.self, forKey: .media)
    }
}

struct BoardEditableContact: Equatable, Decodable {
    var id: String
    var name: String
    /// Editor packages may omit `kind` while metadata is being completed.
    /// Training-board decoding remains strict in `BoardPackageStore`.
    var kind: HoldKind?
    var depthRangeMillimeters: BoardEditableMillimeterRange?
    var gripTypes: [GripType]
    var fingerCapacity: Int?
    var handCapacity: Int?
    var shape: HoldShape?
    var side: ContactSide?
    var pairedContactID: String?
    var declaresPairedContactID: Bool
    var equipmentObjectID: String

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case kind
        case depthRangeMillimeters
        case gripTypes
        case fingerCapacity
        case handCapacity
        case shape
        case side
        case pairedContactID
        case equipmentObjectID
    }

    init(
        id: String,
        name: String,
        kind: HoldKind?,
        depthRangeMillimeters: BoardEditableMillimeterRange? = nil,
        gripTypes: [GripType] = [],
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        shape: HoldShape? = nil,
        side: ContactSide? = nil,
        pairedContactID: String? = nil,
        equipmentObjectID: String = "primary"
    ) {
        self.id = id
        self.name = name
        self.kind = kind
        self.depthRangeMillimeters = depthRangeMillimeters
        self.gripTypes = gripTypes
        self.fingerCapacity = fingerCapacity
        self.handCapacity = handCapacity
        self.shape = shape
        self.side = side
        self.pairedContactID = pairedContactID
        declaresPairedContactID = pairedContactID != nil
        self.equipmentObjectID = equipmentObjectID
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "id", "equipmentObjectID", "name", "kind", "shape",
            "depthRangeMillimeters", "gripTypes", "fingerCapacity", "handCapacity",
            "side", "pairedContactID"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        kind = container.contains(.kind)
            ? try container.decode(HoldKind.self, forKey: .kind)
            : nil
        depthRangeMillimeters = try container.decodeIfPresent(
            BoardEditableMillimeterRange.self,
            forKey: .depthRangeMillimeters
        )
        gripTypes = try container.decode([GripType].self, forKey: .gripTypes)
        fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        handCapacity = try container.decodeIfPresent(Int.self, forKey: .handCapacity)
        shape = try container.decodeIfPresent(HoldShape.self, forKey: .shape)
        side = try container.decodeIfPresent(ContactSide.self, forKey: .side)
        declaresPairedContactID = container.contains(.pairedContactID)
        pairedContactID = declaresPairedContactID
            ? try container.decode(String.self, forKey: .pairedContactID)
            : nil
        equipmentObjectID = try container.decode(String.self, forKey: .equipmentObjectID)
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
    static func data(for document: BoardEditableDocument) throws -> Data {
        try validate(document)
        return CanonicalJSONSerializer.data(canonicalValue(document))
    }

    static func validate(_ document: BoardEditableDocument) throws {
        guard document.schemaVersion == 3 else {
            throw invalid("schemaVersion must be 3", document)
        }
        guard document.id.isEditorBoardIdentifier else {
            throw invalid("board ID must be identifier-shaped", document)
        }
        guard document.revisionID.isEditorBoardIdentifier else {
            throw invalid("revisionID must be identifier-shaped", document)
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
            guard presentation.aspectRatio.isFinite, presentation.aspectRatio > 0 else {
                throw invalid("presentation \(presentation.id) aspect ratio must be positive", document)
            }
            guard case .raster(let assetPath, let contactGeometry) = presentation.media else {
                throw invalid("model-only packages are not editable", document)
            }
            guard assetPath.hasPrefix("assets/"),
                  assetPath.hasSuffix(".png"),
                  !assetPath.hasSuffix("/"),
                  !assetPath.contains("..") else {
                throw invalid("presentation \(presentation.id) raster assetPath must name a package PNG", document)
            }
            guard !contactGeometry.isEmpty else {
                throw invalid("presentation \(presentation.id) contactGeometry must not be empty", document)
            }
            for (contactID, pieces) in contactGeometry {
                guard contactID.isEditorBoardIdentifier, !pieces.isEmpty else {
                    throw invalid("presentation \(presentation.id) has invalid contactGeometry", document)
                }
                for (pieceIndex, piece) in pieces.enumerated() {
                    try validatePiece(piece, contactID: contactID, pieceIndex: pieceIndex)
                }
            }
            if presentation.isDefault {
                defaultPresentationCount += 1
            }
        }
        guard defaultPresentationCount == 1 else {
            throw invalid("presentations must declare exactly one default", document)
        }

        let presentationsByID = Dictionary(
            uniqueKeysWithValues: document.presentations.map { ($0.id, $0) }
        )
        for presentation in document.presentations {
            if case .derived(let sourcePresentationID, _) = presentation.derivation {
                guard sourcePresentationID != presentation.id,
                      let sourcePresentation = presentationsByID[sourcePresentationID],
                      sourcePresentation.derivation == .original else {
                    throw invalid(
                        "presentation \(presentation.id) must reference a canonical presentation",
                        document
                    )
                }
            }
        }

        guard !document.contacts.isEmpty else {
            throw invalid("contacts must not be empty", document)
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
            guard !position.contactIDsWereExplicitlyAuthored || !position.contactIDs.isEmpty else {
                throw invalid("position \(position.id) contactIDs must not be empty", document)
            }
            if case .model = presentation.media, !position.contactIDsWereExplicitlyAuthored {
                throw invalid("model position \(position.id) must declare contactIDs", document)
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
        var contactIDs = Set<String>()
        for contact in document.contacts {
            guard contact.id.isEditorBoardIdentifier, !contact.name.isEmpty, contact.kind != nil else {
                throw invalid("contact \(contact.id) metadata must be complete and identifier-shaped", document)
            }
            guard contactIDs.insert(contact.id).inserted else {
                throw invalid("contact ID \(contact.id) is duplicated", document)
            }
            try validateEquipmentObjectReference(
                for: contact,
                validIDs: equipmentObjectIDs,
                in: document
            )
            if let pairedContactID = contact.pairedContactID {
                guard pairedContactID.isEditorBoardIdentifier else {
                    throw invalid(
                        "contact \(contact.id) must declare an identifier-shaped pairedContactID",
                        document
                    )
                }
            } else if contact.kind == .gaston {
                throw invalid("gaston contact \(contact.id) must declare a pairedContactID", document)
            }
            if let fingerCapacity = contact.fingerCapacity,
               !PhysicalContact.validFingerCapacityRange.contains(fingerCapacity) {
                throw invalid("contact \(contact.id) has an invalid finger capacity", document)
            }
            if let handCapacity = contact.handCapacity,
               !PhysicalContact.validHandCapacityRange.contains(handCapacity) {
                throw invalid("contact \(contact.id) has an invalid hand capacity", document)
            }
            if let depthRange = contact.depthRangeMillimeters,
               !depthRange.lowerBound.isFinite ||
               !depthRange.upperBound.isFinite ||
               depthRange.lowerBound <= 0 ||
               depthRange.upperBound <= 0 ||
               depthRange.lowerBound > depthRange.upperBound {
                throw invalid("contact \(contact.id) has an invalid depth range", document)
            }
            if Set(contact.gripTypes).count != contact.gripTypes.count {
                throw invalid("contact \(contact.id) has duplicate gripTypes", document)
            }
        }
        for presentation in document.presentations {
            guard case .raster(_, let geometry) = presentation.media else { continue }
            for contactID in geometry.keys where !contactIDs.contains(contactID) {
                throw invalid("presentation \(presentation.id) references unknown contact \(contactID)", document)
            }
        }
        let coveredContactIDs = Set(document.presentations.flatMap { presentation -> [String] in
            guard case .raster(_, let geometry) = presentation.media else { return [] }
            return Array(geometry.keys)
        })
        guard coveredContactIDs == contactIDs else {
            throw invalid("raster contactGeometry must cover every contact", document)
        }
        for position in positions {
            for contactID in position.contactIDs where !contactIDs.contains(contactID) {
                throw invalid("position \(position.id) references unknown contactID", document)
            }
        }
        try validateEquipmentObjectOwnership(in: document)
        let contactsByID = Dictionary(uniqueKeysWithValues: document.contacts.map { ($0.id, $0) })
        for contact in document.contacts where contact.declaresPairedContactID {
            guard let pairedContactID = contact.pairedContactID else { continue }
            guard pairedContactID != contact.id,
                  let pairedContact = contactsByID[pairedContactID] else {
                throw invalid("contact \(contact.id) must pair with a distinct existing contact", document)
            }
            guard pairedContact.kind == contact.kind,
                  pairedContact.pairedContactID == contact.id else {
                throw invalid("contact \(contact.id) must have a reciprocal same-kind pair", document)
            }
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
        for contact: BoardEditableContact,
        validIDs: Set<String>,
        in document: BoardEditableDocument
    ) throws {
        guard validIDs.contains(contact.equipmentObjectID) else {
            throw invalid(
                "contact \(contact.id) references unknown equipment object \(contact.equipmentObjectID)",
                document
            )
        }
    }

    private static func validateEquipmentObjectOwnership(
        in document: BoardEditableDocument
    ) throws {
        let ownedEquipmentObjectIDs = Set(document.contacts.map(\.equipmentObjectID))
        for object in document.equipmentObjects where !ownedEquipmentObjectIDs.contains(object.id) {
            throw invalid("equipment object \(object.id) must own at least one contact", document)
        }
    }

    private static func validatePiece(
        _ piece: BoardEditablePiece,
        contactID: String,
        pieceIndex: Int
    ) throws {
        guard piece.frame.isValid else {
            throw invalid("contact \(contactID) geometry[\(pieceIndex)] has an invalid frame")
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
            ("schemaVersion", .int(3)),
            ("id", .string(document.id)),
            ("manufacturer", .string(document.manufacturer)),
            ("name", .string(document.name)),
            ("subtitle", .string(document.subtitle)),
            ("productURL", .string(document.productURL.absoluteString)),
            ("aspectRatio", .double(document.aspectRatio)),
            ("equipmentObjects", .array(document.equipmentObjects.map { object in
                .object([("id", .string(object.id))])
            })),
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
            entries.insert(("dimensions", .string(dimensions)), at: 6)
        }
        entries.append(("revisionID", .string(document.revisionID)))
        entries.append(("contacts", .array(document.contacts.map(canonicalContactValue))))
        return .object(entries)
    }

    private static func canonicalContactValue(_ contact: BoardEditableContact) -> CanonicalJSONValue {
        var entries: [(String, CanonicalJSONValue)] = [
            ("id", .string(contact.id)),
            ("equipmentObjectID", .string(contact.equipmentObjectID)),
            ("name", .string(contact.name)),
        ]
        if let kind = contact.kind {
            entries.append(("kind", .string(kind.rawValue)))
        }
        if let shape = contact.shape {
            entries.append(("shape", .string(shape.rawValue)))
        }
        if let fingerCapacity = contact.fingerCapacity {
            entries.append(("fingerCapacity", .int(fingerCapacity)))
        }
        if let handCapacity = contact.handCapacity {
            entries.append(("handCapacity", .int(handCapacity)))
        }
        if let depthRange = contact.depthRangeMillimeters {
            entries.append(("depthRangeMillimeters", .object([
                ("lowerBound", .double(depthRange.lowerBound)),
                ("upperBound", .double(depthRange.upperBound)),
            ])))
        }
        entries.append(("gripTypes", .array(contact.gripTypes.map { .string($0.rawValue) })))
        if let side = contact.side {
            entries.append(("side", .string(side.rawValue)))
        }
        if let pairedContactID = contact.pairedContactID {
            entries.append(("pairedContactID", .string(pairedContactID)))
        }
        return .object(entries)
    }

    private static func canonicalPresentationValue(
        _ presentation: BoardEditablePresentation
    ) -> CanonicalJSONValue {
        let derivation: CanonicalJSONValue
        switch presentation.derivation {
        case .original:
            derivation = .object([("type", .string("original"))])
        case .derived(let sourcePresentationID, let isInverted):
            derivation = .object([
                ("type", .string("derived")),
                ("sourcePresentationID", .string(sourcePresentationID)),
                ("isInverted", .bool(isInverted)),
            ])
        }
        let media: CanonicalJSONValue
        switch presentation.media {
        case .raster(let assetPath, let contactGeometry):
            media = .object([
                ("type", .string("raster")),
                ("assetPath", .string(assetPath)),
                ("contactGeometry", .object(contactGeometry.keys.sorted().map { contactID in
                    (contactID, .array((contactGeometry[contactID] ?? []).map(canonicalPieceValue)))
                })),
            ])
        case .model:
            preconditionFailure("model-only packages are not editable")
        }
        return .object([
            ("id", .string(presentation.id)),
            ("name", .string(presentation.name)),
            ("aspectRatio", .double(presentation.aspectRatio)),
            ("isDefault", .bool(presentation.isDefault)),
            ("derivation", derivation),
            ("media", media),
        ])
    }

    private static func canonicalPositionValue(_ position: BoardPosition) -> CanonicalJSONValue {
        var entries: [(String, CanonicalJSONValue)] = [
            ("id", .string(position.id)),
            ("presentationID", .string(position.presentationID)),
        ]
        if position.contactIDsWereExplicitlyAuthored {
            entries.append(("contactIDs", .array(position.contactIDs.map(CanonicalJSONValue.string))))
        }
        return .object(entries)
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
