import Foundation
import XCTest
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopePhysicsDescriptorTests: XCTestCase {
    static let modelSHA = String(repeating: "a", count: 64)
    static var fixture: Data {
        let mesh: [String: Any] = ["vertices": [[0,0,0],[1,0,0],[0,1,0],[0,0,1]],
                                  "triangles": [[0,2,1],[0,1,3],[0,3,2],[1,2,3]]]
        let portals: [[String: Any]] = [("front", 0.045, 1), ("back", -0.045, -1)].map { name, z, sign in
            ["id": name, "center": [0,0,z], "normal": [0,0,Double(sign)],
             "boundary": [[-0.012,-0.013,z],[0.012,-0.013,z],[0.012,0.013,z],[-0.012,0.013,z]]]
        }
        let nodes: [[String: Any]] = [
            ["id":"start", "kind":"support", "point":[0,0.3,0]],
            ["id":"enter", "kind":"portal", "portalID":"front"],
            ["id":"exit", "kind":"portal", "portalID":"back"],
            ["id":"end", "kind":"support", "point":[0,0.3,0]]]
        let edges: [[String: Any]] = [
            ["from":"start","to":"enter","kind":"free","winding":"clockwise"],
            ["from":"enter","to":"exit","kind":"channel","channelID":"central"],
            ["from":"exit","to":"end","kind":"free","winding":"counterclockwise"]]
        let estimate: [String: Any] = ["value":1, "provenance":"displayEstimate"]
        let rope: [String: Any] = ["id":"sling", "baselineRadius":0.002,"thicknessScale":3,
            "radius":0.006,"restLength":0.55,"lengthProvenance":"displayEstimate",
            "linearMass":estimate,"nodes":nodes,"edges":edges]
        let channel: [String: Any] = ["id":"central","portalIDs":["front","back"],
            "spine":[[0,0,0.045],[0,0,-0.045]],"vertices":mesh["vertices"]!,"triangles":mesh["triangles"]!]
        let document: [String: Any] = ["schemaVersion":1,"sourceSHA256":String(repeating:"b", count:64),
            "modelSHA256":modelSHA,"coordinateSystem":"hang-ten-board-v1","collision":mesh,
            "portals":portals,"channels":[channel],"profiles":[["id":"front","presentationID":"front",
                "boardMass":estimate,"ropes":[rope]]]]
        return try! JSONSerialization.data(withJSONObject: document, options: [.sortedKeys])
    }

    func testValidGraphAndThickness() throws {
        let input = try RopePhysicsDescriptor.decode(Self.fixture).validated(modelSHA256: Self.modelSHA)
        XCTAssertEqual(input.profiles[0].ropes[0].radius, 0.006)
        XCTAssertEqual(input.profiles[0].ropes[0].restLength, 0.55)
        XCTAssertEqual(input.profiles[0].ropes[0].nodes[1].kind, "portal")
        XCTAssertNil(input.profiles[0].ropes[0].nodes[1].point)
    }

    func testOperatorSelectedSevenMillimeterDiameter() throws {
        let raw=String(decoding:Self.fixture,as:UTF8.self)
        let changed=raw.replacingOccurrences(of:"\"thicknessScale\":3",with:"\"thicknessScale\":1.75")
            .replacingOccurrences(of:"\"radius\":0.006",with:"\"radius\":0.0035")
        XCTAssertNotEqual(changed,raw)
        let input=try RopePhysicsDescriptor.decode(Data(changed.utf8)).validated(modelSHA256:Self.modelSHA)
        XCTAssertEqual(2*input.profiles[0].ropes[0].radius,0.007,accuracy:1e-12)
    }

    func testStaleHashAndUnknownMembers() throws {
        let descriptor = try RopePhysicsDescriptor.decode(Self.fixture)
        XCTAssertThrowsError(try descriptor.validated(modelSHA256: String(repeating:"c", count:64)))
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: Self.fixture) as? [String:Any])
        object["extra"] = true
        let data = try JSONSerialization.data(withJSONObject: object)
        XCTAssertThrowsError(try RopePhysicsDescriptor.decode(data).validated(modelSHA256: Self.modelSHA))
    }

    func testDuplicateMembersIncludingEscapedNames() {
        for raw in [#"{"schemaVersion":1,"schemaVersion":1}"#, #"{"schemaVersion":1,"\u0073chemaVersion":1}"#] {
            XCTAssertThrowsError(try RopePhysicsDescriptor.decode(Data(raw.utf8)))
        }
    }

    func testWrongDiameterAndImpossibleFit() throws {
        let raw = String(decoding: Self.fixture, as: UTF8.self)
        for changed in [raw.replacingOccurrences(of: "\"radius\":0.006", with: "\"radius\":0.002"),
                        raw.replacingOccurrences(of: "0.012", with: "0.0012")] {
            XCTAssertNotEqual(changed, raw)
            XCTAssertThrowsError(try RopePhysicsDescriptor.decode(Data(changed.utf8)).validated(modelSHA256: Self.modelSHA))
        }
    }

    func testInvalidTopologyAndMesh() throws {
        let raw = String(decoding: Self.fixture, as: UTF8.self)
        for changed in [raw.replacingOccurrences(of: "\"to\":\"enter\"", with: "\"to\":\"missing\""),
                        raw.replacingOccurrences(of: "\"channelID\":\"central\"", with: "\"channelID\":\"missing\""),
                        raw.replacingOccurrences(of: "[0,2,1]", with: "[0,2,9]"),
                        raw.replacingOccurrences(of: "hang-ten-board-v1", with: "native-mm"),
                        raw.replacingOccurrences(of: "\"restLength\":0.55", with: "\"restLength\":0"),
                        raw.replacingOccurrences(of: "\"baselineRadius\":0.002", with: "\"baselineRadius\":0"),
                        raw.replacingOccurrences(of: "\"radius\":0.006", with: "\"radius\":true"),
                        raw.replacingOccurrences(of: "\"radius\":0.006", with: "\"radius\":\"NaN\""),
                        raw.replacingOccurrences(of: "\"id\":\"exit\"", with: "\"id\":\"enter\""),
                        raw.replacingOccurrences(of: "\"provenance\":\"displayEstimate\"", with: "\"provenance\":\"\"")] {
            XCTAssertNotEqual(changed, raw)
            XCTAssertThrowsError(try RopePhysicsDescriptor.decode(Data(changed.utf8)).validated(modelSHA256: Self.modelSHA))
        }
    }
}
