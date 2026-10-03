alarm(90)
var hitRed=false,timeRed=false
for (i,q) in queries.enumerated() {
    let (a,b,r)=q
    for delta in [SIMD3<Double>.zero,SIMD3(0,0.0007,-0.0009),SIMD3(0,-0.003,0.006)] {
        let x=reference.sweptSegmentContact(previousStart:a,previousEnd:b,start:a+delta,end:b+delta,radius:r)
        let y=candidate.sweptSegmentContact(previousStart:a,previousEnd:b,start:a+delta,end:b+delta,radius:r)
        guard x.map(signature)==y.map(signature) else {throw RopePhysicsError.invalid("sweep identity \(i)")}
        if let y {hitRed=true;if let time=y.timeOfImpact {timeRed = timeRed || time.bitPattern != (time+0.1).bitPattern}}
    }
}
alarm(0)
guard hitRed,timeRed else {throw RopePhysicsError.invalid("sweep negative controls")}
print("PASS moving sweeps: witness/timeofimpact bits and hit/time negative controls")
