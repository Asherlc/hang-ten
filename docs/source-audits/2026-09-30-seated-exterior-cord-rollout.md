# Exterior cord evidence and display estimates

This record preserves the source assumptions referenced by the J. Bryant
FTG-32 CAD manifest. It is a source mapping, not an execution log or solver
recipe. Follow the [current cord guide](../HANGBOARD_CORD_AUTHORING.md) for
native authoring and validation.

## Connection graph and dimensions

Manufacturer evidence supports the visible attachment points and entry sides
for Captain Fingerfood DUAL/UNLEVEL, J. Bryant FTG-32, Metolius Light Rail II,
and YY Penta Evo. Unknown hidden connections must remain unknown. Do not add
a knot, an interior join, or a material-length split to make a representation
fit a solver.

The retained cord diameter estimates are 3.6 mm for J. Bryant and 4 mm for
DUAL, UNLEVEL, Light Rail II, and Penta Evo. These are display values, not
measurements inferred from bores or photographs. The
[diameter source mapping](2026-09-29-catalog-cord-diameters.md) records the
manufacturer references and the separately confirmed Clavellium, Mini Bar,
and Helium values. Pose placement, supports, and unsourced cord lengths are
also display estimates.

DUAL, UNLEVEL, and Penta retain native route inputs in
`HangTenSuspensionAuthoring`. J. Bryant and Light Rail II currently retain
legacy `pairedLeadCord` data in `HangTenBoardManifest`; their display caches
do not establish native equilibrium or a newly solved hidden passage.
A revision must use the supported native method and pass its independent
clearance, length, tube, and topology checks.

## Lattice threading evidence

The [Lattice MXEdge Lift setup guide](https://latticetraining.com/app/uploads/2024/05/MXEdge-Lift-Instructions-Artwork-PRINT-READY-28-03-24-PDF.pdf)
and [product page](https://latticetraining.com/product/mxedge-lift/) establish
one continuous cord threaded through both end passages, with an exterior
bridge below the board. Preserve that connection graph instead of inventing
two separate loops. Neither source establishes a numeric bore diameter;
any authored bore size must remain labeled a display estimate.

Both MXEdge Lift sizes currently retain legacy manifest suspension. Their
existing display is not proof of native passage completeness. Native geometry
and routing revisions require source review and the normal before/after
front, side, and top comparisons.
