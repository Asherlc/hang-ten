import XCTest
@testable import HangTen

final class BoardModelRealityTests: XCTestCase {
    func testRealityTypesCompile() {
        // This will fail until types exist
        let _ = BoardModelRealityScene.self
        let _ = BoardModelRealityLoader.self
    }
}