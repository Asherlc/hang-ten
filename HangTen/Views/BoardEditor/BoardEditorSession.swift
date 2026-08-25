import Foundation
import SwiftUI

@MainActor
final class BoardEditorSession: ObservableObject {
    struct PieceSelection: Equatable {
        let holdID: String
        let pieceIndex: Int
    }

    enum HandleTarget: Equatable {
        case anchor(commandIndex: Int)
        case control(commandIndex: Int, slot: Int)
        case constraintHandle(ConstrainedHandle)
        case rotation
    }

    enum Tool: String, CaseIterable {
        case pan
        case edit
    }

    enum SessionError: LocalizedError {
        case noSelection
        case pieceNotEditable
        case invalidGeometry(String)
        case segmentNotEditable

        var errorDescription: String? {
            switch self {
            case .noSelection:
                "Select a hold piece first."
            case .pieceNotEditable:
                "This piece uses a rounded-rectangle shape. Convert it to a path to edit it."
            case .invalidGeometry(let reason):
                reason
            case .segmentNotEditable:
                "Choose a vertex first."
            }
        }
    }

    static let historyLimit = 100

    let slug: String
    let pixelWidth: Int
    let pixelHeight: Int
    private let store: BoardEditorStore

    @Published private(set) var document: BoardEditableDocument
    @Published private(set) var selectedPiece: PieceSelection?
    @Published private(set) var selectedHandle: HandleTarget?
    @Published var tool: Tool = .edit
    @Published private(set) var canUndo = false
    @Published private(set) var canRedo = false
    @Published private(set) var lastSaveError: String?
    @Published private(set) var isSaved = true

    private var undoStack: [BoardEditableDocument] = []
    private var redoStack: [BoardEditableDocument] = []

    init(package: BoardEditedPackage, store: BoardEditorStore) {
        self.slug = package.slug
        self.pixelWidth = package.pixelWidth
        self.pixelHeight = package.pixelHeight
        self.document = package.document
        self.store = store
    }

    var minimumResizeWidth: CGFloat {
        CGFloat(6) / CGFloat(max(pixelWidth, 1))
    }

    var minimumResizeHeight: CGFloat {
        CGFloat(6) / CGFloat(max(pixelHeight, 1))
    }

    func hold(id: String) -> BoardEditableHold? {
        document.holds.first { $0.id == id }
    }

    var selectedHold: BoardEditableHold? {
        guard let selectedPiece else { return nil }
        return hold(id: selectedPiece.holdID)
    }

    /// `kind` is required by the package schema, so an editable hold needs
    /// the remaining required metadata before it is considered complete.
    var incompleteMetadataHoldIDs: [String] {
        document.holds.compactMap { hold in
            hold.fingerCapacity == nil
                || hold.depthRangeMillimeters == nil
                || hold.handCapacity == nil
                ? hold.id
                : nil
        }
    }

    var metadataWarningText: String? {
        let count = incompleteMetadataHoldIDs.count
        guard count > 0 else { return nil }
        return "\(count) \(count == 1 ? "hold needs" : "holds need") metadata"
    }

    var metadataWarningAccessibilityLabel: String {
        let count = incompleteMetadataHoldIDs.count
        guard count > 0 else { return "Hangboard hold editor" }
        return "Hangboard hold editor. \(count) \(count == 1 ? "hold is" : "holds are") missing required metadata."
    }

    var metadataWarningAccessibilityValue: String? {
        let ids = incompleteMetadataHoldIDs
        guard !ids.isEmpty else { return nil }
        return "Incomplete \(ids.count == 1 ? "hold" : "holds"): \(ids.joined(separator: ", "))"
    }

    var selectedPieceDocument: BoardEditablePiece? {
        guard let selectedPiece,
              let selectedHold,
              selectedHold.geometry.indices.contains(selectedPiece.pieceIndex) else {
            return nil
        }
        return selectedHold.geometry[selectedPiece.pieceIndex]
    }

    var isRoundedRectPiece: Bool {
        selectedPieceDocument?.shape.type == "roundedRect"
    }

