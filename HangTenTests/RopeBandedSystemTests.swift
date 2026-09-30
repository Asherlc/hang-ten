import XCTest
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeBandedSystemTests: XCTestCase {
    func testReusableFactorizationSupportsChangingLoadsAndImmutableCopies() throws {
        var system=try RopeBandedSystem(size:3,bandwidth:1)
        try system.addSymmetric(row:0,column:0,value:2)
        try system.addSymmetric(row:1,column:1,value:3)
        try system.addSymmetric(row:1,column:0,value:-1)
        try system.addSymmetric(row:2,column:1,value:1)
        let factor=try system.factorized(borderColumns:[[0,-2,1]],borderMatrix:[[4]])
        let copy=factor
        // Mutating the authoring matrix must not mutate an existing factor.
        try system.addSymmetric(row:0,column:0,value:100)
        for expected in [[0.1,0.2,0.3,0.4],[-0.2,0.7,-0.3,0.1],
                         [1e-6,-2e-6,4e-6,3e-6],[3,-5,2,-7],[0,0,0,0]] {
            let x=expected[0],y=expected[1],z=expected[2],height=expected[3]
            let rhs=[2*x-y,-x+3*y+z-2*height,y+height]
            let borderRHS=[-2*y+z+4*height]
            let result=try factor.solve(rhs:rhs,borderRHS:borderRHS)
            for (actual,wanted) in zip(result.base,expected.prefix(3)) {
                XCTAssertEqual(actual,wanted,accuracy:1e-12)
            }
            XCTAssertEqual(result.border[0],height,accuracy:1e-12)
            let repeatResult=try copy.solve(rhs:rhs,borderRHS:borderRHS)
            XCTAssertEqual(result.base,repeatResult.base)
            XCTAssertEqual(result.border,repeatResult.border)
        }
    }

    func testReusableFactorizationPreservesTwoCoupledBorders() throws {
        var system=try RopeBandedSystem(size:3,bandwidth:2)
        try system.addSymmetric(row:0,column:0,value:0.005)
        try system.addSymmetric(row:1,column:1,value:0.005)
        try system.addSymmetric(row:2,column:0,value:-1)
        try system.addSymmetric(row:2,column:1,value:1)
        let columns=[[0.0,0,-1],[1,-1,0]],matrix=[[1.0,0],[0,-1e-12]]
        let factor=try system.factorized(borderColumns:columns,borderMatrix:matrix)
        for expected in [[0.05,0.025,0.001,-0.003,0.002],[-0.2,0.1,-0.02,0.005,-0.007],
                         [1e-6,3e-6,-2e-6,4e-6,1e-6]] {
            let x=expected[0],y=expected[1],lambda=expected[2],height=expected[3],other=expected[4]
            let rhs=[0.005*x-lambda+other,0.005*y+lambda-other,-x+y-height]
            let borderRHS=[-lambda+height,x-y-1e-12*other]
            let cached=try factor.solve(rhs:rhs,borderRHS:borderRHS)
            let cold=try system.solve(rhs:rhs,borderColumns:columns,borderMatrix:matrix,borderRHS:borderRHS)
            for (a,b) in zip(cached.base+cached.border,cold.base+cold.border) {
                XCTAssertEqual(a,b,accuracy:1e-10)
            }
            for (a,b) in zip(cached.base+cached.border,expected) {XCTAssertEqual(a,b,accuracy:1e-10)}
        }
    }

    func testReusableFactorizationHandlesNoBorderAndFailsClosed() throws {
        var system=try RopeBandedSystem(size:2,bandwidth:0)
        try system.addSymmetric(row:0,column:0,value:2)
        try system.addSymmetric(row:1,column:1,value:3)
        let factor=try system.factorized(borderColumns:[],borderMatrix:[])
        XCTAssertEqual(try factor.solve(rhs:[4,-9],borderRHS:[]).base,[2,-3])
        XCTAssertThrowsError(try factor.solve(rhs:[1],borderRHS:[]))
        XCTAssertThrowsError(try factor.solve(rhs:[1,.nan],borderRHS:[]))
        XCTAssertThrowsError(try factor.solve(rhs:[1,2],borderRHS:[1]))
        XCTAssertThrowsError(try system.factorized(borderColumns:[[0]],borderMatrix:[[1]]))
        XCTAssertThrowsError(try system.factorized(borderColumns:[[0,0]],borderMatrix:[[.infinity]]))
        XCTAssertThrowsError(try system.factorized(borderColumns:[[0,0]],borderMatrix:[[0]]))
        let singular=try RopeBandedSystem(size:2,bandwidth:0)
        XCTAssertThrowsError(try singular.factorized(borderColumns:[],borderMatrix:[]))
    }

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
