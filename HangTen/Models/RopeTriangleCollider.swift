import simd

struct RopeSurfaceContact: Sendable {
    let point: SIMD3<Double>
    let normal: SIMD3<Double>
    let distance: Double
}

struct RopeSegmentContact: Sendable {
    let centerlinePoint: SIMD3<Double>
    let surfacePoint: SIMD3<Double>
    let normal: SIMD3<Double>
    let fraction: Double
    let penetrationDepth: Double
    var timeOfImpact: Double? = nil
}

/// Exact triangle queries accelerated by an immutable bounding-volume tree.
/// All queries are board-local; the dynamics core owns the moving transform.
struct RopeTriangleCollider: Sendable {
    private struct Node: Sendable {
        let minimum: SIMD3<Double>
        let maximum: SIMD3<Double>
        let left: Int
        let right: Int
        let faces: [Int]
    }
    let mesh: RopeCollisionMesh
    private let tree: [Node]

    init(input: RopePhysicsInput) throws { try self.init(mesh: input.collision) }

    init(mesh: RopeCollisionMesh) throws {
        guard mesh.vertices.count >= 4, mesh.triangles.count >= 4,
              mesh.vertices.allSatisfy({ $0.x.isFinite && $0.y.isFinite && $0.z.isFinite }) else {
            throw RopePhysicsError.invalid("Invalid collision mesh")
        }
        var edges: [SIMD2<Int>: (Int, Int)] = [:], volume = 0.0
        for face in mesh.triangles {
            guard (0..<3).allSatisfy({ face[$0] >= 0 && face[$0] < mesh.vertices.count }),
                  Set([face.x, face.y, face.z]).count == 3 else { throw RopePhysicsError.invalid("Invalid collision triangle") }
            let a = mesh.vertices[face.x], b = mesh.vertices[face.y], c = mesh.vertices[face.z]
            guard simd_length_squared(simd_cross(b-a,c-a)) > 1e-24 else { throw RopePhysicsError.invalid("Degenerate collision triangle") }
            volume += simd_dot(a, simd_cross(b,c))/6
            for (i,j) in [(face.x,face.y),(face.y,face.z),(face.z,face.x)] {
                let key = SIMD2(min(i,j), max(i,j)), old = edges[key] ?? (0,0)
                edges[key] = (old.0+1,old.1+(i < j ? 1 : -1))
            }
        }
        guard volume > 0, edges.values.allSatisfy({ $0.0 == 2 && $0.1 == 0 }) else {
            throw RopePhysicsError.invalid("Collision mesh must be closed with consistent outward winding")
        }
        var nodes: [Node] = []
        func build(_ indices: [Int]) -> Int {
            var low = SIMD3<Double>(repeating: .infinity), high = SIMD3<Double>(repeating: -.infinity)
            for i in indices {
                for j in 0..<3 { let p = mesh.vertices[mesh.triangles[i][j]]; low = simd_min(low,p); high = simd_max(high,p) }
            }
            let index = nodes.count
            nodes.append(Node(minimum:low,maximum:high,left:-1,right:-1,faces:[]))
            if indices.count <= 8 {
                nodes[index] = Node(minimum:low,maximum:high,left:-1,right:-1,faces:indices)
            } else {
                let size = high-low, axis = size.x >= size.y && size.x >= size.z ? 0 : (size.y >= size.z ? 1 : 2)
                let sorted = indices.sorted { a,b in
                    let fa=mesh.triangles[a], fb=mesh.triangles[b]
                    let ca=mesh.vertices[fa.x][axis]+mesh.vertices[fa.y][axis]+mesh.vertices[fa.z][axis]
                    let cb=mesh.vertices[fb.x][axis]+mesh.vertices[fb.y][axis]+mesh.vertices[fb.z][axis]
                    return ca == cb ? a < b : ca < cb
                }
                let split=sorted.count/2, left=build(Array(sorted[..<split])), right=build(Array(sorted[split...]))
                nodes[index] = Node(minimum:low,maximum:high,left:left,right:right,faces:[])
            }
            return index
        }
        _ = build(Array(mesh.triangles.indices))
        self.mesh=mesh; self.tree=nodes
    }

    func closestSurface(at point: SIMD3<Double>) -> RopeSurfaceContact {
        var best = Double.infinity, result = SIMD3<Double>.zero, normal = SIMD3<Double>.zero
        var stack=[0]
        while let index=stack.popLast() {
            let node=tree[index]
            if Self.boxDistanceSquared(point, node.minimum, node.maximum) > best { continue }
            if node.left >= 0 { stack.append(node.left); stack.append(node.right); continue }
            for i in node.faces {
                let f=mesh.triangles[i], a=mesh.vertices[f.x], b=mesh.vertices[f.y], c=mesh.vertices[f.z]
                let q=Self.triangleClosest(point,a,b,c), distance=simd_length_squared(point-q)
                if distance < best { best=distance; result=q; normal=simd_normalize(simd_cross(b-a,c-a)) }
            }
        }
        return RopeSurfaceContact(point:result,normal:normal,distance:sqrt(best))
    }

