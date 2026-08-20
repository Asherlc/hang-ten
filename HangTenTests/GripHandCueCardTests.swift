import XCTest
@testable import HangTen

final class GripHandCueCardTests: XCTestCase {
    func testHandCueArtworkFacesTheBoardCenter() {
        XCTAssertEqual(GripCueSide.left.handArtworkMirrorScale, -1)
        XCTAssertEqual(GripCueSide.right.handArtworkMirrorScale, 1)
    }

    func testFingerCueUsesHandSpecificVisibleSlotOrder() {
        let configuration = FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])

        let left = GripHandCueCard(posture: nil, fingerConfiguration: configuration, side: .left)
        let right = GripHandCueCard(posture: nil, fingerConfiguration: configuration, side: .right)

        XCTAssertEqual(
            left.visibleFingerSlots,
            [.pinky, .ring, .middle, .index]
        )
        XCTAssertEqual(
            right.visibleFingerSlots,
            [.index, .middle, .ring, .pinky]
        )
        XCTAssertEqual(left.visibleFingerLabel, "P+R+M+I")
        XCTAssertEqual(right.visibleFingerLabel, "I+M+R+P")
    }
}
