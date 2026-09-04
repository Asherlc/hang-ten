import SwiftUI
import UIKit
import XCTest
@testable import HangTen

final class BoardRoutedCordRigGeometryTests: XCTestCase {
    func testQuarterTurnRotatesBodyKeepsWorldFixedAndPairsByScreenOrder() throws {
        let geometry = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: makeRig(),
                projection: BoardPresentationGeometryProjection(rotationDegrees: 90),
                in: CGRect(x: 0, y: 0, width: 400, height: 400)
            )
        )

        assertEqual(geometry.portPoints["body-left"], CGPoint(x: 140, y: 100))
        assertEqual(geometry.portPoints["body-right"], CGPoint(x: 140, y: 300))
        assertEqual(geometry.portPoints["world-left"], CGPoint(x: 110, y: 40))
        assertEqual(geometry.portPoints["world-right"], CGPoint(x: 290, y: 40))
        XCTAssertEqual(
            geometry.tensionSpans(in: .behindFace).map {
                "\($0.bodyPortID)->\($0.worldPortID)"
            },
            ["body-left->world-left", "body-right->world-right"]
        )
        XCTAssertEqual(geometry.authoredPaths(in: .behindFace).map(\.id), ["body-return"])
        XCTAssertEqual(geometry.authoredPaths(in: .aboveFace).map(\.id), ["world-bight"])
        XCTAssertTrue(geometry.authoredPaths(in: .overpass).isEmpty)
    }

    func testRenderableTensionPathsJoinEffectivelyCoincidentWorldEndpointsAtOneApex() throws {
        let template = makeRig()
        let rig = replacing(
            template,
            ports: template.ports.map { port in
                guard port.id == "world-left" || port.id == "world-right" else {
                    return port
                }
                return BoardRoutedCordPort(
                    id: port.id,
                    space: port.space,
                    point: BoardCordPoint(
                        x: port.id == "world-left" ? 150 : 150.00000001,
                        y: 0
                    )
                )
            },
            paths: []
        )
        let geometry = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: rig,
                projection: BoardPresentationGeometryProjection(rotationDegrees: 0),
                in: CGRect(x: 0, y: 0, width: 400, height: 400)
            )
        )

        let paths = geometry.renderableTensionPaths(in: .behindFace)
        XCTAssertEqual(paths.count, 1)
        let elements = pathElements(try XCTUnwrap(paths.first))
        XCTAssertEqual(elements.count, 3)
        guard case .move(let leftBody) = elements[0],
              case .line(let apex) = elements[1],
              case .line(let rightBody) = elements[2] else {
            return XCTFail("Coincident routed spans must form one joined V path")
        }
        assertEqual(leftBody, CGPoint(x: 100, y: 260))
        assertEqual(apex, CGPoint(x: 200.000000005, y: 40), accuracy: 1e-6)
        assertEqual(rightBody, CGPoint(x: 300, y: 260))
    }

    func testBodyRotationSupportsUprightHalfTurnAndArbitraryAngles() throws {
        let canvas = CGRect(x: 0, y: 0, width: 400, height: 400)
        let upright = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: makeRig(),
                projection: BoardPresentationGeometryProjection(rotationDegrees: 0),
                in: canvas
            )
        )
        let inverted = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: makeRig(),
                projection: BoardPresentationGeometryProjection(rotationDegrees: 180),
                in: canvas
            )
        )
        let angled = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: makeRig(),
                projection: BoardPresentationGeometryProjection(rotationDegrees: 45),
                in: canvas
            )
        )

        assertEqual(upright.portPoints["body-left"], CGPoint(x: 100, y: 260))
        assertEqual(inverted.portPoints["body-left"], CGPoint(x: 300, y: 140))
        assertEqual(
            angled.portPoints["body-left"],
            CGPoint(x: 86.8629150101524, y: 171.7157287525381),
            accuracy: 1e-9
        )
        for geometry in [upright, inverted, angled] {
            assertEqual(geometry.portPoints["world-left"], CGPoint(x: 110, y: 40))
        }
    }

    func testDeclaredPairingPreservesAuthoredListOrder() throws {
        let geometry = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: makeRig(pairing: .declared),
                projection: BoardPresentationGeometryProjection(rotationDegrees: 90),
                in: CGRect(x: 0, y: 0, width: 400, height: 400)
            )
        )

        XCTAssertEqual(
            geometry.spans.map { "\($0.bodyPortID)->\($0.worldPortID)" },
            ["body-right->world-right", "body-left->world-left"]
        )
    }

    func testScreenOrderUsesDeclarationIndexToBreakExactCoordinateTies() throws {
        let template = makeRig()
        let rig = replacing(
            template,
            ports: [
                BoardRoutedCordPort(
                    id: "body-z",
                    space: .body,
                    point: BoardCordPoint(x: 150, y: 220)
                ),
                BoardRoutedCordPort(
                    id: "body-a",
                    space: .body,
                    point: BoardCordPoint(x: 150, y: 220)
                ),
                BoardRoutedCordPort(
                    id: "world-z",
                    space: .world,
                    point: BoardCordPoint(x: 150, y: 0)
                ),
                BoardRoutedCordPort(
                    id: "world-a",
                    space: .world,
                    point: BoardCordPoint(x: 150, y: 0)
                ),
            ],
            tensionGroups: [
                BoardRoutedCordTensionGroup(
                    id: "ties",
                    bodyPortIDs: ["body-z", "body-a"],
                    worldPortIDs: ["world-z", "world-a"],
                    pairing: .screenOrder,
                    layer: .overpass
                ),
            ],
            paths: [],
            occlusions: []
        )
        let geometry = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: rig,
                projection: BoardPresentationGeometryProjection(rotationDegrees: 0),
                in: CGRect(x: 0, y: 0, width: 400, height: 400)
            )
        )

        XCTAssertEqual(
            geometry.spans.map { "\($0.bodyPortID)->\($0.worldPortID)" },
            ["body-z->world-z", "body-a->world-a"]
        )
    }

    func testBodyAndWorldPathCommandsUseTheirDeclaredCoordinateSpaces() throws {
        let geometry = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: makeRig(),
                projection: BoardPresentationGeometryProjection(rotationDegrees: 90),
                in: CGRect(x: 0, y: 0, width: 400, height: 400)
            )
        )

        XCTAssertEqual(
            pathElements(try XCTUnwrap(geometry.paths.first { $0.id == "body-return" }).path),
            [
                .move(CGPoint(x: 140, y: 100)),
                .quadCurve(CGPoint(x: 140, y: 300), CGPoint(x: 60, y: 200)),
            ]
        )
        XCTAssertEqual(
            pathElements(try XCTUnwrap(geometry.paths.first { $0.id == "world-bight" }).path),
            [
                .move(CGPoint(x: 110, y: 40)),
                .line(CGPoint(x: 290, y: 40)),
            ]
        )
    }

    func testOcclusionsRotateWithTheBodyAndRadialLipPointsTowardItsIncidentSpan() throws {
        let rig = replacing(
            makeRig(),
            occlusions: [
                .radialLip(
                    BoardRoutedCordRadialLip(
                        bodyPortID: "body-left",
                        radius: 20,
                        chordOffset: 5
                    )
                ),
                .facePatch(
                    BoardRoutedCordFacePatch(commands: [
                        .move(to: BoardCordPoint(x: 220, y: 180)),
                        .line(to: BoardCordPoint(x: 260, y: 180)),
                        .line(to: BoardCordPoint(x: 260, y: 220)),
                        .line(to: BoardCordPoint(x: 220, y: 220)),
                        .close,
                    ])
                ),
            ]
        )
        let geometry = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: rig,
                projection: BoardPresentationGeometryProjection(rotationDegrees: 90),
                in: CGRect(x: 0, y: 0, width: 400, height: 400)
            )
        )
        let lip = try XCTUnwrap(geometry.radialLips.first)

        XCTAssertEqual(lip.bodyPortID, "body-left")
        assertEqual(lip.center, CGPoint(x: 140, y: 100))
        assertEqual(lip.toward, CGPoint(x: 110, y: 40))
        XCTAssertEqual(lip.radius, 20)
        XCTAssertEqual(lip.chordOffset, 5)
        XCTAssertEqual(
            pathElements(try XCTUnwrap(geometry.facePatches.first).path),
            [
                .move(CGPoint(x: 180, y: 270)),
                .line(CGPoint(x: 180, y: 310)),
                .line(CGPoint(x: 140, y: 310)),
                .line(CGPoint(x: 140, y: 270)),
                .closeSubpath,
            ]
        )
    }

    func testPresentationValidationAcceptsGravitySafeSupportedRotations() {
        for degrees in [0.0, 45.0, 90.0, 180.0] {
            XCTAssertNil(
                BoardRoutedCordPresentationValidation.failure(
                    for: makeRig(),
                    rotationDegrees: degrees,
                    rotationAnchor: .center
                ),
                "expected \(degrees) degrees to be valid"
            )
        }
    }

    func testPresentationValidationRejectsNonUpwardTension() {
        let rig = replacing(
            makeRig(),
            ports: makeRig().ports.map { port in
                guard port.id == "world-left" else { return port }
                return BoardRoutedCordPort(
                    id: port.id,
                    space: port.space,
                    point: BoardCordPoint(x: 60, y: 220)
                )
            }
        )

        XCTAssertEqual(
            BoardRoutedCordPresentationValidation.failure(
                for: rig,
                rotationDegrees: 0,
                rotationAnchor: .center
            ),
            .bodyNotBelowWorld(bodyPortID: "body-left", worldPortID: "world-left")
        )
    }

    func testPresentationValidationAppliesStyleInsetToUsedPortsAndEveryPathPoint() {
        let portOutsideInset = replacing(
            makeRig(),
            ports: makeRig().ports.map { port in
                guard port.id == "world-left" else { return port }
                return BoardRoutedCordPort(
                    id: port.id,
                    space: port.space,
                    point: BoardCordPoint(x: -43, y: 0)
                )
            }
        )
        let pathControlOutsideInset = replacing(
            makeRig(),
            paths: [
                BoardRoutedCordPath(
                    id: "bad-control",
                    space: .world,
                    layer: .aboveFace,
                    commands: [
                        .move(to: BoardCordPoint(x: 60, y: 0)),
                        .quad(
                            control: BoardCordPoint(x: -43, y: 100),
                            to: BoardCordPoint(x: 240, y: 0)
                        ),
                    ]
                ),
            ]
        )

        for rig in [portOutsideInset, pathControlOutsideInset] {
            XCTAssertEqual(
                BoardRoutedCordPresentationValidation.failure(
                    for: rig,
                    rotationDegrees: 0,
                    rotationAnchor: .center
                ),
                .centerlineOutsideScene
            )
        }
    }

    func testPresentationValidationChecksFacePatchAndFullRadialLipBounds() {
        let patchOutside = replacing(
            makeRig(),
            occlusions: [
                .facePatch(
                    BoardRoutedCordFacePatch(commands: [
                        .move(to: BoardCordPoint(x: -51, y: 100)),
                        .line(to: BoardCordPoint(x: 0, y: 100)),
                        .line(to: BoardCordPoint(x: 0, y: 150)),
                        .close,
                    ])
                ),
            ]
        )
        let lipOutside = replacing(
            makeRig(),
            occlusions: [
                .radialLip(
                    BoardRoutedCordRadialLip(
                        bodyPortID: "body-left",
                        radius: 101,
                        chordOffset: 5
                    )
                ),
            ]
        )

        XCTAssertEqual(
            BoardRoutedCordPresentationValidation.failure(
                for: patchOutside,
                rotationDegrees: 0,
                rotationAnchor: .center
            ),
            .facePatchOutsideScene
        )
        XCTAssertEqual(
            BoardRoutedCordPresentationValidation.failure(
                for: lipOutside,
                rotationDegrees: 0,
                rotationAnchor: .center
            ),
            .radialLipOutsideScene
        )
    }

    @MainActor
    func testRoutedArtworkDrawsLayerOrderOcclusionAndVisibleBraidOnTransparency() throws {
        let rig = renderOrderRig()
        let canvas = CGRect(x: 0, y: 0, width: 200, height: 200)
        let geometry = try XCTUnwrap(
            BoardRoutedCordRigGeometry.resolve(
                rig: rig,
                projection: BoardPresentationGeometryProjection(rotationDegrees: 0),
                in: canvas
            )
        )
        let renderer = ImageRenderer(
            content: BoardRoutedPresentationArtwork(
                faceImage: solidFaceImage(),
                rig: rig,
                geometry: geometry
            )
            .frame(width: canvas.width, height: canvas.height)
        )
        renderer.scale = 1
        renderer.isOpaque = false
        let image = try XCTUnwrap(renderer.uiImage?.cgImage)
        let untouchedFace = pixelBytes(in: image, x: 80, y: 100)

        XCTAssertEqual(
            pixelBytes(in: image, x: 70, y: 100),
            untouchedFace,
            "behindFace cord must be covered by the opaque face"
        )
        XCTAssertNotEqual(
            pixelBytes(in: image, x: 100, y: 75),
            untouchedFace,
            "aboveFace cord must draw over the face"
        )
        XCTAssertEqual(
            pixelBytes(in: image, x: 100, y: 100),
            untouchedFace,
            "facePatch must redraw the face over an aboveFace cord"
        )
        XCTAssertNotEqual(
            pixelBytes(in: image, x: 130, y: 100),
            untouchedFace,
            "overpass cord must draw after face occlusions"
        )
        XCTAssertEqual(alphaByte(in: image, x: 0, y: 0), 0)

        let overpassColors = Set(
            stride(from: 35, through: 115, by: 2).map { y in
                pixelBytes(in: image, x: 130, y: y)
                    .map(String.init)
                    .joined(separator: ",")
            }
        )
        XCTAssertGreaterThan(
            overpassColors.count,
            2,
            "the routed style must render a visible two-color braided texture"
        )
    }

    @MainActor
    func testEditorArtworkRendersCanonicalAndAliasRoutedPresentationsOnTheScene() throws {
        let rig = renderOrderRig()
        var canonicalDocument = BoardEditorTestFixtures.sampleDocument()
        canonicalDocument.aspectRatio = 1
        canonicalDocument.presentations[0].aspectRatio = 1
        canonicalDocument.presentations[0].cordRig = .routed(rig)
        let canonicalPackage = editedPackage(document: canonicalDocument)

        let canonicalArtwork = BoardEditorCanvasArtwork.make(
            package: canonicalPackage,
            sourceImage: solidFaceImage()
        )

        XCTAssertEqual(canonicalArtwork.routedCordRig, rig)
        XCTAssertNil(canonicalArtwork.directTwoAnchorRig)
        XCTAssertEqual(canonicalArtwork.image.size, CGSize(width: 200, height: 200))
        XCTAssertEqual(
            alphaByte(in: try XCTUnwrap(canonicalArtwork.image.cgImage), x: 0, y: 0),
            0
        )

        var aliasDocument = canonicalDocument
        aliasDocument.presentations[0].isDefault = false
        aliasDocument.presentations.append(
            BoardEditablePresentation(
                id: "front-quarter-turn",
                name: "Front quarter turn",
                assetPath: "assets/primary.png",
                aspectRatio: 1,
                isDefault: true,
                sourcePresentationID: "front",
                rotationDegrees: 90
            )
        )
        let aliasArtwork = BoardEditorCanvasArtwork.make(
            package: editedPackage(document: aliasDocument),
            sourceImage: solidFaceImage()
        )

        XCTAssertEqual(aliasArtwork.routedCordRig, rig)
        XCTAssertEqual(aliasArtwork.sourcePresentationID, "front")
        XCTAssertEqual(aliasArtwork.image.size, CGSize(width: 200, height: 200))
        XCTAssertNotEqual(aliasArtwork.image.pngData(), canonicalArtwork.image.pngData())
    }

    private func makeRig(
        pairing: BoardRoutedCordPairing = .screenOrder
    ) -> BoardRoutedCordRig {
        BoardRoutedCordRig(
            sceneSize: BoardCordSize(width: 400, height: 400),
            sourceFrame: BoardCordRect(x: 50, y: 40, width: 300, height: 320),
            innerFaceFrame: BoardCordRect(x: 0, y: 60, width: 300, height: 200),
            style: BoardRoutedCordStyle(
                diameter: 10,
                outlineColor: "#101010",
                baseColor: "#2255AA",
                braidColors: ["#FFD000", "#0055CC"]
            ),
            ports: [
                BoardRoutedCordPort(
                    id: "body-left",
                    space: .body,
                    point: BoardCordPoint(x: 50, y: 220)
                ),
                BoardRoutedCordPort(
                    id: "body-right",
                    space: .body,
                    point: BoardCordPoint(x: 250, y: 220)
                ),
                BoardRoutedCordPort(
                    id: "world-left",
                    space: .world,
                    point: BoardCordPoint(x: 60, y: 0)
                ),
                BoardRoutedCordPort(
                    id: "world-right",
                    space: .world,
                    point: BoardCordPoint(x: 240, y: 0)
                ),
            ],
            tensionGroups: [
                BoardRoutedCordTensionGroup(
                    id: "main",
                    bodyPortIDs: ["body-right", "body-left"],
                    worldPortIDs: ["world-right", "world-left"],
                    pairing: pairing,
                    layer: .behindFace
                ),
            ],
            paths: [
                BoardRoutedCordPath(
                    id: "body-return",
                    space: .body,
                    layer: .behindFace,
                    commands: [
                        .move(to: BoardCordPoint(x: 50, y: 220)),
                        .quad(
                            control: BoardCordPoint(x: 150, y: 300),
                            to: BoardCordPoint(x: 250, y: 220)
                        ),
                    ]
                ),
                BoardRoutedCordPath(
                    id: "world-bight",
                    space: .world,
                    layer: .aboveFace,
                    commands: [
                        .move(to: BoardCordPoint(x: 60, y: 0)),
                        .line(to: BoardCordPoint(x: 240, y: 0)),
                    ]
                ),
            ],
            occlusions: []
        )
    }

    private func replacing(
        _ rig: BoardRoutedCordRig,
        ports: [BoardRoutedCordPort]? = nil,
        tensionGroups: [BoardRoutedCordTensionGroup]? = nil,
        paths: [BoardRoutedCordPath]? = nil,
        occlusions: [BoardRoutedCordOcclusion]? = nil
    ) -> BoardRoutedCordRig {
        BoardRoutedCordRig(
            sceneSize: rig.sceneSize,
            sourceFrame: rig.sourceFrame,
            innerFaceFrame: rig.innerFaceFrame,
            style: rig.style,
            ports: ports ?? rig.ports,
            tensionGroups: tensionGroups ?? rig.tensionGroups,
            paths: paths ?? rig.paths,
            occlusions: occlusions ?? rig.occlusions
        )
    }

    private func renderOrderRig() -> BoardRoutedCordRig {
        let ports: [(String, BoardRoutedCordSpace, CGFloat, CGFloat)] = [
            ("behind-body", .body, 20, 80),
            ("behind-world", .world, 20, -30),
            ("above-body", .body, 50, 80),
            ("above-world", .world, 50, -30),
            ("over-body", .body, 80, 80),
            ("over-world", .world, 80, -30),
        ]
        return BoardRoutedCordRig(
            sceneSize: BoardCordSize(width: 200, height: 200),
            sourceFrame: BoardCordRect(x: 50, y: 50, width: 100, height: 100),
            innerFaceFrame: BoardCordRect(x: 0, y: 0, width: 100, height: 100),
            style: BoardRoutedCordStyle(
                diameter: 10,
                outlineColor: "#220000",
                baseColor: "#0033CC",
                braidColors: ["#FFD000", "#00FFFF"]
            ),
            ports: ports.map {
                BoardRoutedCordPort(
                    id: $0.0,
                    space: $0.1,
                    point: BoardCordPoint(x: $0.2, y: $0.3)
                )
            },
            tensionGroups: [
                BoardRoutedCordTensionGroup(
                    id: "behind",
                    bodyPortIDs: ["behind-body"],
                    worldPortIDs: ["behind-world"],
                    pairing: .declared,
                    layer: .behindFace
                ),
                BoardRoutedCordTensionGroup(
                    id: "above",
                    bodyPortIDs: ["above-body"],
                    worldPortIDs: ["above-world"],
                    pairing: .declared,
                    layer: .aboveFace
                ),
                BoardRoutedCordTensionGroup(
                    id: "over",
                    bodyPortIDs: ["over-body"],
                    worldPortIDs: ["over-world"],
                    pairing: .declared,
                    layer: .overpass
                ),
            ],
            paths: [],
            occlusions: [
                .facePatch(
                    BoardRoutedCordFacePatch(commands: [
                        .move(to: BoardCordPoint(x: 43, y: 35)),
                        .line(to: BoardCordPoint(x: 57, y: 35)),
                        .line(to: BoardCordPoint(x: 57, y: 65)),
                        .line(to: BoardCordPoint(x: 43, y: 65)),
                        .close,
                    ])
                ),
            ]
        )
    }

    private func editedPackage(document: BoardEditableDocument) -> BoardEditedPackage {
        BoardEditedPackage(
            slug: "routed-fixture",
            packageURL: URL(fileURLWithPath: "/tmp/routed-fixture"),
            document: document,
            imageURL: URL(fileURLWithPath: "/tmp/routed-fixture/assets/primary.png"),
            pixelWidth: 100,
            pixelHeight: 100
        )
    }

    @MainActor
    private func solidFaceImage() -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = false
        return UIGraphicsImageRenderer(
            size: CGSize(width: 100, height: 100),
            format: format
        ).image { context in
            UIColor(red: 0, green: 1, blue: 0, alpha: 1).setFill()
            context.fill(CGRect(x: 0, y: 0, width: 100, height: 100))
        }
    }

    private func pixelBytes(in image: CGImage, x: Int, y: Int) -> [UInt8] {
        guard let providerData = image.dataProvider?.data,
              let bytes = CFDataGetBytePtr(providerData) else {
            return []
        }
        let bytesPerPixel = image.bitsPerPixel / 8
        let offset = y * image.bytesPerRow + x * bytesPerPixel
        return Array(UnsafeBufferPointer(start: bytes + offset, count: bytesPerPixel))
    }

    private func alphaByte(in image: CGImage, x: Int, y: Int) -> UInt8 {
        let bytes = pixelBytes(in: image, x: x, y: y)
        guard !bytes.isEmpty else { return 255 }
        let alphaOffset = image.alphaInfo == .first || image.alphaInfo == .premultipliedFirst
            ? 0
            : bytes.count - 1
        return bytes[alphaOffset]
    }

    private func assertEqual(
        _ actual: CGPoint?,
        _ expected: CGPoint,
        accuracy: CGFloat = 1e-9,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard let actual else {
            return XCTFail("Expected a resolved point", file: file, line: line)
        }
        XCTAssertEqual(actual.x, expected.x, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(actual.y, expected.y, accuracy: accuracy, file: file, line: line)
    }

    private func pathElements(_ path: Path) -> [RoutedPathElement] {
        var result: [RoutedPathElement] = []
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

private enum RoutedPathElement: Equatable {
    case move(CGPoint)
    case line(CGPoint)
    case quadCurve(CGPoint, CGPoint)
    case curve(CGPoint, CGPoint, CGPoint)
    case closeSubpath
}
