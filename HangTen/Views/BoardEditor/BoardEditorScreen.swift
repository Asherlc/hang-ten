import SwiftUI

final class HoldEditorCanvasReference {
    weak var view: HoldEditorCanvasUIView?
}

private enum EditorCanvasBackground: String, CaseIterable, Identifiable {
    case hangBackground
    case white
    case charcoal

    var id: Self { self }

    var name: String {
        switch self {
        case .hangBackground: "Cream"
        case .white: "White"
        case .charcoal: "Charcoal"
        }
    }

    var color: Color {
        switch self {
        case .hangBackground: .hangBackground
        case .white: .white
        case .charcoal: Color(red: 0.16, green: 0.17, blue: 0.18)
        }
    }
}

struct BoardEditorScreen: View {
    @StateObject private var session: BoardEditorSession
    @Environment(\.dismiss) private var dismiss
    @State private var showsUnsavedConfirmation = false
    @State private var showsInspector = false
    @State private var showsExportShare = false
    @State private var canvasReference = HoldEditorCanvasReference()
    @State private var canvasBackground = EditorCanvasBackground.hangBackground
    private let store: BoardEditorStore
    private let imageURL: URL?
    private let loadFailed: Bool

    init(slug: String, store: BoardEditorStore) {
        self.store = store
        _ = try? store.startEditing(slug: slug)
        if let package = try? store.loadDocument(slug: slug) {
            self.imageURL = package.imageURL
            self.loadFailed = false
            _session = StateObject(wrappedValue: BoardEditorSession(package: package, store: store))
        } else {
            self.imageURL = nil
            self.loadFailed = true
            _session = StateObject(wrappedValue: BoardEditorSession(
                package: Self.placeholderPackage(slug: slug),
                store: store
            ))
        }
    }

    static func placeholderPackage(slug: String) -> BoardEditedPackage {
        BoardEditedPackage(
            slug: slug,
            packageURL: URL(fileURLWithPath: "/dev/null"),
            document: BoardEditableDocument(
                id: slug,
                manufacturer: "",
                name: slug,
                subtitle: "",
                productURL: URL(string: "https://example.invalid")!,
                dimensions: "",
                aspectRatio: 2,
                holds: [],
                presentations: []
            ),
            imageURL: URL(fileURLWithPath: "/dev/null"),
            pixelWidth: 1,
            pixelHeight: 1
        )
    }

    private var exportedURL: URL? {
        guard session.isSaved else { return nil }
        return try? store.exportedFileURL(slug: session.slug)
            .appendingPathComponent("board.json")
    }

