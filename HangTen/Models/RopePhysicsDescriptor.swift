import Foundation
import simd

enum RopePhysicsError: Error, LocalizedError, Equatable {
    case invalid(String)
    var errorDescription: String? { if case .invalid(let message) = self { return message }; return nil }
}

struct RopeCollisionMesh: Hashable, Sendable {
    let vertices: [SIMD3<Double>]
    let triangles: [SIMD3<Int>]
}

struct RopePortalRegion: Hashable, Sendable {
    let id: String
    let center: SIMD3<Double>
    let normal: SIMD3<Double>
    let boundary: [SIMD3<Double>]
    let clearanceRadius: Double
}

struct RopeChannelRegion: Hashable, Sendable {
    let id: String
    let portalIDs: [String]
    let spine: [SIMD3<Double>]
    let solid: RopeCollisionMesh
}

struct RopeGraphNode: Hashable, Sendable {
    let id: String
    let kind: String
    let point: SIMD3<Double>?
    let portalID: String?
}

struct RopeGraphEdge: Hashable, Sendable {
    let from: String
    let to: String
    let kind: String
    let channelID: String?
    let winding: String?
}

struct RopePhysicsRope: Hashable, Sendable {
    let id: String
    let baselineRadius: Double
    let radius: Double
    let restLength: Double
    let linearMass: Double
    let nodes: [RopeGraphNode]
    let edges: [RopeGraphEdge]
}

struct RopePhysicsProfile: Hashable, Sendable {
    let id: String
    let presentationID: String
    let instanceID: String?
    let boardMass: Double
    let ropes: [RopePhysicsRope]
}

struct RopePhysicsInput: Hashable, Sendable {
    let modelSHA256: String
    let sourceSHA256: String
    let collision: RopeCollisionMesh
    let portals: [RopePortalRegion]
    let channels: [RopeChannelRegion]
    let profiles: [RopePhysicsProfile]
}

/// Decodes untrusted package data before creating any simulation entities.
struct RopePhysicsDescriptor: Decodable, Sendable {
    private let document: RopeJSON

    init(from decoder: Decoder) throws { document = try RopeJSON(from: decoder) }

    static func decode(_ data: Data) throws -> Self {
        guard data.count <= 64 * 1024 * 1024 else { throw RopePhysicsError.invalid("Physics descriptor exceeds 64 MiB") }
        try rejectDuplicateMembers(data)
        return try JSONDecoder().decode(Self.self, from: data)
    }

