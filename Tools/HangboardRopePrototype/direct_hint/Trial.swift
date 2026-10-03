// This tool only observes frozen correction inputs. It never applies a trial.
extension RopeDynamicsSolver {
    private struct HintPrepared {
        let system:RopeBandedSystem
        let columns:[[Double]],border:[[Double]]
        let rhs:[Double],borderRHS:[Double]
        let variables:[[SIMD3<Int>]],rowVariables:[Int:Int]
        let local:[Int],borderRows:[Int]
        let rows:[ConstraintRow]
    }
    private struct HintTrial {
        let prepared:HintPrepared
        let allRows:[ConstraintRow]
        let selectedIDs:[Int]
        let expectedParticles:[[SIMD3<Double>]]
        let expectedHeight:Double
        let originalSeconds:Double
        func run() throws -> [String:Any] {
            let p=prepared
            let began=ProcessInfo.processInfo.systemUptime
            let factor=try p.system.factorized(borderColumns:p.columns,borderMatrix:p.border)
            let solved=try factor.solve(rhs:p.rhs,borderRHS:p.borderRHS)
            let seconds=ProcessInfo.processInfo.systemUptime-began
            var lambda=Array(repeating:0.0,count:p.rows.count)
            for id in p.local {lambda[id]=solved.base[p.rowVariables[id]!]}
            for (offset,id) in p.borderRows.enumerated() {lambda[id]=solved.border[offset+1]}
            var particles=expectedParticles.map{Array(repeating:SIMD3<Double>.zero,count:$0.count)}
            var difference=abs(solved.border[0]-expectedHeight)
            for r in particles.indices {for i in particles[r].indices {
                let v=p.variables[r][i]
                if v.x>=0 {particles[r][i]=SIMD3(solved.base[v.x],solved.base[v.y],solved.base[v.z])}
                difference=max(difference,simd_distance(particles[r][i],expectedParticles[r][i]))
            }}
            var selected:[Int:Double]=[:]
            for (k,id) in selectedIDs.enumerated() {selected[id]=lambda[k]}
            var equation=0.0,inactiveViolation=0.0,allContactViolation=0.0,positiveMultiplier=0.0
            for id in allRows.indices {
                let row=allRows[id]
                var value=row.residual+row.boardGradient*solved.border[0]
                for k in row.particles.indices {value += simd_dot(row.gradients[k],particles[row.ropeIndex(k)][row.particles[k]])}
                guard value.isFinite else {throw RopePhysicsError.invalid("nonfinite direct trial equation")}
                if row.contact {allContactViolation=max(allContactViolation,-value)}
                if let multiplier=selected[id] {
                    equation=max(equation,abs(value-1e-8*multiplier))
                    if row.contact {positiveMultiplier=max(positiveMultiplier,multiplier)}
                } else {
                    guard row.contact else {throw RopePhysicsError.invalid("equality omitted by hint trial")}
                    inactiveViolation=max(inactiveViolation,-value)
                }
            }
            let originalResidual=p.system.hintResidual(base:solved.base,border:solved.border,
                rhs:p.rhs,columns:p.columns,borderMatrix:p.border,borderRHS:p.borderRHS)
            let accepted=originalResidual<=1e-10 && equation<=1e-8 && allContactViolation<=1e-8 && positiveMultiplier<=0 && difference<=1e-6
            return ["factorSolveSeconds":seconds,"originalContactSeconds":originalSeconds,
                "dimension":p.system.size,"bandwidth":p.system.bandwidth,"borderCount":p.columns.count,
                "selectedContacts":p.rows.filter{$0.contact}.count,"selectedLocalRows":p.local.count,
                "selectedNonlocalRows":p.borderRows.count,"allRows":allRows.count,
                "originalMatrixResidual":originalResidual,"regularizedEquationResidual":equation,
                "inactiveAffineViolation":inactiveViolation,"positiveContactMultiplier":positiveMultiplier,
                "allContactAffineViolation":allContactViolation,
                "maximumSchurDifferenceMeters":difference,"certificatePassed":accepted]
        }
    }
    private static var hintTrials:[HintTrial]=[]
    static func hintTrialReports() throws -> [[String:Any]] {
        var result:[[String:Any]]=[]
        for index in 0..<7 {
            let order=index%2==0 ? Array(hintTrials.indices):Array(hintTrials.indices.reversed())
            for id in order {
                var report=try hintTrials[id].run()
                report["run"]=index;report["correction"]=id
                result.append(report)
            }
        }
        return result
    }
}
enum HintTrialTrace {static var enabled=false}
