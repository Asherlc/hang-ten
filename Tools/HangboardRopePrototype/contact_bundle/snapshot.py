"""Native-only source transform. Product/default solver stays untouched."""
def solver_source(text):
    def swap(old,new):
        nonlocal text
        assert text.count(old)==1,old
        text=text.replace(old,new)
    swap('    private var cachedEvaluation:RopeConfigurationEvaluation?\n','''    private var cachedEvaluation:RopeConfigurationEvaluation?
    private var bundleStepActive=false
    private var bundleHeld:Set<RopeWoodFeature>=[]
    private var bundleEpoch=0
    private var bundleForceFull=false
    private(set) var bundleRepairs=0
    private(set) var bundleAdmissions=0
    private(set) var bundleMerits=0
    private(set) var bundleRows:[Int]=[]
    private(set) var bundleFallbacks=0
    private var bundleExperiment=false
''')
    swap('        candidate.reviewStepCorrections = 0\n','''        candidate.reviewStepCorrections = 0
        candidate.bundleRepairs=0;candidate.bundleAdmissions=0;candidate.bundleMerits=0;candidate.bundleRows=[];candidate.bundleFallbacks=0
''')
    swap('            let failedRetries = trial.reviewStepRetries\n','''            let failedRetries = trial.reviewStepRetries
            let failedBundleRepairs=trial.bundleRepairs,failedBundleAdmissions=trial.bundleAdmissions,failedBundleMerits=trial.bundleMerits
            let failedBundleRows=trial.bundleRows,failedBundleFallbacks=trial.bundleFallbacks
''')
    swap('            trial.reviewStepRetries = failedRetries + 1\n','''            trial.reviewStepRetries = failedRetries + 1
            trial.bundleRepairs=failedBundleRepairs;trial.bundleAdmissions=failedBundleAdmissions;trial.bundleMerits=failedBundleMerits
            trial.bundleRows=failedBundleRows;trial.bundleFallbacks=failedBundleFallbacks
''')
    swap('        let old=state\n','''        bundleStepActive=bundleExperiment
        bundleHeld=[];bundleEpoch += 1;bundleForceFull=false
        let old=state
''')
    swap('            let movement=try correctConstraints(prediction:prediction)\n','''            let progress=try correctConstraints(prediction:prediction)
            if progress.retry {continue}
            let movement=progress.movement
''')
    swap('        var secondRope:Int?=nil\n','        var secondRope:Int?=nil\n        var woodFeature:RopeWoodFeature?=nil\n')
    swap('    private mutating func correctConstraints(prediction:RopeSimulationState) throws -> Double {','''    private struct BundleCorrection {let movement:Double;let retry:Bool}
    private mutating func correctConstraints(prediction:RopeSimulationState) throws -> BundleCorrection {''')
    swap('''        let evaluation=configurationEvaluation(state)
        var rows:[ConstraintRow]=[]''','''        var evaluation=configurationEvaluation(state)
        if bundleStepActive && !bundleForceFull && evaluation.insideFallback {
            bundleForceFull=true;bundleFallbacks += 1;bundleEpoch += 1;cachedEvaluation=nil
            evaluation=configurationEvaluation(state)
        }
        var rows:[ConstraintRow]=[]''')
    swap('                for hit in evaluation.points[r][i] {','''                for (hitIndex,hit) in evaluation.points[r][i].enumerated() {''')
    swap('boardGradient:-normal.y+simd_dot(normal,attached),residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil))','''boardGradient:-normal.y+simd_dot(normal,attached),residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil,
                        woodFeature:evaluation.pointFaces[r][i].indices.contains(hitIndex) ? RopeWoodFeature(rope:r,point:true,index:i,face:evaluation.pointFaces[r][i][hitIndex]):nil))''')
    swap('                for hit in evaluation.rows[r][i] where hit.fraction>1e-6 && hit.fraction<1-1e-6 {','''                // Endpoint witnesses of retained link faces must remain constraints.
                for (hitIndex,hit) in evaluation.rows[r][i].enumerated() where
                    (bundleStepActive && !bundleForceFull) || (hit.fraction>1e-6 && hit.fraction<1-1e-6) {''')
    swap('''                    rows.append(ConstraintRow(rope:r,particles:[i,i+1],gradients:gradients,boardGradient:boardGradient,
                        residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil))''','''                    rows.append(ConstraintRow(rope:r,particles:[i,i+1],gradients:gradients,boardGradient:boardGradient,
                        residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil,
                        woodFeature:evaluation.linkFaces[r][i].indices.contains(hitIndex) ? RopeWoodFeature(rope:r,point:false,index:i,face:evaluation.linkFaces[r][i][hitIndex]):nil))''')
    swap('        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)\n','''        if bundleStepActive {bundleRows.append(rows.filter{$0.contact}.count)}
        let represented=Set(rows.compactMap(\\.woodFeature))
        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)
''')
    swap('''                if try merit(state,prediction:prediction,weights:weights,penalty:penalty)<=score+1e-18 {''','''                let trialScore=try merit(state,prediction:prediction,weights:weights,penalty:penalty)
                if bundleStepActive && !bundleForceFull {
                    let trial=configurationEvaluation(state)
                    if trial.insideFallback {
                        state=before;bundleForceFull=true;bundleFallbacks += 1;bundleEpoch += 1;cachedEvaluation=nil
                        lastCorrectionFullStep=false
                        return BundleCorrection(movement:.infinity,retry:true)
                    }
                    let missing=trial.blockers.subtracting(represented)
                    if !missing.isEmpty {
                        let count=bundleHeld.count;bundleHeld.formUnion(missing)
                        guard bundleHeld.count>count else {throw StepFailure.nonlinearConvergence}
                        bundleAdmissions += bundleHeld.count-count;bundleRepairs += 1
                        state=before;bundleEpoch += 1;cachedEvaluation=nil;lastCorrectionFullStep=false
                        return BundleCorrection(movement:.infinity,retry:true)
                    }
                }
                if trialScore<=score+1e-18 {''')
    swap('''                    lastCorrectionFullStep=alpha==1
                    return (convergenceExperiment ? 1:alpha)*max(maximum,abs(heightCorrection))''','''                    if bundleStepActive && !bundleForceFull {
                        let count=bundleHeld.count
                        for (index,row) in selected.enumerated() where lambda[index]<0 {
                            if let feature=row.woodFeature {bundleHeld.insert(feature)}
                        }
                        if bundleHeld.count != count {bundleEpoch += 1;cachedEvaluation=nil}
                    }
                    lastCorrectionFullStep=alpha==1
                    return BundleCorrection(movement:(convergenceExperiment ? 1:alpha)*max(maximum,abs(heightCorrection)),retry:false)''')
    swap('private struct RopeConfigurationEvaluation:Sendable {','''private struct RopeConfigurationEvaluation:Sendable {
    let bundleEpoch:Int
    let pointFaces:[[[Int]]]
    let linkFaces:[[[Int]]]
    let blockers:Set<RopeWoodFeature>
    let insideFallback:Bool''')
    swap('cached.bits==bits,cached.portalOrder==portalOrder {return cached}','cached.bits==bits,cached.portalOrder==portalOrder,cached.bundleEpoch==bundleEpoch {return cached}')
    swap('''        for rope in candidate.ropes {
            let board=rope.positions.map{candidate.boardPoint($0)}
            let batch=collider.fusedChainContacts(points:board,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,meritRadius:rope.radius+RopeRegionGeometry.clearance)
            clearances.append(batch.clearances)
            points.append(batch.points);rows.append(batch.rows);merits.append(batch.merits)''','''        var pointFaces:[[[Int]]]=[],linkFaces:[[[Int]]]=[],blockers:Set<RopeWoodFeature>=[],inside=false
        for (r,rope) in candidate.ropes.enumerated() {
            let board=rope.positions.map{candidate.boardPoint($0)}
            if bundleStepActive && !bundleForceFull {
                let batch=collider.featureChainContacts(points:board,rope:r,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,
                    meritRadius:rope.radius+RopeRegionGeometry.clearance,held:bundleHeld)
                clearances.append(batch.clearances);points.append(batch.points);rows.append(batch.rows);merits.append(batch.merits)
                pointFaces.append(batch.pointFaces);linkFaces.append(batch.linkFaces);blockers.formUnion(batch.blockers)
                inside = inside || batch.insideFallback
            } else {
                let batch=collider.fusedChainContacts(points:board,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,meritRadius:rope.radius+RopeRegionGeometry.clearance)
                clearances.append(batch.clearances);points.append(batch.points);rows.append(batch.rows);merits.append(batch.merits)
                pointFaces.append(Array(repeating:[],count:rope.positions.count));linkFaces.append(Array(repeating:[],count:rope.restLengths.count))
            }''')
    swap('''let result=RopeConfigurationEvaluation(bits:bits,portalOrder:portalOrder,points:points,rows:rows,merits:merits,clearances:clearances,selfPairs:pairs,cordContacts:cords)''','''let result=RopeConfigurationEvaluation(bundleEpoch:bundleEpoch,pointFaces:pointFaces,linkFaces:linkFaces,blockers:blockers,insideFallback:inside,
            bits:bits,portalOrder:portalOrder,points:points,rows:rows,merits:merits,clearances:clearances,selfPairs:pairs,cordContacts:cords)''')
    swap('''        let evaluation=configurationEvaluation(candidate)
''','''        if bundleStepActive {bundleMerits += 1}
        let evaluation=configurationEvaluation(candidate)
''')
    return text+'''
extension RopeDynamicsSolver {
    mutating func setBundleExperiment(_ enabled:Bool) {bundleExperiment=enabled;cachedEvaluation=nil}
    var bundleReport:[String:Any] {["repairs":bundleRepairs,"admissions":bundleAdmissions,"merits":bundleMerits,
        "contactRows":bundleRows,"fallbacks":bundleFallbacks,"retainedFeatures":bundleHeld.count]}
}
'''
