# Original Tension Grindstone (2017): native CAD source

This migration applies only to `tension-grindstone-original` / `tension.grindstone-original`.
The Mk2 `tension-grindstone` and the separate `tension-grindstone-pro` are unchanged.
The exact twelve existing contact IDs, names, kinds, equipment ownership, grip
lists and depth ranges are preserved. No routines or training cues are added.

## Approved evidence and revision correction

The user approved these exact retained Northern Rocks archival commerce photos
on 2026-09-29. The retired manufacturer image URL was unavailable (404); these
are explicitly commerce evidence, not mislabeled manufacturer photographs.
The source manifest is [original-grindstone-sources.json](2026-09-29-next-three-cad-sources/original-grindstone-sources.json).

| Retained image | Source URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| `tension-climbing-hang-board-grindstone.jpg` | https://www.northernrocks.co.nz/wp-content/uploads/2018/12/tension-climbing-hang-board-grindstone.jpg | `335d5f097153b1da8ca8d53134513680ad12ec02324533c4e4d410efa71e65b5` | Twelve-edge 2/5/5 layout, engraved depths, twin raised upper wings, rounded scalloped rails, through centre opening |
| `tension-climbing-hang-board-grindstone-top.jpg` | https://www.northernrocks.co.nz/wp-content/uploads/2018/12/tension-climbing-hang-board-grindstone-top.jpg | `153f3ca312bf8ac9ead17037ed0c6bd4b5bf462a09c31c7752ddd192a79067a3` | Raised wings, backing and depth tiers, centred top phone slot |
| `tension-climbing-hang-board-grindstone-side.jpg` | https://www.northernrocks.co.nz/wp-content/uploads/2018/12/tension-climbing-hang-board-grindstone-side.jpg | `e644ad4934d0ee9d246611db847cc5554cdacd6a27105acab3b12eeb2e2f6a69` | Recess depth, blind cavity back walls, tier relationship and rounded perimeter |

An older audit incorrectly identified a photograph whose filename ends in
`-pro` as the Original. That photograph is rejected for this migration.
The three images above depict the twelve-edge original, including 30 mm and
50 mm edges that distinguish it from the Pro. There is no pixel tracing,
registration, segmentation, image-derived constraint or mask workflow.

The primary designers' [5 July 2017 interview](https://www.powercompanyclimbing.com/blog/2017/7/5/episode-49-a-better-strip-of-wood-with-tension-climbing)
confirms the original and Pro are distinct, gives the original's 35/30/25/20/15
mm sequence and central 50/22 mm edges in the Grindstone discussion, and explains the top-centre
phone slot (44:48–45:14). These facts were rechecked against the transcript and
the engraved labels in the approved front image.

## Field and geometry mapping

| Source-backed value | Preserved contact IDs / authored behavior |
| --- | --- |
| 35 mm pair | `edge-35-left`, `edge-35-right`: upper inner cavities, 35 mm native pockets |
| 30/25 mm repeated left-to-right sequence | `edge-30-left`, `edge-25-left`, `edge-30-right`, `edge-25-right`: middle row, 30/25 mm native pockets |
| Central 50 mm | `edge-50-center`: centre middle cavity passes through the 50 mm tier; contact is its actual bearing walls, without an invented back wall |
| 20/15 mm repeated left-to-right sequence | `edge-20-left`, `edge-15-left`, `edge-20-right`, `edge-15-right`: bottom row, 20/15 mm native pockets |
| Central 22 mm | `edge-22-center`: centre bottom blind cavity with 22 mm native depth |
| Top phone slot | Utility pocket only; no contact or attachment ID and no training prescription |

The physical layout is symmetric in aperture positions and outer silhouette;
the depth sequence is intentionally repeated left-to-right, rather than
mirrored. The 50 mm opening is visibly through in the approved front photo.
The eleven other contacts have genuine closed back walls. There are no caps
across cavity mouths and no coincident contact overlays.

Overall dimensions remain `Not published by manufacturer`. The 650 × 190 mm
front envelope and 60 mm maximum thickness are **display estimates**, not
published dimensions or measurements of pixels. The top-level historical
aspect ratio remains unchanged; the model presentation ratio is 650/190.
The camera is a display choice looking down by 20 degrees.