    func select(holdID: String?, pieceIndex: Int = 0) {
        selectedPiece = holdID.map { PieceSelection(holdID: $0, pieceIndex: pieceIndex) }
        selectedHandle = nil
    }

    func select(handle: HandleTarget?) {
        selectedHandle = handle
    }

    // MARK: - Board space conversion

    /// Canonical piece-local commands mapped into board-normalized space,
    /// where all interactive editing happens (Workbench display-path parity).
    func boardCommands(for piece: BoardEditablePiece) throws -> [BoardPathCommand] {
        guard let commandDocuments = piece.shape.commands else {
            throw SessionError.pieceNotEditable
        }
        let local = try commandDocuments.holdPathCommands()
        let frame = piece.frame.cgRect
        return local.map { $0.mappedToBoard(frame: frame) }
    }

    /// Bendable marks ride on the canonical curve commands; the engine works
    /// on flag-free commands, so the session keeps this index-aligned mask.
    func bendableFlags(for piece: BoardEditablePiece) -> [Bool] {
        (piece.shape.commands ?? []).map { $0.bendable == true }
    }

    /// Converts edited board-space commands back into canonical piece storage:
    /// the frame becomes the tight anchor bounds and every point renormalizes
    /// into it, mirroring the Workbench display-path save pipeline. Control
    /// points may legitimately fall outside the unit square after this.
    private func canonicalWriteBack(
        _ boardPath: [BoardPathCommand],
        bendableFlags: [Bool]? = nil,
        constraint: ShapeConstraint?,
        treatment: BoardGeometryTreatmentDocument?
    ) throws -> BoardEditablePiece {
        try HoldPathEngine.validateEditableContour(boardPath)
        let anchors = boardPath.compactMap(\.boardAnchor)
        guard let minX = anchors.map(\.x).min(),
              let maxX = anchors.map(\.x).max(),
              let minY = anchors.map(\.y).min(),
              let maxY = anchors.map(\.y).max() else {
            throw SessionError.invalidGeometry("path has no anchor points")
        }
        let width = maxX - minX
        let height = maxY - minY
        guard width > 0, height > 0, width.isFinite, height.isFinite else {
            throw HoldPathEngineError.outlineNeedsNonZeroWidthAndHeight
        }
        let frame = CGRect(x: minX, y: minY, width: width, height: height)
        let normalized = boardPath.map { $0.normalizedToFrame(frame: frame) }
        var commandDocuments = normalized.pathCommandDocuments()
        if let bendableFlags, bendableFlags.count == commandDocuments.count {
            for index in commandDocuments.indices
            where bendableFlags[index] && commandDocuments[index].command == "curve" {
                commandDocuments[index].bendable = true
            }
        }
        return BoardEditablePiece(
            frame: BoardPackageFrameDocument(
                x: Double(frame.minX),
                y: Double(frame.minY),
                width: Double(frame.width),
                height: Double(frame.height)
            ),
            shape: BoardGeometryShapeDocument(
                type: "path",
                commands: commandDocuments,
                cornerRadiusFraction: nil
            ),
            shapeConstraint: constraint,
            treatment: treatment
        )
    }

    // MARK: - History

    private func pushHistory() {
        undoStack.append(document)
        if undoStack.count > Self.historyLimit {
            undoStack.removeFirst()
        }
        redoStack.removeAll()
        canUndo = true
        canRedo = false
        isSaved = false
    }

    /// Records one undo checkpoint at the start of an interactive gesture;
    /// subsequent live updates reuse the same checkpoint.
    func beginInteractiveEdit() {
        pushHistory()
    }

    /// Publishes the post-gesture state; history was captured at gesture
    /// start and replaceGeometry already marked the document dirty.
    func commitLiveChange() {
        objectWillChange.send()
    }

    func undo() {
        guard let previous = undoStack.popLast() else { return }
        redoStack.append(document)
        document = previous
        canUndo = !undoStack.isEmpty
        canRedo = true
        selectedHandle = nil
        isSaved = false
    }

