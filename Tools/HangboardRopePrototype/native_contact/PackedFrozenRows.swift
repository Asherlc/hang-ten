import Foundation

/// Immutable source storage, not an oversized working QP. Every original row
/// is captured/validated once and participates in every full affine scan.
struct PackedFrozenRows {
    private let offsets: [Int], indices: [Int], coefficients: [Double]
    private let residuals: [Double], borders: [Double], groups: [Int]
    private let borderCount: Int, size: Int

    init(source: FrozenContactStream, size: Int, borderCount: Int, equalities: Set<Int>) throws {
        guard source.count >= 0, source.count <= 8_000_000, size > 0, borderCount >= 0,
              size+borderCount <= 50_256 else { throw RopePhysicsError.invalid("Invalid packed source dimensions") }
        var offsets=[0], indices:[Int]=[], coefficients:[Double]=[]
        var residuals:[Double]=[], borders:[Double]=[], groups:[Int]=[]
        var groupIDs:[[Int]:Int]=[:]
        for id in 0..<source.count {
            let row=try source.row(id)
            guard row.indices.count==row.coefficients.count,row.border.count==borderCount,
                  row.residual.isFinite,(row.coefficients+row.border).allSatisfy({$0.isFinite}),
                  row.indices.allSatisfy({(0..<size).contains($0) && !equalities.contains($0)}),
                  indices.count+row.indices.count <= 8_000_000,
                  borders.count+borderCount <= 8_000_000 else {
                throw RopePhysicsError.invalid("Invalid or excessive packed frozen row")
            }
            if groupIDs[row.indices]==nil {groupIDs[row.indices]=groupIDs.count}
            groups.append(groupIDs[row.indices]!)
            indices += row.indices;coefficients += row.coefficients
            offsets.append(indices.count);residuals.append(row.residual);borders += row.border
        }
        self.offsets=offsets;self.indices=indices;self.coefficients=coefficients
        self.residuals=residuals;self.borders=borders;self.groups=groups;self.borderCount=borderCount;self.size=size
    }

    func row(_ id:Int)->RopeLinearContact {
        RopeLinearContact(indices:Array(indices[offsets[id]..<offsets[id+1]]),
            coefficients:Array(coefficients[offsets[id]..<offsets[id+1]]),
            border:Array(borders[id*borderCount..<(id+1)*borderCount]),residual:residuals[id])
    }

    func discover(_ vector:[Double],_ height:[Double],_ multipliers:[Double],_ included:Set<Int>) throws -> [Int] {
        guard vector.count==size,height.count==borderCount,multipliers.count==residuals.count else {
            throw RopePhysicsError.invalid("Invalid packed affine query")
        }
        var worst:[Int:(id:Int,gap:Double)]=[:]
        for id in residuals.indices {
            // Preserve the original operation order and regularization sign.
            var gap=residuals[id]-1e-8*multipliers[id]
            for k in offsets[id]..<offsets[id+1] {gap += coefficients[k]*vector[indices[k]]}
            for k in 0..<borderCount {gap += borders[id*borderCount+k]*height[k]}
            guard gap.isFinite else {throw RopePhysicsError.invalid("Nonfinite packed affine certificate")}
            if gap < -1e-10 {
                guard !included.contains(id) else {throw RopePhysicsError.invalid("Admitted packed row fails certificate")}
                if gap < (worst[groups[id]]?.gap ?? 0) {worst[groups[id]]=(id,gap)}
            }
        }
        return worst.values.map{$0.id}.sorted()
    }
}
