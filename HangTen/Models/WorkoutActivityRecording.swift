import Foundation

extension HoldTarget {
    static func feature(
        _ feature: HoldFeature,
        fallbacks: [HoldFeature],
        fingerCapacity: Int? = nil
    ) -> HoldTarget {
        HoldTarget(
            holdIDs: [],
            kind: nil,
            feature: feature,
            fallbackFeatures: fallbacks,
            fingerCapacity: fingerCapacity
        )
    }
}

struct RecordedActivitySegment: Codable, Hashable {
    let stepID: String
    let stepNumber: Int
    let kind: WorkoutSegmentKind
    let holdIDs: [String]
    let holdType: String?
    let sizeMillimeters: Double?
    let durationSeconds: TimeInterval?

    enum CodingKeys: String, CodingKey { case stepID, stepNumber, kind, holdIDs, holdType, sizeMillimeters, durationSeconds }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(stepID, forKey: .stepID)
        try container.encode(stepNumber, forKey: .stepNumber)
        try container.encode(kind, forKey: .kind)
        try container.encode(holdIDs, forKey: .holdIDs)
        try container.encodeIfPresent(holdType, forKey: .holdType)
        try container.encodeIfPresent(sizeMillimeters, forKey: .sizeMillimeters)
        try container.encodeIfPresent(durationSeconds, forKey: .durationSeconds)
    }
}

struct RecordedActivityStepMeasurement: Codable, Hashable {
    let stepID: String
    let peakLoadKGF: Double?
    let actualLoadedDurationSeconds: TimeInterval?
}

struct WorkoutActivityMetadata: Codable, Hashable {
    let version: Int
    let segments: [RecordedActivitySegment]
    let measurements: [RecordedActivityStepMeasurement]?

    init(
        version: Int = 1,
        segments: [RecordedActivitySegment],
        measurements: [RecordedActivityStepMeasurement]? = nil
    ) {
        self.version = version
        self.segments = segments
        self.measurements = measurements
    }
}

struct WorkoutActivitySegmentKey: Hashable {
    let stepID: String
    let segmentIndex: Int
}

enum WorkoutActivityRecordingError: LocalizedError, Equatable {
    case unresolvedTarget(stepID: String, segmentIndex: Int)
    case invalidObservedDuration(WorkoutActivitySegmentKey)

    var errorDescription: String? {
        switch self {
        case .unresolvedTarget:
            "Hang Ten could not match a workout activity to the selected board."
        case .invalidObservedDuration:
            "Hang Ten could not use the recorded workout duration."
        }
    }
}

