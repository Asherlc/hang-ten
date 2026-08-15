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

private struct PhysicalHoldVisual: View {
    let hold: BoardHold
    let isHighlighted: Bool
    let highlightMode: BoardHighlightMode
    let showsLabel: Bool

    var body: some View {
        let shape = BoardHoldPathShape(pieces: hold.geometry)
        ZStack {
            shape
                .fill(isHighlighted ? highlightFill : Color.hangWoodDeep)
                .overlay {
                    shape.stroke(
                        isHighlighted ? highlightStroke : Color.hangWoodShadow,
                        lineWidth: 1
                    )
            }

            if showsLabel {
                GeometryReader { proxy in
                    Text(hold.name)
                        .font(.system(size: 10, weight: .heavy, design: .rounded))
                        .foregroundStyle(isHighlighted ? Color.white : Color.hangCream)
                        .minimumScaleFactor(0.6)
                        .frame(
                            width: max(1, hold.frame.width * proxy.size.width),
                            height: max(1, hold.frame.height * proxy.size.height)
                        )
                        .position(
                            x: hold.frame.rect.midX * proxy.size.width,
                            y: hold.frame.rect.midY * proxy.size.height
                        )
                }
            }
        }
        .contentShape(shape)
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

struct BoardLegend: View {
    var body: some View {
        HStack(spacing: 12) {
            ForEach(HoldKind.allCases) { kind in
                HStack(spacing: 5) {
                    Circle()
                        .fill(kind.tint)
                        .frame(width: 7, height: 7)
                    Text(kind.label)
                        .font(.system(size: 11, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }
            }
        }
    }
}
