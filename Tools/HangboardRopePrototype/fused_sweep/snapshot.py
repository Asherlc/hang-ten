def once(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)
def collider_source(s):
    start=s.index('    func segmentContact(from start:')
    end=s.index('    /// Retains independent nearby surface witnesses.',start)
    s=s[:start]+"""    func segmentContact(from start: SIMD3<Double>, to end: SIMD3<Double>, radius: Double) -> RopeSegmentContact? {
        segmentContactEvaluation(from:start,to:end,radius:radius).contact
    }
    private func segmentContactEvaluation(from start:SIMD3<Double>,to end:SIMD3<Double>,radius:Double)
        -> (contact:RopeSegmentContact?,nearest:(distance:Double,contact:RopeSegmentContact)) {
        let closest=closestSegment(start,end),contact=closest.contact
        var insideContact:RopeSegmentContact?
        for (p,fraction) in [(start,0.0),(end,1.0)] where contains(p) {
            let surface=closestSurface(at:p)
            let penetration=radius+surface.distance
            if penetration > (insideContact?.penetrationDepth ?? -Double.infinity) {
                let delta=surface.point-p
                let normal=surface.distance > 1e-10 ? delta/surface.distance : surface.normal
                insideContact=RopeSegmentContact(centerlinePoint:p,surfacePoint:surface.point,normal:normal,fraction:fraction,penetrationDepth:penetration)
            }
        }
        if let insideContact {return (insideContact,closest)}
        guard closest.distance < radius else {return (nil,closest)}
        return (RopeSegmentContact(centerlinePoint:contact.centerlinePoint,surfacePoint:contact.surfacePoint,normal:contact.normal,
                                  fraction:contact.fraction,penetrationDepth:radius-closest.distance),closest)
    }

"""+s[end:]
    s=once(s,'            if var hit=segmentContact(from:a,to:b,radius:radius) { hit.timeOfImpact=time; return hit }\n            let nearest=closestSegment(a,b), gap=nearest.distance-radius',
      '            let evaluated=segmentContactEvaluation(from:a,to:b,radius:radius)\n            if var hit=evaluated.contact {hit.timeOfImpact=time;return hit}\n            let nearest=evaluated.nearest,gap=nearest.distance-radius')
    return s
