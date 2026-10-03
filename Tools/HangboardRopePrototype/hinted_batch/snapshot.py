from pathlib import Path
def band_source(s):return s+"\n"+Path(__file__).with_name("Batch.swift").read_text()
def contact_source(s):
    marker='        func response(_ id: Int) throws -> [Double] {'
    assert s.count(marker)==1
    pre="""        let initialIDs=initialMultipliers.keys.sorted()
        guard initialIDs.count*dimension<=8_000_000 else {throw RopePhysicsError.invalid("Excessive rope contact response storage")}
        let batchCount=min(64,max(1,500_000/dimension))
        for start in stride(from:0,to:initialIDs.count,by:batchCount) {
            let ids=Array(initialIDs[start..<min(initialIDs.count,start+batchCount)])
            var rhs=Array(repeating:0.0,count:size*ids.count),borderRHS:[Double]=[]
            for (j,id) in ids.enumerated() {
                let row=contacts[id]
                for k in row.indices.indices {rhs[j*size+row.indices[k]] += row.coefficients[k]}
                borderRHS += row.border
            }
            let result=try factor.solveBatch(rhs:rhs,borderRHS:borderRHS,count:ids.count)
            let nb=border.count
            for (j,id) in ids.enumerated() {
                responses[id]=Array(result.base[j*size..<(j+1)*size])+Array(result.border[j*nb..<(j+1)*nb])
            }
        }
"""
    return s.replace(marker,pre+marker)
