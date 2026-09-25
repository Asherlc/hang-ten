import AVFoundation
import XCTest
import SwiftUI
import UIKit
@testable import HangTen

final class WorkoutSpeechVoiceSelectorTests: XCTestCase {
    func testSelectsBestQualityAmongExactLocaleCandidates() {
        let cases: [(name: String, candidates: [WorkoutSpeechVoiceCandidate], expected: String?)] = [
            (
                "off-locale premium is ignored",
                [
                    WorkoutSpeechVoiceCandidate(identifier: "exact-default", language: "en-US", quality: .default),
                    WorkoutSpeechVoiceCandidate(identifier: "off-locale-premium", language: "en-GB", quality: .premium)
                ],
                "exact-default"
            ),
            (
                "enhanced wins without premium",
                [
                    WorkoutSpeechVoiceCandidate(identifier: "exact-default", language: "en-US", quality: .default),
                    WorkoutSpeechVoiceCandidate(identifier: "exact-enhanced", language: "en-US", quality: .enhanced)
                ],
                "exact-enhanced"
            ),
            (
                "premium wins across all quality tiers",
                [
                    WorkoutSpeechVoiceCandidate(identifier: "exact-default", language: "en-US", quality: .default),
                    WorkoutSpeechVoiceCandidate(identifier: "exact-enhanced", language: "en-US", quality: .enhanced),
                    WorkoutSpeechVoiceCandidate(identifier: "exact-premium", language: "en-US", quality: .premium)
                ],
                "exact-premium"
            ),
            (
                "default is the sole exact-locale voice",
                [
                    WorkoutSpeechVoiceCandidate(identifier: "exact-default", language: "en-US", quality: .default),
                    WorkoutSpeechVoiceCandidate(identifier: "off-locale-premium", language: "en-GB", quality: .premium)
                ],
                "exact-default"
            ),
            (
                "no exact-locale candidate",
                [
                    WorkoutSpeechVoiceCandidate(identifier: "off-locale-premium", language: "en-GB", quality: .premium)
                ],
                nil
            )
        ]

        for testCase in cases {
            XCTAssertEqual(
                WorkoutSpeechVoiceSelector.bestCandidate(
                    from: testCase.candidates,
                    preferredLanguage: "en-US"
                )?.identifier,
                testCase.expected,
                testCase.name
            )
        }
    }
}

final class WorkoutTimelineTests: XCTestCase {
    func testLivePresentationMaterializesEitherHandForLabelsAndPreservesUnresolvedStep() {
        let eitherHand = WorkoutStep(
            id: "either", number: 1, title: "Either hand", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang, handUse: .either,
            side: .both
        )

        XCTAssertEqual(
            WorkoutLiveStepResolver.materialized(eitherHand, selectedHandSide: .right).side,
            .right
        )
        XCTAssertEqual(
            WorkoutTimeline.labels(
                for: WorkoutLiveStepResolver.materialized(eitherHand, selectedHandSide: .right)
            ),
            ["Hang", "Right hand"]
        )
        XCTAssertEqual(
            WorkoutLiveStepResolver.materialized(eitherHand, selectedHandSide: nil),
            eitherHand
        )

        let bilateral = WorkoutStep(
            id: "bilateral", number: 2, title: "Both hands", instruction: "Hang.",
            accessory: "", duration: 7, phase: .hang, handUse: .double,
            side: .both
        )
        XCTAssertEqual(
            WorkoutLiveStepResolver.materialized(bilateral, selectedHandSide: .right),
            bilateral
        )
    }

    func testLivePresentationResolvesBilateralStepsOnAOneHandedBoard() {
        let bilateral = WorkoutStep(
            id: "bilateral", number: 1, title: "Both hands", instruction: "Hang.",
            accessory: "", duration: 7, phase: .hang, handUse: .double,
            side: .both
        )

        let resolved = WorkoutLiveStepResolver.materialized(
            bilateral,
            selectedHandSide: .right,
            boardIsOneHanded: true
        )
        XCTAssertEqual(resolved.handUse, .single)
        XCTAssertEqual(resolved.side, .right)

        XCTAssertEqual(
            WorkoutLiveStepResolver.materialized(bilateral, selectedHandSide: nil, boardIsOneHanded: true),
            bilateral
        )
    }

