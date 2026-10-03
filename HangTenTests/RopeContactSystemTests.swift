import XCTest
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeContactSystemTests: XCTestCase {
    func testImmovableViolatedContactsFailClosedWithColdAndWarmSets() throws {
        var system = try RopeBandedSystem(size: 1, bandwidth: 0)
        try system.addSymmetric(row: 0, column: 0, value: 1)
        let factor = try system.factorized(borderColumns: [], borderMatrix: [])
        for gradient in [0.0, 1e-12] {
            let contact = RopeLinearContact(indices: [0], coefficients: [gradient], border: [], residual: -0.001)
            for warm in [[:], [0: -1.0]] {
                XCTAssertThrowsError(try RopeContactSystem.solve(
                    factor: factor, base: [0], border: [], contacts: [contact], initialMultipliers: warm)) { error in
                    guard case RopeContactSystem.Failure.infeasible = error else {
                        return XCTFail("Expected infeasible immovable contact, got \(error)")
                    }
                }
            }
        }
    }

    func testIndependentCordAndBoardContactsShareOneMinimum() throws {
        var system=try RopeBandedSystem(size:2,bandwidth:0)
        try system.addSymmetric(row:0,column:0,value:2)
        try system.addSymmetric(row:1,column:1,value:3)
        let factor=try system.factorized(borderColumns:[[0,0]],borderMatrix:[[5]])
        let contacts=[RopeLinearContact(indices:[0,1],coefficients:[-1,1],border:[0],residual:-1),
                      RopeLinearContact(indices:[0],coefficients:[1],border:[-1],residual:-0.25)]
        let result=try RopeContactSystem.solve(factor:factor,base:[0,0],border:[0],contacts:contacts)
        XCTAssertEqual(result.base[0],-0.175,accuracy:1e-7)
        XCTAssertEqual(result.base[1],0.825,accuracy:1e-7)
        XCTAssertEqual(result.border[0],-0.425,accuracy:1e-7)
        XCTAssertEqual(Set(result.activeIDs),Set([0,1]))
        XCTAssertEqual(result.multipliers[0],-2.475,accuracy:1e-7)
        XCTAssertEqual(result.multipliers[1],-2.125,accuracy:1e-7)
        // Independent direct KKT reference: identical regularization and
        // both cord and height variables; this must preserve joint coupling.
        let cold=try system.solve(rhs:[0,0],borderColumns:[[0,0],[-1,1],[1,0]],
            borderMatrix:[[5,0,-1],[0,-1e-8,0],[-1,0,-1e-8]],borderRHS:[0,1,0.25])
        for (a,b) in zip(result.base+result.border,cold.base+[cold.border[0]]) {
            XCTAssertEqual(a,b,accuracy:1e-12)
        }
    }

    func testOmittedStrongerInequalityIsDiscoveredAndWeakerContactReleased() throws {
        var system=try RopeBandedSystem(size:1,bandwidth:0)
        try system.addSymmetric(row:0,column:0,value:1)
        let factor=try system.factorized(borderColumns:[],borderMatrix:[])
        let contacts=[RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-0.4),
                      RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-1),
                      RopeLinearContact(indices:[0],coefficients:[-1],border:[],residual:2)]
        let cold=try RopeContactSystem.solve(factor:factor,base:[0],border:[],contacts:contacts)
        let warm=try RopeContactSystem.solve(factor:factor,base:[0],border:[],contacts:contacts,
            initialMultipliers:[0:-0.4,2:-0.2])
        XCTAssertEqual(cold.base[0],1/(1+1e-8),accuracy:1e-12)
        XCTAssertEqual(warm.base[0],cold.base[0],accuracy:1e-12)
        XCTAssertEqual(warm.activeIDs,[1])
        XCTAssertEqual(warm.multipliers[0],0)
        XCTAssertEqual(warm.multipliers[2],0)
        XCTAssertLessThan(warm.multipliers[1],0)
        for row in contacts {XCTAssertGreaterThanOrEqual(row.residual+row.coefficients[0]*warm.base[0],-1.1e-8)}
    }

    func testEqualityBackboneAndChangedLoadsMatchDirectContactKKT() throws {
        var system=try RopeBandedSystem(size:3,bandwidth:2)
        try system.addSymmetric(row:0,column:0,value:0.005)
        try system.addSymmetric(row:1,column:1,value:0.005)
        try system.addSymmetric(row:2,column:0,value:-1)
        try system.addSymmetric(row:2,column:1,value:1)
        try system.addSymmetric(row:2,column:2,value:-1e-8)
        let factor=try system.factorized(borderColumns:[[0,0,-1]],borderMatrix:[[1]])
        for rhs in [[0.0,0,-0.022],[0.002,-0.001,-0.022]] {
            let base=try factor.solve(rhs:rhs,borderRHS:[-0.004])
            let contact=RopeLinearContact(indices:[0,1],coefficients:[1,-1],border:[0],residual:-0.03)
            let solved=try RopeContactSystem.solve(factor:factor,base:base.base,border:base.border,contacts:[contact])
            let reference=try system.solve(rhs:rhs,borderColumns:[[0,0,-1],[1,-1,0]],
                borderMatrix:[[1,0],[0,-1e-8]],borderRHS:[-0.004,0.03])
            for (a,b) in zip(solved.base+solved.border,reference.base+[reference.border[0]]) {
                XCTAssertEqual(a,b,accuracy:1e-10)
            }
            XCTAssertEqual(solved.multipliers[0],reference.border[1],accuracy:1e-10)
        }
    }

    func testDependentContactsStayFeasibleWithoutReusingChangedCoefficients() throws {
        var system=try RopeBandedSystem(size:2,bandwidth:0)
        for i in 0..<2 {try system.addSymmetric(row:i,column:i,value:1)}
        let factor=try system.factorized(borderColumns:[],borderMatrix:[])
        let contacts=[RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-1),
                      RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-1),
                      RopeLinearContact(indices:[0,1],coefficients:[1,1e-5],border:[],residual:-1.1)]
        let result=try RopeContactSystem.solve(factor:factor,base:[0,0],border:[],contacts:contacts,
            initialMultipliers:[0:-0.1,1:-0.1])
        for row in contacts {
            let value=zip(row.indices,row.coefficients).reduce(row.residual){$0+$1.1*result.base[$1.0]}
            XCTAssertGreaterThanOrEqual(value,-1.1e-8)
        }
        XCTAssertTrue(result.multipliers.allSatisfy{$0<=1e-12})
        let changed=[RopeLinearContact(indices:[1],coefficients:[1],border:[],residual:-0.5)]
        let next=try RopeContactSystem.solve(factor:factor,base:[0,0],border:[],contacts:changed)
        XCTAssertEqual(next.base[0],0)
        XCTAssertEqual(next.base[1],0.5/(1+1e-8),accuracy:1e-12)
    }

    func testScaledDependentContactsUseExplicitRegularizedKKTFallback() throws {
        var system=try RopeBandedSystem(size:1,bandwidth:0)
        try system.addSymmetric(row:0,column:0,value:0.005)
        let factor=try system.factorized(borderColumns:[],borderMatrix:[])
        let contacts=[RopeLinearContact(indices:[0],coefficients:[2000],border:[],residual:-0.002),
                      RopeLinearContact(indices:[0],coefficients:[1000],border:[],residual:-0.002)]
        var fallbackCalls=0
        let solved=try RopeContactSystem.solve(factor:factor,base:[0],border:[],contacts:contacts,fallback:{
            fallbackCalls += 1
            // The full KKT retains explicit regularization even while both
            // dependent inequalities are active; its tensile weak row releases.
            var both=try RopeBandedSystem(size:3,bandwidth:2)
            try both.addSymmetric(row:0,column:0,value:0.005)
            for i in 0..<2 {
                try both.addSymmetric(row:i+1,column:0,value:contacts[i].coefficients[0])
                try both.addSymmetric(row:i+1,column:i+1,value:-1e-8)
            }
            let trial=try both.factorized(borderColumns:[],borderMatrix:[]).solve(rhs:[0,0.002,0.002],borderRHS:[])
            XCTAssertGreaterThan(trial.base[1],0)
            XCTAssertLessThan(trial.base[2],0)
            var final=try RopeBandedSystem(size:2,bandwidth:1)
            try final.addSymmetric(row:0,column:0,value:0.005)
            try final.addSymmetric(row:1,column:0,value:1000)
            try final.addSymmetric(row:1,column:1,value:-1e-8)
            let solved=try final.factorized(borderColumns:[],borderMatrix:[]).solve(rhs:[0,0.002],borderRHS:[])
            let direct=(base:[solved.base[0]],border:[solved.base[1]])
            return RopeContactSystem.Solution(base:direct.base,border:[],multipliers:[0,direct.border[0]],activeIDs:[1])
        })
        XCTAssertEqual(fallbackCalls,1)
        XCTAssertEqual(solved.base[0],2e-6,accuracy:1e-15)
        XCTAssertLessThan(solved.multipliers[1],0)
        for row in contacts {XCTAssertGreaterThanOrEqual(row.residual+row.coefficients[0]*solved.base[0],-1e-8)}
    }

    func testMalformedOrNonfiniteContactSystemsFailClosed() throws {
        var system=try RopeBandedSystem(size:1,bandwidth:0)
        try system.addSymmetric(row:0,column:0,value:1)
        let factor=try system.factorized(borderColumns:[],borderMatrix:[])
        for row in [RopeLinearContact(indices:[1],coefficients:[1],border:[],residual:-1),
                    RopeLinearContact(indices:[0],coefficients:[],border:[],residual:-1),
                    RopeLinearContact(indices:[0],coefficients:[.nan],border:[],residual:-1),
                    RopeLinearContact(indices:[0],coefficients:[1],border:[1],residual:-1),
                    RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:.infinity)] {
            XCTAssertThrowsError(try RopeContactSystem.solve(factor:factor,base:[0],border:[],contacts:[row]))
        }
        let row=RopeLinearContact(indices:[0],coefficients:[1],border:[],residual:-1)
        XCTAssertThrowsError(try RopeContactSystem.solve(factor:factor,base:[0,0],border:[],contacts:[]))
        XCTAssertThrowsError(try RopeContactSystem.solve(factor:factor,base:[0],border:[0],contacts:[]))
        XCTAssertThrowsError(try RopeContactSystem.solve(factor:factor,base:[.nan],border:[],contacts:[row]))
        XCTAssertThrowsError(try RopeContactSystem.solve(factor:factor,base:[0],border:[],contacts:[row],initialMultipliers:[0:1]))
        XCTAssertThrowsError(try RopeContactSystem.solve(factor:factor,base:[0],border:[],contacts:[row],initialMultipliers:[1:-1]))
        XCTAssertThrowsError(try RopeContactSystem.solve(factor:factor,base:[0],border:[],contacts:[row],maxIterations:0))
    }
}
