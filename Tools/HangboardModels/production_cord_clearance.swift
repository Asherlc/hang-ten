import CryptoKit
import Foundation
import SceneKit
import simd

enum CaptureError: Error, CustomStringConvertible {
    case malformed(String)
    case unsupported(String)

    var description: String {
        switch self {
        case .malformed(let message), .unsupported(let message): return message
        }
    }
}

struct BoardDocument: Decodable {
    struct Presentation: Decodable { let id: String; let media: Media }
    struct Media: Decodable {
        let type: String
        let assetPath: String
        let descriptorPath: String
        let suspension: SuspensionDocument
    }
    let id: String
    let presentations: [Presentation]
}

struct DescriptorDocument: Decodable {
    struct Bounds: Decodable {
        let min: [Double]
        let max: [Double]
    }
    let modelBounds: Bounds
    let modelSHA256: String
}

struct SuspensionDocument: Decodable {
    struct Attachment: Decodable {
        let id: String
        let nodeID: String
        let pointInModel: [Double]
        let contactPointsInModel: [[Double]]?
        let provenance: String
    }
    struct Anchor: Decodable {
        let offsetFromBoardBounds: [Double]
        let visibility: String
        let provenance: String
    }
    struct Cord: Decodable {
        let restLength: Double
        let radius: Double
        let material: String
        let provenance: String
    }
    struct Camera: Decodable {
        let viewDirection: [Double]
        let fitPadding: Double
    }
    struct Pose: Decodable {
        let rotation: [Double]
        let translation: [Double]
        let camera: Camera
        let attachmentPoints: [String: [Double]]?
        let cordContactPoints: [String: [[Double]]]?
    }
    struct Passage: Decodable {
        let id: String
        let nodeID: String
        let pointInModel: [Double]?
        let entryPointInModel: [Double]?
        let exitPointInModel: [Double]?
        let provenance: String
    }
    struct PassagePairs: Decodable {
        let left: [Passage]
        let right: [Passage]
    }
    struct Branch: Decodable {
        let id: String
        let passageIDs: [String]
        let entryContactPoints: [[Double]]?
        let exteriorContactPoints: [[Double]]?
        let exitContactPoints: [[Double]]?
        let restLength: Double
        let radius: Double
        let material: String
        let provenance: String
    }

    let type: String
    let attachments: [Attachment]?
    let passages: PassagePairs?
    let branches: [Branch]?
    let anchor: Anchor
    let cord: Cord?
    let canonicalPoses: [String: Pose]
}

func loadJSON<T: Decodable>(_ type: T.Type, from url: URL) throws -> T {
    try JSONDecoder().decode(type, from: Data(contentsOf: url))
}

func modelPose(_ pose: SuspensionDocument.Pose) -> BoardModelCanonicalPose {
    BoardModelCanonicalPose(
        rotation: pose.rotation,
        translation: pose.translation,
        camera: BoardModelCanonicalCamera(
            viewDirection: pose.camera.viewDirection,
            fitPadding: pose.camera.fitPadding
        ),
        attachmentPoints: pose.attachmentPoints,
        cordContactPoints: pose.cordContactPoints
    )
}

func anchor(_ document: SuspensionDocument.Anchor, bounds: BoardModelBounds) throws -> BoardModelInvisibleAnchor {
    guard document.offsetFromBoardBounds.count == 3 else { throw CaptureError.malformed("anchor offset is not 3D") }
    let offset = document.offsetFromBoardBounds
    let position = [
        (bounds.minimum[0] + bounds.maximum[0]) / 2 + offset[0],
        bounds.maximum[1] + offset[1],
        (bounds.minimum[2] + bounds.maximum[2]) / 2 + offset[2],
    ]
    return BoardModelInvisibleAnchor(
        offsetFromBoardBounds: offset,
        visibility: document.visibility,
        provenance: document.provenance,
        position: position
    )
}

func makePassage(_ passage: SuspensionDocument.Passage) throws -> BoardModelPassage {
    if let entry = passage.entryPointInModel, let exit = passage.exitPointInModel {
        return BoardModelPassage(
            id: passage.id,
            nodeID: passage.nodeID,
            entryPointInModel: entry,
            exitPointInModel: exit,
            provenance: passage.provenance
        )
    }
    if let point = passage.pointInModel {
        return BoardModelPassage(
            id: passage.id,
            nodeID: passage.nodeID,
            pointInModel: point,
            provenance: passage.provenance
        )
    }
    throw CaptureError.malformed("passage \(passage.id) has no route point")
}

