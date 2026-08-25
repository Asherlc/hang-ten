import XCTest
@testable import HangTen

final class HoldPathEngineTests: XCTestCase {

    private func parse(_ string: String) -> [BoardPathCommand] {
        let arity: [String: Int] = ["M": 1, "L": 1, "Q": 2, "C": 3, "Z": 0]
        var tokens = string.split(whereSeparator: { $0 == " " || $0 == "," }).map(String.init)
        var commands: [BoardPathCommand] = []
        while !tokens.isEmpty {
            let type = tokens.removeFirst()
            guard let pointCount = arity[type] else {
                fatalError("unexpected command \(type)")
            }
            var points: [CGPoint] = []
            for _ in 0..<pointCount {
                let x = CGFloat(Double(tokens.removeFirst())!)
                let y = CGFloat(Double(tokens.removeFirst())!)
                points.append(CGPoint(x: x, y: y))
            }
            switch type {
            case "M":
                commands.append(.move(points[0]))
            case "L":
                commands.append(.line(points[0]))
            case "Q":
                commands.append(.quad(to: points[1], control: points[0]))
            case "C":
                commands.append(.curve(to: points[2], control1: points[0], control2: points[1]))
            default:
                commands.append(.close)
            }
        }
        return commands
    }

    private func serialize(_ commands: [BoardPathCommand]) -> String {
        func coordinate(_ value: CGFloat) -> String {
            let rounded = (value * 1e6).rounded() / 1e6
            if rounded == rounded.rounded() && abs(rounded) < 1e15 {
                return String(Int64(rounded))
            }
            return "\(rounded)"
        }
        var parts: [String] = []
        for command in commands {
            switch command {
            case .close:
                parts.append("Z")
            case .move(let point):
                parts.append(contentsOf: ["M", coordinate(point.x), coordinate(point.y)])
            case .line(let point):
                parts.append(contentsOf: ["L", coordinate(point.x), coordinate(point.y)])
            case .quad(let to, let control):
                parts.append(contentsOf: [
                    "Q", coordinate(control.x), coordinate(control.y),
                    coordinate(to.x), coordinate(to.y),
                ])
            case .curve(let to, let firstControl, let secondControl):
                parts.append(contentsOf: [
                    "C",
                    coordinate(firstControl.x), coordinate(firstControl.y),
                    coordinate(secondControl.x), coordinate(secondControl.y),
                    coordinate(to.x), coordinate(to.y),
                ])
            }
        }
        return parts.joined(separator: " ")
    }

