# YY Baguette Evo rounded cavity terminations — 2026-10-01

Starting source is the actual package FCStd copied byte-for-byte to `before.FCStd`; no source reconstruction, mesh fitting, pixel measurement, or package mutation was performed. Final candidate: `rounded-partitioned.FCStd`. Intermediate `rounded.FCStd` has overlapping shallow/deep floor contacts and is **not** the delivery candidate.

## Evidence and estimates

The retained, previously approved manufacturer evidence set lives at `docs/source-audits/2026-09-29-remaining-cad/yy-baguette-evo/evidence`; exact source URLs and hashes are retained in the adjacent `source-register.json`. Whole source `yy-baguette-evo-image.webp` shows curved outside ends on the long front cavities and a curved internal termination of the deeper stepped cut. Whole `YY_BAGUETTE_EVO_03_FG.webp` shows rounded central rear-cavity termination; whole `YY_BAGUETTE_EVO_07_FG.webp` corroborates rounded top and central recess outlines. The old display mesh was reviewed only as comparative evidence, not used to infer dimensions for this correction.

The 9 mm end radius on front/back recesses and 8.5 mm end radius on top recesses are deliberately selected analytic **display estimates**, not manufacturer dimensions. Their purpose is to represent the evidenced rounded end form within the already authored 20 mm and 18 mm opening widths. They are editable in each native Part::Fillet's `Edges` property, and each feature carries `RadiusProvenance`. The 2.5 mm front lip roundover is retained.

## Native history

Ten native `Part::Fillet` features round the four appropriate end-plane tool edges of the ten existing cavity extrusions. The original YZ section sketches, floor levels, bore features, and maker-depth parameters remain intact. The shallow 10/20 cutting tool on each side spans the full 159 mm shared opening, while the deeper 15/25 tool retains its 77 mm span; both ends of each tool are rounded. Their overlap produces a shared cavity with a curved deeper internal termination, without a separating bridge. The right shallow section placement moves to X=58 mm to mirror the left full opening.

The front lip roundover is geometrically rebound to the changed cylinder/recess intersection boundary (20 edge segments rather than the original 12), retaining radius 2.5 mm. The existing fourteen-cut chain, seam-imprint chain, and final `Joined_SeamBox_z0` body remain native features.

Each of the eighteen non-tray open contact surfaces is first intersected with the corresponding rounded recess tool, then with the final body as before. The four shallow 10/20 contact surface extrusions also span the full opening, and native `Part::Cut` features subtract the deeper rounded tool before final-body intersection. This assigns newly shallow curved end areas while preventing coplanar shallow/deep contact overlap. Both rounded tray surfaces remain unchanged. Every existing contact tag and export identity stays on its original Region object; no tags were inferred or regenerated.

The nine-pose embedded manifest is preserved byte-for-byte. Parent agent owns later camera, cord, compiler, export, delivery-lock, and app validation work. This handoff claims native geometry only, not completed package delivery.

## Execution records

`author.py` performs the tool and body correction; `contact_partition.py` produces the final candidate. `author-first.log` records the bounded stopped attempt that tried downstream recomputation with obsolete lip indices. The successful author pass uses native feature-by-feature recomputation before a complete final recompute. `author.log`, `author-status.json`, `author-report.json`, `contact-partition.log`, and `contact-partition.json` retain results. `author-report.json` records intermediate contact areas; consult the independent audit for final contact validation.

All outputs and temporary interpreter wrappers are workspace-owned under this directory. No HTTP server, simulator, or external application resource was created. Temporary runner directories are removed by the runner on exit.

## Handoff checks

Independent native audit verifies one valid solid, 19 logical contacts / 20 open regions, zero off-final-skin area for every contact, all eighteen unchanged depth witnesses on their surfaces, zero shallow/deep contact overlap on both sides, identical four bore solids and parameters, unchanged nine-pose manifest, fully constrained sketches, no native errors, and no material assignments. Tessellated bounds remain exactly X ±260 mm, Y/Z ±25 mm. The BRep's conservative spline bounding box differs; use the independent bounds and containment diagnostics to distinguish that kernel bound from physical dimensions.

A reopened final candidate passed native end-radius editing: left top-six tool radius 8.5 → 8.0 mm recomputes a valid final solid and changes its volume from 754063.949207 to 754015.732163 mm³. Restoring 8.5 mm returns 754063.949209 mm³ (about 0.0000016 mm³ numerical drift). The saved file hash remains unchanged: `0ce8b0b9ce39637f9b6d4b2c29618ef09430b200513b5548f54d97e83804a448`.

Whole-board before/after front, side, and top previews are `before-after-front-side-top.png`; the supplemental rear preview is `before-after-rear.png`. The oblique diagnostic uses a simple painter renderer and shows occlusion artifacts, so it is not suitable as a visual acceptance figure. All native subprocesses completed and the owned `tmp` directory is empty.
