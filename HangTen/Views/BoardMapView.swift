import SwiftUI
import UIKit

struct BoardMapPresentationContent {
    let presentation: BoardPresentation
    let holds: [BoardHold]

    init(
        board: TrainingBoard,
        requestedPresentationID: String?,
        highlightedHoldIDs: Set<String>
    ) {
        let requested = board.presentation(id: requestedPresentationID)
        let highlighted = board.holds.first {
            highlightedHoldIDs.contains($0.id)
        }.flatMap { board.presentation(id: $0.presentationID) }
        let resolvedPresentation = requested ?? highlighted ?? board.defaultPresentation
        presentation = resolvedPresentation
        holds = board.holds.filter { $0.presentationID == resolvedPresentation.id }
    }
}

struct BoardMapView: View {
    let board: TrainingBoard
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((BoardHold) -> Void)?
    private let requestedPresentationID: String?

    @State private var activePresentationID: String?

    init(
        board: TrainingBoard,
        highlightedHoldIDs: Set<String> = [],
        highlightMode: BoardHighlightMode = .active,
        selectedPresentationID: String? = nil,
        onHoldTap: ((BoardHold) -> Void)? = nil
    ) {
        self.board = board
        self.highlightedHoldIDs = highlightedHoldIDs
        self.highlightMode = highlightMode
        self.onHoldTap = onHoldTap
        requestedPresentationID = selectedPresentationID
        _activePresentationID = State(initialValue: selectedPresentationID)
    }

    var body: some View {
        let content = BoardMapPresentationContent(
            board: board,
            requestedPresentationID: activePresentationID,
            highlightedHoldIDs: highlightedHoldIDs
        )
        VStack(spacing: 8) {
            if board.presentations.count > 1 {
                Picker(
                    "Board surface",
                    selection: Binding(
                        get: { content.presentation.id },
                        set: { activePresentationID = $0 }
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
        .onChange(of: highlightedHoldIDs) { _, holdIDs in
            guard let hold = board.holds.first(where: { holdIDs.contains($0.id) }) else {
                return
            }
            activePresentationID = hold.presentationID
        }
        .onChange(of: requestedPresentationID) { _, presentationID in
            activePresentationID = presentationID
        }
        .onChange(of: board.id) { _, _ in
            activePresentationID = requestedPresentationID
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
