"""Count feature agreement while retaining every original geometric candidate."""
from deferred_witness.snapshot import count_snapshot


def instrument(name,text):
    if name!='RopeTriangleCollider.swift':return text
    start=text.index('    private static func triangleClosest(')
    end=text.index('    static func segmentPair(',start)
    helper=text[start:end].replace('triangleClosest(', 'triangleClosestRegion(',1)
    helper=helper.replace('-> SIMD3<Double> {','-> (SIMD3<Double>,Int) {',1)
    replacements=[('return a }','return (a,0) }'),('return b }','return (b,1) }'),
      ('return c }','return (c,2) }'),
      ('return a+ab*(d1/(d1-d3)) }','return (a+ab*(d1/(d1-d3)),3) }'),
      ('return a+ac*(d2/(d2-d6)) }','return (a+ac*(d2/(d2-d6)),4) }'),
      ('return b+(c-b)*((d4-d3)/((d4-d3)+(d5-d6))) }','return (b+(c-b)*((d4-d3)/((d4-d3)+(d5-d6))),5) }'),
      ('return a+ab*(vb*inverse)+ac*(vc*inverse)','return (a+ab*(vb*inverse)+ac*(vc*inverse),6)')]
    for old,new in replacements:
        assert helper.count(old)==1,'original region arithmetic changed'
        helper=helper.replace(old,new)
    text=count_snapshot(name,text)
    start=text.index('    func fusedContactEvaluation(');end=text.index('    private struct FusedWitness',start)
    section=text[start:end]
    needle='            let normal=simd_normalize(simd_cross(b-a,c-a))'
    assert section.count(needle)==1
    section=section.replace(needle,needle+'\n            var startFeature = -1,endFeature = -1')
    for point,label in [('start','startFeature'),('end','endFeature')]:
        old='                let q=Self.triangleClosest('+point+',a,b,c)'
        assert section.count(old)==1
        section=section.replace(old,'                let classified=Self.triangleClosestRegion('+point+',a,b,c),q=classified.0\n                '+label+'=classified.1')
    needle='            if let counts {\n                counts[0]+='
    assert section.count(needle)==1
    section=section.replace(needle,'''            if let counts,start != end,mask & 6 != 0 {
                counts[7]+=1
                if startFeature>=0,startFeature==endFeature {
                    counts[8+startFeature]+=1
                    let omitted:[Int]
                    switch startFeature {
                    case 0:omitted=[4] // vertex A keeps AB and CA
                    case 1:omitted=[5] // vertex B keeps AB and BC
                    case 2:omitted=[3] // vertex C keeps BC and CA
                    case 3:omitted=[4,5] // edge AB
                    case 4:omitted=[3,4] // edge AC (original CA arithmetic retained)
                    case 5:omitted=[3,5] // edge BC
                    default:omitted=[3,4,5] // face
                    }
                    counts[15]+=omitted.count
                    if omitted.contains(row.winnerID) || omitted.contains(merit.winnerID) {counts[16]+=1}
                    else {counts[17]+=omitted.count}
                }
            }
'''+needle)
    text=text[:start]+section+text[end:]
    # Resize all worker-owned counter slots; the seven original witness slots stay.
    for old,new in [('jobs*7','jobs*18'),('counts+job*7','counts+job*18'),('count:7','count:18')]:text=text.replace(old,new)
    text=text.replace('DeferredWitnessCounts','FeatureRegionCounts')
    return text+'\nextension RopeTriangleCollider {\n'+helper+'}\n'