    func validated(modelSHA256: String) throws -> RopePhysicsInput {
        let d = try document.object(["schemaVersion", "sourceSHA256", "modelSHA256", "coordinateSystem", "collision", "portals", "channels", "profiles"])
        guard try d["schemaVersion"]!.number() == 1,
              try d["coordinateSystem"]!.string() == "hang-ten-board-v1" else {
            throw RopePhysicsError.invalid("Invalid physics schema or coordinate basis")
        }
        let source = try d["sourceSHA256"]!.string(), model = try d["modelSHA256"]!.string()
        guard [source, model].allSatisfy({ $0.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil }),
              model == modelSHA256 else { throw RopePhysicsError.invalid("Physics model hash mismatch") }
        let collision = try Self.mesh(d["collision"]!)
        let portalValues = try d["portals"]!.indexed()
        let portals = try portalValues.map { value -> RopePortalRegion in
            let p = try value.object(["id", "center", "normal", "boundary"])
            let center = try p["center"]!.vector(), normal = try p["normal"]!.vector()
            let boundary = try p["boundary"]!.array().map { try $0.vector() }
            guard abs(simd_length_squared(normal) - 1) <= 1e-6, boundary.count >= 3,
                  boundary.allSatisfy({ abs(simd_dot($0 - center, normal)) <= 1e-7 }) else {
                throw RopePhysicsError.invalid("Invalid portal normal or plane")
            }
            var signs: [Double] = [], distances: [Double] = []
            for i in boundary.indices {
                let a = boundary[i], edge = boundary[(i + 1) % boundary.count] - a
                let length = simd_length(edge)
                guard length > 1e-10 else { throw RopePhysicsError.invalid("Duplicate portal vertices") }
                let side = simd_dot(simd_cross(edge, center - a), normal)
                signs.append(side); distances.append(abs(side) / length)
                let sides = boundary.map { simd_dot(simd_cross(edge, $0 - a), normal) }
                guard !(sides.min()! < -1e-12 && sides.max()! > 1e-12) else {
                    throw RopePhysicsError.invalid("Portal boundary is not convex")
                }
            }
            guard !(signs.min()! < 0 && signs.max()! > 0), distances.min()! > 0 else {
                throw RopePhysicsError.invalid("Portal center is outside aperture")
            }
            return RopePortalRegion(id: try p["id"]!.identifier(), center: center, normal: normal,
                                    boundary: boundary, clearanceRadius: distances.min()!)
        }
        let portalMap = Dictionary(uniqueKeysWithValues: portals.map { ($0.id, $0) })
        let channels = try d["channels"]!.indexed().map { value -> RopeChannelRegion in
            let c = try value.object(["id", "portalIDs", "spine", "vertices", "triangles"])
            let ids = try c["portalIDs"]!.array().map { try $0.identifier() }
            let spine = try c["spine"]!.array().map { try $0.vector() }
            guard ids.count == 2, Set(ids).count == 2, ids.allSatisfy({ portalMap[$0] != nil }), spine.count >= 2 else {
                throw RopePhysicsError.invalid("Channel must connect two distinct portals")
            }
            let solid = try Self.mesh(.object(["vertices": c["vertices"]!, "triangles": c["triangles"]!]))
            return RopeChannelRegion(id: try c["id"]!.identifier(), portalIDs: ids, spine: spine, solid: solid)
        }
        let channelMap = Dictionary(uniqueKeysWithValues: channels.map { ($0.id, $0) })
        var profileKeys = Set<String>()
        let profiles = try d["profiles"]!.indexed().map { value -> RopePhysicsProfile in
            let p = try value.object(["id", "presentationID", "boardMass", "ropes"], optional: ["instanceID"])
            let presentation = try p["presentationID"]!.identifier(), instance = try p["instanceID"]?.identifier()
            guard profileKeys.insert(presentation + "/" + (instance ?? "")).inserted else {
                throw RopePhysicsError.invalid("Duplicate physics presentation instance")
            }
            let ropes = try p["ropes"]!.indexed().map { value -> RopePhysicsRope in
                let r = try value.object(["id", "baselineRadius", "thicknessScale", "radius", "restLength", "lengthProvenance", "linearMass", "nodes", "edges"])
                let baseline = try r["baselineRadius"]!.positive(), radius = try r["radius"]!.positive()
                let scale=try r["thicknessScale"]!.positive()
                guard abs(radius - baseline * scale) <= 1e-12 else {
                    throw RopePhysicsError.invalid("Radius must equal selected baseline scale")
                }
                _ = try r["lengthProvenance"]!.provenance()
                let nodes = try r["nodes"]!.indexed().map { value -> RopeGraphNode in
                    guard case .object(let raw) = value else { throw RopePhysicsError.invalid("Invalid graph node") }
                    let kind = try raw["kind"]?.string()
                    if kind == "portal" {
                        let n = try value.object(["id", "kind", "portalID"])
                        let pid = try n["portalID"]!.identifier()
                        guard let portal = portalMap[pid], radius < portal.clearanceRadius - 1e-9 else {
                            throw RopePhysicsError.invalid("Rope does not fit graph portal")
                        }
                        return RopeGraphNode(id: try n["id"]!.identifier(), kind: "portal", point: nil, portalID: pid)
                    }
                    guard kind == "support" || kind == "attachment" else { throw RopePhysicsError.invalid("Invalid graph node kind") }
                    let n = try value.object(["id", "kind", "point"])
                    return RopeGraphNode(id: try n["id"]!.identifier(), kind: kind!, point: try n["point"]!.vector(), portalID: nil)
                }
                guard nodes.count >= 2, nodes.first!.kind == "support", ["support", "attachment"].contains(nodes.last!.kind) else {
                    throw RopePhysicsError.invalid("Invalid rope graph endpoints")
                }
                let rawEdges = try r["edges"]!.array()
                guard rawEdges.count == nodes.count - 1 else { throw RopePhysicsError.invalid("Invalid rope graph edge count") }
                let edges = try rawEdges.enumerated().map { i, value -> RopeGraphEdge in
                    let e = try value.object(["from", "to", "kind"], optional: ["channelID", "winding"])
                    let from = try e["from"]!.identifier(), to = try e["to"]!.identifier(), kind = try e["kind"]!.string()
                    let cid = try e["channelID"]?.identifier(), winding = try e["winding"]?.string()
                    guard from == nodes[i].id, to == nodes[i + 1].id else { throw RopePhysicsError.invalid("Graph edges out of order") }
                    if kind == "channel" {
                        guard let cid, let channel = channelMap[cid], winding == nil,
                              let a = nodes[i].portalID, let b = nodes[i + 1].portalID,
                              Set([a, b]) == Set(channel.portalIDs) else { throw RopePhysicsError.invalid("Invalid channel graph edge") }
                    } else {
                        guard kind == "free", cid == nil, winding == nil || ["clockwise", "counterclockwise"].contains(winding!) else {
                            throw RopePhysicsError.invalid("Invalid free graph edge")
                        }
                    }
                    return RopeGraphEdge(from: from, to: to, kind: kind, channelID: cid, winding: winding)
                }
                return RopePhysicsRope(id: try r["id"]!.identifier(), baselineRadius: baseline, radius: radius,
                                       restLength: try r["restLength"]!.positive(), linearMass: try r["linearMass"]!.estimate(), nodes: nodes, edges: edges)
            }
            guard !ropes.isEmpty else { throw RopePhysicsError.invalid("Profile needs ropes") }
            return RopePhysicsProfile(id: try p["id"]!.identifier(), presentationID: presentation, instanceID: instance,
                                      boardMass: try p["boardMass"]!.estimate(), ropes: ropes)
        }
        guard !profiles.isEmpty else { throw RopePhysicsError.invalid("Physics needs profiles") }
        return RopePhysicsInput(modelSHA256: model, sourceSHA256: source, collision: collision, portals: portals, channels: channels, profiles: profiles)
    }

