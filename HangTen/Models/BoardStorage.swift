import Foundation

struct BoardHoldPieceDocument: Codable, Hashable {
    let frame: BoardPackageFrameDocument
    let shape: BoardGeometryShapeDocument
    let treatment: BoardGeometryTreatmentDocument?
}

enum BoardHoldFrameComponent: CaseIterable, Hashable {
    case x
    case y
    case width
    case height
}

struct BoardHoldPieceValidationResult {
    let invalidFrameComponents: Set<BoardHoldFrameComponent>
    let conversionFailureReason: String?
    let usesDeclaredFrame: Bool
    let piece: BoardHoldPiece?

    var packageFailureReason: String? {
        if !invalidFrameComponents.isEmpty {
            return "has an invalid frame"
        }
        if let conversionFailureReason {
            return "is invalid: \(conversionFailureReason)"
        }
        if !usesDeclaredFrame {
            return "frame must match its shape bounds"
        }
        return nil
    }
}

struct BoardHoldGeometryValidationResult {
    let isEmpty: Bool
    let pieces: [BoardHoldPieceValidationResult]
}

enum BoardHoldGeometryValidator {
    static func validate(
        _ geometry: [BoardHoldPieceDocument],
        holdID: String,
        pieceID: (Int) -> String
    ) -> BoardHoldGeometryValidationResult {
        BoardHoldGeometryValidationResult(
            isEmpty: geometry.isEmpty,
            pieces: geometry.enumerated().map { index, piece in
                var invalidFrameComponents = Set<BoardHoldFrameComponent>()
                let frame = piece.frame
                if !frame.x.isFinite {
                    invalidFrameComponents.insert(.x)
                }
                if !frame.y.isFinite {
                    invalidFrameComponents.insert(.y)
                }
                if !frame.width.isFinite || frame.width <= 0 {
                    invalidFrameComponents.insert(.width)
                }
                if !frame.height.isFinite || frame.height <= 0 {
                    invalidFrameComponents.insert(.height)
                }

                var conversionFailureReason: String?
                var validatedPiece: BoardHoldPiece?
                do {
                    validatedPiece = try piece.boardHoldPiece(id: pieceID(index), holdID: holdID)
                    conversionFailureReason = nil
                } catch {
                    conversionFailureReason = String(describing: error)
                }

                return BoardHoldPieceValidationResult(
                    invalidFrameComponents: invalidFrameComponents,
                    conversionFailureReason: conversionFailureReason,
                    usesDeclaredFrame: piece.shape.usesDeclaredFrame,
                    piece: validatedPiece
                )
            }
        )
    }
}
