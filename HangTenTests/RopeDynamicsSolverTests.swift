import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeDynamicsSolverTests: XCTestCase {
    private func attachedFixture(orientation: simd_quatd, translation: SIMD3<Double>, count: Int = 2, boardMass: Double = 1, leadLength: Double = 0.1)
        throws -> (RopePhysicsInput, RopeSimulationState, RopeTriangleCollider) {
        let locals = count == 1 ? [SIMD3<Double>(0, 0.02, 0.008)] :
            [SIMD3<Double>(-0.008, 0.02, 0.008), SIMD3<Double>(0.008, 0.02, 0.008)]
        let chains = locals.enumerated().map { index, local in
            let end = orientation.act(local) + translation, start = end + SIMD3<Double>(0, leadLength, 0)
            return RopeChainState(id: "lead-\(index)", radius: 0.001, linearMass: 0.01,
                restLengths: [leadLength], positions: [start, end], previousPositions: [start, end],
                velocities: [.zero, .zero], supports: [0: start], attachments: [1: local], portals: [:], channelSegments: [:])
        }
        let sources = chains.map { chain in
            RopePhysicsRope(id: chain.id, baselineRadius: chain.radius, radius: chain.radius,
                restLength: leadLength, linearMass: chain.linearMass,
                nodes: [RopeGraphNode(id: "start", kind: "support", point: chain.positions[0], portalID: nil),
                        RopeGraphNode(id: "end", kind: "attachment", point: chain.attachments[1], portalID: nil)],
                edges: [RopeGraphEdge(from: "start", to: "end", kind: "free", channelID: nil, winding: nil)])
        }
        let input = RopePhysicsInput(modelSHA256: "fixture", sourceSHA256: "fixture",
            collision: RopeTriangleColliderTests.box(minimum: SIMD3(repeating: -0.01), maximum: SIMD3(repeating: 0.01)),
            portals: [], channels: [], profiles: [RopePhysicsProfile(id: "front", presentationID: "front",
                instanceID: nil, boardMass: boardMass, ropes: sources)])
        let state = RopeSimulationState(profileID: "front", boardMass: boardMass, boardTranslation: translation,
            boardLinearVelocity: .zero, orientation: orientation, ropes: chains)
        return (input, state, try RopeTriangleCollider(input: input))
    }

    func testXTiltRequiresLateralTranslation() throws {
        for angle in [-0.4, 0.4] {
            let q = simd_quatd(angle: angle, axis: SIMD3<Double>(1, 0, 0))
            let (input, state, collider) = try attachedFixture(orientation: q, translation: SIMD3(0, 0, 0.03))
            var solver = try RopeDynamicsSolver(input: input, state: state, collider: collider)
            let frame = try solver.settled(targetOrientation: q, maxDuration: 5)
            XCTAssertLessThan(simd_distance(frame.boardTranslation, SIMD3(0, 0, 0.03)), 0.0002)
            XCTAssertTrue(frame.metrics.geometryAccepted)
            for chain in solver.state.ropes {
                XCTAssertEqual(chain.positions[0], chain.supports[0])
                XCTAssertLessThan(simd_distance(chain.positions[1], solver.state.worldPoint(try XCTUnwrap(chain.attachments[1]))), 1e-10)
            }
        }
    }

    func testSingleAttachmentSettlesUnderItsSupport() throws {
        let q = simd_quatd(angle: 0.4, axis: SIMD3<Double>(1, 0, 0))
        let (input, initial, collider) = try attachedFixture(orientation: q, translation: SIMD3(0, 0, 0.03), count: 1)
        var state = initial
        state.boardLinearVelocity = SIMD3(0.003, 0, -0.005)
        var solver = try RopeDynamicsSolver(input: input, state: state, collider: collider)
        let frame = try solver.settled(targetOrientation: q, maxDuration: 5)
        XCTAssertLessThan(simd_distance(frame.boardTranslation, SIMD3(0, 0, 0.03)), 0.0002)
        XCTAssertTrue(frame.metrics.geometryAccepted)
        XCTAssertEqual(solver.state.ropes[0].positions[0], initial.ropes[0].positions[0])
    }

    func testInfeasibleTiltRollsBackAndLaterValidTargetStillWorks() throws {
        let q = simd_quatd(angle: 0, axis: SIMD3<Double>(1,0,0))
        let (input, state, collider) = try attachedFixture(orientation: q, translation: .zero, leadLength: 0.00001)
        var solver = try RopeDynamicsSolver(input: input, state: state, collider: collider)
        XCTAssertThrowsError(try solver.step(dt: 1.0/240, targetOrientation: simd_quatd(angle: .pi/2, axis: SIMD3(0,1,0)))) {
            XCTAssertTrue($0.localizedDescription.contains("Bounded solve"))
        }
        assertUnchanged(solver.state, state)
        let frame = try solver.step(dt: 1.0/960, targetOrientation: q)
        XCTAssertTrue(frame.metrics.geometryAccepted)
    }

    func testLateralSweptWoodTraversalRejectsClearEndpointTeleport() throws {
        let points = [SIMD3<Double>(0,-0.1,0), SIMD3<Double>(0,0.1,0)]
        let chain = RopeInterContactTests.chain("fixed", points, supports: [0:points[0],1:points[1]], radius: 0.001)
        let source = RopePhysicsRope(id: chain.id, baselineRadius: chain.radius, radius: chain.radius,
            restLength: 0.2, linearMass: chain.linearMass,
            nodes: [RopeGraphNode(id: "a", kind: "support", point: points[0], portalID: nil),
                    RopeGraphNode(id: "b", kind: "support", point: points[1], portalID: nil)],
            edges: [RopeGraphEdge(from: "a", to: "b", kind: "free", channelID: nil, winding: nil)])
        let mesh = RopeTriangleColliderTests.box(minimum: SIMD3(repeating: -0.01), maximum: SIMD3(repeating: 0.01))
        let input = RopePhysicsInput(modelSHA256: "fixture", sourceSHA256: "fixture", collision: mesh,
            portals: [], channels: [], profiles: [RopePhysicsProfile(id: "sweep", presentationID: "sweep", instanceID: nil, boardMass: 1, ropes: [source])])
        let collider = try RopeTriangleCollider(input: input)
        let state = RopeSimulationState(profileID: "sweep", boardMass: 1, boardTranslation: SIMD3(-0.02,0,0),
            boardLinearVelocity: SIMD3(10,0,0), orientation: simd_quatd(angle: 0, axis: SIMD3<Double>(1,0,0)), ropes: [chain])
        var end = state
        end.boardTranslation.x = 0.02
        XCTAssertNil(collider.segmentContact(from: state.boardPoint(points[0]), to: state.boardPoint(points[1]), radius: chain.radius))
        XCTAssertNil(collider.segmentContact(from: end.boardPoint(points[0]), to: end.boardPoint(points[1]), radius: chain.radius))
        XCTAssertNotNil(collider.sweptSegmentContact(previousStart: state.boardPoint(points[0]), previousEnd: state.boardPoint(points[1]),
            start: end.boardPoint(points[0]), end: end.boardPoint(points[1]), radius: chain.radius))
        var solver = try RopeDynamicsSolver(input: input, state: state, collider: collider)
        XCTAssertThrowsError(try solver.step(dt: 1.0/240, targetOrientation: state.orientation)) {
            XCTAssertTrue($0.localizedDescription.contains("Bounded solve"))
            print("lateral swept-wood rejection: \($0)")
        }
        assertUnchanged(solver.state, state)
    }

    private func assertUnchanged(_ actual: RopeSimulationState, _ expected: RopeSimulationState,
        file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertEqual(actual.boardTranslation, expected.boardTranslation, file: file, line: line)
        XCTAssertEqual(actual.boardLinearVelocity, expected.boardLinearVelocity, file: file, line: line)
        XCTAssertEqual(actual.orientation.vector, expected.orientation.vector, file: file, line: line)
        for (a,b) in zip(actual.ropes,expected.ropes) {
            XCTAssertEqual(a.positions,b.positions,file:file,line:line)
            XCTAssertEqual(a.previousPositions,b.previousPositions,file:file,line:line)
            XCTAssertEqual(a.velocities,b.velocities,file:file,line:line)
            XCTAssertEqual(a.restLengths,b.restLengths,file:file,line:line)
        }
    }

    func testLateralBoardVelocityPreventsSettling() throws {
        let q = simd_quatd(angle: 0, axis: SIMD3<Double>(1, 0, 0))
        let (input, initial, collider) = try attachedFixture(orientation: q, translation: .zero)
        for velocity in [SIMD3<Double>(0.01, 0, 0), SIMD3<Double>(0, 0, 0.01)] {
            var state = initial
            state.boardLinearVelocity = velocity
            let metrics = try RopeSimulationMetrics.measure(state: state, input: input, collider: collider,
                boardHistory:[.zero, SIMD3(0.0002, 0, 0)])
            XCTAssertGreaterThanOrEqual(metrics.maximumSpeed, 0.01)
            XCTAssertEqual(metrics.boardDisplacement, 0.0002, accuracy: 1e-12)
        }
    }

    func testVectorTrustUsesAttachmentMotion() {
        let fixed = trustChain([0.1], supports: [0: .zero], attachments: [1: SIMD3(0.1, 0, 0)])
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes: [fixed], corrections: [[.zero, .zero]],
            boardCorrection: SIMD3(0, 0, 0.02)), 0.5, accuracy: 1e-12)
        let moving = trustChain([0.1], attachments: [1: SIMD3(0.1, 0, 0)])
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes: [moving],
            corrections: [[SIMD3(0, 0, 0.02), .zero]], boardCorrection: SIMD3(0, 0, 0.02)), 1)
    }

    func testAssembledWoodLengthAndPortalTranslationDerivatives() throws {
        let input = try RopeThreadedSeedTests.clavellium(), collider = try RopeTriangleCollider(input: input)
        let q = simd_quatd(angle: 0, axis: SIMD3<Double>(1, 0, 0))
        var state = try RopeThreadedSeed.make(input: input, profileID: "front", orientation: q, collider: collider)
        // Avoid the triangulated face's x=0 witness switch: the derivative
        // of each stable manifold row is tested, not a change of active rows.
        state.boardTranslation.x += 0.00031
        state.boardTranslation.z += 0.000071
        try RopePassageTopology.refresh(state: &state, input: input)
        let solver = try RopeDynamicsSolver(input: input, state: state, collider: collider)
        let rows = try solver.assembledConstraintRows()
        XCTAssertTrue(rows.contains { !$0.contact })
        XCTAssertTrue(rows.contains { $0.contact && $0.particles.count == 1 })
        XCTAssertTrue(rows.contains { $0.contact && $0.particles.count == 2 })
        for axis in 0..<3 {
            var samples: [[RopeDynamicsSolver.ConstraintRow]] = []
            for sign in [-1.0, 1.0] {
                var moved = state
                moved.boardTranslation[axis] += sign * 1e-7
                for r in moved.ropes.indices {
                    for (i, local) in moved.ropes[r].attachments { moved.ropes[r].positions[i] = moved.worldPoint(local) }
                }
                try RopePassageTopology.refresh(state: &moved, input: input)
                samples.append(try RopeDynamicsSolver(input: input, state: moved, collider: collider).assembledConstraintRows())
            }
            XCTAssertEqual(samples[0].count, rows.count, "axis \(axis)")
            XCTAssertEqual(samples[1].count, rows.count, "axis \(axis)")
            guard samples.allSatisfy({ $0.count == rows.count }) else { continue }
            for i in rows.indices {
                XCTAssertEqual(samples[0][i].particles, rows[i].particles)
                XCTAssertEqual(samples[1][i].particles, rows[i].particles)
                XCTAssertEqual(rows[i].boardGradient[axis], (samples[1][i].residual - samples[0][i].residual) / 2e-7,
                    accuracy: 1e-6, "row \(i), axis \(axis)")
            }
        }
    }

    func testAssembledSelfAndInterCordAttachmentDerivatives() throws {
        let turn = simd_quatd(angle: 0.63, axis: simd_normalize(SIMD3<Double>(1, 2, 3)))
        let first = [SIMD3<Double>(-0.02, 1, 0), SIMD3<Double>(0.02, 1, 0)]
        let second = [SIMD3<Double>(0, 0.98, 0.0069), SIMD3<Double>(0, 1.02, 0.0069)]
        let loop = first + [SIMD3<Double>(0.02, 1.03, 0.0069)] + second.reversed()
        for inter in [false, true] {
            for attached in [false, true] {
                var chains = (inter ? [first, second] : [loop]).enumerated().map { index, points in
                    RopeInterContactTests.chain("cord-\(index)", points.map { turn.act($0) })
                }
                if attached {
                    let old = chains[0]
                    chains[0] = RopeChainState(id: old.id, radius: old.radius, linearMass: old.linearMass,
                        restLengths: old.restLengths, positions: old.positions, previousPositions: old.previousPositions,
                        velocities: old.velocities, supports: [:], attachments: [1: old.positions[1]], portals: [:], channelSegments: [:])
                }
                let sources = chains.map { chain in
                    RopePhysicsRope(id: chain.id, baselineRadius: chain.radius, radius: chain.radius,
                        restLength: chain.restLengths.reduce(0,+), linearMass: chain.linearMass,
                        nodes: [RopeGraphNode(id: "a", kind: "support", point: chain.positions[0], portalID: nil),
                                RopeGraphNode(id: "b", kind: "support", point: chain.positions.last!, portalID: nil)],
                        edges: [RopeGraphEdge(from: "a", to: "b", kind: "free", channelID: nil, winding: nil)])
                }
                let mesh = RopeTriangleColliderTests.box(minimum: SIMD3(repeating: -0.01), maximum: SIMD3(repeating: 0.01))
                let input = RopePhysicsInput(modelSHA256: "fixture", sourceSHA256: "fixture", collision: mesh,
                    portals: [], channels: [], profiles: [RopePhysicsProfile(id: "contact", presentationID: "contact",
                        instanceID: nil, boardMass: 1, ropes: sources)])
                let state = RopeSimulationState(profileID: "contact", boardMass: 1, boardTranslation: .zero,
                    boardLinearVelocity: .zero, orientation: simd_quatd(angle: 0, axis: SIMD3<Double>(1,0,0)), ropes: chains)
                let collider = try RopeTriangleCollider(input: input)
                func contacts(_ state: RopeSimulationState) throws -> [ConstraintRowForTest] {
                    try RopeDynamicsSolver(input: input, state: state, collider: collider).assembledConstraintRows()
                        .filter { $0.contact && $0.particles.count == 4 }
                }
                let rows = try contacts(state)
                XCTAssertFalse(rows.isEmpty)
                if attached { XCTAssertTrue(rows.contains { simd_length($0.boardGradient) > 0.1 }) }
                for axis in 0..<3 {
                    var samples: [[ConstraintRowForTest]] = []
                    for sign in [-1.0, 1.0] {
                        var moved = state
                        moved.boardTranslation[axis] += sign * 1e-7
                        for r in moved.ropes.indices {
                            for (i, local) in moved.ropes[r].attachments { moved.ropes[r].positions[i] = moved.worldPoint(local) }
                        }
                        samples.append(try contacts(moved))
                    }
                    XCTAssertEqual(samples[0].count, rows.count)
                    XCTAssertEqual(samples[1].count, rows.count)
                    guard samples.allSatisfy({ $0.count == rows.count }) else { continue }
                    for i in rows.indices {
                        XCTAssertEqual(rows[i].boardGradient[axis], (samples[1][i].residual - samples[0][i].residual)/2e-7,
                            accuracy: 1e-6, "inter=\(inter), attached=\(attached), axis=\(axis)")
                    }
                }
            }
        }
    }

    private typealias ConstraintRowForTest = RopeDynamicsSolver.ConstraintRow

    func testAssembledTensionHessianIncludesBodyAndParticleCrossTerms() throws {
        let q = simd_quatd(angle: 0.4, axis: simd_normalize(SIMD3<Double>(1,2,3)))
        let (input, initial, collider) = try attachedFixture(orientation: q, translation: SIMD3(0,0,0.03), count: 1)
        var state = initial
        let old = state.ropes[0], points = [old.positions[0], (old.positions[0]+old.positions[1])/2, old.positions[1]]
        state.ropes[0] = RopeChainState(id: old.id, radius: old.radius, linearMass: old.linearMass,
            restLengths: [0.05,0.05], positions: points, previousPositions: points, velocities: [.zero,.zero,.zero],
            supports: old.supports, attachments: [2: try XCTUnwrap(old.attachments[1])], portals: [:], channelSegments: [:])
        var solver = try RopeDynamicsSolver(input: input, state: state, collider: collider)
        _ = try solver.step(dt: 1.0/240, targetOrientation: simd_quatd(angle: 0.42, axis: simd_normalize(SIMD3<Double>(1,2,3))))
        let tensions = solver.accumulatedLinkTensions[0]
        XCTAssertTrue(tensions.allSatisfy { $0 > 0 })
        let current = solver.state, weights = solver.particleInverseMasses
        let backbone = try solver.constraintBackbone(rows: [], weights: weights, prediction: current)
        func gradient(_ coordinates: [Double]) -> [Double] {
            var moved = current
            moved.ropes[0].positions[1] += SIMD3(coordinates[0],coordinates[1],coordinates[2])
            moved.boardTranslation += SIMD3(coordinates[3],coordinates[4],coordinates[5])
            moved.ropes[0].positions[2] = moved.worldPoint(moved.ropes[0].attachments[2]!)
            var particle = SIMD3<Double>(coordinates[0],coordinates[1],coordinates[2])/weights[0][1]
            var body = SIMD3<Double>(coordinates[3],coordinates[4],coordinates[5])*current.boardMass
            for link in 0..<2 {
                let d = moved.ropes[0].positions[link+1]-moved.ropes[0].positions[link]
                let force = tensions[link]*simd_normalize(d)
                particle += force*(link == 0 ? 1:-1)
                if link == 1 { body += force }
            }
            return [particle.x,particle.y,particle.z,body.x,body.y,body.z]
        }
        var hessian = Array(repeating: Array(repeating: 0.0, count: 6), count: 6)
        for axis in 0..<6 {
            var plus = Array(repeating: 0.0, count: 6), minus = plus
            plus[axis] = 1e-7; minus[axis] = -1e-7
            let a = gradient(plus), b = gradient(minus)
            for row in 0..<6 { hessian[row][axis] = (a[row]-b[row])/2e-7 }
        }
        for axis in 0..<6 {
            let rhs = hessian.map { $0[axis] }
            let response = try backbone.factor.solve(rhs: Array(rhs.prefix(3)), borderRHS: Array(rhs.suffix(3)))
            for i in 0..<6 {
                XCTAssertEqual((response.base+response.border)[i], i == axis ? 1:0, accuracy: 1e-7,
                    "finite-difference Hessian column \(axis), response \(i)")
            }
        }
    }

    func testProductionFallbackMapsAllBodyTranslationComponents() throws {
        let q = simd_quatd(angle: 0, axis: SIMD3<Double>(1, 0, 0))
        let (input, state, collider) = try attachedFixture(orientation: q, translation: .zero, count: 2, boardMass: 0.005)
        let solver = try RopeDynamicsSolver(input: input, state: state, collider: collider)
        let equalities = try solver.assembledConstraintRows().filter { !$0.contact }
        let contacts = [SIMD3<Double>(2000, 0, 2000), SIMD3<Double>(1000, 0, 1000)].map { gradient in
            RopeDynamicsSolver.ConstraintRow(rope: 0, particles: [0], gradients: [.zero],
                boardGradient: gradient, residual: -0.002, contact: true, lengthSegment: nil, secondRope: 1)
        }
        let weights = solver.particleInverseMasses
        let backbone = try solver.constraintBackbone(rows: equalities, weights: weights, prediction: state)
        XCTAssertThrowsError(try RopeContactSystem.solve(factor: backbone.factor, base: backbone.base,
            border: backbone.border, contacts: contacts.map { row in
                RopeLinearContact(indices: [], coefficients: [],
                    border: [row.boardGradient.x, row.boardGradient.y, row.boardGradient.z], residual: row.residual)
            })) { error in
                guard case RopeContactSystem.Failure.illConditioned = error else {
                    return XCTFail("Expected near-dependent primary solve to require fallback, got \(error)")
                }
            }
        let correction = try solver.contactCorrection(rows: equalities + contacts, weights: weights, prediction: state)
        // Independent minimum: x+z >= 2 micrometres, equal inertial weights.
        XCTAssertEqual(correction.boardCorrection.x, 1e-6, accuracy: 1e-10)
        XCTAssertEqual(correction.boardCorrection.y, 0, accuracy: 1e-10)
        XCTAssertEqual(correction.boardCorrection.z, 1e-6, accuracy: 1e-10)
        for row in contacts {
            XCTAssertGreaterThanOrEqual(row.residual + simd_dot(row.boardGradient, correction.boardCorrection), -1e-8)
        }
        var prediction = state
        prediction.boardTranslation += SIMD3(0.000003,0,-0.000004)
        for r in prediction.ropes.indices {
            for (i,local) in prediction.ropes[r].attachments { prediction.ropes[r].positions[i] = prediction.worldPoint(local) }
        }
        let moved = try solver.contactCorrection(rows: equalities+contacts, weights: weights, prediction: prediction)
        let direct = try solver.constraintBackbone(rows: equalities+[contacts[1]], weights: weights, prediction: prediction)
        XCTAssertEqual(direct.border.count,4,"Nonlocal contact must follow X/Y/Z")
        XCTAssertLessThan(simd_distance(moved.boardCorrection,SIMD3(direct.border[0],direct.border[1],direct.border[2])),1e-7)
        for row in contacts {
            XCTAssertGreaterThanOrEqual(row.residual+simd_dot(row.boardGradient,moved.boardCorrection),-1e-8)
        }
    }

    private func trustChain(_ lengths:[Double],supports:[Int:SIMD3<Double>]=[:],attachments:[Int:SIMD3<Double>]=[:])->RopeChainState {
        let positions=[SIMD3<Double>.zero]+lengths.indices.map {SIMD3<Double>(lengths[...$0].reduce(0,+),0,0)}
        return RopeChainState(id:"trust",radius:0.0035,linearMass:0.01,restLengths:lengths,positions:positions,
            previousPositions:positions,velocities:positions.map{_ in .zero},supports:supports,attachments:attachments,
            portals:[:],channelSegments:[:])
    }

    func testTrustAllowsRigidTranslation() {
        let chain=trustChain([0.001,0.002])
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes:[chain],
            corrections:[[SIMD3(1,2,3),SIMD3(1,2,3),SIMD3(1,2,3)]],boardCorrection:SIMD3(0,2,0)),1)
    }

    func testTrustBoundsRelativeMotionOfEachMaterialLink() {
        let chain=trustChain([0.01,0.02])
        // First link changes by 4 mm, second by 2 mm: the first sets alpha to 1/4.
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes:[chain],
            corrections:[[SIMD3(1,0,0),SIMD3(1.004,0,0),SIMD3(1.006,0,0)]],boardCorrection:SIMD3(0,0,0)),0.25,accuracy:1e-12)
    }

    func testTrustBoundsDiagonalAndTransverseMotion() {
        let chain=trustChain([0.01])
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes:[chain],
            corrections:[[.zero,SIMD3(0.003,0.004,0)]],boardCorrection:SIMD3(0,0,0)),0.2,accuracy:1e-12)
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes:[chain],
            corrections:[[.zero,SIMD3(0,0,0.005)]],boardCorrection:SIMD3(0,0,0)),0.2,accuracy:1e-12)
    }

    func testTrustUsesActualFixedSupportDisplacement() {
        let chain=trustChain([0.01],supports:[0:.zero])
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes:[chain],
            corrections:[[SIMD3(1,0,0),SIMD3(0.004,0,0)]],boardCorrection:SIMD3(0,0,0)),0.25,accuracy:1e-12)
    }

    func testTrustUsesActualBoardAttachmentDisplacement() {
        let chain=trustChain([0.01],attachments:[1:SIMD3(0.01,0,0)])
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes:[chain],
            corrections:[[SIMD3(0,0.02,0),.zero]],boardCorrection:SIMD3(0,0.02,0)),1)
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes:[chain],
            corrections:[[.zero,.zero]],boardCorrection:SIMD3(0,0.004,0)),0.25,accuracy:1e-12)
    }

    func testTrustDoesNotUseUnrelatedShortestLink() {
        let tiny=trustChain([0.00001]),moving=trustChain([0.01])
        XCTAssertEqual(RopeDynamicsSolver.correctionFraction(ropes:[tiny,moving],
            corrections:[[.zero,.zero],[.zero,SIMD3(0.004,0,0)]],boardCorrection:SIMD3(0,0,0)),0.25,accuracy:1e-12)
    }

    func testImmovableContactUsesBoundedRetryAndRollsBack() throws {
        let upright = simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1))
        let mesh = RopeTriangleColliderTests.box()
        let points = [SIMD3<Double>(0.9, 0, 0), SIMD3<Double>(0.9, 0.1, 0)]
        let nodes = points.enumerated().map { index, point in
            RopeGraphNode(id: "support-\(index)", kind: "support", point: point, portalID: nil)
        }
        let rope = RopePhysicsRope(id: "fixed", baselineRadius: 0.0035, radius: 0.0035,
            restLength: 0.1, linearMass: 0.01, nodes: nodes,
            edges: [RopeGraphEdge(from: nodes[0].id, to: nodes[1].id, kind: "free", channelID: nil, winding: nil)])
        let profile = RopePhysicsProfile(id: "test", presentationID: "test", instanceID: nil, boardMass: 1, ropes: [rope])
        let input = RopePhysicsInput(modelSHA256: "test", sourceSHA256: "test", collision: mesh,
            portals: [], channels: [], profiles: [profile])
        let chain = RopeChainState(id: rope.id, radius: rope.radius, linearMass: rope.linearMass,
            restLengths: [0.1], positions: points, previousPositions: points, velocities: [.zero, .zero],
            supports: [0: points[0], 1: points[1]], attachments: [:], portals: [:], channelSegments: [:])
        let state = RopeSimulationState(profileID: profile.id, boardMass: 1, boardTranslation:.zero,
            boardLinearVelocity:.zero, orientation: upright, ropes: [chain])
        var solver = try RopeDynamicsSolver(input: input, state: state, collider: RopeTriangleCollider(mesh: mesh))
        // Both endpoints start fixed inside wood. A translating body can try
        // to escape, but the sweep must reject that traversal and roll back.
        XCTAssertThrowsError(try solver.step(dt: 1.0 / 240, targetOrientation: upright)) { error in
            guard case RopePhysicsError.invalid(let reason) = error else {
                return XCTFail("Expected bounded nonlinear failure, got \(error)")
            }
            XCTAssertTrue(reason.hasPrefix("Bounded solve could not resolve"))
        }
        assertUnchanged(solver.state, state)
    }

    func testConnectedNeighborhoodRejectsCrossingAtEarlierSegmentEndpoint() {
        let points: [SIMD3<Double>] = [SIMD3(-0.002, 0, 0), .zero,
            SIMD3(0, 0.001, 0), SIMD3(0, -0.001, 0)]
        // Link 2 crosses link 0 exactly at its endpoint, but these links do
        // not share a material knot. The short intervening arc cannot hide it.
        XCTAssertEqual(RopeSimulationMetrics.selfContactPair(
            positions: points, radius: 0.0035, supports: [:]), SIMD2(0, 2))
    }

    func testLargeFiniteSettlingDurationFailsWithoutIntegerConversionTrap() throws {
        let input = try RopeThreadedSeedTests.clavellium()
        let collider = try RopeTriangleCollider(input: input)
        let upright = simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1))
        let state = try RopeThreadedSeed.make(input: input, profileID: "front", orientation: upright, collider: collider)
        var solver = try RopeDynamicsSolver(input: input, state: state, collider: collider)
        for duration in [Double.greatestFiniteMagnitude, Double(Int.max) / 240] {
            XCTAssertThrowsError(try solver.settled(targetOrientation: upright, maxDuration: duration))
            XCTAssertEqual(solver.state.boardTranslation.y, state.boardTranslation.y)
        }
    }

    func testCancelledSettlingStopsBeforeTakingAnyStep() async throws {
        let input = try RopeThreadedSeedTests.clavellium()
        let collider = try RopeTriangleCollider(input: input)
        let upright = simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1))
        let state = try RopeThreadedSeed.make(input: input, profileID: "front", orientation: upright, collider: collider)
        let initial = try RopeDynamicsSolver(input: input, state: state, collider: collider)
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            var solver = initial
            do {
                _ = try solver.settled(targetOrientation: upright, maxDuration: 5)
                XCTFail("Cancelled settling must throw")
            } catch is CancellationError {
                XCTAssertEqual(solver.state.boardTranslation.y, initial.state.boardTranslation.y)
            }
        }
        try await task.value
    }

    func testRejectsNonfiniteStateAndInvalidTimeStep() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        var state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        for dt in [0, -1, Double.nan, Double.infinity, 1] {
            XCTAssertThrowsError(try solver.step(dt:dt,targetOrientation:q))
        }
        var previousState=state
        previousState.ropes[0].previousPositions[20].x = .nan
        XCTAssertThrowsError(try RopeDynamicsSolver(input:input,state:previousState,collider:collider))
        state.ropes[0].positions[20].x = .nan
        XCTAssertThrowsError(try RopeDynamicsSolver(input:input,state:state,collider:collider))
    }

    func testRejectsLinklessRopeBeforeSimulation() throws {
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        let mesh=RopeTriangleColliderTests.box(minimum:SIMD3(-0.01,-0.01,-0.01),maximum:SIMD3(0.01,0.01,0.01))
        let rope=RopePhysicsRope(id:"lead",baselineRadius:0.002,radius:0.0035,restLength:0,linearMass:0.01,nodes:[],edges:[])
        let input=RopePhysicsInput(modelSHA256:String(repeating:"a",count:64),sourceSHA256:String(repeating:"b",count:64),
            collision:mesh,portals:[],channels:[],profiles:[RopePhysicsProfile(id:"front",presentationID:"front",instanceID:nil,boardMass:1,ropes:[rope])])
        let chain=RopeChainState(id:"lead",radius:0.0035,linearMass:0.01,restLengths:[],positions:[.zero],
            previousPositions:[.zero],velocities:[.zero],supports:[:],attachments:[:],portals:[:],channelSegments:[:])
        let state=RopeSimulationState(profileID:"front",boardMass:1,boardTranslation:.zero,boardLinearVelocity:.zero,orientation:q,ropes:[chain])
        XCTAssertThrowsError(try RopeDynamicsSolver(input:input,state:state,collider:RopeTriangleCollider(input:input)))
    }

    func testLostPredictedCrossingExhaustsBoundedRecoveryAndRollsBack() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        var state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        state.ropes[0].velocities=state.ropes[0].positions.map { _ in SIMD3<Double>(1_000_000,0,0) }
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        XCTAssertThrowsError(try solver.step(dt:1.0/240,targetOrientation:q)) { error in
            // An unrecoverable prediction must exhaust subdivision rather
            // than escape as the first raw topology error.
            XCTAssertTrue(error.localizedDescription.contains("Bounded solve could not resolve"), "\(error)")
            XCTAssertTrue(error.localizedDescription.contains("Lost ordered portal crossing"), "\(error)")
        }
        assertUnchanged(solver.state, state)
    }

    func testTautAttachmentTransfersBoardLoadWithoutStretch() throws {
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        let support=SIMD3<Double>(0,0.114,0),attachment=SIMD3<Double>(0,0.014,0)
        let rope=RopePhysicsRope(id:"lead",baselineRadius:0.002,radius:0.0035,restLength:0.1,linearMass:0.01,
            nodes:[RopeGraphNode(id:"support",kind:"support",point:support,portalID:nil),
                   RopeGraphNode(id:"attachment",kind:"attachment",point:attachment,portalID:nil)],
            edges:[RopeGraphEdge(from:"support",to:"attachment",kind:"free",channelID:nil,winding:nil)])
        let mesh=RopeTriangleColliderTests.box(minimum:SIMD3(-0.01,-0.01,-0.01),maximum:SIMD3(0.01,0.01,0.01))
        let input=RopePhysicsInput(modelSHA256:String(repeating:"a",count:64),sourceSHA256:String(repeating:"b",count:64),
            collision:mesh,portals:[],channels:[],profiles:[RopePhysicsProfile(id:"front",presentationID:"front",instanceID:nil,boardMass:1,ropes:[rope])])
        let chain=RopeChainState(id:"lead",radius:0.0035,linearMass:0.01,restLengths:[0.1],positions:[support,attachment],
            previousPositions:[support,attachment],velocities:[.zero,.zero],supports:[0:support],attachments:[1:attachment],portals:[:],channelSegments:[:])
        let state=RopeSimulationState(profileID:"front",boardMass:1,boardTranslation:.zero,boardLinearVelocity:.zero,orientation:q,ropes:[chain])
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:RopeTriangleCollider(input:input))
        for _ in 0..<240 {
            let frame=try solver.step(dt:1.0/240,targetOrientation:q)
            XCTAssertEqual(frame.boardTranslation.y,0,accuracy:1e-8)
            XCTAssertLessThan(frame.metrics.maximumLocalStrain,1e-7)
            XCTAssertLessThan(frame.metrics.totalLengthError,1e-8)
        }
    }

    func testSlidingPortalBoundaryGradientsFollowMovingIntersection() throws {
        for angle in [0.0,0.7,2.1] {
            let q=simd_quatd(angle:angle,axis:simd_normalize(SIMD3<Double>(1,2,3)))
            let portal=RopePortalRegion(id:"mouth",center:q.act(SIMD3(0,0,0.01)),normal:q.act(SIMD3(0,0,1)),
                boundary:[SIMD3<Double>(-0.02,-0.02,0.01),SIMD3(0.02,-0.02,0.01),SIMD3(0.02,0.02,0.01),SIMD3(-0.02,0.02,0.01)].map{q.act($0)},
                clearanceRadius:0.02)
            let a=q.act(SIMD3<Double>(-0.004,0.003,-0.008)),b=q.act(SIMD3<Double>(0.009,0.012,0.022))
            let rows=try RopePassageTopology.boundaryConstraints(from:a,to:b,portal:portal,radius:0.0035)
            XCTAssertEqual(rows.count,4)
            // Recompute the actual plane intersection, not a fixed material
            // fraction. Omitting its derivative changes the finite differences.
            func residual(_ a:SIMD3<Double>,_ b:SIMD3<Double>,edge:Int)->Double {
                let delta=b-a,f=simd_dot(portal.center-a,portal.normal)/simd_dot(delta,portal.normal)
                let start=portal.boundary[edge],end=portal.boundary[(edge+1)%portal.boundary.count]
                var inward=simd_normalize(simd_cross(portal.normal,end-start))
                if simd_dot(inward,portal.center-start)<0 {inward = -inward}
                return simd_dot(a+f*delta-start,inward)-0.0035-RopeRegionGeometry.clearance
            }
            for edge in rows.indices {
                XCTAssertEqual(rows[edge].residual,residual(a,b,edge:edge),accuracy:1e-12)
                for axis in 0..<3 {
                    var epsilon=SIMD3<Double>.zero;epsilon[axis]=1e-7
                    XCTAssertEqual(rows[edge].firstGradient[axis],
                        (residual(a+epsilon,b,edge:edge)-residual(a-epsilon,b,edge:edge))/2e-7,accuracy:1e-7)
                    XCTAssertEqual(rows[edge].secondGradient[axis],
                        (residual(a,b+epsilon,edge:edge)-residual(a,b-epsilon,edge:edge))/2e-7,accuracy:1e-7)
                }
                let delta=b-a
                XCTAssertEqual(simd_dot(rows[edge].firstGradient,delta),0,accuracy:1e-12)
                XCTAssertEqual(simd_dot(rows[edge].secondGradient,delta),0,accuracy:1e-12)
            }
            XCTAssertThrowsError(try RopePassageTopology.boundaryConstraints(from:a,to:a,portal:portal,radius:0.0035))
        }
    }

    func testSlidingPortalGradientsIncludeBoardHeightAndAttachments() throws {
        let q=simd_quatd(angle:0.7,axis:simd_normalize(SIMD3<Double>(1,2,3)))
        let portal=RopePortalRegion(id:"mouth",center:SIMD3(0,0,0.01),normal:SIMD3(0,0,1),
            boundary:[SIMD3<Double>(-0.02,-0.02,0.01),SIMD3(0.02,-0.02,0.01),SIMD3(0.02,0.02,0.01),SIMD3(-0.02,0.02,0.01)],clearanceRadius:0.02)
        let a=SIMD3<Double>(-0.004,0.003,-0.008),b=SIMD3<Double>(0.009,0.012,0.022)
        let rows=try RopePassageTopology.boundaryConstraints(from:a,to:b,portal:portal,radius:0.0035)
        let localUp=q.inverse.act(SIMD3<Double>(0,1,0)),epsilon=1e-7
        for firstAttached in [false,true] {
            for secondAttached in [false,true] {
                // A board-fixed endpoint moves with board height; an exterior
                // endpoint stays in world space and moves in board coordinates.
                let da=firstAttached ? SIMD3<Double>.zero:-localUp
                let db=secondAttached ? SIMD3<Double>.zero:-localUp
                let plus=try RopePassageTopology.boundaryConstraints(from:a+da*epsilon,to:b+db*epsilon,portal:portal,radius:0.0035)
                let minus=try RopePassageTopology.boundaryConstraints(from:a-da*epsilon,to:b-db*epsilon,portal:portal,radius:0.0035)
                for edge in rows.indices {
                    let firstWorld=q.act(rows[edge].firstGradient),secondWorld=q.act(rows[edge].secondGradient)
                    let derivative = -firstWorld.y-secondWorld.y+(firstAttached ? firstWorld.y:0)+(secondAttached ? secondWorld.y:0)
                    XCTAssertEqual(derivative,(plus[edge].residual-minus[edge].residual)/(2*epsilon),accuracy:1e-7)
                }
            }
        }
    }

    func testSlidingCrossingCorrectionEnforcesConservativeAperture() throws {
        let source=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:source)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        // A conservative planar mouth can be slightly inside the CAD rim.
        // Wood-only corrections cannot enforce this distinct topology boundary.
        let portals=source.portals.map {p in
            RopePortalRegion(id:p.id,center:p.center,normal:p.normal,
                boundary:p.boundary.map{p.center+($0-p.center)*0.999},clearanceRadius:p.clearanceRadius)
        }
        let input=RopePhysicsInput(modelSHA256:source.modelSHA256,sourceSHA256:source.sourceSHA256,
            collision:source.collision,portals:portals,channels:source.channels,profiles:source.profiles)
        let initial=try RopeThreadedSeed.make(input:source,profileID:"front",orientation:q,collider:collider)
        XCTAssertTrue(try RopeSimulationMetrics.measure(state:initial,input:input,collider:collider,
            boardHistory:[initial.boardTranslation]).geometryAccepted)
        var solver=try RopeDynamicsSolver(input:input,state:initial,collider:collider)
        let frame=try solver.step(dt:1.0/240,targetOrientation:q)
        XCTAssertTrue(frame.metrics.geometryAccepted)
        XCTAssertEqual(solver.state.ropes[0].restLengths,initial.ropes[0].restLengths)
        for (id,crossing) in solver.state.ropes[0].portalCrossings {
            let portal=try XCTUnwrap(portals.first{$0.id==id})
            let point=solver.state.boardPoint(crossing.point(in:solver.state.ropes[0].positions))
            XCTAssertGreaterThanOrEqual(RopePassageTopology.boundaryMargin(point,portal:portal),
                solver.state.ropes[0].radius+RopeRegionGeometry.clearance-1e-8)
        }
    }

    func testPortalCrossingsMoveThroughMaterialWithoutChangingRestLengths() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        var state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        let before=state.ropes[0].portalCrossings,rest=state.ropes[0].restLengths
        for i in state.ropes[0].positions.indices where state.ropes[0].supports[i] == nil {
            state.ropes[0].positions[i].z += 0.002
        }
        try RopePassageTopology.refresh(state:&state,input:input)
        XCTAssertEqual(state.ropes[0].restLengths,rest)
        XCTAssertEqual(state.ropes[0].portalCrossings.count,2)
        for (id,crossing) in state.ropes[0].portalCrossings {
            XCTAssertGreaterThan(crossing.materialCoordinate,try XCTUnwrap(before[id]).materialCoordinate+0.5)
            XCTAssertGreaterThan(crossing.segment,try XCTUnwrap(before[id]).segment)
            let portal=try XCTUnwrap(input.portals.first{$0.id == id})
            let point=state.boardPoint(crossing.point(in:state.ropes[0].positions))
            XCTAssertEqual(simd_dot(point-portal.center,portal.normal),0,accuracy:1e-10)
        }
    }

    func testDynamicsFeedsRopeThroughPassageUnderAsymmetricMaterialAllocation() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        var state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        let source=state.ropes[0]
        let front=try XCTUnwrap(source.portals.first{$0.value == "central-front"}?.key)
        let back=try XCTUnwrap(source.portals.first{$0.value == "central-back"}?.key)
        var arc=[0.0]
        for length in source.restLengths {arc.append(arc.last!+length)}
        let frontBegin=try XCTUnwrap(arc.firstIndex{$0>=0.02})
        let backEnd=try XCTUnwrap(arc.lastIndex{$0<=arc.last!-0.02})
        let frontLength=source.restLengths[frontBegin..<front].reduce(0,+)
        let backLength=source.restLengths[back..<backEnd].reduce(0,+)
        // Keep the certified geometric shape and total material length. Put
        // 1 mm less material in the front leg and 1 mm more in the back leg.
        // Leave the material of the common support knot unchanged. Sliding
        // must resolve the leg asymmetry; fixed portal particles cannot.
        let rest=source.restLengths.enumerated().map{i,length in
            length*(i>=frontBegin && i<front ? 1-0.001/frontLength:(i>=back && i<backEnd ? 1+0.001/backLength:1))
        }
        var chain=RopeChainState(id:source.id,radius:source.radius,linearMass:source.linearMass,restLengths:rest,
            positions:source.positions,previousPositions:source.previousPositions,velocities:source.velocities,
            supports:source.supports,attachments:source.attachments,portals:source.portals,channelSegments:source.channelSegments)
        chain.portalCrossings=source.portalCrossings;chain.channelSpans=source.channelSpans
        state.ropes[0]=chain
        let initial=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[state.boardTranslation])
        XCTAssertTrue(initial.geometryAccepted,String(describing:initial))
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        let frame=try solver.settled(targetOrientation:q,maxDuration:5)
        XCTAssertTrue(frame.settled);XCTAssertTrue(frame.metrics.geometryAccepted)
        XCTAssertEqual(solver.state.ropes[0].restLengths,rest)
        for (id,before) in source.portalCrossings {
            let after=try XCTUnwrap(solver.state.ropes[0].portalCrossings[id])
            XCTAssertGreaterThan(after.materialCoordinate,before.materialCoordinate+0.2)
        }
    }

    func testUnconvergedSolutionCannotBeReportedSettled() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        let state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        XCTAssertThrowsError(try solver.settled(targetOrientation:simd_quatd(angle:.pi,axis:SIMD3(0,0,1)),maxDuration:0.01)) {error in
            XCTAssertEqual(error as? RopePhysicsError,.invalid("Rope did not converge within 0.01 seconds"))
        }
    }

    func testSharedSupportSeparationBoundIsConservativeAcrossMotion() {
        for index in 0..<32 {
            let phase=Double(index)*0.71
            let u=SIMD3<Double>(0.03*sin(phase),-0.1,0.02*cos(phase))
            let v=SIMD3<Double>(0.05*cos(phase),-0.08,0.03*sin(phase))
            let nextU=u+SIMD3<Double>(0.025*cos(phase),0.01*sin(phase),-0.015)
            let nextV=v+SIMD3<Double>(-0.04,0.015*cos(phase),0.02*sin(phase))
            let firstFraction=0.001+Double(index%4)*0.02,secondFraction=0.002+Double(index%3)*0.03
            let bound=RopeMotionSweep.sharedSupportSeparationBound(previousFirst:u,first:nextU,
                previousSecond:v,second:nextV,firstFraction:firstFraction,secondFraction:secondFraction)
            XCTAssertGreaterThanOrEqual(bound,0)
            for sample in 0...64 {
                let t=Double(sample)/64,a=u+(nextU-u)*t,b=v+(nextV-v)*t
                let pair=RopeTriangleCollider.segmentPair(a*firstFraction,a,b*secondFraction,b)
                XCTAssertLessThanOrEqual(bound,simd_distance(pair.0,pair.1)+1e-12)
            }
        }
        let u=SIMD3<Double>(0.01,-0.1,0),v=SIMD3<Double>(0.03,-0.1,0)
        XCTAssertEqual(RopeMotionSweep.sharedSupportSeparationBound(previousFirst:u,first:v,
            previousSecond:v,second:u,firstFraction:0.01,secondFraction:0.01),0)
    }

    func testSharedSupportRaysRotateWithoutFalseSweepExhaustion() {
        let support=SIMD3<Double>.zero
        let before=[support,SIMD3(0.01,-0.1,0),SIMD3(0.03,-0.1,0),support]
        let q=simd_quatd(angle:0.003,axis:SIMD3<Double>(0,0,1))
        let after=before.map{q.act($0)}
        let rest=zip(before,before.dropFirst()).map{simd_distance($0,$1)}
        // Swept boxes overlap; the unchanged angle between these rays keeps
        // their trimmed centerlines separated throughout the motion.
        XCTAssertTrue(RopeMotionSweep.selfContactValid(previous:before,positions:after,
            radius:0.0035,supports:[0:support,3:support],restLengths:rest))
    }

    func testSharedSupportRaysCannotSwapThroughEachOther() {
        let support=SIMD3<Double>.zero
        let before=[support,SIMD3(0.01,-0.1,0),SIMD3(0.03,-0.1,0),support]
        let after=[support,before[2],before[1],support]
        let rest=zip(before,before.dropFirst()).map{simd_distance($0,$1)}
        XCTAssertFalse(RopeMotionSweep.selfContactValid(previous:before,positions:after,
            radius:0.0035,supports:[0:support,3:support],restLengths:rest))
    }

    func testSelfSweepCertifiesEndReachedOnLastIteration() {
        let before:[SIMD3<Double>]=[SIMD3(-1,0,0),SIMD3(1,0,0),SIMD3(1,0.001,0),SIMD3(-1,0.001,0)]
        let after=before.map{$0+SIMD3<Double>(0,0.0511,0)}
        // Constant 0.5 mm clearance: the conservative 80% advancement reaches
        // t=1 on iteration 256. A rigid translation cannot create contact.
        XCTAssertTrue(RopeMotionSweep.selfContactValid(previous:before,positions:after,
            radius:0.000275,supports:[:],restLengths:[2,0.001,2]))
    }

    func testSelfContactDetectsCrossingAwayFromSharedSupport() {
        let points:[SIMD3<Double>]=[SIMD3(0,1,0),SIMD3(-1,0,0),SIMD3(1,0,0),SIMD3(1,1,0),SIMD3(0,-1,0),SIMD3(0,1,0)]
        XCTAssertFalse(RopeSimulationMetrics.selfContactValid(positions:points,radius:0.006,supports:[0:points[0],5:points[5]]))
    }

    func testSelfContactManifoldIncludesSimultaneousOverlaps() {
        let points:[SIMD3<Double>]=[SIMD3(-1,0,0),SIMD3(1,0,0),SIMD3(2,2,0),
            SIMD3(-1,0,0.004),SIMD3(1,0,0.004),SIMD3(2,-2,0.004),
            SIMD3(-1,0,0.002),SIMD3(1,0,0.002)]
        let pairs=RopeSimulationMetrics.selfContactPairs(positions:points,radius:0.0035,supports:[:])
        for pair in [SIMD2(0,3),SIMD2(0,6),SIMD2(3,6)] {XCTAssertTrue(pairs.contains(pair))}
        XCTAssertEqual(pairs.first,RopeSimulationMetrics.selfContactPair(positions:points,radius:0.0035,supports:[:]))
    }

    func testSelfContactPenaltyIsContinuousWhenFirstOverlapSeparates() {
        func penalty(_ separation:Double)->Double {
            let points:[SIMD3<Double>]=[SIMD3(-1,0,0),SIMD3(1,0,0),SIMD3(2,2,0),
                SIMD3(-1,0,separation),SIMD3(1,0,separation),SIMD3(3,3,1),
                SIMD3(9,0,0),SIMD3(11,0,0),SIMD3(12,2,0),SIMD3(9,0,0.002),SIMD3(11,0,0.002)]
            return RopeSimulationMetrics.selfContactPairs(positions:points,radius:0.0035,supports:[:],margin:0.0001).reduce(0) {value,pair in
                let witness=RopeTriangleCollider.segmentPair(points[pair.x],points[pair.x+1],points[pair.y],points[pair.y+1])
                return value+max(0,0.00705-simd_distance(witness.0,witness.1))
            }
        }
        let before=penalty(0.00705-1e-8),after=penalty(0.00705+1e-8)
        XCTAssertGreaterThan(before,0.005);XCTAssertGreaterThan(after,0.005)
        XCTAssertEqual(before,after,accuracy:1e-6)
    }

    func testInitializationSeparatesFiniteRadiusOverlapsWithoutChangingMaterial() throws {
        // Synthetic open rope, clear of the fixture wood. The return leg is
        // 4 mm from its first leg: centerlines are separate, 7 mm tubes overlap.
        let points:[SIMD3<Double>]=[SIMD3(-0.1,1,0),SIMD3(0,1,0),SIMD3(0.1,1,0),
            SIMD3(0.12,1.1,0.004),SIMD3(0.1,1,0.004),SIMD3(0,1,0.004),SIMD3(-0.1,1.1,0.004)]
        let rest=zip(points,points.dropFirst()).map{simd_distance($0,$1)}
        let supports=[0:points[0],points.count-1:points.last!]
        let source=RopePhysicsRope(id:"fixture",baselineRadius:0.002,radius:0.0035,
            restLength:rest.reduce(0,+),linearMass:0.01,
            nodes:[RopeGraphNode(id:"a",kind:"support",point:points[0],portalID:nil),
                   RopeGraphNode(id:"b",kind:"support",point:points.last!,portalID:nil)],
            edges:[RopeGraphEdge(from:"a",to:"b",kind:"free",channelID:nil,winding:nil)])
        let input=RopePhysicsInput(modelSHA256:String(repeating:"a",count:64),sourceSHA256:String(repeating:"b",count:64),
            collision:RopeTriangleColliderTests.box(minimum:SIMD3(repeating:-0.01),maximum:SIMD3(repeating:0.01)),
            portals:[],channels:[],profiles:[RopePhysicsProfile(id:"fixture",presentationID:"fixture",instanceID:nil,boardMass:1,ropes:[source])])
        let chain=RopeChainState(id:source.id,radius:source.radius,linearMass:source.linearMass,restLengths:rest,
            positions:points,previousPositions:points,velocities:points.map{_ in .zero},supports:supports,
            attachments:[:],portals:[:],channelSegments:[:])
        let state=RopeSimulationState(profileID:"fixture",boardMass:1,boardTranslation:.zero,boardLinearVelocity:.zero,
            orientation:simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1)),ropes:[chain])
        let collider=try RopeTriangleCollider(input:input)
        let before=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[.zero])
        XCTAssertFalse(before.geometryAccepted);XCTAssertTrue(before.topologyFailure?.contains("Self contact") == true)
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        XCTAssertThrowsError(try solver.projectInitialization(maxIterations:0))
        XCTAssertEqual(solver.state.ropes[0].positions,points)
        let frame=try solver.projectInitialization()
        XCTAssertTrue(frame.metrics.geometryAccepted)
        XCTAssertEqual(solver.state.ropes[0].restLengths,rest)
        for (index,point) in supports {XCTAssertEqual(solver.state.ropes[0].positions[index],point)}

        var crossed=state
        for i in 3...5 {crossed.ropes[0].positions[i].z=0}
        var rejected=try RopeDynamicsSolver(input:input,state:crossed,collider:collider)
        XCTAssertThrowsError(try rejected.projectInitialization()) {error in
            XCTAssertEqual(error as? RopePhysicsError,.invalid("Initial rope centerline crosses itself"))
        }
        XCTAssertEqual(rejected.state.ropes[0].positions,crossed.ropes[0].positions)

        var penetrated=state
        penetrated.ropes[0].positions[2] = .zero
        var invalid=try RopeDynamicsSolver(input:input,state:penetrated,collider:collider)
        XCTAssertThrowsError(try invalid.projectInitialization()) {error in
            XCTAssertEqual(error as? RopePhysicsError,.invalid("Invalid initial wood geometry or threading"))
        }
        XCTAssertEqual(invalid.state.ropes[0].positions,penetrated.ropes[0].positions)
    }

    func testRotatingBoardSweepCoversArcMissedByEndpointChord() throws {
        let angle=Double.pi/2,start=SIMD3<Double>(1,0,0),end=start
        let first=start,last=simd_quatd(angle:angle,axis:SIMD3(0,0,1)).inverse.act(end)
        let deviation=RopeMotionSweep.rotationalDeviation(start:start,end:end,angle:angle)
        for i in 0...100 {
            let t=Double(i)/100
            let actual=simd_quatd(angle:angle*t,axis:SIMD3(0,0,1)).inverse.act(start+(end-start)*t)
            XCTAssertLessThanOrEqual(simd_distance(actual,first+(last-first)*t),deviation)
        }
        let center=SIMD3<Double>(sqrt(0.5),-sqrt(0.5),0)
        let collider=try RopeTriangleCollider(mesh:RopeTriangleColliderTests.box(minimum:center-SIMD3(repeating:0.02),maximum:center+SIMD3(repeating:0.02)))
        XCTAssertNil(collider.sweptSegmentContact(previousStart:first,previousEnd:first,start:last,end:last,radius:0.0035))
        XCTAssertNotNil(collider.sweptSegmentContact(previousStart:first,previousEnd:first,start:last,end:last,radius:0.0035+deviation))
        XCTAssertEqual(RopeMotionSweep.rotationalDeviation(start:start,end:end,angle:0),0)
    }

    func testSweptSelfContactRejectsCrossingWithClearEndpointShapes() {
        let before:[SIMD3<Double>]=[SIMD3(-1,0,-0.02),SIMD3(1,0,-0.02),SIMD3(3,0,-0.02),
                                   SIMD3(3,2,0.02),SIMD3(0,-1,0.02),SIMD3(0,1,0.02)]
        let after=before.map{SIMD3($0.x,$0.y,-$0.z)}
        let rest=zip(before,before.dropFirst()).map{simd_distance($0,$1)}
        XCTAssertTrue(RopeSimulationMetrics.selfContactValid(positions:before,radius:0.0035,supports:[:]))
        XCTAssertTrue(RopeSimulationMetrics.selfContactValid(positions:after,radius:0.0035,supports:[:]))
        XCTAssertFalse(RopeMotionSweep.selfContactValid(previous:before,positions:after,radius:0.0035,supports:[:],restLengths:rest))
        XCTAssertTrue(RopeMotionSweep.selfContactValid(previous:before,positions:before.map{$0+SIMD3(0,0,0.001)},radius:0.0035,supports:[:],restLengths:rest))
    }

    func testConnectedCapsulesAroundQuarterTurnAreNotSelfCrossing() {
        let r=0.0061
        var points:[SIMD3<Double>]=stride(from:-0.01,through:0,by:0.002).map{SIMD3($0,0,0)}
        points += (1...10).map {i in
            let angle=Double(i)*Double.pi/20
            return SIMD3(r*sin(angle),r*(1-cos(angle)),0)
        }
        points += stride(from:0.002,through:0.01,by:0.002).map{SIMD3(r,r+$0,0)}
        XCTAssertTrue(RopeSimulationMetrics.selfContactValid(positions:points,radius:0.006,supports:[:]))
    }
}
