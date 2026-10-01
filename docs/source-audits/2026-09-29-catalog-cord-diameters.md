# Cord diameter evidence across the represented catalog

Audit date: 2026-09-29. The operator's latest instruction supersedes the prior
threefold thickness request: use documented real cord diameters where available
and label unknown sizes as estimates. Clavellium and Mini Bar both remain at
the operator-confirmed 7 mm diameter.

This inventory covers 15 corded products / 17 represented setups. Diameters
are in millimetres. An estimate records an existing authored display value;
it is not a manufacturer specification, pixel measurement, or a size inferred
from a bore. No general threefold multiplier applies to these values.

| Package | Selected diameter | Evidence status |
| --- | ---: | --- |
| `captain-fingerfood-dual` | 4 mm | display estimate |
| `captain-fingerfood-pocket` | 4 mm | display estimate |
| `captain-fingerfood-unlevel` | 4 mm | display estimate |
| `clavellium-training-block` | 7 mm | owner-confirmed |
| `crimptonite-helium-mobile` | 4 mm | manufacturer-published |
| `j-bryant-ftg-32` | 3.6 mm | display estimate |
| `lattice-mini-bar` | 7 mm | owner-confirmed |
| `lattice-mxedge-lift-large` | 4 mm | display estimate |
| `lattice-mxedge-lift-small` | 4 mm | display estimate |
| `metolius-light-rail-2` | 4 mm | display estimate |
| `metolius-rock-rings-3d` | 4 mm | display estimate |
| `nature-stone-hanger` | 4 mm | display estimate |
| `tension-flash-board` | 4 mm | display estimate |
| `yy-baguette-evo` | 4 mm | display estimate |
| `yy-penta-evo` | 4 mm | display estimate |

## Sourced sizes

Clavellium and Mini Bar use the operator's explicit 7 mm confirmation for
both boards. Clavellium retains its documented round-cord adaptation of the
photographed flat sling. Its historical static suspension used a
4 mm display baseline; the shipped static suspension now has radius 3.5 mm
(7 mm diameter). The delivered live physics profile also selects 7 mm using
baseline radius 2 mm and scale 1.75. This baseline is not a separate measured
cord size. Mini Bar's static suspension and candidate physics both select
7 mm. The Mini Bar 7.4 mm CAD bore is an explicitly labeled display estimate,
not a measured factory bore.

[Crimptonite's Helium Mobile page](https://crimptonite.com/product/helium-mobile/)
explicitly identifies the supplied Beal 4 mm cord. Both retained branch
metadata radii are 2 mm. Its two branch budgets describe halves of one
continuous loop; they must not be converted into two independent physical
cords during live migration. Total loop length and the 7 mm CAD bore remain
display estimates.

## Unknown sizes

The selected estimate is twice the currently authored radius, converted from
metres to millimetres. Native packages were read through `generate_board_json`
from their FCStd manifest and suspension sidecar; legacy packages were read
from their canonical `board.json`. Existing provenance already marks these
values as display estimates. Paired Rock Rings and Penta units share their
product's diameter estimate.

Manufacturer evidence checked for the rollout includes the
[Captain DUAL](https://en.captainfingerfood.rocks/products/dual-hangboard),
[POCKET](https://en.captainfingerfood.rocks/products/lines-hangboard), and
[UNLEVEL](https://en.captainfingerfood.rocks/products/unlevel-hangboard) pages;
the [Lattice catalogue](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf);
[Light Rail](https://www.metoliusclimbing.com/products/light-rail),
[Rock Rings](https://www.metoliusclimbing.com/collections/training-equipment/products/rock-rings-3d),
[Stone Hanger](https://natureclimbing.com/products/stone-hanger-1),
[Flash Board](https://tensionclimbing.com/products/flash-board-2),
[Baguette Evo](https://www.yyvertical.com/en/products/baguette-evo), and
[Penta Evo](https://www.yyvertical.com/en/products/penta-evo).
No numeric cord diameter was established for these entries from the checked
material. Published rope lengths, material names, grip sizes and bore widths
do not establish cord diameter. J. Bryant retains its explicitly authored
3.6 mm estimate; its listing does not supply a retained numeric diameter fact.
New verified manufacturer evidence or an owner measurement supersedes an
estimate when available.

This evidence inventory does not promote a pending board to live simulation.
The source collider, continuous connection graph, diameter fit, numerical
settling, native visuals and runtime performance gates still apply separately.