    func testCaptainFingerfoodDualWorkoutsResolveAsOneHandedAfterHandChoice() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "captain-fingerfood.dual"))
        XCTAssertEqual(board.handCapacity, 1)
        XCTAssertTrue(board.isOneHanded)

        let bilateral = WorkoutStep(
            id: "bilateral", number: 1, title: "Hang", instruction: "Hang.",
            accessory: "", duration: 7, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([
                    ContactRequirement(
                        kind: .edge,
                        depth: .range(.init(minimum: 20, maximum: 20)),
                        selection: .bilateralPair
                    )
                ]),
                timing: .fixed,
                duration: 7
            )],
            handUse: .double, side: .both
        )

        XCTAssertTrue(
            bilateral.handUse == .either || board.isOneHanded,
            "Dual must gate the start-of-session hand picker like other one-handed boards"
        )

        let resolved = WorkoutLiveStepResolver.materialized(
            bilateral,
            selectedHandSide: .left,
            boardIsOneHanded: board.isOneHanded
        )
        XCTAssertEqual(resolved.handUse, .single)
        XCTAssertEqual(resolved.side, .left)
        XCTAssertEqual(resolved.workRequirements.map(\.selection), [.single])
        XCTAssertEqual(WorkoutTimeline.labels(for: resolved), ["Hang", "Left hand"])
        XCTAssertFalse(WorkoutHoldCueVisibilityPolicy.showsCue(for: .right, step: resolved))
        XCTAssertTrue(WorkoutHoldCueVisibilityPolicy.showsCue(for: .left, step: resolved))
        XCTAssertEqual(
            GripDiagramView.singleSide(handCapacity: 1, resolvedSide: resolved.side),
            .left
        )
        let dualEdge = try XCTUnwrap(board.contacts.first { $0.id == "curved-edge-20" })
        XCTAssertEqual(GripDiagramView.cueLabel(for: dualEdge), "20 mm curved edge")
    }

    func testBoardHandCapacityDrivesOneHandedWorkoutMaterialization() {
        let bilateral = WorkoutStep(
            id: "bilateral", number: 1, title: "Both hands", instruction: "Hang.",
            accessory: "", duration: 7, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement(kind: .jug, selection: .bilateralPair)]),
                timing: .fixed,
                duration: 7
            )],
            handUse: .double, side: .both
        )
        let contact = PhysicalContact(id: "edge", name: "Edge", kind: .edge, handCapacity: 1)
        let productURL = URL(string: "https://example.com/board")!

        let oneHanded = BoardRevision(
            id: "fixture.one-handed",
            revisionID: "test",
            manufacturer: "Fixture",
            name: "One handed",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            handCapacity: 1,
            contacts: [contact],
            productURL: productURL,
            photoAssetName: nil
        )
        XCTAssertTrue(oneHanded.isOneHanded)
        let resolvedOneHanded = WorkoutLiveStepResolver.materialized(
            bilateral,
            selectedHandSide: .left,
            boardIsOneHanded: oneHanded.isOneHanded
        )
        XCTAssertEqual(resolvedOneHanded.handUse, .single)
        XCTAssertEqual(resolvedOneHanded.side, .left)

        let twoHanded = BoardRevision(
            id: "fixture.two-handed",
            revisionID: "test",
            manufacturer: "Fixture",
            name: "Two handed",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            handCapacity: 2,
            contacts: [contact],
            productURL: productURL,
            photoAssetName: nil
        )
        XCTAssertFalse(twoHanded.isOneHanded)
        XCTAssertEqual(
            WorkoutLiveStepResolver.materialized(
                bilateral,
                selectedHandSide: .left,
                boardIsOneHanded: twoHanded.isOneHanded
            ),
            bilateral
        )

        let omittedDefault = BoardRevision(
            id: "fixture.omitted-default",
            revisionID: "test",
            manufacturer: "Fixture",
            name: "Default two handed",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            contacts: [contact],
            productURL: productURL,
            photoAssetName: nil
        )
        XCTAssertEqual(omittedDefault.handCapacity, 2)
        XCTAssertFalse(omittedDefault.isOneHanded)
        XCTAssertEqual(
            WorkoutLiveStepResolver.materialized(
                bilateral,
                selectedHandSide: .left,
                boardIsOneHanded: omittedDefault.isOneHanded
            ),
            bilateral
        )
    }

    func testOneHandedBoardResolutionNormalizesBilateralTargetsToSingleSelection() throws {
        let bilateral = WorkoutStep(
            id: "bilateral", number: 1, title: "Both hands", instruction: "Hang.",
            accessory: "", duration: 7, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement(kind: .jug, selection: .bilateralPair)]),
                timing: .fixed,
                duration: 7
            )],
            handUse: .double, side: .both
        )

        let resolved = try XCTUnwrap(
            bilateral.resolvingEitherHand(selectedHandSide: .left, boardIsOneHanded: true)
        )

        XCTAssertEqual(resolved.handUse, .single)
        XCTAssertEqual(resolved.side, .left)
        XCTAssertEqual(resolved.workRequirements, [ContactRequirement(kind: .jug, selection: .single)])
        XCTAssertEqual(
            resolved.segments.first?.contactRequirements,
            [ContactRequirement(kind: .jug, selection: .single)]
        )
    }

    func testSessionHandPreferenceMapsLeftRightOnly() {
        XCTAssertEqual(WorkoutSessionHandPreference.left.selectedHandSide, .left)
        XCTAssertEqual(WorkoutSessionHandPreference.right.selectedHandSide, .right)
        XCTAssertNil(WorkoutSessionHandPreference.alternate.selectedHandSide)
        XCTAssertNil(WorkoutSessionHandPreference.both.selectedHandSide)
    }

    func testNeedsHandChoiceGatesOnEitherOrOneHandedDoubleNotBareBoard() {
        let either = WorkoutStep(
            id: "either", number: 1, title: "Either", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang, handUse: .either, side: .both
        )
        let bilateral = WorkoutStep(
            id: "bilateral", number: 1, title: "Both", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang, handUse: .double, side: .both
        )
        let fixedSingle = WorkoutStep(
            id: "left", number: 1, title: "Left", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang, handUse: .single, side: .left
        )
        let rest = WorkoutStep(
            id: "rest", number: 2, title: "Rest", instruction: "Rest.",
            accessory: "", duration: 30, phase: .rest,
            handUse: .double, side: .both
        )

        XCTAssertTrue(
            WorkoutSessionHandResolver.needsHandChoice(steps: [either], boardIsOneHanded: false)
        )
        XCTAssertTrue(
            WorkoutSessionHandResolver.needsHandChoice(steps: [bilateral], boardIsOneHanded: true)
        )
        XCTAssertFalse(
            WorkoutSessionHandResolver.needsHandChoice(steps: [bilateral], boardIsOneHanded: false)
        )
        XCTAssertFalse(
            WorkoutSessionHandResolver.needsHandChoice(steps: [fixedSingle], boardIsOneHanded: true),
            "One-handed board alone must not force a hand choice when no step needs resolution"
        )
        XCTAssertFalse(
            WorkoutSessionHandResolver.needsHandChoice(
                steps: [fixedSingle, rest],
                boardIsOneHanded: true
            ),
            "Default .double rests must not force a hand choice on one-handed boards"
        )
    }

    func testSessionStepsLeaveRestUnchangedForAllPreferences() throws {
        let work = WorkoutStep(
            id: "either", number: 1, title: "Either", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement(kind: .jug, selection: .single)]),
                timing: .fixed,
                duration: 10
            )],
            handUse: .either, side: .both
        )
        let rest = WorkoutStep(
            id: "rest", number: 2, title: "Rest", instruction: "Rest.",
            accessory: "", duration: 30, phase: .rest,
            segments: [WorkoutSegment(
                kind: .rest,
                target: nil,
                timing: .fixed,
                duration: 30
            )],
            handUse: .double, side: .both
        )

        for preference in [
            WorkoutSessionHandPreference.left,
            .right,
            .both,
            .alternate
        ] {
            let resolved = WorkoutSessionHandResolver.sessionSteps(
                from: [work, rest],
                preference: preference,
                boardIsOneHanded: true
            )
            let resolvedRest = try XCTUnwrap(resolved.first { $0.id == "rest" })
            XCTAssertEqual(resolvedRest.id, rest.id, "\(preference)")
            XCTAssertEqual(resolvedRest.title, rest.title, "\(preference)")
            XCTAssertEqual(resolvedRest.instruction, rest.instruction, "\(preference)")
            XCTAssertEqual(resolvedRest.duration, rest.duration, "\(preference)")
            XCTAssertEqual(resolvedRest.phase, rest.phase, "\(preference)")
            XCTAssertEqual(resolvedRest.segments, rest.segments, "\(preference)")
            XCTAssertEqual(resolvedRest.workRequirements, rest.workRequirements, "\(preference)")
            XCTAssertEqual(resolvedRest.handUse, .double, "\(preference)")
            XCTAssertEqual(resolvedRest.side, .both, "\(preference)")
            XCTAssertEqual(resolvedRest.action, rest.action, "\(preference)")
        }
    }

    func testSessionStepsLeftRightMaterializeEitherAndOneHandedDouble() {
        let either = WorkoutStep(
            id: "either", number: 1, title: "Either", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement(kind: .jug, selection: .single)]),
                timing: .fixed,
                duration: 10
            )],
            handUse: .either, side: .both
        )
        let bilateral = WorkoutStep(
            id: "bilateral", number: 2, title: "Both", instruction: "Hang.",
            accessory: "", duration: 7, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement(kind: .jug, selection: .bilateralPair)]),
                timing: .fixed,
                duration: 7
            )],
            handUse: .double, side: .both
        )

        let leftSteps = WorkoutSessionHandResolver.sessionSteps(
            from: [either, bilateral],
            preference: .left,
            boardIsOneHanded: true
        )
        XCTAssertEqual(leftSteps.map(\.id), ["either", "bilateral"])
        XCTAssertEqual(leftSteps.map(\.side), [.left, .left])
        XCTAssertEqual(leftSteps.map(\.handUse), [.single, .single])
        XCTAssertEqual(leftSteps.map(\.number), [1, 2])

        let rightSteps = WorkoutSessionHandResolver.sessionSteps(
            from: [either],
            preference: .right,
            boardIsOneHanded: false
        )
        XCTAssertEqual(rightSteps.first?.side, .right)
        XCTAssertEqual(rightSteps.first?.handUse, .single)
    }

    func testSessionStepsBothPairsHoldsOnTwoHandedBoardsAndUsesSingleHoldOnOneHandedBoards() throws {
        let either = WorkoutStep(
            id: "either", number: 1, title: "Both", instruction: "Hang.",
            accessory: "", duration: 7, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement(kind: .jug, selection: .single)]),
                timing: .fixed,
                duration: 7
            )],
            handUse: .either, side: .both
        )

        let twoHanded = try XCTUnwrap(
            WorkoutSessionHandResolver.sessionSteps(
                from: [either],
                preference: .both,
                boardIsOneHanded: false
            ).first
        )
        XCTAssertEqual(twoHanded.handUse, .double)
        XCTAssertEqual(twoHanded.side, .both)
        XCTAssertEqual(twoHanded.workRequirements.map(\.selection), [.bilateralPair])
        XCTAssertEqual(
            twoHanded.segments.first?.contactRequirements.map(\.selection),
            [.bilateralPair]
        )

        let oneHanded = try XCTUnwrap(
            WorkoutSessionHandResolver.sessionSteps(
                from: [either],
                preference: .both,
                boardIsOneHanded: true
            ).first
        )
        XCTAssertEqual(oneHanded.handUse, .double)
        XCTAssertEqual(oneHanded.side, .both)
        XCTAssertEqual(oneHanded.workRequirements.map(\.selection), [.single])
        XCTAssertEqual(
            oneHanded.segments.first?.contactRequirements.map(\.selection),
            [.single]
        )
    }

    func testSessionStepsAlternateExpandsLeftThenRightWithoutDuplicatingRest() {
        let either = WorkoutStep(
            id: "hang", number: 1, title: "Hang", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement(kind: .edge, selection: .single)]),
                timing: .fixed,
                duration: 10
            )],
            handUse: .either, side: .both
        )
        let rest = WorkoutStep(
            id: "rest", number: 2, title: "Rest", instruction: "Rest.",
            accessory: "", duration: 30, phase: .rest,
            handUse: .double, side: .both
        )
        let fixed = WorkoutStep(
            id: "fixed-left", number: 3, title: "Left only", instruction: "Hang.",
            accessory: "", duration: 5, phase: .hang,
            handUse: .single, side: .left
        )

        let expanded = WorkoutSessionHandResolver.sessionSteps(
            from: [either, rest, fixed],
            preference: .alternate,
            boardIsOneHanded: false
        )

        XCTAssertEqual(expanded.map(\.id), ["hang.left", "hang.right", "rest", "fixed-left"])
        XCTAssertEqual(expanded.map(\.side), [.left, .right, .both, .left])
        XCTAssertEqual(expanded.map(\.handUse), [.single, .single, .double, .single])
        XCTAssertEqual(expanded.map(\.number), [1, 2, 3, 4])
        XCTAssertEqual(Set(expanded.map(\.id)).count, expanded.count)
        XCTAssertEqual(
            expanded.reduce(0) { $0 + $1.duration },
            either.duration * 2 + rest.duration + fixed.duration
        )

        // Already-expanded singles are identity under preference materialize.
        for step in expanded where step.handUse == .single {
            XCTAssertEqual(
                WorkoutSessionHandResolver.materialized(
                    step,
                    preference: .alternate,
                    boardIsOneHanded: false
                ),
                step
            )
        }
    }

    func testSessionStepsAlternateExpandsOneHandedDouble() {
        let bilateral = WorkoutStep(
            id: "bilateral", number: 1, title: "Both", instruction: "Hang.",
            accessory: "", duration: 7, phase: .hang,
            segments: [WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement(kind: .jug, selection: .bilateralPair)]),
                timing: .fixed,
                duration: 7
            )],
            handUse: .double, side: .both
        )

        let expanded = WorkoutSessionHandResolver.sessionSteps(
            from: [bilateral],
            preference: .alternate,
            boardIsOneHanded: true
        )
        XCTAssertEqual(expanded.map(\.id), ["bilateral.left", "bilateral.right"])
        XCTAssertEqual(expanded.map(\.side), [.left, .right])
        XCTAssertEqual(expanded.map(\.handUse), [.single, .single])
        XCTAssertEqual(
            expanded.map { $0.workRequirements.map(\.selection) },
            [[.single], [.single]]
        )
    }

    func testHandCuePolicyHidesOppositeCueAfterEitherHandMaterializes() {
        let eitherHand = WorkoutStep(
            id: "either", number: 1, title: "Either hand", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang, handUse: .either,
            side: .both
        )
        let resolved = WorkoutLiveStepResolver.materialized(
            eitherHand,
            selectedHandSide: .right
        )

        XCTAssertFalse(WorkoutHoldCueVisibilityPolicy.showsCue(for: .left, step: resolved))
        XCTAssertTrue(WorkoutHoldCueVisibilityPolicy.showsCue(for: .right, step: resolved))
    }

    /// Portrait renders its two cue cards from a bare per-side check rather than
    /// the landscape slot policy, so pin the shared rule both orientations call:
    /// a cue step derived from a resting current step still hides the idle hand.
    func testPerSideCueRuleHidesTheIdleHandForACueStepDerivedFromRest() throws {
        let rest = WorkoutStep(
            id: "rest", number: 1, title: "Rest", instruction: "Rest.",
            accessory: "", duration: 30, phase: .rest)
        let singleRight = WorkoutStep(
            id: "work-right", number: 2, title: "Right hang", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang,
            gripType: .halfCrimp, handUse: .single, side: .right
        )
        let timeline = WorkoutTimeline(steps: [rest, singleRight])
        let cueStep = try XCTUnwrap(
            timeline.boardCue(at: 15, countdown: 0, isComplete: false).step
        )

        XCTAssertEqual(cueStep.id, singleRight.id)
        XCTAssertFalse(WorkoutHoldCueVisibilityPolicy.showsCue(for: .left, step: cueStep))
        XCTAssertTrue(WorkoutHoldCueVisibilityPolicy.showsCue(for: .right, step: cueStep))
        // The resting current step is bilateral, which is what made both cards render.
        XCTAssertTrue(WorkoutHoldCueVisibilityPolicy.showsCue(for: .left, step: rest))
        XCTAssertTrue(WorkoutHoldCueVisibilityPolicy.showsCue(for: .right, step: rest))
    }

    func testLandscapeHandCueFollowsCueStepWhileCurrentStepIsResting() throws {
        let leftWork = WorkoutStep(
            id: "work-left", number: 1, title: "Left hang", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang,
            gripType: .halfCrimp, handUse: .single, side: .left
        )
        let rest = WorkoutStep(
            id: "rest", number: 2, title: "Rest", instruction: "Rest.",
            accessory: "", duration: 30, phase: .rest)
        let eitherWork = WorkoutStep(
            id: "work-either", number: 3, title: "Either hang", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang,
            gripType: .halfCrimp, handUse: .either, side: .both
        )
        let timeline = WorkoutTimeline(steps: [leftWork, rest, eitherWork])
        let elapsed: TimeInterval = 15
        let boardCue = timeline.boardCue(at: elapsed, countdown: 0, isComplete: false)
        let currentStep = try XCTUnwrap(timeline.step(at: elapsed))
        let cueStep = WorkoutLiveStepResolver.materialized(
            try XCTUnwrap(boardCue.step),
            selectedHandSide: .right
        )
        let holdCue = WorkoutHoldCue(gripType: .halfCrimp)

        XCTAssertTrue(boardCue.isResting)
        XCTAssertEqual(currentStep.id, rest.id)
        XCTAssertEqual(cueStep.id, eitherWork.id)
        // The resting current step is bilateral, so keying the per-side slot off
        // it would light up both cards for a single-hand cue.
        XCTAssertTrue(WorkoutHoldCueVisibilityPolicy.showsCue(for: .left, step: currentStep))
        XCTAssertTrue(WorkoutHoldCueVisibilityPolicy.showsCue(for: .right, step: currentStep))

        XCTAssertFalse(
            WorkoutLandscapeHandCuePolicy.showsHandCue(
                for: .left,
                holdCue: holdCue,
                cueStep: cueStep,
                countdown: 0,
                isComplete: false,
                isSkipCountdown: false
            )
        )
        XCTAssertTrue(
            WorkoutLandscapeHandCuePolicy.showsHandCue(
                for: .right,
                holdCue: holdCue,
                cueStep: cueStep,
                countdown: 0,
                isComplete: false,
                isSkipCountdown: false
            )
        )
    }

    func testLandscapeHandCueShowsBothSlotsForBilateralCueStep() {
        let bilateral = WorkoutStep(
            id: "bilateral", number: 1, title: "Both hands", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang,
            gripType: .halfCrimp, handUse: .double, side: .both
        )
        let holdCue = WorkoutHoldCue(gripType: .halfCrimp)

        for side in [WorkoutSide.left, .right] {
            XCTAssertTrue(
                WorkoutLandscapeHandCuePolicy.showsHandCue(
                    for: side,
                    holdCue: holdCue,
                    cueStep: bilateral,
                    countdown: 0,
                    isComplete: false,
                    isSkipCountdown: false
                ),
                "\(side) slot should show for a bilateral cue step"
            )
        }
    }

    func testLandscapeHandCueStillHonoursTheCountdownAndCompletionGate() {
        let rightWork = WorkoutStep(
            id: "work-right", number: 1, title: "Right hang", instruction: "Hang.",
            accessory: "", duration: 10, phase: .hang,
            gripType: .halfCrimp, handUse: .single, side: .right
        )
        let holdCue = WorkoutHoldCue(gripType: .halfCrimp)

        XCTAssertFalse(
            WorkoutLandscapeHandCuePolicy.showsHandCue(
                for: .right,
                holdCue: holdCue,
                cueStep: rightWork,
                countdown: 3,
                isComplete: false,
                isSkipCountdown: false
            )
        )
        XCTAssertTrue(
            WorkoutLandscapeHandCuePolicy.showsHandCue(
                for: .right,
                holdCue: holdCue,
                cueStep: rightWork,
                countdown: 3,
                isComplete: false,
                isSkipCountdown: true
            )
        )
        XCTAssertFalse(
            WorkoutLandscapeHandCuePolicy.showsHandCue(
                for: .right,
                holdCue: nil,
                cueStep: rightWork,
                countdown: 0,
                isComplete: false,
                isSkipCountdown: false
            )
        )
    }

    private func loadedLiftStep(
        id: String = "loaded-lift",
        repetitions: Int,
        externalLoadKGF: Double? = nil
    ) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 1,
            title: "Loaded lift",
            instruction: "",
            accessory: "",
            duration: 30,
            phase: .pull,
            handUse: .single,
            side: .left,
            action: .loadedLift,
            repetitions: repetitions,
            externalLoadKGF: externalLoadKGF
        )
    }

    func testLoadedLiftTimelineShowsPrescribedRepetitions() {
        let step = loadedLiftStep(repetitions: 7)

        XCTAssertTrue(WorkoutTimeline.labels(for: step).contains("7 lifts"))
    }

    func testLoadedLiftCompletionCapsAtPrescribedRepetitions() {
        let step = loadedLiftStep(repetitions: 2)
        var completion = WorkoutLiftCompletion()

        completion.completeLift(for: step)
        completion.completeLift(for: step)
        completion.completeLift(for: step)

        XCTAssertEqual(completion.completedRepetitions(for: step), 2)
    }

    func testLoadedLiftCompletionRequiresAnActiveStartedSession() {
        XCTAssertFalse(
            WorkoutLiftCompletionPolicy.isEnabled(
                completedRepetitions: 0,
                prescribedRepetitions: 7,
                sessionCanNavigate: false
            )
        )
        XCTAssertFalse(
            WorkoutLiftCompletionPolicy.isEnabled(
                completedRepetitions: 7,
                prescribedRepetitions: 7,
                sessionCanNavigate: true
            )
        )
        XCTAssertTrue(
            WorkoutLiftCompletionPolicy.isEnabled(
                completedRepetitions: 6,
                prescribedRepetitions: 7,
                sessionCanNavigate: true
            )
        )
    }

    func testLoadedLiftRuntimeLoadDefaultsFromPlanAndCanBeChangedPerStep() {
        let first = loadedLiftStep(repetitions: 2, externalLoadKGF: 12)
        let second = loadedLiftStep(id: "second-lift", repetitions: 2, externalLoadKGF: -5)
        var completion = WorkoutLiftCompletion()

        XCTAssertEqual(completion.externalLoadKGF(for: first), 12)
        XCTAssertEqual(completion.externalLoadKGF(for: second), -5)

        completion.setExternalLoadKGF(18.5, for: first)

        XCTAssertEqual(completion.externalLoadKGF(for: first), 18.5)
        XCTAssertEqual(completion.externalLoadKGF(for: second), -5)
    }

    func testRestTimelineLabelDoesNotClaimHangOrBothHands() {
        let rest = WorkoutStep(
            id: "rest",
            number: 1,
            title: "Rest",
            instruction: "",
            accessory: "",
            duration: 30,
            phase: .rest)

        XCTAssertEqual(WorkoutTimeline.labels(for: rest), ["Rest"])
    }

    func testHighlightResolverUsesCenterNearestSemanticTargetForSingleHandSteps() {
        let board = BoardRevision(
            id: "portable",
            revisionID: "test-fixture",
            manufacturer: "Test",
            name: "Portable",
            subtitle: "",
            dimensions: "",
            aspectRatio: 1,
            equipmentObjects: [.init(id: "left-ring"), .init(id: "right-ring")],
            contacts: [
                PhysicalContact(
                    id: "left-pocket",
                    equipmentObjectID: "left-ring",
                    name: "Left pocket",
                    kind: .pocket,
                    side: .left
                ),
                PhysicalContact(
                    id: "left-edge",
                    equipmentObjectID: "left-ring",
                    name: "Left edge",
                    kind: .edge,
                    side: .left
                ),
                PhysicalContact(
                    id: "right-pocket",
                    equipmentObjectID: "right-ring",
                    name: "Right pocket",
                    kind: .pocket,
                    side: .right
                )
            ],
            productURL: URL(string: "https://example.com/portable")!,
            photoAssetName: nil,
            presentations: [
                rasterPresentation(frames: [
                    "left-pocket": CGRect(x: 0, y: 0, width: 0.2, height: 0.2),
                    "left-edge": CGRect(x: 0.2, y: 0, width: 0.2, height: 0.2),
                    "right-pocket": CGRect(x: 0.8, y: 0, width: 0.2, height: 0.2)
                ])
            ]
        )
        let step = WorkoutStep(
            id: "left",
            number: 1,
            title: "Left lift",
            instruction: "",
            accessory: "",
            duration: 30,
            phase: .pull,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.pocket)]),
                    timing: .undefined,
                    duration: nil
                )
            ],
            handUse: .single,
            side: .left,
            action: .loadedLift,
            repetitions: 1
        )

        XCTAssertEqual(
            WorkoutHighlightResolver.contactIDs(for: step, on: board),
            ["left-pocket"]
        )

        let rightStep = WorkoutStep(
            id: "right",
            number: 2,
            title: "Right lift",
            instruction: "",
            accessory: "",
            duration: 30,
            phase: .pull,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.pocket)]),
                    timing: .undefined,
                    duration: nil
                )
            ],
            handUse: .single,
            side: .right,
            action: .loadedLift,
            repetitions: 1
        )
        XCTAssertEqual(
            WorkoutHighlightResolver.contactIDs(for: rightStep, on: board),
            ["left-pocket"]
        )
    }

    func testHighlightResolverDoesNotSubstituteForMissingRequiredFeatures() {
        let board = BoardRevision(
            id: "portable-fallback",
            revisionID: "test-fixture",
            manufacturer: "Test",
            name: "Portable fallback",
            subtitle: "",
            dimensions: "",
            aspectRatio: 1,
            equipmentObjects: [.init(id: "left"), .init(id: "right")],
            contacts: [
                PhysicalContact(
                    id: "left-edge",
                    equipmentObjectID: "left",
                    name: "Left edge",
                    kind: .edge,
                ),
                PhysicalContact(
                    id: "right-edge",
                    equipmentObjectID: "right",
                    name: "Right edge",
                    kind: .edge,
                )
            ],
            productURL: URL(string: "https://example.com/portable-fallback")!,
            photoAssetName: nil,
            presentations: [
                rasterPresentation(frames: [
                    "left-edge": CGRect(x: 0, y: 0, width: 0.2, height: 0.2),
                    "right-edge": CGRect(x: 0.8, y: 0, width: 0.2, height: 0.2)
                ])
            ]
        )
        let step = WorkoutStep(
            id: "fallback",
            number: 1,
            title: "Fallback",
            instruction: "",
            accessory: "",
            duration: 30,
            phase: .pull,
            action: .loadedLift,
            repetitions: 1
        )

        XCTAssertEqual(
            WorkoutHighlightResolver.contactIDs(for: step, on: board),
            []
        )
    }

    func testHoldCueRejectsIncompatibleNonEmptyContactGripMetadataForStepGrip() {
        let hold = PhysicalContact(
            id: "cue-edge",
            name: "Cue edge",
            kind: .edge,
            gripTypes: [.openHand]
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.edge)]),
                    timing: .undefined,
                    duration: nil
                )
            ],
            gripType: .halfCrimp,
            fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .ring])
        )

        let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))

        XCTAssertNil(cue)
    }

    func testHoldCueDoesNotInferGripFromBoardMetadata() {
        let hold = PhysicalContact(
            id: "cue-pocket",
            name: "Cue pocket",
            kind: .pocket,
            fingerCapacity: 3,
            gripTypes: [.openHand]
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.pocket)]),
                    timing: .undefined,
                    duration: nil
                )
            ]
        )

        let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))

        XCTAssertNil(cue)
    }

    func testHoldCueAcceptsHighlightedRequiredFeatureHold() {
        let hold = PhysicalContact(
            id: "fallback-edge",
            name: "Fallback edge",
            kind: .edge,
            depth: .category(.large),
            gripTypes: [.halfCrimp]
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.edge(depth: .category(.large))]),
                    timing: .undefined,
                    duration: nil
                )
            ],
            gripType: .halfCrimp
        )

        let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))

        XCTAssertEqual(cue?.hold, hold)
    }

    func testHoldCueIsUnavailableForMultiTargetSteps() {
        let hold = PhysicalContact(
            id: "cue-edge",
            name: "Cue edge",
            kind: .edge,
            gripTypes: [.halfCrimp]
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.edge), .kind(.jug)]),
                    timing: .undefined,
                    duration: nil
                )
            ]
        )

        XCTAssertNil(WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold])))
    }

    func testHoldCueResolvesWhenHighlightedHoldMatchesSingleTarget() {
        let hold = PhysicalContact(
            id: "cue-edge",
            name: "Cue edge",
            kind: .edge,
            gripTypes: [.halfCrimp]
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.edge, selection: .single)]),
                    timing: .undefined,
                    duration: nil
                )
            ],
            gripType: .halfCrimp
        )

        XCTAssertNotNil(
            WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))
        )
    }

    func testHoldCueKeepsSourceBackedGripWhenRequirementDoesNotResolveOnBoard() {
        let fingers = FingerConfiguration(
            engagedFingers: [.index, .middle, .ring, .pinky]
        )
        let step = WorkoutStep(
            id: "max-hang-cue",
            number: 1,
            title: "Max hang",
            instruction: "Hang on a 20 mm edge.",
            accessory: "7s",
            duration: 7,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([
                        .edge(depth: .range(.init(minimum: 20, maximum: 20)))
                    ]),
                    timing: .fixed,
                    duration: 7
                )
            ],
            gripType: .halfCrimp,
            fingerConfiguration: fingers,
            handUse: .either
        )

        let cue = WorkoutHoldCuePolicy.resolve(
            step: step,
            hold: nil,
            on: board(containing: [
                PhysicalContact(
                    id: "edge-19",
                    name: "19 mm",
                    kind: .edge,
                    depth: .range(.init(minimum: 19, maximum: 19))
                )
            ])
        )

        XCTAssertNil(cue?.hold)
        XCTAssertEqual(cue?.gripType, .halfCrimp)
        XCTAssertEqual(cue?.fingerConfiguration, fingers)
    }

    func testSelfSelectedWorkKeepsItsSourceBackedGripCueWithoutInventingAContact() {
        let fingers = FingerConfiguration(
            engagedFingers: [.index, .middle, .ring, .pinky]
        )
        let step = WorkoutStep(
            id: "self-selected-cue",
            number: 1,
            title: "Self-selected",
            instruction: "Use the prescribed grip on your selected contact.",
            accessory: "",
            duration: 10,
            phase: .hang,
            gripType: .halfCrimp,
            fingerConfiguration: fingers
        )

        let cue = WorkoutHoldCuePolicy.resolve(
            step: step,
            hold: nil,
            on: board(containing: [])
        )

        XCTAssertNil(cue?.hold)
        XCTAssertEqual(cue?.gripType, .halfCrimp)
        XCTAssertEqual(cue?.fingerConfiguration, fingers)
    }

    func testSourceBackedHoldCueRemainsVisibleAtCountdownZero() {
        let hold = PhysicalContact(
            id: "cue-edge",
            name: "Cue edge",
            kind: .edge,
            handCapacity: 2,
            gripTypes: [.halfCrimp]
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            gripType: .halfCrimp,
            fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .ring])
        )
        let holdCue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))

        XCTAssertTrue(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: holdCue,
                countdown: 0,
                isComplete: false
            )
        )
    }

    func testHoldCueVisibilityShowsAvailableCueDuringSkipCountdown() {
        let holdCue = WorkoutHoldCue(
            hold: PhysicalContact(
                id: "cue-edge",
                name: "Cue edge",
                kind: .edge,
            ),
            gripType: .openHand,
            fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .ring])
        )

        XCTAssertTrue(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: holdCue,
                countdown: 3,
                isComplete: false,
                isSkipCountdown: true
            )
        )
    }

    func testHoldCueVisibilityStillSuppressesCountdownCompletionAndMissingCue() {
        let holdCue = WorkoutHoldCue(
            hold: PhysicalContact(
                id: "cue-edge",
                name: "Cue edge",
                kind: .edge,
            ),
            gripType: .openHand
        )

        XCTAssertFalse(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: holdCue,
                countdown: 3,
                isComplete: false
            )
        )
        XCTAssertFalse(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: holdCue,
                countdown: 0,
                isComplete: true
            )
        )
        XCTAssertFalse(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: nil,
                countdown: 0,
                isComplete: false
            )
        )
    }

    func testHoldCueIsUnavailableWhenHighlightedHoldDoesNotMatchSingleTarget() {
        let targetHold = PhysicalContact(
            id: "target-edge",
            name: "Target edge",
            kind: .edge,
        )
        let highlightedHold = PhysicalContact(
            id: "highlighted-jug",
            name: "Highlighted jug",
            kind: .jug,
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.edge)]),
                    timing: .undefined,
                    duration: nil
                )
            ],
            gripType: .halfCrimp
        )

        XCTAssertNil(
            WorkoutHoldCuePolicy.resolve(
                step: step,
                hold: highlightedHold,
                on: board(containing: [targetHold, highlightedHold])
            )
        )
    }

    private func board(containing holds: [PhysicalContact]) -> BoardRevision {
        let frames = Dictionary(uniqueKeysWithValues: holds.enumerated().map { index, hold in
            (hold.id, CGRect(x: Double(index) * 0.1, y: 0, width: 0.1, height: 0.1))
        })
        return BoardRevision(
            id: "cue-board",
            revisionID: "test-fixture",
            manufacturer: "Test",
            name: "Cue board",
            subtitle: "",
            dimensions: "",
            aspectRatio: 1,
            contacts: holds,
            productURL: URL(string: "https://example.com/cue-board")!,
            photoAssetName: nil,
            presentations: [rasterPresentation(frames: frames)]
        )
    }

    private func rasterPresentation(frames: [String: CGRect]) -> BoardPresentation {
        let geometry = Dictionary(uniqueKeysWithValues: frames.map { id, frame in
            (id, [BoardContactPiece(
                id: "\(id)-piece",
                contactID: id,
                frame: frame,
                shape: .roundedRect(cornerRadiusFraction: 0),
                treatment: .surface
            )])
        })
        return BoardPresentation(
            id: "primary",
            name: "Primary",
            aspectRatio: 1,
            isDefault: true,
            media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry))
        )
    }

    private let steps: [WorkoutStep] = [
        WorkoutStep(
            id: "first",
            number: 1,
            title: "First",
            instruction: "First instruction",
            accessory: "First accessory",
            duration: 60,
            phase: .hang,
            timedWorkDuration: 30
        ),
        WorkoutStep(
            id: "second",
            number: 2,
            title: "Second",
            instruction: "Second instruction",
            accessory: "Second accessory",
            duration: 20,
            phase: .rest),
        WorkoutStep(
            id: "third",
            number: 3,
            title: "Third",
            instruction: "Third instruction",
            accessory: "Third accessory",
            duration: 10,
            phase: .hang)
    ]

    func testDurationAndOffsetsIncludeWholeSteps() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.duration, 90)
        XCTAssertEqual(timeline.startOffset(for: "first"), 0)
        XCTAssertEqual(timeline.startOffset(for: "second"), 60)
        XCTAssertEqual(timeline.startOffset(for: "third"), 80)
    }

    func testExactBoundaryResolvesToFollowingStep() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.step(at: 60)?.id, "second")
        XCTAssertEqual(timeline.elapsedInStep(at: 65), 5)
    }

    func testNegativeElapsedClampsToTheFirstStep() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.step(at: -1)?.id, "first")
        XCTAssertEqual(timeline.elapsedInStep(at: -1), 0)
    }

    func testElapsedAtOrPastPlanDurationClampsToTheFinalStep() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.step(at: 90)?.id, "third")
        XCTAssertEqual(timeline.elapsedInStep(at: 90), 10)
        XCTAssertEqual(timeline.step(at: 120)?.id, "third")
        XCTAssertEqual(timeline.elapsedInStep(at: 120), 10)
    }

    func testSelectionTargetsDifferentStepStartsAndCurrentStepIsNoOp() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.selectionTarget(for: "third", at: 10), 80)
        XCTAssertEqual(timeline.selectionTarget(for: "first", at: 75), 0)
        XCTAssertNil(timeline.selectionTarget(for: "second", at: 75))
    }

    func testSkipUsesTheFullStepBoundaryIncludingRest() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.skipTarget(from: 45), 60)
        XCTAssertEqual(timeline.skipTarget(from: 65), 80)
    }

    func testSkippingTheFinalStepStopsAtPlanDuration() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.skipTarget(from: 85), 90)
        XCTAssertEqual(timeline.selectionTarget(for: "third", at: 65), 80)
    }

    func testEmptyTimelineHasNoNavigationTargets() {
        let timeline = WorkoutTimeline(steps: [])

        XCTAssertEqual(timeline.duration, 0)
        XCTAssertNil(timeline.step(at: 0))
        XCTAssertNil(timeline.startOffset(for: "missing"))
        XCTAssertNil(timeline.selectionTarget(for: "missing", at: 0))
        XCTAssertNil(timeline.skipTarget(from: 0))
    }

    private let restPreviewSteps: [WorkoutStep] = [
        WorkoutStep(
            id: "work",
            number: 1,
            title: "Work",
            instruction: "Work instruction",
            accessory: "Work accessory",
            duration: 30,
            phase: .hang,
            timedWorkDuration: 15
        ),
        WorkoutStep(
            id: "rest-one",
            number: 2,
            title: "Rest one",
            instruction: "Rest instruction",
            accessory: "Rest accessory",
            duration: 10,
            phase: .rest),
        WorkoutStep(
            id: "rest-two",
            number: 3,
            title: "Rest two",
            instruction: "Rest instruction",
            accessory: "Rest accessory",
            duration: 10,
            phase: .rest),
        WorkoutStep(
            id: "next-work",
            number: 4,
            title: "Next work",
            instruction: "Next work instruction",
            accessory: "Next work accessory",
            duration: 20,
            phase: .pull),
        WorkoutStep(
            id: "final-rest",
            number: 5,
            title: "Final rest",
            instruction: "Final rest instruction",
            accessory: "Final rest accessory",
            duration: 5,
            phase: .rest)
    ]

    func testNextWorkStepSkipsConsecutiveRestSteps() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        XCTAssertEqual(timeline.nextWorkStep(after: "work")?.id, "next-work")
        XCTAssertEqual(timeline.nextWorkStep(after: "rest-one")?.id, "next-work")
        XCTAssertEqual(timeline.nextWorkStep(after: "rest-two")?.id, "next-work")
        XCTAssertNil(timeline.nextWorkStep(after: "next-work"))
    }

    func testHoldPreviewUsesNextWorkStepDuringTimedAndExplicitRest() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        XCTAssertEqual(timeline.holdPreviewStep(at: 5)?.id, "work")
        XCTAssertEqual(timeline.holdPreviewStep(at: 20)?.id, "next-work")
        XCTAssertEqual(timeline.holdPreviewStep(at: 35)?.id, "next-work")
    }

    func testHoldPreviewWithCurrentStepAndElapsedUsesProvidedLocation() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        XCTAssertEqual(
            timeline.holdPreviewStep(
                currentStep: restPreviewSteps[0],
                stepElapsed: 15
            )?.id,
            "next-work"
        )
        XCTAssertEqual(
            timeline.holdPreviewStep(
                currentStep: restPreviewSteps[0],
                stepElapsed: 5
            )?.id,
            "work"
        )
        XCTAssertEqual(
            timeline.holdPreviewStep(
                currentStep: restPreviewSteps[1],
                stepElapsed: 2
            )?.id,
            "next-work"
        )
    }

    func testHoldPreviewHasNoHighlightSourceAfterTheFinalRestStep() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        XCTAssertNil(timeline.holdPreviewStep(at: 72))
    }

    func testBoardCueUsesNextWorkStepAndPreviewModeDuringRest() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let cue = timeline.boardCue(at: 35, countdown: 0, isComplete: false)

        XCTAssertEqual(cue.step?.id, "next-work")
        XCTAssertEqual(cue.mode, .preview)
        XCTAssertTrue(cue.isResting)
        XCTAssertFalse(cue.isSuppressed)
    }

    func testBoardCuePreviewsDestinationWorkStepDuringSkipCountdown() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let cue = timeline.boardCue(
            currentStep: restPreviewSteps[3],
            stepElapsed: 0,
            countdown: 3,
            isComplete: false,
            isSkipCountdown: true
        )

        XCTAssertEqual(cue.step?.id, "next-work")
        XCTAssertEqual(cue.mode, .preview)
        XCTAssertFalse(cue.isResting)
        XCTAssertFalse(cue.isSuppressed)
    }

    func testBoardCueUsesProvidedTimedRestLocationWithoutRecomputingIt() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let elapsedCue = timeline.boardCue(at: 20, countdown: 0, isComplete: false)
        let suppliedCue = timeline.boardCue(
            currentStep: restPreviewSteps[0],
            stepElapsed: 20,
            countdown: 0,
            isComplete: false
        )

        XCTAssertEqual(elapsedCue.step?.id, "next-work")
        XCTAssertEqual(elapsedCue.mode, .preview)
        XCTAssertTrue(elapsedCue.isResting)
        XCTAssertEqual(suppliedCue, elapsedCue)
    }

    func testBoardCueUsesActiveModeDuringWork() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let cue = timeline.boardCue(at: 5, countdown: 0, isComplete: false)

        XCTAssertEqual(cue.step?.id, "work")
        XCTAssertEqual(cue.mode, .active)
        XCTAssertFalse(cue.isResting)
        XCTAssertFalse(cue.isSuppressed)
    }

    func testBoardCueSuppressesCountdownAndCompletion() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let countdownCue = timeline.boardCue(at: 5, countdown: 3, isComplete: false)
        XCTAssertNil(countdownCue.step)
        XCTAssertTrue(countdownCue.isSuppressed)

        let completionCue = timeline.boardCue(at: 72, countdown: 0, isComplete: true)
        XCTAssertNil(completionCue.step)
        XCTAssertTrue(completionCue.isSuppressed)
    }

    func testBoardCueKeepsFinalRestAsRecoveryWithoutPreviewStep() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let cue = timeline.boardCue(at: 72, countdown: 0, isComplete: false)

        XCTAssertNil(cue.step)
        XCTAssertEqual(cue.mode, .preview)
        XCTAssertTrue(cue.isResting)
        XCTAssertFalse(cue.isSuppressed)
    }

    func testRestPreviewStrokeCompanionIsOpaqueAndDarkerThanRestBlue() {
        let fill = UIColor(Color.restBlue)
        let stroke = UIColor(Color.restBlueDeep)
        var fillRed: CGFloat = 0
        var fillGreen: CGFloat = 0
        var fillBlue: CGFloat = 0
        var fillAlpha: CGFloat = 0
        var strokeRed: CGFloat = 0
        var strokeGreen: CGFloat = 0
        var strokeBlue: CGFloat = 0
        var strokeAlpha: CGFloat = 0

        XCTAssertTrue(fill.getRed(&fillRed, green: &fillGreen, blue: &fillBlue, alpha: &fillAlpha))
        XCTAssertTrue(stroke.getRed(&strokeRed, green: &strokeGreen, blue: &strokeBlue, alpha: &strokeAlpha))
        XCTAssertEqual(strokeAlpha, 1, accuracy: 0.001)
        XCTAssertLessThan(strokeRed, fillRed)
        XCTAssertLessThan(strokeGreen, fillGreen)
        XCTAssertLessThan(strokeBlue, fillBlue)
    }

    func testBilateralSelectionWidensSingleRequirementToPair() {
        let single = ContactRequirement(kind: .edge, fingerCapacity: 4, selection: .single)
        XCTAssertEqual(single.bilateralSelection.selection, .bilateralPair)
        XCTAssertEqual(single.bilateralSelection.kind, .edge)
        XCTAssertEqual(single.bilateralSelection.fingerCapacity, 4)

        let alreadyPaired = ContactRequirement(kind: .edge, selection: .bilateralPair)
        XCTAssertEqual(alreadyPaired.bilateralSelection, alreadyPaired)

        let pinned = ContactRequirement(contactID: "left-edge", kind: .edge, selection: .single)
        XCTAssertEqual(
            pinned.bilateralSelection,
            pinned,
            "An exact contact cannot form a pair and must stay single"
        )

        let pinnedPair = ContactRequirement(contactID: "left-edge", kind: .edge, selection: .bilateralPair)
        XCTAssertEqual(pinnedPair.bilateralSelection.selection, .single)
    }

    func testDefaultHandPreferenceFollowsBoardCapacity() {
        XCTAssertEqual(WorkoutSessionHandPreference.defaultPreference(boardHandCapacity: 2), .both)
        XCTAssertEqual(WorkoutSessionHandPreference.defaultPreference(boardHandCapacity: 1), .alternate)
    }

    func testHandChoiceCopyOnlySaysTwoBoardsForOneHandedBoards() {
        XCTAssertEqual(HandChoiceCopy.bothHandsTitle(boardIsOneHanded: false), "Both hands")
        XCTAssertEqual(HandChoiceCopy.bothHandsTitle(boardIsOneHanded: true), "Both hands (two boards)")
        XCTAssertEqual(
            HandChoiceCopy.bothHandsHint(boardIsOneHanded: false),
            "Both hands simultaneously on this board."
        )
        XCTAssertEqual(
            HandChoiceCopy.bothHandsHint(boardIsOneHanded: true),
            "Both hands simultaneously on two boards."
        )
    }

    func testResolutionAwareDefaultFallsBackToAlternateWhenBothCannotResolve() {
        let board = BoardRevision(
            id: "fixture.single-contact",
            revisionID: "test",
            manufacturer: "Fixture",
            name: "Single contact",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            handCapacity: 2,
            contacts: [
                PhysicalContact(id: "only-edge", name: "Only edge", kind: .edge, handCapacity: 1)
            ],
            productURL: URL(string: "https://example.com/board")!,
            photoAssetName: nil
        )
        let plan = TrainingPlan(
            id: "fixture.either",
            title: "Either",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/plan")!,
            provenance: .adapted,
            boardID: board.id,
            steps: [
                WorkoutStep(
                    id: "either", number: 1, title: "Either", instruction: "",
                    accessory: "", duration: 7, phase: .hang,
                    segments: [WorkoutSegment(
                        kind: .work,
                        target: .fromLegacyTargets([ContactRequirement(kind: .edge, selection: .single)]),
                        timing: .fixed,
                        duration: 7
                    )],
                    handUse: .either, side: .both
                )
            ]
        )

        XCTAssertFalse(WorkoutSessionHandResolver.bothHandsResolve(plan: plan, board: board))
        XCTAssertEqual(
            WorkoutSessionHandResolver.defaultPreference(plan: plan, board: board),
            .alternate
        )
    }

    func testResolutionAwareDefaultKeepsBothWhenAPairResolves() throws {
        let plan = try XCTUnwrap(PlanCatalog.all.first { $0.id == "research.max-hangs" })
        let board = try XCTUnwrap(
            BoardCatalog.all.first { board in
                plan.steps.allSatisfy { step in
                    guard !step.isRestStep else { return true }
                    let requirements = step.workRequirements
                    guard !requirements.isEmpty else { return true }
                    return (try? ContactResolver.resolve(requirements, step: step, board: board))?.isEmpty == false
                }
            },
            "Expected at least one registered board where Max Hangs resolves its pair"
        )

        let workStep = try XCTUnwrap(plan.steps.first { !$0.isRestStep })
        XCTAssertEqual(
            (try ContactResolver.resolve(workStep.workRequirements, step: workStep, board: board)).count,
            2
        )

        XCTAssertTrue(WorkoutSessionHandResolver.bothHandsResolve(plan: plan, board: board))
        XCTAssertEqual(
            WorkoutSessionHandResolver.defaultPreference(plan: plan, board: board),
            .both
        )
    }
}