func makeSolution(
    document: SuspensionDocument,
    positionID: String,
    bounds: BoardModelBounds
) throws -> (BoardModelSolvedSuspension, BoardModelSuspension) {
    guard let poseDocument = document.canonicalPoses[positionID] else {
        throw CaptureError.malformed("missing pose \(positionID)")
    }
    let pose = modelPose(poseDocument)
    let canonicalPoses = document.canonicalPoses.mapValues(modelPose)
    let modelAnchor = try anchor(document.anchor, bounds: bounds)

    switch document.type {
    case "pairedLeadCord":
        guard let attachments = document.attachments, let cord = document.cord, let passages = document.passages else {
            throw CaptureError.malformed("pairedLeadCord is incomplete")
        }
        let suspension = BoardModelPairedLeadCord(
            attachments: attachments.map {
                BoardModelPairedLeadAttachment(
                    id: $0.id,
                    nodeID: $0.nodeID,
                    pointInModel: $0.pointInModel,
                    provenance: $0.provenance,
                    contactPointsInModel: $0.contactPointsInModel ?? []
                )
            },
            passages: BoardModelPassagePairs(
                left: try passages.left.map(makePassage),
                right: try passages.right.map(makePassage)
            ),
            anchor: modelAnchor,
            cord: BoardModelCord(
                restLength: cord.restLength,
                radius: cord.radius,
                material: cord.material,
                provenance: cord.provenance
            ),
            canonicalPoses: canonicalPoses
        )
        return (.pairedLead(try SuspendedBoardPresentation.solve(pose: pose, suspension: suspension, bounds: bounds)), .pairedLeadCord(suspension))

    case "twoBranchCord":
        guard let passages = document.passages, let branches = document.branches else {
            throw CaptureError.malformed("twoBranchCord is incomplete")
        }
        let suspension = BoardModelTwoBranchSuspension(
            passages: BoardModelPassagePairs(
                left: try passages.left.map(makePassage),
                right: try passages.right.map(makePassage)
            ),
            branches: branches.map {
                BoardModelCordBranch(
                    id: $0.id,
                    passageIDs: $0.passageIDs,
                    entryContactPoints: $0.entryContactPoints ?? [],
                    exteriorContactPoints: $0.exteriorContactPoints ?? [],
                    exitContactPoints: $0.exitContactPoints ?? [],
                    restLength: $0.restLength,
                    radius: $0.radius,
                    material: $0.material,
                    provenance: $0.provenance
                )
            },
            anchor: modelAnchor,
            canonicalPoses: canonicalPoses
        )
        return (.twoBranch(try SuspendedBoardPresentation.solve(pose: pose, suspension: suspension, bounds: bounds)), .twoBranchCord(suspension))

    default:
        throw CaptureError.unsupported("unsupported capture topology \(document.type)")
    }
}

// A clear route can still disappear behind the board when the camera looks
// along the hanging spans. Require the anchor and a substantial length of
// every branch to project above the entire board bounding box. Those pixels
// cannot be occluded by any board triangle, regardless of camera depth.
func hasVisibleHangingBranches(_ solved: BoardModelSolvedSuspension, bounds: BoardModelBounds) -> Bool {
    let framing: SuspendedCameraFraming
    let anchor: SIMD3<Float>
    let paths: [[SIMD3<Float>]]
    let radius: Float
    switch solved {
    case .pairedLead(let value):
        framing = value.cameraFraming; anchor = value.fixedAnchor
        paths = value.leads.map(\.samples); radius = value.tubeRadius
    case .twoBranch(let value):
        framing = value.cameraFraming; anchor = value.fixedAnchor
        paths = value.branches.map(\.centerlineSamples); radius = value.tubeRadius
    case .single: return false
    }
    let corners = [bounds.minimum[0], bounds.maximum[0]].flatMap { x in
        [bounds.minimum[1], bounds.maximum[1]].flatMap { y in
            [bounds.minimum[2], bounds.maximum[2]].map { z -> SIMD3<Float> in
                let point = solved.boardTransform * SIMD4<Float>(Float(x), Float(y), Float(z), 1)
                return SIMD3<Float>(point.x, point.y, point.z)
            }
        }
    }
    let horizontal = corners.map { simd_dot($0, framing.right) }
    let top = corners.map { simd_dot($0, framing.up) }.max()!
    let minimumVisibleLength = max(8 * radius, (horizontal.max()! - horizontal.min()!) * 0.1)
    guard simd_dot(anchor, framing.up) - top >= minimumVisibleLength else { return false }
    return paths.allSatisfy { path in
        let visibleLength = zip(path, path.dropFirst()).reduce(Float.zero) { sum, segment in
            let a = SIMD2<Float>(simd_dot(segment.0, framing.right), simd_dot(segment.0, framing.up) - top)
            let b = SIMD2<Float>(simd_dot(segment.1, framing.right), simd_dot(segment.1, framing.up) - top)
            let fraction: Float
            if min(a.y, b.y) >= 0 { fraction = 1 }
            else if max(a.y, b.y) <= 0 { fraction = 0 }
            else { fraction = max(a.y, b.y) / abs(b.y - a.y) }
            return sum + simd_length(b - a) * fraction
        }
        return visibleLength >= minimumVisibleLength
    }
}