    private static func mesh(_ value: RopeJSON) throws -> RopeCollisionMesh {
        let m = try value.object(["vertices", "triangles"])
        let vertices = try m["vertices"]!.array().map { try $0.vector() }
        let triangles = try m["triangles"]!.array().map { value -> SIMD3<Int> in
            let numbers = try value.array().map { try $0.number() }
            guard numbers.count == 3, numbers.allSatisfy({ $0 >= 0 && $0 < Double(vertices.count) && $0.rounded() == $0 }), Set(numbers).count == 3 else {
                throw RopePhysicsError.invalid("Invalid triangle indices")
            }
            return SIMD3(Int(numbers[0]), Int(numbers[1]), Int(numbers[2]))
        }
        guard vertices.count >= 4, triangles.count >= 4 else { throw RopePhysicsError.invalid("Empty collision solid") }
        var edges: [SIMD2<Int>: (Int, Int)] = [:], volume = 0.0
        for face in triangles {
            let a = vertices[face.x], b = vertices[face.y], c = vertices[face.z]
            guard simd_length_squared(simd_cross(b-a, c-a)) > 1e-24 else { throw RopePhysicsError.invalid("Degenerate collision triangle") }
            volume += simd_dot(a, simd_cross(b,c)) / 6
            for (i,j) in [(face.x,face.y),(face.y,face.z),(face.z,face.x)] {
                let key = SIMD2(min(i,j), max(i,j)), old = edges[key] ?? (0,0)
                edges[key] = (old.0 + 1, old.1 + (i < j ? 1 : -1))
            }
        }
        guard volume > 0, edges.values.allSatisfy({ $0.0 == 2 && $0.1 == 0 }) else {
            throw RopePhysicsError.invalid("Collision solid must be closed with outward consistent winding")
        }
        return RopeCollisionMesh(vertices: vertices, triangles: triangles)
    }

