def collider_source(s):
    old='    func queryParity(_ point:SIMD3<Double>)->Bool {contains(point)}'
    assert s.count(old)==1
    return s.replace(old,"""    func queryParity(_ point:SIMD3<Double>)->Bool {
        let root=tree[0]
        if point.x<root.minimum.x || point.x>root.maximum.x || point.y<root.minimum.y || point.y>root.maximum.y || point.z<root.minimum.z || point.z>root.maximum.z {return false}
        return contains(point)
    }""")

def full_source(s):
    old='    private func contains(_ point: SIMD3<Double>) -> Bool {'
    assert s.count(old)==1
    return s.replace(old,old+"""
        let root=tree[0]
        if point.x<root.minimum.x || point.x>root.maximum.x || point.y<root.minimum.y || point.y>root.maximum.y || point.z<root.minimum.z || point.z>root.maximum.z {return false}""")