final class WorkoutClockTests: XCTestCase {
    deinit {}

    func testElapsedUsesNonUniformMonotonicSamplesInsteadOfCallbackCount() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.start(initialCountdown: 0)
        now += 0.4
        XCTAssertEqual(clock.elapsed, 0.4, accuracy: 0.000_1)

        now += 1.3
        XCTAssertEqual(clock.elapsed, 1.7, accuracy: 0.000_1)
    }

    func testInitialCountdownShowsThreeTwoOneBeforeElapsedBegins() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.start(initialCountdown: 3)
        XCTAssertEqual(clock.countdownRemaining, 3)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 2)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 1)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 0)
        XCTAssertEqual(clock.elapsed, 0)
    }

    func testSeekedClockShowsANewInitialCountdownBeforeElapsedResumes() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.seek(to: 60)
        clock.start(initialCountdown: 3)

        XCTAssertEqual(clock.countdownRemaining, 3)

        now += 1.1
        XCTAssertEqual(clock.countdownRemaining, 2)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 1)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 0)
        XCTAssertEqual(clock.elapsed, 60.1, accuracy: 0.000_1)
    }

    func testPauseAndResumePreserveElapsedTime() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.start(initialCountdown: 0)
        now += 1.7
        clock.pause()
        now += 20
        XCTAssertEqual(clock.elapsed, 1.7, accuracy: 0.000_1)

        clock.start(initialCountdown: 0)
        now += 0.4
        XCTAssertEqual(clock.elapsed, 2.1, accuracy: 0.000_1)
    }

    func testRunningSeekRebasesTheActiveAnchorWithoutDoubleCounting() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.start(initialCountdown: 0)
        now += 1
        clock.seek(to: 10)
        now += 0.4

        XCTAssertEqual(clock.elapsed, 10.4, accuracy: 0.000_1)
    }
}

