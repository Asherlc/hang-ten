import Foundation

/// Published protocols checked against their primary sources on 2026-10-05.
/// These are guided presets, rather than claims of unchanged official routines.
extension LegacyPlanSeedCatalog {
    static let publishedHangboardPlans: [TrainingPlan] = [
        publishedBeastmakerMaxHangs,
        publishedBeastmakerRepeaters,
        publishedTensionSixAndTen,
        publishedTensionSixSixPlus,
        publishedTensionSingleHangs,
        publishedTensionLongHangs,
        publishedCameronTwoHanded,
        publishedCameronOneHanded,
        publishedREI101
    ]

    static let publishedHangboardNotes: [String: String] = [
        "beastmaker-max-hangs": "Guided adaptation: one athlete-selected grip block, three 10-second hangs and 3-minute rests, selecting the lower published values. Pause for longer if not fully recovered. Replay with another chosen grip; the source leaves the number of grips open. Beastmaker recommends no more than two fingerboard sessions weekly and weight increases of no more than 2 kg at a time.",
        "beastmaker-repeaters": "Guided adaptation: one athlete-selected grip block of six 7-second hangs with 3-second rests. The source leaves the number of grip types open. Rest 3 minutes before replaying with another chosen grip. Beastmaker recommends no more than two fingerboard sessions weekly.",
        "tension-6-and-10": "Guided adaptation: four sets, five 6-second hangs per set, 10 seconds after each hang and 2 minutes between sets. First two sets use half crimp; last two use open crimp, following the source's usual half-and-half split. Select a comfortable four-finger edge (the source generally suggests about 15–20 mm) and a load that approaches form failure on repetition five without failing. Source load adjustments are 2.5–5 lb.",
        "tension-6-6-6-plus": "Guided adaptation: four sets, first two half crimp and last two open crimp. For each set, pause the main workout timer, then start the separate stopwatch. Repeat 6 seconds hanging and 6 seconds resting, six or more repetitions until proper grip or shoulder form fails. Stop the stopwatch, skip the step and resume the main timer. The stopwatch records the whole set including its short rests. If left running, the main timer advances after 72 seconds. Rest 2 minutes between sets. Increase load by the smallest useful amount after reaching the chosen upper repetition range.",
        "tension-single-hangs": "Guided adaptation: four 4-second hangs and 2-minute rests, selecting the source's lowest stated duration and count. First two hangs use half crimp; last two use open crimp. The source's main example is 6 seconds and allows 4–8 seconds. Before a performance phase, select a load leaving a 2–3-second buffer to form failure. Source recommends prior years of regular climbing and repeater training.",
        "tension-long-hangs": "Guided adaptation: three stopwatch hangs, using an athlete-selected open crimp or half crimp, with 2-minute rests. Pause the main workout timer, then start the separate stopwatch; each hang ends at form failure. Stop the stopwatch, skip the step and resume the main timer. If left running, the main timer advances after 15 seconds. Choose load to reach form failure in 15–30 seconds. No fixed grip sequence is prescribed.",
        "cameron-horst-two-handed-7-53": "Guided adaptation: three sets of three 7-second hangs, exactly 53 seconds between hangs and 3 minutes between sets. Choose a roughly 20 mm edge; set training weight to what you can hold for a single 10-second hang. Complete the source's 20–30-minute progressive warm-up before starting. Source recommends twice weekly; avoid this protocol during performance climbing. If the final set is not a struggle, consider adding 5–10 lb next workout.",
        "cameron-horst-one-arm": "Guided adaptation: five left/right pairs of 5-second hangs on a 20–24 mm edge, switching directly between hands, with 3 minutes between pairs. Left-first order is an app choice. Choose half crimp or open crimp; replay with the other grip as appropriate, because the source does not prescribe their order or allocation. Complete the source's 20–30-minute progressive warm-up before starting. Use a helper sling or counterweight as needed. Source limits this advanced protocol to twice weekly; add 2–5 lb only after completing all five hangs per hand unassisted.",
        "rei-hangboard-training-101": "Guided adaptation of the initial three-week phase: four sets of four 10-second hangs using a matched pair, all four fingers and an open-handed grip. Rest 1 minute between hangs and 5 minutes between sets; the set break replaces the final 1-minute break. Warm up fully before starting. After three weeks the source switches to holds allowing only 5–8-second hangs. Stop the workout if a set cannot be completed; take a week off for finger or elbow soreness and reevaluate form."
    ]

