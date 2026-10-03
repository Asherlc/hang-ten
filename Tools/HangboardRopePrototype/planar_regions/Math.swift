import Foundation
import simd

struct RopePlanarCandidates {
    let first:[(SIMD3<Double>,SIMD3<Double>,Double)]
    let last:[(SIMD3<Double>,SIMD3<Double>,Double)]
    let link:[(SIMD3<Double>,SIMD3<Double>,Double)]
    let boundaryPairs:Int
}
struct RopePlanarWork:Sendable {
    var calls=0,boundaryPairs=0,fallbacks=0
}
struct RopePlanarRegion:Sendable {
    let axis:Int,coordinate:Double
    let edges:[(SIMD3<Double>,SIMD3<Double>)]
    let normal:SIMD3<Double>
    let faces:[Int]
    func containsProjection(_ point:SIMD3<Double>)->Bool? {
        guard axis>=0,axis<3,!edges.isEmpty,
              point.x.isFinite,point.y.isFinite,point.z.isFinite,
              max(abs(point.x),max(abs(point.y),abs(point.z)))<=0.5 else{return nil}
        let u=axis==0 ? 1:0,v=axis==2 ? 1:2
        var inside=false
        for (a,b) in edges {
            let dx=b[u]-a[u],dy=b[v]-a[v]
            let cross=dx*(point[v]-a[v])-dy*(point[u]-a[u])
            // Domain <=.5m bounds the subtraction/product error below32 ulps(m^2).
            // A boundary-ambiguous membership sends the entire patch to the original.
            if abs(cross)<=32*Double.ulpOfOne,
               point[u]>=min(a[u],b[u])-1e-9,point[u]<=max(a[u],b[u])+1e-9,
               point[v]>=min(a[v],b[v])-1e-9,point[v]<=max(a[v],b[v])+1e-9 {return nil}
            if (a[v]>point[v]) != (b[v]>point[v]) {
                if abs(cross)<=32*Double.ulpOfOne {return nil}
                if (cross>0)==(dy>0) {inside.toggle()}
            }
        }
        return inside
    }
    func projected(_ point:SIMD3<Double>)->SIMD3<Double> {
        var result=point;result[axis]=coordinate;return result
    }
    func candidates(_ start:SIMD3<Double>,_ end:SIMD3<Double>)->RopePlanarCandidates? {
        guard let firstInside=containsProjection(start),let lastInside=containsProjection(end) else{return nil}
        var first:[(SIMD3<Double>,SIMD3<Double>,Double)]=[],last:[(SIMD3<Double>,SIMD3<Double>,Double)]=[],pairs=0
        if firstInside {first=[(start,projected(start),0)]}
        else {for (a,b) in edges {first.append(RopeTriangleCollider.segmentPair(start,start,a,b));pairs += 1}}
        if start==end {return RopePlanarCandidates(first:first,last:first,link:first,boundaryPairs:pairs)}
        if lastInside {last=[(end,projected(end),1)]}
        else {for (a,b) in edges {let p=RopeTriangleCollider.segmentPair(end,end,a,b);last.append((p.0,p.1,1));pairs += 1}}
        var link=first+last
        let divisor=end[axis]-start[axis]
        if divisor != 0 {
            let fraction=(coordinate-start[axis])/divisor
            if fraction>=0,fraction<=1 {
                let p=start+(end-start)*fraction
                guard let inside=containsProjection(p) else{return nil}
                if inside {link.append((p,p,fraction))}
            }
        }
        for (a,b) in edges {link.append(RopeTriangleCollider.segmentPair(start,end,a,b));pairs += 1}
        return RopePlanarCandidates(first:first,last:last,link:link,boundaryPairs:pairs)
    }
}
func planarRegionFixtures()throws {
    func region(_ axis:Int)->RopePlanarRegion {
        let axes=(0..<3).filter{$0 != axis}
        func p(_ x:Double,_ y:Double)->SIMD3<Double> {var r=SIMD3<Double>.zero;r[axes[0]]=x;r[axes[1]]=y;return r}
        let outer=[p(-0.02,-0.02),p(0.02,-0.02),p(0.02,0.02),p(-0.02,0.02)]
        let hole=[p(-0.005,-0.005),p(-0.005,0.005),p(0.005,0.005),p(0.005,-0.005)]
        var edges:[(SIMD3<Double>,SIMD3<Double>)]=[]
        for loop in [outer,hole] {for i in loop.indices {edges.append((loop[i],loop[(i+1)%loop.count]))}}
        var normal=SIMD3<Double>.zero;normal[axis]=1
        return RopePlanarRegion(axis:axis,coordinate:0,edges:edges,normal:normal,faces:[])
    }
    for axis in 0..<3 {
        let r=region(axis),axes=(0..<3).filter{$0 != axis}
        func p(_ x:Double,_ y:Double,_ height:Double)->SIMD3<Double> {var v=SIMD3<Double>.zero;v[axes[0]]=x;v[axes[1]]=y;v[axis]=height;return v}
        guard r.containsProjection(p(0.01,0,0))==true,r.containsProjection(p(0,0,0))==false,
              r.containsProjection(p(0.03,0,0))==false,r.containsProjection(p(0.005,0,0))==nil else {
            throw RopePhysicsError.invalid("planar region holes/interior/exterior/boundary")
        }
        func minimum(_ start:SIMD3<Double>,_ end:SIMD3<Double>)throws->Double {
            guard let candidates=r.candidates(start,end),!candidates.link.isEmpty else {throw RopePhysicsError.invalid("planar region candidate unknown")}
            return candidates.link.map{simd_distance($0.0,$0.1)}.min()!
        }
        // Crossing through wood vs through a hole.
        guard try minimum(p(0.01,0,0.01),p(0.01,0,-0.01))==0,
              abs(try minimum(p(0,0,0.01),p(0,0,-0.01))-0.005)<1e-12,
              // Parallel link endpoints lie beyond the region, but its interior crosses wood.
              abs(try minimum(p(-0.03,0.01,0.0036),p(0.03,0.01,0.0036))-0.0036)<1e-12,
              // Hole corner: diagonal wall response must not fill the hole.
              abs(try minimum(p(0.004,0.004,0),p(0.004,0.004,0))-0.001)<1e-12 else {
            throw RopePhysicsError.invalid("planar crossing/parallel/hole-corner minimum")
        }
        let a=p(-0.01,0.01,0.0036),b=p(0.01,0.01,0.0036)
        guard let candidates=r.candidates(a,b),candidates.link.contains(where:{$0.2==0 && simd_distance($0.0,$0.1)==0.0036}),
              candidates.link.contains(where:{$0.2==1 && simd_distance($0.0,$0.1)==0.0036}) else {
            throw RopePhysicsError.invalid("parallel opposite-endpoint response ties")
        }
        guard r.containsProjection(p(Double.nan,0,0))==nil,r.candidates(p(0.6,0,0),b)==nil else {
            throw RopePhysicsError.invalid("planar invalid domain")
        }
    }
    print("PASS planar region holes/crossing/parallel/corner/ties/unknown fixtures")
}