final class CountdownAudioSchedulerTests: XCTestCase {
    // A one-second cadence needs each bundled spoken number to leave a gap before the next slot.
    func testBundledCountdownBuffersMustFitWithinOneSecondSlots() {
        XCTAssertTrue(
            BundledCountdownAudioBufferSource.fitsWithinCountdownSlot(
                makeCountdownPCMBuffer(duration: 0.99)
            )
        )
        XCTAssertFalse(
            BundledCountdownAudioBufferSource.fitsWithinCountdownSlot(
                makeCountdownPCMBuffer(duration: 1)
            )
        )
    }

    // Catches a complete bundled pack unnecessarily constructing or using Apple synthesis.
    func testCompleteBundledPackIsSelectedWithoutConstructingAppleRenderer() {
        let expectedBuffers = [
            "3": [makeCountdownPCMBuffer(duration: 0.5)],
            "2": [makeCountdownPCMBuffer(duration: 0.5)],
            "1": [makeCountdownPCMBuffer(duration: 0.5)]
        ]
        let source = RecordingCountdownAudioBufferSource(result: expectedBuffers)
        let bundledBackend = RecordingCountdownAudioSchedulingBackend()
        let appleFactory = RecordingAppleCountdownRendererFactory()
        var bundledFactoryBuffers: [String: [AVAudioPCMBuffer]]?
        let selector = CountdownAudioSchedulingBackendSelector(
            bufferSource: source,
            bundledBackendFactory: { buffers in
                bundledFactoryBuffers = buffers
                return bundledBackend
            },
            appleRendererFactory: appleFactory.makeBackend
        )

        let backend = selector.backend(for: ["1", "2", "3"])
        backend.prewarm { _ in }

        XCTAssertEqual(source.requestedPhraseSets, [["1", "2", "3"]])
        XCTAssertEqual(Set(bundledFactoryBuffers?.keys.map { $0 } ?? []), ["1", "2", "3"])
        XCTAssertTrue(bundledFactoryBuffers?["1"]?.first === expectedBuffers["1"]?.first)
        XCTAssertEqual(bundledBackend.prewarmCallCount, 1)
        XCTAssertEqual(appleFactory.callCount, 0)
    }

    // Catches a failed pack lookup contributing partial buffers to Apple preparation.
    func testMissingBundledPackSelectsOnlyOneAppleRenderer() {
        let source = RecordingCountdownAudioBufferSource(result: nil)
        let appleBackend = RecordingCountdownAudioSchedulingBackend()
        let appleFactory = RecordingAppleCountdownRendererFactory(backend: appleBackend)
        var bundledFactoryCallCount = 0
        let selector = CountdownAudioSchedulingBackendSelector(
            bufferSource: source,
            bundledBackendFactory: { _ in
                bundledFactoryCallCount += 1
                return RecordingCountdownAudioSchedulingBackend()
            },
            appleRendererFactory: appleFactory.makeBackend
        )

        let backend = selector.backend(for: ["1", "2", "3"])
        backend.prewarm { _ in }

        XCTAssertEqual(source.requestedPhraseSets, [["1", "2", "3"]])
        XCTAssertEqual(bundledFactoryCallCount, 0)
        XCTAssertEqual(appleFactory.callCount, 1)
        XCTAssertEqual(appleBackend.prewarmCallCount, 1)
    }

    func testEmptyColdRenderRetriesBeforeCountdownArming() {
        XCTAssertTrue(
            CountdownAudioRenderAttemptPolicy.shouldRetry(
                completedAttempts: 1,
                renderedBufferCount: 0
            )
        )
        XCTAssertFalse(
            CountdownAudioRenderAttemptPolicy.shouldRetry(
                completedAttempts: 2,
                renderedBufferCount: 1
            )
        )
        XCTAssertTrue(
            CountdownAudioRenderAttemptPolicy.shouldIgnoreCallback(
                phraseIsAlreadyPrepared: true
            )
        )
    }

    func testEmptyRenderRetryExhaustionFailsWithoutScheduling() {
        XCTAssertFalse(
            CountdownAudioRenderAttemptPolicy.shouldRetry(
                completedAttempts: CountdownAudioRenderAttemptPolicy.maximumAttempts,
                renderedBufferCount: 0
            )
        )

        let backend = RecordingCountdownAudioSchedulingBackend(scheduleResult: false)
        let lifecycleLogger = RecordingCountdownAudioLifecycleLogger()
        let scheduler = CountdownAudioScheduler(
            backend: backend,
            lifecycleLogger: lifecycleLogger
        )
        scheduler.prewarm { _ in }

        XCTAssertFalse(scheduler.schedule(remainingFrom: "3", startHostTime: 100))
        XCTAssertFalse(lifecycleLogger.events.contains { event in
            if case .scheduleAccepted = event { return true }
            return false
        })
    }

    func testLifecycleLoggerRecordsPrewarmAndAcceptedHostTimeOffsets() {
        let backend = RecordingCountdownAudioSchedulingBackend()
        let lifecycleLogger = RecordingCountdownAudioLifecycleLogger()
        let scheduler = CountdownAudioScheduler(
            backend: backend,
            lifecycleLogger: lifecycleLogger
        )

        scheduler.prewarm { _ in }
        XCTAssertTrue(scheduler.schedule(remainingFrom: "3", startHostTime: 100))

        XCTAssertEqual(
            lifecycleLogger.events,
            [
                .prewarmCompleted(succeeded: true),
                .scheduleAccepted(phrases: ["3", "2", "1"], startHostTime: 100, offsets: [0, 1, 2])
            ]
        )
    }

    func testLifecycleLoggerRecordsRejectedScheduleWithoutFallback() {
        let backend = RecordingCountdownAudioSchedulingBackend(scheduleResult: false)
        let lifecycleLogger = RecordingCountdownAudioLifecycleLogger()
        let scheduler = CountdownAudioScheduler(
            backend: backend,
            lifecycleLogger: lifecycleLogger
        )

        XCTAssertFalse(scheduler.schedule(remainingFrom: "3", startHostTime: 100))
        XCTAssertEqual(
            lifecycleLogger.events,
            [.scheduleRejected(phrases: ["3", "2", "1"], startHostTime: 100)]
        )
    }

    func testPrewarmCompletesOnlyAfterBackendPreparation() {
        let backend = RecordingCountdownAudioSchedulingBackend(
            automaticallyCompletesPrewarm: false
        )
        let scheduler = CountdownAudioScheduler(backend: backend)
        var result: Bool?

        scheduler.prewarm { result = $0 }

        XCTAssertNil(result)
        backend.completePrewarm(succeeded: true)
        XCTAssertEqual(result, true)
    }

    // Catches a regression that schedules only the currently displayed countdown number.
    func testThreeSchedulesEveryCountdownCueAtOneSecondOffsets() {
        let backend = RecordingCountdownAudioSchedulingBackend()
        let scheduler = CountdownAudioScheduler(backend: backend)

        XCTAssertTrue(scheduler.schedule(remainingFrom: "3", startHostTime: 100))
        XCTAssertEqual(backend.schedules.count, 1)
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.phrase), ["3", "2", "1"])
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.offset), [0, 1, 2])
        XCTAssertEqual(backend.schedules[0].startHostTime, 100)
    }

    // Catches a regression that always restarts a full countdown after a later tick.
    func testTwoSchedulesOnlyTheRemainingCountdownCues() {
        let backend = RecordingCountdownAudioSchedulingBackend()
        let scheduler = CountdownAudioScheduler(backend: backend)

        XCTAssertTrue(scheduler.schedule(remainingFrom: "2", startHostTime: 101))
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.phrase), ["2", "1"])
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.offset), [0, 1])
    }

    // Catches a regression that queues a second sequence when SwiftUI publishes a later tick.
    func testDuplicateActiveCountdownDoesNotScheduleAnyAdditionalCue() {
        let backend = RecordingCountdownAudioSchedulingBackend()
        let scheduler = CountdownAudioScheduler(backend: backend)

        XCTAssertTrue(scheduler.schedule(remainingFrom: "3", startHostTime: 100))
        XCTAssertFalse(scheduler.schedule(remainingFrom: "2", startHostTime: 101))
        XCTAssertEqual(backend.schedules.count, 1)
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.phrase), ["3", "2", "1"])
    }
}

final class CountdownAudioBufferSchedulingBackendTests: XCTestCase {
    func testPrewarmPreparesEngineBeforeAnyBufferIsScheduled() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 0.5)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertTrue(backend.prewarm(CountdownAudioSchedule(remainingFrom: "3")))
        XCTAssertEqual(playback.events, [.prepare])

        XCTAssertTrue(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "3"),
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.prepareCallCount, 1)
        XCTAssertEqual(playback.events.first, .prepare)
        XCTAssertEqual(playback.events.filter { $0 == .start }.count, 1)
    }

    // Catches cue offsets being converted from seconds with the wrong host-time scale.
    func testCueOffsetsConvertToExactHostTimesAndAllScheduleBeforePlay() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let startHostTime = AVAudioTime.hostTime(forSeconds: 100)
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 0.5)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertTrue(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "3"),
                startHostTime: startHostTime
            )
        )

        let oneSecond = AVAudioTime.hostTime(forSeconds: 1)
        XCTAssertEqual(
            playback.scheduledHostTimes,
            [startHostTime, startHostTime + oneSecond, startHostTime + (2 * oneSecond)]
        )
        let expectedEvents: [RecordingCountdownAudioBufferPlayback.Event] = [
            .prepare,
            .start,
            .schedule(startHostTime),
            .schedule(startHostTime + oneSecond),
            .schedule(startHostTime + (2 * oneSecond)),
            .play
        ]
        XCTAssertEqual(playback.events, expectedEvents)
    }

    // Catches callback chunks within one cue being scheduled at the same time.
    func testMultipleCueBuffersUseAccumulatedSampleDurationHostOffsets() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let startHostTime = AVAudioTime.hostTime(forSeconds: 100)
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "1": [
                        makeCountdownPCMBuffer(duration: 0.25),
                        makeCountdownPCMBuffer(duration: 0.5)
                    ]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertTrue(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "1"),
                startHostTime: startHostTime
            )
        )

        XCTAssertEqual(
            playback.scheduledHostTimes,
            [startHostTime, startHostTime + AVAudioTime.hostTime(forSeconds: 0.25)]
        )
    }

    // Catches a deadline crossing after buffers are queued but before playback starts.
    func testDeadlineCrossingImmediatelyBeforePlayClearsScheduledBuffers() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let startHostTime = AVAudioTime.hostTime(forSeconds: 100)
        var observedHostTimes = [
            startHostTime - 3,
            startHostTime - 2,
            startHostTime
        ]
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in ["1": [makeCountdownPCMBuffer(duration: 0.5)]] },
            playback: playback,
            currentHostTime: { observedHostTimes.removeFirst() }
        )

        XCTAssertFalse(
            backend.schedule(CountdownAudioSchedule(remainingFrom: "1"), startHostTime: startHostTime)
        )
        XCTAssertEqual(playback.scheduledBufferCountBeforeLastStop, 1)
        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.playCallCount, 0)
        XCTAssertEqual(playback.stopCallCount, 1)
    }

    // Catches a rendered number that fills its slot and can delay or collide with the next cue.
    func testCueThatDoesNotFitStrictlyWithinOneSecondRejectsAllPlayback() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 1.0)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertFalse(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "3"),
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.prepareCallCount, 0)
        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.playCallCount, 0)
    }

    // Catches a fractional short segment placing its second number before the
    // first number's rendered audio has finished.
    func testFractionalShortSegmentRejectsCueThatExceedsItsNextCueSlot() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 0.5)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )
        let schedule = CountdownAudioSchedule(remainingFrom: "3")
            .appendingShortIntervals([1.2], startingAt: 3)

        XCTAssertFalse(
            backend.schedule(
                schedule,
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.prepareCallCount, 0)
        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.playCallCount, 0)
    }

    // Catches the final cue using a one-second fallback deadline instead of
    // the actual end of a fractional short segment.
    func testFinalCueMustFitWithinFractionalShortSegmentEnd() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 0.5)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )
        let schedule = CountdownAudioSchedule(remainingFrom: "3")
            .appendingShortIntervals([0.2], startingAt: 3)

        XCTAssertFalse(
            backend.schedule(
                schedule,
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.prepareCallCount, 0)
        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.playCallCount, 0)
    }

    // Catches stop leaving pre-scheduled buffers owned by the player node.
    func testStopClearsScheduledPlayback() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in ["1": [makeCountdownPCMBuffer(duration: 0.5)]] },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertTrue(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "1"),
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.scheduledBufferCount, 1)

        backend.stop()

        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.stopCallCount, 1)
    }
}

