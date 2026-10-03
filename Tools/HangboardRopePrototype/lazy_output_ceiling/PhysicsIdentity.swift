extension RopeDynamicsSolver {
    func lazyAdditionalPhysicsIdentity()->[UInt64] {
        var bits:[UInt64]=[convergenceExperiment ? 1:0,lastCorrectionFullStep ? 1:0]
        if let bounds=acceptedSegmentClearanceBounds {
            bits += [1,UInt64(bounds.count)]
            for row in bounds {bits.append(UInt64(row.count));bits += row.map(\.bitPattern)}
        } else {bits.append(0)}
        bits.append(UInt64(contactHints.count))
        for (row,lambda) in contactHints {
            bits.append(UInt64(row.indices.count));bits += row.indices.map{UInt64($0)}
            bits += row.coefficients.map(\.bitPattern)
            bits.append(UInt64(row.border.count));bits += row.border.map(\.bitPattern)
            bits += [row.residual.bitPattern,lambda.bitPattern]
        }
        return bits
    }
}
