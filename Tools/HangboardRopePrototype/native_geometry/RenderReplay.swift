import Foundation
import simd

guard CommandLine.arguments.count == 6 else {exit(2)}
let doc = try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2]))) as! [String:Any]
let positions = doc["positions"] as! [[[Double]]],radii = doc["radii"] as! [Double]
guard positions.map(\.count) == [715,715] else {throw RopePhysicsError.invalid("Production render chain shape")}
func points(_ rope: [[Double]]) -> [SIMD3<Float>] {
    rope.map {SIMD3(Float($0[0]),Float($0[1]),Float($0[2]))}
}
func same(_ a: Float,_ b: Float) -> Bool {a.bitPattern == b.bitPattern}
var checksum = 0,profiles: [[String:Any]] = []
for segments in [8,6,4] {
    var timings: [Double] = [],originalTimings: [Double] = []
    for iteration in 0..<60 {
        var rendered: [[RopeTubeVertex]] = [],original: [[OriginalRopeTubeVertex]] = []
        func current() throws {
            let start = ProcessInfo.processInfo.systemUptime
            for r in positions.indices {
                rendered.append(try RopeTubeGeometry.vertices(points:points(positions[r]),radialSegments:segments,radius:Float(radii[r])))
            }
            if iteration >= 10 {timings.append(ProcessInfo.processInfo.systemUptime-start)}
        }
        func reference() throws {
            let start = ProcessInfo.processInfo.systemUptime
            for r in positions.indices {
                original.append(try OriginalRopeTubeGeometry.vertices(points:points(positions[r]),radialSegments:segments,radius:Float(radii[r])))
            }
            if iteration >= 10 {originalTimings.append(ProcessInfo.processInfo.systemUptime-start)}
        }
        // Alternate order within one process to reduce shared-host/order bias.
        if iteration % 2 == 0 {try current();try reference()} else {try reference();try current()}
        for r in positions.indices {
            guard zip(original[r],rendered[r]).allSatisfy({a,b in
                (0..<3).allSatisfy {same(a.position[$0],b.position[$0]) && same(a.normal[$0],b.normal[$0])}
            }),original[r].count == rendered[r].count else {throw RopePhysicsError.invalid("Tube optimization changed rendered vertex bits")}
            checksum += rendered[r].count
        }
    }
    profiles.append(["radialSegments":segments,"vertices":positions.reduce(0) {$0+$1.count}*segments,
        "p95Seconds":timings.sorted()[47],"meanSeconds":timings.reduce(0,+)/50,
        "originalReferenceP95Seconds":originalTimings.sorted()[47],"originalReferenceMeanSeconds":originalTimings.reduce(0,+)/50,
        "maximumCircleSilhouetteErrorInRadii":1-cos(Double.pi/Double(segments)),
        "maximumProjectedRadiusForHalfPixelError":0.5/(1-cos(Double.pi/Double(segments)))])
}
let report: [String:Any] = ["owner":ProcessInfo.processInfo.environment["HANGTEN_AFFINE_GEOMETRY_OWNER"]!,
    "scope":"CPU vertex generation plus Double-to-Float conversion for both715-particle loops; mesh upload, RealityKit rendering and physics excluded. Fixed original seed geometry is not an accepted display frame.",
    "renderedVertexBitsMatchOriginal":true,"runtimeRadialSegments":8,"physicalStateChanged":false,
    "radialLODAdopted":false,"devicePerformanceMeasured":false,"measuredRepetitions":50,"warmups":10,
    "profiles":profiles,"checksum":checksum]
let data = try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys])
try data.write(to:URL(fileURLWithPath:CommandLine.arguments[4]));print(String(data:data,encoding:.utf8)!)
