import SwiftUI
import XCTest
@testable import HangTen

final class BoardCordRigGeometryTests: XCTestCase {
    private let portBackRig = BoardDirectTwoAnchorCordRig(
        sceneSize: BoardCordSize(width: 1200, height: 1464),
        sourceFrame: BoardCordRect(x: 0, y: 214, width: 1200, height: 1250),
        innerFaceFrame: BoardCordRect(x: -100, y: -10, width: 1400, height: 1400),
        attachmentPoints: [
            BoardCordPoint(x: 203, y: 712),
            BoardCordPoint(x: 997, y: 712),
        ],
        pullPoint: BoardCordPoint(x: 600, y: 71.5),
        eyeletRadius: 34
    )

    func testApprovedPortGeometryUsesClockFaceProjectionAndWorldUpSupport() {
        XCTAssertEqual(
            portBackRig.attachmentPoints.map(\.y).reduce(0, +) / 2 - portBackRig.pullPoint.y,
            640.5
        )
        XCTAssertEqual(640.5, 1.5 * 427)

        let canvas = CGRect(x: 0, y: 0, width: 1200, height: 1464)
        let anchor = BoardGeometryRotationAnchor(x: 0.5, y: 113.0 / 183.0)
        let uprightGeometry = BoardCordRigGeometry.make(
            rig: portBackRig,
            projection: BoardPresentationGeometryProjection(
                rotationDegrees: 0,
                rotationAnchor: anchor
            ),
            in: canvas
        )
        XCTAssertEqual(uprightGeometry.sceneRect, canvas)
        XCTAssertEqual(
            uprightGeometry.sourceRect,
            CGRect(x: 0, y: 214, width: 1200, height: 1250)
        )
        XCTAssertEqual(uprightGeometry.faceTransform, .identity)

        let ninetyGeometry = BoardCordRigGeometry.make(
            rig: portBackRig,
            projection: BoardPresentationGeometryProjection(
                rotationDegrees: 90,
                rotationAnchor: anchor
            ),
            in: canvas
        )
        XCTAssertEqual(
            ninetyGeometry.faceTransform,
            CGAffineTransform(a: 0, b: 1, c: -1, d: 0, tx: 1504, ty: 304)
        )
        assertEqual(ninetyGeometry.projectedAttachments[0], CGPoint(x: 578, y: 507))
        assertEqual(ninetyGeometry.projectedAttachments[1], CGPoint(x: 578, y: 1301))

        let invertedGeometry = BoardCordRigGeometry.make(
            rig: portBackRig,
            projection: BoardPresentationGeometryProjection(
                rotationDegrees: 180,
                rotationAnchor: anchor
            ),
            in: canvas
        )
        XCTAssertEqual(
            invertedGeometry.faceTransform,
            CGAffineTransform(a: -1, b: 0, c: 0, d: -1, tx: 1200, ty: 1808)
        )
        assertEqual(
            invertedGeometry.faceRect,
            CGRect(x: -100, y: 204, width: 1400, height: 1400)
        )
        assertEqual(
            invertedGeometry.projectedAttachments[0],
            CGPoint(x: 997, y: 882)
        )
        assertEqual(
            invertedGeometry.projectedAttachments[1],
            CGPoint(x: 203, y: 882)
        )
        assertEqual(
            invertedGeometry.pairedAttachments[0],
            CGPoint(x: 203, y: 882)
        )
        assertEqual(
            invertedGeometry.pairedAttachments[1],
            CGPoint(x: 997, y: 882)
        )
        assertEqual(invertedGeometry.strands[0].start, CGPoint(x: 578, y: 285.5))
        assertEqual(invertedGeometry.strands[1].start, CGPoint(x: 622, y: 285.5))
        XCTAssertTrue(canvas.contains(invertedGeometry.strokeBounds))
        XCTAssertEqual(invertedGeometry.eyeletForegroundCrescents.count, 2)
        XCTAssertTrue(
            uprightGeometry.eyeletForegroundCrescents[0].contains(
                CGPoint(x: 188, y: 952)
            )
        )
        XCTAssertFalse(
            uprightGeometry.eyeletForegroundCrescents[0].contains(
                CGPoint(x: 218, y: 900)
            )
        )
        XCTAssertEqual(
            uprightGeometry.supportPaths.map(pathElements),
            invertedGeometry.supportPaths.map(pathElements)
        )
        XCTAssertNotEqual(uprightGeometry.faceTransform, invertedGeometry.faceTransform)

        let twoSeventyGeometry = BoardCordRigGeometry.make(
            rig: portBackRig,
            projection: BoardPresentationGeometryProjection(
                rotationDegrees: 270,
                rotationAnchor: anchor
            ),
            in: canvas
        )
        XCTAssertEqual(
            twoSeventyGeometry.faceTransform,
            CGAffineTransform(a: 0, b: -1, c: 1, d: 0, tx: -304, ty: 1504)
        )
    }

    private func assertEqual(
        _ actual: CGPoint,
        _ expected: CGPoint,
        accuracy: CGFloat = 1e-9,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(actual.x, expected.x, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(actual.y, expected.y, accuracy: accuracy, file: file, line: line)
    }

    private func assertEqual(
        _ actual: CGRect,
        _ expected: CGRect,
        accuracy: CGFloat = 1e-9,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(actual.minX, expected.minX, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(actual.minY, expected.minY, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(actual.width, expected.width, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(actual.height, expected.height, accuracy: accuracy, file: file, line: line)
    }

    private func pathElements(_ path: Path) -> [PathElement] {
        var result: [PathElement] = []
        path.forEach { element in
            switch element {
            case .move(let point):
                result.append(.move(point))
            case .line(let point):
                result.append(.line(point))
            case .quadCurve(let point, let control):
                result.append(.quadCurve(point, control))
            case .curve(let point, let control1, let control2):
                result.append(.curve(point, control1, control2))
            case .closeSubpath:
                result.append(.closeSubpath)
            }
        }
        return result
    }
}

private enum PathElement: Equatable {
    case move(CGPoint)
    case line(CGPoint)
    case quadCurve(CGPoint, CGPoint)
    case curve(CGPoint, CGPoint, CGPoint)
    case closeSubpath
}
