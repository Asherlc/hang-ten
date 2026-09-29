# CAD plastic appearance

The user selected a playful mint matte finish after reviewing gray, ivory, mint,
lilac and yellow visual concepts. Mint is an artistic app display color, not
a claim about a manufacturer colorway. The molded-surface cue is a subtle
non-directional procedural stipple; it has no wood bands or image texture.

The native manifests select exact body/contact descriptor nodes through
`media.display.plasticNodeIDs`. Attachments, cords and unselected stone surfaces
retain their existing appearance. `woodNodeIDs` and `plasticNodeIDs` must be
unique, known, nonattachment and disjoint. Missing selectors retain neutral PBR.
The renderer contains no product IDs. Both selectors propagate through unnamed
imported mesh children and the full baseline is restored after active or preview
highlighting. A mint matte PBR fallback handles unavailable custom shaders.

USDZs remain unbound and material-free. Only the embedded manifest property
changes in each FCStd; all other archive members, geometry, descriptor and cord
metadata remain unchanged. Native metadata is updated with
`Tools/HangboardCAD/set_board_manifest.py`, never a committed `board.json`.

## Surface selection evidence

Reviewed 2026-09-29. The following existing package identities and retained
manufacturer evidence govern material grouping. The sources support the
manufactured plastic/resin category, not the chosen mint color or exact physical
surface roughness. Exact nodes come from each package's current CAD descriptor;
all body/contact nodes receive the finish, attachment-role nodes are excluded.

| CAD package | Manufacturer evidence | Retained material grouping |
| --- | --- | --- |
| `clavellium-training-block` | [Product source](https://www.etsy.com/listing/1740404071) | PETG (retained package subtitle; current seller page unavailable) |
| `escape-beta-22` | [Product source](https://escapeclimbing.com/products/ec72100) | Molded plastic/resin |
| `evolv-kilter-basic-long` | [Product source](https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105) | Molded plastic/resin |
| `metolius-foundry` | [Product source](https://www.metoliusclimbing.com/products/foundry-training-board) | Molded plastic/resin |
| `metolius-project` | [Product source](https://www.metoliusclimbing.com/products/project-training-board) | Molded plastic/resin |
| `metolius-rock-rings-3d` | [Product source](https://www.metoliusclimbing.com/collections/training-equipment/products/rock-rings-3d) | Molded plastic/resin |
| `soill-iron-palm-2` | [Product source](https://soillholds.com/products/iron-palm-2-0) | Molded plastic/resin |
| `soill-split-palm` | [Product source](https://soillholds.com/products/split-palm) | Molded plastic/resin |
| `soill-training-tiles` | [Product source](https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin) | Molded plastic/resin |
| `trango-rock-prodigy-pivot` | [Product source](https://trango.com/products/rock-prodigy-pivot?variant=33101615890537) | Molded plastic/resin |
| `trango-rock-prodigy-training-center` | [Product source](https://trango.com/products/rock-prodigy-training-center) | Molded plastic/resin |

The former Training Tiles Canada URL currently redirects to Iron Palm, so it
is not fresh proof of Training Tiles. Its previously retained package evidence
and the manufacturer Training Tiles page govern this grouping. Metolius
Foundry/Project/Rock Rings, Escape Beta and Trango retain their already-audited
manufactured-surface classification; no specific polymer chemistry is asserted.

## Validation

Package tests cover explicit selectors, invalid values and conflicting finishes.
iOS tests cover package decoding, selector rejection, plastic highlight/restore,
wood highlight/restore and mixed wood/granite surfaces. Review app-rendered mint
boards at detail and thumbnail size on a workspace-owned simulator.