    func redo() {
        guard let next = redoStack.popLast() else { return }
        undoStack.append(document)
        document = next
        canUndo = true
        canRedo = !redoStack.isEmpty
        selectedHandle = nil
        isSaved = false
    }

    // MARK: - Live gesture edits

    func translateSelectedPiece(deltaX: CGFloat, deltaY: CGFloat, recordsHistory: Bool) throws {
        try mutateSelectedBoardPath(recordsHistory: recordsHistory) { boardPath, _ in
            HoldPathEngine.translatePath(&boardPath, deltaX: deltaX, deltaY: deltaY)
        }
    }

    func moveSelectedAnchor(commandIndex: Int, deltaX: CGFloat, deltaY: CGFloat, recordsHistory: Bool) throws {
        try mutateSelectedBoardPath(recordsHistory: recordsHistory) { boardPath, _ in
            HoldPathEngine.moveVertex(&boardPath, index: commandIndex, deltaX: deltaX, deltaY: deltaY)
        }
    }

    func dragControlPoint(commandIndex: Int, slot: Int, deltaX: CGFloat, deltaY: CGFloat, recordsHistory: Bool) throws {
        try mutateSelectedBoardPath(recordsHistory: recordsHistory) { boardPath, _ in
            guard let current = boardPath.controlPoint(commandIndex: commandIndex, slot: slot) else { return }
            boardPath.setControlPoint(
                commandIndex: commandIndex,
                slot: slot,
                point: CGPoint(x: current.x + deltaX, y: current.y + deltaY)
            )
        }
    }

    // MARK: - Discrete edits

    func addVertexAfterAnchor(index: Int) throws {
        try mutateSelectedBoardPath(recordsHistory: true) { boardPath, bendableFlags in
            guard boardPath.indices.contains(index) else { return }
            let start = boardPath[index].boardAnchor ?? .zero
            let nextIndex = (index + 1) % boardPath.count
            let end = boardPath[nextIndex].boardAnchor ?? CGPoint(x: start.x + 1, y: start.y)
            let midpoint = CGPoint(x: (start.x + end.x) / 2, y: (start.y + end.y) / 2)
            HoldPathEngine.addVertex(&boardPath, afterIndex: index, x: midpoint.x, y: midpoint.y)
            if nextIndex < bendableFlags.count {
                let carried = bendableFlags[nextIndex]
                bendableFlags.insert(carried, at: nextIndex)
            }
        }
    }

    func addInflection(after index: Int, at point: CGPoint) throws {
        try mutateSelectedBoardPath(recordsHistory: true) { boardPath, bendableFlags in
            _ = HoldPathEngine.addInflectionPoint(&boardPath, afterIndex: index, point: point)
            let splitIndex = index + 1
            if boardPath.indices.contains(splitIndex), splitIndex < bendableFlags.count {
                let carried = bendableFlags[splitIndex]
                bendableFlags.insert(carried, at: splitIndex)
            }
        }
    }

    func deleteAnchor(index: Int) throws {
        try mutateSelectedBoardPath(recordsHistory: true) { boardPath, bendableFlags in
            HoldPathEngine.deleteVertex(&boardPath, index: index)
            if bendableFlags.indices.contains(index) {
                bendableFlags.remove(at: index)
            }
        }
        selectedHandle = nil
    }

    func straightenSegment(after index: Int) throws {
        try mutateSelectedBoardPath(recordsHistory: true) { boardPath, bendableFlags in
            _ = HoldPathEngine.makeSegmentStraight(&boardPath, afterIndex: index)
            let straightenedIndex = index + 1
            if bendableFlags.indices.contains(straightenedIndex) {
                bendableFlags[straightenedIndex] = false
            }
        }
    }

    func bendSegment(after index: Int) throws {
        try mutateSelectedBoardPath(recordsHistory: true) { boardPath, bendableFlags in
            _ = HoldPathEngine.makeSegmentBendable(&boardPath, afterIndex: index)
            let curveIndex = index + 1
            if bendableFlags.indices.contains(curveIndex) {
                bendableFlags[curveIndex] = true
            }
        }
    }