    private static let publishedBeastmakerURL = "https://www.beastmaker.co.uk/pages/training"
    private static let publishedTensionURL = "https://tensionclimbing.com/blogs/blog/hangboarding-a-way"
    private static let publishedCameronURL = "https://trainingforclimbing.com/advanced-hangboard-training-technique/"
    private static let publishedFourFingerEdge = ContactRequirement(
        kind: .edge, fingerCapacity: 4, selection: .bilateralPair
    )

    private static func publishedPlan(
        id: String, title: String, subtitle: String, level: String,
        source: String, url: String, steps: [WorkoutStep]
    ) -> TrainingPlan {
        TrainingPlan(
            id: id, title: title, subtitle: subtitle, level: level,
            sourceLabel: source, sourceURL: URL(string: url), provenance: .adapted,
            boardID: nil,
            steps: steps.enumerated().map { $0.element.withNumber($0.offset + 1) }
        )
    }

    private static func publishedHang(
        _ id: String, title: String, instruction: String, duration: TimeInterval,
        target: WorkoutSegmentTarget = .selfSelected,
        timing: WorkoutSegmentTiming = .fixed, grip: GripType? = nil,
        fingers: FingerConfiguration? = nil,
        handUse: WorkoutHandUse = .double, side: WorkoutSide = .both,
        repetitions: Int? = nil
    ) -> WorkoutStep {
        WorkoutStep(
            id: id, number: 0, title: title, instruction: instruction,
            accessory: timing == .stopwatch ? "Until form failure · stopwatch" : "\(Int(duration))-second hang",
            duration: duration, phase: .hang,
            segments: [.init(kind: .work, target: target, timing: timing,
                             duration: timing == .fixed ? duration : nil)],
            gripType: grip, fingerConfiguration: fingers, handUse: handUse, side: side, repetitions: repetitions,
            timedWorkDuration: timing == .fixed ? duration : nil
        )
    }

    private static func publishedRest(
        _ id: String, seconds: TimeInterval, instruction: String = "Rest before the next hang."
    ) -> WorkoutStep {
        WorkoutStep(
            id: id, number: 0, title: "Rest", instruction: instruction,
            accessory: "\(Int(seconds))-second rest", duration: seconds, phase: .rest,
            segments: [.init(kind: .rest, target: nil, timing: .fixed, duration: seconds)]
        )
    }

    private static let publishedBeastmakerMaxHangs: TrainingPlan = {
        let id = "beastmaker-max-hangs"
        var steps: [WorkoutStep] = []
        for repetition in 1...3 {
            steps.append(publishedHang("\(id).hang-\(repetition)", title: "Max hang \(repetition) of 3",
                                       instruction: "Use a hold and grip you want to improve; hang for 10 seconds." + (repetition == 3 ? " Rest at least 3 minutes and until fully recovered before replaying with another grip." : ""), duration: 10))
            if repetition < 3 {
                steps.append(publishedRest("\(id).rest-\(repetition)", seconds: 180,
                                           instruction: "Rest at least 3 minutes. Pause longer until you feel fully recovered."))
            }
        }
        return publishedPlan(id: id, title: "Beastmaker Max Hangs", subtitle: "Maximum strength · one selected grip", level: "Strength",
                             source: "Beastmaker · Training", url: publishedBeastmakerURL, steps: steps)
    }()

    private static let publishedBeastmakerRepeaters: TrainingPlan = {
        let id = "beastmaker-repeaters"
        var steps: [WorkoutStep] = []
        for repetition in 1...6 {
            steps.append(publishedHang("\(id).hang-\(repetition)", title: "Repeater \(repetition) of 6",
                                       instruction: "Use a hold and grip you want to improve; hang for 7 seconds.", duration: 7))
            steps.append(publishedRest("\(id).rest-\(repetition)", seconds: 3))
        }
        steps.append(publishedRest("\(id).grip-rest", seconds: 180,
                                   instruction: "Rest 3 minutes before replaying this block with another chosen grip."))
        return publishedPlan(id: id, title: "Beastmaker Repeaters", subtitle: "Strength endurance · 7 seconds on / 3 off", level: "Strength endurance",
                             source: "Beastmaker · Training", url: publishedBeastmakerURL, steps: steps)
    }()

