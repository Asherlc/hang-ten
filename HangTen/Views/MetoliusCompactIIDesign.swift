import SwiftUI

enum BoardDesignCatalog {
    static func design(for boardID: String) -> BoardDesign? {
        designs[boardID]
    }

    private static let designs: [String: BoardDesign] = {
        let result: [String: BoardDesign] = [
            BoardCatalog.compactII.id: .metoliusCompactII,
            BoardCatalog.rockProdigyTrainingCenter.id: .trangoRockProdigyTrainingCenter
        ]

        #if DEBUG
        for board in BoardCatalog.all {
            guard let design = result[board.id] else { continue }
            let modelHoldIDs = Set(board.holds.map(\.id))
            let renderedHoldIDs = Set(design.holds.map(\.holdID))
            assert(
                modelHoldIDs == renderedHoldIDs,
                "Board hold metadata and rendered geometry differ for \(board.id)"
            )
        }
        #endif

        return result
    }()
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

        // The Compact II's outer jugs are the rounded top caps, not the
        // horizontal side rails beneath them. This path follows the visible
        // cap and is clipped to the board silhouette by the shared renderer.
        let outerJugTop = BoardShape.path(
            BoardNormalizedPath(commands: [
                .move(CGPoint(x: 0.36, y: 0.00)),
                .line(CGPoint(x: 0.88, y: 0.00)),
                .curve(
                    to: CGPoint(x: 1.00, y: 0.18),
                    control1: CGPoint(x: 0.96, y: 0.00),
                    control2: CGPoint(x: 1.00, y: 0.08)
                ),
                .line(CGPoint(x: 1.00, y: 0.93)),
                .line(CGPoint(x: 0.18, y: 0.93)),
                .curve(
                    to: CGPoint(x: 0.00, y: 0.46),
                    control1: CGPoint(x: 0.07, y: 0.88),
                    control2: CGPoint(x: 0.00, y: 0.67)
                ),
                .curve(
                    to: CGPoint(x: 0.36, y: 0.00),
                    control1: CGPoint(x: 0.00, y: 0.16),
                    control2: CGPoint(x: 0.15, y: 0.01)
                ),
                .close
            ])
        )

        let layers: [BoardLayer] = [
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
            )
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

        addPair(
            leftID: "jug-left",
            rightID: "jug-right",
            suffix: "top-cap",
            leftFrame: CGRect(x: 0.000, y: 0.000, width: 0.165, height: 0.255),
            shape: outerJugTop,
            treatment: .surface
        )

        addPair(
            leftID: "sloper-flat-left",
            rightID: "sloper-flat-right",
            suffix: "top-surface",
            leftFrame: CGRect(x: 0.158, y: 0.035, width: 0.190, height: 0.128),
            shape: .roundedRect(cornerRadiusFraction: 0.025),
            treatment: .surface
        )
        holds.append(
            BoardHoldPiece(
                id: "sloper-round-center-surface",
                holdID: "sloper-round-center",
                frame: CGRect(x: 0.352, y: 0.035, width: 0.296, height: 0.128),
                shape: .roundedRect(cornerRadiusFraction: 0.025),
                treatment: .surface
            )
        )

        addPair(
            leftID: "edge-29-left",
            rightID: "edge-29-right",
            suffix: "upper-side-rail",
            leftFrame: CGRect(x: 0.021, y: 0.245, width: 0.165, height: 0.270),
            shape: outerUpper,
            treatment: .shelf(.broadJug)
        )

        addPair(
            leftID: "pocket-29-three-left",
            rightID: "pocket-29-three-right",
            suffix: "upper",
            leftFrame: CGRect(x: 0.199, y: 0.365, width: 0.109, height: 0.148),
            shape: .roundedRect(cornerRadiusFraction: 0.40),
            treatment: .recess(.deepSlot)
        )
        addPair(
            leftID: "pocket-29-two-left",
            rightID: "pocket-29-two-right",
            suffix: "upper",
            leftFrame: CGRect(x: 0.328, y: 0.370, width: 0.077, height: 0.147),
            shape: .roundedRect(cornerRadiusFraction: 0.44),
            treatment: .recess(.deepSlot)
        )
        holds.append(
            BoardHoldPiece(
                id: "pocket-29-four-center-upper",
                holdID: "pocket-29-four-center",
                frame: CGRect(x: 0.425, y: 0.365, width: 0.150, height: 0.148),
                shape: .roundedRect(cornerRadiusFraction: 0.35),
                treatment: .recess(.deepSlot)
            )
        )

        addPair(
            leftID: "edge-19-left",
            rightID: "edge-19-right",
            suffix: "lower-side-rail",
            leftFrame: CGRect(x: 0.035, y: 0.620, width: 0.160, height: 0.245),
            shape: outerLower,
            treatment: .shelf(.broadJug)
        )
        addPair(
            leftID: "pocket-19-three-left",
            rightID: "pocket-19-three-right",
            suffix: "lower",
            leftFrame: CGRect(x: 0.216, y: 0.733, width: 0.104, height: 0.140),
            shape: .roundedRect(cornerRadiusFraction: 0.40),
            treatment: .recess(.shallowSlot)
        )
        addPair(
            leftID: "pocket-19-two-left",
            rightID: "pocket-19-two-right",
            suffix: "lower",
            leftFrame: CGRect(x: 0.336, y: 0.733, width: 0.073, height: 0.140),
            shape: .roundedRect(cornerRadiusFraction: 0.44),
            treatment: .recess(.shallowSlot)
        )
        holds.append(
            BoardHoldPiece(
                id: "pocket-19-four-center-lower",
                holdID: "pocket-19-four-center",
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
