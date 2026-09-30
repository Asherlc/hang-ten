import XCTest
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeBandedSystemTests: XCTestCase {
    func testPivotedIndefiniteBandAndBoardBorder() throws {
        var system=try RopeBandedSystem(size:3,bandwidth:1)
        try system.addSymmetric(row:0,column:0,value:2)
        try system.addSymmetric(row:1,column:1,value:3)
        try system.addSymmetric(row:1,column:0,value:-1)
        try system.addSymmetric(row:2,column:1,value:1)
        let result=try system.solve(rhs:[0,0,0.6],borderColumns:[[0,-2,1]],borderMatrix:[[4]],borderRHS:[1.5])
        for (actual,expected) in zip(result.base,[0.1,0.2,0.3]) {XCTAssertEqual(actual,expected,accuracy:1e-12)}
        XCTAssertEqual(result.border[0],0.4,accuracy:1e-12)
    }

    func testTwoBordersCoupleAttachmentAndSelfContact() throws {
        var system=try RopeBandedSystem(size:3,bandwidth:2)
        try system.addSymmetric(row:0,column:0,value:0.005)
        try system.addSymmetric(row:1,column:1,value:0.005)
        try system.addSymmetric(row:2,column:0,value:-1)
        try system.addSymmetric(row:2,column:1,value:1)
        let result=try system.solve(rhs:[0.00125,-0.000875,-0.022],borderColumns:[[0,0,-1],[1,-1,0]],
            borderMatrix:[[1,0],[0,-1e-12]],borderRHS:[-0.004,0.025-2e-15])
        for (actual,expected) in zip(result.base,[0.05,0.025,0.001]) {XCTAssertEqual(actual,expected,accuracy:1e-10)}
        XCTAssertEqual(result.border[0],-0.003,accuracy:1e-10)
        XCTAssertEqual(result.border[1],0.002,accuracy:1e-10)
    }

    func testSingularityAndOutOfBandTermsFailClosed() throws {
        var system=try RopeBandedSystem(size:3,bandwidth:1)
        XCTAssertThrowsError(try system.addSymmetric(row:0,column:2,value:1))
        XCTAssertThrowsError(try system.solve(rhs:[0,0,0],borderColumns:[],borderMatrix:[],borderRHS:[]))
        XCTAssertThrowsError(try RopeBandedSystem(size:0,bandwidth:0))
        XCTAssertThrowsError(try system.solve(rhs:[0,0,0],
            borderColumns:Array(repeating:[0,0,0],count:257),
            borderMatrix:Array(repeating:Array(repeating:0,count:257),count:257),
            borderRHS:Array(repeating:0,count:257)))
    }

    func testSimultaneousContactBorderBeyondThirtyTwoRows() throws {
        var system=try RopeBandedSystem(size:3,bandwidth:0)
        for i in 0..<3 {try system.addSymmetric(row:i,column:i,value:2)}
        let count=40,expected=[0.2,-0.3,0.4]
        let expectedBorder=(0..<count).map{Double($0-20)*0.01}
        let columns=(0..<count).map{[Double($0+1)*0.001,0.002,-0.001]}
        var matrix=Array(repeating:Array(repeating:0.0,count:count),count:count)
        for i in 0..<count {matrix[i][i]=3}
        let rhs=(0..<3).map {axis in
            2*expected[axis]+(0..<count).reduce(0.0){$0+columns[$1][axis]*expectedBorder[$1]}
        }
        let borderRHS=(0..<count).map {i in
            zip(columns[i],expected).reduce(0.0){$0+$1.0*$1.1}+3*expectedBorder[i]
        }
        let result=try system.solve(rhs:rhs,borderColumns:columns,borderMatrix:matrix,borderRHS:borderRHS)
        for (actual,wanted) in zip(result.base,expected) {XCTAssertEqual(actual,wanted,accuracy:1e-11)}
        for (actual,wanted) in zip(result.border,expectedBorder) {XCTAssertEqual(actual,wanted,accuracy:1e-11)}
    }
}
