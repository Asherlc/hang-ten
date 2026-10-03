extension RopeTriangleCollider {
    // Equal minima retain distinct fractions/normals; no near-tie tolerance is introduced.
    private static func planarHits(_ candidates:[(SIMD3<Double>,SIMD3<Double>,Double)],radius:Double,
        normal:SIMD3<Double>,point:Bool)->[RopeSegmentContact] {
        let square=radius*radius
        var best=square,selected:[(SIMD3<Double>,SIMD3<Double>,Double)]=[]
        for candidate in candidates {
            let distance=simd_length_squared(candidate.0-candidate.1)
            if distance<best {best=distance;selected=[candidate]}
            else if distance==best,distance<square {selected.append(candidate)}
        }
        guard !selected.isEmpty else{return []}
        let distance=sqrt(best)
        return selected.map {p,q,f in RopeSegmentContact(centerlinePoint:p,surfacePoint:q,
            normal:distance>1e-10 ? (p-q)/distance:normal,fraction:point ? 0:f,penetrationDepth:radius-distance)}
    }
}