    private func assertPoint(
        _ actual: CGPoint,
        _ expectedX: CGFloat,
        _ expectedY: CGFloat,
        accuracy: CGFloat = 1e-6,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(actual.x, expectedX, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(actual.y, expectedY, accuracy: accuracy, file: file, line: line)
    }

    private func assertBounds(
        _ actual: HoldPathBounds,
        _ minX: CGFloat,
        _ minY: CGFloat,
        _ maxX: CGFloat,
        _ maxY: CGFloat,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(actual.minX, minX, accuracy: 1e-6, file: file, line: line)
        XCTAssertEqual(actual.minY, minY, accuracy: 1e-6, file: file, line: line)
        XCTAssertEqual(actual.maxX, maxX, accuracy: 1e-6, file: file, line: line)
        XCTAssertEqual(actual.maxY, maxY, accuracy: 1e-6, file: file, line: line)
    }

    private func assertSVG(
        _ commands: [BoardPathCommand],
        _ expected: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(serialize(commands), expected, file: file, line: line)
    }

    func testBendableReplacesStraightSegmentWithIdenticalCubic() {
        var commands = parse("M 0 0 L 10 0 L 10 10 Z")

        XCTAssertEqual(HoldPathEngine.makeSegmentBendable(&commands, afterIndex: 0), true)
        assertSVG(commands, "M 0 0 C 3.333333 0 6.666667 0 10 0 L 10 10 Z")
        XCTAssertEqual(HoldPathEngine.makeSegmentBendable(&commands, afterIndex: 0), false)
    }

    func testBendSegmentToPointPullsMarkedCubicThroughPointer() {
        var commands = parse("M 10 10 C 16.666667 10 23.333333 10 30 10 L 30 30 L 10 30 Z")

        XCTAssertEqual(HoldPathEngine.bendSegmentToPoint(&commands, afterIndex: 0, point: CGPoint(x: 20, y: 18)), true)
        if case .curve(let end, let control1, let control2) = commands[1] {
            XCTAssertEqual(end, CGPoint(x: 30, y: 10))
            let expectedControl = CGPoint(
                x: (8 * 20.0 - 10.0 - 30.0) / 6,
                y: (8 * 18.0 - 10.0 - 10.0) / 6
            )
            XCTAssertEqual(control1.x, expectedControl.x, accuracy: 1e-9)
            XCTAssertEqual(control1.y, expectedControl.y, accuracy: 1e-9)
            XCTAssertEqual(control2, control1)
        } else {
            XCTFail("expected marked cubic")
        }
        XCTAssertEqual(commands[1].holdEndPoint, CGPoint(x: 30, y: 10))
        XCTAssertEqual(commands[0].holdEndPoint, CGPoint(x: 10, y: 10))
    }

    func testBendableConvertsClosingEdgeWhileRetainingOneFinalClose() {
        var commands = parse("M 0 0 L 10 0 L 10 10 Z")

        XCTAssertEqual(HoldPathEngine.makeSegmentBendable(&commands, afterIndex: 2), true)
        assertSVG(commands, "M 0 0 L 10 0 L 10 10 C 6.666667 6.666667 3.333333 3.333333 0 0 Z")
        XCTAssertEqual(commands.filter(\.isHoldMoveCommand).count, 1)
        XCTAssertEqual(commands.filter(\.isHoldCloseCommand).count, 1)
        XCTAssertTrue(commands.last!.isHoldCloseCommand)
    }

    func testStraightReplacesQuadraticAndCubicSegments() {
        for (path, expected) in [
            ("M 0 0 Q 5 10 10 0 L 10 10 Z", "M 0 0 L 10 0 L 10 10 Z"),
            ("M 0 0 C 2 10 8 10 10 0 L 10 10 Z", "M 0 0 L 10 0 L 10 10 Z"),
        ] {
            var commands = parse(path)

            XCTAssertEqual(HoldPathEngine.makeSegmentStraight(&commands, afterIndex: 0), true, path)
            assertSVG(commands, expected)
            XCTAssertEqual(HoldPathEngine.makeSegmentStraight(&commands, afterIndex: 0), false)
        }
    }

    func testStraightReplacesClosingCurveWhileRetainingOneFinalClose() {
        var commands = parse("M 0 0 L 10 0 L 10 10 Q 4 14 0 0 Z")

        XCTAssertEqual(HoldPathEngine.makeSegmentStraight(&commands, afterIndex: 2), true)
        assertSVG(commands, "M 0 0 L 10 0 L 10 10 L 0 0 Z")
        XCTAssertEqual(commands.filter(\.isHoldCloseCommand).count, 1)
        XCTAssertTrue(commands.last!.isHoldCloseCommand)
    }

    func testSnapPreservesStartWhileAligningEndpoint() {
        var horizontal = parse("M 0 0 L 10 5 L 20 10 Z")
        XCTAssertEqual(HoldPathEngine.snapSegmentHorizontal(&horizontal, afterIndex: 0), true)
        assertSVG(horizontal, "M 0 0 L 10 0 L 20 10 Z")

        var vertical = parse("M 0 0 L 10 5 L 20 10 Z")
        XCTAssertEqual(HoldPathEngine.snapSegmentVertical(&vertical, afterIndex: 0), true)
        assertSVG(vertical, "M 0 0 L 0 5 L 20 10 Z")
    }

    func testAxisSnapMaterializesAlignedClosingEdge() {
        var horizontal = parse("M 0 0 L 10 0 L 10 10 L 2 8 Z")
        XCTAssertEqual(HoldPathEngine.snapSegmentHorizontal(&horizontal, afterIndex: 3), true)
        assertSVG(horizontal, "M 0 0 L 10 0 L 10 10 L 2 8 L 0 8 Z")
        XCTAssertEqual(horizontal.filter(\.isHoldMoveCommand).count, 1)
        XCTAssertEqual(horizontal.filter(\.isHoldCloseCommand).count, 1)
        XCTAssertTrue(horizontal.last!.isHoldCloseCommand)

        var vertical = parse("M 0 0 L 10 0 L 10 10 L 2 8 Z")
        XCTAssertEqual(HoldPathEngine.snapSegmentVertical(&vertical, afterIndex: 3), true)
        assertSVG(vertical, "M 0 0 L 10 0 L 10 10 L 2 8 L 2 0 Z")
        XCTAssertTrue(vertical.last!.isHoldCloseCommand)
    }

    func testAxisSnappingLeavesCurvesAndAlignedSegmentsUnchanged() {
        for (snap, path) in [
            (HoldPathEngine.snapSegmentHorizontal, "M 0 0 L 10 0 L 10 10 Z"),
            (HoldPathEngine.snapSegmentVertical, "M 0 0 L 0 10 L 10 10 Z"),
            (HoldPathEngine.snapSegmentHorizontal, "M 0 0 Q 5 10 10 0 L 10 10 Z"),
            (HoldPathEngine.snapSegmentVertical, "M 0 0 Q 5 10 10 0 L 10 10 Z"),
        ] {
            var commands = parse(path)

            XCTAssertEqual(snap(&commands, 0), false, path)
            assertSVG(commands, path)
        }
    }

    func testRoundVertexTrimsAdjacentStraightsAndKeepsSharpPointAsControl() {
        var commands = parse("M 0 0 L 10 0 L 10 10 L 0 10 Z")

        XCTAssertEqual(HoldPathEngine.roundVertex(&commands, index: 1), true)
        assertSVG(commands, "M 0 0 L 8 0 Q 10 0 10 2 L 10 10 L 0 10 Z")
    }

    func testRoundVertexRoundsFirstAndLastVerticesThroughClosingEdge() {
        var first = parse("M 0 0 L 10 0 L 10 10 L 0 10 Z")

        XCTAssertEqual(HoldPathEngine.roundVertex(&first, index: 0), true)
        assertSVG(first, "M 0 2 Q 0 0 2 0 L 10 0 L 10 10 L 0 10 Z")
        XCTAssertEqual(first.filter(\.isHoldMoveCommand).count, 1)
        XCTAssertEqual(first.filter(\.isHoldCloseCommand).count, 1)
        XCTAssertTrue(first.last!.isHoldCloseCommand)

        var last = parse("M 0 0 L 10 0 L 10 10 L 0 10 Z")

        XCTAssertEqual(HoldPathEngine.roundVertex(&last, index: 3), true)
        assertSVG(last, "M 0 0 L 10 0 L 10 10 L 2 10 Q 0 10 0 8 Z")
        XCTAssertEqual(last.filter(\.isHoldMoveCommand).count, 1)
        XCTAssertEqual(last.filter(\.isHoldCloseCommand).count, 1)
        XCTAssertTrue(last.last!.isHoldCloseCommand)
    }

    func testRoundVertexLeavesDegenerateAndCurvedVerticesUnchanged() {
        for (path, index) in [
            ("M 0 0 L 10 0 L 20 0 Z", 1),
            ("M 0 0 Q 5 0 10 0 L 10 10 Z", 1),
        ] {
            var commands = parse(path)

            XCTAssertEqual(HoldPathEngine.roundVertex(&commands, index: index), false, path)
            assertSVG(commands, path)
        }
    }

    func testOutlinePresetGenerationMatchesWorkbenchSerialization() throws {
        let source = parse("M 10 20 L 50 20 L 50 40 L 10 40 Z")
        let expectedPaths: [OutlinePreset: String] = [
            .oval: "M 30 20 C 41.045695 20 50 24.477153 50 30 C 50 35.522847 41.045695 40 30 40 C 18.954305 40 10 35.522847 10 30 C 10 24.477153 18.954305 20 30 20 Z",
            .circle: "M 30 20 C 35.522847 20 40 24.477153 40 30 C 40 35.522847 35.522847 40 30 40 C 24.477153 40 20 35.522847 20 30 C 20 24.477153 24.477153 20 30 20 Z",
            .pill: "M 20 20 L 40 20 C 45.522847 20 50 24.477153 50 30 C 50 35.522847 45.522847 40 40 40 L 20 40 C 14.477153 40 10 35.522847 10 30 C 10 24.477153 14.477153 20 20 20 Z",
            .roundedRectangle: "M 14 20 L 46 20 C 48.209139 20 50 21.790861 50 24 L 50 36 C 50 38.209139 48.209139 40 46 40 L 14 40 C 11.790861 40 10 38.209139 10 36 L 10 24 C 10 21.790861 11.790861 20 14 20 Z",
            .rectangle: "M 10 20 L 50 20 L 50 40 L 10 40 Z",
        ]
        for (preset, expected) in expectedPaths {
            let generated = try HoldPathEngine.createOutlineShapePath(of: source, preset: preset)
            assertSVG(generated, expected, file: #filePath, line: #line)
            XCTAssertTrue(generated.last!.isHoldCloseCommand)
            try HoldPathEngine.validateEditableContour(generated)
        }
    }

    func testOutlineVerticalPillInsideSourceBounds() throws {
        let source = parse("M 10 10 L 30 10 L 30 70 L 10 70 Z")

        let generated = try HoldPathEngine.createOutlineShapePath(of: source, preset: .pill)

        assertSVG(
            generated,
            "M 10 20 L 10 60 C 10 65.522847 14.477153 70 20 70 C 25.522847 70 30 65.522847 30 60 L 30 20 C 30 14.477153 25.522847 10 20 10 C 14.477153 10 10 14.477153 10 20 Z"
        )
    }

    func testOutlineUsesTrueQuadraticExtremaInsteadOfControlPoint() throws {
        let source = parse("M 0 0 Q 100 100 200 0 L 200 40 L 0 40 Z")

        let generated = try HoldPathEngine.createOutlineShapePath(of: source, preset: .oval)

        assertSVG(
            generated,
            "M 100 0 C 155.228475 0 200 11.192881 200 25 C 200 38.807119 155.228475 50 100 50 C 44.771525 50 0 38.807119 0 25 C 0 11.192881 44.771525 0 100 0 Z"
        )
    }

    func testOutlineUsesTrueCubicExtremaInsteadOfControlPoints() throws {
        let source = parse("M 0 0 C 0 120 200 120 200 0 L 200 60 L 0 60 Z")

        let generated = try HoldPathEngine.createOutlineShapePath(of: source, preset: .oval)

        assertSVG(
            generated,
            "M 100 0 C 155.228475 0 200 20.147186 200 45 C 200 69.852814 155.228475 90 100 90 C 44.771525 90 0 69.852814 0 45 C 0 20.147186 44.771525 0 100 0 Z"
        )
    }

    func testConstrainedModelExposesUnrotatedRectangleHandles() throws {
        let model = try HoldPathEngine.constrainedOutlineModel(
            commands: parse("M 10 20 L 50 20 L 50 40 L 10 40 Z"),
            constraint: ShapeConstraint(shape: .rectangle, rotationDegrees: 0)
        )

        assertPoint(model.center, 30, 30)
        XCTAssertEqual(model.rotationDegrees, 0)
        assertBounds(model.intrinsicBounds, 10, 20, 50, 40)
        XCTAssertEqual(model.handles.count, 8)
        for (handle, expected) in [
            ConstrainedHandle.nw: CGPoint(x: 10, y: 20),
            .n: CGPoint(x: 30, y: 20),
            .ne: CGPoint(x: 50, y: 20),
            .e: CGPoint(x: 50, y: 30),
            .se: CGPoint(x: 50, y: 40),
            .s: CGPoint(x: 30, y: 40),
            .sw: CGPoint(x: 10, y: 40),
            .w: CGPoint(x: 10, y: 30),
        ] {
            XCTAssertEqual(model.handles[handle], expected, "\(handle)")
        }
    }

    func testConstrainedModelInverseRotatesRectangleAndMapsHandlesToWorld() throws {
        let model = try HoldPathEngine.constrainedOutlineModel(
            commands: parse("M 40 10 L 40 50 L 20 50 L 20 10 Z"),
            constraint: ShapeConstraint(shape: .rectangle, rotationDegrees: 90)
        )

        assertPoint(model.center, 30, 30)
        XCTAssertEqual(model.rotationDegrees, 90)
        assertBounds(model.intrinsicBounds, 10, 20, 50, 40)
        for (handle, expected) in [
            ConstrainedHandle.nw: CGPoint(x: 40, y: 10),
            .n: CGPoint(x: 40, y: 30),
            .ne: CGPoint(x: 40, y: 50),
            .e: CGPoint(x: 30, y: 50),
            .se: CGPoint(x: 20, y: 50),
            .s: CGPoint(x: 20, y: 30),
            .sw: CGPoint(x: 20, y: 10),
            .w: CGPoint(x: 30, y: 10),
        ] {
            assertPoint(model.handles[handle] ?? .zero, expected.x, expected.y)
        }
    }

    func testConstrainedModelRejectsRotationsOutsideNormalizedRange() {
        for rotationDegrees in [-181.0, 180.0, 450.0] {
            XCTAssertThrowsError(
                try HoldPathEngine.constrainedOutlineModel(
                    commands: parse("M 10 20 L 50 20 L 50 40 L 10 40 Z"),
                    constraint: ShapeConstraint(shape: .rectangle, rotationDegrees: rotationDegrees)
                ),
                "\(rotationDegrees)"
            ) { error in
                XCTAssertEqual(
                    error as? HoldPathEngineError,
                    .shapeRotationMustBeNormalized,
                    "\(rotationDegrees)"
                )
            }
        }
    }

    func testConstrainedModelUsesTrueQuadraticAndCubicExtrema() throws {
        let quadratic = try HoldPathEngine.constrainedOutlineModel(
            commands: parse("M 0 0 Q 100 100 200 0 L 200 40 L 0 40 Z"),
            constraint: ShapeConstraint(shape: .rectangle, rotationDegrees: 0)
        )
        let cubic = try HoldPathEngine.constrainedOutlineModel(
            commands: parse("M 0 0 C 0 120 200 120 200 0 L 200 60 L 0 60 Z"),
            constraint: ShapeConstraint(shape: .rectangle, rotationDegrees: 0)
        )

        assertPoint(quadratic.center, 100, 25)
        assertBounds(quadratic.intrinsicBounds, 0, 0, 200, 50)
        assertPoint(cubic.center, 100, 45)
        assertBounds(cubic.intrinsicBounds, 0, 0, 200, 90)
    }

    func testResizeSupportsEveryRectangleHandleWithFixedOppositeEdgeOrCorner() throws {
        let source = parse("M 0 0 L 10 0 L 10 8 L 0 8 Z")
        let constraint = ShapeConstraint(shape: .rectangle, rotationDegrees: 0)
        let cases: [(ConstrainedHandle, CGPoint, String)] = [
            (.nw, CGPoint(x: -2, y: -3), "M -2 -3 L 10 -3 L 10 8 L -2 8 Z"),
            (.n, CGPoint(x: 999, y: -3), "M 0 -3 L 10 -3 L 10 8 L 0 8 Z"),
            (.ne, CGPoint(x: 12, y: -3), "M 0 -3 L 12 -3 L 12 8 L 0 8 Z"),
            (.e, CGPoint(x: 12, y: 999), "M 0 0 L 12 0 L 12 8 L 0 8 Z"),
            (.se, CGPoint(x: 12, y: 11), "M 0 0 L 12 0 L 12 11 L 0 11 Z"),
            (.s, CGPoint(x: 999, y: 11), "M 0 0 L 10 0 L 10 11 L 0 11 Z"),
            (.sw, CGPoint(x: -2, y: 11), "M -2 0 L 10 0 L 10 11 L -2 11 Z"),
            (.w, CGPoint(x: -2, y: 999), "M -2 0 L 10 0 L 10 8 L -2 8 Z"),
        ]

        for (handle, pointer, expectedPath) in cases {
            let resized = try HoldPathEngine.resizeConstrainedOutline(
                commands: source,
                constraint: constraint,
                handle: handle,
                pointer: pointer
            )
            assertSVG(resized.commands, expectedPath, file: #filePath, line: #line)
            XCTAssertEqual(resized.shapeConstraint, constraint)
        }
    }

    func testResizeClampsDraggedRectangleAxesWithoutFlipping() throws {
        let source = parse("M 0 0 L 10 0 L 10 8 L 0 8 Z")
        let constraint = ShapeConstraint(shape: .rectangle, rotationDegrees: 0)

        let inwardCorner = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: constraint,
            handle: .se,
            pointer: CGPoint(x: -10, y: -10)
        )
        assertSVG(inwardCorner.commands, "M 0 0 L 2 0 L 2 2 L 0 2 Z")

        let invertedSide = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: constraint,
            handle: .w,
            pointer: CGPoint(x: 20, y: 999)
        )
        assertSVG(invertedSide.commands, "M 8 0 L 10 0 L 10 8 L 8 8 Z")
    }

    func testResizeRegeneratesOvalWhenSideChangesOneIntrinsicDimension() throws {
        let source = parse(
            "M 5 0 C 7.761424 0 10 1.790861 10 4 C 10 6.209139 7.761424 8 5 8 C 2.238576 8 0 6.209139 0 4 C 0 1.790861 2.238576 0 5 0 Z"
        )

        let resized = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: ShapeConstraint(shape: .oval, rotationDegrees: 0),
            handle: .e,
            pointer: CGPoint(x: 14, y: 999)
        )

        assertSVG(
            resized.commands,
            "M 7 0 C 10.865993 0 14 1.790861 14 4 C 14 6.209139 10.865993 8 7 8 C 3.134007 8 0 6.209139 0 4 C 0 1.790861 3.134007 0 7 0 Z"
        )
    }

