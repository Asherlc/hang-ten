import SwiftUI
import UIKit

struct BoardMapView: View {
    let board: TrainingBoard
    var highlightedHoldIDs: Set<String> = []
    var highlightMode: BoardHighlightMode = .active
    var onHoldTap: ((BoardHold) -> Void)?

    var body: some View {
        GeometryReader { _ in
            ZStack {
                BoardPresentationImage(board: board)

                ForEach(board.holds) { hold in
                    PhysicalHoldVisual(
                        hold: hold,
                        isHighlighted: highlightedHoldIDs.contains(hold.id),
                        highlightMode: highlightMode,
                        onTap: onHoldTap
                    )
                }
            }
        }
        .aspectRatio(board.aspectRatio, contentMode: .fit)
        .animation(.easeInOut(duration: 0.18), value: highlightedHoldIDs)
    }
}

/// Loads only a package-declared presentation file. A board without one has
/// no image view and never falls back to an asset-catalog name.
struct BoardPresentationImage: View {
    let board: TrainingBoard

    @ViewBuilder
    var body: some View {
        if let url = BoardCatalog.packageStore.presentationImageURL(for: board),
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

    var body: some View {
        let shape = BoardHoldPathShape(pieces: hold.geometry)
        ZStack {
            shape
                .fill(isHighlighted ? highlightFill.opacity(0.38) : Color.clear)
            .overlay {
                shape.stroke(
                    isHighlighted ? highlightStroke : Color.clear,
                    lineWidth: 2
                )
            }
        }
        .contentShape(shape)
        .onTapGesture {
            onTap?(hold)
        }
        .accessibilityLabel(hold.name)
        .accessibilityAddTraits(.isButton)
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
