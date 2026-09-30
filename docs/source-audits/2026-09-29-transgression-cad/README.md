# Transgression source and field audit — 2026-09-29

The user approved these exact four retained images, separately identifying the
2011 polyester and 2013 polyurethane Transgression revisions, before geometry
was authored. Original bytes and source/image URLs with SHA-256 digests are in
`sources.json`. The photographs are retained for source audit and human review;
they are never package media, rendering inputs, or geometry tracing inputs.

## Retained evidence

| Revision | Image | Publisher and role | Evidence |
| --- | --- | --- | --- |
| 2011 polyester | `designer-1.jpg` | Eva López, original product designer | Oblique installed original marbled board: projecting continuous ribs, top jug, open rear shell and mounting flanges. |
| 2011 polyester | `designer-2.jpg` | Eva López, original product designer | Original front detail: eight descending depth engravings. |
| 2013 polyurethane | `pu-review-1.jpg` | Kris Hampton / Power Company Climbing, secondary reviewer | Confirmed newer polyurethane sample, full front, same eight continuous edges and top jug. |
| 2013 polyurethane | `pu-review-0.jpg` | Kris Hampton / Power Company Climbing, secondary reviewer | Oblique newer sample detail showing rounded contact edges. |

The reviewer explicitly identifies the newer manufacturing material. These
secondary views fill the missing confirmed polyurethane angles in the primary
designer publication; they are not manufacturing drawings.

## Field mappings

Primary designer article:
https://en-eva-lopez.blogspot.com/2012/04/transgression-fingerboard-for-high.html

Secondary reviewed polyurethane sample:
https://www.powercompanyclimbing.com/blog/2014/06/review-transgression-hangboard-and.html

| Embedded manifest field or authored representation | Source and interpretation |
| --- | --- |
| `manufacturer: JM Climbing Surfaces` | Designer article credits the collaboration with JM Climbing Surfaces and Dafnis. Eva López is the designer. Current Surfaces for Climbing branding is represented in the stable package prefix; this field preserves the historical maker. |
| Product name `Transgression` | Designer article and lettering in the retained front views. |
| Name revision suffix and `revisionID` | Designer states first polyester version was released in 2011 and the polyurethane version in 2013. |
| `subtitle: Eight continuous edges and a top jug.` | Physical inventory in the retained front and oblique images. This describes objects, without exercise prescriptions. |
| `productURL` | Primary designer article above, shared by both revisions. |
| Contacts `edge-18`, `edge-14`, `edge-12`, `edge-10`, `edge-9`, `edge-8`, `edge-7`, `edge-6`; exact depths in mm | Designer product explanation and original engraved front inventory, corroborated by the newer front. Descending top-to-bottom physical inventory. Each spans the board as one physical contact, with no invented left/right pairing. |
| `jug-top`, name `Top jug`, kind `jug` | Continuous upper jug visible in retained oblique and front views. Its CAD dimensions are display estimates; no factual depth is declared. |
| `gripTypes: []` for every contact | Grip prescriptions are intentionally absent; no training routine or finger cue is introduced. |
| One `equipmentObjects` entry, one primary presentation, default original derivation | Application identity and presentation structure for one physical board, not manufacturer metadata. |
| Model paths, camera, padding `0.08`, aspect ratio `1.35`, contact IDs | Application/display choices. Aspect ratio is the estimated 540/400 display envelope, not a sourced physical specification. |
| 2013 lips rounder than 2011 | Designer explicitly states newer edges are somewhat more rounded. The numeric 1/2 mm radii are operator-selected display estimates, not published radii. |
| Rear concavity and projecting upper/lower shell flanges | Visible in the original designer oblique. Shared broad shell topology is an explicitly labeled adaptation to the newer revision because its retained front/detail do not expose the rear. |

## Limits and exclusions

No primary overall envelope was verified. Both revisions use the same estimated
540 × 400 × 150 mm display envelope; `dimensions` is omitted from both manifests.
The newer review reports 23.5 × 16 × 6 inches (596.9 × 406.4 × 152.4 mm), which
conflicts with other commerce listings. The 2013-11-07
[Alpinsport Basis article](https://www.alpinsport-basis-blog.de/fingerkraft-mit-system-die-trainingsboards-progression-und-transgression-von-jm-climbing/)
reports 40 × 54 × 15 cm for the polyester board and separately 40 × 68 cm for
its backing board. The [Bergfreunde polyurethane listing](https://www.bergfreunde.de/surfaces-for-climbing-transgression-trainingsboard/)
reports 50 × 38 cm and 15 cm depth. The chosen shared display envelope uses the
older commerce figure only as an estimated size context. It is retained as secondary context,
not promoted to factual dimensions. No unseen revision-specific silhouette
change is invented.

`designer-4.jpg` from the original research is expressly excluded: the pictured
board is engraved PROGRESSION and has Progression's inventory. No Progression
measurements or holds were transferred. Mounting holes, screws, backing board,
lettering, logos, texture and marbling are omitted from display geometry. The
physical board does have mounting features; those omissions follow display
policy and are not a product claim. See the complete numeric and native CAD
provenance in `../../2026-09-29-transgression-cad-provenance.md`.

See [integration validation and final review images](validation.md).