private final class RecordingCountdownAudioBufferPlayback: CountdownAudioBufferPlayback {
    enum Event: Equatable {
        case prepare
        case start
        case schedule(UInt64)
        case play
        case stop
    }

    private(set) var prepareCallCount = 0
    private(set) var scheduledBufferCount = 0
    private(set) var scheduledBufferCountBeforeLastStop = 0
    private(set) var playCallCount = 0
    private(set) var stopCallCount = 0
    private(set) var scheduledHostTimes: [UInt64] = []
    private(set) var events: [Event] = []

    func prepare(format: AVAudioFormat) {
        prepareCallCount += 1
        events.append(.prepare)
    }

    func start() throws {
        events.append(.start)
    }

    func schedule(_ buffer: AVAudioPCMBuffer, atHostTime hostTime: UInt64) {
        scheduledBufferCount += 1
        scheduledHostTimes.append(hostTime)
        events.append(.schedule(hostTime))
    }

    func play() {
        playCallCount += 1
        events.append(.play)
    }

    func stop() {
        stopCallCount += 1
        scheduledBufferCountBeforeLastStop = scheduledBufferCount
        scheduledBufferCount = 0
        scheduledHostTimes.removeAll()
        events.append(.stop)
    }
}

private func makeCountdownPCMBuffer(duration: TimeInterval) -> AVAudioPCMBuffer {
    let sampleRate = 100.0
    let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 1)!
    let frameCount = AVAudioFrameCount(duration * sampleRate)
    let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount)!
    buffer.frameLength = frameCount
    return buffer
}

private final class RecordingCountdownAudioSchedulingBackend: CountdownAudioSchedulingBackend {
    struct ScheduledSequence {
        let schedule: CountdownAudioSchedule
        let startHostTime: UInt64
    }

    private(set) var schedules: [ScheduledSequence] = []
    private(set) var prewarmCallCount = 0
    private let automaticallyCompletesPrewarm: Bool
    private let scheduleResult: Bool
    private var prewarmCompletion: ((Bool) -> Void)?

    init(
        automaticallyCompletesPrewarm: Bool = true,
        scheduleResult: Bool = true
    ) {
        self.automaticallyCompletesPrewarm = automaticallyCompletesPrewarm
        self.scheduleResult = scheduleResult
    }

    func prewarm(completion: @escaping (Bool) -> Void) {
        prewarmCallCount += 1
        if automaticallyCompletesPrewarm {
            completion(true)
        } else {
            prewarmCompletion = completion
        }
    }

    func completePrewarm(succeeded: Bool) {
        let completion = prewarmCompletion
        prewarmCompletion = nil
        completion?(succeeded)
    }

    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool {
        guard scheduleResult else { return false }
        schedules.append(ScheduledSequence(schedule: schedule, startHostTime: startHostTime))
        return true
    }

    func stop() {}
}

private final class RecordingCountdownAudioBufferSource: CountdownAudioBufferSource {
    private let result: [String: [AVAudioPCMBuffer]]?
    private(set) var requestedPhraseSets: [Set<String>] = []

    init(result: [String: [AVAudioPCMBuffer]]?) {
        self.result = result
    }

    func buffers(for phrases: Set<String>) -> [String: [AVAudioPCMBuffer]]? {
        requestedPhraseSets.append(phrases)
        return result
    }
}

private final class RecordingAppleCountdownRendererFactory {
    private let backend: RecordingCountdownAudioSchedulingBackend
    private(set) var callCount = 0

    init(backend: RecordingCountdownAudioSchedulingBackend = RecordingCountdownAudioSchedulingBackend()) {
        self.backend = backend
    }

    func makeBackend() -> any CountdownAudioSchedulingBackend {
        callCount += 1
        return backend
    }
}

private final class RecordingCountdownAudioLifecycleLogger: CountdownAudioLifecycleLogging {
    enum Event: Equatable {
        case prewarmCompleted(succeeded: Bool)
        case scheduleAccepted(phrases: [String], startHostTime: UInt64, offsets: [TimeInterval])
        case scheduleRejected(phrases: [String], startHostTime: UInt64)
    }

    private(set) var events: [Event] = []

    func prewarmCompleted(succeeded: Bool) {
        events.append(.prewarmCompleted(succeeded: succeeded))
    }

    func scheduleAccepted(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) {
        events.append(
            .scheduleAccepted(
                phrases: schedule.cues.map(\.phrase),
                startHostTime: startHostTime,
                offsets: schedule.cues.map(\.offset)
            )
        )
    }

    func scheduleRejected(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) {
        events.append(
            .scheduleRejected(
                phrases: schedule.cues.map(\.phrase),
                startHostTime: startHostTime
            )
        )
    }
}

@MainActor
final class WorkoutSpeechOwnershipTests: XCTestCase {
    func testRepeatedStopPreservesPendingStopOwnershipUntilCallback() {
        var ownership = WorkoutSpeechOwnership()
        let utterance = AVSpeechUtterance(string: "3")

        ownership.begin(utterance)
        ownership.requestStop()
        ownership.requestStop()

        XCTAssertTrue(ownership.ownsPendingStop(utterance))
        ownership.finishPendingStop(utterance)
        XCTAssertFalse(ownership.ownsPendingStop(utterance))
    }

    func testGenerationAndUtteranceIdentityProtectActiveAndPendingStopOwnership() {
        var ownership = WorkoutSpeechOwnership()
        let firstUtterance = AVSpeechUtterance(string: "3")
        let replacementUtterance = AVSpeechUtterance(string: "2")

        ownership.begin(firstUtterance)
        XCTAssertTrue(ownership.ownsActive(firstUtterance))

        ownership.requestStop()
        XCTAssertFalse(ownership.ownsActive(firstUtterance))
        XCTAssertTrue(ownership.ownsPendingStop(firstUtterance))
        ownership.finishPendingStop(firstUtterance)
        XCTAssertFalse(ownership.ownsPendingStop(firstUtterance))

        ownership.begin(replacementUtterance)
        XCTAssertFalse(ownership.ownsPendingStop(firstUtterance))
        XCTAssertTrue(ownership.ownsActive(replacementUtterance))

        ownership.finishActive(firstUtterance)
        XCTAssertTrue(ownership.ownsActive(replacementUtterance))
        ownership.finishActive(replacementUtterance)
        XCTAssertFalse(ownership.ownsActive(replacementUtterance))
    }
}

final class WorkoutAudioSessionConfigurationTests: XCTestCase {
    // Catches a spoken-audio session mode that interrupts background playback instead of ducking it.
    func testCountdownCuesUsePlaybackDefaultModeAndDuckOtherAudio() {
        let configuration = WorkoutAudioSessionConfiguration.countdownCues

        XCTAssertEqual(configuration.category, .playback)
        XCTAssertEqual(configuration.mode, .default)
        XCTAssertTrue(configuration.options.contains(.duckOthers))
        XCTAssertFalse(configuration.options.contains(.interruptSpokenAudioAndMixWithOthers))
    }
}

@MainActor
final class WorkoutAudioCoachTests: XCTestCase {
    // Catches constructing the default scheduler and its audio backend before an athlete starts a countdown.
    func testCountdownSchedulerFactoryWaitsForPreparationRequest() {
        var factoryCallCount = 0
        let scheduler = RecordingCountdownAudioScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownSchedulerFactory: {
                factoryCallCount += 1
                return scheduler
            },
            countdownCompletionScheduler: RecordingWorkoutCountdownCompletionScheduler()
        )

        XCTAssertEqual(factoryCallCount, 0)
        coach.stop()
        XCTAssertEqual(factoryCallCount, 0)
        XCTAssertEqual(coach.countdownPreparationState, .idle)

        coach.prepareCountdownAudio()

