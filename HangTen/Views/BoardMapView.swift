import SwiftUI
import UIKit

struct BoardMapView: View {
    let board: TrainingBoard
    var highlightedHoldIDs: Set<String> = []
    var highlightMode: BoardHighlightMode = .active
    var showsLabels = true
    var onHoldTap: ((BoardHold) -> Void)?

    var body: some View {
        PhysicalBoardMap(
            board: board,
            highlightedHoldIDs: highlightedHoldIDs,
            highlightMode: highlightMode,
            showsLabels: showsLabels,
            onHoldTap: onHoldTap
        )
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

/// Renders a board's real presentation photo with each hold's own geometry
/// driving both its highlight overlay and its tap/hit-testing region, so the
/// interactive area always matches what the photo actually shows.
private struct PhysicalBoardMap: View {
    let board: TrainingBoard
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let showsLabels: Bool
    let onHoldTap: ((BoardHold) -> Void)?

    var body: some View {
        GeometryReader { proxy in
            ZStack {
                BoardPresentationImage(board: board)

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
        .animation(.easeInOut(duration: 0.18), value: highlightedHoldIDs)
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
            if isHighlighted {
                shape
                    .fill(highlightFill.opacity(0.6))
                    .overlay {
                        shape.stroke(highlightStroke, lineWidth: 2)
                    }
            }

            if showsLabel {
                GeometryReader { proxy in
                    Text(hold.name)
                        .font(.system(size: 10, weight: .heavy, design: .rounded))
                        .foregroundStyle(Color.white)
                        .minimumScaleFactor(0.6)
                        .padding(.horizontal, 4)
                        .background(Color.black.opacity(0.35), in: Capsule())
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

struct BoardHoldPathShape: Shape {
    let pieces: [BoardHoldPiece]

    func path(in rect: CGRect) -> Path {
        var path = Path()
        for piece in pieces {
            path.addPath(piece.path(in: rect))
        }
        return path
    }
}