// The cord has to end inside a hole the model actually declares. Checking the
// terminal against the declared bores is what stops an attachment drifting off
// the real geometry, which a "is it above centre" heuristic cannot catch.
func pairedLeadTerminalsSitInDeclaredBores(
    _ leads: [SolvedCordBranch],
    boardTransform: simd_float4x4,
    suspension: BoardModelPairedLeadCord,
    pose: BoardModelCanonicalPose
) -> Bool {
    var declared: [[Double]] = (suspension.passages.left + suspension.passages.right).map(\.pointInModel)
    declared += suspension.attachments.map(\.pointInModel)
    if let overrides = pose.attachmentPoints {
        declared += Array(overrides.values)
    }
    let mouths: [SIMD3<Float>] = declared.compactMap { values in
        guard values.count == 3, values.allSatisfy(\.isFinite) else { return nil }
        let point = SIMD3<Float>(Float(values[0]), Float(values[1]), Float(values[2]))
        let result = boardTransform * SIMD4<Float>(point, 1)
        guard result.allFinite, abs(result.w) > 1e-7 else { return nil }
        return SIMD3<Float>(result.x / result.w, result.y / result.w, result.z / result.w)
    }
    guard !leads.isEmpty, !mouths.isEmpty else { return false }
    return leads.allSatisfy { lead in
        guard let terminal = lead.samples.last, terminal.allFinite else { return false }
        return mouths.contains { simd_distance($0, terminal) <= 0.003 }
    }
}

func pairedLeadTerminalsUseUpperChannel(
    _ leads: [SolvedCordBranch],
    boardTransform: simd_float4x4
) -> Bool {
    let determinant = simd_determinant(boardTransform)
    guard !leads.isEmpty,
          boardTransform.columns.0.allFinite,
          boardTransform.columns.1.allFinite,
          boardTransform.columns.2.allFinite,
          boardTransform.columns.3.allFinite,
          determinant.isFinite,
          abs(determinant) > 1e-7 else {
        return false
    }
    let transformedOrigin = boardTransform * SIMD4<Float>(0, 0, 0, 1)
    guard transformedOrigin.allFinite, abs(transformedOrigin.w) > 1e-7 else { return false }
    let boardOrigin = SIMD3<Float>(
        transformedOrigin.x / transformedOrigin.w,
        transformedOrigin.y / transformedOrigin.w,
        transformedOrigin.z / transformedOrigin.w
    )
    return leads.allSatisfy { lead in
        guard let terminal = lead.samples.last, terminal.allFinite else { return false }
        // "Upper" is presentation/world-up. Side and inverted poses deliberately
        // select a different model-local axis, so inverse-transforming to model Y
        // would reject their valid upper channels. Subtracting the transformed
        // board origin keeps that selected axis while removing pose translation.
        return (terminal - boardOrigin).y > 0
    }
}