        XCTAssertEqual(factoryCallCount, 1)
        XCTAssertEqual(scheduler.prewarmCallCount, 1)
    }

    // Catches app launch prewarming the countdown engine before an athlete requests it.
    func testCountdownAudioPreparationRemainsIdleUntilRequested() async {
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownScheduler: scheduler
        )

        XCTAssertEqual(coach.countdownPreparationState, .idle)
        XCTAssertEqual(scheduler.prewarmCallCount, 0)

        coach.prepareCountdownAudio()

        XCTAssertEqual(coach.countdownPreparationState, .preparing)
        XCTAssertEqual(scheduler.prewarmCallCount, 1)
        scheduler.completePrewarm(succeeded: true)
        await Task.yield()
        XCTAssertEqual(coach.countdownPreparationState, .ready)
    }

    // Catches a cancelled prewarm completion changing the state of a later preparation.
    func testStalePrewarmCompletionCannotChangeLaterPreparation() async {
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownScheduler: scheduler
        )

        coach.prepareCountdownAudio()
        coach.stop()
        coach.prepareCountdownAudio()

        XCTAssertEqual(coach.countdownPreparationState, .preparing)
        XCTAssertEqual(scheduler.prewarmCallCount, 2)

        scheduler.completePrewarm(at: 0, succeeded: false)
        await Task.yield()

        XCTAssertEqual(coach.countdownPreparationState, .preparing)

        scheduler.completePrewarm(at: 0, succeeded: true)
        await Task.yield()

        XCTAssertEqual(coach.countdownPreparationState, .ready)
    }

    // Catches a later countdown request leaving a failed prewarm permanently unavailable.
    func testFailedPrewarmRetriesWhenCountdownIsRequestedAgain() async {
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownScheduler: scheduler
        )

        coach.prepareCountdownAudio()
        scheduler.completePrewarm(succeeded: false)
        await Task.yield()

        XCTAssertEqual(coach.countdownPreparationState, .failed)
        XCTAssertTrue(
            WorkoutSessionPolicy.shouldPrepareCountdownAudio(
                preparationState: coach.countdownPreparationState
            )
        )

        coach.prepareCountdownAudio()

        XCTAssertEqual(coach.countdownPreparationState, .preparing)
        XCTAssertEqual(scheduler.prewarmCallCount, 2)
    }

    // Catches completion restarting the countdown engine after its scheduled playback ends.
    func testCountdownCompletionReturnsPreparationToIdleWithoutPrewarming() async {
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let completionScheduler = RecordingWorkoutCountdownCompletionScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownScheduler: scheduler,
            countdownCompletionScheduler: completionScheduler
        )
        coach.prepareCountdownAudio()
        scheduler.completePrewarm(succeeded: true)
        await Task.yield()

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        completionScheduler.complete()

        XCTAssertEqual(coach.countdownPreparationState, .idle)
        XCTAssertEqual(scheduler.prewarmCallCount, 1)
    }

    // Catches later fixed-interval countdowns being dropped after the prior sequence returns to idle.
    func testIdleCountdownRequestPrewarmsBeforeSchedulingAndActivatingAudioSession() async {
        let audioSession = RecordingWorkoutAudioSession()
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let completionScheduler = RecordingWorkoutCountdownCompletionScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: audioSession,
            countdownScheduler: scheduler,
            countdownCompletionScheduler: completionScheduler
        )

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertEqual(coach.countdownPreparationState, .preparing)
        XCTAssertEqual(scheduler.prewarmCallCount, 1)
        XCTAssertTrue(scheduler.startedSequences.isEmpty)
        XCTAssertEqual(audioSession.configurationCount, 0)
        XCTAssertEqual(audioSession.activationCount, 0)

        scheduler.completePrewarm(succeeded: true)
        await Task.yield()

        XCTAssertEqual(coach.countdownPreparationState, .ready)
        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1"]])
        XCTAssertEqual(scheduler.startedOffsets, [[0, 1, 2]])
        XCTAssertEqual(completionScheduler.scheduledUptime, 103)
        XCTAssertEqual(audioSession.configurationCount, 1)
        XCTAssertEqual(audioSession.activationCount, 1)
    }

    // Catches a synchronous prewarm failure being reported as an accepted deferred countdown.
    func testSynchronousDeferredCountdownPrewarmFailureReturnsFalseAndClearsRequest() {
        let audioSession = RecordingWorkoutAudioSession()
        let scheduler = RecordingCountdownAudioScheduler(prewarmResult: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: audioSession,
            countdownScheduler: scheduler
        )

        XCTAssertFalse(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertEqual(coach.countdownPreparationState, .failed)
        XCTAssertEqual(scheduler.prewarmCallCount, 1)
        XCTAssertTrue(scheduler.startedSequences.isEmpty)
        XCTAssertEqual(audioSession.configurationCount, 0)
        XCTAssertEqual(audioSession.activationCount, 0)

        XCTAssertFalse(coach.startCountdown(remainingFrom: "3", startUptime: 200))
        XCTAssertEqual(scheduler.prewarmCallCount, 2)
    }

    // Catches a synchronous deferred schedule rejection being reported as an accepted countdown.
    func testSynchronousDeferredCountdownScheduleRejectionReturnsFalseAndReleasesAudioSession() {
        let audioSession = RecordingWorkoutAudioSession()
        let scheduler = RecordingCountdownAudioScheduler(scheduleResult: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: audioSession,
            countdownScheduler: scheduler
        )

        XCTAssertFalse(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertEqual(coach.countdownPreparationState, .ready)
        XCTAssertEqual(scheduler.prewarmCallCount, 1)
        XCTAssertTrue(scheduler.startedSequences.isEmpty)
        XCTAssertEqual(audioSession.configurationCount, 1)
        XCTAssertEqual(audioSession.activationCount, 1)
        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    // Catches a cancelled deferred countdown scheduling itself when prewarming finishes later.
    func testStopBeforeDeferredCountdownPrewarmCompletesPreventsSchedulingAndActivation() async {
        let audioSession = RecordingWorkoutAudioSession()
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: audioSession,
            countdownScheduler: scheduler
        )

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertEqual(scheduler.prewarmCallCount, 1)

        coach.stop()
        scheduler.completePrewarm(succeeded: true)
        await Task.yield()

        XCTAssertEqual(coach.countdownPreparationState, .idle)
        XCTAssertTrue(scheduler.startedSequences.isEmpty)
        XCTAssertEqual(audioSession.configurationCount, 0)
        XCTAssertEqual(audioSession.activationCount, 0)
    }

    // Catches a spoken cue allowing a stale deferred countdown to schedule after it takes over audio.
    func testSpeakingBeforeDeferredCountdownPrewarmCompletesPreventsCountdownScheduling() async {
        let audioSession = RecordingWorkoutAudioSession()
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: audioSession,
            countdownScheduler: scheduler
        )

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertEqual(scheduler.prewarmCallCount, 1)

        coach.speak("Pause")
        XCTAssertEqual(audioSession.activationCount, 1)
        scheduler.completePrewarm(succeeded: true)
        await Task.yield()

        XCTAssertTrue(scheduler.startedSequences.isEmpty)
        XCTAssertEqual(audioSession.activationCount, 1)
    }

    // Catches a regression that lets later SwiftUI countdown ticks enqueue another sequence.
    func testCountdownStartsOnePreScheduledSequenceAndIgnoresLaterTicks() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler
        )
        coach.prepareCountdownAudio()

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertFalse(coach.startCountdown(remainingFrom: "2", startUptime: 101))

        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1"]])
    }

    // Catches a regression that sends scheduler-owned numeric cues to live speech synthesis.
    func testScheduledCountdownDoesNotSpeakAnyNumberLive() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler
        )
        coach.prepareCountdownAudio()

        coach.startCountdown(remainingFrom: "3", startUptime: 100)
        coach.startCountdown(remainingFrom: "2", startUptime: 101)
        coach.startCountdown(remainingFrom: "1", startUptime: 102)

        XCTAssertTrue(synthesizer.utterances.isEmpty)
        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1"]])
    }

    // Catches a regression that restores other-app audio before scheduled buffers are cancelled.
    func testStopCancelsCountdownBeforeDeactivatingAudioSession() {
        var events: [String] = []
        let audioSession = RecordingWorkoutAudioSession()
        audioSession.onSuccessfulNotificationAwareDeactivation = {
            events.append("session.deactivate")
        }
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler(onStop: {
            events.append("countdown.stop")
        })
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler
        )
        coach.prepareCountdownAudio()

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        coach.stop()

        XCTAssertEqual(events, ["countdown.stop", "session.deactivate"])
        XCTAssertEqual(coach.countdownPreparationState, .idle)
        XCTAssertEqual(scheduler.prewarmCallCount, 1)
    }

    // Catches cancellation rebuilding a countdown backend while spoken cues take over.
    func testSpeakingCancelsCountdownAndReturnsPreparationToIdleWithoutPrewarming() async {
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownScheduler: scheduler
        )
        coach.prepareCountdownAudio()
        scheduler.completePrewarm(succeeded: true)
        await Task.yield()
        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))

        coach.speak("Pause")

        XCTAssertEqual(coach.countdownPreparationState, .idle)
        XCTAssertEqual(scheduler.prewarmCallCount, 1)
    }

    // Catches countdown ownership surviving after its final one-second slot.
    func testScheduledCountdownCompletionStopsPlaybackBeforeDeactivatingAudioSession() {
        var events: [String] = []
        let audioSession = RecordingWorkoutAudioSession()
        audioSession.onSuccessfulNotificationAwareDeactivation = {
            events.append("session.deactivate")
        }
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler(onStop: {
            events.append("countdown.stop")
        })
        let completionScheduler = RecordingWorkoutCountdownCompletionScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler,
            countdownCompletionScheduler: completionScheduler
        )
        coach.prepareCountdownAudio()

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertEqual(completionScheduler.scheduledUptime, 103)

        completionScheduler.complete()

        XCTAssertEqual(events, ["countdown.stop", "session.deactivate"])

        coach.prepareCountdownAudio()
        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 200))
        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1"], ["3", "2", "1"]])
    }

    // Catches a bounded retry budget leaving other-app audio ducked indefinitely.
    func testCountdownCompletionRetriesDeactivationUntilItNotifiesOtherApps() async {
        let audioSession = RecordingWorkoutAudioSession(failedDeactivationAttempts: 4)
        let deactivated = expectation(description: "notification-aware deactivation")
        audioSession.onSuccessfulNotificationAwareDeactivation = {
            deactivated.fulfill()
        }
        let completionScheduler = RecordingWorkoutCountdownCompletionScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: audioSession,
            countdownScheduler: RecordingCountdownAudioScheduler(),
            countdownCompletionScheduler: completionScheduler,
            sleep: { _ in }
        )
        coach.prepareCountdownAudio()

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        completionScheduler.complete()

        await fulfillment(of: [deactivated], timeout: 5)
        XCTAssertEqual(audioSession.deactivationAttemptCount, 5)
        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }

    // Catches a rejected late schedule falling back to queued live speech.
    func testRejectedCountdownScheduleStaysSilentAndReleasesAudioSession() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler(scheduleResult: false)
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler
        )
        coach.prepareCountdownAudio()

        XCTAssertFalse(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertTrue(synthesizer.utterances.isEmpty)
        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    func testSpeakDoesNotCallStopBeforeEachCue() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        coach.speak("2")

        XCTAssertEqual(
            synthesizer.stopCallCount,
            0,
            "WorkoutAudioCoach should not stop the synthesizer before each successive cue."
        )
        XCTAssertEqual(synthesizer.utterances.count, 2)
        XCTAssertEqual(synthesizer.utterances.map(\.speechString), ["3", "2"])
    }

    func testStopStillStopsSynthesizerImmediately() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.stop()

        XCTAssertEqual(
            synthesizer.stopCallCount,
            1,
            "WorkoutAudioCoach.stop() must still stop speech immediately."
        )
    }

    func testStopWaitsForSpeechCancellationBeforeDeactivatingAudioSession() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        coach.stop()

        XCTAssertEqual(audioSession.activationCount, 1)
        XCTAssertEqual(audioSession.deactivationCount, 0)

        synthesizer.isSpeaking = false
        synthesizer.sendCancellation()
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }

    func testReplacementCueKeepsAudioSessionActiveUntilReplacementFinishes() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )
        coach.speak("3")
        coach.speak("2")

        synthesizer.sendCancellation(of: synthesizer.utterances[0])
        await Task.yield()

        XCTAssertEqual(audioSession.activationCount, 1)
        XCTAssertEqual(audioSession.deactivationCount, 0)

        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: synthesizer.utterances[1])
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)

        coach.stop()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }

    func testStaleCallbackFromReplacedCueDoesNotAffectReplacement() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        let replacedUtterance = synthesizer.utterances[0]
        coach.speak("2")
        let replacementUtterance = synthesizer.utterances[1]
        synthesizer.sendStart(of: replacementUtterance)

        synthesizer.sendCancellation(of: replacedUtterance)
        await Task.yield()

        XCTAssertTrue(coach.isSpeaking)
        XCTAssertEqual(audioSession.deactivationCount, 0)

        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: replacementUtterance)
        await Task.yield()

        XCTAssertFalse(coach.isSpeaking)
        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    func testCueCompletionImmediatelyDeactivatesAudioSessionAndNotifiesOtherApps() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )
        coach.speak("3")
        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: synthesizer.utterances[0])
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }

    func testStopOwnsCancellationAndIgnoresLaterCallbacks() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        let stoppedUtterance = synthesizer.utterances[0]
        coach.stop()

        XCTAssertEqual(audioSession.deactivationCount, 0)

        synthesizer.isSpeaking = false
        synthesizer.sendCancellation(of: stoppedUtterance)
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertFalse(coach.isSpeaking)

        synthesizer.sendFinish(of: stoppedUtterance)
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    func testNewCueAfterStopStartsFreshAudioSessionGeneration() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        let stoppedUtterance = synthesizer.utterances[0]
        coach.stop()

        coach.speak("2")
        let newUtterance = synthesizer.utterances[1]
        synthesizer.sendStart(of: newUtterance)
        synthesizer.sendCancellation(of: stoppedUtterance)
        await Task.yield()

        XCTAssertEqual(audioSession.activationCount, 1)
        XCTAssertEqual(audioSession.deactivationCount, 0)
        XCTAssertTrue(coach.isSpeaking)

        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: newUtterance)
        await Task.yield()
        coach.stop()

        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    func testDeactivationRetriesAfterTransientFailureOnceSpeechHasFinished() async {
        let audioSession = RecordingWorkoutAudioSession(failedDeactivationAttempts: 1)
        let deactivated = expectation(description: "notification-aware deactivation")
        audioSession.onSuccessfulNotificationAwareDeactivation = {
            deactivated.fulfill()
        }
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            sleep: { _ in }
        )

        coach.speak("3")

        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: synthesizer.utterances[0])
        coach.stop()
        await fulfillment(of: [deactivated], timeout: 5)

        XCTAssertEqual(audioSession.deactivationAttemptCount, 2)
        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }
}

private final class RecordingCountdownAudioScheduler: CountdownAudioScheduling {
    private let backend = RecordingCountdownAudioSchedulingBackend()
    private lazy var scheduler = CountdownAudioScheduler(backend: backend)
    private(set) var stopCallCount = 0
    private let onStop: () -> Void
    private let scheduleResult: Bool
    private let automaticallyCompletesPrewarm: Bool
    private let prewarmResult: Bool
    private var prewarmCompletions: [(Bool) -> Void] = []
    private(set) var prewarmCallCount = 0

    var startedSequences: [[String]] {
        backend.schedules.map { sequence in
            sequence.schedule.cues.map(\.phrase)
        }
    }

    var startedOffsets: [[TimeInterval]] {
        backend.schedules.map { sequence in
            sequence.schedule.cues.map(\.offset)
        }
    }

    init(
        onStop: @escaping () -> Void = {},
        scheduleResult: Bool = true,
        automaticallyCompletesPrewarm: Bool = true,
        prewarmResult: Bool = true
    ) {
        self.onStop = onStop
        self.scheduleResult = scheduleResult
        self.automaticallyCompletesPrewarm = automaticallyCompletesPrewarm
        self.prewarmResult = prewarmResult
    }

    func prewarm(completion: @escaping (Bool) -> Void) {
        prewarmCallCount += 1
        if automaticallyCompletesPrewarm {
            completion(prewarmResult)
        } else {
            prewarmCompletions.append(completion)
        }
    }

    func completePrewarm(succeeded: Bool) {
        completePrewarm(at: 0, succeeded: succeeded)
    }

    func completePrewarm(at index: Int, succeeded: Bool) {
        guard prewarmCompletions.indices.contains(index) else { return }
        let completion = prewarmCompletions.remove(at: index)
        completion(succeeded)
    }

    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool {
        guard scheduleResult else { return false }
        return scheduler.schedule(schedule, startHostTime: startHostTime)
    }

    func stop() {
        stopCallCount += 1
        scheduler.stop()
        onStop()
    }
}

@MainActor
private final class RecordingWorkoutCountdownCompletionScheduler:
    WorkoutCountdownCompletionScheduling
{
    private(set) var scheduledUptime: TimeInterval?
    private var completion: (() -> Void)?

    func schedule(atUptime uptime: TimeInterval, completion: @escaping () -> Void) {
        scheduledUptime = uptime
        self.completion = completion
    }

    func cancel() {
        scheduledUptime = nil
        completion = nil
    }

    func complete() {
        let completion = completion
        cancel()
        completion?()
    }
}

@MainActor
private final class RecordingWorkoutSpeechSynthesizer: WorkoutSpeechSynthesizing {
    var delegate: AVSpeechSynthesizerDelegate?
    var isSpeaking = false
    private(set) var utterances: [AVSpeechUtterance] = []
    private(set) var stopCallCount = 0

    func stopSpeaking(at boundary: AVSpeechBoundary) -> Bool {
        // Cancellation remains in progress until a test delivers its delegate callback.
        stopCallCount += 1
        return true
    }

    func speak(_ utterance: AVSpeechUtterance) {
        utterances.append(utterance)
        isSpeaking = true
    }

    func sendStart(of utterance: AVSpeechUtterance) {
        delegate?.speechSynthesizer?(
            AVSpeechSynthesizer(),
            didStart: utterance
        )
    }

    func sendCancellation(of utterance: AVSpeechUtterance? = nil) {
        delegate?.speechSynthesizer?(
            AVSpeechSynthesizer(),
            didCancel: utterance ?? utterances[0]
        )
    }

    func sendFinish(of utterance: AVSpeechUtterance) {
        delegate?.speechSynthesizer?(AVSpeechSynthesizer(), didFinish: utterance)
    }
}

@MainActor
private final class RecordingWorkoutAudioSession: WorkoutAudioSessionManaging {
    private(set) var configurationCount = 0
    private(set) var activationCount = 0
    private(set) var deactivationAttemptCount = 0
    private(set) var deactivationCount = 0
    private(set) var didDeactivateWithNotification = false
    var onSuccessfulNotificationAwareDeactivation: (() -> Void)?
    private var failedDeactivationAttempts: Int

    init(failedDeactivationAttempts: Int = 0) {
        self.failedDeactivationAttempts = failedDeactivationAttempts
    }

    func configureForSpokenCues() throws {
        configurationCount += 1
    }

    func activate() throws {
        activationCount += 1
    }

    func deactivateAndNotifyOthers() throws {
        deactivationAttemptCount += 1
        guard failedDeactivationAttempts == 0 else {
            failedDeactivationAttempts -= 1
            throw RecordingWorkoutAudioSessionError.deactivationFailed
        }

        deactivationCount += 1
        didDeactivateWithNotification = true
        onSuccessfulNotificationAwareDeactivation?()
    }
}

private enum RecordingWorkoutAudioSessionError: Error {
    case deactivationFailed
}

