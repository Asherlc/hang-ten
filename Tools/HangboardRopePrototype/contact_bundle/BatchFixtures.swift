// Read-only geometry parity tests for the native feature output contract.
do {
    let held:RopeWoodFeature=RopeWoodFeature(rope:0,point:false,index:0,face:6)
    let start=SIMD3<Double>(0.00355,0.00355,-0.01),end=SIMD3<Double>(0.00355,0.00355,-0.03)
    let endpoint=collider.featureChainContacts(points:[start,end],rope:0,rowRadius:rowRadius,meritRadius:0.0036,held:[held])
    let slot=endpoint.linkFaces[0].firstIndex(of:6)!
    try require(endpoint.rows[0][slot].fraction==0,"Held face lost its endpoint witness in batch")
    let insidePoints=[a-SIMD3(0.006,0,0),b-SIMD3(0.006,0,0)]
    let signed=collider.featureChainContacts(points:insidePoints,rope:0,rowRadius:rowRadius,meritRadius:0.0036,held:[])
    let original=collider.fusedChainContacts(points:insidePoints,rowRadius:rowRadius,meritRadius:0.0036)
    try require(signed.insideFallback,"Batch did not invoke original signed fallback")
    try require(signed.rows[0].map{[$0.fraction.bitPattern,$0.penetrationDepth.bitPattern]}==original.rows[0].map{[$0.fraction.bitPattern,$0.penetrationDepth.bitPattern]},"Signed fallback output changed")
    let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
    let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
    let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
    let mesh=try RopeTriangleCollider(input:input),upright=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
    let seed=try RopeThreadedSeed.make(input:input,profileID:input.profiles[0].id,orientation:upright,collider:mesh)
    var comparisons=0
    for rope in seed.ropes {
        for shift in [SIMD3<Double>.zero,SIMD3(0.0002,0,0),SIMD3(0,0.0002,0),SIMD3(0,0,-0.0002)] {
            let points=rope.positions.map{seed.boardPoint($0)+shift}
            let batch=mesh.featureChainContacts(points:points,rope:0,rowRadius:rowRadius,meritRadius:0.0036,held:[])
            let full=mesh.fusedChainContacts(points:points,rowRadius:rowRadius,meritRadius:0.0036)
            for i in rope.restLengths.indices {
                let d=batch.merits[i].map(\.penetrationDepth).max() ?? 0
                let original=full.merits[i].map(\.penetrationDepth).max() ?? 0
                try require(d.bitPattern==original.bitPattern,"Original mesh merit changed at link \(i)")
                try require(batch.clearances[i]?.bitPattern==full.clearances[i]?.bitPattern,"Original row clearance receipt changed")
                comparisons += 1
            }
        }
    }
    let result:[String:Any]=["owner":"strong-owl-live-physics","actualMeshLinkComparisons":comparisons,
        "meritDepthBitIdentity":true,"clearanceReceiptBitIdentity":true,"heldEndpointRetained":true,"originalSignedFallbackExecuted":true,
        "scope":"actual Clav seed plus three fixed displacements, including channels and mouths; no dynamics/speed claim"]
    try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:
        URL(fileURLWithPath:CommandLine.arguments[1]).appendingPathComponent("batch-fixtures.json"))
    print("PASS native feature batch",comparisons,"actual mesh links, endpoint retention, original signed fallback")
} catch {print("FAIL feature batch",error);exit(2)}
