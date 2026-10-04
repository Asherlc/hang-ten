import SwiftUI
import UIKit

struct BoardDetailHoldMap {
    struct Entry: Identifiable, Hashable {
        let number: Int
        let hold: PhysicalContact
        let frame: HoldFrame
        let pieces: [BoardContactPiece]

        var id: String { hold.id }
    }

    let presentation: BoardPresentation
    let entries: [Entry]

    init(board: BoardRevision, presentationID: String?) {
        let content = BoardMapPresentationContent(
            board: board,
            selectedPresentationID: presentationID
        )
        presentation = content.presentation
        entries = content.holds.enumerated().compactMap { index, hold in
            guard let frame = hold.resolvedFrame(in: content.presentation) else { return nil }
            return Entry(
                number: index + 1,
                hold: hold,
                frame: frame,
                pieces: content.pieces(for: hold.id)
            )
        }
    }
}

struct BoardHoldSpecification: Equatable, Identifiable {
    let label: String
    let value: String

    var id: String { label }
}

enum BoardDetailContentOrder: Hashable {
    case map
    case selectedHold
    case holdLegend

    static func sections(hasSelectedHold: Bool) -> [Self] {
        hasSelectedHold ? [.map, .selectedHold, .holdLegend] : [.map, .holdLegend]
    }
}

enum BoardHoldSpecifications {
    static func entries(for hold: PhysicalContact) -> [BoardHoldSpecification] {
        var entries = [BoardHoldSpecification(label: "Kind", value: hold.kind.detailLabel)]

        if let depth = hold.depth {
            switch depth {
            case let .category(size):
                entries.append(.init(label: "Depth", value: size.label))
            case let .range(range):
                if range.minimum == range.maximum {
                    entries.append(.init(label: "Depth", value: millimeters(range.minimum)))
                } else {
                    entries.append(
                        .init(
                            label: "Depth range",
                            value: "\(millimeters(range.minimum))–\(millimeters(range.maximum))"
                        )
                    )
                }
            }
        }
        if !hold.gripTypes.isEmpty {
            let labels = hold.gripTypes.sorted { $0.rawValue < $1.rawValue }.map(\.label)
            entries.append(.init(label: "Grip", value: labels.joined(separator: ", ")))
        }
        if let fingerCapacity = hold.fingerCapacity {
            entries.append(.init(label: "Finger capacity", value: "\(fingerCapacity)"))
        }
        if let handCapacity = hold.handCapacity {
            entries.append(.init(label: "Hand capacity", value: "\(handCapacity)"))
        }
        return entries
    }

    private static func millimeters(_ measurement: Double) -> String {
        let formatted = measurement.rounded() == measurement
            ? String(format: "%.0f", measurement)
            : String(format: "%.1f", measurement)
        return "\(formatted) mm"
    }
}

struct BoardMapPresentationContent {
    let presentation: BoardPresentation
    let holds: [PhysicalContact]

    init(
        board: BoardRevision,
        selectedPresentationID: String?
    ) {
        let resolvedPresentation = board.presentation(id: selectedPresentationID)
            ?? board.defaultPresentation
        presentation = resolvedPresentation
        holds = board.contacts(in: resolvedPresentation)
    }

    func pieces(for holdID: String) -> [BoardContactPiece] {
        guard case .raster(let media) = presentation.media else { return [] }
        return media.contactGeometry[holdID] ?? []
    }
}

extension BoardPresentation {
    @MainActor
    func aspectRatio(for positionID: String?) -> CGFloat {
        guard case .model(let media) = media,
              let orientation = media.orientation,
              let positionID,
              let framing = BoardModelRealityScene.framing(
                  bounds: media.descriptor.modelBounds,
                  display: media.display,
                  orientation: orientation,
                  positionID: positionID
              ) else {
            return aspectRatio
        }
        return CGFloat(framing.width) / CGFloat(framing.height)
    }
}

struct BoardMapPresentationSelection: Equatable {
    private(set) var presentationID: String

