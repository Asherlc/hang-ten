# Interim automatically seated exterior cords

The user explicitly authorized “Ship seated cords first; continue live physics”
on 2026-09-30. This is the first exterior-route batch, not completion of the
catalog or proof that live settling meets its performance target.

| Package | Setups | Canonical poses | Exterior leads |
| --- | ---: | ---: | ---: |
| Captain Fingerfood DUAL | 1 | 4 | 8 |
| Captain Fingerfood UNLEVEL | 1 | 4 | 8 |
| J. Bryant FTG-32 | 1 | 2 | 4 |
| Metolius Light Rail II | 1 | 2 | 4 |
| YY Penta Evo | 2 | 4 | 8 |
| Total | 6 | 16 | 32 |

The batch preserves the existing source-backed attachment/entry-side evidence,
all hold/contact inventories, every USDZ, native geometry, cord diameter and
length provenance, and each instance identity. Unknown diameters remain labeled
estimates: 3.6 mm for J. Bryant and 4 mm for the other four products. The owner's
7 mm live Clavellium profile, 7 mm Mini Bar profile and documented 4 mm Helium value are unchanged. Clavellium still has an older 4 mm static fallback; correcting that cache to the confirmed 7 mm is outstanding and is not covered by this batch.
See `2026-09-29-catalog-cord-diameters.md` for source mappings. None of these
exterior caches invents an interior connection, a knot or a material-length split.

## Authoring and clearance

`Tools/HangboardCAD/solve_exterior_rope.py` finds planar shortest routes on an
offset of the actual surface section, using a visibility graph of its complete
boundaries and holes. It refuses embedded endpoints, open meshes and unsupported
entry sides. Round-buffer chords are conservatively inflated. Full-surface
clearance is checked independently of the selected section.

The adaptive whole-segment check uses the 1-Lipschitz signed-distance bound
`(da + db - L)/2` for each interval. It refines ambiguous intervals instead of
accepting from samples alone. The fixed limits are 25 refinement rounds and
100,000 distance samples, with a 10 µm numerical authoring tolerance. This is
not an outward-rounded CAD/mesh error certificate. Closed outward surfaces and
ordinary floating-point proximity/classification are required.

Independent routing caused the two Captain vertical pocket poses to overlap.
`solve_pair` now searches a fixed nine-plane family per lead, projects the
existing estimated approach point onto each candidate plane while preserving
its entry side, and chooses the shortest pair passing complete segment-pair
clearance. It retains the shared initial straight rays at the anchor; downstream
segments require diameter + 1 mm separation. There is no iteration-budget
escalation or manually authored detour. This remains a bounded static
approximation, not a global 3D equilibrium, friction or dynamic settling model.

The routes exclude their anchor and terminal in package contact-point caches;
the renderer reconstructs those endpoints. A direct lead uses its computed
midpoint so the cache remains nonempty. Cached routes preserve their solved
anchor rather than invoking the legacy face-plane anchor projection. Excess
published/display length remains a capacity bound under the existing renderer;
it does not establish conserved material allocations or a solved hanging height.

Native CAD whole-segment `distToShape(Part.makeLine(...))` checks passed for all
four J. Bryant and all four Light Rail leads. The CAD manifest edits leave every
non-Document.xml archive member byte-identical. Other meshes are unchanged;
removing duplicate/zero-area triangles for collision queries does not fill
holes or alter their surface. The caches do not promote these existing clipped
exterior representations to full hidden-passage CAD cord migrations.

## Retained evidence

Workspace-owned evidence lives under `.context/strong-owl-seated-cords/`:

- `inventory.json`, `exterior-candidate-routes.json`, and `whole-segment-clearance.json`.
- `native-exterior-clearance.json` and the exported native solids.
- `anchor-red/green` and `catalog-red/green2/diagnostic` native logs/results.
- `joint-retry.log`, `production-joint.log`, and the fixed routing search.
- `capture-cases.json` and matched prior/current front, side and top screenshots.

The native catalog regression exercises all 16 poses, including both Penta
instances, through the production renderer's length, self-contact and paired
clearance gates. A production-asset scene regression additionally loads the
actual Penta USDZ and selects both orientations. Visual review exposed a
pre-existing instance selection bug: it passed only the base transform and
omitted canonical placement/rotation, making the model unavailable. The caller
now composes the canonical transform with that base, and combined camera framing
includes both units and their cords. Tests assert both placements, reverse
orientation and the centered camera. Cross-unit cord checks retain all initial
segments without the shared-anchor exception. The authoring regressions include a thin obstruction between
samples, a seated tangent, entry-side preservation, empty-section rejection,
embedded endpoints, and independently overlapping leads.

## Work remaining

Captain Pocket has one endpoint that cannot fit its estimated diameter.
MXEdge Large/Small lack the source-shown through-height passages in their CAD.
Rock Rings needs native-solid queries at its tessellation seams; Stone Hanger
has missing interior surface coverage; Baguette has open mesh seams. Tension's
existing full wrapped routing and Clavellium's static fallback also need their
own route/diameter audits. Their caches are not replaced by this batch.

Lattice's primary setup guide establishes one continuous cord threaded through
both end passages, with an exterior bridge below the board. A correction must
preserve that topology rather than inventing two separate loops. Retained guide:
[Lattice setup guide](https://latticetraining.com/app/uploads/2024/05/MXEdge-Lift-Instructions-Artwork-PRINT-READY-28-03-24-PDF.pdf).
Product evidence: [MXEdge Lift](https://latticetraining.com/product/mxedge-lift/).
Neither source documents the bore diameter; any authored value must be labeled
an estimate.

Live physics remains separate and unpromoted. The closed performance screens
and the unverified device target remain recorded in their existing audits.

## Final batch validation

91 native tests passed with zero failures or skips, including the production-asset Penta scene regression. All 13 exterior-authoring regressions passed. Package validation and the delivery lock passed for all 49 models and 117 locked files. All 32 exterior leads passed adaptive whole-segment clearance; all 16 within-setup pairs and both Penta cross-unit poses passed segment-pair clearance. Native CAD checks independently passed all eight J. Bryant/Light Rail leads.

All 24 matched prior/current simulator views were visually reviewed, covering every canonical pose and representative front/side/top views of each product. Penta’s prior views show the pre-existing unavailable-model failure; current views show both loaded units. Retained final evidence: `integration-final.log`, `integration-summary.json`, `authoring-final.log`, `packages-final.log`, `delivery.json`, `paired-cord-clearance.json`, `native-geometry-identity.json`, and `inputs.json` under the workspace evidence directory.
