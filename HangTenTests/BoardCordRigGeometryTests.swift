import SwiftUI
import XCTest
@testable import HangTen

final class BoardCordRigGeometryTests: XCTestCase {
    private let portFrontRig = BoardDirectTwoAnchorCordRig(
        sceneSize: BoardCordSize(width: 1200, height: 1464),
        sourceFrame: BoardCordRect(x: 0, y: 214, width: 1200, height: 1250),
        innerFaceFrame: BoardCordRect(x: -100, y: -10, width: 1400, height: 1400),
        attachmentPoints: [
            BoardCordPoint(x: 276, y: 804),
            BoardCordPoint(x: 920, y: 804),
        ],
        pullPoint: BoardCordPoint(x: 600, y: 71.5),
        eyeletRadius: 34
    )

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

    @MainActor
    func testZeroSizedRiggedArtworkCanvasTerminatesWithoutDrawingBraid() throws {
        let board = try XCTUnwrap(
            BoardCatalog.packageStore.board(id: "frictitious.port-a-board")
        )
        let presentation = try XCTUnwrap(board.presentation(id: "primary"))
        let renderer = ImageRenderer(
            content: BoardPresentationArtwork(
                board: board,
                presentation: presentation,
                projection: BoardPresentationGeometryProjection(
                    presentation: presentation
                ),
                canvasSize: .zero
            )
            .frame(width: 1, height: 1)
        )
        renderer.scale = 1
        renderer.isOpaque = false

        XCTAssertNotNil(renderer.uiImage)
    }

