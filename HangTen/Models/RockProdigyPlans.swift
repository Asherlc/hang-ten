import Foundation

extension LegacyPlanSeedCatalog {
    static let publishedRockProdigyPlans: [TrainingPlan] = [
        rockProdigyBeginner, rockProdigyIntermediate, rockProdigyAdvanced,
        rockProdigyPivotIntroductory, rockProdigyPivotIntermediate
    ]

    static let rockProdigyPublishedNotes: [String: String] = [
        "rock-prodigy.original-beginner": "Guided preset: six athlete-selected grips, the minimum of the original article’s 6–10. One set of five 10-second hangs per grip; 5 seconds between hangs and 2 minutes between grips. Choose and record appropriate added or removed resistance per grip. Complete the source’s warm-up before starting; it is outside this timed preset.",
        "rock-prodigy.rptc-intermediate": "Guided preset follows the intermediate workout table: warm-up jug, then six working grips with seven and six repetitions. The table prescribes 3-minute set rests; the separate single-set timing diagram instead shows 2:53 after the seventh hang. This adaptation uses the intermediate table’s 3 minutes. Baseline is individual, often below bodyweight; the second set adds 10 lb to that grip’s baseline. Aim for near-failure at the end of each grip’s last set; after successfully completing a workout, the guide suggests 5 lb more for like sets next workout. No climbing or other finger training for at least 48 hours afterward. Wide pinch width remains athlete-selected. This table is restricted to the Training Center. Its current package lacks edge depth and pocket capacity/depth metadata, so the named edge and pocket grips must be located manually from the source guide; their highlights are omitted.",
        "rock-prodigy.original-advanced": "Original 2006 article, rather than the subsequently updated Training Manual. Six athlete-selected grips, three sets of seven, six and five 7-second hangs; 3 seconds between repetitions, 2 minutes between sets, 3 minutes between grips. Increase resistance between sets. Complete the source’s warm-up before this timed preset.",
        "rock-prodigy.pivot-introductory": "Pivot Quick Start Guide pages 16–17. Includes every printed repetition rest, the additional 20-second between-exercise pauses and the three 2-minute rotation breaks. Follow the guide’s orientation and grip illustrations manually: the current package cannot truthfully resolve all named grips or orientation-specific highlights, so this preset has no hold highlights; the model does not automatically rotate. Warm up before starting, as the guide instructs.",
        "rock-prodigy.pivot-intermediate": "Pivot Quick Start Guide pages 18–19. Includes every printed repetition rest, the additional 15-second between-exercise pauses and the four 2-minute rotation breaks. Follow the guide’s orientation and grip illustrations manually: the current package lacks deep mono and full orientation-specific hold metadata, so this preset has no hold highlights; the model does not automatically rotate. Warm up before starting, as the guide instructs."
    ]

    private static let originalRockProdigyURL = URL(string: "https://rockclimberstrainingmanual.com/tools-for-rock-climbing-training/the-making-of-a-rock-prodigy/")!
    private static let rptcPublishedURL = URL(string: "https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155")!
    private static let pivotPublishedURL = URL(string: "https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507")!

