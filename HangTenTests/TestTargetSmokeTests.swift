import XCTest
@testable import HangTen

final class TestTargetSmokeTests: XCTestCase {
    func testUnitTestTargetLoadsTheHangTenModule() {
        XCTAssertEqual(1 + 1, 2)
    }
}
