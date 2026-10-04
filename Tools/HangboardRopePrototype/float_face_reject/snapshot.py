"""Stateless Float direction proposal, fresh Double certificate; native screen only."""
from pathlib import Path
from armijo.snapshot import once

def math_source(collider):
    start=collider.index('    private static func triangleClosest(')
    end=collider.index('\n    static func segmentPair(',start)
    closest=collider[start:end].replace('private static func triangleClosest','static func closest').replace('Double','Float')
    return Path(__file__).with_name('Math.swift').read_text().replace('// FLOAT_CLOSEST',closest)

def collider_source(source):
    source=once(source,'oracleDrops:[Bool]?=nil,captureDrop:',
        'oracleDrops:[Bool]?=nil,floatRejection:Bool=false,captureDrop:')
    source=once(source,'            let normal=simd_normalize(simd_cross(b-a,c-a))\n            var first=FusedWitness',
        '''            if floatRejection,FloatFaceReject.separates(start,end,a,b,c,rowRadius) {
                // Preserve the original rounded ray result independently of geometric separation.
                let ray = start != end && mask & 6 != 0 ? Self.rayTriangle(start,end-start,a,b,c):nil
                if ray==nil || ray!<0 || ray!>1 {
                    if let oracleDrops {precondition(oracleDrops[index],"Float certificate dropped nonempty original face")}
                    captureDrop?(index,true)
                    continue
                }
            }
            let normal=simd_normalize(simd_cross(b-a,c-a))
            var first=FusedWitness''')
    # Oracle masks in verification mode must verify rather than skip before the proposal.
    source=once(source,'if oracleDrops?[index]==true {continue}',
        'if !floatRejection && oracleDrops?[index]==true {continue}')
    source=once(source,'oracleDrops:[[Bool]]?=nil,captureDrops:Bool=false)->',
        'oracleDrops:[[Bool]]?=nil,captureDrops:Bool=false,floatRejection:Bool=false)->')
    source=once(source,'oracleDrops:oracleDrops?[i],captureDrop:observer)',
        'oracleDrops:oracleDrops?[i],floatRejection:floatRejection,captureDrop:observer)')
    source=once(source,'captureDrop?(index,first.hit==nil','if !floatRejection {captureDrop?(index,first.hit==nil')
    source=once(source,'&& !(row.best<rowSquare))','&& !(row.best<rowSquare))}')
    return source

def solver_source(source):
    return once(source,'oracleDrops:floorRequest.0,captureDrops:floorRequest.1)',
        'oracleDrops:floorRequest.0,captureDrops:floorRequest.1,floatRejection:EmptyFaceFloor.mode==4 || EmptyFaceFloor.mode==5)')

def trace_source(source):
    source=once(source,'if mode==2 || mode==3 {','if mode==2 || mode==3 || mode==5 {')
    source=once(source,'return (mode==2 ? record.zeros:record.drops,false)',
        'return (mode==2 ? record.zeros:record.drops,mode==5)')
    source=once(source,'static var records:[Record]=[]','static var verifiedRejects=0\n    static var records:[Record]=[]')
    source=once(source,'        seconds+=elapsed','        seconds+=elapsed\n        if mode==5 {verifiedRejects += drops.reduce(0){$0+$1.filter{$0}.count}}')
    return source

def driver_source(source):
    source=once(source,'    for iteration in 0..<7 {',
        '''    try floatFaceFixtures()
    var verified=initial;verified.woodMajorizerExperiment=true
    EmptyFaceFloor.start(5)
    let verification=try run(&verified)
    guard try serialize(verified.bundleCheckpoint())==checkpoint,try schedule(verification.1)==expectedSchedule,
          EmptyFaceFloor.cursor==EmptyFaceFloor.records.count else {throw RopePhysicsError.invalid("Float per-face verification/checkpoint")}
    result["allRejectedFacesOriginalEmpty"]=true
    result["verifiedRejectCount"]=EmptyFaceFloor.verifiedRejects
    guard EmptyFaceFloor.verifiedRejects>0 else {throw RopePhysicsError.invalid("vacuous Float rejection")}
    result["finiteDirectionDoubleCertificate"]=true
    result["floatReceiptProof"]=false
    result["runtimeAlgorithm"]=true
    if CommandLine.arguments.contains("--verification-only") {try persist(nil);print("PASS Float nonvacuous verification",EmptyFaceFloor.verifiedRejects);exit(0)}
    for iteration in 0..<7 {''')
    source=once(source,'let orders=[[0,2,3],[3,0,2],[2,3,0]],order=orders[iteration%3]',
        'let orders=[[0,4],[4,0]],order=orders[iteration%2]')
    source=once(source,'mode==0 || EmptyFaceFloor.cursor==EmptyFaceFloor.records.count',
        'mode==0 || mode==4 || EmptyFaceFloor.cursor==EmptyFaceFloor.records.count')
    start=source.index('        let overhead=times[2]!')
    end=source.index('\n} catch {',start)
    source=source[:start]+'''        pairs.append(["order":order,"unmaskedSeconds":times[0]!,"candidateSeconds":times[4]!,
            "ratio":times[4]!/times[0]!,"unmaskedQuerySeconds":queries[0]!,"candidateQuerySeconds":queries[4]!])
    }
    for key in ["unmaskedSeconds","candidateSeconds","ratio","unmaskedQuerySeconds","candidateQuerySeconds"] {
        result["median"+key.prefix(1).uppercased()+key.dropFirst()]=median(pairs.map{$0[key] as! Double})
    }
    result["completeCheckpointAndScheduleIdentity"]=true;result["workAndAccuracyPass"]=true
    let timing=result["medianCandidateSeconds"] as! Double,ratio=result["medianRatio"] as! Double
    result["pilotSpeedPass"]=timing<0.004 && ratio<=0.80
    try persist(nil)
    print("STATELESS FLOAT PILOT",timing<0.004 && ratio<=0.80 ? "PASS":"FAIL","median",timing,"ratio",ratio)
    if timing>=0.004 || ratio>0.80 {exit(3)}'''+source[end:]
    return source
