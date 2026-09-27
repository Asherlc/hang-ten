# Lattice Mini Bar CAD migration provenance

Reviewed 2026-09-26. The canonical source is
`Hangboards/lattice-mini-bar/lattice-mini-bar.FCStd`. Its document-level
`HangTenBoardManifest` generates `board.json`; the package has one unbound USDZ
and descriptor. The temporary authoring script is
`.context/frantic-kiwi/author_mini_bar.py` (SHA-256
`714eb6f61ec247c2f0acc18e212b3b4529a114fded42bf861d4f9d8a8ec6f5ad`)
and is not a build input. The saved FreeCAD sketch, pad, and surface regions
stand alone.

## Exact revision and retained evidence

The [current Lattice product page](https://latticetraining.com/product/mini-bar-portable-hangboard/)
names the 10 mm edge, 20 mm edge, ergonomic jug, and mini pinch, says the bar is
15.5 cm long and made from tulipwood, and describes flipping the bar and
adjusting its rope angle. Its technical table rounds the box to 6 × 6 × 15 cm;
that is not used as a precise section drawing. The
[Lattice catalogue, page 8](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf)
corroborates the four contacts and 15.5 cm length. The previously audited
[presentation evidence](2026-08-29-lattice-mini-bar-presentation-assets.md)
identifies the current one-piece asymmetric section and contact views.

The user approved the exact Lattice Web-1, Web-2, Web-7, Web-8, Web-9, Web-10,
and Web-11 gallery URLs before CAD authoring, then approved two pose-specific
exterior wrapped cord loops. Current downloads of six URLs differ in hash from
the August audit; the visible photographs remain the same revision. Their
current bytes are retained in
`docs/source-audits/2026-09-13-model-cord-snapshots/lattice-mini-bar-Web-*.jpg`,
with exact URLs, SHA-256 hashes, and the approval recorded in
`2026-09-13-model-hangboard-cord-audit.json`. The product page snapshot is
retained there as `lattice-mini-bar-product.html` (SHA-256
`f2294055f6a19e506aeb6a7d0ea600be5d8ff472ee8167639b12d0ffcbc8b1ff`).
Web-1 and Web-2 establish the one-piece bar, flat ends, asymmetric through
relief, and loops near both ends. Web-7 and Web-8 show the respective edge
uses; Web-9 shows the end section and pinch orientation; Web-10 shows rotated
edge use; Web-11 shows jug use. These are distinct visual views of this revision.

## Authored geometry and metadata mapping

The 155 mm length is the published product fact. The end profile is a directly
authored, fully constrained FreeCAD sketch of three circular exterior arcs,
one arc at the open concavity, and straight shoulder runs. It is a display
approximation drawn from the approved photos, not traced from pixels or claimed
as manufacturing geometry. Its exported bounds are about 155 × 60 × 63 mm
after coordinate conversion; the approximately 6 cm section agrees only with
the rounded technical-table size. The pad and contact surface extrusions remain
editable FreeCAD features. The flat 10 and 20 mm shoulder runs measure exactly
10 and 20 mm along the native depth axis. Their IDs and source claims are
preserved from the preceding package. The concavity surface is `mini-pinch`;
the rounded exterior run is `ergonomic-jug`. The four contact names, kinds,
hand capacity, grip depth fields, and revision ID are otherwise preserved.

The four former raster presentations become one model presentation with four
positions. The edge and jug pose angles and pinch camera direction are
`displayEstimate` values chosen to expose the sourced grip surfaces. No
additional grip, training cue, or performance claim was inferred.

The gallery shows four hanging strands and an exterior bight around each end.
The representation therefore has two ordered exterior branch routes on the
same body node. Each canonical pose supplies its own `wrappedRoutes` in
unposed importer coordinates. These route points, 2 mm tube radius, 180 mm
anchor offset, and 0.75 m per-branch rendering capacity are display estimates.
Retailers [Needle Sports](https://www.needlesports.com/Catalogue/Climbing/Bouldering-Training-Sport/Training-Equipment/Lattice-Mini-Bar-LAT-MINIBAR)
and [Bananafingers](https://bananafingers.co.uk/lattice-mini-bar-portable-fingerboard)
report 1.5 m of included rope; that is a total product length, not a measured
0.75 m physical loop. The rendering capacity is the illustrative half-total
and exceeds the resolved path in all four poses. The route does not assert
independent physical cords, a bore, an unseen knot path, or a safety property.
The cord stays transient, unbound to picking, and outside the USDZ.

The prior committed raster views are used only for the three-view visual
comparison at `.context/frantic-kiwi/mini-bar-preview/cad-vs-prior.png`; they
were not geometry inputs. Mounting hardware and a rendered knot are omitted
from the display model. The product photographs show cord hardware but do not
give a reliable construction path for the knot.
