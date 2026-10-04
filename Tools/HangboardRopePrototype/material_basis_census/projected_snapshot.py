"""Oracle-active-set projected KKT discriminator; copied sources only."""
from pathlib import Path
from armijo.snapshot import once

def band_source(source):
    return source+"""
extension RopeBandedSystem {
    func projectedEntries()->[(Int,Int,Double)] {
        var result:[(Int,Int,Double)]=[]
        for j in 0..<size {for i in j...min(size-1,j+bandwidth) {
            let v=matrix[2*bandwidth+i-j+j*leadingDimension]
            if v != 0 {result.append((i,j,v))}
        }}
        return result
    }
}
"""

def solver_source(source):
    source=once(source,'        let selected=solved.ids.map{rows[$0]},lambda=solved.multipliers',"""        if ProjectedKKT.enabled {
            ProjectedKKT.protected=state.ropes.enumerated().map{r,rope in
                var p=Set(rope.supports.keys).union(rope.attachments.keys)
                for crossing in rope.portalCrossings.values {p.insert(crossing.segment);p.insert(crossing.segment+1)}
                for row in rows where row.contact {for j in row.particles.indices where row.ropeIndex(j)==r {p.insert(row.particles[j])}}
                return p
            }
            ProjectedKKT.capture=true
            do {_ = try constraintBackbone(rows:solved.ids.map{rows[$0]},weights:weights,prediction:prediction)}
            catch ProjectedCapture.done {}
            ProjectedKKT.capture=false
            guard var captured=ProjectedKKT.pending else {throw RopePhysicsError.invalid("projected capture missing")}
            captured.allRows=rows.enumerated().map{id,row in
                var terms:[(Int,Double)]=[(captured.size,row.boardGradient)]
                for j in row.particles.indices {for axis in 0..<3 {
                    let v=captured.variables[row.ropeIndex(j)][row.particles[j]][axis]
                    if v>=0 {terms.append((v,row.gradients[j][axis]))}
                }}
                return ProjectedRow(terms:terms,residual:row.residual,contact:row.contact,active:solved.ids.contains(id))
            }
            captured.reference=Array(repeating:0,count:captured.size+captured.columns.count)
            captured.reference[captured.size]=solved.height
            for r in weights.indices {for i in weights[r].indices where weights[r][i]>0 {for axis in 0..<3 {
                captured.reference[captured.variables[r][i][axis]]=solved.particles[r][i][axis]
            }}}
            for i in solved.ids.indices {
                let variable=captured.rowVariables[i] ?? (captured.size+1+captured.borderRows.firstIndex(of:i)!)
                captured.reference[variable]=solved.multipliers[i]
            }
            ProjectedKKT.inputs.append(captured);ProjectedKKT.pending=nil
        }
        let selected=solved.ids.map{rows[$0]},lambda=solved.multipliers""")
    source=once(source,'        let factor=try system.factorized(borderColumns:columns,borderMatrix:border)',"""        if ProjectedKKT.capture {
            ProjectedKKT.pending=ProjectedInput(size:size,bandwidth:bandwidth,entries:system.projectedEntries(),columns:columns,border:border,rhs:rhs,borderRHS:borderRHS,
                variables:variables,ropes:state.ropes,protected:ProjectedKKT.protected,
                selectedRows:rows.map{($0.contact,$0.residual)},rowVariables:rowVariables,borderRows:borderRows)
            throw ProjectedCapture.done
        }
        let factor=try system.factorized(borderColumns:columns,borderMatrix:border)""")
    return source

def driver_source(source):
    return source[:source.index('do {\n    var checkpoints:')]+Path(__file__).with_name('ProjectedMain.swift.txt').read_text()
