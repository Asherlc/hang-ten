# Next three native CAD migrations: evidence review

Branch: `migrate/next-three-hangboards-cad`. Workspace owner: `supreme-zebra-next-cad`.

## Approval

On 2026-09-29 the user explicitly answered **“Approve both source sets”** to the review of the exact four manufacturer images listed below. A subsequent explicit user message reconfirmed this approval. This approval covers Evo and Honestone geometry authoring; it does not cover Original Grindstone.

## Retained approved sources

### yy-verticalboard-evo-1.webp

- Publisher: YY Vertical
- Source: https://cdn.shopify.com/s/files/1/0285/5010/3128/files/YY_-_VBE_-_1_gris.webp?v=1770125892
- Retained: `docs/source-audits/2026-09-29-next-three-cad-sources/yy-verticalboard-evo-1.webp`
- SHA-256: `e1c1eb02942c1809cbc251c4ff6a2beb47b88c1314fd5bb33e0da496d1355214`
- Supports: Full front view; contact inventory and silhouette.

### yy-verticalboard-evo-3.webp

- Publisher: YY Vertical
- Source: https://cdn.shopify.com/s/files/1/0285/5010/3128/files/YY_-_VBE_-_13_gris.webp?v=1770127775
- Retained: `docs/source-audits/2026-09-29-next-three-cad-sources/yy-verticalboard-evo-3.webp`
- SHA-256: `3b697ed3911db64df2737f0fb0c0a44372f8b7fe7128ea04a9ce9b6e16dd8d25`
- Supports: Angled close-up; recess lips and sloper transition.

### tension-honestone-1.png

- Publisher: Tension Climbing
- Source: https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Honestone1.png?v=1726542571
- Retained: `docs/source-audits/2026-09-29-next-three-cad-sources/tension-honestone-1.png`
- SHA-256: `b41c5de625814fb685b5290fa779721287c40854c70afe4778292205056c276b`
- Supports: Full front view; contact inventory and silhouette.

### tension-honestone-3.jpg

- Publisher: Tension Climbing
- Source: https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Honestone3.jpg?v=1726542571
- Retained: `docs/source-audits/2026-09-29-next-three-cad-sources/tension-honestone-3.jpg`
- SHA-256: `85ac5f15f8fb70814368c9762eee5d15372300f9c29bbbe6b7eb2e3c5e10bf39`
- Supports: Installed oblique view; thickness, slopers and stepped cavity floors.

## Scope and preserved inventory

- `yy-verticalboard-evo`: 25 contacts, all identity and factual metadata preserved.
- `tension-honestone`: 15 contacts, all identity and factual metadata preserved.
- `tension-grindstone-original`: 12 contacts, evidence gate remains open.

The 2026-09-29 reservation recheck found no dirty target paths across local worktrees, no target FCStd history in all refs, and no competing open PR for these target packages. Excluded Whetstone PR523, Trango Natural PR521, Clavellium and the First/Light/One batch PR524. The current `tension-grindstone` and `tension-grindstone-pro` packages are separate revisions and must remain untouched.

## Original Grindstone research status

The package product URL is no longer available. The historical audit at commit `86a1e5440`, `docs/source-audits/2026-08-12-soill-tension-board-packages.md`, records a commerce archival front image at https://www.northernrocks.co.nz/wp-content/uploads/2018/12/tension-climbing-hang-board-grindstone-pro.jpg. Despite the listing/file name, that audit identifies the pictured layout as original Grindstone. It must be re-inspected and retained before proposing approval. The manufacturer CDN reference in that audit was not recoverable at its original audit.

Manufacturer interview: https://www.powercompanyclimbing.com/blog/2017/7/5/episode-49-a-better-strip-of-wood-with-tension-climbing — the 2017 designers describe paired 35/30/25/20/15 mm edges and center 50/22 mm edges. This supports revision/contact facts, not a substitute for two distinct photos. Current manufacturer Grindstone photos show the Mk2 and are excluded.

## Authoring and verification contract

Use native constrained parametric FreeCAD sketches/features with real cavity floors. Direct authoring only; no pixel inference, tracing, registration, segmentation, or generated evidence. Keep sourced facts separate from display estimates. Omit mounting hardware/holes from the display geometry. Preserve factual metadata and contact IDs; generate board.json at build time from the embedded manifest. USDZ meshes remain unbound and material-free. Before delivery: pinned byte-identical rebuild, native recompute and persisted depth edits, staging parity, all picking contacts, full Swift/Python checks and front/side/top prior-asset comparisons plus in-app screenshots. PR524 must reach origin/main before final integration/lock refresh. No merge of this batch is authorized.
