import SwiftUI

enum BoardDesignCatalog {
    static func design(for boardID: String) -> BoardDesign? {
        designs[boardID]
    }

    /// A board can only be considered production-ready when its bespoke design
    /// covers every hold in the board catalog. This keeps a future board from
    /// silently falling back to a generic rectangle after its photo has been
    /// added.
    static func coverageIssues(for board: TrainingBoard) -> [String] {
        var issues: [String] = []
        if designs[board.id] == nil {
            issues.append("Missing bespoke design for board \"\(board.id)\".")
            return issues
        }

        let designedHoldIDs = Set(designs[board.id]?.holds.map(\.holdID) ?? [])
        for holdID in board.holds.map(\.id) where !designedHoldIDs.contains(holdID) {
            issues.append("Board \"\(board.id)\" has no designed geometry for hold \"\(holdID)\".")
        }
        return issues
    }

    static var catalogCoverageIssues: [String] {
        BoardCatalog.all.flatMap(coverageIssues(for:))
    }

    private static let designs: [String: BoardDesign] = [
        BoardCatalog.compactII.id: .metoliusCompactII
    ]
}

extension BoardDesign {
    /// Compact II geometry follows the product photos; its rendering follows
    /// the shared smooth, sculpted board language used by every bespoke board.
    static let metoliusCompactII: BoardDesign = {
        let silhouette = BoardShape.path(
            BoardNormalizedPath(commands: [
                .move(CGPoint(x: 0.065, y: 0.000)),
                .line(CGPoint(x: 0.148, y: 0.000)),
                .quad(to: CGPoint(x: 0.164, y: 0.058), control: CGPoint(x: 0.158, y: 0.008)),
                .line(CGPoint(x: 0.836, y: 0.058)),
                .quad(to: CGPoint(x: 0.852, y: 0.000), control: CGPoint(x: 0.842, y: 0.008)),
                .line(CGPoint(x: 0.935, y: 0.000)),
                .curve(
                    to: CGPoint(x: 1.000, y: 0.095),
                    control1: CGPoint(x: 0.973, y: 0.002),
                    control2: CGPoint(x: 1.000, y: 0.045)
                ),
                .curve(
                    to: CGPoint(x: 0.998, y: 0.155),
                    control1: CGPoint(x: 1.000, y: 0.115),
                    control2: CGPoint(x: 1.000, y: 0.140)
                ),
                .curve(
                    to: CGPoint(x: 0.978, y: 0.300),
                    control1: CGPoint(x: 0.995, y: 0.190),
                    control2: CGPoint(x: 0.980, y: 0.230)
                ),
                .curve(
                    to: CGPoint(x: 0.973, y: 0.500),
                    control1: CGPoint(x: 0.970, y: 0.360),
                    control2: CGPoint(x: 0.980, y: 0.430)
                ),
                .curve(
                    to: CGPoint(x: 0.976, y: 0.610),
                    control1: CGPoint(x: 0.970, y: 0.540),
                    control2: CGPoint(x: 0.972, y: 0.580)
                ),
                .curve(
                    to: CGPoint(x: 0.966, y: 0.740),
                    control1: CGPoint(x: 0.975, y: 0.650),
                    control2: CGPoint(x: 0.970, y: 0.700)
                ),
                .curve(
                    to: CGPoint(x: 0.957, y: 0.880),
                    control1: CGPoint(x: 0.962, y: 0.790),
                    control2: CGPoint(x: 0.958, y: 0.840)
                ),
                .curve(
                    to: CGPoint(x: 0.932, y: 0.997),
                    control1: CGPoint(x: 0.958, y: 0.950),
                    control2: CGPoint(x: 0.956, y: 0.986)
                ),
                .line(CGPoint(x: 0.068, y: 0.997)),
                .curve(
                    to: CGPoint(x: 0.043, y: 0.880),
                    control1: CGPoint(x: 0.044, y: 0.986),
                    control2: CGPoint(x: 0.042, y: 0.950)
                ),
                .curve(
                    to: CGPoint(x: 0.034, y: 0.740),
                    control1: CGPoint(x: 0.042, y: 0.840),
                    control2: CGPoint(x: 0.038, y: 0.790)
                ),
                .curve(
                    to: CGPoint(x: 0.024, y: 0.610),
                    control1: CGPoint(x: 0.030, y: 0.700),
                    control2: CGPoint(x: 0.025, y: 0.650)
                ),
                .curve(
                    to: CGPoint(x: 0.027, y: 0.500),
                    control1: CGPoint(x: 0.028, y: 0.580),
                    control2: CGPoint(x: 0.030, y: 0.540)
                ),
                .curve(
                    to: CGPoint(x: 0.022, y: 0.300),
                    control1: CGPoint(x: 0.020, y: 0.430),
                    control2: CGPoint(x: 0.030, y: 0.360)
                ),
                .curve(
                    to: CGPoint(x: 0.002, y: 0.155),
                    control1: CGPoint(x: 0.020, y: 0.230),
                    control2: CGPoint(x: 0.005, y: 0.190)
                ),
                .curve(
                    to: CGPoint(x: 0.000, y: 0.095),
                    control1: CGPoint(x: 0.000, y: 0.140),
                    control2: CGPoint(x: 0.000, y: 0.115)
                ),
                .curve(
                    to: CGPoint(x: 0.065, y: 0.000),
                    control1: CGPoint(x: 0.000, y: 0.045),
                    control2: CGPoint(x: 0.027, y: 0.002)
                ),
                .close
            ])
        )

        let topPlane = BoardShape.path(
            BoardNormalizedPath(commands: [
                .move(CGPoint(x: 0.000, y: 1.000)),
                .line(CGPoint(x: 0.000, y: 0.160)),
                .line(CGPoint(x: 1.000, y: 0.160)),
                .line(CGPoint(x: 1.000, y: 1.000)),
                .quad(to: CGPoint(x: 0.970, y: 1.000), control: CGPoint(x: 0.995, y: 1.000)),
                .line(CGPoint(x: 0.030, y: 1.000)),
                .quad(to: CGPoint(x: 0.000, y: 1.000), control: CGPoint(x: 0.005, y: 1.000)),
                .close
            ])
        )

        let separator = BoardShape.path(
            BoardNormalizedPath(commands: [
                .move(CGPoint(x: 0.000, y: 0.060)),
                .quad(to: CGPoint(x: 0.015, y: 0.000), control: CGPoint(x: 0.000, y: 0.020)),
                .line(CGPoint(x: 0.985, y: 0.000)),
                .quad(to: CGPoint(x: 1.000, y: 0.060), control: CGPoint(x: 1.000, y: 0.020)),
                .line(CGPoint(x: 0.998, y: 0.830)),
                .quad(to: CGPoint(x: 0.975, y: 1.000), control: CGPoint(x: 1.000, y: 0.960)),
                .line(CGPoint(x: 0.025, y: 1.000)),
                .quad(to: CGPoint(x: 0.002, y: 0.830), control: CGPoint(x: 0.000, y: 0.960)),
                .close
            ])
        )

        let outerUpper = BoardShape.path(
            BoardNormalizedPath(commands: [
                .move(CGPoint(x: 0.065, y: 0.030)),
                .line(CGPoint(x: 0.875, y: 0.030)),
                .quad(to: CGPoint(x: 1.000, y: 0.150), control: CGPoint(x: 0.970, y: 0.030)),
                .line(CGPoint(x: 0.995, y: 0.835)),
                .quad(to: CGPoint(x: 0.875, y: 0.970), control: CGPoint(x: 0.985, y: 0.970)),
                .line(CGPoint(x: 0.085, y: 0.950)),
                .quad(to: CGPoint(x: 0.000, y: 0.790), control: CGPoint(x: 0.015, y: 0.940)),
                .line(CGPoint(x: 0.015, y: 0.210)),
                .quad(to: CGPoint(x: 0.065, y: 0.030), control: CGPoint(x: 0.020, y: 0.070)),
                .close
            ])
        )

        let outerLower = BoardShape.path(
            BoardNormalizedPath(commands: [
                .move(CGPoint(x: 0.050, y: 0.045)),
                .line(CGPoint(x: 0.890, y: 0.025)),
                .quad(to: CGPoint(x: 1.000, y: 0.160), control: CGPoint(x: 0.985, y: 0.025)),
                .line(CGPoint(x: 0.985, y: 0.835)),
                .quad(to: CGPoint(x: 0.860, y: 0.970), control: CGPoint(x: 0.975, y: 0.970)),
                .line(CGPoint(x: 0.075, y: 0.950)),
                .quad(to: CGPoint(x: 0.000, y: 0.785), control: CGPoint(x: 0.015, y: 0.940)),
                .line(CGPoint(x: 0.010, y: 0.200)),
                .quad(to: CGPoint(x: 0.050, y: 0.045), control: CGPoint(x: 0.015, y: 0.075)),
                .close
            ])
        )

        var layers: [BoardLayer] = [
            BoardLayer(
                frame: CGRect(x: 0.158, y: 0.035, width: 0.684, height: 0.128),
                shape: topPlane,
                role: .topPlane
            ),
            BoardLayer(
                frame: CGRect(x: 0.025, y: 0.505, width: 0.950, height: 0.115),
                shape: separator,
                role: .separator
            ),
            BoardLayer(
                frame: CGRect(x: 0.043, y: 0.875, width: 0.914, height: 0.105),
                shape: .roundedRect(cornerRadiusFraction: 0.16),
                role: .bottomPlane
            ),
            BoardLayer(
                frame: CGRect(x: 0.348, y: 0.060, width: 0.004, height: 0.101),
                shape: .roundedRect(cornerRadiusFraction: 0.50),
                role: .topSeam
            ),
            BoardLayer(
                frame: CGRect(x: 0.648, y: 0.060, width: 0.004, height: 0.101),
                shape: .roundedRect(cornerRadiusFraction: 0.50),
                role: .topSeam
            ),
        ]

        var holds: [BoardHoldPiece] = []

        func addPair(
            leftID: String,
            rightID: String,
            suffix: String,
            leftFrame: CGRect,
            shape: BoardShape,
            treatment: BoardHoldTreatment
        ) {
            holds.append(
                BoardHoldPiece(
                    id: "\(leftID)-\(suffix)",
                    holdID: leftID,
                    frame: leftFrame,
                    shape: shape,
                    treatment: treatment
                )
            )
            holds.append(
                BoardHoldPiece(
                    id: "\(rightID)-\(suffix)",
                    holdID: rightID,
                    frame: leftFrame.mirroredHorizontally,
                    shape: shape.mirroredHorizontally,
                    treatment: treatment
                )
            )
        }

        holds.append(
            BoardHoldPiece(
                id: "sloper-center-upper",
                holdID: "sloper-center",
                frame: CGRect(x: 0.431, y: 0.365, width: 0.136, height: 0.148),
                shape: .roundedRect(cornerRadiusFraction: 0.35),
                treatment: .recess(.deepSlot)
            )
        )

        addPair(
            leftID: "jug-left",
            rightID: "jug-right",
            suffix: "upper-shelf",
            leftFrame: CGRect(x: 0.021, y: 0.245, width: 0.165, height: 0.270),
            shape: outerUpper,
            treatment: .shelf(.broadJug)
        )
        addPair(
            leftID: "jug-left",
            rightID: "jug-right",
            suffix: "lower-shelf",
            leftFrame: CGRect(x: 0.035, y: 0.620, width: 0.160, height: 0.245),
            shape: outerLower,
            treatment: .shelf(.broadJug)
        )

        addPair(
            leftID: "edge-29-left",
            rightID: "edge-29-right",
            suffix: "upper",
            leftFrame: CGRect(x: 0.217, y: 0.365, width: 0.107, height: 0.148),
            shape: .roundedRect(cornerRadiusFraction: 0.40),
            treatment: .recess(.deepSlot)
        )
        addPair(
            leftID: "pocket-4-deep-left",
            rightID: "pocket-4-deep-right",
            suffix: "upper",
            leftFrame: CGRect(x: 0.344, y: 0.370, width: 0.067, height: 0.147),
            shape: .roundedRect(cornerRadiusFraction: 0.44),
            treatment: .recess(.deepSlot)
        )

        addPair(
            leftID: "edge-19-left",
            rightID: "edge-19-right",
            suffix: "lower",
            leftFrame: CGRect(x: 0.228, y: 0.733, width: 0.107, height: 0.140),
            shape: .roundedRect(cornerRadiusFraction: 0.40),
            treatment: .recess(.shallowSlot)
        )
        addPair(
            leftID: "pocket-3-shallow-left",
            rightID: "pocket-3-shallow-right",
            suffix: "lower",
            leftFrame: CGRect(x: 0.348, y: 0.733, width: 0.067, height: 0.140),
            shape: .roundedRect(cornerRadiusFraction: 0.44),
            treatment: .recess(.shallowSlot)
        )
        holds.append(
            BoardHoldPiece(
                id: "sloper-center-lower",
                holdID: "sloper-center-lower",
                frame: CGRect(x: 0.425, y: 0.733, width: 0.150, height: 0.140),
                shape: .roundedRect(cornerRadiusFraction: 0.35),
                treatment: .recess(.shallowSlot)
            )
        )

        return BoardDesign(
            id: BoardCatalog.compactII.id,
            canvasFrame: CGRect(x: 0.025, y: 0.005, width: 0.950, height: 0.965),
            silhouette: silhouette,
            layers: layers,
            holds: holds,
            palette: .sculptedWood
        )
    }()
}
