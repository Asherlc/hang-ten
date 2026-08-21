import SwiftUI
import UIKit

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
        holds = board.holds.filter { $0.presentationID == resolvedPresentation.id }
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
        presentationID = Self.presentationID(
            for: activeHoldID,
            on: board
        ) ?? board.holds.first(where: {
            highlightedHoldIDs.contains($0.id)
        })?.presentationID ?? board.presentation(id: requestedPresentationID)?.id
            ?? board.defaultPresentation.id
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
        if let activePresentationID = Self.presentationID(for: activeHoldID, on: board) {
            presentationID = activePresentationID
            return
        }
        let addedHoldIDs = highlightedHoldIDs.subtracting(previousHoldIDs)
        if let addedHold = board.holds.first(where: { addedHoldIDs.contains($0.id) }) {
            presentationID = addedHold.presentationID
        }
    }

    mutating func activateHold(id: String?, on board: TrainingBoard) {
        guard let activePresentationID = Self.presentationID(for: id, on: board) else {
            return
        }
        presentationID = activePresentationID
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

    private static func presentationID(for holdID: String?, on board: TrainingBoard) -> String? {
        guard let holdID else { return nil }
        return board.holds.first(where: { $0.id == holdID })?.presentationID
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
                ZStack {
                    BoardPresentationImage(
                        board: board,
                        presentationID: content.presentation.id
                    )

                    ForEach(content.holds) { hold in
                        PhysicalHoldVisual(
                            hold: hold,
                            isHighlighted: highlightedHoldIDs.contains(hold.id),
                            highlightMode: highlightMode,
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
            presentationSelection.reset(
                board: board,
                requestedPresentationID: presentationID,
                activeHoldID: activeHoldID,
                highlightedHoldIDs: highlightedHoldIDs
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
    let onTap: ((BoardHold) -> Void)?

    @ViewBuilder
    var body: some View {
        let shape = BoardHoldPathShape(pieces: hold.geometry)
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