final class WorkoutSessionPolicyTests: XCTestCase {
    func testScaleTrackingRequiresSelectedScaleAndCompletedInitialPreparation() {
        XCTAssertFalse(
            WorkoutSessionPolicy.isScaleTrackingReady(
                source: .sensor,
                didCompleteInitialPreparation: false
            )
        )
        XCTAssertTrue(
            WorkoutSessionPolicy.isScaleTrackingReady(
                source: .sensor,
                didCompleteInitialPreparation: true
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.isScaleTrackingReady(
                source: .manual,
                didCompleteInitialPreparation: true
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.isScaleTrackingReady(
                source: .untracked,
                didCompleteInitialPreparation: true
            )
        )
    }

    func testNonSensorSessionsPersistNeutralForceSensorProfile() {
        for source in [WorkoutInitialWeightSource.manual, .untracked] {
            XCTAssertEqual(
                WorkoutSessionPolicy.recordedForceSensorProfile(
                    source: source,
                    connectedProfile: .motherboard,
                    configuredProfile: .genericWHC06
                ),
                .automatic
            )
        }
        XCTAssertEqual(
            WorkoutSessionPolicy.recordedForceSensorProfile(
                source: .sensor,
                connectedProfile: .progressor,
                configuredProfile: .genericWHC06
            ),
            .progressor
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.recordedForceSensorProfile(
                source: .sensor,
                connectedProfile: nil,
                configuredProfile: .genericWHC06
            ),
            .genericWHC06
        )
    }

    func testDebugCountdownCaptureLeadDoesNotChangeVisibleCountdownDuration() {
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownAudioArmLead(
                environment: ["HANGTEN_REVIEW_COUNTDOWN_CAPTURE": "1"]
            ),
            5
        )
        XCTAssertEqual(WorkoutSessionPolicy.countdownDuration(for: .initial), 3)
        XCTAssertEqual(WorkoutSessionPolicy.countdownDuration(for: .skip), 3)
    }

    // Catches a first start crossing its exact boundary before prewarm resolves.
    func testFirstCountdownWaitsForPrewarmButFailurePreservesVisualCountdown() {
        XCTAssertTrue(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: true,
                preparationState: .preparing
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: true,
                preparationState: .idle
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: true,
                preparationState: .ready
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: true,
                preparationState: .failed
            )
        )
        XCTAssertTrue(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: false,
                preparationState: .preparing
            )
        )
    }

    // Catches failed prewarm consuming the same pending countdown more than once or retrying it.
    func testFailedPreparationConsumesPendingCountdownAndStartsItVisiblyOnce() {
        var pendingCountdown: Int? = 42

        XCTAssertEqual(
            WorkoutSessionPolicy.consumePendingCountdown(
                &pendingCountdown,
                afterPreparationState: .failed
            ),
            .beginVisibly
        )
        XCTAssertNil(pendingCountdown)
        XCTAssertEqual(
            WorkoutSessionPolicy.consumePendingCountdown(
                &pendingCountdown,
                afterPreparationState: .failed
            ),
            .none
        )

        var readyPendingCountdown: Int? = 42
        XCTAssertEqual(
            WorkoutSessionPolicy.consumePendingCountdown(
                &readyPendingCountdown,
                afterPreparationState: .ready
            ),
            .requestAudioCountdown
        )
        XCTAssertNil(readyPendingCountdown)
    }

    func testCountdownDurationsKeepInitialAndSkipStartAtThree() {
        let now = Date(timeIntervalSinceReferenceDate: 2_000)

        XCTAssertEqual(
            WorkoutSessionPolicy.startDate(for: .initial, now: now),
            now.addingTimeInterval(3)
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.startDate(for: .skip, now: now),
            now.addingTimeInterval(3)
        )
    }

    func testMonotonicCountdownRemainingUsesCeilingAndReachesZeroAtStart() {
        let now: TimeInterval = 100
        let start = now + 5

        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startUptime: start, nowUptime: now),
            5
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startUptime: start, nowUptime: now + 1.1),
            4
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startUptime: start, nowUptime: start),
            0
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startUptime: nil, nowUptime: now),
            0
        )
    }

    func testImmediateStartIsAllowedOnlyForAnUnstartedFirstAppearance() {
        XCTAssertTrue(
            WorkoutSessionPolicy.shouldAutoStart(
                didAutoStart: false,
                isRunning: false,
                routineStartedAt: nil
            )
        )
    }

    func testImmediateStartIsDisabledAfterTheOneShotHasRun() {
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldAutoStart(
                didAutoStart: true,
                isRunning: false,
                routineStartedAt: nil
            )
        )
    }

    func testImmediateStartDoesNotRestartAStartedOrPausedSession() {
        let routineStart = Date(timeIntervalSinceReferenceDate: 1_000)

        XCTAssertFalse(
            WorkoutSessionPolicy.shouldAutoStart(
                didAutoStart: false,
                isRunning: true,
                routineStartedAt: routineStart
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldAutoStart(
                didAutoStart: false,
                isRunning: false,
                routineStartedAt: routineStart
            )
        )
    }

    func testPausedSessionAtStepOneIsNotAFirstStartAndResumesImmediately() {
        let originalRoutineStart = Date(timeIntervalSinceReferenceDate: 1_000)
        let resumedAt = Date(timeIntervalSinceReferenceDate: 1_120)

        XCTAssertTrue(WorkoutSessionPolicy.isFirstStart(routineStartedAt: nil))
        XCTAssertFalse(WorkoutSessionPolicy.isFirstStart(routineStartedAt: originalRoutineStart))
        XCTAssertEqual(
            WorkoutSessionPolicy.runStartDate(routineStartedAt: originalRoutineStart, now: resumedAt),
            resumedAt
        )
    }

    func testCompletionIntervalMapsExplicitActiveElapsedTimeOntoAbsoluteStartDate() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            planDuration: 600,
            elapsed: 24.5
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, Date(timeIntervalSinceReferenceDate: 1_024.5))
    }

    func testCompletionIntervalExcludesPausedGapFromClockElapsedTime() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)

        clock.start(initialCountdown: 0)
        now += 12.5
        clock.pause()
        now += 3_600
        clock.start(initialCountdown: 0)
        now += 7.5

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            planDuration: 600,
            elapsed: clock.elapsed
        )

        XCTAssertEqual(interval.duration, 20, accuracy: 0.000_1)
    }

    func testCompletionIntervalCapsExplicitActiveElapsedTimeAtPlanDuration() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            planDuration: 60,
            elapsed: 80
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, Date(timeIntervalSinceReferenceDate: 1_060))
    }

    func testCompletionIntervalUsesActualCompletionDateAfterPausedGap() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)
        let recordedAt = Date(timeIntervalSinceReferenceDate: 4_600)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            recordedAt: recordedAt
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, recordedAt)
        XCTAssertEqual(interval.duration, 3_600)
    }

    func testCompletionIntervalClampsPreStartCompletionToStartDate() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)
        let recordedAt = Date(timeIntervalSinceReferenceDate: 900)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            recordedAt: recordedAt
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, sessionStart)
        XCTAssertEqual(interval.duration, 0)
    }

    func testWorkoutMeasurementEligibilityRejectsPreStartAndAcceptsBoundaryAndAfterStart() {
        let startedAt = Date(timeIntervalSince1970: 100)

        XCTAssertFalse(
            WorkoutSessionPolicy.isMeasurementEligible(
                routineStartedAt: startedAt,
                measurementTimestamp: Date(timeIntervalSince1970: 99.999)
            )
        )
        XCTAssertTrue(
            WorkoutSessionPolicy.isMeasurementEligible(
                routineStartedAt: startedAt,
                measurementTimestamp: startedAt
            )
        )
        XCTAssertTrue(
            WorkoutSessionPolicy.isMeasurementEligible(
                routineStartedAt: startedAt,
                measurementTimestamp: Date(timeIntervalSince1970: 100.001)
            )
        )
    }
}

final class WorkoutStepDurationTests: XCTestCase {
    deinit {}

    func testRestPhaseHasFullDurationAsRest() {
        let rest = WorkoutStep(
            id: "rest",
            number: 1,
            title: "Rest",
            instruction: "Rest.",
            accessory: "",
            duration: 30,
            phase: .rest)

        XCTAssertEqual(rest.activeDuration, 30)
        XCTAssertFalse(rest.hasRestInterval)
        XCTAssertEqual(rest.restDuration, 0)
    }

    func testTimedPullTaskHasNoFollowingRest() {
        let pull = WorkoutStep(
            id: "pull",
            number: 1,
            title: "Pull",
            instruction: "Do 2 pull-ups.",
            accessory: "",
            duration: 10,
            phase: .pull,
            timedWorkDuration: 10
        )

        XCTAssertEqual(pull.activeDuration, 10)
        XCTAssertFalse(pull.hasRestInterval)
    }
}

final class MetoliusTaskExpansionTests: XCTestCase {
    deinit {}

    func testPullUpTasksUseFiveSecondsPerPullUp() throws {
        let task = MetoliusCycleBuilder.pullUps(
            count: 3,
            title: "Three pull-ups",
            instruction: "Do 3 pull-ups on the jugs.",
            phase: .pull,
            targets: [.kind(.jug)]
        )

        let steps = try MetoliusCycleBuilder.expand(planID: "test", minute: 1, tasks: [task])

        XCTAssertEqual(steps[0].duration, 15)
        XCTAssertEqual(steps[1].phase, .rest)
        XCTAssertEqual(steps[1].duration, 45)
    }

    func testExpansionKeepsTaskOrderAndAddsRemainingMinuteRest() throws {
        let first = MetoliusCycleBuilder.fixed(
            title: "First hang",
            instruction: "Hang for 15 seconds.",
            duration: 15,
            phase: .hang,
            targets: [.edge(depth: .category(.large))]
        )
        let second = MetoliusCycleBuilder.pullUps(
            count: 2,
            title: "Pull-ups",
            instruction: "Do 2 pull-ups.",
            phase: .pull,
            targets: [.kind(.jug)]
        )

        let steps = try MetoliusCycleBuilder.expand(planID: "test", minute: 2, tasks: [first, second])

        XCTAssertEqual(steps.map(\.id), ["test.minute-2.task-1", "test.minute-2.task-2", "test.minute-2.rest"])
        XCTAssertEqual(steps.map(\.duration), [15, 10, 35])
        XCTAssertEqual(steps[0].workRequirements, first.targets)
        XCTAssertEqual(steps[1].workRequirements, second.targets)
    }

    func testExpansionRejectsTasksThatExceedTheMinute() {
        let overfull = MetoliusTaskDefinition(
            title: "Overfull",
            instruction: "Overfull",
            accessory: "",
            duration: 61,
            phase: .hang,
            targets: [.edge(depth: .category(.large))],
            gripType: nil
        )

        XCTAssertThrowsError(try MetoliusCycleBuilder.expand(planID: "test", minute: 3, tasks: [overfull]))
    }
}

final class MetoliusCatalogExpansionTests: XCTestCase {
    deinit {}

    private let sourceURL = URL(
        string: "https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide"
    )!

    func testIntermediateMinuteTwoIsTwoTaskStepsThenRest() {
        let steps = PlanCatalog.metoliusIntermediate.steps.filter {
            $0.id.hasPrefix("intermediate.minute-2.")
        }

        XCTAssertEqual(
            steps.map(\.title),
            ["Round sloper pull-ups", "Medium-edge hang", "Minute 2 rest"]
        )
        XCTAssertEqual(steps.map(\.duration), [10, 20, 30])
        XCTAssertEqual(
            steps[0].workRequirements,
            [ContactRequirement(kind: .sloper, shape: .round)]
        )
        XCTAssertEqual(
            steps[1].workRequirements,
            [ContactRequirement.edge(depth: .category(.medium))]
        )
        XCTAssertEqual(steps[2].phase, .rest)
    }

    func testIntermediateOffsetPullsTellTheHandSwitchAsSeparateSteps() {
        let steps = PlanCatalog.metoliusIntermediate.steps.filter {
            $0.id.hasPrefix("intermediate.minute-6.")
        }

        XCTAssertEqual(steps.map(\.duration), [15, 15, 30])
        let offsetTargets = [
            ContactRequirement.kind(.jug),
            ContactRequirement.edge(depth: .category(.small))
        ]
        XCTAssertEqual(steps[0].workRequirements, offsetTargets)
        XCTAssertEqual(steps[1].workRequirements, offsetTargets)
        XCTAssertTrue(steps[1].instruction.lowercased().contains("change hands"))
        XCTAssertTrue(steps[1].instruction.lowercased().contains("repeat"))
        XCTAssertEqual(steps[2].phase, .rest)
    }

    func testMaxEffortMetoliusStepsUseStopwatchTiming() throws {
        let step = try XCTUnwrap(
            PlanCatalog.metoliusEntry.steps.first { $0.title == "Maximum sloper hang" }
        )

        XCTAssertEqual(step.duration, 60)
        XCTAssertEqual(step.timedWorkDuration, nil)
        XCTAssertEqual(step.segments.count, 1)
        let work = step.segments[0]
        XCTAssertEqual(work.kind, .work)
        XCTAssertEqual(work.timing, .stopwatch)
        XCTAssertNil(work.duration)
        guard case let .requirements(requirements)? = work.target else {
            return XCTFail("Expected stopwatch work to keep round-sloper requirements")
        }
        XCTAssertEqual(requirements, [ContactRequirement(kind: .sloper, shape: .round)])
    }

    func testAdvancedMinuteFourLeavesTwentySecondsToRest() {
        let steps = PlanCatalog.metoliusAdvanced.steps.filter { $0.id.hasPrefix("advanced.minute-4.") }

        XCTAssertEqual(steps.map(\.duration), [40, 20])
        XCTAssertEqual(steps.last?.phase, .rest)
    }

    func testMetoliusPlansRemainTenMinutesAndAreMarkedAdapted() {
        let plans = [
            PlanCatalog.metoliusEntry,
            PlanCatalog.metoliusIntermediate,
            PlanCatalog.metoliusAdvanced
        ]

        XCTAssertEqual(plans.map(\.steps.count), [20, 26, 27])
        for plan in plans {
            XCTAssertEqual(plan.duration, 600)
            XCTAssertEqual(plan.provenance, .adapted)
            XCTAssertEqual(plan.sourceURL, sourceURL)
            XCTAssertEqual(plan.subtitle, "Ten 60-second hangboard sequences.")
            XCTAssertEqual(plan.steps.map(\.number), Array(1...plan.steps.count))
            XCTAssertEqual(Set(plan.steps.map(\.id)).count, plan.steps.count)
        }
    }

    func testExpandedCatalogPreservesCompoundTasksChoicesAndMaximumEfforts() {
        let entry = PlanCatalog.metoliusEntry.steps
        let advanced = PlanCatalog.metoliusAdvanced.steps

        let pocketShrugs = entry.filter { $0.id.hasPrefix("entry.minute-4.") }
        XCTAssertEqual(pocketShrugs.map(\.duration), [15, 45])
        XCTAssertTrue(pocketShrugs[0].instruction.contains("3 shrugs"))

        let entryMinuteSix = entry.filter { $0.id.hasPrefix("entry.minute-6.") }
        XCTAssertEqual(entryMinuteSix.map(\.duration), [10, 5, 45])
        XCTAssertEqual(
            entryMinuteSix[0].workRequirements,
            [ContactRequirement(kind: .sloper, shape: .round)]
        )
        XCTAssertEqual(
            entryMinuteSix[1].workRequirements,
            [ContactRequirement.kind(.pocket)]
        )

        let advancedMinuteEight = advanced.filter { $0.id.hasPrefix("advanced.minute-8.") }
        XCTAssertEqual(advancedMinuteEight.map(\.duration), [15, 15, 30])
        XCTAssertEqual(advancedMinuteEight.count, 3)
        XCTAssertTrue(advancedMinuteEight[1].title.lowercased().contains("choose one"))
        XCTAssertTrue(advancedMinuteEight[1].instruction.lowercased().contains("choose one"))
        XCTAssertTrue(advancedMinuteEight[1].instruction.contains("5-second front lever"))
        XCTAssertTrue(advancedMinuteEight[1].instruction.contains("15-second straight-arm hang"))
        XCTAssertTrue(advancedMinuteEight[1].accessory.lowercased().contains("choose one"))
        XCTAssertTrue(advancedMinuteEight[1].accessory.contains("5 seconds"))
        XCTAssertTrue(advancedMinuteEight[1].accessory.contains("15 seconds"))

        let advancedMinuteTen = advanced.filter { $0.id.hasPrefix("advanced.minute-10.") }
        XCTAssertEqual(advancedMinuteTen.map(\.duration), [60])
        XCTAssertTrue(advancedMinuteTen[0].instruction.lowercased().contains("to failure"))
        XCTAssertTrue(advancedMinuteTen[0].instruction.lowercased().contains("no rest"))
    }
}

final class WorkoutAudioCuePolicyTests: XCTestCase {
    private let stepID = "f80-set-2-rep-3"

    @MainActor
    func testRoutePrearmsThreeSecondSegmentWithoutInterruptingOrDuplicatingPrecedingCountdown() {
        let scheduler = RecordingCountdownAudioScheduler()
        let completionScheduler = RecordingWorkoutCountdownCompletionScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownScheduler: scheduler,
            countdownCompletionScheduler: completionScheduler
        )
        coach.prepareCountdownAudio()
        let startUptime = ProcessInfo.processInfo.systemUptime + 10
        let routeSteps = [
            WorkoutStep(
                id: "preceding",
                number: 1,
                title: "Preceding",
                instruction: "",
                accessory: "",
                duration: 10,
                phase: .hang),
            WorkoutStep(
                id: "short",
                number: 2,
                title: "Short",
                instruction: "",
                accessory: "",
                duration: 3,
                phase: .hang),
            WorkoutStep(
                id: "following",
                number: 3,
                title: "Following",
                instruction: "",
                accessory: "",
                duration: 10,
                phase: .rest)
        ]
        let followingShortDurations = WorkoutCountdownIntervalPolicy.shortDurations(
            in: routeSteps,
            startingAt: 10
        )
        XCTAssertEqual(followingShortDurations, [3])
        let precedingMoment = WorkoutAudioCuePolicy.scheduledMoment(
            stepID: "preceding",
            segmentName: "active",
            initialCountdown: 0,
            intervalSecondsRemaining: 4,
            intervalDuration: 10,
            followingShortSegmentDurations: followingShortDurations,
            isComplete: false
        )
        let action = WorkoutAudioCuePolicy.action(
            previous: nil,
            current: precedingMoment,
            countdownStartUptime: startUptime
        )

        XCTAssertTrue(WorkoutAudioCueRouter.route(action, to: coach))
        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1", "3", "2", "1"]])
        XCTAssertEqual(scheduler.startedOffsets, [[0, 1, 2, 3, 4, 5]])
        XCTAssertEqual(scheduler.stopCallCount, 0)
        XCTAssertEqual(completionScheduler.scheduledUptime, startUptime + 6)

