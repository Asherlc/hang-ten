import XCTest
final class PrimalTests:XCTestCase {
 func testIndependentLoopsAndBoardAgainstFullKKT() throws {
  var system=try RopeBandedSystem(size:2,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:2)
  try system.addSymmetric(row:1,column:1,value:3)
  let factor=try system.primalPrepared(borderColumns:[[0,0]],borderMatrix:[[5]])
  let contacts=[RopeLinearContact(indices:[0,1],coefficients:[-1,1],border:[0],residual:-0.001),
    RopeLinearContact(indices:[0],coefficients:[1],border:[-1],residual:-0.00025)]
  let answer=try PrimalContactIP.solve(factor:factor,base:[0,0],border:[0],contacts:contacts)
  let reference=try system.solve(rhs:[0,0],borderColumns:[[0,0],[-1,1],[1,0]],
    borderMatrix:[[5,0,-1],[0,-1e-8,0],[-1,0,-1e-8]],borderRHS:[0,0.001,0.00025])
  for (a,b) in zip(answer.base+answer.border,reference.base+[reference.border[0]]) {XCTAssertEqual(a,b,accuracy:1e-10)}
  for i in 0..<2 {XCTAssertEqual(answer.multipliers[i],reference.border[i+1],accuracy:1e-10)}
 }
 func testDependentStrongConstraintIsNotDiscarded() throws {
  var system=try RopeBandedSystem(size:1,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:1)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let contacts=[RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-0.0004),
    RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-0.001),
    RopeLinearContact(indices:[0],coefficients:[-1],border:[],residual:0.002)]
  let answer=try PrimalContactIP.solve(factor:factor,base:[0],border:[],contacts:contacts)
  XCTAssertEqual(answer.base[0],0.001/(1+1e-8),accuracy:1e-10)
  XCTAssertEqual(answer.multipliers[0],0,accuracy:1e-10)
  XCTAssertEqual(answer.multipliers[1],-0.001/(1+1e-8),accuracy:1e-10)
  for row in contacts {XCTAssertGreaterThanOrEqual(row.residual+row.coefficients[0]*answer.base[0],-1e-8)}
 }
 func testEqualityAndBoardAgainstFullKKT() throws {
  var system=try RopeBandedSystem(size:3,bandwidth:2)
  try system.addSymmetric(row:0,column:0,value:0.005)
  try system.addSymmetric(row:1,column:1,value:0.005)
  try system.addSymmetric(row:2,column:0,value:-1)
  try system.addSymmetric(row:2,column:1,value:1)
  try system.addSymmetric(row:2,column:2,value:-1e-8)
  let factor=try system.primalPrepared(borderColumns:[[0,0,-1]],borderMatrix:[[1]],equalities:[2])
  let base=try factor.solve(rhs:[0,0,-0.022],borderRHS:[-0.004])
  let contacts=[RopeLinearContact(indices:[0,1],coefficients:[1,-1],border:[0],residual:-0.03)]
  let answer=try PrimalContactIP.solve(factor:factor,base:base.base,border:base.border,contacts:contacts)
  let reference=try system.solve(rhs:[0,0,-0.022],borderColumns:[[0,0,-1],[1,-1,0]],
   borderMatrix:[[1,0],[0,-1e-8]],borderRHS:[-0.004,0.03])
  for (a,b) in zip(answer.base+answer.border,reference.base+[reference.border[0]]) {XCTAssertEqual(a,b,accuracy:1e-10)}
  XCTAssertEqual(answer.multipliers[0],reference.border[1],accuracy:1e-10)
 }
 func testNonlocalContactStaysGloballyCoupled() throws {
  var system=try RopeBandedSystem(size:4,bandwidth:0)
  for i in 0..<4 {try system.addSymmetric(row:i,column:i,value:Double(i+1))}
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let contacts=[RopeLinearContact(indices:[0,3],coefficients:[-1,1],border:[],residual:-0.001)]
  let result=try PrimalContactIP.solve(factor:factor,base:[0,0,0,0],border:[],contacts:contacts)
  let reference=try system.solve(rhs:[0,0,0,0],borderColumns:[[-1,0,0,1]],borderMatrix:[[-1e-8]],borderRHS:[0.001])
  for (a,b) in zip(result.base,reference.base) {XCTAssertEqual(a,b,accuracy:1e-10)}
 }
 func testRegularizedPenetrationCannotOverridePhysicalGate() throws {
  var system=try RopeBandedSystem(size:1,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:2)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let contacts=[RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:0)]
  XCTAssertThrowsError(try PrimalContactIP.solve(factor:factor,base:[-1],border:[],contacts:contacts))
 }
 func testCapsAndNonfiniteFailClosed() throws {
  var system=try RopeBandedSystem(size:1,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:1)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let c=RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-0.001)
  XCTAssertThrowsError(try PrimalContactIP.solve(factor:factor,base:[0],border:[],contacts:[c],maxIterations:0))
  XCTAssertThrowsError(try PrimalContactIP.solve(factor:factor,base:[Double.nan],border:[],contacts:[c]))
 }
 func testChangedWeightsKeepBothLoopsAndHeightCoupled() throws {
  var system=try RopeBandedSystem(size:2,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:2)
  try system.addSymmetric(row:1,column:1,value:3)
  let factor=try system.primalPrepared(borderColumns:[[0,0]],borderMatrix:[[5]])
  let rows=[RopeLinearContact(indices:[0,1],coefficients:[-1,1],border:[0],residual:0),
   RopeLinearContact(indices:[0],coefficients:[1],border:[-1],residual:0)]
  let prepared=try SparseNewtonPrepared(factor:factor,contacts:rows,diagonal:[4,7])
  let first=try prepared.refined([1,2],[3])
  for (actual,want) in zip(first.base+first.border,[327.0/557,346.0/557,330.0/557]) {XCTAssertEqual(actual,want,accuracy:1e-12)}
  try prepared.refactor(diagonal:[1,2])
  let changed=try prepared.refined([1,2],[3])
  for (actual,want) in zip(changed.base+changed.border,[22.0/39,25.0/39,23.0/39]) {XCTAssertEqual(actual,want,accuracy:1e-12)}
 }
 func testChangingWeightsDoesNotAccumulatePriorContactCurvature() throws {
  var system=try RopeBandedSystem(size:1,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:2)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let row=RopeLinearContact(indices:[0],coefficients:[2],border:[],residual:0)
  let prepared=try SparseNewtonPrepared(factor:factor,contacts:[row],diagonal:[3])
  XCTAssertEqual(try prepared.refined([7],[]).base[0],0.5,accuracy:1e-12)
  try prepared.refactor(diagonal:[0.5])
  XCTAssertEqual(try prepared.refined([7],[]).base[0],1.75,accuracy:1e-12)
  try prepared.refactor(diagonal:[3])
  XCTAssertEqual(try prepared.refined([7],[]).base[0],0.5,accuracy:1e-12)
 }
 func testInvalidWeightUpdatePreservesLastValidSolve() throws {
  var system=try RopeBandedSystem(size:1,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:2)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let row=RopeLinearContact(indices:[0],coefficients:[2],border:[],residual:0)
  let prepared=try SparseNewtonPrepared(factor:factor,contacts:[row],diagonal:[3])
  for bad in [[],[0],[-1],[Double.nan],[Double.infinity]] {
   XCTAssertThrowsError(try prepared.refactor(diagonal:bad))
   XCTAssertEqual(try prepared.refined([7],[]).base[0],0.5,accuracy:1e-12)
  }
 }

 func testStreamFindsLateConstraintBeyondMaterializationLimit() throws {
  var system=try RopeBandedSystem(size:2,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:1)
  try system.addSymmetric(row:1,column:1,value:1)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let weak=RopeLinearContact(indices:[0,1],coefficients:[1,0],border:[],residual:-0.0004)
  let late=RopeLinearContact(indices:[0,1],coefficients:[-1,1],border:[],residual:0.0003)
  var visitedLate=0
  let stream=FrozenContactStream(count:100_001,row:{id in
   if id==100_000 {visitedLate += 1;return late};return weak
  })
  var biggest=0
  let answer=try StreamedContactAdmission.solve(factor:factor,base:[0,0],border:[],contacts:stream,
   observe:{_,count,_ in biggest=max(biggest,count)})
  XCTAssertEqual(answer.base[0],0.0004,accuracy:1e-10)
  XCTAssertEqual(answer.base[1],0.0001,accuracy:1e-10)
  XCTAssertEqual(answer.multipliers.count,100_001)
  XCTAssertGreaterThan(visitedLate,1)
  XCTAssertLessThanOrEqual(biggest,100_000)
  XCTAssertGreaterThanOrEqual(late.residual-answer.base[0]+answer.base[1],-1e-8)
 }
 func testStreamCertifiesContactResidualBelowPhysicalTolerance() throws {
  var system=try RopeBandedSystem(size:1,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:1)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let row=RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-5e-9)
  let stream=FrozenContactStream(count:1,row:{_ in row})
  let answer=try StreamedContactAdmission.solve(factor:factor,base:[0],border:[],contacts:stream)
  XCTAssertGreaterThanOrEqual(row.residual+answer.base[0]-1e-8*answer.multipliers[0],-1e-10)
  XCTAssertGreaterThanOrEqual(answer.base[0],4.9e-9)
 }

 func testPackedSourceCapturesEveryRowExactlyOnce() throws {
  var system=try RopeBandedSystem(size:2,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:1)
  try system.addSymmetric(row:1,column:1,value:1)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  var visits=[0,0]
  let rows=[RopeLinearContact(indices:[0,1],coefficients:[1,0],border:[],residual:-0.0004),
   RopeLinearContact(indices:[0,1],coefficients:[-1,1],border:[],residual:0.0003)]
  let source=FrozenContactStream(count:2,row:{visits[$0]+=1;return rows[$0]})
  let answer=try StreamedContactAdmission.solve(factor:factor,base:[0,0],border:[],contacts:source,packSource:true)
  XCTAssertEqual(answer.base[0],0.0004,accuracy:1e-10)
  XCTAssertEqual(answer.base[1],0.0001,accuracy:1e-10)
  XCTAssertEqual(visits,[1,1])
 }

 func testStreamRetainsIndependentLoopsAndBoardHeight() throws {
  var system=try RopeBandedSystem(size:2,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:2)
  try system.addSymmetric(row:1,column:1,value:3)
  let factor=try system.primalPrepared(borderColumns:[[0,0]],borderMatrix:[[5]])
  let rows=[RopeLinearContact(indices:[0,1],coefficients:[-1,1],border:[0],residual:-0.001),
   RopeLinearContact(indices:[0],coefficients:[1],border:[-1],residual:-0.00025)]
  let stream=FrozenContactStream(count:rows.count,row:{rows[$0]})
  let answer=try StreamedContactAdmission.solve(factor:factor,base:[0,0],border:[0],contacts:stream)
  for (actual,want) in zip(answer.base+answer.border,[-0.000175,0.000825,-0.000425]) {XCTAssertEqual(actual,want,accuracy:1e-10)}
 }
 func testClearMalformedRowCannotEscapeStreamValidation() throws {
  var system=try RopeBandedSystem(size:1,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:1)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let good=RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:1)
  let malformed=RopeLinearContact(indices:[1],coefficients:[1],border:[],residual:1)
  let stream=FrozenContactStream(count:100_001,row:{$0==100_000 ? malformed:good})
  XCTAssertThrowsError(try StreamedContactAdmission.solve(factor:factor,base:[0],border:[],contacts:stream))
 }
 func testStreamingDoesNotExpandTheWorkingQPBudget() throws {
  var system=try RopeBandedSystem(size:1,bandwidth:0)
  try system.addSymmetric(row:0,column:0,value:1)
  let factor=try system.primalPrepared(borderColumns:[],borderMatrix:[])
  let row=RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:1)
  let stream=FrozenContactStream(count:100_001,row:{_ in row})
  let seed=Dictionary(uniqueKeysWithValues:(0..<100_001).map{($0,0.0)})
  XCTAssertThrowsError(try StreamedContactAdmission.solve(factor:factor,base:[0],border:[],contacts:stream,initialMultipliers:seed))
 }

}
let suite=PrimalTests.defaultTestSuite;suite.run()
guard let result=suite.testRun,result.executionCount==15,result.totalFailureCount==0 else {exit(1)}
