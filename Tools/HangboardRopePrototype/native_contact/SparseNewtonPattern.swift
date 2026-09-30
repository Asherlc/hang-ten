import Accelerate

/// Workspace-only CSC pattern for one frozen, admitted contact set. A changed
/// Jacobian/Hessian/contact set constructs a new pattern. Each changed Newton
/// weight recomputes numerical values and factors; no stale factor is reused.
final class SparseNewtonPrepared {
    let n: Int, nb: Int, dimension: Int
    private var starts: [Int]
    private var indices: [Int32]
    private let baseValues: [Double]
    private let contributions: [[(slot: Int, first: Double, second: Double)]]
    private var values: [Double]
    private var factor: SparseOpaqueFactorization_Double?

    init(factor original: PrimalPrepared, contacts: [RopeLinearContact], diagonal: [Double]) throws {
        let n = original.baseCount, nb = original.borderCount, dimension = n + nb
        guard dimension > 0, dimension <= 50_256, contacts.count == diagonal.count,
              contacts.count <= 100_000, contacts.allSatisfy({ row in
                  row.indices.count == row.coefficients.count && row.border.count == nb &&
                  row.indices.allSatisfy({ (0..<n).contains($0) }) &&
                  (row.coefficients + row.border).allSatisfy({ $0.isFinite })
              }) else { throw RopePhysicsError.invalid("Invalid sparse pattern input") }
        var originalValues: [Int: Double] = [:]
        var keys = Set<Int>()
        func key(_ row: Int, _ column: Int) -> Int {
            min(row, column) * dimension + max(row, column)
        }
        func originalTerm(_ row: Int, _ column: Int, _ value: Double) {
            if value != 0 {
                let index = key(row, column)
                originalValues[index, default: 0] += value
                keys.insert(index)
            }
        }
        for (r, c, v) in original.system.lowerEntries() { originalTerm(r, c, v) }
        for j in 0..<nb {
            for i in 0..<n { originalTerm(n+j, i, original.columns[j][i]) }
            for k in 0...j { originalTerm(n+j, n+k, original.borderMatrix[j][k]) }
        }
        var nonlocalCount = 0, contributionCount = 0
        var terms: [[(key: Int, first: Double, second: Double)]] = []
        for row in contacts {
            if let first = row.indices.min(), let last = row.indices.max(), last-first > original.system.bandwidth {
                nonlocalCount += 1
            }
            let coefficients = zip(row.indices, row.coefficients).filter { $0.1 != 0 } +
                row.border.indices.compactMap { row.border[$0] != 0 ? (n+$0, row.border[$0]) : nil }
            var products: [(key: Int, first: Double, second: Double)] = []
            for i in coefficients.indices { for j in 0...i {
                let index = key(coefficients[i].0, coefficients[j].0)
                keys.insert(index)
                products.append((index, coefficients[i].1, coefficients[j].1))
            } }
            contributionCount += products.count
            guard keys.count <= 8_000_000, contributionCount <= 8_000_000 else {
                throw RopePhysicsError.invalid("Excessive sparse pattern")
            }
            terms.append(products)
        }
        guard nonlocalCount+nb <= 256 else { throw RopePhysicsError.invalid("Excessive nonlocal sparse pattern") }
        let ordered = keys.sorted()
        let slots = Dictionary(uniqueKeysWithValues: ordered.enumerated().map { ($0.element, $0.offset) })
        var starts = [0], indices: [Int32] = [], column = 0
        for index in ordered {
            while column < index/dimension { starts.append(indices.count); column += 1 }
            indices.append(Int32(index % dimension))
        }
        while starts.count < dimension+1 { starts.append(indices.count) }
        self.n = n; self.nb = nb; self.dimension = dimension
        self.starts = starts; self.indices = indices
        baseValues = ordered.map { originalValues[$0] ?? 0 }
        contributions = terms.map { $0.map { (slots[$0.key]!, $0.first, $0.second) } }
        values = baseValues
        factor = nil
        try refactor(diagonal: diagonal)
    }

    func refactor(diagonal: [Double]) throws {
        guard diagonal.count == contributions.count, diagonal.allSatisfy({ $0.isFinite && $0 > 0 }) else {
            throw RopePhysicsError.invalid("Invalid sparse Newton weights")
        }
        var next = baseValues
        for id in contributions.indices {
            for contribution in contributions[id] {
                next[contribution.slot] += diagonal[id] * contribution.first * contribution.second
            }
        }
        guard next.allSatisfy({ $0.isFinite }) else { throw RopePhysicsError.invalid("Nonfinite sparse Newton matrix") }
        values = next
        var attributes = SparseAttributes_t()
        attributes.kind = SparseSymmetric; attributes.triangle = SparseLowerTriangle
        // The pattern arrays remain identical, including numerical zeros. Only
        // the weights change; SparseRefactor performs a new numeric factor.
        starts.withUnsafeMutableBufferPointer { s in
            indices.withUnsafeMutableBufferPointer { i in
                values.withUnsafeMutableBufferPointer { v in
                    let structure = SparseMatrixStructure(rowCount: Int32(dimension), columnCount: Int32(dimension),
                        columnStarts: s.baseAddress!, rowIndices: i.baseAddress!, attributes: attributes, blockSize: 1)
                    let matrix = SparseMatrix_Double(structure: structure, data: v.baseAddress!)
                    if var numeric = factor {
                        SparseRefactor(matrix, &numeric)
                        factor = numeric
                    } else {
                        factor = SparseFactor(SparseFactorizationLDLTTPP, matrix)
                    }
                }
            }
        }
        guard factor?.status == SparseStatusOK else {
            throw RopePhysicsError.invalid("Sparse Newton numeric factorization failed")
        }
    }

    deinit { if let factor { SparseCleanup(factor) } }

    private func product(_ x: [Double]) -> [Double] {
        var result = Array(repeating: 0.0, count: dimension)
        for c in 0..<dimension { for k in starts[c]..<starts[c+1] {
            let r = Int(indices[k]), v = values[k]
            result[r] += v*x[c]
            if r != c { result[c] += v*x[r] }
        } }
        return result
    }

    private func solve(_ rhs: [Double]) throws -> [Double] {
        guard let factor, factor.status == SparseStatusOK else { throw RopePhysicsError.invalid("Unfactored sparse Newton system") }
        var result = rhs
        result.withUnsafeMutableBufferPointer { x in
            SparseSolve(factor, DenseVector_Double(count: Int32(dimension), data: x.baseAddress!))
        }
        return result
    }

    func refined(_ rhs: [Double], _ border: [Double]) throws -> (base: [Double], border: [Double]) {
        guard rhs.count == n, border.count == nb else { throw RopePhysicsError.invalid("Invalid sparse Newton load") }
        let load = rhs+border
        var result = try solve(load)
        for _ in 0..<3 {
            let error = zip(load, product(result)).map(-)
            if error.map({ abs($0) }).max()! <= 1e-12 * max(1, load.map({ abs($0) }).max()!) { break }
            result = zip(result, try solve(error)).map(+)
        }
        guard result.allSatisfy({ $0.isFinite }) else { throw RopePhysicsError.invalid("Nonfinite sparse Newton result") }
        return (Array(result.prefix(n)), Array(result.suffix(nb)))
    }
}
