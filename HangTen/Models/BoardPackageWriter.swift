import Foundation

struct BoardEditableDocument: Equatable, Decodable {
    var schemaVersion: Int
    var id: String
    var manufacturer: String
    var name: String
    var subtitle: String
    var productURL: URL
    var dimensions: String
    var aspectRatio: Double
    var presentationAssetPath: String
    var holds: [BoardEditableHold]

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

    init(
        schemaVersion: Int,
        id: String,
        manufacturer: String,
        name: String,
        subtitle: String,
        productURL: URL,
        dimensions: String,
        aspectRatio: Double,
        presentationAssetPath: String,
        holds: [BoardEditableHold]
    ) {
        self.schemaVersion = schemaVersion
        self.id = id
        self.manufacturer = manufacturer
        self.name = name
        self.subtitle = subtitle
        self.productURL = productURL
        self.dimensions = dimensions
        self.aspectRatio = aspectRatio
        self.presentationAssetPath = presentationAssetPath
        self.holds = holds
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
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
        let presentation = try container.decode(
            BoardEditablePresentationDocument.self,
            forKey: .presentation
        )
        presentationAssetPath = presentation.assetPath
        holds = try container.decode([BoardEditableHold].self, forKey: .holds)
    }

    init(data: Data) throws {
        self = try JSONDecoder().decode(BoardEditableDocument.self, from: data)
    }
}

private struct BoardEditablePresentationDocument: Decodable {
    let assetPath: String

    private enum CodingKeys: String, CodingKey {
        case assetPath
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["assetPath"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        assetPath = try container.decode(String.self, forKey: .assetPath)
    }
}

struct BoardEditableHold: Equatable, Decodable {
    var id: String
    var name: String
    var kind: HoldKind
    var sizeMillimeters: Int?
    var depthRangeMillimeters: BoardEditableMillimeterRange?
    var gripType: GripType?
    var fingerCapacity: Int?
    var handCapacity: Int?
    var features: [HoldFeature]?
    var geometry: [BoardEditablePiece]

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

    init(
        id: String,
        name: String,
        kind: HoldKind,
        sizeMillimeters: Int? = nil,
        depthRangeMillimeters: BoardEditableMillimeterRange? = nil,
        gripType: GripType? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        features: [HoldFeature]? = nil,
        geometry: [BoardEditablePiece]
    ) {
        self.id = id
        self.name = name
        self.kind = kind
        self.sizeMillimeters = sizeMillimeters
        self.depthRangeMillimeters = depthRangeMillimeters
        self.gripType = gripType
        self.fingerCapacity = fingerCapacity
        self.handCapacity = handCapacity
        self.features = features
        self.geometry = geometry
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys([
            "id", "name", "kind", "geometry", "sizeMillimeters",
            "depthRangeMillimeters", "gripType", "fingerCapacity", "handCapacity", "features"
        ])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        kind = try container.decode(HoldKind.self, forKey: .kind)
        geometry = try container.decode([BoardEditablePiece].self, forKey: .geometry)
        sizeMillimeters = try container.decodeIfPresent(Int.self, forKey: .sizeMillimeters)
        depthRangeMillimeters = try container.decodeIfPresent(
            BoardEditableMillimeterRange.self,
            forKey: .depthRangeMillimeters
        )
        gripType = try container.decodeIfPresent(GripType.self, forKey: .gripType)
        fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        handCapacity = try container.decodeIfPresent(Int.self, forKey: .handCapacity)
        features = try container.decodeIfPresent([HoldFeature].self, forKey: .features)
    }
}

struct BoardEditableMillimeterRange: Equatable, Decodable {
    var lowerBound: Int
    var upperBound: Int

    private enum CodingKeys: String, CodingKey {
        case lowerBound
        case upperBound
    }

    init(lowerBound: Int, upperBound: Int) {
        self.lowerBound = lowerBound
        self.upperBound = upperBound
    }

    init(from decoder: Decoder) throws {
        try decoder.rejectUnknownEditorKeys(["lowerBound", "upperBound"])
        let container = try decoder.container(keyedBy: CodingKeys.self)
        lowerBound = try container.decode(Int.self, forKey: .lowerBound)
        upperBound = try container.decode(Int.self, forKey: .upperBound)
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
        guard document.schemaVersion == 1 else {
            throw invalid("unsupported schemaVersion", document)
        }
        guard document.id.isEditorBoardIdentifier else {
            throw invalid("board ID must be identifier-shaped", document)
        }
        let requiredStrings = [
            document.manufacturer,
            document.name,
            document.subtitle,
            document.dimensions
        ]
        guard requiredStrings.allSatisfy({ !$0.isEmpty }) else {
            throw invalid("required metadata must not be empty", document)
        }
        guard document.productURL.scheme == "https", document.productURL.host != nil else {
            throw invalid("product URL must be absolute HTTPS", document)
        }
        guard document.aspectRatio.isFinite, document.aspectRatio > 0 else {
            throw invalid("aspect ratio must be positive", document)
        }
        guard document.presentationAssetPath == "assets/primary.png" else {
            throw invalid("presentation.assetPath must be assets/primary.png", document)
        }

        var holdIDs = Set<String>()
        for hold in document.holds {
            guard hold.id.isEditorBoardIdentifier, !hold.name.isEmpty else {
                throw invalid("hold \(hold.id) metadata must be non-empty and identifier-shaped", document)
            }
            guard holdIDs.insert(hold.id).inserted else {
                throw invalid("hold ID \(hold.id) is duplicated", document)
            }
            if let fingerCapacity = hold.fingerCapacity,
               !BoardHold.validFingerCapacityRange.contains(fingerCapacity) {
                throw invalid("hold \(hold.id) has an invalid finger capacity", document)
            }
            if let handCapacity = hold.handCapacity,
               !BoardHold.validHandCapacityRange.contains(handCapacity) {
                throw invalid("hold \(hold.id) has an invalid hand capacity", document)
            }
            if let size = hold.sizeMillimeters, size <= 0 {
                throw invalid("hold \(hold.id) has a non-positive size", document)
            }
            if let depthRange = hold.depthRangeMillimeters,
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
        .object([
            ("schemaVersion", .int(document.schemaVersion)),
            ("id", .string(document.id)),
            ("manufacturer", .string(document.manufacturer)),
            ("name", .string(document.name)),
            ("subtitle", .string(document.subtitle)),
            ("productURL", .string(document.productURL.absoluteString)),
            ("dimensions", .string(document.dimensions)),
            ("aspectRatio", .double(document.aspectRatio)),
            ("presentation", .object([
                ("assetPath", .string(document.presentationAssetPath)),
            ])),
            ("holds", .array(document.holds.map(canonicalHoldValue))),
        ])
    }

    private static func canonicalHoldValue(_ hold: BoardEditableHold) -> CanonicalJSONValue {
        var entries: [(String, CanonicalJSONValue)] = [
            ("id", .string(hold.id)),
            ("name", .string(hold.name)),
            ("kind", .string(hold.kind.rawValue)),
        ]
        if let sizeMillimeters = hold.sizeMillimeters {
            entries.append(("sizeMillimeters", .int(sizeMillimeters)))
        }
        if let depthRange = hold.depthRangeMillimeters {
            entries.append(("depthRangeMillimeters", .object([
                ("lowerBound", .int(depthRange.lowerBound)),
                ("upperBound", .int(depthRange.upperBound)),
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
        entries.append(("geometry", .array(hold.geometry.map(canonicalPieceValue))))
        return .object(entries)
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
