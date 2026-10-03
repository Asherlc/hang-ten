// Native-only output contract: nearest/retained rows, complete scalar merit,
// and every omitted violating face. Original fixed-radius BVH eligibility.
struct RopeWoodFeature:Hashable,Sendable {
    let rope:Int
    let point:Bool
    let index:Int
    let face:Int
}
private struct RopeRawFeature {
    var square=Double.infinity
    var center=SIMD3<Double>.zero
    var surface=SIMD3<Double>.zero
    var fraction=0.0
    var face = -1
    mutating func consider(_ p:SIMD3<Double>,_ q:SIMD3<Double>,_ f:Double,_ id:Int) {
        let d=simd_length_squared(p-q)
        if d<square {square=d;center=p;surface=q;fraction=f;face=id}
    }
}
struct RopeFeatureLinkOutput {
    var first:[RopeMeshFeatureContact]=[]
    var link:[RopeMeshFeatureContact]=[]
    var last:[RopeMeshFeatureContact]=[]
    var merit:[RopeSegmentContact]=[]
    var clearance:Double?=nil
    var blockers:[Int]=[]
}
struct RopeFeatureChainOutput {
    var points:[[RopeSegmentContact]]
    var rows:[[RopeSegmentContact]]
    var merits:[[RopeSegmentContact]]
    var clearances:[Double?]
    var pointFaces:[[Int]]
    var linkFaces:[[Int]]
    var blockers:Set<RopeWoodFeature>
    var insideFallback:Bool
}
extension RopeTriangleCollider {
    private func featureHit(_ raw:RopeRawFeature,radius:Double)->RopeMeshFeatureContact {
        let distance=sqrt(raw.square),face=mesh.triangles[raw.face]
        let a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]
        return RopeMeshFeatureContact(face:raw.face,squaredDistance:raw.square,contact:RopeSegmentContact(
            centerlinePoint:raw.center,surfacePoint:raw.surface,
            normal:distance>1e-10 ? (raw.center-raw.surface)/distance:simd_normalize(simd_cross(b-a,c-a)),
            fraction:raw.fraction,penetrationDepth:radius-distance))
    }
    func featureLinkEvaluation(from start:SIMD3<Double>,to end:SIMD3<Double>,rowRadius:Double,meritRadius:Double,
        heldFirst:[Int],heldLink:[Int],heldLast:[Int])->RopeFeatureLinkOutput {
        let low=simd_min(start,end),high=simd_max(start,end)
        let rowSquare=rowRadius*rowRadius,meritSquare=meritRadius*meritRadius
        var stack=[(0,15)],faces:[(Int,Int)]=[]
        while let (index,parent)=stack.popLast() {
            let node=tree[index]
            let link=simd_length_squared(simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3(repeating:0)))
            let first=simd_length_squared(simd_max(simd_max(node.minimum-start,start-node.maximum),SIMD3(repeating:0)))
            let last=simd_length_squared(simd_max(simd_max(node.minimum-end,end-node.maximum),SIMD3(repeating:0)))
            var mask=parent
            if first>=rowSquare {mask &= ~1};if link>=rowSquare {mask &= ~2}
            if link>=meritSquare {mask &= ~4};if last>=rowSquare {mask &= ~8}
            if mask==0 {continue}
            if node.left>=0 {stack.append((node.left,mask));stack.append((node.right,mask))}
            else {for id in node.faces {faces.append((id,mask))}}
        }
        for id in heldFirst {faces.append((id,16))}
        for id in heldLink {faces.append((id,32))}
        for id in heldLast {faces.append((id,64))}
        faces.sort{$0.0<$1.0}
        var nearestFirst=RopeRawFeature(),nearestLink=RopeRawFeature(),nearestLast=RopeRawFeature(),deepest=RopeRawFeature()
        var result=RopeFeatureLinkOutput(),cursor=0
        while cursor<faces.count {
            let id=faces[cursor].0;var mask=0
            while cursor<faces.count && faces[cursor].0==id {mask |= faces[cursor].1;cursor += 1}
            let face=mesh.triangles[id],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]
            var first=RopeRawFeature(),link=RopeRawFeature(),last=RopeRawFeature()
            if mask & 55 != 0 {
                let q=Self.triangleClosest(start,a,b,c)
                if mask & 17 != 0 {first.consider(start,q,0,id)}
                if mask & 38 != 0 {link.consider(start,q,0,id)}
            }
            if mask & 72 != 0 || (start != end && mask & 38 != 0) {
                let q=Self.triangleClosest(end,a,b,c)
                if mask & 72 != 0 {last.consider(end,q,0,id)}
                if start != end && mask & 38 != 0 {link.consider(end,q,1,id)}
            }
            if start != end && mask & 38 != 0 {
                if let t=Self.rayTriangle(start,end-start,a,b,c),t>=0,t<=1 {
                    let p=start+(end-start)*t;link.consider(p,p,t,id)
                }
                let ab=Self.segmentPair(start,end,a,b),bc=Self.segmentPair(start,end,b,c),ca=Self.segmentPair(start,end,c,a)
                link.consider(ab.0,ab.1,ab.2,id);link.consider(bc.0,bc.1,bc.2,id);link.consider(ca.0,ca.1,ca.2,id)
            }
            if mask & 1 != 0 && first.square<rowSquare && first.square<nearestFirst.square {nearestFirst=first}
            if mask & 2 != 0 && link.square<rowSquare && link.square<nearestLink.square {nearestLink=link}
            if mask & 8 != 0 && last.square<rowSquare && last.square<nearestLast.square {nearestLast=last}
            if mask & 4 != 0 && link.square<meritSquare {
                if link.square<deepest.square {deepest=link}
                if meritRadius-sqrt(link.square)>1e-8 {result.blockers.append(id)}
            }
            if mask & 16 != 0 {result.first.append(featureHit(first,radius:rowRadius))}
            if mask & 32 != 0 {result.link.append(featureHit(link,radius:rowRadius))}
            if mask & 64 != 0 {result.last.append(featureHit(last,radius:rowRadius))}
        }
        if nearestFirst.face>=0 && !heldFirst.contains(nearestFirst.face) {result.first.append(featureHit(nearestFirst,radius:rowRadius))}
        if nearestLink.face>=0 && !heldLink.contains(nearestLink.face) {result.link.append(featureHit(nearestLink,radius:rowRadius))}
        if nearestLast.face>=0 && !heldLast.contains(nearestLast.face) {result.last.append(featureHit(nearestLast,radius:rowRadius))}
        result.first.sort{$0.face<$1.face};result.link.sort{$0.face<$1.face};result.last.sort{$0.face<$1.face}
        if deepest.face>=0 {result.merit=[featureHit(deepest,radius:meritRadius).contact]}
        let minimum=sqrt(nearestLink.square)
        result.clearance=minimum<1e-10 ? 0:minimum
        return result
    }
}
private final class RopeFeatureBatchStorage:@unchecked Sendable {
    let inside:UnsafeMutablePointer<Bool>
    let results:UnsafeMutablePointer<RopeFeatureLinkOutput>
    let pointCount:Int,linkCount:Int
    init(points:Int) {
        pointCount=points;linkCount=points-1
        inside = .allocate(capacity:pointCount);inside.initialize(repeating:false,count:pointCount)
        results = .allocate(capacity:linkCount);results.initialize(repeating:RopeFeatureLinkOutput(),count:linkCount)
    }
    deinit {inside.deinitialize(count:pointCount);inside.deallocate();results.deinitialize(count:linkCount);results.deallocate()}
}
extension RopeTriangleCollider {
    func featureChainContacts(points:[SIMD3<Double>],rope:Int,rowRadius:Double,meritRadius:Double,
        held:Set<RopeWoodFeature>)->RopeFeatureChainOutput {
        precondition(points.count>=2)
        let links=points.count-1,storage=RopeFeatureBatchStorage(points:points.count),jobs=links>=64 ? 4:1
        func ranges(_ count:Int,_ job:Int)->Range<Int> {let chunk=(count+jobs-1)/jobs;return min(count,job*chunk)..<min(count,(job+1)*chunk)}
        var heldPoints=Array(repeating:[Int](),count:points.count),heldLinks=Array(repeating:[Int](),count:links)
        for id in held where id.rope==rope {if id.point {heldPoints[id.index].append(id.face)} else {heldLinks[id.index].append(id.face)}}
        let hp=heldPoints,hl=heldLinks
        DispatchQueue.concurrentPerform(iterations:jobs) {job in
            for i in ranges(points.count,job) {storage.inside[i]=queryParity(points[i])}
        }
        if (0..<points.count).contains(where:{storage.inside[$0]}) {
            let full=fusedChainContacts(points:points,rowRadius:rowRadius,meritRadius:meritRadius)
            return RopeFeatureChainOutput(points:full.points,rows:full.rows,merits:full.merits,clearances:full.clearances,
                pointFaces:Array(repeating:[],count:points.count),linkFaces:Array(repeating:[],count:links),blockers:[],insideFallback:true)
        }
        DispatchQueue.concurrentPerform(iterations:jobs) {job in
            for i in ranges(links,job) {storage.results[i]=featureLinkEvaluation(from:points[i],to:points[i+1],rowRadius:rowRadius,
                meritRadius:meritRadius,heldFirst:hp[i],heldLink:hl[i],heldLast:i==links-1 ? hp[i+1]:[])}
        }
        var output=RopeFeatureChainOutput(points:Array(repeating:[],count:points.count),rows:[],merits:[],clearances:[],
            pointFaces:Array(repeating:[],count:points.count),linkFaces:[],blockers:[],insideFallback:false)
        for i in 0..<links {
            let r=storage.results[i]
            output.points[i]=r.first.map(\.contact);output.pointFaces[i]=r.first.map(\.face)
            output.rows.append(r.link.map(\.contact));output.linkFaces.append(r.link.map(\.face))
            output.merits.append(r.merit);output.clearances.append(r.clearance)
            for face in r.blockers {output.blockers.insert(RopeWoodFeature(rope:rope,point:false,index:i,face:face))}
            if i==links-1 {output.points[i+1]=r.last.map(\.contact);output.pointFaces[i+1]=r.last.map(\.face)}
        }
        return output
    }
}
