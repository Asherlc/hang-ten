import SwiftUI
import UIKit

struct BoardMapView: View {
    let board: TrainingBoard
    var highlightedHoldIDs: Set<String> = []
    var highlightMode: BoardHighlightMode = .active
    var showsLabels = true
    var onHoldTap: ((BoardHold) -> Void)?

    var body: some View {
        Group {
            if let design = BoardCatalog.packageStore.design(for: board.id) {
                DesignedBoardMap(
                    board: board,
                    design: design,
                    highlightedHoldIDs: highlightedHoldIDs,
                    highlightMode: highlightMode,
                    onHoldTap: onHoldTap
                )
            } else {
                GenericVectorBoardMap(
                    board: board,
                    highlightedHoldIDs: highlightedHoldIDs,
                    highlightMode: highlightMode,
                    showsLabels: showsLabels,
                    onHoldTap: onHoldTap
                )
            }
        }
        .aspectRatio(board.aspectRatio, contentMode: .fit)
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

/// A thin SwiftUI adapter over the shared board design language. The design's
/// resolved hold geometry drives the recess, highlight, and interaction region.
private struct DesignedBoardMap: View {
    let board: TrainingBoard
    let design: BoardDesign
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((BoardHold) -> Void)?

    var body: some View {
        GeometryReader { proxy in
            let boardRect = design.boardRect(in: proxy.size)

            ZStack {
                Canvas(opaque: false, rendersAsynchronously: true) { context, size in
                    design.draw(
                        in: &context,
                        size: size,
                        highlightedHoldIDs: highlightedHoldIDs,
                        highlightMode: highlightMode
                    )
                }

                ForEach(board.holds) { hold in
                    let pieces = design.holdPieces(for: hold.id)
                    if !pieces.isEmpty {
                        let hitShape = BoardHoldPathShape(pieces: pieces)
                        hitShape
                            .fill(Color.clear)
                            .contentShape(hitShape)
                            .frame(
                                width: boardRect.width,
                                height: boardRect.height
                            )
                            .position(
                                x: boardRect.midX,
                                y: boardRect.midY
                            )
                            .onTapGesture {
                                onHoldTap?(hold)
                            }
                            .accessibilityLabel(hold.name)
                            .accessibilityAddTraits(.isButton)
                    }
                }
            }
        }
        .animation(.easeInOut(duration: 0.18), value: highlightedHoldIDs)
    }
}

// MARK: - Generic fallback for boards awaiting bespoke geometry

private struct GenericVectorBoardMap: View {
    let board: TrainingBoard
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let showsLabels: Bool
    let onHoldTap: ((BoardHold) -> Void)?

    var body: some View {
        GeometryReader { proxy in
            ZStack {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [.hangWoodLight, .hangWood],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                ForEach(board.holds) { hold in
                    let isHighlighted = highlightedHoldIDs.contains(hold.id)

                    PhysicalHoldVisual(
                        hold: hold,
                        isHighlighted: isHighlighted,
                        highlightMode: highlightMode,
                        showsLabel: showsLabels
                    )
                    .frame(width: proxy.size.width, height: proxy.size.height)
                    .position(x: proxy.size.width / 2, y: proxy.size.height / 2)
                    .onTapGesture {
                        onHoldTap?(hold)
                    }
                }
            }
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
