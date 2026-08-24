import SwiftUI

struct HoldInspectorView: View {
    @ObservedObject var session: BoardEditorSession
    @Environment(\.dismiss) private var dismiss
    @State private var actionError: String?

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 20) {
                header
                if let hold = session.selectedHold {
                    pieceTabs(hold)
                    if session.isRoundedRectPiece {
                        roundedRectNotice
                    } else if let piece = session.selectedPieceDocument {
                        constraintSection(piece)
                        vertexSection
                        segmentSection
                    }
                } else {
                    Text("Tap a hold on the board to edit it.")
                        .font(.system(size: 14, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }
                if let actionError {
                    Text(actionError)
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundStyle(Color.holdActiveDeep)
                }
            }
            .padding(18)
            .padding(.bottom, 24)
        }
        .background(Color.hangBackground)
        .navigationTitle("Hold")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Done") { dismiss() }
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(session.selectedHold?.name ?? "No hold selected")
                .font(.system(size: 19, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            HStack(spacing: 8) {
                if let kind = session.selectedHold?.kind {
                    Pill(title: kind.rawValue, tint: .hangGreenDark, fill: .hangGreen.opacity(0.2))
                }
                if let piece = session.selectedPieceDocument, let constraint = piece.shapeConstraint {
                    Pill(
                        title: "Constrained · \(constraint.shape.rawValue)",
                        tint: .restBlueDeep,
                        fill: Color.restBlue.opacity(0.15)
                    )
                } else if session.selectedPieceDocument != nil {
                    Pill(title: "Freeform", tint: .hangMuted, fill: Color.hangLine.opacity(0.4))
                }
            }
        }
    }

    private func pieceTabs(_ hold: BoardEditableHold) -> some View {
        Group {
            if hold.geometry.count > 1, let selection = session.selectedPiece {
                Picker("Piece", selection: Binding(
                    get: { selection.pieceIndex },
                    set: { session.select(holdID: hold.id, pieceIndex: $0) }
                )) {
                    ForEach(hold.geometry.indices, id: \.self) { index in
                        Text("Piece \(index + 1)").tag(index)
                    }
                }
                .pickerStyle(.segmented)
            }
        }
    }

    private var roundedRectNotice: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionLabel(title: "Rounded rectangle shape")
            Text(
                "This piece stores a rounded-rectangle shape. Converting it to a path keeps its exact outline and lets you edit vertices directly."
            )
            .font(.system(size: 13, weight: .medium, design: .rounded))
            .foregroundStyle(Color.hangMuted)
            Button {
                perform { try session.convertRoundedRectToPath() }
            } label: {
                Text("Convert to editable path")
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangGreenDark)
                    .frame(maxWidth: .infinity)
                    .frame(height: 44)
                    .background(Color.hangGreen.opacity(0.22), in: RoundedRectangle(cornerRadius: 13, style: .continuous))
            }
        }
        .hangCard(padding: 14)
    }

    private func constraintSection(_ piece: BoardEditablePiece) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionLabel(title: "Shape constraint")

            Menu {
                Button("Custom / freeform") {
                    perform { session.setConstraint(nil) }
                }
                ForEach(ShapeConstraintShape.allCases, id: \.self) { shape in
                    Button(shape.displayName) {
                        perform {
                            session.setConstraint(ShapeConstraint(
                                shape: shape,
                                rotationDegrees: piece.shapeConstraint?.rotationDegrees ?? 0
                            ))
                            try? session.applyPreset(OutlinePresetMapping.preset(for: shape))
                        }
                    }
                }
            } label: {
                HStack {
                    Text(piece.shapeConstraint?.displayName ?? "Custom / freeform")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Spacer()
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color.hangMuted)
                }
                .frame(height: 40)
                .padding(.horizontal, 12)
                .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 11, style: .continuous))
            }

            if let constraint = piece.shapeConstraint {
                HStack(spacing: 10) {
                    Button {
                        perform { session.setConstraintRotation(constraint.rotationDegrees - 5) }
                    } label: {
                        Image(systemName: "minus")
                            .frame(width: 44, height: 40)
                            .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 11, style: .continuous))
                    }
                    .accessibilityLabel("Rotate counterclockwise five degrees")

                    Text("\(Int(constraint.rotationDegrees.rounded()))°")
                        .font(.system(size: 16, weight: .bold, design: .rounded).monospacedDigit())
                        .foregroundStyle(Color.hangInk)
                        .frame(maxWidth: .infinity)

                    Button {
                        perform { session.setConstraintRotation(constraint.rotationDegrees + 5) }
                    } label: {
                        Image(systemName: "plus")
                            .frame(width: 44, height: 40)
                            .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 11, style: .continuous))
                    }
                    .accessibilityLabel("Rotate clockwise five degrees")
                }
                Text("Drag the round rotation handle above the selection to rotate interactively.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
        }
        .hangCard(padding: 14)
    }

    private var vertexSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionLabel(title: "Vertex")
            if let index = session.selectedAnchorIndex {
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    inspectorButton("Add vertex") { try session.addVertexAfterAnchor(index: index) }
                    inspectorButton("Delete", destructive: true) { try session.deleteAnchor(index: index) }
                    inspectorButton("Round corner") { try session.roundVertex(at: index) }
                }
            } else {
                Text("Drag or tap a square anchor handle to select a vertex.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
        }
        .hangCard(padding: 14)
    }

    private var segmentSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionLabel(title: "Segment after selected vertex")
            if let index = session.selectedAnchorIndex {
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    inspectorButton("Straighten") { try session.straightenSegment(after: index) }
                    inspectorButton("Bend") { try session.bendSegment(after: index) }
                    inspectorButton("Snap horizontal") { try session.snapSegment(after: index, horizontal: true) }
                    inspectorButton("Snap vertical") { try session.snapSegment(after: index, horizontal: false) }
                }
            } else {
                Text("Select a vertex to bend, straighten, or axis-snap the segment that follows it.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
        }
        .hangCard(padding: 14)
    }

    private func inspectorButton(
        _ title: String,
        destructive: Bool = false,
        action: @escaping () throws -> Void
    ) -> some View {
        Button {
            perform(action)
        } label: {
            Text(title)
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(destructive ? Color.holdActiveDeep : Color.hangInk)
                .frame(maxWidth: .infinity)
                .frame(height: 40)
                .background(
                    destructive ? Color.holdActive.opacity(0.12) : Color.hangCream,
                    in: RoundedRectangle(cornerRadius: 11, style: .continuous)
                )
        }
    }

    private func perform(_ action: () throws -> Void) {
        do {
            try action()
            actionError = nil
        } catch {
            actionError = error.localizedDescription
        }
    }
}

extension ShapeConstraintShape {
    var displayName: String {
        switch self {
        case .oval: "Oval"
        case .circle: "Circle"
        case .pill: "Pill"
        case .roundedRectangle: "Rounded rectangle"
        case .rectangle: "Rectangle"
        }
    }
}

extension ShapeConstraint {
    var displayName: String {
        shape.displayName
    }
}