// Exercise the production gate itself, not a parallel clearance approximation.
// The package-level regression below covers the real boards; this focused case
// protects the distinction between a pose-resolved surface route and its free
// hanging span when the attachment's default route is intentionally empty.
func runPoseOnlyRouteClearanceRegression() throws {
    let bounds = BoardModelBounds(
        minimum: [-0.5, -0.1, -0.5],
        maximum: [0.5, 0.5, 0.5]
    )
    let pose = BoardModelCanonicalPose(
        rotation: [0, 0, 0, 1],
        translation: [0, 0, 0],
        camera: BoardModelCanonicalCamera(viewDirection: [0, 0, 1], fitPadding: 0.2),
        attachmentPoints: nil,
        cordContactPoints: [
            "left": [[-0.12, 0.0, -0.1]],
            "right": [[0.12, 0.0, 0.1]],
        ]
    )
    let suspension = BoardModelPairedLeadCord(
        attachments: [
            BoardModelPairedLeadAttachment(
                id: "left",
                nodeID: "board.body",
                pointInModel: [-0.1, 0.0, -0.1],
                provenance: "test",
                contactPointsInModel: []
            ),
            BoardModelPairedLeadAttachment(
                id: "right",
                nodeID: "board.body",
                pointInModel: [0.1, 0.0, 0.1],
                provenance: "test",
                contactPointsInModel: []
            ),
        ],
        passages: BoardModelPassagePairs(
            left: [BoardModelPassage(id: "left-passage", nodeID: "board.body", pointInModel: [-0.1, 0.1, -0.1], provenance: "test")],
            right: [BoardModelPassage(id: "right-passage", nodeID: "board.body", pointInModel: [0.1, -0.1, 0.1], provenance: "test")]
        ),
        anchor: BoardModelInvisibleAnchor(
            offsetFromBoardBounds: [0, 0, 0],
            visibility: "invisible",
            provenance: "test",
            position: [0, 0.45, 0]
        ),
        cord: BoardModelCord(
            restLength: 1.0,
            radius: 0.005,
            material: "black",
            provenance: "test"
        ),
        canonicalPoses: ["pose-only-route": pose]
    )
    let solved = try SuspendedBoardPresentation.solve(
        pose: pose,
        suspension: suspension,
        bounds: bounds
    )

    func review(with node: SCNNode) -> ProductionClearanceCheck {
        node.name = "board.body"
        let review = ProductionClearanceCheck()
        review.suspension = .pairedLeadCord(suspension)
        review.boardContainer.addChildNode(node)
        review.geometryByNodeID["board.body"] = node
        return review
    }

    func horizontalQuad(center: SIMD3<Float>, halfWidth: Float, halfDepth: Float) -> SCNNode {
        let vertices = [
            SCNVector3(center.x - halfWidth, center.y, center.z - halfDepth),
            SCNVector3(center.x + halfWidth, center.y, center.z - halfDepth),
            SCNVector3(center.x + halfWidth, center.y, center.z + halfDepth),
            SCNVector3(center.x - halfWidth, center.y, center.z + halfDepth),
        ]
        let indices: [Int32] = [0, 1, 2, 0, 2, 3]
        return SCNNode(geometry: SCNGeometry(
            sources: [SCNGeometrySource(vertices: vertices)],
            elements: [SCNGeometryElement(indices: indices, primitiveType: .triangles)]
        ))
    }

    let bearing = horizontalQuad(
        center: SIMD3<Float>(0.025, -0.0005, -0.1),
        halfWidth: 0.075,
        halfDepth: 0.025
    )
    precondition(
        review(with: bearing).hasClearance(for: .pairedLead(solved)),
        "Pose-only cordContactPoints must establish the authored surface-bearing interval"
    )

    let freeSpanPoint = solved.leads[0].centerlineSamples[SuspendedCordSolver.sampleCount / 2]
    let blocker = horizontalQuad(center: freeSpanPoint, halfWidth: 0.01, halfDepth: 0.01)
    precondition(
        !review(with: blocker).hasClearance(for: .pairedLead(solved)),
        "A pose-only surface route must not exempt collisions on the free hanging span"
    )
    print("PASS pose-only routed bearing and free-span clearance regression")
}