    var body: some View {
        Group {
            if loadFailed {
                Text("This board package could not be opened for editing.")
                    .foregroundStyle(Color.hangMuted)
                    .padding()
            } else {
                editorCanvas
            }
        }
        .background(Color.hangBackground)
        .navigationTitle(session.document.name)
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button {
                    if session.isSaved || loadFailed {
                        dismiss()
                    } else {
                        showsUnsavedConfirmation = true
                    }
                } label: {
                    Image(systemName: "chevron.left")
                }
                .accessibilityLabel("Back")
            }
            ToolbarItem(placement: .topBarTrailing) {
                if let exportedURL {
                    ShareLink(item: exportedURL) {
                        Image(systemName: "square.and.arrow.up")
                    }
                    .accessibilityLabel("Export board JSON")
                    .accessibilityIdentifier("boardEditor.export")
                }
            }
        }
        .confirmationDialog(
            "Discard unsaved geometry changes?",
            isPresented: $showsUnsavedConfirmation,
            titleVisibility: .visible
        ) {
            Button("Discard changes", role: .destructive) { dismiss() }
            Button("Keep editing", role: .cancel) {}
        }
        .safeAreaInset(edge: .bottom) {
            if !loadFailed {
                editorToolbar
            }
        }
        .sheet(isPresented: $showsInspector) {
            NavigationStack {
                HoldInspectorView(session: session)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
        }
    }

    private var editorCanvas: some View {
        ZStack {
            HoldEditorCanvasView(
                session: session,
                image: imageURL.flatMap { UIImage(contentsOfFile: $0.path) },
                editorBackgroundColor: UIColor(canvasBackground.color),
                reference: canvasReference
            )
            .ignoresSafeArea(edges: .bottom)

            VStack(spacing: 0) {
                HStack(spacing: 12) {
                    if let metadataWarningText = session.metadataWarningText {
                        Label(metadataWarningText, systemImage: "exclamationmark.triangle.fill")
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.holdOrange)
                            .padding(.horizontal, 10)
                            .frame(height: 34)
                            .background(Color.hangCream.opacity(0.9), in: Capsule())
                            .accessibilityLabel("Warning: \(metadataWarningText)")
                            .accessibilityIdentifier("boardEditor.metadataWarning")
                    }

                    Picker("Tool", selection: $session.tool) {
                        ForEach(BoardEditorSession.Tool.allCases, id: \.self) { tool in
                            Image(systemName: tool == .pan ? "hand.draw" : "cursorarrow.rays")
                                .tag(tool)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(maxWidth: 150)
                    .background(Color.hangCream.opacity(0.85), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .accessibilityIdentifier("boardEditor.tool")

                    Menu {
                        ForEach(EditorCanvasBackground.allCases) { background in
                            Button {
                                canvasBackground = background
                            } label: {
                                Label(background.name, systemImage: background == canvasBackground ? "checkmark" : "circle.fill")
                            }
                        }
                    } label: {
                        Circle()
                            .fill(canvasBackground.color)
                            .frame(width: 24, height: 24)
                            .overlay {
                                Circle().stroke(Color.hangInk.opacity(0.5), lineWidth: 1)
                            }
                            .frame(width: 40, height: 40)
                            .background(Color.hangCream.opacity(0.9), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }
                    .accessibilityLabel("Canvas background: \(canvasBackground.name)")
                    .accessibilityHint("Choose a canvas background color")
                    .accessibilityIdentifier("boardEditor.backgroundColor")

                    Spacer()

                    Button {
                        canvasReference.view?.zoomToFit()
                    } label: {
                        Image(systemName: "arrow.down.right.and.arrow.up.left")
                            .font(.system(size: 15, weight: .bold))
                            .foregroundStyle(Color.hangInk)
                            .frame(width: 40, height: 40)
                            .background(Color.hangCream.opacity(0.9), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }
                    .accessibilityLabel("Zoom to fit")
                    .accessibilityIdentifier("boardEditor.zoomToFit")
                }
                .padding(.horizontal, 16)
                .padding(.top, 8)
                Spacer()
            }
        }
    }

    private var editorToolbar: some View {
        HStack(spacing: 14) {
            Button {
                session.undo()
            } label: {
                Image(systemName: "arrow.uturn.backward")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color.hangInk)
                    .frame(width: 44, height: 44)
                    .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
            }
            .disabled(!session.canUndo)
            .opacity(session.canUndo ? 1 : 0.4)
            .accessibilityLabel("Undo")
            .accessibilityIdentifier("boardEditor.undo")

            Button {
                session.redo()
            } label: {
                Image(systemName: "arrow.uturn.forward")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color.hangInk)
                    .frame(width: 44, height: 44)
                    .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
            }
            .disabled(!session.canRedo)
            .opacity(session.canRedo ? 1 : 0.4)
            .accessibilityLabel("Redo")
            .accessibilityIdentifier("boardEditor.redo")

            Button {
                showsInspector = true
            } label: {
                Label("Hold", systemImage: "hand.tap")
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangGreenDark)
                    .frame(maxWidth: .infinity)
                    .frame(height: 44)
                    .background(Color.hangGreen.opacity(0.22), in: RoundedRectangle(cornerRadius: 13, style: .continuous))
            }
            .disabled(session.selectedPiece == nil)
            .accessibilityIdentifier("boardEditor.inspector")

            Button {
                session.save()
            } label: {
                Image(systemName: session.isSaved ? "checkmark.circle.fill" : "square.and.arrow.down")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(session.isSaved ? Color.hangGreenDark : Color.hangInk)
                    .frame(width: 44, height: 44)
                    .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
            }
            .accessibilityLabel(session.isSaved ? "Saved" : "Save")
            .accessibilityIdentifier("boardEditor.save")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.ultraThinMaterial)
        .alert(
            "Could not save",
            isPresented: Binding(
                get: { session.lastSaveError != nil },
                set: { if !$0 {} }
            )
        ) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(session.lastSaveError ?? "")
        }
    }
}