    @MainActor
    func testApprovedPortGeometryUsesClockFaceProjectionAndWorldUpSupport() throws {
        XCTAssertEqual(
            portFrontRig.attachmentPoints.map(\.y).reduce(0, +) / 2 - portFrontRig.pullPoint.y,
            732.5
        )
        XCTAssertEqual(portFrontRig.pullPoint.y, 71.5)

        let canvas = CGRect(x: 0, y: 0, width: 1200, height: 1464)
        let anchor = BoardGeometryRotationAnchor(x: 0.5, y: 113.0 / 183.0)
        let uprightGeometry = BoardCordRigGeometry.make(
            rig: portFrontRig,
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
            rig: portFrontRig,
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
        assertEqual(ninetyGeometry.projectedAttachments[0], CGPoint(x: 486, y: 580))
        assertEqual(ninetyGeometry.projectedAttachments[1], CGPoint(x: 486, y: 1224))

        let invertedGeometry = BoardCordRigGeometry.make(
            rig: portFrontRig,
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
            CGPoint(x: 924, y: 790)
        )
        assertEqual(
            invertedGeometry.projectedAttachments[1],
            CGPoint(x: 280, y: 790)
        )
        assertEqual(
            invertedGeometry.pairedAttachments[0],
            CGPoint(x: 280, y: 790)
        )
        assertEqual(
            invertedGeometry.pairedAttachments[1],
            CGPoint(x: 924, y: 790)
        )
        assertEqual(invertedGeometry.strands[0].start, CGPoint(x: 578, y: 285.5))
        assertEqual(invertedGeometry.strands[1].start, CGPoint(x: 622, y: 285.5))
        XCTAssertTrue(canvas.contains(invertedGeometry.strokeBounds))
        XCTAssertEqual(invertedGeometry.eyeletForegroundCrescents.count, 2)
        XCTAssertTrue(
            uprightGeometry.eyeletForegroundCrescents[0].contains(
                CGPoint(x: 261, y: 1044)
            )
        )
        XCTAssertFalse(
            uprightGeometry.eyeletForegroundCrescents[0].contains(
                CGPoint(x: 291, y: 992)
            )
        )
        XCTAssertEqual(
            uprightGeometry.supportPaths.map(pathElements),
            invertedGeometry.supportPaths.map(pathElements)
        )
        XCTAssertNotEqual(uprightGeometry.faceTransform, invertedGeometry.faceTransform)

        let twoSeventyGeometry = BoardCordRigGeometry.make(
            rig: portFrontRig,
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

        try writeReviewArtifactsIfRequested()
    }

    @MainActor
    private func writeReviewArtifactsIfRequested() throws {
        let board = try XCTUnwrap(
            BoardCatalog.packageStore.board(id: "frictitious.port-a-board")
        )
        XCTAssertNil(board.presentation(id: "cord-option-4-20mm-incut"))
        for presentationID in ["primary", "front-inverted"] {
            XCTAssertEqual(
                BoardCatalog.packageStore.presentationImageURL(
                    for: board,
                    presentationID: presentationID
                )?.lastPathComponent,
                "primary.png"
            )
        }
        let back = try XCTUnwrap(board.presentation(id: "back"))
        let backInverted = try XCTUnwrap(board.presentation(id: "back-inverted"))
        XCTAssertEqual(back.cordRig, .directTwoAnchor(portBackRig))
        XCTAssertNil(backInverted.cordRig)
        XCTAssertEqual(board.resolvedCordRig(for: backInverted), .directTwoAnchor(portBackRig))
        XCTAssertEqual(
            backInverted.geometryRotationAnchor,
            BoardGeometryRotationAnchor(x: 0.5, y: 113.0 / 183.0)
        )
        for presentationID in ["primary", "front-inverted", "back", "back-inverted"] {
            XCTAssertEqual(
                BoardCatalog.packageStore.presentationImageURL(
                    for: board,
                    presentationID: presentationID
                )?.lastPathComponent,
                "back.png"
            )
            XCTAssertEqual(
                BoardCatalog.packageStore.presentationArtworkImageURL(
                    for: board,
                    presentationID: presentationID
                )?.lastPathComponent,
                "back.png"
            )
        }
        let backURL = try XCTUnwrap(
            BoardCatalog.packageStore.presentationImageURL(
                for: board,
                presentationID: "back"
            )
        )
        XCTAssertFalse(
            FileManager.default.fileExists(
                atPath: backURL.deletingLastPathComponent()
                    .appendingPathComponent("back-inverted.png").path
            )
        )
        guard let directoryPath = ProcessInfo.processInfo.environment["HANGTEN_CORD_REVIEW_DIR"] else {
            return
        }

        let directory = URL(fileURLWithPath: directoryPath, isDirectory: true)
        try FileManager.default.createDirectory(
            at: directory,
            withIntermediateDirectories: true
        )

        for presentationID in ["back", "back-inverted"] {
            let presentation = try XCTUnwrap(board.presentation(id: presentationID))
            let canvasSize = CGSize(width: 1200, height: 1464)
            let renderer = ImageRenderer(
                content: BoardPresentationArtwork(
                    board: board,
                    presentation: presentation,
                    projection: BoardPresentationGeometryProjection(
                        presentation: presentation
                    ),
                    canvasSize: canvasSize
                )
                .frame(width: canvasSize.width, height: canvasSize.height)
            )
            renderer.scale = 1
            renderer.isOpaque = false

            let image = try XCTUnwrap(renderer.uiImage)
            XCTAssertEqual(image.size, canvasSize)
            let data = try XCTUnwrap(image.pngData())
            let decoded = try XCTUnwrap(UIImage(data: data)?.cgImage)
            XCTAssertEqual(decoded.width, 1200)
            XCTAssertEqual(decoded.height, 1464)
            assertTransparentCorners(in: decoded)
            try data.write(
                to: directory.appendingPathComponent("\(presentationID).png"),
                options: .atomic
            )
        }
    }

    private func assertTransparentCorners(
        in image: CGImage,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard let providerData = image.dataProvider?.data,
              let bytes = CFDataGetBytePtr(providerData) else {
            return XCTFail("Rendered image has no pixel data", file: file, line: line)
        }
        let bytesPerPixel = image.bitsPerPixel / 8
        let alphaOffset = image.alphaInfo == .first || image.alphaInfo == .premultipliedFirst
            ? 0
            : bytesPerPixel - 1
        for point in [
            CGPoint(x: 0, y: 0),
            CGPoint(x: image.width - 1, y: 0),
            CGPoint(x: 0, y: image.height - 1),
            CGPoint(x: image.width - 1, y: image.height - 1),
        ] {
            let offset = Int(point.y) * image.bytesPerRow
                + Int(point.x) * bytesPerPixel
                + alphaOffset
            XCTAssertEqual(bytes[offset], 0, file: file, line: line)
        }
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