internal enum BoardTargetResolver {
    static func resolveHoldIDs(
        for target: HoldTarget,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [String] {
        resolveHoldIDs(for: target, among: compatibleHolds(on: board, gripType: gripType))
    }

    static func resolveHoldIDs(
        for target: HoldTarget,
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [String] {
        selectHoldIDs(
            resolveHoldIDs(for: target, on: board, gripType: gripType),
            for: handUse,
            side: side,
            on: board
        )
    }

    static func resolveObjects(
        for target: HoldTarget,
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [String] {
        let selectedHoldIDs = Set(resolveHoldIDs(
            for: target,
            handUse: handUse,
            side: side,
            on: board,
            gripType: gripType
        ))
        var objectIDs: [String] = []
        for hold in board.holds where selectedHoldIDs.contains(hold.id) {
            if !objectIDs.contains(hold.equipmentObjectID) {
                objectIDs.append(hold.equipmentObjectID)
            }
        }
        return objectIDs
    }

    private static func resolveHoldIDs(for target: HoldTarget, among holds: [BoardHold]) -> [String] {
        if !target.holdIDs.isEmpty {
            let available = Set(holds.map(\.id))
            return target.holdIDs.filter(available.contains)
        }
        if let feature = target.feature {
            let exact = matching(feature, fingerCapacity: target.fingerCapacity, among: holds)
            let selectedExact = selectingGenericPocketPair(
                from: exact,
                feature: feature,
                fingerCapacity: target.fingerCapacity
            )
            if !selectedExact.isEmpty {
                if feature.holdKind == .pocket, target.fingerCapacity != nil {
                    return oneHoldPerHand(from: selectedExact).map(\.id)
                }
                return selectedExact.map(\.id)
            }
            for fallback in target.fallbackFeatures {
                let matches = matching(fallback, fingerCapacity: target.fingerCapacity, among: holds)
                let selectedMatches = selectingGenericPocketPair(
                    from: matches,
                    feature: fallback,
                    fingerCapacity: target.fingerCapacity
                )
                if !selectedMatches.isEmpty { return selectedMatches.map(\.id) }

                // A fallback identifies a physically available substitute, not
                // the source-prescribed finger capacity. Preserve capacity for
                // the primary target, but do not reject an explicit fallback
                // merely because that substitute has no matching capacity.
                let capacityAgnosticMatches = matching(fallback, fingerCapacity: nil, among: holds)
                let selectedCapacityAgnosticMatches = selectingGenericPocketPair(
                    from: capacityAgnosticMatches,
                    feature: fallback,
                    fingerCapacity: target.fingerCapacity
                )
                if !selectedCapacityAgnosticMatches.isEmpty {
                    return selectedCapacityAgnosticMatches.map(\.id)
                }

            }
            return []
        }
        guard let kind = target.kind else { return [] }
        let matches = holds.filter { hold in
            guard hold.kind == kind else { return false }
            guard let capacity = target.fingerCapacity else { return true }
            return hold.fingerCapacity == capacity
        }
        if kind == .pocket {
            if target.fingerCapacity != nil, !matches.isEmpty {
                return oneHoldPerHand(from: matches).map(\.id)
            }
            if target.fingerCapacity == nil {
                return genericPocketSelection(from: matches).map(\.id)
            }
        }
        if !matches.isEmpty { return matches.map(\.id) }
        for fallback in target.fallbackFeatures {
            let fallbackMatches = matching(
                fallback,
                fingerCapacity: target.fingerCapacity,
                among: holds
            )
            if !fallbackMatches.isEmpty { return fallbackMatches.map(\.id) }
        }

        // Only a capacity-qualified pocket target may relax a declared
        // fallback's capacity. This is the documented availability ladder
        // for pocket routines; doing it for every kind target would broaden
        // unrelated targets and custom routines. Try every exact-capacity
        // fallback above before accepting any capacity-agnostic substitute.
        if kind == .pocket, target.fingerCapacity != nil {
            for fallback in target.fallbackFeatures {
                // A declared fallback is an available substitute, rather than a
                // claim that it shares the source target's finger capacity.
                let capacityAgnosticFallbackMatches = matching(
                    fallback,
                    fingerCapacity: nil,
                    among: holds
                )
                if !capacityAgnosticFallbackMatches.isEmpty {
                    return capacityAgnosticFallbackMatches.map(\.id)
                }
            }
        }
        return []
    }

    static func resolveHolds(
        for target: HoldTarget,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [BoardHold] {
        let ids = Set(resolveHoldIDs(for: target, on: board, gripType: gripType))
        return board.holds.filter { ids.contains($0.id) }
    }

    static func resolveHolds(
        for target: HoldTarget,
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [BoardHold] {
        let ids = Set(resolveHoldIDs(
            for: target,
            handUse: handUse,
            side: side,
            on: board,
            gripType: gripType
        ))
        return board.holds.filter { ids.contains($0.id) }
    }

    static func substituteHoldIDs(
        for target: HoldTarget,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [String] {
        let holds = compatibleHolds(on: board, gripType: gripType)
        let primary = resolveHoldIDs(for: target, among: holds)
        if !primary.isEmpty { return primary }
        let closestPrimary = closestMatch(for: target, among: holds)
        if !closestPrimary.isEmpty { return closestPrimary }
        guard target.feature?.holdKind == .pocket || target.kind == .pocket else { return [] }
        for fallback in target.fallbackFeatures where fallback.holdKind == .edge {
            let fallbackTarget = HoldTarget.feature(
                fallback,
                fingerCapacity: target.fingerCapacity
            )
            let closestFallback = closestMatch(for: fallbackTarget, among: holds)
            if !closestFallback.isEmpty { return closestFallback }
        }
        return []
    }

    static func substituteHoldIDs(
        for target: HoldTarget,
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [String] {
        let holds = compatibleHolds(on: board, gripType: gripType)
        let primary = resolveHoldIDs(for: target, among: holds)
        if !primary.isEmpty {
            return selectHoldIDs(primary, for: handUse, side: side, on: board)
        }
        let closestPrimary = closestMatch(for: target, among: holds)
        if !closestPrimary.isEmpty {
            return selectHoldIDs(closestPrimary, for: handUse, side: side, on: board)
        }
        guard target.feature?.holdKind == .pocket || target.kind == .pocket else { return [] }
        for fallback in target.fallbackFeatures where fallback.holdKind == .edge {
            let fallbackTarget = HoldTarget.feature(
                fallback,
                fingerCapacity: target.fingerCapacity
            )
            let closestFallback = closestMatch(for: fallbackTarget, among: holds)
            if !closestFallback.isEmpty {
                return selectHoldIDs(closestFallback, for: handUse, side: side, on: board)
            }
        }
        return []
    }

    static func substituteHolds(
        for target: HoldTarget,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [BoardHold] {
        let ids = Set(substituteHoldIDs(for: target, on: board, gripType: gripType))
        return board.holds.filter { ids.contains($0.id) }
    }

    static func substituteHolds(
        for target: HoldTarget,
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [BoardHold] {
        let ids = Set(substituteHoldIDs(
            for: target,
            handUse: handUse,
            side: side,
            on: board,
            gripType: gripType
        ))
        return board.holds.filter { ids.contains($0.id) }
    }

    private static func selectHoldIDs(
        _ candidateIDs: [String],
        for handUse: WorkoutHandUse,
        side: WorkoutSide,
        on board: TrainingBoard
    ) -> [String] {
        let candidates = candidateIDs.compactMap { id in
            board.holds.first { $0.id == id }
        }
        switch handUse {
        case .single:
            guard side != .both else { return [] }
            let objectIDs = candidates.reduce(into: [String]()) { result, hold in
                if !result.contains(hold.equipmentObjectID) {
                    result.append(hold.equipmentObjectID)
                }
            }
            guard !objectIDs.isEmpty else { return [] }
            let rankedObjectIDs = objectIDs.sorted { lhs, rhs in
                let lhsCenter = horizontalCenter(of: lhs, among: candidates)
                let rhsCenter = horizontalCenter(of: rhs, among: candidates)
                if lhsCenter != rhsCenter { return lhsCenter < rhsCenter }
                return lhs < rhs
            }
            let objectID = side == .left ? rankedObjectIDs.first! : rankedObjectIDs.last!
            return candidates.filter { $0.equipmentObjectID == objectID }.map(\.id)
        case .double:
            guard side == .both else { return [] }
            var selectedObjectIDs: [String] = []
            for hold in candidates where !selectedObjectIDs.contains(hold.equipmentObjectID) {
                selectedObjectIDs.append(hold.equipmentObjectID)
                if selectedObjectIDs.count == 2 { break }
            }
            if selectedObjectIDs.count == 2 {
                return candidates.filter { selectedObjectIDs.contains($0.equipmentObjectID) }.map(\.id)
            }
            if let bilateralHold = candidates.first(where: { $0.handCapacity == 2 }) {
                return [bilateralHold.id]
            }
            // Older package metadata has no hand-capacity declaration. Keep
            // its established selection behavior, but never construct a
            // bilateral target from a hold explicitly documented for one hand.
            guard !candidates.contains(where: { $0.handCapacity == 1 }) else { return [] }
            return candidates.map(\.id)
        }
    }

    private static func horizontalCenter(
        of equipmentObjectID: String,
        among holds: [BoardHold]
    ) -> Double {
        let centers = holds
            .filter { $0.equipmentObjectID == equipmentObjectID }
            .map { $0.frame.x + $0.frame.width / 2 }
        guard !centers.isEmpty else { return 0.5 }
        return centers.reduce(0, +) / Double(centers.count)
    }

    private static func compatibleHolds(on board: TrainingBoard, gripType: GripType?) -> [BoardHold] {
        guard gripType == .halfCrimp || gripType == .fullCrimp else { return board.holds }
        return board.holds.filter {
            $0.kind == .edge
                && $0.gripType != .openHand
                && $0.features?.contains(.largeOpenHandRail) != true
        }
    }

    /// A target's feature must match exactly; its finger count (when
    /// specified) must too, since `.pocket` alone no longer implies a count.
    private static func matching(_ feature: HoldFeature, fingerCapacity: Int?, among holds: [BoardHold]) -> [BoardHold] {
        holds.filter { hold in
            guard hold.features?.contains(feature) == true else { return false }
            guard let fingerCapacity else { return true }
            return hold.fingerCapacity == fingerCapacity
        }
    }

    private static func closestMatch(for target: HoldTarget, among holds: [BoardHold]) -> [String] {
        if let feature = target.feature {
            let primary = byFeatureGroup(feature, target: target, among: holds)
            if !primary.isEmpty { return primary }
            // resolveHoldIDs already tried each fallback as an exact tagged
            // match; a board missing that tagging (or the primary feature's
            // kind entirely, e.g. no pockets) still deserves a same-kind
            // substitution for its declared fallbacks before giving up. This
            // intentionally skips byFeatureGroup's own further rescues (edge
            // boards standing in for pockets): a plan author who named one
            // specific fallback feature didn't ask for that fallback's
            // fallbacks too.
            for fallback in target.fallbackFeatures {
                let matches = sameKindOrGroup(fallback, target: target, among: holds)
                if !matches.isEmpty { return matches }
            }
            return []
        }
        guard let kind = target.kind else { return [] }
        let sameKindCandidates = holds.filter { $0.kind == kind }
        let sameKind = preferringFingerCapacity(sameKindCandidates, target: target)
        if !sameKind.isEmpty {
            // A capacity-qualified pocket must not silently become a
            // differently sized pocket when its plan declares an
            // availability fallback. Exact-capacity pockets remain first;
            // otherwise let the plan's stated fallback order decide before
            // considering a mismatched pocket.
            if kind == .pocket,
               target.fingerCapacity != nil,
               !target.fallbackFeatures.isEmpty,
               !sameKindCandidates.contains(where: { $0.fingerCapacity == target.fingerCapacity }) {
                for fallback in target.fallbackFeatures {
                    let matches = sameKindOrGroup(fallback, target: target, among: holds)
                    if !matches.isEmpty { return matches }
                }
            }
            if kind == .pocket {
                if target.fingerCapacity != nil {
                    return oneHoldPerHand(from: sameKind).map(\.id)
                }
                return genericPocketSelection(from: sameKind).map(\.id)
            }
            return sameKind.map(\.id)
        }
        for fallback in target.fallbackFeatures {
            let matches = sameKindOrGroup(fallback, target: target, among: holds)
            if !matches.isEmpty { return matches }
        }
        if kind == .pocket, target.fingerCapacity != nil {
            return crossKindEdges(for: target, among: holds).map(\.id)
        }
        guard kind == .edge else { return [] }
        return crossKindPockets(for: target, among: holds).map(\.id)
    }

    private static func byFeatureGroup(_ feature: HoldFeature, target: HoldTarget, among holds: [BoardHold]) -> [String] {
        let direct = sameKindOrGroup(feature, target: target, among: holds)
        if !direct.isEmpty { return direct }

        if feature.holdKind == .edge {
            let pockets = crossKindPockets(for: target, among: holds)
            if !pockets.isEmpty { return pockets.map(\.id) }
        }

        if let capacity = target.fingerCapacity {
            let crossKind = holds.filter { $0.fingerCapacity == capacity }
            if !crossKind.isEmpty { return crossKind.map(\.id) }
        }

        return []
    }

    /// A feature's own group tag, then its physical kind regardless of
    /// tagging. Deliberately stops short of `byFeatureGroup`'s further
    /// cross-kind rescues, which exist for a target's own declared feature,
    /// not for stepping through a declared fallback's fallbacks.
    private static func sameKindOrGroup(_ feature: HoldFeature, target: HoldTarget, among holds: [BoardHold]) -> [String] {
        let group = feature.featureGroup
        let groupFeatures = Set(HoldFeature.allCases.filter { $0.featureGroup == group })

        let sameGroup = holds.filter { hold in
            guard hold.kind == feature.holdKind,
                  let features = hold.features else { return false }
            return !features.isDisjoint(with: groupFeatures)
        }
        let preferredSameGroup = preferringFingerCapacity(sameGroup, target: target)
        let selectedSameGroup = selectingGenericPocketPair(
            from: preferredSameGroup,
            feature: feature,
            fingerCapacity: target.fingerCapacity
        )
        if !selectedSameGroup.isEmpty { return selectedSameGroup.map(\.id) }

        let sameKind = holds.filter { $0.kind == feature.holdKind }
        let preferredSameKind = preferringFingerCapacity(sameKind, target: target)
        if feature.holdKind == .pocket, target.fingerCapacity == nil {
            return genericPocketSelection(from: preferredSameKind).map(\.id)
        }
        // Untagged holds are only a physical-kind fallback, so they cannot
        // identify every same-kind hold as the source-prescribed target. When
        // the plan feature has a source-backed depth adaptation, prefer the
        // nearest documented measurement before falling back to board order.
        let rankedRepresentative = preferredSameKind
            .min { depthDistance(of: $0, from: feature) < depthDistance(of: $1, from: feature) }
        guard let representative = rankedRepresentative else { return [] }

        if feature.holdKind == .pocket {
            let pairedPockets = oneHoldPerHand(from: preferredSameKind)
            if pairedPockets.count == 2 { return pairedPockets.map(\.id) }
        }

        if feature.holdKind == .edge {
            if let pairedEdges = matchingEdgePair(from: preferredSameKind, feature: feature) {
                return pairedEdges.map(\.id)
            }
        }

        return [representative.id]
    }

    /// When the target specifies a finger count, prefer candidates that
    /// match it; if none do, fall back to the unfiltered set rather than
    /// losing the substitution entirely over a capacity mismatch.
    private static func preferringFingerCapacity(_ holds: [BoardHold], target: HoldTarget) -> [BoardHold] {
        guard let capacity = target.fingerCapacity else { return holds }
        let matching = holds.filter { $0.fingerCapacity == capacity }
        return matching.isEmpty ? holds : matching
    }

    /// These are semantic-plan adaptations documented in
    /// `docs/source-audits/2026-08-10-plan-cue-provenance.md`, not inferred
    /// board metadata. Features without a documented measurement stay order
    /// based so unknown source facts are never fabricated.
    private static func targetDepthMillimeters(for feature: HoldFeature) -> Int? {
        switch feature {
        case .largeEdge: 29
        case .mediumEdge: 20
        case .smallEdge: 12
        default: nil
        }
    }

    private static func depthDistance(of hold: BoardHold, from feature: HoldFeature) -> Double {
        guard let sourceTargetDepth = targetDepthMillimeters(for: feature) else { return .infinity }
        let targetDepth = Double(sourceTargetDepth)
        if let range = hold.depthRangeMillimeters {
            if range.contains(targetDepth) { return 0 }
            return min(abs(range.lowerBound - targetDepth), abs(range.upperBound - targetDepth))
        }
        if let size = hold.sizeMillimeters {
            return abs(size - targetDepth)
        }
        return .infinity
    }

    /// Generic edge cues may use a bilateral pair only when the two holds
    /// share their documented physical descriptor and compatible geometry.
    /// Rank viable pairs by the source-backed depth adaptation before visual
    /// symmetry so a farther pair cannot win merely through board order.
    private static func matchingEdgePair(
        from holds: [BoardHold],
        feature: HoldFeature
    ) -> [BoardHold]? {
        let left = holds.filter { $0.frame.x + $0.frame.width <= 0.5 }
        let right = holds.filter { $0.frame.x >= 0.5 }
        let pairs = left.flatMap { leftHold in
            right.compactMap { rightHold -> (BoardHold, BoardHold)? in
                let pair = (leftHold, rightHold)
                guard hasMatchingEdgeDescriptor(pair), isMatchingPocketPair(pair) else {
                    return nil
                }
                return pair
            }
        }
        guard let pair = pairs.min(by: {
            let leftDistance = depthDistance(of: $0.0, from: feature)
            let rightDistance = depthDistance(of: $1.0, from: feature)
            if leftDistance != rightDistance { return leftDistance < rightDistance }
            return symmetryScore(of: $0) < symmetryScore(of: $1)
        }) else {
            return nil
        }
        return [pair.0, pair.1]
    }

    private static func hasMatchingEdgeDescriptor(_ pair: (BoardHold, BoardHold)) -> Bool {
        let leftHasMeasurement = pair.0.sizeMillimeters != nil || pair.0.depthRangeMillimeters != nil
        let rightHasMeasurement = pair.1.sizeMillimeters != nil || pair.1.depthRangeMillimeters != nil
        guard pair.0.gripType == pair.1.gripType,
              pair.0.fingerCapacity == pair.1.fingerCapacity,
              pair.0.handCapacity == pair.1.handCapacity else {
            return false
        }
        if !leftHasMeasurement && !rightHasMeasurement {
            return true
        }
        guard leftHasMeasurement && rightHasMeasurement else { return false }
        return pair.0.sizeMillimeters == pair.1.sizeMillimeters
            && pair.0.depthRangeMillimeters == pair.1.depthRangeMillimeters
    }

    private static func crossKindPockets(for target: HoldTarget, among holds: [BoardHold]) -> [BoardHold] {
        let pockets = holds.filter { $0.kind == .pocket }
        guard let capacity = target.fingerCapacity else {
            return oneHoldPerHand(from: pockets)
        }
        return pockets.filter { $0.fingerCapacity == capacity }
    }

    /// A capacity-qualified pocket request may use same-capacity edges only
    /// when the board has no pocket candidate. An unqualified pocket request
    /// must not broaden into an arbitrary edge selection.
    private static func crossKindEdges(for target: HoldTarget, among holds: [BoardHold]) -> [BoardHold] {
        guard let capacity = target.fingerCapacity else { return [] }
        return holds.filter { $0.kind == .edge && $0.fingerCapacity == capacity }
    }

    private static func selectingGenericPocketPair(
        from holds: [BoardHold],
        feature: HoldFeature,
        fingerCapacity: Int?
    ) -> [BoardHold] {
        guard feature.holdKind == .pocket, fingerCapacity == nil else { return holds }
        return genericPocketSelection(from: holds)
    }

    /// Generic pocket cues prefer a geometry-backed bilateral pair. A lone
    /// pocket remains usable only when its frame is wholly on one board side;
    /// a centered or midline-crossing contact is not a hand-specific fallback.
    private static func genericPocketSelection(from holds: [BoardHold]) -> [BoardHold] {
        if let pair = matchingPocketPair(from: holds) { return pair }
        return holds.first(where: isWhollyOnOneSide).map { [$0] } ?? []
    }

    private static func isWhollyOnOneSide(_ hold: BoardHold) -> Bool {
        hold.frame.x + hold.frame.width <= 0.5 || hold.frame.x >= 0.5
    }

    /// Generic pocket cues need a usable two-handed pair. Choose known,
    /// matching-capacity pockets with compatible rows and frames. Horizontal
    /// reflection ranks those matches, but asymmetric board layouts remain
    /// eligible.
    private static func matchingPocketPair(from holds: [BoardHold]) -> [BoardHold]? {
        let left = holds.filter { $0.frame.x + $0.frame.width <= 0.5 }
        let right = holds.filter { $0.frame.x >= 0.5 }
        let pairs = left.flatMap { leftHold in
            right.compactMap { rightHold -> (BoardHold, BoardHold)? in
                guard let capacity = leftHold.fingerCapacity,
                      rightHold.fingerCapacity == capacity else { return nil }
                let pair = (leftHold, rightHold)
                return isMatchingPocketPair(pair) ? pair : nil
            }
        }
        guard let pair = pairs.min(by: { symmetryScore(of: $0) < symmetryScore(of: $1) }) else {
            return nil
        }
        return [pair.0, pair.1]
    }

    private static func isMatchingPocketPair(_ pair: (BoardHold, BoardHold)) -> Bool {
        let differences = symmetryDifferences(of: pair)
        let referenceWidth = max(pair.0.frame.width, pair.1.frame.width)
        let referenceHeight = max(pair.0.frame.height, pair.1.frame.height)
        guard referenceWidth > 0, referenceHeight > 0 else { return false }
        let tolerance = 0.25
        return differences.verticalAlignment <= referenceHeight * tolerance
            && differences.width <= referenceWidth * tolerance
            && differences.height <= referenceHeight * tolerance
    }

    private static func symmetryScore(of pair: (BoardHold, BoardHold)) -> Double {
        let differences = symmetryDifferences(of: pair)
        let referenceWidth = max(pair.0.frame.width, pair.1.frame.width)
        let referenceHeight = max(pair.0.frame.height, pair.1.frame.height)
        return differences.horizontalReflection / referenceWidth
            + differences.verticalAlignment / referenceHeight
            + differences.width / referenceWidth
            + differences.height / referenceHeight
    }

    private static func symmetryDifferences(of pair: (BoardHold, BoardHold)) -> (
        verticalAlignment: Double,
        horizontalReflection: Double,
        width: Double,
        height: Double
    ) {
        let leftCenter = pair.0.frame.x + pair.0.frame.width / 2
        let rightCenter = pair.1.frame.x + pair.1.frame.width / 2
        let leftVerticalCenter = pair.0.frame.y + pair.0.frame.height / 2
        let rightVerticalCenter = pair.1.frame.y + pair.1.frame.height / 2
        return (
            abs(leftVerticalCenter - rightVerticalCenter),
            abs(leftCenter - (1 - rightCenter)),
            abs(pair.0.frame.width - pair.1.frame.width),
            abs(pair.0.frame.height - pair.1.frame.height)
        )
    }

    /// A bilateral target represents a two-handed hang, so highlight one
    /// eligible hold on each half of the board rather than every candidate.
    private static func oneHoldPerHand(from holds: [BoardHold]) -> [BoardHold] {
        let left = holds.first { $0.frame.x + $0.frame.width / 2 < 0.5 }
        let right = holds.first { $0.frame.x + $0.frame.width / 2 >= 0.5 }
        return [left, right].compactMap { $0 }
    }
}

struct WorkoutActivityRecorder {
    func segments(
        for plan: TrainingPlan,
        on board: TrainingBoard,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:]
    ) throws -> [RecordedActivitySegment] {
        var result: [RecordedActivitySegment] = []
        for step in plan.steps {
            for (index, segment) in step.segments.enumerated() {
                let key = WorkoutActivitySegmentKey(stepID: step.id, segmentIndex: index)
                let duration: TimeInterval?
                switch segment.kind {
                case .rest:
                    duration = segment.duration
                case .work:
                    switch segment.timing {
                    case .fixed: duration = segment.duration
                    case .undefined: duration = nil
                    case .stopwatch:
                        if let observed = stopwatchDurations[key] {
                            guard observed.isFinite, observed >= 0 else { throw WorkoutActivityRecordingError.invalidObservedDuration(key) }
                            duration = observed
                        } else { duration = nil }
                    }
                }
                if segment.kind == .rest {
                    result.append(RecordedActivitySegment(stepID: step.id, stepNumber: step.number, kind: .rest, holdIDs: [], holdType: nil, sizeMillimeters: nil, durationSeconds: duration))
                    continue
                }
                guard !segment.targets.isEmpty else {
                    guard allowsUntargetedRPTCSelfSelectedWork(
                        segment,
                        in: step,
                        plan: plan
                    ) else {
                        throw WorkoutActivityRecordingError.unresolvedTarget(
                            stepID: step.id,
                            segmentIndex: index
                        )
                    }
                    result.append(
                        RecordedActivitySegment(
                            stepID: step.id,
                            stepNumber: step.number,
                            kind: .work,
                            holdIDs: [],
                            holdType: nil,
                            sizeMillimeters: nil,
                            durationSeconds: duration
                        )
                    )
                    continue
                }
                let holdsByTarget = segment.targets.map {
                    BoardTargetResolver.substituteHolds(
                        for: $0,
                        handUse: step.handUse,
                        side: step.side,
                        on: board,
                        gripType: step.gripType
                    )
                }
                guard holdsByTarget.allSatisfy({ !$0.isEmpty }) else { throw WorkoutActivityRecordingError.unresolvedTarget(stepID: step.id, segmentIndex: index) }
                let holds = holdsByTarget.flatMap { $0 }
                guard !holds.isEmpty else { throw WorkoutActivityRecordingError.unresolvedTarget(stepID: step.id, segmentIndex: index) }
                if segment.targets.count > 1 {
                    result.append(
                        RecordedActivitySegment(
                            stepID: step.id,
                            stepNumber: step.number,
                            kind: .work,
                            holdIDs: holds.map(\.id),
                            holdType: nil,
                            sizeMillimeters: nil,
                            durationSeconds: duration
                        )
                    )
                    continue
                }
                var groups: [(HoldKind, Double?, [String])] = []
                for hold in holds {
                    let descriptor = (hold.kind, hold.sizeMillimeters)
                    if let i = groups.firstIndex(where: { $0.0 == descriptor.0 && $0.1 == descriptor.1 }) { groups[i].2.append(hold.id) }
                    else { groups.append((hold.kind, hold.sizeMillimeters, [hold.id])) }
                }
                result += groups.map { kind, size, ids in
                    RecordedActivitySegment(
                        stepID: step.id,
                        stepNumber: step.number,
                        kind: .work,
                        holdIDs: ids,
                        holdType: kind.rawValue,
                        sizeMillimeters: size,
                        durationSeconds: duration
                    )
                }
            }
        }
        return result
    }

    private func allowsUntargetedRPTCSelfSelectedWork(
        _ segment: WorkoutSegment,
        in step: WorkoutStep,
        plan: TrainingPlan
    ) -> Bool {
        let expectedStepIDs = Set((1...7).map { "rptc-repeaters-set-rep-\($0).segment-1" })
        return plan.id == LegacyPlanSeedCatalog.rptcRepeaters.id &&
            plan.provenance == .official &&
            plan.sourceURL == LegacyPlanSeedCatalog.rptcRepeaters.sourceURL &&
            plan.boardID == nil &&
            plan.steps.count == 15 &&
            expectedStepIDs.contains(step.id) &&
            step.phase == .hang &&
            step.targets.isEmpty &&
            step.duration == 7 &&
            step.timedWorkDuration == 7 &&
            step.segments == [segment] &&
            segment.kind == .work &&
            segment.targets.isEmpty &&
            segment.timing == .fixed &&
            segment.duration == 7
    }

    func metadata(
        for plan: TrainingPlan,
        on board: TrainingBoard,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:],
        stepMeasurements: [WorkoutStepMeasurement] = []
    ) throws -> WorkoutActivityMetadata {
        WorkoutActivityMetadata(
            segments: try segments(
                for: plan,
                on: board,
                stopwatchDurations: stopwatchDurations
            ),
            measurements: measuredSteps(from: stepMeasurements)
        )
    }

    private func measuredSteps(
        from measurements: [WorkoutStepMeasurement]
    ) -> [RecordedActivityStepMeasurement]? {
        let result = measurements.compactMap { measurement -> RecordedActivityStepMeasurement? in
            guard measurement.sampleCount > 0 else { return nil }
            let peakLoadKGF = measurement.peakLoadKGF.flatMap {
                $0.isFinite && $0 >= 0 ? $0 : nil
            }
            let loadedDuration = measurement.actualLoadedDuration
            let actualLoadedDurationSeconds = loadedDuration.isFinite && loadedDuration >= 0
                ? loadedDuration
                : nil
            guard peakLoadKGF != nil || actualLoadedDurationSeconds != nil else { return nil }
            return RecordedActivityStepMeasurement(
                stepID: measurement.stepID,
                peakLoadKGF: peakLoadKGF,
                actualLoadedDurationSeconds: actualLoadedDurationSeconds
            )
        }
        return result.isEmpty ? nil : result
    }

    func json(for metadata: WorkoutActivityMetadata) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(metadata)
        return String(decoding: data, as: UTF8.self)
    }
}