    private static func rockRest(_ id: String, _ title: String, _ seconds: TimeInterval, instruction: String? = nil) -> WorkoutStep {
        WorkoutStep(id: id, number: 0, title: title, instruction: instruction ?? "Rest before the next set.", accessory: "\(Int(seconds))s rest", duration: seconds, phase: .rest,
                    segments: [WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: seconds)])
    }

    private static func rockHang(_ id: String, _ title: String, _ instruction: String, hang: TimeInterval, rest: TimeInterval,
                                 targets: [ContactRequirement] = [], grip: GripType? = nil,
                                 fingers: FingerConfiguration? = nil) -> WorkoutStep {
        var segments = [WorkoutSegment(kind: .work, target: .fromLegacyTargets(targets), timing: .fixed, duration: hang)]
        if rest > 0 { segments.append(WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: rest)) }
        return WorkoutStep(id: id, number: 0, title: title, instruction: instruction,
                           accessory: "\(Int(hang))s hang" + (rest > 0 ? " · \(Int(rest))s rest" : ""),
                           duration: hang + rest, phase: .hang, segments: segments,
                           gripType: grip, fingerConfiguration: fingers, timedWorkDuration: hang)
    }

    private static func rockNumbered(_ steps: [WorkoutStep]) -> [WorkoutStep] {
        steps.enumerated().map { index, step in
            WorkoutStep(id: step.id, number: index + 1, title: step.title, instruction: step.instruction,
                        accessory: step.accessory, duration: step.duration, phase: step.phase, segments: step.segments,
                        gripType: step.gripType, fingerConfiguration: step.fingerConfiguration,
                        handUse: step.handUse, side: step.side, action: step.action,
                        repetitions: step.repetitions, externalLoadKGF: step.externalLoadKGF,
                        timedWorkDuration: step.timedWorkDuration)
        }
    }

    private static let rockProdigyBeginner = TrainingPlan(
        id: "rock-prodigy.original-beginner", title: "Rock Prodigy · Original Beginner",
        subtitle: "Strength · six athlete-selected grips, 10/5 repeaters.", level: "Beginner",
        sourceLabel: "Anderson · Making of a Rockprodigy (2006)", sourceURL: originalRockProdigyURL,
        provenance: .adapted, boardID: nil,
        steps: rockNumbered({
            var steps: [WorkoutStep] = []
            for grip in 1...6 {
                for rep in 1...5 {
                    steps.append(rockHang("rp-beginner-\(grip)-\(rep)", "Selected grip \(grip) · rep \(rep) of 5",
                                          "Use grip \(grip) from your six chosen positions. Dead hang for 10 seconds. Record the added or removed resistance; choose resistance so the last repetition is difficult to complete.",
                                          hang: 10, rest: rep < 5 ? 5 : 0))
                }
                if grip < 6 { steps.append(rockRest("rp-beginner-rest-\(grip)", "Between-grip recovery", 120)) }
            }
            return steps
        }())
    )

    private static let rockProdigyAdvanced = TrainingPlan(
        id: "rock-prodigy.original-advanced", title: "Rock Prodigy · Original Advanced",
        subtitle: "Strength · six selected grips, 7/6/5-repetition sets.", level: "Advanced",
        sourceLabel: "Anderson · Making of a Rockprodigy (2006)", sourceURL: originalRockProdigyURL,
        provenance: .adapted, boardID: nil,
        steps: rockNumbered({
            var steps: [WorkoutStep] = []
            for grip in 1...6 {
                for (setIndex, reps) in [7, 6, 5].enumerated() {
                    for rep in 1...reps {
                        steps.append(rockHang("rp-advanced-\(grip)-\(setIndex + 1)-\(rep)", "Selected grip \(grip) · set \(setIndex + 1) · rep \(rep) of \(reps)",
                                              "Dead hang on selected grip \(grip). Increase resistance between sets on this grip and record it; this is the original article’s three-set protocol.",
                                              hang: 7, rest: rep < reps ? 3 : 0))
                    }
                    if setIndex < 2 { steps.append(rockRest("rp-advanced-set-rest-\(grip)-\(setIndex + 1)", "Between-set recovery · increase resistance", 120)) }
                }
                if grip < 6 { steps.append(rockRest("rp-advanced-grip-rest-\(grip)", "Between-grip recovery", 180)) }
            }
            return steps
        }())
    )

    private static let rockProdigyIntermediate = TrainingPlan(
        id: "rock-prodigy.rptc-intermediate", title: "Rock Prodigy · RPTC Intermediate",
        subtitle: "Strength · jug warm-up and six working grips, 7/3 repeaters.", level: "Intermediate",
        sourceLabel: "Trango · RPTC intermediate workout table", sourceURL: rptcPublishedURL,
        provenance: .adapted, boardID: "trango.rock-prodigy-training-center",
        steps: rockNumbered({
            let pair = ContactSelectionPolicy.bilateralPair
            let grips: [(String, ContactRequirement?, GripType?)] = [
                ("Warm-up jug", .kind(.jug, selection: pair), nil),
                ("Large open-hand edge", nil, .openHand),
                ("Deep two-finger pocket", nil, nil),
                ("Small semi-closed crimp", nil, nil),
                ("Shallow three-finger pocket", nil, nil),
                ("Wide pinch", .kind(.pinch, selection: pair), nil),
                ("Sloper", .kind(.sloper, selection: pair), .sloper)
            ]
            var steps: [WorkoutStep] = []
            for (gripIndex, grip) in grips.enumerated() {
                let counts = gripIndex == 0 ? [7] : [7, 6]
                for (setIndex, reps) in counts.enumerated() {
                    for rep in 1...reps {
                        steps.append(rockHang("rp-rptc-\(gripIndex)-\(setIndex)-\(rep)", "\(grip.0) · set \(setIndex + 1) · rep \(rep) of \(reps)",
                                              "Dead hang on the \(grip.0.lowercased()) with both hands. \(setIndex == 0 ? "Use this grip’s baseline resistance." : "Add 10 lb to this grip’s baseline.") No pull-ups or lock-offs." + (grip.1 == nil ? " Locate this grip in the guide." : ""),
                                              hang: 7, rest: rep < reps ? 3 : 0, targets: grip.1.map { [$0] } ?? [], grip: grip.2))
                    }
                    if gripIndex < grips.count - 1 || setIndex < counts.count - 1 {
                        steps.append(rockRest("rp-rptc-rest-\(gripIndex)-\(setIndex)", "Three-minute set recovery", 180))
                    }
                }
            }
            return steps
        }())
    )

    private struct PivotExercise {
        let orientation: String
        let name: String
        let hang: TimeInterval
        let rest: TimeInterval
        let repeats: Int
        let pause: TimeInterval
        let nextOrientation: String?

        var fingers: FingerConfiguration? {
            switch name {
            case "Two-finger pocket": FingerConfiguration(engagedFingers: [.middle, .ring])
            case "Three-finger pocket": FingerConfiguration(engagedFingers: [.index, .middle, .ring])
            case "Deep mono": FingerConfiguration(engagedFingers: [.middle])
            default: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])
            }
        }

        // The source requires paired contacts. Current Pivot model contacts
        // lack resolver-compatible bilateral frames, even for named pockets
        // and slopers, so retain the source instructions without substitution.
        var targets: [ContactRequirement] { [] }

    }

    private static func pivotSteps(_ id: String, _ exercises: [PivotExercise]) -> [WorkoutStep] {
        var steps: [WorkoutStep] = []
        for (index, exercise) in exercises.enumerated() {
            for rep in 1...exercise.repeats {
                steps.append(rockHang("\(id)-\(index + 1)-\(rep)", "Orientation \(exercise.orientation) · \(exercise.name) · \(rep)/\(exercise.repeats)",
                                      "Hang on the \(exercise.name.lowercased()) in orientation \(exercise.orientation). Follow the guide’s grip illustration and set the physical board orientation manually.",
                                      hang: exercise.hang, rest: exercise.rest, targets: exercise.targets, fingers: exercise.fingers))
            }
            if exercise.pause > 0 {
                steps.append(rockRest("\(id)-pause-\(index + 1)", "Pause one full cycle", exercise.pause,
                                      instruction: "After finishing this grip set, pause one full cycle before the next exercise in this orientation."))
            }
            if let next = exercise.nextOrientation {
                steps.append(rockRest("\(id)-rotate-\(index + 1)", "Rest and pivot to orientation \(next)", 120,
                                      instruction: "Rest two minutes and re-orient the physical board to orientation \(next), following the manufacturer’s guide."))
            }
        }
        return rockNumbered(steps)
    }

    private static let rockProdigyPivotIntroductory = TrainingPlan(
        id: "rock-prodigy.pivot-introductory", title: "Rock Prodigy Pivot · Introductory",
        subtitle: "Strength and endurance · six exercises with rotation breaks.", level: "Introductory",
        sourceLabel: "Trango · Pivot Quick Start Guide, pp. 16–17", sourceURL: pivotPublishedURL,
        provenance: .adapted, boardID: "trango.rock-prodigy-pivot",
        steps: pivotSteps("rp-pivot-intro", [
            .init(orientation: "1", name: "Jug", hang: 10, rest: 10, repeats: 3, pause: 20, nextOrientation: nil),
            .init(orientation: "1", name: "Sloper rail", hang: 10, rest: 10, repeats: 3, pause: 0, nextOrientation: "3"),
            .init(orientation: "3", name: "Sloper", hang: 10, rest: 10, repeats: 3, pause: 20, nextOrientation: nil),
            .init(orientation: "3", name: "Large crimp", hang: 5, rest: 15, repeats: 3, pause: 0, nextOrientation: "3 Switch"),
            .init(orientation: "3 Switch", name: "Incut rail", hang: 10, rest: 10, repeats: 6, pause: 0, nextOrientation: "1"),
            .init(orientation: "1", name: "Horizontal pinch", hang: 10, rest: 10, repeats: 3, pause: 0, nextOrientation: nil)
        ])
    )

    private static let rockProdigyPivotIntermediate = TrainingPlan(
        id: "rock-prodigy.pivot-intermediate", title: "Rock Prodigy Pivot · Intermediate",
        subtitle: "Strength and endurance · ten exercises with rotation breaks.", level: "Intermediate",
        sourceLabel: "Trango · Pivot Quick Start Guide, pp. 18–19", sourceURL: pivotPublishedURL,
        provenance: .adapted, boardID: "trango.rock-prodigy-pivot",
        steps: pivotSteps("rp-pivot-intermediate", [
            .init(orientation: "1", name: "Jug", hang: 10, rest: 5, repeats: 5, pause: 15, nextOrientation: nil),
            .init(orientation: "1", name: "Sloper rail", hang: 10, rest: 5, repeats: 5, pause: 15, nextOrientation: nil),
            .init(orientation: "1", name: "Small sloped crimp", hang: 10, rest: 5, repeats: 5, pause: 0, nextOrientation: "3"),
            .init(orientation: "3", name: "Large closed crimp", hang: 10, rest: 5, repeats: 5, pause: 15, nextOrientation: nil),
            .init(orientation: "3", name: "Three-finger pocket", hang: 10, rest: 5, repeats: 5, pause: 15, nextOrientation: nil),
            .init(orientation: "3", name: "Two-finger pocket", hang: 10, rest: 5, repeats: 5, pause: 0, nextOrientation: "4"),
            .init(orientation: "4", name: "Deep mono", hang: 10, rest: 5, repeats: 5, pause: 0, nextOrientation: "1"),
            .init(orientation: "1", name: "Horizontal pinch (wide)", hang: 10, rest: 5, repeats: 5, pause: 15, nextOrientation: nil),
            .init(orientation: "1", name: "Horizontal pinch (narrow)", hang: 10, rest: 5, repeats: 5, pause: 0, nextOrientation: "3"),
            .init(orientation: "3", name: "Sloper", hang: 10, rest: 5, repeats: 5, pause: 0, nextOrientation: nil)
        ])
    )
}