All remaining authored dimensions are operator-selected analytic display
estimates: 26 mm backing; 32 mm lower and 50 mm middle tier; 60 mm upper wings;
lower/middle lobe centres at X = −256/−128/0/128/256 mm, Z = 29/92 mm;
138 × 58 mm lobes with 20 mm corner radii; upper wings at X = ±192 mm,
Z = 164 mm, 266 × 52 mm with 19 mm radii; 102 × 28 mm hold apertures with
13 mm radii; 18 mm backing corners; 3 mm outer rounds; 2 mm cavity-lip
chamfers; and a 116 × 12 mm top phone slot with 5 mm corners and a 12 mm
utility cut. These values approximate the approved photographs' shape and
relationships without claiming fabrication accuracy. Lip chamfers approximate
the photographed soft mouth transition. Phone-slot tilt is not dimensioned
by the evidence and is represented with a simple native pocket.

Mounting holes, screws and other mounting hardware are deliberately omitted
from the display model. Engraving and wood grain are omitted; the USDZ is
material-free and texture-free. These display omissions do not imply the
physical board lacks these features.

## Native construction and verification

The source is `Hangboards/tension-grindstone-original/tension-grindstone-original.FCStd`.
The throwaway operator authoring script is
`.context/supreme-zebra-next-cad-grindstone/author.py`; it is not a build input.
The document contains constrained line/arc Sketcher profiles, native
PartDesign pads, pockets, an outer fillet and cavity-mouth chamfer. Twelve
live SubShapeBinders refer to the final body's cavity faces. These bindings
include bearing walls, end walls, lip transitions and each available back
wall, and the standard compiler partitions them out of the body.

No `Part::Feature`, frozen B-rep, imported mesh or Python feature proxy is
used. `set_board_manifest.py` embeds the preserved factual metadata and the
model presentation. The former `board.json` and raster are removed; build-time
metadata comes from the FCStd. Standard compile exports unbound meshes.

The retained regression check is
`Tools/HangboardCAD/tests/original_grindstone_native_source_checks.py`, with
pytest wrapper `test_original_grindstone_native.py`. It reopens and recomputes
the native source, checks all twelve actual depth extents and surface bindings,
asserts through/closed-back topology and the noncontact phone pocket, edits the
left 15 mm Pocket to 17 mm, verifies its live binding and body-volume change,
saves a workspace-owned copy, and repeats the checks after reopening that copy.
It also verifies that the committed source bytes remain unchanged.

Compiler reports and front/side/top comparison images are retained under
`.context/supreme-zebra-next-cad-grindstone/`. The prior asset was raster-only,
so the comparison explicitly shows that historical raster beside three new
orthographic renders; it does not invent prior side/top geometry. App-level
picking, staging, shared suites and delivery-lock refresh belong to the parent
integration pass.

All output is workspace-owned. No HTTP server, simulator, external volume or
other external resource was created by this authoring task.

### Recorded results

Pinned FreeCAD 1.1.3 check and publish both passed, yielding identical model
SHA-256 `9137b9b5620286ccc0c0f7f49c7e4d448037b56ec8f9882090b4779f8d0dba0e`.
The 2,121,055-byte USDZ has 13 unbound meshes and 96,692 triangles; direct USD
inspection found no materials or shaders. Exported bounds are exactly the
estimated 650 × 190 × 60 mm envelope. All twelve measured contact depths
equal their retained nominal facts. Native persisted-edit checks passed.
The FCStd hash after metadata embedding is
`9c7a839a37a00c273a88ed32fc017b7ef13ea818e3276051c271d2c585126c00`.

Both `preview.py` and independent `/usr/bin/usdrecord` renders were inspected.
Hydra front/side/top/three-quarter images show coherent tier geometry, visible
blind cavity backs, the open central 50 mm cavity, and the phone slot in the
angled view. `previews/prior-comparison.png` presents all three orthographic
views beside the prior committed raster. `previews/source-comparison.png`
shows complete approved photographs beside the CAD renders. These comparison
layouts do not crop, align or derive any geometry from source images.