    static func resolvePositionID(
        board: BoardRevision,
        presentationID: String?,
        activeHoldID: String?,
        highlightedHoldIDs: Set<String> = [],
        preferredPositionID: String? = nil
    ) -> String? {
        let resolvedPresentationID = presentationID ?? board.defaultPresentation.id
        // A user-selected pose survives selection changes only while it can
        // represent the current presentation and all requested contacts.
        if let preferred = board.position(id: preferredPositionID),
           preferred.presentationID == resolvedPresentationID {
            let requiredIDs = activeHoldID.map { Set([$0]) } ?? highlightedHoldIDs
            if requiredIDs.isSubset(of: Set(board.contactIDs(inPosition: preferred.id))) {
                return preferred.id
            }
        }
        if let activeHoldID,
           let activePosition = board.position(
               presentationID: resolvedPresentationID,
               containingContactID: activeHoldID
           ) {
            return activePosition.id
        }
        if activeHoldID == nil,
           let highlightedPosition = board.contacts.lazy
               .filter({ highlightedHoldIDs.contains($0.id) })
               .compactMap({
                   board.position(
                       presentationID: resolvedPresentationID,
                       containingContactID: $0.id
                   )
               })
               .first {
            return highlightedPosition.id
        }
        guard activeHoldID == nil else { return nil }
        return board.position(presentationID: resolvedPresentationID)?.id
    }

    init(
        board: BoardRevision,
        requestedPresentationID: String?,
        activeHoldID: String?,
        highlightedHoldIDs: Set<String>
    ) {
        let initialPresentationID = board.presentation(id: requestedPresentationID)?.id
            ?? board.defaultPresentation.id
        if let activePresentationID = Self.presentationID(
            for: activeHoldID,
            preferring: initialPresentationID,
            on: board
        ) {
            presentationID = activePresentationID
        } else if let highlightedHoldID = board.contacts.first(where: {
            highlightedHoldIDs.contains($0.id)
        })?.id,
           let highlightedPresentationID = Self.presentationID(
               for: highlightedHoldID,
               preferring: initialPresentationID,
               on: board
           ) {
            presentationID = highlightedPresentationID
        } else {
            presentationID = initialPresentationID
        }
    }

    mutating func selectPresentation(id: String, on board: BoardRevision) {
        guard let presentation = board.presentation(id: id) else { return }
        presentationID = presentation.id
    }

    mutating func updateHighlights(
        from previousHoldIDs: Set<String>,
        to highlightedHoldIDs: Set<String>,
        activeHoldID: String?,
        on board: BoardRevision
    ) {
        if let activePresentationID = Self.presentationID(
            for: activeHoldID,
            preferring: presentationID,
            on: board
        ) {
            presentationID = activePresentationID
            return
        }
        let addedHoldIDs = highlightedHoldIDs.subtracting(previousHoldIDs)
        if let addedHold = board.contacts.first(where: { addedHoldIDs.contains($0.id) }) {
            presentationID = Self.presentationID(
                for: addedHold.id,
                preferring: presentationID,
                on: board
            ) ?? presentationID
        }
    }

    mutating func activateHold(id: String?, on board: BoardRevision) {
        guard let activePresentationID = Self.presentationID(
            for: id,
            preferring: presentationID,
            on: board
        ) else {
            return
        }
        presentationID = activePresentationID
    }

    mutating func updateRequestedPresentation(
        id: String?,
        activeHoldID: String?,
        highlightedHoldIDs: Set<String>,
        on board: BoardRevision
    ) {
        if let requestedPresentation = board.presentation(id: id) {
            presentationID = requestedPresentation.id
            return
        }
        reset(
            board: board,
            requestedPresentationID: nil,
            activeHoldID: activeHoldID,
            highlightedHoldIDs: highlightedHoldIDs
        )
    }

    mutating func reset(
        board: BoardRevision,
        requestedPresentationID: String?,
        activeHoldID: String?,
        highlightedHoldIDs: Set<String>
    ) {
        self = Self(
            board: board,
            requestedPresentationID: requestedPresentationID,
            activeHoldID: activeHoldID,
            highlightedHoldIDs: highlightedHoldIDs
        )
    }

    private static func presentationID(
        for holdID: String?,
        preferring preferredPresentationID: String,
        on board: BoardRevision
    ) -> String? {
        guard let holdID else { return nil }
        guard board.contacts.contains(where: { $0.id == holdID }) else {
            return nil
        }
        guard let preferredPresentation = board.presentation(id: preferredPresentationID) else {
            return board.presentations.first(where: { $0.containsContact(id: holdID) })?.id
        }
        if preferredPresentation.containsContact(id: holdID) { return preferredPresentation.id }
        return board.presentations.first(where: { $0.containsContact(id: holdID) })?.id
    }
}