    /// JSONDecoder drops duplicate keys; scan decoded key strings before using it.
    private static func rejectDuplicateMembers(_ data: Data) throws {
        let bytes = Array(data)
        var stack: [Set<String>?] = [], i = 0
        while i < bytes.count {
            switch bytes[i] {
            case 123: stack.append(Set()); i += 1
            case 91: stack.append(nil); i += 1
            case 125, 93:
                guard !stack.isEmpty else { throw RopePhysicsError.invalid("Invalid JSON nesting") }
                stack.removeLast(); i += 1
            case 34:
                let start = i; i += 1
                while i < bytes.count && bytes[i] != 34 {
                    if bytes[i] == 92 { i += 1 }; i += 1
                }
                guard i < bytes.count else { throw RopePhysicsError.invalid("Unterminated JSON string") }
                i += 1
                var next = i
                while next < bytes.count && [9,10,13,32].contains(bytes[next]) { next += 1 }
                if next < bytes.count && bytes[next] == 58 {
                    guard let last = stack.indices.last, var keys = stack[last] else { throw RopePhysicsError.invalid("Invalid JSON member") }
                    let key = try JSONDecoder().decode(String.self, from: Data(bytes[start..<i]))
                    guard keys.insert(key).inserted else { throw RopePhysicsError.invalid("Duplicate physics member \(key)") }
                    stack[last] = keys
                }
            default: i += 1
            }
            guard stack.count < 128 else { throw RopePhysicsError.invalid("Excessive physics nesting") }
        }
    }
}

private indirect enum RopeJSON: Decodable, Sendable {
    case object([String: RopeJSON]), array([RopeJSON]), string(String), number(Double), boolean(Bool), null
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(Bool.self) { self = .boolean(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode([RopeJSON].self) { self = .array(v) }
        else { self = .object(try c.decode([String: RopeJSON].self)) }
    }
    func object(_ required: Set<String>, optional: Set<String> = []) throws -> [String: RopeJSON] {
        guard case .object(let v) = self, required.isSubset(of: Set(v.keys)), Set(v.keys).isSubset(of: required.union(optional)) else {
            throw RopePhysicsError.invalid("Invalid physics members")
        }; return v
    }
    func array() throws -> [RopeJSON] { guard case .array(let v) = self else { throw RopePhysicsError.invalid("Expected physics array") }; return v }
    func string() throws -> String { guard case .string(let v) = self else { throw RopePhysicsError.invalid("Expected physics string") }; return v }
    func number() throws -> Double { guard case .number(let v) = self, v.isFinite else { throw RopePhysicsError.invalid("Expected finite physics number") }; return v }
    func positive() throws -> Double { let v = try number(); guard v > 0 else { throw RopePhysicsError.invalid("Expected positive physics value") }; return v }
    func identifier() throws -> String { let v = try string(); guard v.range(of: "^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", options: .regularExpression) != nil else { throw RopePhysicsError.invalid("Invalid physics ID") }; return v }
    func provenance() throws -> String { let v = try string(); guard !v.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw RopePhysicsError.invalid("Missing physics provenance") }; return v }
    func vector() throws -> SIMD3<Double> { let a = try array().map { try $0.number() }; guard a.count == 3 else { throw RopePhysicsError.invalid("Expected vector3") }; return SIMD3(a[0], a[1], a[2]) }
    func estimate() throws -> Double { let e = try object(["value", "provenance"]); _ = try e["provenance"]!.provenance(); return try e["value"]!.positive() }
    func indexed() throws -> [RopeJSON] {
        let values = try array(); var ids = Set<String>()
        for value in values {
            guard case .object(let d) = value, let id = d["id"], try ids.insert(id.identifier()).inserted else { throw RopePhysicsError.invalid("Duplicate or invalid physics ID") }
        }; return values
    }
}
