"""Prune only original edge witnesses whose computed boxes cannot improve best."""
from pathlib import Path


def collider_source(text):
    start=text.index('    func fusedContactEvaluation(');end=text.index('    private struct FusedWitness',start)
    section=text[start:end]
    needle='        let rowSquare=rowRadius*rowRadius,meritSquare=meritRadius*meritRadius'
    assert section.count(needle)==1
    section=section.replace(needle,needle+'\n        let pairBox=Self.fpPairBox(start,end)')
    old="                let ab=Self.segmentPair(start,end,a,b),bc=Self.segmentPair(start,end,b,c),ca=Self.segmentPair(start,end,c,a)\n                for q in [ab,bc,ca] {if mask & 2 != 0 {row.consider(q.0,q.1,q.2)};if mask & 4 != 0 {merit.consider(q.0,q.1,q.2)}}"
    assert section.count(old)==1
    new=[]
    for a,b in [('a','b'),('b','c'),('c','a')]:
        new.append("""                do {
                    let required=max(mask & 2 != 0 ? row.best:0,mask & 4 != 0 ? merit.best:0)
                    let bound=pairBox.flatMap{Self.fpEdgeSquaredBound(low:$0.0,high:$0.1,a:"""+a+",b:"+b+""" )}
                    if bound == nil || bound!<required {
                        let q=Self.segmentPair(start,end,"""+a+","+b+""" )
                        if mask & 2 != 0 {row.consider(q.0,q.1,q.2)};if mask & 4 != 0 {merit.consider(q.0,q.1,q.2)}
                    }
                }""")
    section=section.replace(old,'\n'.join(new))
    return text[:start]+section+text[end:]+'\n'+(Path(__file__).parent/'Bounds.swift').read_text()