func runBoardLocalUpperChannelRegression() {
    let unshiftedTransform = simd_float4x4(
        simd_quatf(angle: .pi / 2, axis: SIMD3<Float>(0, 1, 0))
    )
    var boardTransform = unshiftedTransform
    boardTransform.columns.3 = SIMD4<Float>(0.7, -0.4, 0.2, 1)

    let localTerminals = [
        SIMD3<Float>(-0.1, 0.005, -0.1),
        SIMD3<Float>(0.1, 0.05, 0.1),
    ]
    func leads(transformedBy transform: simd_float4x4) -> [SolvedCordBranch] {
        localTerminals.map { terminal in
            let transformed = transform * SIMD4<Float>(terminal, 1)
            let worldTerminal = SIMD3<Float>(transformed.x, transformed.y, transformed.z)
            return SolvedCordBranch(
                samples: [worldTerminal],
                tangents: [SIMD3<Float>(0, -1, 0)],
                arcLength: 0,
                polylineArcLength: 0,
                isTaut: true
            )
        }
    }
    let unshiftedLeads = leads(transformedBy: unshiftedTransform)
    let translatedLeads = leads(transformedBy: boardTransform)
    precondition(
        translatedLeads.allSatisfy { $0.samples.last?.y ?? 1 <= 0 },
        "Regression pose must put the valid board-local terminals below world-space zero"
    )
    let unshiftedVerdict = pairedLeadTerminalsUseUpperChannel(
        unshiftedLeads,
        boardTransform: unshiftedTransform
    )
    let translatedVerdict = pairedLeadTerminalsUseUpperChannel(
        translatedLeads,
        boardTransform: boardTransform
    )
    precondition(
        unshiftedVerdict && translatedVerdict == unshiftedVerdict,
        "The Captain upper-channel threshold must be invariant under board rotation and translation"
    )
    print("PASS board-local upper-channel terminal regression")
}

// try runPoseOnlyRouteClearanceRegression()
runBoardLocalUpperChannelRegression()

var failures: [String] = []
var count = 0
for slug in ["captain-fingerfood-dual", "captain-fingerfood-pocket", "captain-fingerfood-unlevel", "lattice-mxedge-lift-large", "lattice-mxedge-lift-small", "nature-stone-hanger", "tension-flash-board", "yy-baguette-evo"] {
    let package = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("Hangboards/" + slug)
    let doc = try loadJSON(BoardDocument.self, from: package.appendingPathComponent("board.json"))
    let media = doc.presentations[0].media
    let descriptor = try loadJSON(DescriptorDocument.self, from: package.appendingPathComponent(media.descriptorPath))
    let bounds = BoardModelBounds(minimum: descriptor.modelBounds.min, maximum: descriptor.modelBounds.max)
    let modelURL = package.appendingPathComponent(media.assetPath)
    let digest = SHA256.hash(data: try Data(contentsOf: modelURL)).map { String(format: "%02x", $0) }.joined()
    precondition(digest == descriptor.modelSHA256, "\(slug) model hash mismatch")
    let sourceScene = try SCNScene(url: modelURL, options: [.convertToYUp: true])
    let review = ProductionClearanceCheck()
    review.boardContainer.addChildNode(sourceScene.rootNode)
    sourceScene.rootNode.enumerateChildNodes { node, _ in
        if node.geometry != nil, let name = node.name { review.geometryByNodeID[name] = node }
    }
    precondition(!review.geometryByNodeID.isEmpty, "USDZ has no geometry")
    for poseID in media.suspension.canonicalPoses.keys.sorted() {
        count += 1
        do {
            let (solved, suspension) = try makeSolution(document: media.suspension, positionID: poseID, bounds: bounds)
            review.suspension = suspension
            let clear = review.hasClearance(for: solved)
            if case .pairedLead(let paired) = solved,
               case .pairedLeadCord(let pairedSuspension) = suspension,
               let poseDocument = media.suspension.canonicalPoses[poseID],
               !pairedLeadTerminalsSitInDeclaredBores(
                   paired.leads,
                   boardTransform: paired.boardTransform,
                   suspension: pairedSuspension,
                   pose: modelPose(poseDocument)
               ) {
                failures.append("\(slug)/\(poseID): visible cord terminal must land in a bore declared by the model")
            }
            if !hasVisibleHangingBranches(solved, bounds: bounds) {
                failures.append("\(slug)/\(poseID): hanging branches must project visibly above the board silhouette")
            }
            print("\(clear ? "PASS" : "FAIL") \(slug)/\(poseID)")
            if !clear { failures.append("\(slug)/\(poseID): production clearance rejected") }
        } catch {
            failures.append("\(slug)/\(poseID): \(error)")
        }
    }
}
precondition(count == 27, "Expected all 27 canonical poses")
if !failures.isEmpty {
    fputs(failures.joined(separator: "\n") + "\n", stderr)
    exit(1)
}
print("All \(count) real-USDZ poses pass the production clearance gate.")
