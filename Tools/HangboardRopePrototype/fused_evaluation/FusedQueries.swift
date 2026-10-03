// Added to a native snapshot only. Original kernels and per-query ordering remain authoritative.
extension RopeTriangleCollider {
    // Outputs: point(start), link(row), link(merit), point(end).
    func fusedContacts(from start:SIMD3<Double>,to end:SIMD3<Double>,rowRadius:Double,meritRadius:Double,
                       startInside:Bool,endInside:Bool)->[[RopeSegmentContact]] {
        if startInside || endInside {
            return [segmentContacts(from:start,to:start,radius:rowRadius),
                    segmentContacts(from:start,to:end,radius:rowRadius),
                    segmentContacts(from:start,to:end,radius:meritRadius),
                    segmentContacts(from:end,to:end,radius:rowRadius)]
        }
        let low=simd_min(start,end),high=simd_max(start,end)
        let rowSquare=rowRadius*rowRadius,meritSquare=meritRadius*meritRadius
        var stack=[(0,15)],faces:[(Int,Int)]=[],firstHits:[RopeSegmentContact]=[],rowHits:[RopeSegmentContact]=[],meritHits:[RopeSegmentContact]=[],lastHits:[RopeSegmentContact]=[]
        while let (index,parent)=stack.popLast() {
            let node=tree[index]
            let link=simd_length_squared(simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3(repeating:0)))
            let first=simd_length_squared(simd_max(simd_max(node.minimum-start,start-node.maximum),SIMD3(repeating:0)))
            let last=simd_length_squared(simd_max(simd_max(node.minimum-end,end-node.maximum),SIMD3(repeating:0)))
            var mask=parent
            if first>=rowSquare {mask &= ~1}
            if link>=rowSquare {mask &= ~2}
            if link>=meritSquare {mask &= ~4}
            if last>=rowSquare {mask &= ~8}
            if mask==0 {continue}
            if node.left>=0 {stack.append((node.left,mask));stack.append((node.right,mask))}
            else {for face in node.faces {faces.append((face,mask))}}
        }
        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {
            let face=mesh.triangles[index],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]
            let normal=simd_normalize(simd_cross(b-a,c-a))
            var first=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)
            var row=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)
            var merit=FusedWitness(best:meritSquare,radius:meritRadius,faceNormal:normal)
            var last=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)
            if mask & 7 != 0 {
                let q=Self.triangleClosest(start,a,b,c)
                if mask & 1 != 0 {first.consider(start,q,0)};if mask & 2 != 0 {row.consider(start,q,0)};if mask & 4 != 0 {merit.consider(start,q,0)}
            }
            if mask & 8 != 0 || (start != end && mask & 6 != 0) {
                let q=Self.triangleClosest(end,a,b,c)
                if mask & 8 != 0 {last.consider(end,q,0)}
                if start != end {if mask & 2 != 0 {row.consider(end,q,1)};if mask & 4 != 0 {merit.consider(end,q,1)}}
            }
            if start != end && mask & 6 != 0 {
                if let t=Self.rayTriangle(start,end-start,a,b,c),t>=0,t<=1 {
                    let p=start+(end-start)*t;if mask & 2 != 0 {row.consider(p,p,t)};if mask & 4 != 0 {merit.consider(p,p,t)}
                }
                let ab=Self.segmentPair(start,end,a,b),bc=Self.segmentPair(start,end,b,c),ca=Self.segmentPair(start,end,c,a)
                for q in [ab,bc,ca] {if mask & 2 != 0 {row.consider(q.0,q.1,q.2)};if mask & 4 != 0 {merit.consider(q.0,q.1,q.2)}}
            }
            Self.mergeFused(first.hit,into:&firstHits);Self.mergeFused(row.hit,into:&rowHits)
            Self.mergeFused(merit.hit,into:&meritHits);Self.mergeFused(last.hit,into:&lastHits)
        }
        return [firstHits,rowHits,meritHits,lastHits]
    }
    private struct FusedWitness {
        var best:Double
        let radius:Double
        let faceNormal:SIMD3<Double>
        var hit:RopeSegmentContact?
        mutating func consider(_ p:SIMD3<Double>,_ q:SIMD3<Double>,_ fraction:Double) {
            let distanceSquared=simd_length_squared(p-q)
            guard distanceSquared<best else{return}
            best=distanceSquared
            let distance=sqrt(distanceSquared)
            hit=RopeSegmentContact(centerlinePoint:p,surfacePoint:q,
                normal:distance>1e-10 ? (p-q)/distance:faceNormal,fraction:fraction,penetrationDepth:radius-distance)
        }
    }
    private static func mergeFused(_ witness:RopeSegmentContact?,into result:inout [RopeSegmentContact]) {
        guard let hit=witness else{return}
        if let duplicate=result.firstIndex(where:{abs($0.fraction-hit.fraction)<1e-6 && simd_dot($0.normal,hit.normal)>1-1e-8}) {
            if hit.penetrationDepth>result[duplicate].penetrationDepth {result[duplicate]=hit}
        } else {result.append(hit)}
    }
}
