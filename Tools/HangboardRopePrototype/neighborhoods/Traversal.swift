// Immutable acquired leaf IDs; every query recomputes the original masks.
extension RopeTriangleCollider {
    private func neighborhoodFaces(start:SIMD3<Double>,end:SIMD3<Double>,rowRadius:Double,meritRadius:Double,
        enabled:Bool,prior:RopeQueryNeighborhood?,verify:Bool)->(faces:[(Int,Int)],neighborhood:RopeQueryNeighborhood?,reused:Bool,conflict:Bool) {
        let low=simd_min(start,end),high=simd_max(start,end)
        let rowSquare=rowRadius*rowRadius,meritSquare=meritRadius*meritRadius
        func mask(_ index:Int,_ parent:Int)->Int {
            let node=tree[index]
            let link=simd_length_squared(simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3(repeating:0)))
            let first=simd_length_squared(simd_max(simd_max(node.minimum-start,start-node.maximum),SIMD3(repeating:0)))
            let last=simd_length_squared(simd_max(simd_max(node.minimum-end,end-node.maximum),SIMD3(repeating:0)))
            var result=parent
            if first>=rowSquare {result &= ~1}
            if link>=rowSquare {result &= ~2}
            if link>=meritSquare {result &= ~4}
            if last>=rowSquare {result &= ~8}
            return result
        }
        func original()->[(Int,Int)] {
            var stack=[(0,15)],faces:[(Int,Int)]=[]
            while let (index,parent)=stack.popLast() {
                let node=tree[index],m=mask(index,parent)
                if m==0 {continue}
                if node.left>=0 {stack.append((node.left,m));stack.append((node.right,m))}
                else {for face in node.faces {faces.append((face,m))}}
            }
            return faces
        }
        let valid=enabled && supportDomain && rowRadius.isFinite && meritRadius.isFinite &&
            rowRadius>=0.001 && rowRadius<=0.01 && meritRadius>0 && meritRadius<=rowRadius &&
            [start,end].allSatisfy {$0.x.isFinite && $0.y.isFinite && $0.z.isFinite && max(abs($0.x),max(abs($0.y),abs($0.z)))<=0.5}
        guard valid else {return (original(),nil,false,false)}
        var roster:RopeQueryNeighborhood?,reused=false
        if let prior,prior.covers(low:low,high:high,radius:rowRadius,identity:neighborhoodIdentity),
           prior.leaves.allSatisfy({tree.indices.contains($0) && tree[$0].left<0}) {
            roster=prior;reused=true
        } else {
            let expanded=(rowRadius+RopeQueryNeighborhood.halo+1e-9).nextUp,square=expanded*expanded
            var stack=[0],leaves:[Int]=[],overflow=false
            while let index=stack.popLast() {
                let node=tree[index]
                let gap=simd_length_squared(simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3(repeating:0)))
                if gap>=square {continue}
                if node.left>=0 {stack.append(node.left);stack.append(node.right)}
                else {
                    leaves.append(index)
                    if leaves.count>RopeQueryNeighborhood.leafCap {overflow=true;break}
                }
            }
            if !overflow {roster=RopeQueryNeighborhood(identity:neighborhoodIdentity,low:low,high:high,rowRadius:rowRadius,leaves:leaves)}
        }
        guard let roster else {return (original(),nil,false,false)}
        var faces:[(Int,Int)]=[]
        for index in roster.leaves {
            let m=mask(index,15)
            if m != 0 {for face in tree[index].faces {faces.append((face,m))}}
        }
        var conflict=false
        if verify {
            let expected=original().sorted(by:{$0.0<$1.0}),actual=faces.sorted(by:{$0.0<$1.0})
            conflict=expected.count != actual.count || !zip(expected,actual).allSatisfy{$0.0.0==$0.1.0 && $0.0.1==$0.1.1}
        }
        return (faces,roster,reused,conflict)
    }
}
