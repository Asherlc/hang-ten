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
- `tension-grindstone-original`: 12 contacts, evidence gate approved.

The 2026-09-29 reservation recheck found no dirty target paths across local worktrees, no target FCStd history in all refs, and no competing open PR for these target packages. Excluded Whetstone PR523, Trango Natural PR521, Clavellium and the First/Light/One batch PR524. The current `tension-grindstone` and `tension-grindstone-pro` packages are separate revisions and must remain untouched.

## Original Grindstone research status

The package product URL is no longer available. The historical audit at commit `86a1e5440`, `docs/source-audits/2026-08-12-soill-tension-board-packages.md`, records a commerce archival front image at https://www.northernrocks.co.nz/wp-content/uploads/2018/12/tension-climbing-hang-board-grindstone-pro.jpg. The historical audit identifies that image as Original Grindstone, but current visual reinspection contradicts it: the retrieved bytes show 7 mm incuts, monos and two-finger pockets, identifying Grindstone Pro. SHA-256 `a3342e27f8292cce75ac4e9b9959cd1ea077449936ec6545d057b92fbfdd084b`. This image is rejected for Original Grindstone and is not in the approved source set. The manufacturer CDN reference was rechecked and returns HTTP 404.

Manufacturer interview: https://www.powercompanyclimbing.com/blog/2017/7/5/episode-49-a-better-strip-of-wood-with-tension-climbing — the 2017 designers describe paired 35/30/25/20/15 mm edges and center 50/22 mm edges. This supports revision/contact facts, not a substitute for two distinct photos. Current manufacturer Grindstone photos show the Mk2 and are excluded.

## Authoring and verification contract

Use native constrained parametric FreeCAD sketches/features with real cavity floors. Direct authoring only; no pixel inference, tracing, registration, segmentation, or generated evidence. Keep sourced facts separate from display estimates. Omit mounting hardware/holes from the display geometry. Preserve factual metadata and contact IDs; generate board.json at build time from the embedded manifest. USDZ meshes remain unbound and material-free. Before delivery: pinned byte-identical rebuild, native recompute and persisted depth edits, staging parity, all picking contacts, full Swift/Python checks and front/side/top prior-asset comparisons plus in-app screenshots. PR524 must reach origin/main before final integration/lock refresh. No merge of this batch is authorized.

## Approved Original Grindstone source set

Northern Rocks commerce archival photos were retrieved via its media API and visually inspected. All three show Original Grindstone, with paired 35/30/25/20/15 mm edges, center 50/22 mm edges and phone slot. They are not the rejected Pro image.

- [tension-climbing-hang-board-grindstone-top.jpg](https://www.northernrocks.co.nz/wp-content/uploads/2018/12/tension-climbing-hang-board-grindstone-top.jpg) — SHA-256 `153f3ca312bf8ac9ead17037ed0c6bd4b5bf462a09c31c7752ddd192a79067a3`; retained `docs/source-audits/2026-09-29-next-three-cad-sources/tension-climbing-hang-board-grindstone-top.jpg`.
- [tension-climbing-hang-board-grindstone-side.jpg](https://www.northernrocks.co.nz/wp-content/uploads/2018/12/tension-climbing-hang-board-grindstone-side.jpg) — SHA-256 `e644ad4934d0ee9d246611db847cc5554cdacd6a27105acab3b12eeb2e2f6a69`; retained `docs/source-audits/2026-09-29-next-three-cad-sources/tension-climbing-hang-board-grindstone-side.jpg`.
- [tension-climbing-hang-board-grindstone.jpg](https://www.northernrocks.co.nz/wp-content/uploads/2018/12/tension-climbing-hang-board-grindstone.jpg) — SHA-256 `335d5f097153b1da8ca8d53134513680ad12ec02324533c4e4d410efa71e65b5`; retained `docs/source-audits/2026-09-29-next-three-cad-sources/tension-climbing-hang-board-grindstone.jpg`.

On 2026-09-29 the user explicitly answered **“Approve Original Grindstone sources”** for the three exact Northern Rocks commerce archival images listed above. A subsequent explicit message reconfirmed this approval independently of any asynchronous request lifetime. All three package evidence gates are now approved.
