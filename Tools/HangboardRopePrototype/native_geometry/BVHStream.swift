import Foundation
import Metal
import simd

struct IntegerBounds {
    var low: SIMD4<Int32>
    var high: SIMD4<Int32>
    init(_ points: [SIMD3<Double>]) throws {
        guard !points.isEmpty, points.allSatisfy({ simd_reduce_max(simd_abs($0)) < 100 && $0.x.isFinite && $0.y.isFinite && $0.z.isFinite }) else {
            throw RopePhysicsError.invalid("Integer bounds coordinate range")
        }
        var lo = SIMD3<Double>(repeating: .infinity), hi = SIMD3<Double>(repeating: -.infinity)
        for p in points { lo = simd_min(lo, p); hi = simd_max(hi, p) }
        let l = (0..<3).map { Int32(floor((lo[$0] * 1e6).nextDown)) }
        let h = (0..<3).map { Int32(ceil((hi[$0] * 1e6).nextUp)) }
        low = SIMD4(l[0], l[1], l[2], 0); high = SIMD4(h[0], h[1], h[2], 0)
    }
}
struct BVHNode { var bounds: IntegerBounds; var links: SIMD4<Int32> }
struct BVHQuery {
    var bounds: IntegerBounds
    var radiusSquared: UInt64
    var padding: UInt64 = 0
    init(_ points: [SIMD3<Double>], _ radius: Double) throws {
        guard radius.isFinite && radius > 0 && radius < 1 else { throw RopePhysicsError.invalid("Query radius") }
        bounds = try IntegerBounds(points)
        let r = UInt64(ceil((radius * 1e6).nextUp)); radiusSquared = r * r
    }
}
func integerIntersects(_ bounds: IntegerBounds, _ query: BVHQuery) -> Bool {
    var square: UInt64 = 0
    for axis in 0..<3 {
        let gap = max(0, max(Int64(bounds.low[axis]) - Int64(query.bounds.high[axis]), Int64(query.bounds.low[axis]) - Int64(bounds.high[axis])))
        square += UInt64(gap * gap)
    }
    return square <= query.radiusSquared
}
final class BVHStream {
    let deviceName: String
    private let device: MTLDevice
    private let queue: MTLCommandQueue
    private let pipeline: MTLComputePipelineState
    private let nodeBuffer: MTLBuffer, faceBuffer: MTLBuffer, triangleBuffer: MTLBuffer
    private let owner: String
    private let nodeCount: Int, triangleCount: Int
    private(set) var gpuSeconds = 0.0
    private(set) var candidateCount = 0
    init(nodes: [BVHNode], faces: [UInt32], triangles: [IntegerBounds]) throws {
        guard let owner = ProcessInfo.processInfo.environment["HANGTEN_GEOMETRY_SCREEN_OWNER"], owner == URL(fileURLWithPath:FileManager.default.currentDirectoryPath).lastPathComponent,
              let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue(),
              !nodes.isEmpty, triangles.count <= 8_000_000, faces.count == triangles.count,
              Set(faces) == Set(triangles.indices.map(UInt32.init)),
              MemoryLayout<BVHNode>.stride == 48, MemoryLayout<BVHQuery>.stride == 48 else {
            throw RopePhysicsError.invalid("GPU BVH setup")
        }
        var visited = Set<Int>(), coveredSlots = Set<Int>()
        func check(_ index: Int, _ depth: Int) throws {
            guard nodes.indices.contains(index), depth < 63, visited.insert(index).inserted else { throw RopePhysicsError.invalid("GPU BVH tree shape") }
            let n = nodes[index], l = n.links
            guard (0..<3).allSatisfy({ n.bounds.low[$0] <= n.bounds.high[$0] && n.bounds.low[$0] >= -100_000_001 && n.bounds.high[$0] <= 100_000_001 }) else {
                throw RopePhysicsError.invalid("GPU BVH bounds")
            }
            if l.x >= 0 {
                guard l.y >= 0, l.w == 0 else { throw RopePhysicsError.invalid("GPU BVH children") }
                for child in [Int(l.x),Int(l.y)] {
                    guard nodes.indices.contains(child), (0..<3).allSatisfy({ nodes[child].bounds.low[$0] >= n.bounds.low[$0] && nodes[child].bounds.high[$0] <= n.bounds.high[$0] }) else { throw RopePhysicsError.invalid("GPU BVH containment") }
                    try check(child, depth+1)
                }
            } else {
                guard l.y == -1, l.z >= 0, l.w > 0, Int(l.z)+Int(l.w) <= faces.count else { throw RopePhysicsError.invalid("GPU BVH leaf") }
                for j in Int(l.z)..<(Int(l.z)+Int(l.w)) {
                    guard coveredSlots.insert(j).inserted else { throw RopePhysicsError.invalid("GPU BVH overlapping leaves") }
                    let f = triangles[Int(faces[j])]
                    guard (0..<3).allSatisfy({ f.low[$0] >= n.bounds.low[$0] && f.high[$0] <= n.bounds.high[$0] }) else { throw RopePhysicsError.invalid("GPU BVH leaf containment") }
                }
            }
        }
        try check(0,0)
        guard visited.count == nodes.count, coveredSlots.count == faces.count else { throw RopePhysicsError.invalid("GPU BVH unreachable nodes or omitted facets") }
        self.owner = owner; self.device = device; self.queue = queue; deviceName = device.name
        queue.label = owner + "-bvh-contact-queue"
        let options = MTLCompileOptions(); options.fastMathEnabled = false
        let library = try device.makeLibrary(source: Self.shader, options: options)
        pipeline = try device.makeComputePipelineState(function: library.makeFunction(name: "candidates")!)
        func buffer<T>(_ values: [T], _ name: String) throws -> MTLBuffer {
            guard let b = values.withUnsafeBytes({ device.makeBuffer(bytes:$0.baseAddress!,length:$0.count,options:.storageModeShared) }) else { throw RopePhysicsError.invalid("GPU BVH allocation") }
            b.label = owner + "-" + name; return b
        }
        nodeBuffer = try buffer(nodes,"bvh-nodes"); faceBuffer = try buffer(faces,"bvh-faces"); triangleBuffer = try buffer(triangles,"bvh-triangles")
        nodeCount = nodes.count; triangleCount = triangles.count
    }
    func candidates(_ queries: [BVHQuery]) throws -> [[Int]] {
        guard !queries.isEmpty, queries.count <= 100_000 else { throw RopePhysicsError.invalid("GPU BVH query budget") }
        func allocate(_ bytes: Int, _ name: String) throws -> MTLBuffer {
            guard let b = device.makeBuffer(length:max(4,bytes),options:.storageModeShared) else { throw RopePhysicsError.invalid("GPU BVH allocation") }
            b.label = owner + "-" + name; return b
        }
        let queryBuffer = try allocate(queries.count * MemoryLayout<BVHQuery>.stride,"bvh-queries")
        queries.withUnsafeBytes { queryBuffer.contents().copyMemory(from:$0.baseAddress!,byteCount:$0.count) }
        let countBuffer = try allocate(queries.count * MemoryLayout<SIMD2<UInt32>>.stride,"bvh-counts")
        let offsetBuffer = try allocate(queries.count * 4,"bvh-offsets")
        let placeholder = try allocate(4,"bvh-placeholder")
        func run(_ output: MTLBuffer, _ emitting: Bool) throws -> Double {
            guard let command = queue.makeCommandBuffer(), let encoder = command.makeComputeCommandEncoder() else { throw RopePhysicsError.invalid("GPU BVH command") }
            command.label = owner + (emitting ? "-bvh-emit" : "-bvh-count")
            encoder.setComputePipelineState(pipeline)
            for (i,b) in [nodeBuffer,faceBuffer,triangleBuffer,queryBuffer,countBuffer,offsetBuffer,output].enumerated() { encoder.setBuffer(b,offset:0,index:i) }
            var config = SIMD4<UInt32>(UInt32(queries.count),UInt32(nodeCount),UInt32(triangleCount),emitting ? 1 : 0)
            encoder.setBytes(&config,length:MemoryLayout<SIMD4<UInt32>>.stride,index:7)
            encoder.dispatchThreads(MTLSize(width:queries.count,height:1,depth:1),threadsPerThreadgroup:MTLSize(width:min(64,pipeline.maxTotalThreadsPerThreadgroup),height:1,depth:1))
            encoder.endEncoding(); command.commit(); command.waitUntilCompleted()
            guard command.status == .completed else { throw command.error ?? RopePhysicsError.invalid("GPU BVH command failed") }
            return command.gpuEndTime-command.gpuStartTime
        }
        gpuSeconds = try run(placeholder,false)
        let counts = countBuffer.contents().bindMemory(to:SIMD2<UInt32>.self,capacity:queries.count)
        let offsets = offsetBuffer.contents().bindMemory(to:UInt32.self,capacity:queries.count)
        var total = 0, sizes: [Int] = []
        for i in queries.indices {
            guard counts[i].y == 0 else { throw RopePhysicsError.invalid("GPU BVH traversal failure") }
            offsets[i] = UInt32(total); let n = Int(counts[i].x); sizes.append(n); total += n
            guard total <= 8_000_000 else { throw RopePhysicsError.invalid("GPU BVH candidate budget") }
        }
        let output = try allocate(total * 4,"bvh-candidates")
        gpuSeconds += try run(output,true)
        let ids = output.contents().bindMemory(to:UInt32.self,capacity:max(total,1))
        var result: [[Int]] = []; result.reserveCapacity(queries.count)
        for i in queries.indices {
            guard counts[i].y == 0, Int(counts[i].x) == sizes[i] else { throw RopePhysicsError.invalid("GPU BVH emission mismatch") }
            let start = Int(offsets[i]); result.append((start..<(start+sizes[i])).map { Int(ids[$0]) }.sorted())
        }
        candidateCount = total
        return result
    }
    private static let shader = """
    #include <metal_stdlib>
    using namespace metal;
    struct Bounds { int4 low; int4 high; };
    struct Node { Bounds bounds; int4 links; };
    struct Query { Bounds bounds; ulong radiusSquared; ulong padding; };
    bool intersects(Bounds b, Query q) {
        ulong square=0;
        for(uint a=0;a<3;a++) {
            long gap=max(long(0),max(long(b.low[a])-long(q.bounds.high[a]),long(q.bounds.low[a])-long(b.high[a])));
            square+=ulong(gap*gap);
        }
        return square<=q.radiusSquared;
    }
    kernel void candidates(device const Node *nodes [[buffer(0)]],device const uint *faces [[buffer(1)]],
        device const Bounds *triangles [[buffer(2)]],device const Query *queries [[buffer(3)]],
        device uint2 *counts [[buffer(4)]],device const uint *offsets [[buffer(5)]],
        device uint *output [[buffer(6)]],constant uint4 &config [[buffer(7)]],uint qi [[thread_position_in_grid]]) {
        if(qi>=config.x) return;
        Query q=queries[qi]; uint stack[64]; uint top=1,found=0,status=0,visits=0;
        stack[0]=0; uint expected=config.w ? counts[qi].x : 0;
        while(top>0) {
            uint index=stack[--top];
            if(index>=config.y || ++visits>config.y) {status=1;break;}
            Node n=nodes[index]; if(!intersects(n.bounds,q))continue;
            if(n.links.x>=0) {
                if(top+2>64){status=2;break;}
                stack[top++]=uint(n.links.x);stack[top++]=uint(n.links.y);
            } else {
                for(int j=0;j<n.links.w;j++) {
                    uint face=faces[n.links.z+j];
                    if(face>=config.z){status=3;break;}
                    if(intersects(triangles[face],q)) {
                        if(config.w) {
                            if(found>=expected){status=4;break;}
                            output[offsets[qi]+found]=face;
                        }
                        found++;
                    }
                }
                if(status)break;
            }
        }
        counts[qi]=uint2(found,status);
    }
    """
}
