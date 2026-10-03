private struct TriangleKernel:Sendable {
    let a:SIMD3<Double>,b:SIMD3<Double>,c:SIMD3<Double>
    let ab:SIMD3<Double>,ac:SIMD3<Double>,normal:SIMD3<Double>
    let parityCross:SIMD3<Double>,parityInverse:Double?
    static let direction=simd_normalize(SIMD3<Double>(1,0.3713906763541037,0.5291502622129182))
    init(a:SIMD3<Double>,b:SIMD3<Double>,c:SIMD3<Double>) {
        self.a=a;self.b=b;self.c=c
        ab=b-a;ac=c-a;normal=simd_normalize(simd_cross(b-a,c-a))
        parityCross=simd_cross(Self.direction,c-a)
        let determinant=simd_dot(b-a,parityCross)
        parityInverse=abs(determinant)>1e-15 ? 1/determinant:nil
    }
    func parityRay(_ p:SIMD3<Double>)->Double? {
        guard let inverse=parityInverse else{return nil}
        let s=p-a,u=simd_dot(s,parityCross)*inverse
        guard u>=(-1e-12),u<=1+1e-12 else{return nil}
        let q=simd_cross(s,ab),v=simd_dot(Self.direction,q)*inverse
        guard v>=(-1e-12),u+v<=1+1e-12 else{return nil}
        return simd_dot(ac,q)*inverse
    }
}
