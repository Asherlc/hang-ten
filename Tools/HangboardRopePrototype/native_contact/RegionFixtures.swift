import XCTest

final class RegionTests: XCTestCase {
    func prepared(_ rows: [RopeLinearContact], size: Int, border: Int = 0) throws -> PackedFrozenRows {
        try PackedFrozenRows(source: FrozenContactStream(count: rows.count, row: { rows[$0] }),
                             size: size, borderCount: border, equalities: [])
    }

    func testClearSourceAboveWorkingBudgetIsCertifiedTogether() throws {
        let rows = (0..<100_001).map { _ in
            RopeLinearContact(indices: [0,1], coefficients: [1,-1], border: [], residual: 0.001)
        }
        let regions = try AffineRegionCertificate(packed: prepared(rows, size: 2))
        XCTAssertEqual(try regions.discover([0,0], [], Array(repeating: 0, count: rows.count), []), [])
        XCTAssertEqual(regions.lastExactRows, 0)
        XCTAssertEqual(regions.lastCertifiedRows, rows.count)
    }

    func testLateOpposingFacetCannotBeHiddenByClearNeighbors() throws {
        var rows = (0..<256).map { _ in
            RopeLinearContact(indices: [0,1], coefficients: [1,0], border: [], residual: 0.001)
        }
        rows.append(RopeLinearContact(indices: [0,1], coefficients: [-1,1], border: [], residual: 0.0003))
        let packed = try prepared(rows, size: 2), regions = try AffineRegionCertificate(packed: packed)
        let x = [0.0004,0.0], mu = Array(repeating: 0.0, count: rows.count)
        XCTAssertEqual(try regions.discover(x, [], mu, []), [256])
        XCTAssertEqual(try regions.discover(x, [], mu, []), try packed.discover(x, [], mu, []))
        XCTAssertThrowsError(try regions.discover(x, [], mu, [256]))
    }

    func testInitiallyClearFacetsRemainCoupledToHeight() throws {
        let rows = (0..<64).map { i in
            RopeLinearContact(indices: [0], coefficients: [Double(i % 2)], border: [-1], residual: 0.0001)
        }
        let packed = try prepared(rows, size: 1, border: 1), regions = try AffineRegionCertificate(packed: packed)
        let mu = Array(repeating: 0.0, count: rows.count)
        XCTAssertEqual(try regions.discover([0], [0], mu, []), [])
        XCTAssertEqual(try regions.discover([0], [0.0002], mu, []), [0])
        XCTAssertEqual(try regions.discover([0], [0.0002], mu, []), try packed.discover([0], [0.0002], mu, []))
    }

    func testStrictThresholdCancellationAndRegularizationMatchFullScan() throws {
        let rows = [
            RopeLinearContact(indices: [0], coefficients: [1], border: [], residual: -1e-10.nextUp),
            RopeLinearContact(indices: [1,1,0], coefficients: [1e16,-1e16,1], border: [], residual: 0),
            RopeLinearContact(indices: [0], coefficients: [0], border: [], residual: -5e-9)
        ]
        let packed = try prepared(rows, size: 2), regions = try AffineRegionCertificate(packed: packed)
        for x in [[0.0,1], [-2e-10,1]] {
            for mu in [[0.0,0,0], [0,0,-1.0], [1e-13,0,0]] {
                XCTAssertEqual(try regions.discover(x, [], mu, []), try packed.discover(x, [], mu, []))
            }
        }
    }

    func testNonfiniteQueriesAndOverflowFailClosed() throws {
        let row = RopeLinearContact(indices: [0], coefficients: [1], border: [0], residual: 1)
        let regions = try AffineRegionCertificate(packed: prepared([row], size: 1, border: 1))
        XCTAssertThrowsError(try regions.discover([.nan], [0], [0], []))
        XCTAssertThrowsError(try regions.discover([0], [.infinity], [0], []))
        XCTAssertThrowsError(try regions.discover([0], [0], [.nan], []))
        XCTAssertThrowsError(try regions.discover([0], [0], [0], [1]))
        let huge = RopeLinearContact(indices: [0], coefficients: [.greatestFiniteMagnitude], border: [], residual: 1)
        let overflow = try AffineRegionCertificate(packed: prepared([huge], size: 1))
        XCTAssertThrowsError(try overflow.discover([4], [], [0], []))
        let hugeResidual = RopeLinearContact(indices: [], coefficients: [], border: [], residual: .greatestFiniteMagnitude)
        let dualOverflow = try AffineRegionCertificate(packed: prepared([hugeResidual], size: 1))
        XCTAssertThrowsError(try dualOverflow.discover([0], [], [-Double.greatestFiniteMagnitude], []))
    }

    func testMalformedClearRowCannotEscapeCaptureValidation() throws {
        let good = RopeLinearContact(indices: [0], coefficients: [1], border: [], residual: 1)
        let bad = RopeLinearContact(indices: [1], coefficients: [1], border: [], residual: 1)
        XCTAssertThrowsError(try AffineRegionCertificate(packed: prepared([good,bad], size: 1)))
    }

    func testDeterministicVariedNormalsMatchEveryBruteForceQuery() throws {
        var seed: UInt64 = 19
        func number() -> Double {
            seed = seed &* 6364136223846793005 &+ 1442695040888963407
            return Double(seed >> 11) / Double(UInt64.max >> 11) * 2 - 1
        }
        let rows = (0..<1024).map { i in
            RopeLinearContact(indices: i % 3 == 0 ? [0,1,0] : [0,1],
                coefficients: i % 3 == 0 ? [number(),number(),number()] : [number(),number()],
                border: [number()], residual: number()*0.001)
        }
        let packed = try prepared(rows, size: 2, border: 1), regions = try AffineRegionCertificate(packed: packed)
        for _ in 0..<100 {
            let x = [number()*0.002,number()*0.002], height = [number()*0.002]
            let mu = rows.map { _ in min(0,number())*0.001 }
            XCTAssertEqual(try regions.discover(x, height, mu, []), try packed.discover(x, height, mu, []))
        }
    }
}
let suite = RegionTests.defaultTestSuite; suite.run()
guard let result = suite.testRun, result.executionCount == 7, result.totalFailureCount == 0 else { exit(1) }