    private static let publishedTensionSixAndTen: TrainingPlan = {
        let id = "tension-6-and-10"
        var steps: [WorkoutStep] = []
        for set in 1...4 {
            let grip: GripType = set <= 2 ? .halfCrimp : .openHand
            let name = set <= 2 ? "half crimp" : "open crimp"
            for repetition in 1...5 {
                steps.append(publishedHang("\(id).set-\(set).hang-\(repetition)", title: "Set \(set) · hang \(repetition) of 5",
                                           instruction: "Hang using \(name). Choose load to approach form failure on the fifth repetition without failing.", duration: 6,
                                           target: .requirements([publishedFourFingerEdge]), grip: grip))
                steps.append(publishedRest("\(id).set-\(set).rest-\(repetition)", seconds: 10))
            }
            if set < 4 { steps.append(publishedRest("\(id).set-rest-\(set)", seconds: 120)) }
        }
        return publishedPlan(id: id, title: "Tension 6 and 10", subtitle: "Structural strength · four sets of five", level: "Strength",
                             source: "Tension · Hangboarding: A Way (2019)", url: publishedTensionURL, steps: steps)
    }()

    private static let publishedTensionSixSixPlus: TrainingPlan = {
        let id = "tension-6-6-6-plus"
        var steps: [WorkoutStep] = []
        for set in 1...4 {
            let grip: GripType = set <= 2 ? .halfCrimp : .openHand
            let name = set <= 2 ? "half crimp" : "open crimp"
            steps.append(publishedHang("\(id).set-\(set)", title: "Set \(set) · 6:6 to form failure",
                                       instruction: "Pause main timer; start stopwatch. \(name.capitalized): 6s hang / 6s rest, 6+ reps to form failure. Stop stopwatch, skip step, resume main timer.",
                                       duration: 72, target: .requirements([publishedFourFingerEdge]), timing: .stopwatch, grip: grip))
            if set < 4 { steps.append(publishedRest("\(id).set-rest-\(set)", seconds: 120)) }
        }
        return publishedPlan(id: id, title: "Tension 6:6×6+", subtitle: "Work capacity · repeat to form failure", level: "Strength endurance",
                             source: "Tension · Hangboarding: A Way (2019)", url: publishedTensionURL, steps: steps)
    }()

    private static let publishedTensionSingleHangs: TrainingPlan = {
        let id = "tension-single-hangs"
        var steps: [WorkoutStep] = []
        for repetition in 1...4 {
            let name = repetition <= 2 ? "half crimp" : "open crimp"
            steps.append(publishedHang("\(id).hang-\(repetition)", title: "Single hang \(repetition) of 4",
                                       instruction: "Hang in \(name) for 4 seconds. Select load leaving 2–3 seconds before form failure.", duration: 4,
                                       target: .requirements([publishedFourFingerEdge]), grip: repetition <= 2 ? .halfCrimp : .openHand))
            if repetition < 4 { steps.append(publishedRest("\(id).rest-\(repetition)", seconds: 120)) }
        }
        return publishedPlan(id: id, title: "Tension Single Hangs", subtitle: "Maximum strength · four 4-second hangs", level: "Strength",
                             source: "Tension · Hangboarding: A Way (2019)", url: publishedTensionURL, steps: steps)
    }()