enum BoardMapRotationOptions {
    static func positions(on board: BoardRevision, presentationID: String) -> [BoardPosition] {
        guard let presentation = board.presentation(id: presentationID),
              case .model(let media) = presentation.media,
              let instances = media.instances, instances.count > 1,
              instances.allSatisfy({ $0.suspension == nil }) else { return [] }
        let positions = board.positions.filter { $0.presentationID == presentationID }
        guard positions.count > 1, let first = positions.first else { return [] }
        let contacts = Set(board.contactIDs(inPosition: first.id))
        guard !contacts.isEmpty,
              positions.allSatisfy({ position in
                  Set(board.contactIDs(inPosition: position.id)) == contacts
                      && instances.allSatisfy { $0.positionTransforms?[position.id] != nil }
              }) else { return [] }
        return positions
    }
}

private struct BoardRotationSelector: View {
    let board: BoardRevision
    let presentationID: String
    @Binding var positionID: String?
    let accessibilityID: String

    var body: some View {
        let positions = BoardMapRotationOptions.positions(on: board, presentationID: presentationID)
        if !positions.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text("Rotation")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Picker("Rotation", selection: $positionID) {
                    ForEach(Array(positions.enumerated()), id: \.element.id) { index, position in
                        let number = position.id.hasPrefix("p") ? Int(position.id.dropFirst()) : nil
                        Text("Position \(number ?? index + 1)")
                            .tag(Optional(position.id))
                    }
                }
                .pickerStyle(.segmented)
                .accessibilityLabel("Board rotation")
                .accessibilityIdentifier(accessibilityID)
            }
        }
    }
}

struct BoardDetailMapView: View {
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    let board: BoardRevision
    @Binding var selectedHoldID: String?
    private let maximumMapHeight: CGFloat?
    private let selectedHoldContent: AnyView?

    @State private var presentationSelection: BoardMapPresentationSelection
    @State private var preferredPositionIDs: [String: String] = [:]

