// Native-only feature-bundle experiment. The app still uses complete manifolds.
struct RopeBundleFixtureResult {
    let base:[Double]
    let height:Double
    let passes:Int
    let featureIDs:Set<Int>
}
struct RopeMeshFeatureContact {
    let face:Int
    let squaredDistance:Double
    let contact:RopeSegmentContact
}
extension RopeTriangleCollider {
    /// Original fixed-radius BVH eligibility; no tighter running-best bound.
    func featureCandidates(from a:SIMD3<Double>,to b:SIMD3<Double>,radius:Double)->[Int] {
        let low=simd_min(a,b),high=simd_max(a,b),square=radius*radius
        var pending=[0],faces:[Int]=[]
        while let id=pending.popLast() {
            let node=tree[id]
            let separation=simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3<Double>(repeating:0))
            if simd_length_squared(separation)>=square {continue}
            if node.left>=0 {pending.append(node.left);pending.append(node.right)} else {faces += node.faces}
        }
        return faces.sorted()
    }
    /// Reevaluate an admitted triangle without the normal discovery cutoff.
    /// Positive-gap rows therefore survive a repair at the unchanged state.
    func contactForFeature(_ id:Int,from a:SIMD3<Double>,to b:SIMD3<Double>,radius:Double)->RopeMeshFeatureContact {
        precondition(mesh.triangles.indices.contains(id))
        let face=mesh.triangles[id],x=mesh.vertices[face.x],y=mesh.vertices[face.y],z=mesh.vertices[face.z]
        let faceNormal=simd_normalize(simd_cross(y-x,z-x))
        var best=Double.infinity,point=a,surface=SIMD3<Double>.zero,fraction=0.0
        func consider(_ p:SIMD3<Double>,_ q:SIMD3<Double>,_ f:Double) {
            let square=simd_length_squared(p-q)
            if square<best {best=square;point=p;surface=q;fraction=f}
        }
        consider(a,Self.triangleClosest(a,x,y,z),0)
        if a != b {
            consider(b,Self.triangleClosest(b,x,y,z),1)
            if let t=Self.rayTriangle(a,b-a,x,y,z),t>=0,t<=1 {
                let p=a+(b-a)*t;consider(p,p,t)
            }
            let xy=Self.segmentPair(a,b,x,y),yz=Self.segmentPair(a,b,y,z),zx=Self.segmentPair(a,b,z,x)
            consider(xy.0,xy.1,xy.2);consider(yz.0,yz.1,yz.2);consider(zx.0,zx.1,zx.2)
        }
        let distance=sqrt(best)
        return RopeMeshFeatureContact(face:id,squaredDistance:best,contact:RopeSegmentContact(
            centerlinePoint:point,surfacePoint:surface,normal:distance>1e-10 ? (point-surface)/distance:faceNormal,
            fraction:fraction,penetrationDepth:radius-distance))
    }
    func nearestFeature(from a:SIMD3<Double>,to b:SIMD3<Double>,radius:Double)->RopeMeshFeatureContact? {
        var best:RopeMeshFeatureContact?
        for id in featureCandidates(from:a,to:b,radius:radius) {
            let hit=contactForFeature(id,from:a,to:b,radius:radius)
            guard hit.squaredDistance<radius*radius else {continue}
            if hit.squaredDistance<(best?.squaredDistance ?? .infinity) {best=hit}
        }
        return best
    }
    /// Search OMITTED features, so a known winner or a tie cannot mask a second
    /// wall. This deliberately preserves complete original candidate coverage.
    func blockingFeatures(from a:SIMD3<Double>,to b:SIMD3<Double>,radius:Double,
        excluding:Set<Int>)->[RopeMeshFeatureContact] {
        featureCandidates(from:a,to:b,radius:radius).filter{!excluding.contains($0)}.compactMap {id in
            let hit=contactForFeature(id,from:a,to:b,radius:radius)
            return hit.squaredDistance<radius*radius && hit.contact.penetrationDepth>1e-8 ? hit:nil
        }
    }
}
enum RopeContactBundle {
    enum Failure:Error {case insideFallback,sweptTraversal}
    static func solveTranslatedCapsule(collider:RopeTriangleCollider,from a:SIMD3<Double>,to b:SIMD3<Double>,
        radius:Double,factor:RopeBandedFactorization,base:[Double],border:[Double]) throws -> RopeBundleFixtureResult {
        guard !collider.queryParity(a),!collider.queryParity(b) else {
            throw Failure.insideFallback
        }
        let rowRadius=radius+RopeRegionGeometry.clearance+0.00005,meritRadius=radius+RopeRegionGeometry.clearance
        guard let initial=collider.nearestFeature(from:a,to:b,radius:rowRadius) else {
            throw RopePhysicsError.invalid("Missing initial fixture contact")
        }
        var features:Set<Int>=[initial.face]
        // Fixed small-fixture cap registered before the RED/GREEN execution.
        for pass in 1...4 {
            let rows=features.sorted().map {id -> RopeLinearContact in
                let hit=collider.contactForFeature(id,from:a,to:b,radius:rowRadius).contact
                return RopeLinearContact(indices:[0,1],coefficients:[hit.normal.x,hit.normal.y],border:[-hit.normal.y],
                    residual:0.00005-hit.penetrationDepth)
            }
            let result=try RopeContactSystem.solve(factor:factor,base:base,border:border,contacts:rows)
            let delta=SIMD3(result.base[0],result.base[1]-result.border[0],0)
            let trialA=a+delta,trialB=b+delta
            guard !collider.queryParity(trialA),!collider.queryParity(trialB) else {
                throw Failure.insideFallback
            }
            let missing=collider.blockingFeatures(from:trialA,to:trialB,radius:meritRadius,excluding:features)
            if !missing.isEmpty {
                let previous=features.count;features.formUnion(missing.map(\.face))
                guard features.count>previous else {throw RopePhysicsError.invalid("No feature admission progress")}
                continue
            }
            guard collider.segmentClearance(from:trialA,to:trialB)>=radius-0.00005 else {
                throw RopePhysicsError.invalid("Invalid final fixture mesh clearance")
            }
            guard collider.sweptSegmentContact(previousStart:a,previousEnd:b,start:trialA,end:trialB,radius:radius-0.00005)==nil else {
                throw Failure.sweptTraversal
            }
            return RopeBundleFixtureResult(base:result.base,height:result.border[0],passes:pass,featureIDs:features)
        }
        throw RopePhysicsError.invalid("Fixture feature-repair cap")
    }
}
