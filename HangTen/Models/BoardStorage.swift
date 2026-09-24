import Foundation

struct BoardContactPieceDocument: Codable, Hashable {
    let frame: BoardPackageFrameDocument
    let shape: BoardGeometryShapeDocument
    let treatment: BoardGeometryTreatmentDocument?
}

enum BoardContactFrameComponent: CaseIterable, Hashable {
    case x
    case y
    case width
    case height
}

struct BoardContactPieceValidationResult {
    let invalidFrameComponents: Set<BoardContactFrameComponent>
    let conversionFailureReason: String?
    let usesDeclaredFrame: Bool
    let piece: BoardContactPiece?

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

struct BoardContactGeometryValidationResult {
    let isEmpty: Bool
    let pieces: [BoardContactPieceValidationResult]
}

enum BoardContactGeometryValidator {
    static func validate(
        _ geometry: [BoardContactPieceDocument],
        contactID: String,
        pieceID: (Int) -> String
    ) -> BoardContactGeometryValidationResult {
        // NOTE: Frame coordinates are intentionally NOT constrained to [0,1].
        // Package geometry may place holds off-canvas (e.g. x = -0.3,
        // width = 2.0). Normalized-frame bounds are enforced separately by
        // the board package compiler before shipping.
        BoardContactGeometryValidationResult(
            isEmpty: geometry.isEmpty,
            pieces: geometry.enumerated().map { index, piece in
                var invalidFrameComponents = Set<BoardContactFrameComponent>()
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
                var validatedPiece: BoardContactPiece?
                do {
                    validatedPiece = try piece.boardContactPiece(id: pieceID(index), contactID: contactID)
                    conversionFailureReason = nil
                } catch {
                    conversionFailureReason = String(describing: error)
                }

                return BoardContactPieceValidationResult(
                    invalidFrameComponents: invalidFrameComponents,
                    conversionFailureReason: conversionFailureReason,
                    usesDeclaredFrame: piece.shape.usesDeclaredFrame,
                    piece: validatedPiece
                )
            }
        )
    }
}