    func signedDistance(at point: SIMD3<Double>) -> Double {
        let distance=closestSurface(at:point).distance
        if distance < 1e-10 { return 0 }
        return contains(point) ? -distance : distance
    }

    func segmentContact(from start: SIMD3<Double>, to end: SIMD3<Double>, radius: Double) -> RopeSegmentContact? {
        let closest=closestSegment(start,end)
        var contact=closest.contact
        let startSurface=closestSurface(at:start), endSurface=closestSurface(at:end)
        for (p,surface,fraction) in [(start,startSurface,0.0),(end,endSurface,1.0)] where contains(p) {
            let penetration=radius+surface.distance
            if penetration > radius-closest.distance {
                let delta=surface.point-p
                let normal=surface.distance > 1e-10 ? delta/surface.distance : surface.normal
                contact=RopeSegmentContact(centerlinePoint:p,surfacePoint:surface.point,normal:normal,fraction:fraction,penetrationDepth:penetration)
                return contact
            }
        }
        guard closest.distance < radius else { return nil }
        return RopeSegmentContact(centerlinePoint:contact.centerlinePoint,surfacePoint:contact.surfacePoint,normal:contact.normal,
                                  fraction:contact.fraction,penetrationDepth:radius-closest.distance)
    }

    /// Conservative advancement uses the Lipschitz bound on segment motion.
    /// It cannot step over a thin wall merely because the final shape is clear.
    func sweptSegmentContact(previousStart: SIMD3<Double>, previousEnd: SIMD3<Double>, start: SIMD3<Double>, end: SIMD3<Double>, radius: Double) -> RopeSegmentContact? {
        let movement=max(simd_length(start-previousStart),simd_length(end-previousEnd))
        var time=0.0
        for _ in 0..<256 {
            let a=previousStart+(start-previousStart)*time, b=previousEnd+(end-previousEnd)*time
            if var hit=segmentContact(from:a,to:b,radius:radius) { hit.timeOfImpact=time; return hit }
            let nearest=closestSegment(a,b), gap=nearest.distance-radius
            if gap <= 1e-9 {
                var hit=nearest.contact; hit.timeOfImpact=time; return hit
            }
            if movement <= 1e-12 || time >= 1 { return nil }
            let step=0.8*gap/movement
            if time+step > 1 { return segmentContact(from:start,to:end,radius:radius) }
            time += step
        }
        // A bounded query that cannot establish clearance blocks the move.
        let a=previousStart+(start-previousStart)*time, b=previousEnd+(end-previousEnd)*time
        var hit=closestSegment(a,b).contact; hit.timeOfImpact=time; return hit
    }

    private func contains(_ point: SIMD3<Double>) -> Bool {
        let direction=simd_normalize(SIMD3<Double>(1,0.3713906763541037,0.5291502622129182))
        var distances: [Double]=[], stack=[0]
        while let index=stack.popLast() {
            let node=tree[index]
            guard Self.rayBox(point,direction,node.minimum,node.maximum) else { continue }
            if node.left >= 0 { stack.append(node.left); stack.append(node.right); continue }
            for i in node.faces {
                let f=mesh.triangles[i]
                if let t=Self.rayTriangle(point,direction,mesh.vertices[f.x],mesh.vertices[f.y],mesh.vertices[f.z]), t > 1e-10 { distances.append(t) }
            }
        }
        distances.sort()
        var count=0, last = -Double.infinity
        for d in distances where d-last > 1e-9 { count += 1; last=d }
        return count % 2 == 1
    }

