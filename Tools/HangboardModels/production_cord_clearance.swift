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
        guard let attachments = document.attachments, let cord = document.cord else {
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

var failures: [String] = []
var count = 0
for slug in ["captain-fingerfood-dual", "captain-fingerfood-pocket", "captain-fingerfood-unlevel", "yy-baguette-evo"] {
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
               paired.leads.contains(where: { $0.samples.last!.y <= 0 }) {
                failures.append("\(slug)/\(poseID): visible cord terminal must tuck into the selected upper channel")
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
precondition(count == 17, "Expected all 17 canonical poses")
if !failures.isEmpty {
    fputs(failures.joined(separator: "\n") + "\n", stderr)
    exit(1)
}
print("All \(count) real-USDZ poses pass the production clearance gate.")
