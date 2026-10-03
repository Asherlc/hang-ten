var highReceiptRed=false
func validReceipt(_ value:Double?,_ exact:Double,_ radius:Double)->Bool {
    guard let value else{return true}
    if value.isFinite {return value.bitPattern==exact.bitPattern}
    return value==Double.infinity && exact>=radius
}
for (i,q) in queries.enumerated() {
    let (a,b,r)=q
    let receipt=candidate.fusedContactEvaluation(from:a,to:b,rowRadius:r,meritRadius:r-0.00005,
        startInside:candidate.queryParity(a),endInside:candidate.queryParity(b)).clearance
    let exact=reference.segmentClearance(from:a,to:b)
    guard validReceipt(receipt,exact,r) else {throw RopePhysicsError.invalid("raw clearance receipt \(i)")}
    if let receipt,receipt.isFinite {highReceiptRed = highReceiptRed || !validReceipt(receipt+0.001,exact,r)}
}
guard highReceiptRed else {throw RopePhysicsError.invalid("false high receipt accepted")}
print("PASS raw nearest-distance / no-witness lower-bound receipts; falsely high distance rejected")