    private func closestSegment(_ start: SIMD3<Double>, _ end: SIMD3<Double>) -> (distance:Double,contact:RopeSegmentContact) {
        let low=simd_min(start,end), high=simd_max(start,end)
        var best=Double.infinity
        var contact=RopeSegmentContact(centerlinePoint:start,surfacePoint:start,normal:SIMD3(0,1,0),fraction:0,penetrationDepth:0)
        var stack=[0]
        func consider(_ p: SIMD3<Double>, _ q: SIMD3<Double>, _ fraction:Double, _ faceNormal: SIMD3<Double>) {
            let square=simd_length_squared(p-q)
            if square < best {
                best=square
                let distance=sqrt(square), normal=distance > 1e-10 ? (p-q)/distance : faceNormal
                contact=RopeSegmentContact(centerlinePoint:p,surfacePoint:q,normal:normal,fraction:fraction,penetrationDepth:0)
            }
        }
        while let index=stack.popLast() {
            let node=tree[index], separation=simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3(repeating:0))
            if simd_length_squared(separation) > best { continue }
            if node.left >= 0 { stack.append(node.left); stack.append(node.right); continue }
            for i in node.faces {
                let f=mesh.triangles[i], a=mesh.vertices[f.x], b=mesh.vertices[f.y], c=mesh.vertices[f.z]
                let normal=simd_normalize(simd_cross(b-a,c-a))
                let delta=end-start
                if let t=Self.rayTriangle(start,delta,a,b,c), t >= 0, t <= 1 {
                    let p=start+delta*t; consider(p,p,t,normal)
                }
                consider(start,Self.triangleClosest(start,a,b,c),0,normal)
                consider(end,Self.triangleClosest(end,a,b,c),1,normal)
                for (u,v) in [(a,b),(b,c),(c,a)] {
                    let pair=Self.segmentPair(start,end,u,v)
                    consider(pair.0,pair.1,pair.2,normal)
                }
            }
        }
        return (sqrt(best),contact)
    }

    private static func boxDistanceSquared(_ p: SIMD3<Double>, _ low: SIMD3<Double>, _ high: SIMD3<Double>) -> Double {
        simd_length_squared(simd_max(simd_max(low-p,p-high),SIMD3(repeating:0)))
    }

    private static func rayBox(_ origin: SIMD3<Double>, _ direction: SIMD3<Double>, _ low: SIMD3<Double>, _ high: SIMD3<Double>) -> Bool {
        var near=0.0, far=Double.infinity
        for axis in 0..<3 {
            if abs(direction[axis]) < 1e-15 { if origin[axis] < low[axis] || origin[axis] > high[axis] { return false }; continue }
            let a=(low[axis]-origin[axis])/direction[axis], b=(high[axis]-origin[axis])/direction[axis]
            near=max(near,min(a,b)); far=min(far,max(a,b))
            if near > far { return false }
        }
        return true
    }

    private static func rayTriangle(_ p: SIMD3<Double>, _ direction: SIMD3<Double>, _ a: SIMD3<Double>, _ b: SIMD3<Double>, _ c: SIMD3<Double>) -> Double? {
        let e1=b-a, e2=c-a, cross=simd_cross(direction,e2), determinant=simd_dot(e1,cross)
        guard abs(determinant) > 1e-15 else { return nil }
        let inverse=1/determinant, s=p-a, u=simd_dot(s,cross)*inverse
        guard u >= -1e-12, u <= 1+1e-12 else { return nil }
        let q=simd_cross(s,e1), v=simd_dot(direction,q)*inverse
        guard v >= -1e-12, u+v <= 1+1e-12 else { return nil }
        return simd_dot(e2,q)*inverse
    }

    private static func triangleClosest(_ p: SIMD3<Double>, _ a: SIMD3<Double>, _ b: SIMD3<Double>, _ c: SIMD3<Double>) -> SIMD3<Double> {
        let ab=b-a, ac=c-a, ap=p-a, d1=simd_dot(ab,ap), d2=simd_dot(ac,ap)
        if d1 <= 0 && d2 <= 0 { return a }
        let bp=p-b, d3=simd_dot(ab,bp), d4=simd_dot(ac,bp)
        if d3 >= 0 && d4 <= d3 { return b }
        let vc=d1*d4-d3*d2
        if vc <= 0 && d1 >= 0 && d3 <= 0 { return a+ab*(d1/(d1-d3)) }
        let cp=p-c, d5=simd_dot(ab,cp), d6=simd_dot(ac,cp)
        if d6 >= 0 && d5 <= d6 { return c }
        let vb=d5*d2-d1*d6
        if vb <= 0 && d2 >= 0 && d6 <= 0 { return a+ac*(d2/(d2-d6)) }
        let va=d3*d6-d5*d4
        if va <= 0 && d4-d3 >= 0 && d5-d6 >= 0 { return b+(c-b)*((d4-d3)/((d4-d3)+(d5-d6))) }
        let inverse=1/(va+vb+vc)
        return a+ab*(vb*inverse)+ac*(vc*inverse)
    }

    private static func segmentPair(_ p: SIMD3<Double>, _ q: SIMD3<Double>, _ a: SIMD3<Double>, _ b: SIMD3<Double>) -> (SIMD3<Double>,SIMD3<Double>,Double) {
        let d1=q-p, d2=b-a, r=p-a, aa=simd_dot(d1,d1), ee=simd_dot(d2,d2), f=simd_dot(d2,r)
        var s=0.0, t=0.0
        if aa <= 1e-24 { t=min(1,max(0,f/ee)) }
        else {
            let c=simd_dot(d1,r)
            if ee <= 1e-24 { s=min(1,max(0,-c/aa)) }
            else {
                let bb=simd_dot(d1,d2), denominator=aa*ee-bb*bb
                if denominator > 1e-24 { s=min(1,max(0,(bb*f-c*ee)/denominator)) }
                t=(bb*s+f)/ee
                if t < 0 { t=0; s=min(1,max(0,-c/aa)) }
                else if t > 1 { t=1; s=min(1,max(0,(bb-c)/aa)) }
            }
        }
        return (p+d1*s,a+d2*t,s)
    }
}