    func snapSegment(after index: Int, horizontal: Bool) throws {
        try mutateSelectedBoardPath(recordsHistory: true) { boardPath, _ in
            _ = horizontal
                ? HoldPathEngine.snapSegmentHorizontal(&boardPath, afterIndex: index)
                : HoldPathEngine.snapSegmentVertical(&boardPath, afterIndex: index)
        }
    }

    func roundVertex(at index: Int) throws {
        try mutateSelectedBoardPath(recordsHistory: true) { boardPath, bendableFlags in
            _ = HoldPathEngine.roundVertex(&boardPath, index: index)
            for cleared in (index + 1)...(index + 2) where bendableFlags.indices.contains(cleared) {
                bendableFlags[cleared] = false
            }
        }
    }

    func applyPreset(_ preset: OutlinePreset) throws {
        guard let piece = selectedPieceDocument else { throw SessionError.noSelection }
        try ensurePathPiece(piece)
        let existingRotation = piece.shapeConstraint?.rotationDegrees ?? 0
        try mutateSelectedBoardPath(
            recordsHistory: true,
            constraintOverride: ShapeConstraint(
                shape: OutlinePresetMapping.constraintShape(for: preset),
                rotationDegrees: existingRotation
            )
        ) { boardPath, bendableFlags in
            boardPath = try HoldPathEngine.createOutlineShapePath(of: boardPath, preset: preset)
            for index in bendableFlags.indices {
                bendableFlags[index] = false
            }
        }
    }

    func convertRoundedRectToPath() throws {
        guard let selection = selectedPiece,
              let piece = selectedPieceDocument,
              piece.shape.type == "roundedRect" else { return }
        let cornerFraction = piece.shape.cornerRadiusFraction ?? 0
        let frame = piece.frame.cgRect
        let radius = min(frame.width, frame.height) * CGFloat(cornerFraction)
        let bounds = HoldPathBounds(
            minX: frame.minX,
            minY: frame.minY,
            maxX: frame.maxX,
            maxY: frame.maxY
        )
        let boardPath = HoldPathEngine.roundedRectangleCommands(bounds, radius)
        let converted = try canonicalWriteBack(
            boardPath,
            constraint: piece.shapeConstraint,
            treatment: piece.treatment
        )
        pushHistory()
        replaceGeometry(at: selection, with: converted)
    }

    func setConstraintRotation(_ degrees: Double) {
        guard let piece = selectedPieceDocument, let constraint = piece.shapeConstraint else { return }
        replaceSelectedPieceInPlace { current in
            BoardEditablePiece(
                frame: current.frame,
                shape: current.shape,
                shapeConstraint: ShapeConstraint(
                    shape: constraint.shape,
                    rotationDegrees: Self.normalizedConstraintDegrees(degrees)
                ),
                treatment: current.treatment
            )
        }
    }

    /// Shape-constraint metadata is editing guidance only; the saved path
    /// stays untouched when an operator assigns or clears it.
    func setConstraint(_ constraint: ShapeConstraint?) {
        guard let piece = selectedPieceDocument else { return }
        replaceSelectedPieceInPlace { current in
            BoardEditablePiece(
                frame: current.frame,
                shape: current.shape,
                shapeConstraint: constraint,
                treatment: current.treatment
            )
        }
    }

    var selectedAnchorIndex: Int? {
        if case .anchor(let index)? = selectedHandle { return index }
        return nil
    }

    /// Freely rotates an unconstrained path about its anchor centroid.
    func rotateUnconstrained(byDegrees delta: Double) throws {
        guard let piece = selectedPieceDocument else { throw SessionError.noSelection }
        try ensurePathPiece(piece)
        guard piece.shapeConstraint == nil else { return }
        try mutateSelectedBoardPath(recordsHistory: true) { boardPath, _ in
            HoldPathEngine.rotatePath(
                &boardPath,
                angleRadians: CGFloat(delta * Double.pi / 180),
                pivot: Self.anchorCentroid(boardPath)
            )
        }
    }