    init(
        board: BoardRevision,
        selectedHoldID: Binding<String?>,
        maximumMapHeight: CGFloat? = nil,
        selectedHoldContent: AnyView? = nil
    ) {
        self.board = board
        _selectedHoldID = selectedHoldID
        self.maximumMapHeight = maximumMapHeight
        self.selectedHoldContent = selectedHoldContent
        let initialPresentation = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: nil,
            activeHoldID: selectedHoldID.wrappedValue,
            highlightedHoldIDs: []
        )
        _presentationSelection = State(initialValue: initialPresentation)
    }

    var body: some View {
        let map = BoardDetailHoldMap(
            board: board,
            presentationID: presentationSelection.presentationID
        )
        let contentOrder = BoardDetailContentOrder.sections(
            hasSelectedHold: selectedHoldContent != nil
        )
        VStack(alignment: .leading, spacing: 12) {
            ForEach(contentOrder, id: \.self) { section in
                switch section {
                case .map:
                    mapContent(map)
                case .selectedHold:
                    selectedHoldContent
                case .holdLegend:
                    holdLegend(map)
                }
            }
        }
        .animation(.easeInOut(duration: 0.18), value: selectedHoldID)
        .onChange(of: board.id) { _, _ in preferredPositionIDs.removeAll() }
    }

    @ViewBuilder
    private func mapContent(_ map: BoardDetailHoldMap) -> some View {
        // Explicit VStack keeps the segmented picker above the sized map with
        // zero intra-section spacing (outer BoardDetailMapView spacing is 12).
        VStack(alignment: .leading, spacing: 0) {
            if board.presentations.count > 1 {
                Picker(
                    "Board surface",
                    selection: Binding(
                        get: { map.presentation.id },
                        set: selectPresentation
                    )
                ) {
                    ForEach(board.presentations) { presentation in
                        Text(presentation.name).tag(presentation.id)
                    }
                }
                .pickerStyle(.segmented)
                .accessibilityIdentifier("boardDetail.presentationSelector")
            }

            BoardRotationSelector(
                board: board,
                presentationID: map.presentation.id,
                positionID: Binding(
                    get: { BoardMapPresentationSelection.resolvePositionID(
                        board: board, presentationID: map.presentation.id, activeHoldID: selectedHoldID,
                        preferredPositionID: preferredPositionIDs[map.presentation.id]
                    ) },
                    set: { preferredPositionIDs[map.presentation.id] = $0 }
                ),
                accessibilityID: "boardDetail.rotationSelector"
            )
            .padding(.bottom, BoardMapRotationOptions.positions(on: board, presentationID: map.presentation.id).isEmpty ? 0 : 8)

            Group {
                switch map.presentation.media {
                case .raster:
                    GeometryReader { proxy in
                        let boardBounds = proxy.size
                        ZStack {
                            BoardPresentationImage(board: board, presentationID: map.presentation.id)

                            ForEach(map.entries) { entry in
                                PhysicalHoldVisual(
                                    hold: entry.hold,
                                    pieces: entry.pieces,
                                    isHighlighted: selectedHoldID == entry.hold.id,
                                    highlightMode: .active,
                                    isInverted: map.presentation.isInverted,
                                    onTap: { select($0.id) }
                                )
                                .frame(width: boardBounds.width, height: boardBounds.height)

                                BoardHoldNumberMarker(
                                    entry: entry,
                                    isSelected: selectedHoldID == entry.hold.id
                                ) {
                                    select(entry.hold.id)
                                }
                                .position(markerPosition(for: entry.frame, in: boardBounds, isInverted: map.presentation.isInverted))
                            }
                        }
                    }
                case .model:
                    BoardModelSurface(
                        board: board,
                        presentation: map.presentation,
                        positionID: BoardMapPresentationSelection.resolvePositionID(
                            board: board, presentationID: map.presentation.id, activeHoldID: selectedHoldID,
                            preferredPositionID: preferredPositionIDs[map.presentation.id]
                        ),
                        highlightedContactIDs: Set([selectedHoldID].compactMap { $0 }),
                        highlightMode: .active,
                        onContactTap: { select($0.id) }
                    )
                }
            }
            .modifier(
                BoardDetailMapSizeModifier(
                    aspectRatio: map.presentation.aspectRatio,
                    maximumHeight: maximumMapHeight
                )
            )
        }
    }

    @ViewBuilder
    private func holdLegend(_ map: BoardDetailHoldMap) -> some View {
        if !map.entries.isEmpty {
            SectionLabel(title: "Hold map")
            LazyVGrid(
                    columns: dynamicTypeSize.isAccessibilitySize
                        ? [GridItem(.flexible())]
                        : [GridItem(.adaptive(minimum: 132), spacing: 8)],
                    alignment: .leading,
                    spacing: 8
            ) {
                ForEach(map.entries) { entry in
                    Button {
                        select(entry.hold.id)
                    } label: {
                        HStack(spacing: 8) {
                            Text("\(entry.number)")
                                .font(.system(size: 12, weight: .bold, design: .rounded))
                                .foregroundStyle(Color.hangCream)
                                .frame(width: 24, height: 24)
                                .background(
                                    selectedHoldID == entry.hold.id
                                        ? Color.holdActiveDeep
                                        : Color.hangGreenDark,
                                    in: Circle()
                                )
                            Text(entry.hold.name)
                                .font(.system(.footnote, design: .rounded, weight: .semibold))
                                .foregroundStyle(Color.hangInk)
                                .fixedSize(horizontal: false, vertical: true)
                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 7)
                        .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                        .contentShape(Rectangle())
                        .background(
                            selectedHoldID == entry.hold.id
                                ? Color.holdActive.opacity(0.16)
                                : Color.hangBackground,
                            in: RoundedRectangle(cornerRadius: 10, style: .continuous)
                        )
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Hold \(entry.number): \(entry.hold.name)")
                    .accessibilityAddTraits(
                        selectedHoldID == entry.hold.id ? .isSelected : []
                    )
                    .accessibilityIdentifier("boardDetail.holdLegend.\(entry.hold.id)")
                }
            }
        }
    }

    private func selectPresentation(_ id: String) {
        presentationSelection.selectPresentation(id: id, on: board)
        selectedHoldID = BoardDetailHoldMap(board: board, presentationID: id).entries.first?.hold.id
    }

    private func select(_ holdID: String) {
        selectedHoldID = holdID
    }

    private func markerPosition(
        for frame: HoldFrame,
        in bounds: CGSize,
        isInverted: Bool
    ) -> CGPoint {
        let center = CGPoint(
            x: frame.x * bounds.width + frame.width * bounds.width / 2,
            y: frame.y * bounds.height + frame.height * bounds.height / 2
        )
        guard isInverted else { return center }
        return CGPoint(x: bounds.width - center.x, y: bounds.height - center.y)
    }
}

