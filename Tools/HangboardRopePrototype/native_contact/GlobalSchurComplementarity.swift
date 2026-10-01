import Foundation
import Accelerate

/// Experimental simultaneous contact solve. Chain, equality and height
/// responses all come from the original globally coupled frozen matrix.
/// Positive-force/slack interior point is the successor; the retained FB path
/// is selected explicitly for reproducing its closed hard-input rejection.
final class GlobalSchurSession {
    private struct Key: Hashable {
        let indices: [Int], coefficients: [Double], border: [Double]
    }
    private struct Response {
        let base: [Double], border: [Double]
    }
    private let factor: PrimalPrepared
    private let batchResponses: Bool
    private var responses: [Key: Response] = [:]
    private var cachedJacobianEntries = 0
    private(set) var lastStatistics: [String: Double] = [:]
    var cachedResponseCount: Int { responses.count }
    init(factor: PrimalPrepared) {
        self.factor = factor
        batchResponses = ProcessInfo.processInfo.environment["HANGTEN_BATCH_CONTACT_RESPONSES"] == "1"
    }

    func solve(base: [Double], border: [Double], contacts: [RopeLinearContact],
               initialMultipliers: [Int: Double] = [:], maxIterations: Int = 50) throws -> RopeContactSystem.Solution {
        let n = factor.baseCount, nb = factor.borderCount, m = contacts.count, epsilon = 1e-8
        let equalities = Set(factor.equalities)
        guard n > 0, base.count == n, border.count == nb, n+nb+m <= 50_256, m <= 100_000,
              m == 0 || m <= 8_000_000/m, (1...50).contains(maxIterations),
              (base+border).allSatisfy({ $0.isFinite }),
              initialMultipliers.allSatisfy({ contacts.indices.contains($0.key) && $0.value.isFinite && $0.value <= 0 }),
              contacts.allSatisfy({ row in
                  row.indices.count == row.coefficients.count && row.border.count == nb && row.residual.isFinite &&
                  row.indices.allSatisfy({ (0..<n).contains($0) && !equalities.contains($0) }) &&
                  (row.coefficients+row.border).allSatisfy({ $0.isFinite })
              }) else { throw RopePhysicsError.invalid("Invalid global Schur input or array budget") }
        let nonlocal = contacts.filter { ($0.indices.max() ?? 0)-($0.indices.min() ?? 0) > factor.system.bandwidth }.count
        guard nonlocal+nb <= 256 else { throw RopePhysicsError.invalid("Global Schur nonlocal budget") }
        var entries = 0
        for row in contacts {
            let count = row.indices.count+row.coefficients.count+row.border.count
            guard count <= 8_000_000-entries else { throw RopePhysicsError.invalid("Global Schur working array budget") }
            entries += count
        }
        func dot(_ row: RopeLinearContact, _ x: [Double], _ b: [Double]) -> Double {
            var value = 0.0
            for k in row.indices.indices { value += row.coefficients[k]*x[row.indices[k]] }
            for k in 0..<nb { value += row.border[k]*b[k] }
            return value
        }
        func norm(_ v: [Double]) -> Double { v.map { abs($0) }.max() ?? 0 }
        let started = ProcessInfo.processInfo.systemUptime
        let before = responses.count
        var responseBatches = 0
        if batchResponses {
            var missing: [(Key, RopeLinearContact)] = [], seen = Set<Key>()
            var pendingEntries = 0
            for row in contacts {
                let key = Key(indices: row.indices, coefficients: row.coefficients, border: row.border)
                if responses[key] != nil || !seen.insert(key).inserted { continue }
                let keyEntries = row.indices.count+row.coefficients.count+row.border.count
                guard responses.count+missing.count+1 <= 8_000_000/(n+nb),
                      keyEntries <= 8_000_000-cachedJacobianEntries-pendingEntries else {
                    throw RopePhysicsError.invalid("Global Schur response array budget")
                }
                pendingEntries += keyEntries
                missing.append((key,row))
            }
            let width = min(64,500_000/(n+nb))
            for start in stride(from: 0, to: missing.count, by: width) {
                let chunk = missing[start..<min(start+width,missing.count)]
                let loads = chunk.map { pair -> [Double] in
                    var load = Array(repeating: 0.0, count: n)
                    for k in pair.1.indices.indices { load[pair.1.indices[k]] += pair.1.coefficients[k] }
                    return load
                }
                let solved = try factor.refinedBatch(loads,chunk.map { $0.1.border })
                responseBatches += 1
                for (pair,value) in zip(chunk,solved) {
                    responses[pair.0] = Response(base: value.base, border: value.border)
                    cachedJacobianEntries += pair.0.indices.count+pair.0.coefficients.count+pair.0.border.count
                }
            }
        }
        let response = try contacts.map { row -> Response in
            let key = Key(indices: row.indices, coefficients: row.coefficients, border: row.border)
            if let cached = responses[key] { return cached }
            let keyEntries = row.indices.count+row.coefficients.count+row.border.count
            guard responses.count+1 <= 8_000_000/(n+nb), keyEntries <= 8_000_000-cachedJacobianEntries else {
                throw RopePhysicsError.invalid("Global Schur response array budget")
            }
            var load = Array(repeating: 0.0, count: n)
            for k in row.indices.indices { load[row.indices[k]] += row.coefficients[k] }
            let solved = try factor.refined(load, row.border)
            let value = Response(base: solved.base, border: solved.border)
            responses[key] = value
            cachedJacobianEntries += keyEntries
            return value
        }
        let responseSeconds = ProcessInfo.processInfo.systemUptime-started
        // Exact global compliance, including both ropes, length equalities,
        // nonlocal contacts and board height. There is no per-loop solve.
        var schur = Array(repeating: 0.0, count: m*m)
        for j in 0..<m { for i in 0..<m { schur[i+j*m] = dot(contacts[i], response[j].base, response[j].border) } }
        guard schur.allSatisfy({ $0.isFinite }) else { throw RopePhysicsError.invalid("Nonfinite global compliance") }
        let constructionSeconds = ProcessInfo.processInfo.systemUptime-started
        var h = Array(repeating: 0.0, count: n)
        for (r,c,v) in factor.system.lowerEntries() where r == c { h[r] = v }
        let scales = try contacts.map { row -> Double in
            var compliance = 0.0
            for k in row.indices.indices {
                guard h[row.indices[k]] > 0 else { throw RopePhysicsError.invalid("Global Schur local scale") }
                compliance += row.coefficients[k]*row.coefficients[k]/h[row.indices[k]]
            }
            for k in 0..<nb where row.border[k] != 0 {
                guard factor.borderMatrix[k][k] > 0 else { throw RopePhysicsError.invalid("Global Schur height scale") }
                compliance += row.border[k]*row.border[k]/factor.borderMatrix[k][k]
            }
            return compliance > 0 ? 1/compliance : 1
        }
        guard scales.allSatisfy({ $0.isFinite && $0 > 0 }) else { throw RopePhysicsError.invalid("Nonfinite global Schur scales") }
        let initial = contacts.map { $0.residual+dot($0,base,border) }
        let load = factor.product(base,border)
        struct Evaluation {
            let q: [Double], gap: [Double], phi: [Double], a: [Double], b: [Double]
            let merit: Double, accepted: Bool
        }
        func evaluate(_ mu: [Double]) throws -> Evaluation {
            var q = initial
            for j in 0..<m where mu[j] != 0 { for i in 0..<m { q[i] -= schur[i+j*m]*mu[j] } }
            let gap = (0..<m).map { q[$0]-epsilon*mu[$0] }
            var phi: [Double] = [], a: [Double] = [], b: [Double] = []
            for i in 0..<m {
                let l = -mu[i]/scales[i], g = gap[i], r = hypot(l,g)
                phi.append((r-max(l,g))-min(l,g))
                a.append(r == 0 ? -1 : (l > 0 ? -g*g/(r*(r+l)) : l/r-1))
                b.append(r == 0 ? -1 : (g > 0 ? -l*l/(r*(r+g)) : g/r-1))
            }
            let merit = phi.reduce(0) { $0+$1*$1 }
            guard merit.isFinite, (q+gap+phi+a+b+mu).allSatisfy({ $0.isFinite }) else {
                throw RopePhysicsError.invalid("Nonfinite global Schur root evaluation")
            }
            let accepted = (q.min() ?? 0) >= -1e-8 && (gap.min() ?? 0) >= -1e-10 &&
                norm((0..<m).map { mu[$0]*gap[$0] }) <= 1e-14 && (mu.max() ?? 0) <= 1e-12
            return Evaluation(q: q, gap: gap, phi: phi, a: a, b: b, merit: merit, accepted: accepted)
        }
        var factorizations = 0, factorSeconds = 0.0, lineTrials = 0
        func direction(_ current: Evaluation, _ mu: [Double]) throws -> [Double] {
            let active = (0..<m).filter { current.b[$0] != 0 }, count = active.count
            let inactive = (0..<m).filter { current.b[$0] == 0 }
            var result = Array(repeating: 0.0, count: m)
            for id in inactive { result[id] = -mu[id] }
            if count == 0 { return result }
            var matrix = Array(repeating: 0.0, count: count*count), rhs = Array(repeating: 0.0, count: count)
            var scale = rhs
            for (i,id) in active.enumerated() {
                let diagonal = schur[id+id*m]+epsilon+current.a[id]/(scales[id]*current.b[id])
                guard diagonal.isFinite, diagonal > 0 else { throw RopePhysicsError.invalid("Invalid global Schur Newton diagonal") }
                scale[i] = 1/sqrt(diagonal)
                rhs[i] = current.phi[id]/current.b[id]
                for other in inactive { rhs[i] -= schur[id+other*m]*result[other] }
            }
            for (j,jid) in active.enumerated() { for (i,iid) in active.enumerated() {
                var value = schur[iid+jid*m]
                if i == j { value += epsilon+current.a[iid]/(scales[iid]*current.b[iid]) }
                matrix[i+j*count] = value*scale[i]*scale[j]
            } }
            guard (matrix+rhs+scale).allSatisfy({ $0.isFinite }) else { throw RopePhysicsError.invalid("Nonfinite condensed Newton matrix") }
            var numeric = matrix, dimension = __LAPACK_int(count), leading = dimension, info: __LAPACK_int = 0
            var triangle: Int8 = 76
            let start = ProcessInfo.processInfo.systemUptime
            dpotrf_(&triangle,&dimension,&numeric,&leading,&info)
            factorizations += 1; factorSeconds += ProcessInfo.processInfo.systemUptime-start
            guard info == 0 else { throw RopePhysicsError.invalid("Global Schur Newton factorization (\(info))") }
            func linear(_ load: [Double]) throws -> [Double] {
                var answer = zip(load,scale).map(*)
                var one: __LAPACK_int = 1
                dpotrs_(&triangle,&dimension,&one,&numeric,&leading,&answer,&leading,&info)
                guard info == 0 else { throw RopePhysicsError.invalid("Global Schur Newton solve (\(info))") }
                return zip(answer,scale).map(*)
            }
            var answer = try linear(rhs)
            for _ in 0..<3 {
                var error = rhs
                for (j,jid) in active.enumerated() { for (i,iid) in active.enumerated() {
                    var value = schur[iid+jid*m]
                    if i == j { value += epsilon+current.a[iid]/(scales[iid]*current.b[iid]) }
                    error[i] -= value*answer[j]
                } }
                if norm(error) <= 1e-12*max(1,norm(rhs)) { break }
                answer = zip(answer,try linear(error)).map(+)
            }
            guard answer.allSatisfy({ $0.isFinite }) else { throw RopePhysicsError.invalid("Nonfinite global Schur direction") }
            for (i,id) in active.enumerated() { result[id] = answer[i] }
            return result
        }
        func recover(_ mu: [Double]) throws -> RopeContactSystem.Solution {
            var rhs = load.base, borderRHS = load.border
            for i in 0..<m {
                for k in contacts[i].indices.indices { rhs[contacts[i].indices[k]] -= contacts[i].coefficients[k]*mu[i] }
                for k in 0..<nb { borderRHS[k] -= contacts[i].border[k]*mu[i] }
            }
            let solved = try factor.refined(rhs,borderRHS)
            var product = factor.product(solved.base,solved.border)
            for i in 0..<m {
                for k in contacts[i].indices.indices { product.base[contacts[i].indices[k]] += contacts[i].coefficients[k]*mu[i] }
                for k in 0..<nb { product.border[k] += contacts[i].border[k]*mu[i] }
            }
            let error = zip(product.base+product.border,load.base+load.border).map(-)
            let physicalEquality = norm(factor.equalities.map { error[$0]+epsilon*solved.base[$0] })
            // The condensed system is only a numerical accelerator. Final
            // certificates retain the original ordered row arithmetic, including
            // C-epsilon*mu before sparse additions. Positive gap matters too:
            // a feasibility-only source scan cannot certify complementarity.
            func ordered(_ row: RopeLinearContact, _ start: Double) -> Double {
                var value = start
                for k in row.indices.indices { value += row.coefficients[k]*solved.base[row.indices[k]] }
                for k in 0..<nb { value += row.border[k]*solved.border[k] }
                return value
            }
            let q = contacts.map { ordered($0,$0.residual) }
            let gap = (0..<m).map { ordered(contacts[$0],contacts[$0].residual-epsilon*mu[$0]) }
            guard norm(error) <= 1e-10, physicalEquality <= 1e-8, (q.min() ?? 0) >= -1e-8,
                  (gap.min() ?? 0) >= -1e-10, norm((0..<m).map { mu[$0]*gap[$0] }) <= 1e-14,
                  (mu.max() ?? 0) <= 1e-12, (solved.base+solved.border+gap).allSatisfy({ $0.isFinite }) else {
                throw RopePhysicsError.invalid("Global Schur original-matrix certificate: stationarity \(norm(error)), physical \(q.min() ?? 0), complementarity \(norm((0..<m).map { mu[$0]*gap[$0] }))")
            }
            lastStatistics = ["workingRows": Double(m), "newResponses": Double(responses.count-before),
                "cachedResponses": Double(responses.count), "responseAndComplianceSeconds": constructionSeconds,
                "responseSolveSeconds": responseSeconds,
                "complianceAssemblySeconds": constructionSeconds-responseSeconds,
                "batchedResponses": batchResponses ? Double(responses.count-before) : 0,
                "responseBatches": Double(responseBatches),
                "newtonFactorizations": Double(factorizations), "newtonFactorSeconds": factorSeconds,
                "lineSearchTrials": Double(lineTrials)]
            if let profile=factor.responseProfile {
                lastStatistics.merge(profile.seconds,uniquingKeysWith:{_,new in new})
            }
            return RopeContactSystem.Solution(base: solved.base, border: solved.border, multipliers: mu,
                activeIDs: (0..<m).filter { mu[$0] < -1e-12 })
        }
        if ProcessInfo.processInfo.environment["HANGTEN_SCHUR_METHOD"] != "fischer-burmeister" {
            func fraction(_ values: [Double], _ changes: [Double], _ safety: Double = 1) -> Double {
                var alpha = 1.0
                for i in values.indices where changes[i] < 0 { alpha = min(alpha,-safety*values[i]/changes[i]) }
                return alpha
            }
            var force = Array(repeating: 0.001, count: m)
            var slack = try evaluate(force.map { -$0 }).gap.map { max(1e-5,$0) }
            for iteration in 0...maxIterations {
                let current = try evaluate(force.map { -$0 })
                let rp = zip(slack,current.gap).map(-)
                // A feasible barrier iterate can still move micrometres under
                // tiny inactive forces. Converge beyond the acceptance floor
                // before original-matrix/oracle certification; no gate is loosened.
                let barrierResidual = norm((0..<m).map { force[$0]*current.gap[$0] })
                if current.accepted && barrierResidual <= 1e-18 && norm(rp) <= 1e-10 && (slack.min() ?? 0) >= 0 && (force.min() ?? 0) >= 0 {
                    return try recover(force.map { -$0 })
                }
                guard iteration < maxIterations, m > 0 else {
                    throw RopePhysicsError.invalid("Condensed interior-point iteration bound: gap \(current.gap.min() ?? 0), contact \(norm(rp)), complementarity \(norm((0..<m).map { force[$0]*current.gap[$0] }))")
                }
                let diagonal = (0..<m).map { epsilon+slack[$0]/force[$0] }
                guard diagonal.allSatisfy({ $0.isFinite && $0 > 0 }) else { throw RopePhysicsError.invalid("Invalid condensed interior-point weights") }
                let scale = (0..<m).map { 1/sqrt(schur[$0+$0*m]+diagonal[$0]) }
                var matrix = schur
                for j in 0..<m { for i in 0..<m {
                    if i == j { matrix[i+j*m] += diagonal[i] }
                    matrix[i+j*m] *= scale[i]*scale[j]
                } }
                guard (matrix+scale).allSatisfy({ $0.isFinite }) else { throw RopePhysicsError.invalid("Nonfinite condensed interior-point matrix") }
                var numeric = matrix, dimension = __LAPACK_int(m), leading = dimension, info: __LAPACK_int = 0
                var triangle: Int8 = 76
                let start = ProcessInfo.processInfo.systemUptime
                dpotrf_(&triangle,&dimension,&numeric,&leading,&info)
                factorizations += 1; factorSeconds += ProcessInfo.processInfo.systemUptime-start
                guard info == 0 else { throw RopePhysicsError.invalid("Condensed interior-point factorization (\(info))") }
                func linear(_ rhs: [Double]) throws -> [Double] {
                    func solve(_ load: [Double]) throws -> [Double] {
                        var answer = zip(load,scale).map(*)
                        var one: __LAPACK_int = 1
                        dpotrs_(&triangle,&dimension,&one,&numeric,&leading,&answer,&leading,&info)
                        guard info == 0 else { throw RopePhysicsError.invalid("Condensed interior-point Newton solve (\(info))") }
                        return zip(answer,scale).map(*)
                    }
                    var answer = try solve(rhs)
                    for _ in 0..<3 {
                        var error = rhs
                        for j in 0..<m { for i in 0..<m { error[i] -= schur[i+j*m]*answer[j] } }
                        for i in 0..<m { error[i] -= diagonal[i]*answer[i] }
                        if norm(zip(error,scale).map(*)) <= 1e-12*max(1,norm(zip(rhs,scale).map(*))) { break }
                        answer = zip(answer,try solve(error)).map(+)
                    }
                    guard answer.allSatisfy({ $0.isFinite }) else { throw RopePhysicsError.invalid("Nonfinite condensed interior-point direction") }
                    return answer
                }
                func direction(_ rc: [Double]) throws -> (force: [Double], slack: [Double]) {
                    let df = try linear((0..<m).map { rp[$0]+rc[$0]/force[$0] })
                    let ds = (0..<m).map { (rc[$0]-slack[$0]*df[$0])/force[$0] }
                    return (df,ds)
                }
                let affine = try direction((0..<m).map { -slack[$0]*force[$0] })
                let ap = fraction(slack,affine.slack), ad = fraction(force,affine.force)
                let mean = zip(slack,force).reduce(0.0) { $0+$1.0*$1.1 }/Double(m)
                let predicted = (0..<m).reduce(0.0) { $0+(slack[$1]+ap*affine.slack[$1])*(force[$1]+ad*affine.force[$1]) }/Double(m)
                let sigma = pow(min(1,max(0,predicted/mean)),3)
                let corrected = try direction((0..<m).map { sigma*mean-slack[$0]*force[$0]-affine.slack[$0]*affine.force[$0] })
                // One fraction keeps the eliminated stationarity exact and
                // contracts the original slack-gap equation simultaneously.
                let alpha = min(fraction(slack,corrected.slack,0.995),fraction(force,corrected.force,0.995))
                for i in 0..<m { force[i] += alpha*corrected.force[i]; slack[i] += alpha*corrected.slack[i] }
                guard (force+slack).allSatisfy({ $0.isFinite && $0 > 0 }) else { throw RopePhysicsError.invalid("Invalid condensed interior-point iterate") }
            }
        }
        var mu = (0..<m).map { initialMultipliers[$0] ?? 0 }
        for iteration in 0..<maxIterations {
            let current = try evaluate(mu)
            if current.accepted { return try recover(mu) }
            let delta = try direction(current,mu)
            var alpha = 1.0, accepted = false
            for _ in 0..<20 {
                lineTrials += 1
                let candidate = (0..<m).map { mu[$0]+alpha*delta[$0] }
                let value = try evaluate(candidate)
                if value.accepted || value.merit <= (1-1e-4*alpha)*current.merit {
                    mu = candidate; accepted = true; break
                }
                alpha *= 0.5
            }
            guard accepted else {
                if let path = ProcessInfo.processInfo.environment["HANGTEN_SCHUR_FAILURE_OUTPUT"] {
                    var jacobian = (0..<m).map { current.a[$0]*(-delta[$0]/scales[$0])-current.b[$0]*epsilon*delta[$0] }
                    var asymmetry = 0.0
                    for j in 0..<m { for i in 0..<m {
                        jacobian[i] -= current.b[i]*schur[i+j*m]*delta[j]
                        asymmetry = max(asymmetry,abs(schur[i+j*m]-schur[j+i*m]))
                    } }
                    let report: [String: Any] = ["scope": "rejected condensed working QP, no adoption",
                        "schur": schur, "scales": scales, "initial": initial, "mu": mu, "delta": delta,
                        "q": current.q, "gap": current.gap, "phi": current.phi, "a": current.a, "b": current.b,
                        "jacobianDelta": jacobian, "jacobianResidual": norm(zip(jacobian,current.phi).map(+)),
                        "meritDirectionalDerivative": 2*zip(jacobian,current.phi).reduce(0) { $0+$1.0*$1.1 },
                        "asymmetry": asymmetry, "maximumCompliance": norm(schur), "iteration": iteration]
                    try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]).write(to: URL(fileURLWithPath: path))
                }
                throw RopePhysicsError.invalid("Global Schur merit line-search bound at iteration \(iteration): rows \(m), merit \(current.merit), physical \(current.q.min() ?? 0), gap \(current.gap.min() ?? 0), complementarity \(norm((0..<m).map { mu[$0]*current.gap[$0] })), dual \(mu.max() ?? 0), direction \(norm(delta)), factors \(factorizations)")
            }
        }
        let final = try evaluate(mu)
        if final.accepted { return try recover(mu) }
        throw RopePhysicsError.invalid("Global Schur iteration bound: merit \(final.merit), physical \(final.q.min() ?? 0)")
    }
}

enum PrimalContactIP {
    static func solve(factor: PrimalPrepared, base: [Double], border: [Double], contacts: [RopeLinearContact],
                      initialMultipliers: [Int: Double] = [:], maxIterations: Int = 50,
                      fallback: (() throws -> RopeContactSystem.Solution)? = nil) throws -> RopeContactSystem.Solution {
        try GlobalSchurSession(factor: factor).solve(base: base, border: border, contacts: contacts,
            initialMultipliers: initialMultipliers, maxIterations: maxIterations)
    }
}