    /// Interactive constrained resize driven by one of the eight handles.
    func resizeConstrained(
        handle: ConstrainedHandle,
        pointerBoardSpace: CGPoint,
        recordsHistory: Bool
    ) throws {
        guard let selection = selectedPiece else { throw SessionError.noSelection }
        guard let hold = self.hold(id: selection.holdID),
              hold.geometry.indices.contains(selection.pieceIndex) else {
            throw SessionError.noSelection
        }
        let piece = hold.geometry[selection.pieceIndex]
        try ensurePathPiece(piece)
        guard let constraint = piece.shapeConstraint else { return }
        let result = try HoldPathEngine.resizeConstrainedOutline(
            commands: try boardCommands(for: piece),
            constraint: constraint,
            handle: handle,
            pointer: pointerBoardSpace,
            minimumWidth: minimumResizeWidth,
            minimumHeight: minimumResizeHeight
        )
        let updated = try canonicalWriteBack(
            result.commands,
            bendableFlags: [],
            constraint: result.shapeConstraint,
            treatment: piece.treatment
        )
        if recordsHistory {
            pushHistory()
        }
        replaceGeometry(at: selection, with: updated)
    }

    /// Replaces the selected path piece wholesale; the canvas drives this with
    /// gesture-start-relative math so repeated moves never compound drift.
    /// Bendable marks ride on the piece and survive the replacement.
    func replaceSelectedBoardPath(
        _ boardPath: [BoardPathCommand],
        constraint: ShapeConstraint?,
        recordsHistory: Bool
    ) throws {
        guard let selection = selectedPiece else { throw SessionError.noSelection }
        guard let hold = self.hold(id: selection.holdID),
              hold.geometry.indices.contains(selection.pieceIndex) else {
            throw SessionError.noSelection
        }
        let piece = hold.geometry[selection.pieceIndex]
        try ensurePathPiece(piece)
        let updated = try canonicalWriteBack(
            boardPath,
            bendableFlags: bendableFlags(for: piece),
            constraint: constraint ?? piece.shapeConstraint,
            treatment: piece.treatment
        )
        if recordsHistory {
            pushHistory()
        }
        replaceGeometry(at: selection, with: updated)
    }

    func isSegmentBendable(after index: Int) -> Bool {
        guard let piece = selectedPieceDocument,
              let commands = piece.shape.commands,
              commands.indices.contains(index) else {
            return false
        }
        return commands[index].bendable == true
    }

    /// Bends a marked cubic through the pointer; anchors stay fixed.
    func dragBendableSegment(after index: Int, point: CGPoint, recordsHistory: Bool) throws {
        try mutateSelectedBoardPath(recordsHistory: recordsHistory) { boardPath, _ in
            _ = HoldPathEngine.bendSegmentToPoint(&boardPath, afterIndex: index, point: point)
        }
    }

    // MARK: - Persistence

    func save() {
        do {
            try store.save(document: document, slug: slug)
            lastSaveError = nil
            isSaved = true
        } catch {
            lastSaveError = error.localizedDescription
        }
    }

    // MARK: - Static geometry helpers

    static func anchorCentroid(_ commands: [BoardPathCommand]) -> CGPoint {
        let points = commands.compactMap(\.boardAnchor)
        guard !points.isEmpty else { return .zero }
        let sumX = points.reduce(CGFloat(0)) { $0 + $1.x }
        let sumY = points.reduce(CGFloat(0)) { $0 + $1.y }
        return CGPoint(x: sumX / CGFloat(points.count), y: sumY / CGFloat(points.count))
    }

    static func normalizedConstraintDegrees(_ degrees: Double) -> Double {
        var normalized = ((degrees + 180).truncatingRemainder(dividingBy: 360) + 360)
            .truncatingRemainder(dividingBy: 360) - 180
        if normalized == -0 { normalized = 0 }
        if normalized == 180 { normalized = -180 }
        return normalized
    }

    // MARK: - Mutation plumbing

    private func ensurePathPiece(_ piece: BoardEditablePiece) throws {
        guard piece.shape.type == "path" else { throw SessionError.pieceNotEditable }
    }