private struct BoardDetailMapSizeModifier: ViewModifier {
    let aspectRatio: CGFloat
    let maximumHeight: CGFloat?
    var accessibilityIdentifier: String? = "boardDetail.map"

    /// Fits the map through one modifier chain so compact-height changes preserve its renderer identity.
    func body(content: Content) -> some View {
        // Preserve the model surface's identity when compact-height metrics
        // become available or rotation changes the optional height limit.
        content
            .aspectRatio(aspectRatio, contentMode: .fit)
            .frame(maxWidth: maximumHeight.map { max(0, $0 * aspectRatio) })
            // Keep the accessibility node on the fitted map, before the outer
            // frame expands to the available width.
            .background {
                if let accessibilityIdentifier {
                    Color.clear
                        .accessibilityElement()
                        .accessibilityIdentifier(accessibilityIdentifier)
                }
            }
            .frame(maxWidth: .infinity)
    }
}

private struct BoardHoldNumberMarker: View {
    let entry: BoardDetailHoldMap.Entry
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text("\(entry.number)")
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangCream)
                .frame(width: 28, height: 28)
                .background(isSelected ? Color.holdActiveDeep : Color.hangGreenDark, in: Circle())
                .overlay {
                    Circle()
                        .stroke(Color.hangCream, lineWidth: 2)
                }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Hold \(entry.number): \(entry.hold.name)")
        .accessibilityAddTraits(isSelected ? .isSelected : [])
        .accessibilityIdentifier("boardDetail.holdMarker.\(entry.hold.id)")
    }
}

struct BoardMapView: View {
    let board: BoardRevision
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((PhysicalContact) -> Void)?
    private let requestedPresentationID: String?
    private let activeHoldID: String?
    private let isDisplayOnly: Bool
    private let maximumMapHeight: CGFloat?

    @State private var presentationSelection: BoardMapPresentationSelection
    @State private var preferredPositionIDs: [String: String] = [:]

    init(
        board: BoardRevision,
        highlightedHoldIDs: Set<String> = [],
        highlightMode: BoardHighlightMode = .active,
        selectedPresentationID: String? = nil,
        activeHoldID: String? = nil,
        onHoldTap: ((PhysicalContact) -> Void)? = nil,
        isDisplayOnly: Bool = false,
        maximumMapHeight: CGFloat? = nil
    ) {
        self.board = board
        self.highlightedHoldIDs = highlightedHoldIDs
        self.highlightMode = highlightMode
        self.onHoldTap = onHoldTap
        requestedPresentationID = selectedPresentationID
        self.activeHoldID = activeHoldID
        self.isDisplayOnly = isDisplayOnly
        self.maximumMapHeight = maximumMapHeight
        let resolvedSelection = BoardMapPresentationSelection(
            board: board,
            requestedPresentationID: selectedPresentationID,
            activeHoldID: activeHoldID,
            highlightedHoldIDs: highlightedHoldIDs
        )
        _presentationSelection = State(initialValue: resolvedSelection)
    }

