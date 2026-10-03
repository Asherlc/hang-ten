def once(source,old,new):
    assert source.count(old)==1,old
    return source.replace(old,new)
def solver_source(source):
    source=once(source,'    private var lastStepDuration=1.0/240','    private var lastStepDuration=1.0/240\n    private var contactHints:[(RopeLinearContact,Double)]=[]')
    source=once(source,'    private func contactCorrection(rows:','    private mutating func contactCorrection(rows:')
    source=once(source,'        let solved:RopeContactSystem.Solution',"""        var buckets:[[Int]:[Int]]=[:]
        for id in contacts.indices {buckets[contacts[id].indices,default:[]].append(id)}
        var initial:[Int:Double]=[:]
        for (old,multiplier) in contactHints where multiplier<0 {
            var chosen:Int?,best=Double.infinity
            for id in buckets[old.indices] ?? [] {
                let row=contacts[id]
                guard row.coefficients.count==old.coefficients.count,row.border.count==old.border.count else {continue}
                var error=0.0
                for k in row.coefficients.indices {let d=row.coefficients[k]-old.coefficients[k];error += d*d}
                for k in row.border.indices {let d=row.border[k]-old.border[k];error += d*d}
                if error<best {best=error;chosen=id}
            }
            if let chosen {initial[chosen,default:0] += multiplier}
        }
        let fallbackSolver=self
        let solved:RopeContactSystem.Solution""")
    source=once(source,'                contacts:contacts,maxIterations:', '                contacts:contacts,initialMultipliers:initial,maxIterations:')
    source=source.replace('        var particles=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}',
      '        contactHints=solved.activeIDs.map{(contacts[$0],solved.multipliers[$0])}\n        var particles=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}',1)
    source=once(source,'let direct=try fullContactCorrection(rows:rows,weights:weights,prediction:prediction)','let direct=try fallbackSolver.fullContactCorrection(rows:rows,weights:weights,prediction:prediction)')
    return source
