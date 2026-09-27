# Trango Rock Prodigy Training Center CAD provenance

Date: 2026-09-26. The canonical source is
`Hangboards/trango-rock-prodigy-training-center/trango-rock-prodigy-training-center.FCStd`.
Its document manifest is the previously reviewed `board.json`; the latter is
generated during package staging and is not committed. A temporary authoring
script and measurement images live under `.context/quiet-bedbug/` and are not
build inputs. The saved FCStd contains the editable sketches and operations.

## Evidence and interpretation

| Evidence | Retained hash / location | Supports |
| --- | --- | --- |
| [Trango product page](https://trango.com/products/rock-prodigy-training-center), including its [main photo](https://trango.com/cdn/shop/files/22830_Rock_Prodigy_Training_Center_Main_Image.jpg?v=1737728750) | Product HTML SHA-256 `a79689cf96b7b15248dbbf076829aab0ac03625c8e100ff4a79e911352957910`; photo at `docs/source-audits/2026-09-13-model-cord-snapshots/trango-rock-prodigy-training-center-main.jpg`, SHA-256 `8293f7bd2c2517f8fda72d7ad678671cc801cd7d31fecd4e20ee42eea7170ebf` | Exact product identity, two symmetric halves, visible front layout and contact topology. The page lists 9.1 × 12.1 in per half. |
| [Trango mounting instructions](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Mounting_Instructions_no_screws_v2.pdf?v=1587749856) | SHA-256 `d77bd227b0bada32ebbc940cb9066f1e1cc51b46e8a80259f4a56c7deb338121` | Rounded grip guidance and adjustable half spacing; no hold-depth drawing. |
| [Trango use instructions](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155) | SHA-256 `9800be405e9aa58fd8d9bd1fefbf9ac5bcd738baaa344c6af084fbf98a44465c`; existing [source audit](2026-08-27-rptc-use-instructions.md) | Named grip/contact identity; no manufacturing geometry. |
| Prior committed USDZ at `HEAD` before this migration | SHA-256 `9b9fbeda3846f72bd671fdb0733f2ce39c69342c033933ce75653a67a060f105` | Approved display mesh used as a dimensional reference for a native CAD approximation. |

The product photo and the use/mounting documents are distinct manufacturer
views of this revision. The page provides the overall per-half size. No
manufacturer side drawing or hold-depth schedule was found, so depth and
sculpted sections are **display estimates measured from the prior approved
mesh**, not published physical dimensions. The front photo was used for visual
comparison only; no geometry was extracted from pixels. Mounting holes and
hardware are omitted from the display source.

## Authoring map

The left half's silhouette is a rounded Sketcher profile. Three depth levels
form the base plate and two stepped tiers. Separate sketches and native
extrusions/lofts/cuts construct the jug hook, sloper, variable rails, crimp,
slot, four finger pockets, and angled pinch blocks. Contact shells are explicit
regions of those authored solids. The right half is a FreeCAD mirror of the
left across X = 0. The source exports one body node and the same 24 physical
contact IDs as the original package. All sketches and cutters are editable in
the saved document; there is no faceted mesh import.

The native frame is millimetres, +X right, +Z up, front -Y. The prior asset's
measured per-half envelope is about 307 × 231 mm, close to the published
12.1 × 9.1 in (307.34 × 231.14 mm). The approved mesh set the plate/tier front
planes at -50/-41/-32 mm, with the frontmost jug near -101 mm. Cross-sections
and depth maps of that USDZ were measured under `.context/quiet-bedbug/` to
choose sketch radii, Bézier controls, rail and pocket boundaries, and pinch
angle. These values are modeling approximations, not new grip prescriptions.
The FCStd and its embedded manifest are the only sources used at build time.

## Review

The migrated front, side, and top renderings were compared with the prior
committed USDZ in workspace-owned side-by-side images under
`.context/quiet-bedbug/prev1/`. The oblique comparison is at
`.context/quiet-bedbug/{new3q,ref3q}.png`. The migrated source SHA-256 is
`de2ce4db5f7d84dfdf92c0b4024ce787c34bfbb918202cb81f12a776222e1872`;
the compiled USDZ SHA-256 is
`f55ee5cc3c390a1b4268c41bf14ed0d92a991eb28acc9d3519595a059295dc64`.
The compiler reports 162,804 triangles and 24 contact IDs. It reopened the
source without modifying it. An additional FreeCAD reopen found 31 fully
constrained sketches, one body node, 24 contact nodes, and no imported mesh
objects. Package validation and Android staging passed; staged `board.json`
and USDZ bytes match the generated manifest and shipped asset. The pinned
macOS compiler rebuilt the USDZ and descriptor byte-identically. USDZ
inspection found 25 meshes, no material bindings, no materials, and no
textures. An isolated iPhone 17 Pro simulator build succeeded on the first
revision; its board-detail
screen rendered the migrated asset and highlighted the left deep middle-ring
pocket. A right-pinch deep link was also attempted, but its captured frame
still showed the default left jug, so that selection is unverified. Each
dedicated simulator was deleted after review. The final bore-removal revision
also built successfully, but `simctl launch` stalled before the app process
started; the owned simulator and DerivedData were removed by the cleanup trap.
There is no final-revision app screenshot.