    var body: some View {
        let content = BoardMapPresentationContent(
            board: board,
            selectedPresentationID: presentationSelection.presentationID
        )
        let selectedPositionID = BoardMapPresentationSelection.resolvePositionID(
            board: board,
            presentationID: content.presentation.id,
            activeHoldID: activeHoldID,
            highlightedHoldIDs: highlightedHoldIDs,
            preferredPositionID: preferredPositionIDs[content.presentation.id]
        )
        let displayedHolds = content.holds
        VStack(spacing: 8) {
            if board.presentations.count > 1 {
                Picker(
                    "Board surface",
                    selection: Binding(
                        get: { content.presentation.id },
                        set: { selectPresentation(id: $0) }
                    )
                ) {
                    ForEach(board.presentations) { presentation in
                        Text(presentation.name).tag(presentation.id)
                    }
                }
                .pickerStyle(.segmented)
                .accessibilityLabel("Board surface")
                .accessibilityIdentifier("boardMap.presentationSelector")
            }

            if !isDisplayOnly {
                BoardRotationSelector(
                    board: board,
                    presentationID: content.presentation.id,
                    positionID: Binding(
                        get: { selectedPositionID },
                        set: { preferredPositionIDs[content.presentation.id] = $0 }
                    ),
                    accessibilityID: "boardMap.rotationSelector"
                )
            }

            Group {
                switch content.presentation.media {
                case .raster:
                    GeometryReader { proxy in
                        let boardBounds = proxy.size
                        ZStack {
                            BoardPresentationImage(
                                board: board,
                                presentationID: content.presentation.id
                            )

                            ForEach(displayedHolds) { hold in
                                PhysicalHoldVisual(
                                    hold: hold,
                                    pieces: content.pieces(for: hold.id),
                                    isHighlighted: highlightedHoldIDs.contains(hold.id),
                                    highlightMode: highlightMode,
                                    isInverted: content.presentation.isInverted,
                                    onTap: onHoldTap
                                )
                                .frame(width: boardBounds.width, height: boardBounds.height)
                            }
                        }
                        .frame(width: boardBounds.width, height: boardBounds.height)
                    }
                case .model:
                    BoardModelSurface(
                        board: board,
                        presentation: content.presentation,
                        positionID: selectedPositionID,
                        highlightedContactIDs: highlightedHoldIDs,
                        highlightMode: highlightMode,
                        onContactTap: onHoldTap,
                        isDisplayOnly: isDisplayOnly
                    )
                }
            }
            .modifier(BoardDetailMapSizeModifier(
                aspectRatio: content.presentation.aspectRatio,
                maximumHeight: maximumMapHeight,
                accessibilityIdentifier: nil
            ))
        }
        .animation(.easeInOut(duration: 0.18), value: highlightedHoldIDs)
        .onChange(of: highlightedHoldIDs) { previousHoldIDs, holdIDs in
            presentationSelection.updateHighlights(
                from: previousHoldIDs,
                to: holdIDs,
                activeHoldID: activeHoldID,
                on: board
            )
        }
        .onChange(of: activeHoldID) { _, holdID in
            presentationSelection.activateHold(id: holdID, on: board)
        }
        .onChange(of: requestedPresentationID) { _, presentationID in
            presentationSelection.updateRequestedPresentation(
                id: presentationID,
                activeHoldID: activeHoldID,
                highlightedHoldIDs: highlightedHoldIDs,
                on: board
            )
        }
        .onChange(of: board.id) { _, _ in
            preferredPositionIDs.removeAll()
            presentationSelection.reset(
                board: board,
                requestedPresentationID: requestedPresentationID,
                activeHoldID: activeHoldID,
                highlightedHoldIDs: highlightedHoldIDs
            )
        }
    }

    private func selectPresentation(id: String) {
        presentationSelection.selectPresentation(id: id, on: board)
    }
}

/// Loads only a package-declared presentation file. A board without one has
/// no image view and never falls back to an asset-catalog name.
struct BoardPresentationImage: View {
    let board: BoardRevision
    let presentationID: String?

    init(board: BoardRevision, presentationID: String? = nil) {
        self.board = board
        self.presentationID = presentationID
    }

    @ViewBuilder
    var body: some View {
        if let url = BoardCatalog.packageStore.presentationImageURL(
            for: board,
            presentationID: presentationID
        ),
           let image = UIImage(contentsOfFile: url.path) {
            Image(uiImage: image)
                .resizable()
        }
    }
}

private struct PhysicalHoldVisual: View {
    let hold: PhysicalContact
    let pieces: [BoardContactPiece]
    let isHighlighted: Bool
    let highlightMode: BoardHighlightMode
    let isInverted: Bool
    let onTap: ((PhysicalContact) -> Void)?

    @ViewBuilder
    var body: some View {
        let shape = BoardContactPathShape(pieces: pieces)
        let visual = ZStack {
            shape
                .fill(isHighlighted ? highlightFill.opacity(0.38) : Color.clear)
            .overlay {
                shape.stroke(
                    isHighlighted ? highlightStroke : Color.clear,
                    lineWidth: 2
                )
            }
        }
        if let onTap {
            visual
                .rotationEffect(isInverted ? .degrees(180) : .zero)
                .contentShape(.interaction, shape)
                .contentShape(.accessibility, shape)
                .onTapGesture {
                    onTap(hold)
                }
                .accessibilityLabel(hold.name)
                .accessibilityElement(children: .combine)
                .accessibilityAddTraits(.isButton)
        } else {
            visual
                .rotationEffect(isInverted ? .degrees(180) : .zero)
        }
    }

    private var highlightFill: Color {
        switch highlightMode {
        case .active: .holdActive
        case .preview: .restBlue
        }
    }

    private var highlightStroke: Color {
        switch highlightMode {
        case .active: .holdActiveDeep
        case .preview: .restBlueDeep
        }
    }
}
