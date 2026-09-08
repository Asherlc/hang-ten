import XCTest
@testable import HangTen

final class GripHandCueCardTests: XCTestCase {
    func testHandCueArtworkFacesTheBoardCenter() {
        XCTAssertEqual(GripCueSide.left.handArtworkMirrorScale, -1)
        XCTAssertEqual(GripCueSide.right.handArtworkMirrorScale, 1)
    }

    func testPocketCountDoesNotInventExactFingerHighlights() {
        for grip in GripType.allCases {
            let pose = GripHandPose(posture: grip, fingerConfiguration: nil)
            XCTAssertTrue(pose.highlightedFingers.isEmpty, "\(grip) must not imply exact fingers")
            XCTAssertFalse(pose.hasExplicitFingers)
        }
    }

    func testAllExplicitFingerCombinationsRemainExactAcrossEveryGrip() {
        for mask in 1..<16 {
            let selected = Set(FingerSlot.allCases.enumerated().compactMap { offset, finger in
                mask & (1 << offset) == 0 ? nil : finger
            })
            let configuration = FingerConfiguration(engagedFingers: selected)
            for grip in GripType.allCases {
                XCTAssertEqual(GripHandPose(posture: grip, fingerConfiguration: configuration).highlightedFingers, selected)
            }
        }
    }

    func testEveryPocketUsesExplicitFingerBitsWithoutInferringMembershipFromCount() {
        let cases: [(Set<FingerSlot>, String)] = [
            ([.index], "Pocket1"), ([.middle], "Pocket2"), ([.index, .middle], "Pocket3"),
            ([.ring], "Pocket4"), ([.index, .ring], "Pocket5"), ([.middle, .ring], "Pocket6"),
            ([.index, .middle, .ring], "Pocket7"), ([.pinky], "Pocket8"),
            ([.index, .pinky], "Pocket9"), ([.middle, .pinky], "Pocket10"),
            ([.index, .middle, .pinky], "Pocket11"), ([.ring, .pinky], "Pocket12"),
            ([.index, .ring, .pinky], "Pocket13"), ([.middle, .ring, .pinky], "Pocket14"),
            ([.index, .middle, .ring, .pinky], "Pocket15")
        ]
        for grip in [GripType.twoFingerPocket, .threeFingerPocket, .fourFingerPocket] {
            XCTAssertEqual(GripHandPose(posture: grip, fingerConfiguration: nil).action(), "Pocket0")
            for (fingers, expected) in cases {
                let pose = GripHandPose(posture: grip, fingerConfiguration: FingerConfiguration(engagedFingers: fingers))
                XCTAssertEqual(pose.action(), expected)
                XCTAssertEqual(pose.highlightedFingers, fingers)
            }
        }
    }

