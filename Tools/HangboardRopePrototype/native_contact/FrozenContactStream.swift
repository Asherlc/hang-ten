import Foundation

/// The provider captures immutable geometry/state of one frozen linearization.
/// Re-querying a mutable live state through this closure is outside its contract.
struct FrozenContactStream {
    let count: Int
    let row: (Int) throws -> RopeLinearContact
}

enum StreamedContactAdmission {
    static func solve(factor: PrimalPrepared, base: [Double], border: [Double], contacts: FrozenContactStream,
                      initialMultipliers: [Int: Double] = [:], maxIterations: Int = 50, maxAdmissions: Int = 20,
                      observe: ((Int, Int, Int) -> Void)? = nil) throws -> RopeContactSystem.Solution {
        let size = base.count, count = contacts.count, equalities = Set(factor.equalities)
        guard size == factor.baseCount, border.count == factor.borderCount, size > 0, size+border.count <= 50_256,
              count >= 0, count <= 8_000_000, (1...50).contains(maxIterations), (1...20).contains(maxAdmissions),
              (base+border).allSatisfy({ $0.isFinite }), initialMultipliers.allSatisfy({
                  (0..<count).contains($0.key) && $0.value.isFinite && $0.value <= 0
              }) else { throw RopePhysicsError.invalid("Invalid streamed contact input") }

        func discover(_ vector: [Double], _ height: [Double], _ multipliers: [Double], _ included: Set<Int>) throws -> [Int] {
            var worst: [[Int]: (id: Int, gap: Double)] = [:]
            for id in 0..<count {
                let row = try contacts.row(id)
                // Validate clear and omitted rows too. Streaming is no license
                // to skip a malformed or nonfinite inequality.
                guard row.indices.count == row.coefficients.count, row.border.count == height.count,
                      row.residual.isFinite, (row.coefficients+row.border).allSatisfy({ $0.isFinite }),
                      row.indices.allSatisfy({ (0..<size).contains($0) && !equalities.contains($0) }) else {
                    throw RopePhysicsError.invalid("Invalid frozen streamed row")
                }
                var gap = row.residual-1e-8*multipliers[id]
                for k in row.indices.indices { gap += row.coefficients[k]*vector[row.indices[k]] }
                for k in row.border.indices { gap += row.border[k]*height[k] }
                guard gap.isFinite else { throw RopePhysicsError.invalid("Nonfinite streamed affine certificate") }
                // Certify the regularized contact equation at its existing
                // tolerance, independently of the looser physical gap gate.
                if gap < -1e-10 {
                    guard !included.contains(id) else { throw RopePhysicsError.invalid("Admitted streamed row fails certificate") }
                    // References group representatives only. No redundancy is
                    // assumed; every original row participates in each scan.
                    if gap < (worst[row.indices]?.gap ?? 0) { worst[row.indices] = (id, gap) }
                }
            }
            return worst.values.map { $0.id }.sorted()
        }
        var included = Set(try discover(base, border, Array(repeating: 0, count: count), []))
        included.formUnion(initialMultipliers.keys)
        var dual = initialMultipliers
        for admission in 0..<maxAdmissions {
            // Preserve the existing working-QP contact budget. A source larger
            // than it is scanned, never materialized as an oversized QP input.
            guard included.count <= 100_000 else { throw RopePhysicsError.invalid("Excessive admitted contact set") }
            let ids = included.sorted(), subset = try ids.map { try contacts.row($0) }
            let warm = Dictionary(uniqueKeysWithValues: ids.enumerated().compactMap { offset, id in
                dual[id].map { (offset, min(0, $0)) }
            })
            let solved = try PrimalContactIP.solve(factor: factor, base: base, border: border,
                contacts: subset, initialMultipliers: warm, maxIterations: maxIterations)
            guard solved.base.count == size, solved.border.count == border.count, solved.multipliers.count == ids.count,
                  solved.activeIDs.allSatisfy({ ids.indices.contains($0) }),
                  (solved.base+solved.border+solved.multipliers).allSatisfy({ $0.isFinite }),
                  solved.multipliers.allSatisfy({ $0 <= 1e-12 }) else { throw RopePhysicsError.invalid("Invalid streamed working solution") }
            var multipliers = Array(repeating: 0.0, count: count)
            for index in ids.indices { multipliers[ids[index]] = solved.multipliers[index] }
            let added = try discover(solved.base, solved.border, multipliers, included)
            observe?(admission+1, ids.count, added.count)
            if added.isEmpty {
                return RopeContactSystem.Solution(base: solved.base, border: solved.border,
                    multipliers: multipliers, activeIDs: solved.activeIDs.map { ids[$0] })
            }
            dual = Dictionary(uniqueKeysWithValues: solved.activeIDs.map { (ids[$0], min(0, solved.multipliers[$0])) })
            included.formUnion(added)
        }
        throw RopePhysicsError.invalid("Streamed affine admission limit")
    }
}