    private func mutateSelectedBoardPath(
        recordsHistory: Bool,
        constraintOverride: ShapeConstraint? = nil,
        _ transform: (inout [BoardPathCommand], inout [Bool]) throws -> Void
    ) throws {
        guard let selection = selectedPiece else { throw SessionError.noSelection }
        guard let hold = self.hold(id: selection.holdID),
              hold.geometry.indices.contains(selection.pieceIndex) else {
            throw SessionError.noSelection
        }
        let piece = hold.geometry[selection.pieceIndex]
        try ensurePathPiece(piece)
        var boardPath = try boardCommands(for: piece)
        var bendableFlags = bendableFlags(for: piece)
        try transform(&boardPath, &bendableFlags)
        let updated = try canonicalWriteBack(
            boardPath,
            bendableFlags: bendableFlags,
            constraint: constraintOverride ?? piece.shapeConstraint,
            treatment: piece.treatment
        )
        if recordsHistory {
            pushHistory()
        }
        replaceGeometry(at: selection, with: updated)
    }

    private func replaceSelectedPieceInPlace(_ transform: (BoardEditablePiece) -> BoardEditablePiece) {
        guard let selection = selectedPiece else { return }
        guard let hold = self.hold(id: selection.holdID),
              hold.geometry.indices.contains(selection.pieceIndex) else { return }
        pushHistory()
        replaceGeometry(at: selection, with: transform(hold.geometry[selection.pieceIndex]))
    }

    private func replaceGeometry(at selection: PieceSelection, with piece: BoardEditablePiece) {
        guard var hold = self.hold(id: selection.holdID),
              hold.geometry.indices.contains(selection.pieceIndex) else { return }
        hold.geometry[selection.pieceIndex] = piece
        if let index = document.holds.firstIndex(where: { $0.id == selection.holdID }) {
            document.holds[index] = hold
        }
        isSaved = false
    }
}

enum OutlinePresetMapping {
    static func constraintShape(for preset: OutlinePreset) -> ShapeConstraintShape {
        switch preset {
        case .circle: .circle
        case .oval: .oval
        case .pill: .pill
        case .roundedRectangle: .roundedRectangle
        case .rectangle: .rectangle
        }
    }

    static func preset(for shape: ShapeConstraintShape) -> OutlinePreset {
        switch shape {
        case .circle: .circle
        case .oval: .oval
        case .pill: .pill
        case .roundedRectangle: .roundedRectangle
        case .rectangle: .rectangle
        }
    }
}

extension BoardPathCommand {
    /// The point on the contour this command lands on; close has none.
    var boardAnchor: CGPoint? { holdEndPoint }

    func controlPoint(slot: Int) -> CGPoint? {
        switch self {
        case .quad(_, let control):
            slot == 0 ? control : nil
        case .curve(_, let control1, let control2):
            slot == 0 ? control1 : control2
        default:
            nil
        }
    }

    func mappedToBoard(frame: CGRect) -> BoardPathCommand {
        mapPoints { point in
            CGPoint(x: frame.minX + point.x * frame.width, y: frame.minY + point.y * frame.height)
        }
    }

    func normalizedToFrame(frame: CGRect) -> BoardPathCommand {
        mapPoints { point in
            CGPoint(
                x: (point.x - frame.minX) / frame.width,
                y: (point.y - frame.minY) / frame.height
            )
        }
    }
}

extension Array where Element == BoardPathCommand {
    func controlPoint(commandIndex: Int, slot: Int) -> CGPoint? {
        guard indices.contains(commandIndex) else { return nil }
        return self[commandIndex].controlPoint(slot: slot)
    }

    mutating func setControlPoint(commandIndex: Int, slot: Int, point: CGPoint) {
        guard indices.contains(commandIndex) else { return }
        switch self[commandIndex] {
        case .quad(let to, _):
            self[commandIndex] = .quad(to: to, control: point)
        case .curve(let to, let control1, let control2):
            self[commandIndex] = slot == 0
                ? .curve(to: to, control1: point, control2: control2)
                : .curve(to: to, control1: control1, control2: point)
        default:
            break
        }
    }
}