    func testResizeRotatesOvalInLocalAxesAndRotatesControlsBack() throws {
        let source = parse(
            "M 9 4 C 9 6.761424 7.209139 9 5 9 C 2.790861 9 1 6.761424 1 4 C 1 1.238576 2.790861 -1 5 -1 C 7.209139 -1 9 1.238576 9 4 Z"
        )

        let resized = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: ShapeConstraint(shape: .oval, rotationDegrees: 90),
            handle: .e,
            pointer: CGPoint(x: 5, y: 13)
        )

        assertSVG(
            resized.commands,
            "M 9 6 C 9 9.865993 7.209139 13 5 13 C 2.790861 13 1 9.865993 1 6 C 1 2.134007 2.790861 -1 5 -1 C 7.209139 -1 9 2.134007 9 6 Z"
        )
        XCTAssertEqual(resized.shapeConstraint, ShapeConstraint(shape: .oval, rotationDegrees: 90))
    }

    func testResizeKeepsCircleCornerDragsSquareAroundOppositeCorner() throws {
        let source = parse(
            "M 5 0 C 7.761424 0 10 2.238576 10 5 C 10 7.761424 7.761424 10 5 10 C 2.238576 10 0 7.761424 0 5 C 0 2.238576 2.238576 0 5 0 Z"
        )

        let resized = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: ShapeConstraint(shape: .circle, rotationDegrees: 0),
            handle: .se,
            pointer: CGPoint(x: 14, y: 12)
        )

        assertSVG(
            resized.commands,
            "M 7 0 C 10.865993 0 14 3.134007 14 7 C 14 10.865993 10.865993 14 7 14 C 3.134007 14 0 10.865993 0 7 C 0 3.134007 3.134007 0 7 0 Z"
        )
    }

    func testResizeKeepsCircleCenteredOnPerpendicularAxisDuringEdgeDrag() throws {
        let source = parse(
            "M 5 0 C 7.761424 0 10 2.238576 10 5 C 10 7.761424 7.761424 10 5 10 C 2.238576 10 0 7.761424 0 5 C 0 2.238576 2.238576 0 5 0 Z"
        )

        let resized = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: ShapeConstraint(shape: .circle, rotationDegrees: 0),
            handle: .e,
            pointer: CGPoint(x: 14, y: 999)
        )

        assertSVG(
            resized.commands,
            "M 7 -2 C 10.865993 -2 14 1.134007 14 5 C 14 8.865993 10.865993 12 7 12 C 3.134007 12 0 8.865993 0 5 C 0 1.134007 3.134007 -2 7 -2 Z"
        )
    }

    func testResizeClampsCircleDragsBeforeTheyInvert() throws {
        let source = parse(
            "M 5 0 C 7.761424 0 10 2.238576 10 5 C 10 7.761424 7.761424 10 5 10 C 2.238576 10 0 7.761424 0 5 C 0 2.238576 2.238576 0 5 0 Z"
        )
        let constraint = ShapeConstraint(shape: .circle, rotationDegrees: 0)

        let cornerClamp = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: constraint,
            handle: .nw,
            pointer: CGPoint(x: 9, y: 8)
        )
        assertSVG(
            cornerClamp.commands,
            "M 9 8 C 9.552285 8 10 8.447715 10 9 C 10 9.552285 9.552285 10 9 10 C 8.447715 10 8 9.552285 8 9 C 8 8.447715 8.447715 8 9 8 Z"
        )

        let edgeClamp = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: constraint,
            handle: .w,
            pointer: CGPoint(x: 20, y: 999)
        )
        assertSVG(
            edgeClamp.commands,
            "M 9 4 C 9.552285 4 10 4.447715 10 5 C 10 5.552285 9.552285 6 9 6 C 8.447715 6 8 5.552285 8 5 C 8 4.447715 8.447715 4 9 4 Z"
        )
    }

    func testResizeRegeneratesHorizontalAndVerticalPillsFromShorterDimension() throws {
        let horizontalSource = parse(
            "M 2 0 L 8 0 C 9.104569 0 10 0.895431 10 2 C 10 3.104569 9.104569 4 8 4 L 2 4 C 0.895431 4 0 3.104569 0 2 C 0 0.895431 0.895431 0 2 0 Z"
        )
        let horizontal = try HoldPathEngine.resizeConstrainedOutline(
            commands: horizontalSource,
            constraint: ShapeConstraint(shape: .pill, rotationDegrees: 0),
            handle: .e,
            pointer: CGPoint(x: 14, y: 999)
        )
        assertSVG(
            horizontal.commands,
            "M 2 0 L 12 0 C 13.104569 0 14 0.895431 14 2 C 14 3.104569 13.104569 4 12 4 L 2 4 C 0.895431 4 0 3.104569 0 2 C 0 0.895431 0.895431 0 2 0 Z"
        )

        let verticalSource = parse(
            "M 0 2 L 0 8 C 0 9.104569 0.895431 10 2 10 C 3.104569 10 4 9.104569 4 8 L 4 2 C 4 0.895431 3.104569 0 2 0 C 0.895431 0 0 0.895431 0 2 Z"
        )
        let vertical = try HoldPathEngine.resizeConstrainedOutline(
            commands: verticalSource,
            constraint: ShapeConstraint(shape: .pill, rotationDegrees: 0),
            handle: .s,
            pointer: CGPoint(x: 999, y: 14)
        )
        assertSVG(
            vertical.commands,
            "M 0 2 L 0 12 C 0 13.104569 0.895431 14 2 14 C 3.104569 14 4 13.104569 4 12 L 4 2 C 4 0.895431 3.104569 0 2 0 C 0.895431 0 0 0.895431 0 2 Z"
        )
    }

    func testResizeRejectsFinitePointerWhenInverseRotationOverflows() {
        XCTAssertThrowsError(
            try HoldPathEngine.resizeConstrainedOutline(
                commands: parse("M 5 -2.071068 L 12.071068 5 L 5 12.071068 L -2.071068 5 Z"),
                constraint: ShapeConstraint(shape: .rectangle, rotationDegrees: 45),
                handle: .e,
                pointer: CGPoint(x: CGFloat.greatestFiniteMagnitude, y: CGFloat.greatestFiniteMagnitude)
            )
        ) { error in
            XCTAssertEqual(error as? HoldPathEngineError, .constrainedResizeLocalPointerMustBeFinite)
        }
    }

    func testResizeRejectsFiniteLocalBoundsWhoseDerivedDimensionsOverflow() {
        let halfMaximum = CGFloat.greatestFiniteMagnitude / 2
        XCTAssertThrowsError(
            try HoldPathEngine.resizeConstrainedOutline(
                commands: parse(
                    "M \(-halfMaximum) 0 L \(halfMaximum) 0 L \(halfMaximum) 10 L \(-halfMaximum) 10 Z"
                ),
                constraint: ShapeConstraint(shape: .rectangle, rotationDegrees: 0),
                handle: .e,
                pointer: CGPoint(x: CGFloat.greatestFiniteMagnitude, y: 5)
            )
        ) { error in
            XCTAssertEqual(error as? HoldPathEngineError, .constrainedResizeDimensionsMustBeFinite)
        }
    }

    func testResizeEnforcesNormalizedSixCanvasPixelMinimum() throws {
        let canvasWidth: CGFloat = 1200
        let canvasHeight: CGFloat = 800
        let minimumWidth = CGFloat(6) / canvasWidth
        let minimumHeight = CGFloat(6) / canvasHeight
        let source = parse("M 0 0 L 0.5 0 L 0.5 0.5 L 0 0.5 Z")
        let constraint = ShapeConstraint(shape: .rectangle, rotationDegrees: 0)

        let clamped = try HoldPathEngine.resizeConstrainedOutline(
            commands: source,
            constraint: constraint,
            handle: .se,
            pointer: CGPoint(x: -1, y: -1),
            minimumWidth: minimumWidth,
            minimumHeight: minimumHeight
        )

        let bounds = clamped.commands.holdPathBounds()!
        XCTAssertGreaterThanOrEqual(bounds.width + 1e-9, minimumWidth)
        XCTAssertGreaterThanOrEqual(bounds.height + 1e-9, minimumHeight)
        XCTAssertEqual(bounds.width, minimumWidth, accuracy: 1e-12)
        XCTAssertEqual(bounds.height, minimumHeight, accuracy: 1e-12)
    }

    func testValidateEditableContourRejectsLoaderInvalidPaths() throws {
        XCTAssertThrowsError(try HoldPathEngine.validateEditableContour(parse("M 0 0 L 1 0 L 1 1")))

        var doubleMove = parse("M 0 0 L 1 0 L 1 1 Z")
        doubleMove[2] = .move(CGPoint(x: 1, y: 1))
        XCTAssertThrowsError(try HoldPathEngine.validateEditableContour(doubleMove))

        XCTAssertThrowsError(
            try HoldPathEngine.validateEditableContour(parse("M 0 0 L 1 0 L 1 0 Z"))
        ) { error in
            guard case BoardGeometryAdaptationError.invalid(let reason) = error else {
                return XCTFail("expected adaptation error")
            }
            XCTAssertTrue(reason.contains("at least three unique points"), reason)
        }

        var outOfFrame = parse("M 0 0 L 1 0 L 1 1 Z")
        outOfFrame[2] = .line(CGPoint(x: 1, y: 2))
        try HoldPathEngine.validateEditableContour(outOfFrame)
        XCTAssertThrowsError(try outOfFrame.pathCommandDocuments().holdPathCommands())

        try HoldPathEngine.validateEditableContour(parse("M 0 0 Q 0.5 1 1 0 L 1 1 L 0 1 Z"))
    }

    func testMoveVertexTranslatesAnchorsAndDependentControls() {
        var anchor = parse("M 0 0 L 50 50 Q 60 60 100 100 Z")
        HoldPathEngine.moveVertex(&anchor, index: 1, deltaX: 10, deltaY: 10)
        XCTAssertEqual(anchor[1].holdEndPoint, CGPoint(x: 60, y: 60))

        var quad = parse("M 0 0 L 10 10 Q 20 20 50 50 Z")
        HoldPathEngine.moveVertex(&quad, index: 2, deltaX: 5, deltaY: -5)
        XCTAssertEqual(quad[2].holdEndPoint, CGPoint(x: 55, y: 45))
        guard case .quad(_, let quadControl) = quad[2] else {
            return XCTFail("expected quad")
        }
        XCTAssertEqual(quadControl, CGPoint(x: 25, y: 15))

        var cubic = parse("M 0 0 L 10 10 C 20 20 30 30 50 50 Z")
        HoldPathEngine.moveVertex(&cubic, index: 2, deltaX: 5, deltaY: 5)
        XCTAssertEqual(cubic[2].holdEndPoint, CGPoint(x: 55, y: 55))
        guard case .curve(_, let firstControl, let secondControl) = cubic[2] else {
            return XCTFail("expected curve")
        }
        XCTAssertEqual(firstControl, CGPoint(x: 25, y: 25))
        XCTAssertEqual(secondControl, CGPoint(x: 35, y: 35))

        var start = parse("M 10 10 L 50 50 Z")
        HoldPathEngine.moveVertex(&start, index: 0, deltaX: 5, deltaY: 5)
        XCTAssertEqual(start[0].holdEndPoint, CGPoint(x: 15, y: 15))
    }

    func testAddVertexInsertsOnSegmentAfterAfterIndex() {
        var line = parse("M 0 0 L 100 0 L 100 100 Z")
        HoldPathEngine.addVertex(&line, afterIndex: 0, x: 50, y: 0)
        XCTAssertEqual(line.count, 5)
        XCTAssertEqual(line[1].holdEndPoint, CGPoint(x: 50, y: 0))
        XCTAssertEqual(line[2].holdEndPoint, CGPoint(x: 100, y: 0))
    }

    func testAddVertexSubdividesQuadraticAndCubicSegments() {
        var quad = parse("M 0 0 Q 50 100 100 0 Z")
        HoldPathEngine.addVertex(&quad, afterIndex: 0, x: 50, y: 50)
        XCTAssertEqual(quad.count, 4)
        XCTAssertEqual(quad[1].holdEndPoint, CGPoint(x: 50, y: 50))
        XCTAssertEqual(quad[2].holdEndPoint, CGPoint(x: 100, y: 0))

        var cubic = parse("M 0 0 C 25 100 75 100 100 0 Z")
        HoldPathEngine.addVertex(&cubic, afterIndex: 0, x: 50, y: 50)
        XCTAssertEqual(cubic.count, 4)
        if case .curve = cubic[1], case .curve = cubic[2] {} else {
            XCTFail("expected two cubic segments")
        }
    }

    func testAddVertexSubdividesAfterNonMoveCommandLeavingPrecedingSegmentUnchanged() {
        var quad = parse("M 0 0 L 20 0 Q 60 100 100 0 Z")
        HoldPathEngine.addVertex(&quad, afterIndex: 1, x: 60, y: 50)
        XCTAssertEqual(quad.count, 5)
        XCTAssertEqual(quad[1].holdEndPoint, CGPoint(x: 20, y: 0))
        XCTAssertEqual(quad[3].holdEndPoint, CGPoint(x: 100, y: 0))

        var cubic = parse("M 0 0 L 20 0 C 40 100 80 100 100 0 Z")
        HoldPathEngine.addVertex(&cubic, afterIndex: 1, x: 60, y: 50)
        XCTAssertEqual(cubic.count, 5)
        XCTAssertEqual(cubic[1].holdEndPoint, CGPoint(x: 20, y: 0))
        XCTAssertEqual(cubic[3].holdEndPoint, CGPoint(x: 100, y: 0))
    }

    func testInflectionPointSubdivisionAndDeletionRoundTrip() {
        let originalPath = "M 0 0 Q 100 100 100 0 L 0 100 Z"
        var commands = parse(originalPath)

        XCTAssertEqual(
            HoldPathEngine.addInflectionPoint(&commands, afterIndex: 0, point: CGPoint(x: 43.75, y: 37.5)),
            true
        )
        XCTAssertTrue(HoldPathEngine.isInflectionVertex(commands, index: 1))

        HoldPathEngine.deleteVertex(&commands, index: 1)
        assertSVG(commands, originalPath)
    }

    func testCubicInflectionPointSubdividesWithoutChangingCurve() {
        var commands = parse("M 0 0 C 0 100 100 100 100 0 L 0 100 Z")

        XCTAssertEqual(
            HoldPathEngine.addInflectionPoint(&commands, afterIndex: 0, point: CGPoint(x: 15.625, y: 56.25)),
            true
        )
        XCTAssertEqual(commands[1].holdEndPoint, CGPoint(x: 15.625, y: 56.25))
        guard case .curve(_, let firstControl, let secondControl) = commands[1] else {
            return XCTFail("expected curve")
        }
        assertPoint(firstControl, 0, 25)
        assertPoint(secondControl, 6.25, 43.75)
        guard case .curve(_, let rightFirstControl, let rightSecondControl) = commands[2] else {
            return XCTFail("expected curve")
        }
        assertPoint(rightFirstControl, 43.75, 93.75)
        assertPoint(rightSecondControl, 100, 75)
        XCTAssertTrue(HoldPathEngine.isInflectionVertex(commands, index: 1))
    }

    func testDraggedInflectionPointsRemainRemovableCurveVertices() {
        for (path, type) in [
            ("M 0 0 Q 100 100 100 0 L 0 100 Z", "Q"),
            ("M 0 0 C 0 100 100 100 100 0 L 0 100 Z", "C"),
        ] {
            var commands = parse(path)
            XCTAssertEqual(
                HoldPathEngine.addInflectionPoint(&commands, afterIndex: 0, point: CGPoint(x: 43.75, y: 37.5)),
                true,
                path
            )
            HoldPathEngine.moveVertex(&commands, index: 1, deltaX: 8, deltaY: -5)

            XCTAssertTrue(
                HoldPathEngine.isInflectionVertex(commands, index: 1),
                "\(type) inflection point is removable after dragging"
            )
            HoldPathEngine.deleteVertex(&commands, index: 1)
            switch commands[1] {
            case .quad:
                XCTAssertEqual(type, "Q")
            case .curve:
                XCTAssertEqual(type, "C")
            default:
                XCTFail("deletion keeps the segment bendable")
            }
        }
    }

    func testRemovingQuadraticInflectionNearOutgoingControlStaysFinite() throws {
        var commands = parse("M 0 0 Q 100 100 100 0 L 0 100 Z")

        XCTAssertEqual(
            HoldPathEngine.addInflectionPoint(&commands, afterIndex: 0, point: CGPoint(x: 75, y: 50)),
            true
        )
        HoldPathEngine.moveVertex(&commands, index: 1, deltaX: 25, deltaY: 0)
        XCTAssertTrue(HoldPathEngine.isInflectionVertex(commands, index: 1))
        HoldPathEngine.deleteVertex(&commands, index: 1)

        guard case .quad(_, let control) = commands[1] else {
            return XCTFail("expected quad")
        }
        XCTAssertTrue(control.x.isFinite && control.y.isFinite)
        try HoldPathEngine.validateEditableContour(commands)
    }

    func testRemovingCubicInflectionNearOutgoingControlStaysBounded() throws {
        var commands = parse("M 0 0 C 0 100 100 100 100 0 L 0 100 Z")

        XCTAssertEqual(
            HoldPathEngine.addInflectionPoint(&commands, afterIndex: 0, point: CGPoint(x: 50, y: 75)),
            true
        )
        HoldPathEngine.moveVertex(&commands, index: 1, deltaX: 24.999999999, deltaY: 0)
        XCTAssertTrue(HoldPathEngine.isInflectionVertex(commands, index: 1))
        HoldPathEngine.deleteVertex(&commands, index: 1)

        guard case .curve(_, let firstControl, let secondControl) = commands[1] else {
            return XCTFail("expected curve")
        }
        XCTAssertTrue(firstControl.x.isFinite && firstControl.y.isFinite)
        XCTAssertLessThanOrEqual(max(abs(firstControl.x), abs(firstControl.y)), 1_000)
        XCTAssertLessThanOrEqual(max(abs(secondControl.x), abs(secondControl.y)), 1_000)
        try HoldPathEngine.validateEditableContour(commands)
    }

    func testDeleteVertexRemovesVerticesAndConvertsAdjacentCurvesToLines() {
        var contour = parse("M 0 0 L 25 50 L 50 0 L 75 50 Z")
        HoldPathEngine.deleteVertex(&contour, index: 2)
        XCTAssertEqual(contour.count, 4)
        XCTAssertEqual(contour[2].holdEndPoint, CGPoint(x: 75, y: 50))

        var open = parse("M 0 0 L 25 50 L 50 0 L 75 50")
        HoldPathEngine.deleteVertex(&open, index: 2)
        assertSVG(open, "M 0 0 L 25 50 L 75 50")

        var betweenQuads = parse("M 0 0 Q 25 50 50 0 L 75 50 Q 100 100 125 0 Z")
        HoldPathEngine.deleteVertex(&betweenQuads, index: 2)
        XCTAssertEqual(betweenQuads.count, 4)
        if case .quad(let end, _) = betweenQuads[1] {
            XCTAssertEqual(end, CGPoint(x: 50, y: 0))
        } else {
            XCTFail("preceding curve untouched")
        }
        XCTAssertEqual(betweenQuads[2].holdEndPoint, CGPoint(x: 125, y: 0))
    }

    func testDeleteVertexRefusesNoninitialMoveAndTinyContours() {
        var multiContour = parse("M 0 0 L 25 0 L 25 25 Z M 50 50 L 75 50 L 75 75 Z")
        let original = serialize(multiContour)
        HoldPathEngine.deleteVertex(&multiContour, index: 4)
        XCTAssertEqual(serialize(multiContour), original)

        var triangle = parse("M 0 0 L 50 0 L 100 50 Z")
        HoldPathEngine.deleteVertex(&triangle, index: 2)
        XCTAssertEqual(serialize(triangle), "M 0 0 L 50 0 L 100 50 Z")

        var pair = parse("M 0 0 L 50 0 Z")
        HoldPathEngine.deleteVertex(&pair, index: 0)
        XCTAssertEqual(pair.count, 3)
    }

    func testDeleteVertexPromotesNextVertexToMoveWhenDeletingStart() {
        for (path, expected) in [
            ("M 0 0 L 50 0 L 100 50 L 0 50 Z", "M 50 0 L 100 50 L 0 50 Z"),
            ("M 0 0 Q 25 50 50 0 L 100 50 L 0 50 Z", "M 50 0 L 100 50 L 0 50 Z"),
            ("M 0 0 C 10 50 40 50 50 0 L 100 50 L 0 50 Z", "M 50 0 L 100 50 L 0 50 Z"),
        ] {
            var commands = parse(path)
            HoldPathEngine.deleteVertex(&commands, index: 0)
            assertSVG(commands, expected)
            XCTAssertEqual(commands.map { command -> String in
                switch command {
                case .move: "M"
                case .line: "L"
                case .quad: "Q"
                case .curve: "C"
                case .close: "Z"
                }
            }, ["M", "L", "L", "Z"])
        }
    }

    func testDeleteVertexBeforeCloseLeavesCurvedPreviousSegmentUntouched() {
        var commands = parse("M 0 0 L 20 20 Q 40 80 80 0 L 120 40 Z")
        HoldPathEngine.deleteVertex(&commands, index: 3)

        XCTAssertEqual(commands.count, 4)
        guard case .quad(let end, let control) = commands[2] else {
            return XCTFail("expected untouched quad")
        }
        XCTAssertEqual(end, CGPoint(x: 80, y: 0))
        XCTAssertEqual(control, CGPoint(x: 40, y: 80))
        XCTAssertTrue(commands[3].isHoldCloseCommand)
    }

    func testRotatePathRotatesAnchorsAndCarriesControls() {
        var anchors = parse("M 20 10 L 20 20 L 10 20 Z")
        HoldPathEngine.rotatePath(&anchors, angleRadians: .pi / 2, pivot: CGPoint(x: 10, y: 10))
        assertSVG(anchors, "M 10 20 L 0 20 L 0 10 Z")

        var curved = parse("M 10 10 Q 20 10 20 20 Z")
        HoldPathEngine.rotatePath(&curved, angleRadians: .pi / 2, pivot: CGPoint(x: 10, y: 10))
        guard case .quad(let end, let control) = curved[1] else {
            return XCTFail("expected quad")
        }
        XCTAssertEqual(control, CGPoint(x: 10, y: 20))
        XCTAssertEqual(end, CGPoint(x: 0, y: 20))

        var pivotPoint = parse("M 10 10 L 30 10 Z")
        HoldPathEngine.rotatePath(&pivotPoint, angleRadians: .pi / 4, pivot: CGPoint(x: 10, y: 10))
        XCTAssertEqual(pivotPoint[0].holdEndPoint, CGPoint(x: 10, y: 10))
    }
}

private extension Array where Element == BoardPathCommand {
    func holdPathBounds() -> HoldPathBounds? {
        try? HoldPathEngine.validBounds(of: self)
    }
}
