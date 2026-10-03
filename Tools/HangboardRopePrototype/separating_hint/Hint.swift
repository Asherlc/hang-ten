import Foundation
import simd

// A hint never authorizes a skip without a fresh whole-segment projection test.
// This experimental support envelope is NOT a proof for every rounded output of
// triangleClosest. The driver checks every proposal against the original query.
struct RopeSeparationHint {
    let direction:SIMD3<Double>
    let triangleUpper:Double
    let normUpper:Double
    static func dotUpper(_ a:SIMD3<Double>,_ b:SIMD3<Double>)->Double {
        let x=(a.x*b.x).nextUp,y=(a.y*b.y).nextUp,z=(a.z*b.z).nextUp
        return ((x+y).nextUp+z).nextUp
    }
    static func dotLower(_ a:SIMD3<Double>,_ b:SIMD3<Double>)->Double {
        let x=(a.x*b.x).nextDown,y=(a.y*b.y).nextDown,z=(a.z*b.z).nextDown
        return ((x+y).nextDown+z).nextDown
    }
    static func interpolationError(_ a:SIMD3<Double>,_ d:SIMD3<Double>)->SIMD3<Double> {
        var error=SIMD3<Double>.zero
        for k in 0..<3 {
            let multiplication=abs(d[k]).ulp
            let extent=((abs(a[k])+abs(d[k])).nextUp+multiplication).nextUp
            error[k]=(multiplication+extent.ulp).nextUp
        }
        return error
    }
    static func edgeUpper(_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ n:SIMD3<Double>)->Double {
        let d=b-a
        let exactUpper=(dotUpper(a,n)+max(0,dotUpper(d,n))).nextUp
        return (exactUpper+dotUpper(simd_abs(n),interpolationError(a,d))).nextUp
    }
    init?(_ n:SIMD3<Double>,_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ c:SIMD3<Double>) {
        direction=n
#if SCREEN_EDGE_ONLY
        guard [a,b,c].allSatisfy({$0.x.isFinite && $0.y.isFinite && $0.z.isFinite && simd_reduce_max(simd_abs($0))<=0.5}) else{return nil}
        triangleUpper=max(Self.edgeUpper(a,b,n),max(Self.edgeUpper(b,c,n),Self.edgeUpper(c,a,n)))
#else
        triangleUpper=max(Self.dotUpper(a,n),max(Self.dotUpper(b,n),Self.dotUpper(c,n)))
#endif
        normUpper=sqrt(Self.dotUpper(n,n)).nextUp
        guard triangleUpper.isFinite,normUpper.isFinite,normUpper>0 else{return nil}
    }
    func separates(_ start:SIMD3<Double>,_ end:SIMD3<Double>,_ radius:Double)->Bool {
#if SCREEN_EDGE_ONLY
        guard start.x.isFinite,start.y.isFinite,start.z.isFinite,end.x.isFinite,end.y.isFinite,end.z.isFinite,
              simd_reduce_max(simd_abs(start))<=0.5,simd_reduce_max(simd_abs(end))<=0.5,
              radius>=0.001,radius<=0.01 else{return false}
        let d=end-start
        let linearLower=(Self.dotLower(start,direction)+min(0,Self.dotLower(d,direction))).nextDown
        let support=(linearLower-Self.dotUpper(simd_abs(direction),Self.interpolationError(start,d))).nextDown
#else
        // Original segmentPair interpolates start + (end-start)*s. Include its
        // rounded reconstructed endpoint, even if it lies outside the raw box.
        let reconstructed=start+(end-start)
        let support=min(Self.dotLower(start,direction),min(Self.dotLower(end,direction),Self.dotLower(reconstructed,direction)))
#endif
        let gap=(support-triangleUpper).nextDown
        let expansion=((radius+1e-9).nextUp*normUpper).nextUp
        return gap.isFinite && expansion.isFinite && gap>expansion
    }
}

struct RopeDirectionFaceResult {
    let first:RopeSegmentContact?,row:RopeSegmentContact?,merit:RopeSegmentContact?,last:RopeSegmentContact?
    let clearance:Double
    let direction:SIMD3<Double>?
    var empty:Bool {first==nil && row==nil && merit==nil && last==nil && clearance == .infinity}
    var bits:[UInt64] {
        var result=[clearance.bitPattern]
        for hit in [first,row,merit,last] {
            guard let hit else {result.append(0);continue}
            result.append(1)
            for p in [hit.centerlinePoint,hit.surfacePoint,hit.normal] {result += [p.x.bitPattern,p.y.bitPattern,p.z.bitPattern]}
            result += [hit.fraction.bitPattern,hit.penetrationDepth.bitPattern]
        }
        return result
    }
}