        let shortSegmentMoment = WorkoutAudioCuePolicy.scheduledMoment(
            stepID: "short",
            segmentName: "active",
            initialCountdown: 0,
            intervalSecondsRemaining: 3,
            intervalDuration: 3,
            followingShortSegmentDurations: [],
            isComplete: false
        )
        XCTAssertNil(shortSegmentMoment)
        XCTAssertFalse(
            WorkoutAudioCueRouter.route(
                WorkoutAudioCuePolicy.action(
                    previous: precedingMoment,
                    current: shortSegmentMoment,
                    countdownStartUptime: startUptime + 3
                ),
                to: coach
            )
        )
        XCTAssertEqual(scheduler.startedSequences.count, 1)
        XCTAssertEqual(scheduler.stopCallCount, 0)
    }

    func testMissingAudioMomentLeavesInFlightCueUntouched() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: nil,
                countdownStartUptime: nil
            ),
            .none
        )
    }

    func testNonnumericAudioMomentKeepsLiveSpeechRouting() {
        let moment = WorkoutAudioMoment(key: "step-start", phrase: "Begin minute one")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: moment,
                countdownStartUptime: nil
            ),
            .speak(moment)
        )
    }

    // Catches an initial countdown being routed as three independent live-speech calls.
    func testInitialThreeStartsOneSchedulerOwnedSequence() {
        let three = WorkoutAudioMoment(key: "initial-3", phrase: "3")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: three,
                countdownStartUptime: 100
            ),
            .startCountdown(
                schedule: CountdownAudioSchedule(remainingFrom: "3"),
                startUptime: 100
            )
        )
        assertLaterCountdownTicksHaveNoIndependentAction(
            three: three,
            two: WorkoutAudioMoment(key: "initial-2", phrase: "2"),
            one: WorkoutAudioMoment(key: "initial-1", phrase: "1")
        )
    }

    // Catches a skip countdown bypassing the scheduler-owned sequence route.
    func testSkipThreeStartsOneSchedulerOwnedSequence() {
        let three = WorkoutAudioMoment(key: "skip-3", phrase: "3")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: three,
                countdownStartUptime: 200
            ),
            .startCountdown(
                schedule: CountdownAudioSchedule(remainingFrom: "3"),
                startUptime: 200
            )
        )
        assertLaterCountdownTicksHaveNoIndependentAction(
            three: three,
            two: WorkoutAudioMoment(key: "skip-2", phrase: "2"),
            one: WorkoutAudioMoment(key: "skip-1", phrase: "1")
        )
    }

    // Catches a fixed segment's final three seconds being sent to live speech.
    func testFinalSegmentThreeStartsOneSchedulerOwnedSequence() {
        let three = WorkoutAudioMoment(key: "\(stepID)-active-3", phrase: "3")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: three,
                countdownStartUptime: 300
            ),
            .startCountdown(
                schedule: CountdownAudioSchedule(remainingFrom: "3"),
                startUptime: 300
            )
        )
        assertLaterCountdownTicksHaveNoIndependentAction(
            three: three,
            two: WorkoutAudioMoment(key: "\(stepID)-active-2", phrase: "2"),
            one: WorkoutAudioMoment(key: "\(stepID)-active-1", phrase: "1")
        )
    }

    // Catches delayed first delivery dropping the complete remaining numeric sequence.
    func testLaterNumberStartsRemainingSequenceWhenNoEarlierMomentWasDelivered() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: WorkoutAudioMoment(key: "initial-2", phrase: "2"),
                countdownStartUptime: 101
            ),
            .startCountdown(
                schedule: CountdownAudioSchedule(remainingFrom: "2"),
                startUptime: 101
            )
        )
    }

    func testSkipCountdownCueUsesOnlyTheCountdownNumber() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 3,
                intervalSecondsRemaining: 60,
                isComplete: false,
                countdownKind: .skip
            ),
            WorkoutAudioMoment(key: "skip-3", phrase: "3")
        )
    }

    func testInitialCountdownReturnsOnlyNumericValues() {
        for countdown in [3, 2, 1] {
            let moment = WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: countdown,
                intervalSecondsRemaining: 60,
                isComplete: false
            )

            XCTAssertEqual(
                moment,
                WorkoutAudioMoment(
                    key: "initial-\(countdown)",
                    phrase: "\(countdown)"
                )
            )
        }
    }

    func testIntervalCountdownReturnsNumericValuesWithStableSegmentKeys() {
        for secondsRemaining in [3, 2, 1] {
            let moment = WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 0,
                intervalSecondsRemaining: secondsRemaining,
                isComplete: false
            )

            XCTAssertEqual(
                moment,
                WorkoutAudioMoment(
                    key: "\(stepID)-active-\(secondsRemaining)",
                    phrase: "\(secondsRemaining)"
                )
            )
        }
    }

    func testFixedSegmentArmsThreeAtThePrecedingFourSecondTick() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.scheduledMoment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 0,
                intervalSecondsRemaining: 4,
                isComplete: false
            ),
            WorkoutAudioMoment(
                key: "\(stepID)-active-3",
                phrase: "3",
                countdownSchedule: CountdownAudioSchedule(remainingFrom: "3")
            )
        )
    }

    func testSegmentStartAndNormalIntervalReturnNoCue() {
        XCTAssertNil(
            WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "rest",
                initialCountdown: 0,
                intervalSecondsRemaining: 60,
                isComplete: false
            )
        )
    }

    func testCompletionReturnsNoCueEvenDuringTheFinalThreeSeconds() {
        XCTAssertNil(
            WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 0,
                intervalSecondsRemaining: 3,
                isComplete: true
            )
        )
    }

    func testCompletionDuringInitialCountdownLeavesInFlightCueUntouched() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: WorkoutAudioCuePolicy.moment(
                    stepID: stepID,
                    segmentName: "active",
                    initialCountdown: 3,
                    intervalSecondsRemaining: 60,
                    isComplete: true
                ),
                countdownStartUptime: 100
            ),
            .none
        )
    }

    func testCompletionDuringSkipCountdownLeavesInFlightCueUntouched() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: WorkoutAudioCuePolicy.moment(
                    stepID: stepID,
                    segmentName: "active",
                    initialCountdown: 2,
                    intervalSecondsRemaining: 60,
                    isComplete: true,
                    countdownKind: .skip
                ),
                countdownStartUptime: 100
            ),
            .none
        )
    }

    func testShortIntervalReturnsOnlyTheApplicableNumber() {
        let moment = WorkoutAudioCuePolicy.moment(
            stepID: stepID,
            segmentName: "rest",
            initialCountdown: 0,
            intervalSecondsRemaining: 2,
            isComplete: false
        )

        XCTAssertEqual(
            moment,
            WorkoutAudioMoment(
                key: "\(stepID)-rest-2",
                phrase: "2"
            )
        )
    }

    private func assertLaterCountdownTicksHaveNoIndependentAction(
        three: WorkoutAudioMoment,
        two: WorkoutAudioMoment,
        one: WorkoutAudioMoment,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: three,
                current: two,
                countdownStartUptime: 101
            ),
            .none,
            file: file,
            line: line
        )
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: two,
                current: one,
                countdownStartUptime: 102
            ),
            .none,
            file: file,
            line: line
        )
    }
}

final class WorkoutSessionStateTests: XCTestCase {
    private let steps: [WorkoutStep] = [
        WorkoutStep(
            id: "first",
            number: 1,
            title: "First",
            instruction: "First instruction",
            accessory: "First accessory",
            duration: 60,
            phase: .hang,
            timedWorkDuration: 30
        ),
        WorkoutStep(
            id: "second",
            number: 2,
            title: "Second",
            instruction: "Second instruction",
            accessory: "Second accessory",
            duration: 20,
            phase: .rest),
        WorkoutStep(
            id: "third",
            number: 3,
            title: "Third",
            instruction: "Third instruction",
            accessory: "Third accessory",
            duration: 10,
            phase: .hang)
    ]

    func testInitialStartUsesMonotonicUptimeForElapsedAndCountdown() {
        let wallClockStart = Date(timeIntervalSinceReferenceDate: 3_000)
        let uptime: TimeInterval = 100
        var state = WorkoutSessionState()

        state.toggleRunning(uptime: uptime, now: wallClockStart)

        XCTAssertEqual(state.activeStartUptime, 103)
        XCTAssertEqual(state.routineStartedAt, wallClockStart.addingTimeInterval(3))
        XCTAssertEqual(state.countdownRemaining(at: uptime), 3)
        XCTAssertEqual(state.countdownRemaining(at: uptime + 1.1), 2)
        XCTAssertEqual(
            state.currentElapsed(planDuration: 90, at: uptime + 2.9),
            0,
            accuracy: 0.000_1
        )

        state.transitionExpiredCountdown(at: uptime + 3)

        XCTAssertEqual(state.currentElapsed(planDuration: 90, at: uptime + 4.25), 1.25, accuracy: 0.000_1)
    }

    func testPreparedInitialCountdownBeginsAtArmBoundaryAndRemainsExactlyThreeSeconds() {
        let armedAt: TimeInterval = 100.1
        let wallClockArm = Date(timeIntervalSinceReferenceDate: 3_000.1)
        var state = WorkoutSessionState()

        XCTAssertNil(state.activeStartUptime)
        state.toggleRunning(uptime: armedAt, now: wallClockArm)

        XCTAssertEqual(state.countdownRemaining(at: armedAt), 3)
        XCTAssertEqual(state.countdownRemaining(at: armedAt + 2.999), 1)
        XCTAssertEqual(state.countdownRemaining(at: armedAt + 3), 0)
        XCTAssertEqual(state.activeStartUptime, armedAt + 3)
    }

    func testPreparedSkipCountdownBeginsAtArmBoundaryAndRemainsExactlyThreeSeconds() {
        let armedAt: TimeInterval = 200.1
        var state = WorkoutSessionState(
            activeStartUptime: 190,
            pausedElapsed: 0,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_900)
        )

        state.startSkipCountdown(to: 60, at: armedAt)

        XCTAssertEqual(state.countdownRemaining(at: armedAt), 3)
        XCTAssertEqual(state.countdownRemaining(at: armedAt + 3), 0)
        XCTAssertEqual(state.activeStartUptime, armedAt + 3)
    }

    func testRunningSkipIntoRestTransitionsImmediatelyAndKeepsRunning() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 10,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, now)
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now), 60)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 1), 61)
    }

    func testPausedSkipIntoRestTransitionsImmediatelyAndKeepsPaused() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: nil,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))

        XCTAssertNil(state.countdownKind)
        XCTAssertNil(state.activeStartUptime)
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 10), 60)
    }

    func testPausedSessionSkipCountsDownThenExplicitExpiryStartsRunningDestination() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: nil,
            pausedElapsed: 65,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.countdownRemaining(at: now), 3)
        XCTAssertFalse(state.canNavigate(planDuration: timeline.duration, at: now))

        let countdownStart = now + 3
        XCTAssertEqual(state.countdownRemaining(at: countdownStart), 0)
        XCTAssertEqual(state.countdownKind, .skip)
        state.transitionExpiredCountdown(at: countdownStart)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, countdownStart)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: countdownStart), 80)
        XCTAssertTrue(state.canNavigate(planDuration: timeline.duration, at: countdownStart))
    }

    func testPausedDirectSeekPreservesPausedState() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: nil,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        state.seek(to: 80, planDuration: timeline.duration, at: now)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 4), 80)
    }

    func testInitialStartCancelAndRestartLifecycle() {
        let now: TimeInterval = 100
        let wallClockStart = Date(timeIntervalSinceReferenceDate: 3_000)
        var state = WorkoutSessionState()

        state.toggleRunning(uptime: now, now: wallClockStart)

        let firstStart = now + 3
        XCTAssertEqual(state.activeStartUptime, firstStart)
        XCTAssertEqual(state.routineStartedAt, wallClockStart.addingTimeInterval(3))
        XCTAssertEqual(state.countdownKind, .initial)
        XCTAssertEqual(state.countdownRemaining(at: now), 3)

        state.cancelCountdown(at: now + 1)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.routineStartedAt)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 0)

        let restart = now + 10
        state.toggleRunning(uptime: restart, now: wallClockStart.addingTimeInterval(10))

        XCTAssertEqual(state.activeStartUptime, restart + 3)
        XCTAssertEqual(state.routineStartedAt, wallClockStart.addingTimeInterval(13))
        XCTAssertEqual(state.countdownKind, .initial)
    }

    func testCountdownExpiryReadIsPureUntilExplicitTransitionClearsKind() {
        let now: TimeInterval = 100
        let expiry = now + 5
        let immutableState = WorkoutSessionState(
            activeStartUptime: expiry,
            countdownKind: .skip,
            pausedElapsed: 60,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )
        var state = WorkoutSessionState(
            activeStartUptime: expiry,
            countdownKind: .skip,
            pausedElapsed: 60,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertEqual(immutableState.countdownRemaining(at: expiry), 0)
        XCTAssertEqual(state.countdownRemaining(at: expiry), 0)
        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.activeStartUptime, expiry)

        state.transitionExpiredCountdown(at: expiry - 0.1)

        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.activeStartUptime, expiry)

        state.transitionExpiredCountdown(at: expiry)

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, expiry)
    }

    func testCancelSkipCountdownKeepsDestinationPaused() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 65,
            pausedElapsed: 0,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        state.cancelCountdown(at: now + 2)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.routineStartedAt, Date(timeIntervalSinceReferenceDate: 2_980))
    }

    func testInterruptionDuringSkipCountdownKeepsDestinationPaused() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 65,
            pausedElapsed: 0,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        state.pauseForInterruption(at: now + 2)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.routineStartedAt, Date(timeIntervalSinceReferenceDate: 2_980))
    }

    func testDirectSeekClearsPendingSkipCountdownAndPreservesRunning() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 65,
            pausedElapsed: 0,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        state.seek(to: 80, planDuration: timeline.duration, at: now + 2)

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, now + 2)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(
            state.currentElapsed(planDuration: timeline.duration, at: now + 4),
            82
        )
    }

    func testFinalSkipSeeksDirectlyToCompletion() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 1,
            pausedElapsed: 85,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_900)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, now)
        XCTAssertEqual(state.pausedElapsed, 90)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 10), 90)
        XCTAssertFalse(state.canNavigate(planDuration: timeline.duration, at: now))
    }

}

final class FreeWorkoutTimelineUpdateTests: XCTestCase {
    private func makeStep(id: String, duration: TimeInterval) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 1,
            title: "Hang",
            instruction: "Hang.",
            accessory: "10s hang",
            duration: duration,
            phase: .hang,
            segments: [
                WorkoutSegment(kind: .work, target: .selfSelected, timing: .fixed, duration: duration)
            ]
        )
    }

    func testUpdateStepDurationShiftsLaterOffsets() {
        var timeline = WorkoutTimeline(steps: [
            makeStep(id: "a", duration: 10),
            makeStep(id: "b", duration: 20),
        ])
        XCTAssertTrue(timeline.updateStep(id: "a", FreeWorkoutStepUpdates(duration: 30)))
        XCTAssertEqual(timeline.duration, 50)
        XCTAssertEqual(timeline.startOffset(for: "b"), 30)
        XCTAssertEqual(timeline.currentSteps.first?.duration, 30)
    }

    func testUpdateStepWeightAndReps() {
        var timeline = WorkoutTimeline(steps: [makeStep(id: "a", duration: 10)])
        XCTAssertTrue(timeline.updateStep(
            id: "a",
            FreeWorkoutStepUpdates(externalLoadKGF: 10, repetitions: 5)
        ))
        XCTAssertEqual(timeline.currentSteps.first?.externalLoadKGF, 10)
        XCTAssertEqual(timeline.currentSteps.first?.repetitions, 5)
    }

    func testUpdateStepClampsTimedWorkToDuration() {
        var step = makeStep(id: "a", duration: 60)
        step = WorkoutStep(
            id: step.id, number: step.number, title: step.title,
            instruction: step.instruction, accessory: step.accessory,
            duration: step.duration, phase: step.phase, segments: step.segments,
            timedWorkDuration: 10
        )
        var timeline = WorkoutTimeline(steps: [step])
        XCTAssertTrue(timeline.updateStep(id: "a", FreeWorkoutStepUpdates(duration: 5)))
        XCTAssertEqual(timeline.currentSteps.first?.timedWorkDuration, 5)
    }

    func testUpdateUnknownStepReturnsFalse() {
        var timeline = WorkoutTimeline(steps: [makeStep(id: "a", duration: 10)])
        XCTAssertFalse(timeline.updateStep(id: "missing", FreeWorkoutStepUpdates(duration: 30)))
        XCTAssertEqual(timeline.duration, 10)
    }

    func testUpdateStepKeepsCompoundSegmentDurationsConsistent() {
        let step = WorkoutStep(
            id: "a",
            number: 1,
            title: "Hang",
            instruction: "Hang.",
            accessory: "",
            duration: 60,
            phase: .hang,
            segments: [
                WorkoutSegment(kind: .work, target: .selfSelected, timing: .fixed, duration: 10),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 50),
            ],
            timedWorkDuration: 10
        )
        var timeline = WorkoutTimeline(steps: [step])
        XCTAssertTrue(timeline.updateStep(id: "a", FreeWorkoutStepUpdates(duration: 30, timedWorkDuration: 20)))
        let updated = timeline.currentSteps[0]
        XCTAssertEqual(updated.duration, 30)
        XCTAssertEqual(updated.timedWorkDuration, 20)
        XCTAssertEqual(updated.segments[0].duration, 20)
        XCTAssertEqual(updated.segments[1].duration, 10)
        XCTAssertEqual(updated.segments.compactMap(\.duration).reduce(0, +), 30)
    }
}
