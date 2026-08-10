import SwiftUI

extension BoardDesign {
    /// Normalized vector artwork for the two-piece Rock Prodigy Training
    /// Center. The pieces are rendered in the manufacturer's default
    /// symmetric side-by-side arrangement.
    static let trangoRockProdigyTrainingCenter: BoardDesign = {
        func pairedPath(_ left: BoardNormalizedPath) -> BoardShape {
            .path(
                BoardNormalizedPath(
                    commands: left.commands + left.mirroredHorizontally.commands
                )
            )
        }

        let leftSilhouette = BoardNormalizedPath(commands: [
            // Main face.
            .move(CGPoint(x: 0.180, y: 0.190)),
            .line(CGPoint(x: 0.405, y: 0.190)),
            .quad(to: CGPoint(x: 0.465, y: 0.245), control: CGPoint(x: 0.450, y: 0.195)),
            .line(CGPoint(x: 0.465, y: 0.675)),
            .quad(to: CGPoint(x: 0.410, y: 0.720), control: CGPoint(x: 0.460, y: 0.710)),
            .line(CGPoint(x: 0.185, y: 0.720)),
            .quad(to: CGPoint(x: 0.145, y: 0.675), control: CGPoint(x: 0.150, y: 0.710)),
            .line(CGPoint(x: 0.145, y: 0.300)),
            .quad(to: CGPoint(x: 0.180, y: 0.190), control: CGPoint(x: 0.150, y: 0.235)),
            .close,
            // Raised top jug.
            .move(CGPoint(x: 0.265, y: 0.100)),
            .line(CGPoint(x: 0.405, y: 0.100)),
            .quad(to: CGPoint(x: 0.415, y: 0.125), control: CGPoint(x: 0.415, y: 0.105)),
            .line(CGPoint(x: 0.415, y: 0.205)),
            .line(CGPoint(x: 0.265, y: 0.205)),
            .close,
            // Upper lower-finger tab.
            .move(CGPoint(x: 0.190, y: 0.675)),
            .line(CGPoint(x: 0.385, y: 0.675)),
            .line(CGPoint(x: 0.385, y: 0.815)),
            .quad(to: CGPoint(x: 0.355, y: 0.845), control: CGPoint(x: 0.380, y: 0.840)),
            .line(CGPoint(x: 0.215, y: 0.845)),
            .quad(to: CGPoint(x: 0.190, y: 0.815), control: CGPoint(x: 0.195, y: 0.840)),
            .close,
            // Lower finger tab.
            .move(CGPoint(x: 0.225, y: 0.805)),
            .line(CGPoint(x: 0.370, y: 0.805)),
            .line(CGPoint(x: 0.370, y: 0.940)),
            .quad(to: CGPoint(x: 0.340, y: 0.970), control: CGPoint(x: 0.365, y: 0.965)),
            .line(CGPoint(x: 0.250, y: 0.970)),
            .quad(to: CGPoint(x: 0.225, y: 0.940), control: CGPoint(x: 0.230, y: 0.965)),
            .close,
            // Outer angled pinch/sloper block.
            .move(CGPoint(x: 0.025, y: 0.290)),
            .line(CGPoint(x: 0.135, y: 0.235)),
            .line(CGPoint(x: 0.185, y: 0.285)),
            .line(CGPoint(x: 0.185, y: 0.445)),
            .line(CGPoint(x: 0.135, y: 0.505)),
            .line(CGPoint(x: 0.045, y: 0.485)),
            .quad(to: CGPoint(x: 0.025, y: 0.290), control: CGPoint(x: 0.025, y: 0.450)),
            .close
        ])

        let pieceFace = BoardShape.path(
            BoardNormalizedPath(commands: [
                .move(CGPoint(x: 0.025, y: 0.040)),
                .line(CGPoint(x: 0.930, y: 0.040)),
                .quad(to: CGPoint(x: 1.000, y: 0.180), control: CGPoint(x: 0.975, y: 0.055)),
                .line(CGPoint(x: 0.985, y: 0.820)),
                .quad(to: CGPoint(x: 0.850, y: 0.975), control: CGPoint(x: 0.975, y: 0.960)),
                .line(CGPoint(x: 0.120, y: 0.975)),
                .quad(to: CGPoint(x: 0.000, y: 0.820), control: CGPoint(x: 0.025, y: 0.960)),
                .line(CGPoint(x: 0.015, y: 0.180)),
                .quad(to: CGPoint(x: 0.025, y: 0.040), control: CGPoint(x: 0.015, y: 0.060)),
                .close
            ])
        )

        let outerBlock = BoardShape.path(
            BoardNormalizedPath(commands: [
                .move(CGPoint(x: 0.270, y: 0.000)),
                .line(CGPoint(x: 0.700, y: 0.070)),
                .curve(
                    to: CGPoint(x: 0.980, y: 0.430),
                    control1: CGPoint(x: 0.920, y: 0.070),
                    control2: CGPoint(x: 0.980, y: 0.230)
                ),
                .line(CGPoint(x: 0.680, y: 0.940)),
                .line(CGPoint(x: 0.220, y: 1.000)),
                .curve(
                    to: CGPoint(x: 0.000, y: 0.380),
                    control1: CGPoint(x: 0.040, y: 0.840),
                    control2: CGPoint(x: 0.000, y: 0.620)
                ),
                .curve(
                    to: CGPoint(x: 0.270, y: 0.000),
                    control1: CGPoint(x: 0.000, y: 0.150),
                    control2: CGPoint(x: 0.120, y: 0.030)
                ),
                .close
            ])
        )

        let layers: [BoardLayer] = [
            BoardLayer(
                frame: CGRect(x: 0.145, y: 0.185, width: 0.320, height: 0.535),
                shape: pieceFace,
                role: .faceLight
            ),
            BoardLayer(
                frame: CGRect(x: 0.190, y: 0.675, width: 0.195, height: 0.170),
                shape: .roundedRect(cornerRadiusFraction: 0.15),
                role: .faceLight
            ),
            BoardLayer(
                frame: CGRect(x: 0.225, y: 0.805, width: 0.145, height: 0.165),
                shape: .roundedRect(cornerRadiusFraction: 0.18),
                role: .bottomPlane
            ),
            BoardLayer(
                frame: CGRect(x: 0.025, y: 0.235, width: 0.160, height: 0.270),
                shape: outerBlock,
                role: .shelf
            ),
            BoardLayer(
                frame: CGRect(x: 0.265, y: 0.100, width: 0.150, height: 0.105),
                shape: .roundedRect(cornerRadiusFraction: 0.10),
                role: .shelf
            ),
            BoardLayer(
                frame: CGRect(x: 0.495, y: 0.180, width: 0.010, height: 0.790),
                shape: .roundedRect(cornerRadiusFraction: 0.50),
                role: .separator
            )
        ] + [
            BoardLayer(
                frame: CGRect(x: 0.535, y: 0.185, width: 0.320, height: 0.535),
                shape: pieceFace.mirroredHorizontally,
                role: .faceLight
            ),
            BoardLayer(
                frame: CGRect(x: 0.615, y: 0.675, width: 0.195, height: 0.170),
                shape: .roundedRect(cornerRadiusFraction: 0.15),
                role: .faceLight
            ),
            BoardLayer(
                frame: CGRect(x: 0.630, y: 0.805, width: 0.145, height: 0.165),
                shape: .roundedRect(cornerRadiusFraction: 0.18),
                role: .bottomPlane
            ),
            BoardLayer(
                frame: CGRect(x: 0.815, y: 0.235, width: 0.160, height: 0.270),
                shape: outerBlock.mirroredHorizontally,
                role: .shelf
            ),
            BoardLayer(
                frame: CGRect(x: 0.585, y: 0.100, width: 0.150, height: 0.105),
                shape: .roundedRect(cornerRadiusFraction: 0.10),
                role: .shelf
            )
        ]

        var holds: [BoardHoldPiece] = []
        func addPair(
            leftID: String,
            rightID: String,
            suffix: String,
            frame: CGRect,
            shape: BoardShape,
            treatment: BoardHoldTreatment
        ) {
            holds.append(
                BoardHoldPiece(
                    id: "\(leftID).\(suffix)",
                    holdID: leftID,
                    frame: frame,
                    shape: shape,
                    treatment: treatment
                )
            )
            holds.append(
                BoardHoldPiece(
                    id: "\(rightID).\(suffix)",
                    holdID: rightID,
                    frame: frame.mirroredHorizontally,
                    shape: shape.mirroredHorizontally,
                    treatment: treatment
                )
            )
        }

        let leftIDs = [
            "trango.rptc.left.top-jug",
            "trango.rptc.left.large-open-rail",
            "trango.rptc.left.small-crimp-rail",
            "trango.rptc.left.three-finger-slot",
            "trango.rptc.left.thin-crimp",
            "trango.rptc.left.deep-mr-pocket",
            "trango.rptc.left.shallow-mr-pocket",
            "trango.rptc.left.medium-im-pocket",
            "trango.rptc.left.shallow-im-pocket",
            "trango.rptc.left.wide-pinch",
            "trango.rptc.left.medium-pinch",
            "trango.rptc.left.small-pinch",
            "trango.rptc.left.sloper"
        ]
        let rightIDs = leftIDs.map { $0.replacingOccurrences(of: ".left.", with: ".right.") }

        addPair(leftID: leftIDs[0], rightID: rightIDs[0], suffix: "surface", frame: CGRect(x: 0.270, y: 0.100, width: 0.145, height: 0.105), shape: .roundedRect(cornerRadiusFraction: 0.10), treatment: .shelf(.broadJug))
        addPair(leftID: leftIDs[1], rightID: rightIDs[1], suffix: "rail", frame: CGRect(x: 0.205, y: 0.275, width: 0.235, height: 0.060), shape: .roundedRect(cornerRadiusFraction: 0.32), treatment: .recess(.deepSlot))
        addPair(leftID: leftIDs[2], rightID: rightIDs[2], suffix: "rail", frame: CGRect(x: 0.205, y: 0.365, width: 0.235, height: 0.055), shape: .roundedRect(cornerRadiusFraction: 0.32), treatment: .recess(.shallowSlot))
        addPair(leftID: leftIDs[3], rightID: rightIDs[3], suffix: "slot", frame: CGRect(x: 0.235, y: 0.465, width: 0.135, height: 0.080), shape: .roundedRect(cornerRadiusFraction: 0.38), treatment: .recess(.deepSlot))
        addPair(leftID: leftIDs[4], rightID: rightIDs[4], suffix: "crimp", frame: CGRect(x: 0.315, y: 0.605, width: 0.105, height: 0.040), shape: .roundedRect(cornerRadiusFraction: 0.20), treatment: .recess(.shallowSlot))
        addPair(leftID: leftIDs[5], rightID: rightIDs[5], suffix: "pocket", frame: CGRect(x: 0.195, y: 0.705, width: 0.095, height: 0.055), shape: .roundedRect(cornerRadiusFraction: 0.45), treatment: .recess(.deepSlot))
        addPair(leftID: leftIDs[6], rightID: rightIDs[6], suffix: "pocket", frame: CGRect(x: 0.225, y: 0.835, width: 0.095, height: 0.055), shape: .roundedRect(cornerRadiusFraction: 0.45), treatment: .recess(.shallowSlot))
        addPair(leftID: leftIDs[7], rightID: rightIDs[7], suffix: "pocket", frame: CGRect(x: 0.320, y: 0.705, width: 0.095, height: 0.055), shape: .roundedRect(cornerRadiusFraction: 0.45), treatment: .recess(.deepSlot))
        addPair(leftID: leftIDs[8], rightID: rightIDs[8], suffix: "pocket", frame: CGRect(x: 0.320, y: 0.835, width: 0.095, height: 0.055), shape: .roundedRect(cornerRadiusFraction: 0.45), treatment: .recess(.shallowSlot))

        let outerFrame = CGRect(x: 0.025, y: 0.245, width: 0.160, height: 0.245)
        for index in 9..<leftIDs.count {
            addPair(
                leftID: leftIDs[index],
                rightID: rightIDs[index],
                suffix: "outer-contact",
                frame: outerFrame,
                shape: outerBlock,
                treatment: .surface
            )
        }

        return BoardDesign(
            id: BoardCatalog.rockProdigyTrainingCenter.id,
            canvasFrame: CGRect(x: 0.015, y: 0.020, width: 0.970, height: 0.960),
            silhouette: pairedPath(leftSilhouette),
            layers: layers,
            holds: holds,
            palette: .sculptedWood
        )
    }()
}
