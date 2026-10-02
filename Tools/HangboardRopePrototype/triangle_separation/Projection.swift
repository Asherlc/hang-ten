// Immutable preflight only. A direction need not be exact: supports use all vertices.
private struct RopeTriangleProjection: Sendable {
    let direction:SIMD3<Double>
    let lower:Double
    let upper:Double
    let normUpper:Double
    private static let gamma5=(5*Double.ulpOfOne/2)/(1-5*Double.ulpOfOne/2)
    static func interval(_ point:SIMD3<Double>,_ n:SIMD3<Double>)->(Double,Double) {
        let x=point.x*n.x,y=point.y*n.y,z=point.z*n.z
        let value=(x+y)+z
        let sum=(abs(x).nextUp+abs(y).nextUp).nextUp+abs(z).nextUp
        let error=(gamma5*sum.nextUp).nextUp+Double.leastNormalMagnitude*8
        return ((value-error).nextDown,(value+error).nextUp)
    }
    init(_ direction:SIMD3<Double>,_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ c:SIMD3<Double>) {
        self.direction=direction
        let x=Self.interval(a,direction),y=Self.interval(b,direction),z=Self.interval(c,direction)
        lower=min(x.0,min(y.0,z.0));upper=max(x.1,max(y.1,z.1))
        let norm=Self.interval(direction,direction)
        normUpper=sqrt(max(0,norm.1)).nextUp
    }
    func separates(_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ radius:Double)->Bool {
        let x=Self.interval(a,direction),y=a == b ? x:Self.interval(b,direction)
        let lo=min(x.0,y.0),hi=max(x.1,y.1)
        let reach=(radius*normUpper).nextUp
        return (lo-upper).nextDown>reach || (lower-hi).nextDown>reach
    }
}