    private static let publishedTensionLongHangs: TrainingPlan = {
        let id = "tension-long-hangs"
        var steps: [WorkoutStep] = []
        for repetition in 1...3 {
            steps.append(publishedHang("\(id).hang-\(repetition)", title: "Long hang \(repetition) of 3",
                                       instruction: "Pause main timer; start stopwatch. Open or half crimp to grip/shoulder form failure (aim 15–30s). Stop stopwatch, skip step, resume main timer.", duration: 15,
                                       target: .requirements([publishedFourFingerEdge]), timing: .stopwatch))
            if repetition < 3 { steps.append(publishedRest("\(id).rest-\(repetition)", seconds: 120)) }
        }
        return publishedPlan(id: id, title: "Tension Long Hangs", subtitle: "Structural capacity · hangs to form failure", level: "Strength endurance",
                             source: "Tension · Hangboarding: A Way (2019)", url: publishedTensionURL, steps: steps)
    }()

    private static let publishedCameronTwoHanded: TrainingPlan = {
        let id = "cameron-horst-two-handed-7-53"
        var steps: [WorkoutStep] = []
        for set in 1...3 {
            for repetition in 1...3 {
                steps.append(publishedHang("\(id).set-\(set).hang-\(repetition)", title: "Set \(set) · hang \(repetition) of 3",
                                           instruction: "Use a roughly 20 mm hold with both hands. Use the training weight you can hold for one 10-second hang.", duration: 7,
                                           target: .requirements([.edge(depth: .range(.init(minimum: 20, maximum: 20)), selection: .bilateralPair)])))
                if repetition < 3 { steps.append(publishedRest("\(id).set-\(set).rest-\(repetition)", seconds: 53)) }
            }
            if set < 3 { steps.append(publishedRest("\(id).set-rest-\(set)", seconds: 180)) }
        }
        return publishedPlan(id: id, title: "Cameron Hörst Two-Handed 7/53", subtitle: "Finger strength · three sets of three", level: "Intermediate / Advanced",
                             source: "Cameron Hörst · Training For Climbing (2023)", url: publishedCameronURL, steps: steps)
    }()

    private static let publishedCameronOneHanded: TrainingPlan = {
        let id = "cameron-horst-one-arm"
        let edge = ContactRequirement.edge(depth: .range(.init(minimum: 20, maximum: 24)), selection: .single)
        var steps: [WorkoutStep] = []
        for pair in 1...5 {
            for side in [WorkoutSide.left, .right] {
                steps.append(publishedHang("\(id).pair-\(pair).\(side.rawValue)", title: "Pair \(pair) · \(side.rawValue) hand",
                                           instruction: "Hang one-handed on a 20–24 mm edge for 5 seconds. Choose half crimp or open crimp. Use a helper sling or counterweight with the free hand if needed; switch directly to the other hand after the first hang.", duration: 5,
                                           target: .requirements([edge]), handUse: .single, side: side))
            }
            if pair < 5 { steps.append(publishedRest("\(id).pair-rest-\(pair)", seconds: 180)) }
        }
        return publishedPlan(id: id, title: "Cameron Hörst One-Arm Strength", subtitle: "Maximum strength · five hangs per hand", level: "Advanced",
                             source: "Cameron Hörst · Training For Climbing (2023)", url: publishedCameronURL, steps: steps)
    }()

    private static let publishedREI101: TrainingPlan = {
        let id = "rei-hangboard-training-101"
        var steps: [WorkoutStep] = []
        for set in 1...4 {
            for repetition in 1...4 {
                steps.append(publishedHang("\(id).set-\(set).hang-\(repetition)", title: "Set \(set) · hang \(repetition) of 4",
                                           instruction: "Open hand on matched holds with four fingers; no crimping. Choose holds allowing 10–15s. Slight elbow bend; shoulder blades down and back.", duration: 10, grip: .openHand,
                                           fingers: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])))
                if repetition < 4 { steps.append(publishedRest("\(id).set-\(set).rest-\(repetition)", seconds: 60)) }
            }
            if set < 4 { steps.append(publishedRest("\(id).set-rest-\(set)", seconds: 300,
                                                   instruction: "Rest 5 minutes. Use the same holds or holds of similar challenge for the next set.")) }
        }
        return publishedPlan(id: id, title: "REI Hangboard Training 101", subtitle: "Finger strength · initial three-week phase", level: "Introductory",
                             source: "REI · Dave Sheldon (2017)", url: "https://www.rei.com/blog/uncategorized/hangboard-training-101", steps: steps)
    }()
}
