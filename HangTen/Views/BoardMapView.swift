import SwiftUI
import UIKit

struct BoardDetailHoldMap {
    struct Entry: Identifiable, Hashable {
        let number: Int
        let hold: BoardHold

        var id: String { hold.id }
    }

    let presentation: BoardPresentation
    let entries: [Entry]

    init(board: TrainingBoard, presentationID: String?) {
        let content = BoardMapPresentationContent(
            board: board,
            selectedPresentationID: presentationID
        )
        presentation = content.presentation
        entries = content.holds.enumerated().map { index, hold in
            Entry(number: index + 1, hold: hold)
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
    static func entries(for hold: BoardHold) -> [BoardHoldSpecification] {
        var entries = [BoardHoldSpecification(label: "Kind", value: hold.kind.detailLabel)]

        if let size = hold.sizeMillimeters {
            entries.append(.init(label: "Depth", value: millimeters(size)))
        } else if let range = hold.depthRangeMillimeters {
            entries.append(
                .init(
                    label: "Depth range",
                    value: "\(millimeters(range.lowerBound))–\(millimeters(range.upperBound))"
                )
            )
        }
        if let gripType = hold.gripType {
            entries.append(.init(label: "Grip", value: gripType.label))
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
    let holds: [BoardHold]

    init(
        board: TrainingBoard,
        selectedPresentationID: String?
    ) {
        let resolvedPresentation = board.presentation(id: selectedPresentationID)
            ?? board.defaultPresentation
        presentation = resolvedPresentation
        holds = board.availableHolds(for: resolvedPresentation)
    }
}

struct BoardMapPresentationSelection: Equatable {
    private(set) var presentationID: String

    init(
        board: TrainingBoard,
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
        } else if let highlightedHoldID = board.holds.first(where: {
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

    mutating func selectPresentation(id: String, on board: TrainingBoard) {
        guard let presentation = board.presentation(id: id) else { return }
        presentationID = presentation.id
    }

    mutating func updateHighlights(
        from previousHoldIDs: Set<String>,
        to highlightedHoldIDs: Set<String>,
        activeHoldID: String?,
        on board: TrainingBoard
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
        if let addedHold = board.holds.first(where: { addedHoldIDs.contains($0.id) }) {
            presentationID = Self.presentationID(
                for: addedHold.id,
                preferring: presentationID,
                on: board
            ) ?? presentationID
        }
    }

    mutating func activateHold(id: String?, on board: TrainingBoard) {
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
        on board: TrainingBoard
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
        board: TrainingBoard,
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
        on board: TrainingBoard
    ) -> String? {
        guard let holdID else { return nil }
        guard board.holds.contains(where: { $0.id == holdID }) else {
            return nil
        }
        if let preferredPresentation = board.presentation(id: preferredPresentationID),
           board.availableHolds(for: preferredPresentation).contains(where: { $0.id == holdID }) {
            return preferredPresentation.id
        }
        return board.presentations.first(where: { presentation in
            board.availableHolds(for: presentation).contains(where: { $0.id == holdID })
        })?.id
    }
}

struct BoardDetailMapView: View {
    let board: TrainingBoard
    @Binding var selectedHoldID: String?
    private let selectedHoldContent: AnyView?

    @State private var presentationSelection: BoardMapPresentationSelection

    init(
        board: TrainingBoard,
        selectedHoldID: Binding<String?>,
        selectedHoldContent: AnyView? = nil
    ) {
        self.board = board
        _selectedHoldID = selectedHoldID
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
    }

    @ViewBuilder
    private func mapContent(_ map: BoardDetailHoldMap) -> some View {
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

        GeometryReader { proxy in
            let boardBounds = proxy.size
            let boardRect = CGRect(origin: .zero, size: boardBounds)
            let projection = BoardPresentationGeometryProjection(
                presentation: map.presentation
            )
            let cordGeometry = BoardPresentationArtwork.geometry(
                for: board,
                presentation: map.presentation,
                projection: projection,
                canvasSize: boardBounds
            )
            ZStack {
                BoardPresentationArtwork(
                    board: board,
                    presentation: map.presentation,
                    projection: projection,
                    canvasSize: boardBounds,
                    geometry: cordGeometry
                )

                ForEach(map.entries) { entry in
                    PhysicalHoldVisual(
                        hold: entry.hold,
                        isHighlighted: selectedHoldID == entry.hold.id,
                        highlightMode: .active,
                        projection: projection,
                        canonicalRect: cordGeometry?.faceRect,
                        onTap: { select($0.id) }
                    )
                    .frame(width: boardBounds.width, height: boardBounds.height)

                    BoardHoldNumberMarker(
                        entry: entry,
                        isSelected: selectedHoldID == entry.hold.id
                    ) {
                        select(entry.hold.id)
                    }
                    .position(
                        markerPosition(
                            for: entry.hold,
                            in: boardRect,
                            projection: projection,
                            canonicalRect: cordGeometry?.faceRect
                        )
                    )
                }
            }
        }
        .aspectRatio(map.presentation.aspectRatio, contentMode: .fit)
        .accessibilityIdentifier("boardDetail.map")
    }

    @ViewBuilder
    private func holdLegend(_ map: BoardDetailHoldMap) -> some View {
        if !map.entries.isEmpty {
            SectionLabel(title: "Hold map")
            LazyVGrid(
                    columns: [GridItem(.adaptive(minimum: 132), spacing: 8)],
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
                                .font(.system(size: 13, weight: .semibold, design: .rounded))
                                .foregroundStyle(Color.hangInk)
                                .lineLimit(1)
                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 7)
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
        for hold: BoardHold,
        in bounds: CGRect,
        projection: BoardPresentationGeometryProjection,
        canonicalRect: CGRect?
    ) -> CGPoint {
        let sourceRect = canonicalRect ?? bounds
        let center = CGPoint(
            x: sourceRect.minX + hold.frame.x * sourceRect.width
                + hold.frame.width * sourceRect.width / 2,
            y: sourceRect.minY + hold.frame.y * sourceRect.height
                + hold.frame.height * sourceRect.height / 2
        )
        return projection.project(center, in: bounds)
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
    let board: TrainingBoard
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((BoardHold) -> Void)?
    private let requestedPresentationID: String?
    private let activeHoldID: String?

    @State private var presentationSelection: BoardMapPresentationSelection

    init(
        board: TrainingBoard,
        highlightedHoldIDs: Set<String> = [],
        highlightMode: BoardHighlightMode = .active,
        selectedPresentationID: String? = nil,
        activeHoldID: String? = nil,
        onHoldTap: ((BoardHold) -> Void)? = nil
    ) {
        self.board = board
        self.highlightedHoldIDs = highlightedHoldIDs
        self.highlightMode = highlightMode
        self.onHoldTap = onHoldTap
        requestedPresentationID = selectedPresentationID
        self.activeHoldID = activeHoldID
        _presentationSelection = State(
            initialValue: BoardMapPresentationSelection(
                board: board,
                requestedPresentationID: selectedPresentationID,
                activeHoldID: activeHoldID,
                highlightedHoldIDs: highlightedHoldIDs
            )
        )
    }

    var body: some View {
        let content = BoardMapPresentationContent(
            board: board,
            selectedPresentationID: presentationSelection.presentationID
        )
        VStack(spacing: 8) {
            if board.presentations.count > 1 {
                Picker(
                    "Board surface",
                    selection: Binding(
                        get: { content.presentation.id },
                        set: { presentationSelection.selectPresentation(id: $0, on: board) }
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

            GeometryReader { proxy in
                let boardBounds = proxy.size
                let projection = BoardPresentationGeometryProjection(
                    presentation: content.presentation
                )
                let cordGeometry = BoardPresentationArtwork.geometry(
                    for: board,
                    presentation: content.presentation,
                    projection: projection,
                    canvasSize: boardBounds
                )
                ZStack {
                    BoardPresentationArtwork(
                        board: board,
                        presentation: content.presentation,
                        projection: projection,
                        canvasSize: boardBounds,
                        geometry: cordGeometry
                    )

                    ForEach(content.holds) { hold in
                        PhysicalHoldVisual(
                            hold: hold,
                            isHighlighted: highlightedHoldIDs.contains(hold.id),
                            highlightMode: highlightMode,
                            projection: projection,
                            canonicalRect: cordGeometry?.faceRect,
                            onTap: onHoldTap
                        )
                        .frame(width: boardBounds.width, height: boardBounds.height)
                    }
                }
                .frame(width: boardBounds.width, height: boardBounds.height)
            }
            .aspectRatio(content.presentation.aspectRatio, contentMode: .fit)
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
            presentationSelection.reset(
                board: board,
                requestedPresentationID: requestedPresentationID,
                activeHoldID: activeHoldID,
                highlightedHoldIDs: highlightedHoldIDs
            )
        }
    }
}

/// Loads only a package-declared presentation file. A board without one has
/// no image view and never falls back to an asset-catalog name.
struct BoardPresentationImage: View {
    let board: TrainingBoard
    let presentationID: String?

    init(board: TrainingBoard, presentationID: String? = nil) {
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
    let hold: BoardHold
    let isHighlighted: Bool
    let highlightMode: BoardHighlightMode
    let projection: BoardPresentationGeometryProjection
    let canonicalRect: CGRect?
    let onTap: ((BoardHold) -> Void)?

    @ViewBuilder
    var body: some View {
        let shape = BoardHoldPathShape(
            pieces: hold.geometry,
            projection: projection,
            canonicalRect: canonicalRect
        )
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
