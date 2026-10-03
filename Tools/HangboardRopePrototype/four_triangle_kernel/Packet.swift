import simd

// Four independent Double kernels. Masks select original scalar branches.
private struct RopeFourVector {
    var x:SIMD4<Double>,y:SIMD4<Double>,z:SIMD4<Double>
    init(_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ c:SIMD3<Double>,_ d:SIMD3<Double>) {
        x=SIMD4(a.x,b.x,c.x,d.x);y=SIMD4(a.y,b.y,c.y,d.y);z=SIMD4(a.z,b.z,c.z,d.z)
    }
    init(_ p:SIMD3<Double>) {x=SIMD4(repeating:p.x);y=SIMD4(repeating:p.y);z=SIMD4(repeating:p.z)}
    init(x:SIMD4<Double>,y:SIMD4<Double>,z:SIMD4<Double>) {self.x=x;self.y=y;self.z=z}
    static func +(_ a:Self,_ b:Self)->Self {Self(x:a.x+b.x,y:a.y+b.y,z:a.z+b.z)}
    static func -(_ a:Self,_ b:Self)->Self {Self(x:a.x-b.x,y:a.y-b.y,z:a.z-b.z)}
    static prefix func -(_ a:Self)->Self {Self(x:-a.x,y:-a.y,z:-a.z)}
    static func *(_ a:Self,_ b:SIMD4<Double>)->Self {Self(x:a.x*b,y:a.y*b,z:a.z*b)}
    func lane(_ i:Int)->SIMD3<Double> {SIMD3(x[i],y[i],z[i])}
    static func dot(_ a:Self,_ b:Self)->SIMD4<Double> {a.x*b.x+a.y*b.y+a.z*b.z}
    static func cross(_ a:Self,_ b:Self)->Self {Self(x:a.y*b.z-a.z*b.y,y:a.z*b.x-a.x*b.z,z:a.x*b.y-a.y*b.x)}
    func selected(_ other:Self,_ mask:SIMDMask<SIMD4<Int64>>)->Self {
        var p=self;p.x.replace(with:other.x,where:mask);p.y.replace(with:other.y,where:mask);p.z.replace(with:other.z,where:mask);return p
    }
}
private struct RopeFourTriangleKernel {
    let a:RopeFourVector,b:RopeFourVector,c:RopeFourVector
    private func choose(_ x:SIMD4<Double>,_ y:SIMD4<Double>,_ mask:SIMDMask<SIMD4<Int64>>)->SIMD4<Double> {
        var result=x;result.replace(with:y,where:mask);return result
    }
    private func clamp(_ x:SIMD4<Double>)->SIMD4<Double> {simd_min(SIMD4(repeating:1),simd_max(SIMD4(repeating:0),x))}
    func closest(_ point:SIMD3<Double>)->RopeFourVector {
        let p=RopeFourVector(point),ab=b-a,ac=c-a,ap=p-a
        let d1=RopeFourVector.dot(ab,ap),d2=RopeFourVector.dot(ac,ap)
        let bp=p-b,d3=RopeFourVector.dot(ab,bp),d4=RopeFourVector.dot(ac,bp)
        let vc=d1*d4-d3*d2
        let cp=p-c,d5=RopeFourVector.dot(ab,cp),d6=RopeFourVector.dot(ac,cp)
        let vb=d5*d2-d1*d6,va=d3*d6-d5*d4
        let inverse=SIMD4<Double>(repeating:1)/(va+vb+vc)
        var result=a+ab*(vb*inverse)+ac*(vc*inverse)
        result=result.selected(b+(c-b)*((d4-d3)/((d4-d3)+(d5-d6))),(va .<= 0) .& (d4-d3 .>= 0) .& (d5-d6 .>= 0))
        result=result.selected(a+ac*(d2/(d2-d6)),(vb .<= 0) .& (d2 .>= 0) .& (d6 .<= 0))
        result=result.selected(c,(d6 .>= 0) .& (d5 .<= d6))
        result=result.selected(a+ab*(d1/(d1-d3)),(vc .<= 0) .& (d1 .>= 0) .& (d3 .<= 0))
        result=result.selected(b,(d3 .>= 0) .& (d4 .<= d3))
        return result.selected(a,(d1 .<= 0) .& (d2 .<= 0))
    }
    func ray(_ start:SIMD3<Double>,_ direction:SIMD3<Double>)->(SIMD4<Double>,SIMDMask<SIMD4<Int64>>) {
        let e1=b-a,e2=c-a,cross=RopeFourVector.cross(RopeFourVector(direction),e2)
        let determinant=RopeFourVector.dot(e1,cross),inverse=SIMD4<Double>(repeating:1)/determinant,s=RopeFourVector(start)-a
        let u=RopeFourVector.dot(s,cross)*inverse,q=RopeFourVector.cross(s,e1),v=RopeFourVector.dot(RopeFourVector(direction),q)*inverse
        let valid=(abs(determinant) .> 1e-15) .& (u .>= -1e-12) .& (u .<= 1+1e-12) .& (v .>= -1e-12) .& (u+v .<= 1+1e-12)
        return (RopeFourVector.dot(e2,q)*inverse,valid)
    }
    func pair(_ start:SIMD3<Double>,_ end:SIMD3<Double>,_ edgeA:RopeFourVector,_ edgeB:RopeFourVector)
        -> (RopeFourVector,RopeFourVector,SIMD4<Double>) {
        let delta=end-start,d1=RopeFourVector(delta),d2=edgeB-edgeA,r=RopeFourVector(start)-edgeA
        let aa=simd_dot(delta,delta),ee=RopeFourVector.dot(d2,d2),f=RopeFourVector.dot(d2,r)
        var s=SIMD4<Double>(repeating:0),t=s
        if aa<=1e-24 {t=clamp(f/ee)} else {
            let cc=RopeFourVector.dot(d1,r),bb=RopeFourVector.dot(d1,d2),denominator=aa*ee-bb*bb
            s=choose(s,clamp((bb*f-cc*ee)/denominator),denominator .> 1e-24)
            t=(bb*s+f)/ee
            let below=t .< 0,above=t .> 1
            s=choose(s,clamp(-cc/aa),below);s=choose(s,clamp((bb-cc)/aa),above)
            t=choose(t,SIMD4(repeating:0),below);t=choose(t,SIMD4(repeating:1),above)
            s=choose(s,clamp(-cc/aa),ee .<= 1e-24);t=choose(t,SIMD4(repeating:0),ee .<= 1e-24)
        }
        return (RopeFourVector(start)+d1*s,edgeA+d2*t,s)
    }
}
