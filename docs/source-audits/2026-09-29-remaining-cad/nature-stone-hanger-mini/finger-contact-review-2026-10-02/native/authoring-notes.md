# Mini upper-rail finger-contact correction — scratch candidate

Owner: `placid-badger`. The user rejected the crown-only highlight because it omitted the actual finger-contact area. This candidate is a new correction pending root review and human review; prior crown acceptance does not apply.

The selected outside upper rail now includes the front and rear flat pad-bearing areas and the outer side continuation down to the native central recess-mouth lip. The lower boundary is `FinalSolid.Face21` ZMax, currently **19.82417332780598 mm**. It is an expression-driven native boundary, not a published grip-depth measurement. Front/rear flat band coverage runs to z27.5 mm, joining the previously authored crown up to z30 mm. The new pressure-band area is **1524.059875078127 mm²**.

Native selected exterior faces:18/26/27/34/40/60/63/66/68/70/71/74, restricted above the lip boundary. Existing rounded crown faces28/29/30/41/42/43/59/65/69 stay selected. The pressure band is jug-only. Original shared crown30/43/69 still belongs to jug and pinch-60; existing pinch-only23/31/44 is unchanged. The source-backed60 mm pinch denotes upper/lower opposition along native Z, distinct from the25 mm front/rear thickness of this upper rail. No new contact or factual dimension is introduced. All four source contacts,15/15/60 mm factual depths, position membership order, and the entire embedded manifest are unchanged.

Excluded: groove-wall interiors, cavity back wall6, wood-hold undersides/lips, lower frame and lower rear panel. No image tracing, cropping, pixel measurement, inferred pressure map, shader, overlay, duplicate face or physical body reshaping was used.

## Native construction and authority

`FinalSolid` remains the original one closed native collision solid. `CompleteExteriorSurface` binds the entire `Shell1` with `Refine=False`. A deliberately selected outside-face binder and a native `Part::Common` with `UpperRailPressureMask` produce the upper pressure band. The mask Z follows `UpperRailMouthLipReference.Shape.BoundBox.ZMax`. A native `Part::Cut` subtracts the band from the exterior; `ExportBodySurface`, a `Part::Compound` of remainder and band, is the one exported body node. It contains only exterior faces with real tessellation seams, never internal planar caps. `nature_jug_pressure` binds the band and exports assigned body triangles. All helpers are ordinary native link/expression objects; no custom Python feature is required when reopening the document.

`ExportBodySurface` is an exterior surface compound, not a claimed closed CAD solid. Its exact per-original-face Boolean coverage proof has zero missing/off-original area, zero component overlap, and90 faces corresponding to the original78 surface faces. The unchanged closed `FinalSolid` has exact two-way volume/surface equality. The collider is freshly exported from `FinalSolid` and is identical in geometry and native cord features.

The complete-shell reference makes FreeCAD serialize `FinalSolid.Shape.brp` and its topology map differently. This is explicitly recorded; original BRep byte identity is not claimed for that member. Other original geometry members remain byte-identical. Mathematical solid equality and exact collision vertices/triangles/features establish preserved physical geometry. Exported triangulation may change at the added analytic band seam; full old triangle-position identity is not claimed.

## Evidence

The retained whole manufacturer front/reverse/side photographs establish the physical upper rail and surface shape. The user identifies the requested jug pad-contact coverage. The whole hand-use photograph gives use context but does not establish an exact rear finger-pad footprint. Matching the rear band to the front mouth boundary is a deliberate display-contact interpretation, not a manufacturer pressure measurement or training prescription.

Sources and existing hashes are retained in `docs/source-audits/2026-09-29-remaining-cad/nature-stone-hanger-mini/sources.json`:
- https://natureclimbing.com/products/stone-hanger-mini-oak
- https://natureclimbing.com/cdn/shop/files/Oakminihanger1.jpg?v=1774539696
- https://natureclimbing.com/cdn/shop/files/Oakminihanger2.jpg?v=1774539697
- https://natureclimbing.com/cdn/shop/files/Oakminihanger3.jpg?v=1774539696
- https://natureclimbing.com/cdn/shop/files/MiniHanger-86.jpg

## Verification and historical attempts

The initial all-face exterior binder lost references when a groove radius edit changed face topology. The final full-shell binding handles that change, with refinement disabled to preserve existing face boundaries. Required probes change the actual mouth fillet radius1.50→1.55 mm and groove radius1.7→1.8 mm, recompute all native helpers cleanly, verify band position/on-body coverage, then restore exact body geometry without saving the probes. No broader dimension experiments were run.

Distinct attempt stdout/stderr, command, ownership and cleanup receipts retain failed and stopped phases. Shared convenience proof/progress files describe the latest candidate. The final handoff includes a hashed artifact inventory. Tools are pinned FreeCAD1.1.3/OCCT7.8.1/OpenUSD26.8. Prior/candidate preview images render actual imported USDZ triangles at identical scales with a per-pixel depth buffer; they are neutral diagnostic renders and do not claim app rendering. Canonical package, sidecar routes and poses are untouched by this worker. Root owns promotion, sidecar model hash integration, route checks and final human review.
