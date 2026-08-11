import SwiftUI

struct BoardMapView: View {
    let board: TrainingBoard
    var highlightedHoldIDs: Set<String> = []
    var highlightMode: BoardHighlightMode = .active
    var showsLabels = true
    var onHoldTap: ((BoardHold) -> Void)?

    var body: some View {
        Group {
            if let design = BoardDesignCatalog.design(for: board.id) {
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
                    if let hitFrame = design.interactionFrame(for: hold.id) {
                        Color.clear
                            .contentShape(Rectangle())
                            .frame(
                                width: boardRect.width * hitFrame.width,
                                height: boardRect.height * hitFrame.height
                            )
                            .position(
                                x: boardRect.minX + boardRect.width * hitFrame.midX,
                                y: boardRect.minY + boardRect.height * hitFrame.midY
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
                    let frame = hold.frame.rect
                    let isHighlighted = highlightedHoldIDs.contains(hold.id)

                    GenericHoldVisual(
                        hold: hold,
                        isHighlighted: isHighlighted,
                        highlightMode: highlightMode,
                        showsLabel: showsLabels
                    )
                    .frame(
                        width: proxy.size.width * frame.width,
                        height: proxy.size.height * frame.height
                    )
                    .position(
                        x: proxy.size.width * frame.midX,
                        y: proxy.size.height * frame.midY
                    )
                    .contentShape(Rectangle())
                    .onTapGesture {
                        onHoldTap?(hold)
                    }
                }
            }
        }
    }
}

private struct GenericHoldVisual: View {
    let hold: BoardHold
    let isHighlighted: Bool
    let highlightMode: BoardHighlightMode
    let showsLabel: Bool

    var body: some View {
        ZStack {
            holdShape
                .fill(isHighlighted ? highlightFill : Color.hangWoodDeep)
                .overlay {
                    holdShape
                        .stroke(
                            isHighlighted ? highlightStroke : Color.hangWoodShadow,
                            lineWidth: 1
                        )
                }

            if showsLabel {
                Text(hold.shortLabel)
                    .font(.system(size: 10, weight: .heavy, design: .rounded))
                    .foregroundStyle(isHighlighted ? Color.white : Color.hangCream)
                    .minimumScaleFactor(0.6)
            }
        }
    }

    private var highlightFill: Color {
        switch highlightMode {
        case .active:
            return .holdActive
        case .preview:
            return .restBlue
        }
    }

    private var highlightStroke: Color {
        switch highlightMode {
        case .active:
            return .holdActiveDeep
        case .preview:
            return .restBlueDeep
        }
    }

    private var holdShape: AnyShape {
        switch hold.kind {
        case .jug:
            AnyShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        case .edge:
            AnyShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
        case .pocket:
            AnyShape(Capsule())
        case .pinch:
            AnyShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
        case .sloper:
            AnyShape(Ellipse())
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