    func testPostureSelectionDoesNotChangeWithHighlights() {
        let cases: [(GripType?, String)] = [(nil, "Neutral"), (.openHand, "OpenHand"),
            (.halfCrimp, "HalfCrimp"), (.fullCrimp, "FullCrimp"), (.sloper, "Sloper")]
        for (grip, expected) in cases {
            XCTAssertEqual(GripHandPose(posture: grip, fingerConfiguration: nil).action(), expected)
            XCTAssertEqual(GripHandPose(posture: grip,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .pinky])).action(), expected)
        }
    }

    func testEvaluatedMeshLoaderAcceptsCompleteSchemaTwoFixture() throws {
        let data = try JSONSerialization.data(withJSONObject: validFixture())
        let asset = try GripHandAsset.decode(data)
        XCTAssertEqual(asset.vertexCount, 3)
    }

    func testBundledBlenderSurfacesHaveAllPosesAndDigits() throws {
        let asset = try GripHandAsset.bundled.get()
        try asset.validate()
        XCTAssertGreaterThan(asset.vertexCount, 1000)
        XCTAssertEqual(Set(asset.digitIndices), Set(0...5))
        for name in ["OpenHand", "HalfCrimp", "FullCrimp", "Sloper"] {
            XCTAssertNotEqual(asset.poses[name]?.positions, asset.poses["Neutral"]?.positions)
        }
        XCTAssertNotEqual(asset.poses["Pocket6"]?.positions, asset.poses["Pocket9"]?.positions)
    }

    func testMeshLoaderRejectsUnsupportedSchemaAndMissingPose() throws {
        try assertInvalidAsset { $0["schemaVersion"] = 1 }
        try assertInvalidAsset { object in
            var poses = try XCTUnwrap(object["poses"] as? [String: Any])
            poses.removeValue(forKey: "Pocket9")
            object["poses"] = poses
        }
    }

    func testMeshLoaderRejectsInvalidTriangleIndices() throws {
        try assertInvalidAsset { $0["indices"] = [3, 0, 1] }
        try assertInvalidAsset { $0["indices"] = [0, 1] }
        try assertInvalidAsset { $0["indices"] = [] }
    }

    func testMeshLoaderRejectsInconsistentPoseBuffersIncludingExtraPoses() throws {
        for name in ["HalfCrimp", "OptionalExtra"] {
            try assertInvalidAsset { object in
                var poses = try XCTUnwrap(object["poses"] as? [String: Any])
                poses[name] = ["positions": [0, 0, 0], "normals": [0, 0, 1]]
                object["poses"] = poses
            }
        }
        try assertInvalidAsset { object in
            var poses = try XCTUnwrap(object["poses"] as? [String: Any])
            poses["Neutral"] = ["positions": [0, 0], "normals": [0, 0]]
            object["poses"] = poses
        }
        try assertInvalidAsset { object in
            var poses = try XCTUnwrap(object["poses"] as? [String: Any])
            poses["Sloper"] = ["positions": [0, 0, 0, 1, 0, 0, 0, 1, 0], "normals": []]
            object["poses"] = poses
        }
    }

    func testMeshLoaderRejectsInvalidDigitAndHighlightBuffers() throws {
        try assertInvalidAsset { $0["digitIndices"] = [0, 1, 6] }
        try assertInvalidAsset { $0["digitIndices"] = [0, 1] }
        try assertInvalidAsset { $0["highlightWeights"] = [0, 1, 1.1] }
        try assertInvalidAsset { $0["highlightWeights"] = [0, -0.1, 1] }
        try assertInvalidAsset { $0["highlightWeights"] = [] }
    }

    func testMeshLoaderRejectsNonFiniteValuesAndMalformedJSON() throws {
        let data = try JSONSerialization.data(withJSONObject: validFixture())
        let text = try XCTUnwrap(String(data: data, encoding: .utf8))
        // JSON has no NaN literal; an overflowing exponent must also be rejected.
        let overflow = text.replacingOccurrences(of: "[0,0,0,1,0,0,0,1,0]",
                                                 with: "[1e100,0,0,1,0,0,0,1,0]")
        XCTAssertNotEqual(text, overflow)
        XCTAssertThrowsError(try GripHandAsset.decode(Data(overflow.utf8)))
        XCTAssertThrowsError(try GripHandAsset.decode(Data("{}".utf8)))
    }

    private func validFixture() -> [String: Any] {
        let surface = ["positions": [0, 0, 0, 1, 0, 0, 0, 1, 0],
                       "normals": [0, 0, 1, 0, 0, 1, 0, 0, 1]]
        let names = ["Neutral", "OpenHand", "HalfCrimp", "FullCrimp", "Sloper"]
            + (0...15).map { "Pocket\($0)" }
        return ["schemaVersion": 2, "indices": [0, 1, 2], "digitIndices": [0, 1, 2],
                "highlightWeights": [0, 0, 1],
                "poses": Dictionary(uniqueKeysWithValues: names.map { ($0, surface) })]
    }

    private func assertInvalidAsset(_ mutate: (inout [String: Any]) throws -> Void,
                                    file: StaticString = #filePath, line: UInt = #line) throws {
        var object = validFixture()
        try mutate(&object)
        let data = try JSONSerialization.data(withJSONObject: object)
        XCTAssertThrowsError(try GripHandAsset.decode(data), file: file, line: line)
    }
}
