# Hangboard Presentation Remediation Design

## Goal and scope

Revalidate all 85 PNG presentation assets across the 61 bundled hangboard
packages and repair every genuine material, product-likeness, perspective, or
render-consistency defect. The completed catalog keeps Hang Ten's established
simplified, unbranded illustration style: manufacturer and independent
photographs establish the physical product, but are not shipped as catalog
assets.

The review covers every declared presentation, including alternate usable
surfaces. A conforming asset must depict the exact physical revision, preserve
its real construction material and topology, show the working surface head-on,
and use the same restrained studio-render treatment as comparable assets in
the catalog.

## Confirmed decisions

- Keep every usable surface established by source evidence. A side, end, back,
  or reversible face remains a distinct presentation when it is a real working
  surface.
- Render each presentation orthographically head-on to its own working surface.
  The conventional front of the whole product does not take precedence over
  the surface being trained on.
- Revalidate all 85 assets under the corrected catalog contract, including the
  current passes. Regenerate or edit only assets that genuinely fail it.
- Preserve compliant assets as catalog baselines. Uniformity does not justify
  unnecessary replacement or a topology regression.
- Preserve the simplified and unbranded catalog convention. Logos, labels,
  mounting scenery, photographic backgrounds, and publication-specific image
  styling are omitted unless a physical marking is required to distinguish a
  usable contact and primary evidence establishes it.

## Source and evidence contract

Every presentation receives a fresh live-web evidence review. The review
records the exact product name, physical revision, material, and usable surface
shown. Local documentation may help locate a package or stable identifier, but
it is not product proof and cannot justify a visual or material claim.

Evidence consists of:

1. a live official manufacturer product page, manual, catalogue, hold diagram,
   or archived first-party page for the exact revision;
2. official straight-on and oblique pictures sufficient to establish layout,
   depth transitions, material, and the intended working surfaces; and
3. independent retailer, review, or owner pictures where available, used to
   corroborate real-world finish, construction, and perspectives that polished
   manufacturer imagery may obscure.

The manifest records the review date, direct HTTPS URL, publisher, source kind,
revision applicability, and the precise claim supported by each source. An
independent source may corroborate an official claim but does not override
unambiguous first-party specifications. Conflicting evidence is recorded and
resolved to a named physical revision rather than blended into one invented
product.

Source images are evidence and image-generation references only. They are not
copied, retouched, cropped, or promoted into the app. The accepted asset must
be an original simplified render. No shape, contact, component, finish,
material cue, or usable surface may be filled in from model assumptions. If
the evidence does not establish a detail, omit that detail or reject the
candidate.

Distinct physical revisions are separate packages when their construction,
material, usable surfaces, or hold topology differs. The remediation must not
make one presentation combine features from multiple revisions. A cosmetic
edition may remain one product only when evidence establishes that its physical
layout and material are unchanged.

## Material-specific render contract

All presentations use a common off-white studio background, centered
orthographic composition, neutral lighting direction, restrained contact
shadows, clean antialiasing, and consistent object scale within the appropriate
form-factor cohort. The product fills a comparable share of the frame to its
selected baseline without cropping hardware or inflating compact products to
look full-width. Recesses and thickness changes are communicated through
controlled shading, not a tilted camera.

Smoothing is a shared rendering treatment rather than a demand that unlike
materials look alike. Surfaces use continuous, non-airbrushed transitions and
bounded texture detail while retaining the cues that identify their actual
construction:

- wood preserves plausible end grain or face grain, laminated boundaries when
  sourced, warm diffuse response, and the exact published finish without
  plastic gloss;
- molded plastic, resin, and urethane preserve the sourced color, molding
  seams or aggregate only when visible and relevant, and a matte manufactured
  surface without invented wood grain;
- metal preserves the exact anodized, raw, painted, or powder-coated finish
  with restrained specular response and crisp manufactured edges;
- stone or mineral composites preserve a dense mineral surface without being
  smoothed into wood or molded plastic; and
- mixed-material products preserve each documented component independently,
  including sourced ropes, pins, fasteners, or plates that affect the product's
  physical identity.

Each asset is compared with an accepted catalog baseline selected by both
material and form factor, such as a full-width wood board, molded resin board,
metal lifting edge, or suspended multi-surface device. The selected comparator
and the reason it applies are recorded in the manifest. A baseline governs
composition, lighting, texture frequency, and edge treatment; it never supplies
missing product geometry.

## Remediation manifest

Add the machine-readable audit ledger at
`docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`.
It is a review and provenance artifact, not package input. It declares the
complete set of 61 package identifiers and 85 presentation asset paths so
coverage can be validated mechanically.

Each presentation record contains:

- package ID, product name, presentation ID, asset path, and declared working
  surface;
- exact physical revision, manufacturer, material or material set, and form
  factor;
- current asset SHA-256 hash and one decision: `keep`, `regenerate`, `edit`,
  `removeUnsupportedPresentation`, or `splitPhysicalRevision`;
- findings for product likeness, material, topology, head-on perspective,
  smoothing, framing, and cross-catalog consistency, each with an explanation;
- official and independent evidence entries with source URL, publisher, source
  kind, review date, revision applicability, image role, and supported claim;
- the material/form-factor baseline asset and the reason for choosing it;
- the exact generation or edit prompt, every supplied source image's role, and
  the current asset's role when image editing is used;
- every generated candidate's SHA-256 hash, disposition, and a concrete
  acceptance or rejection reason;
- the accepted asset hash, final dimensions, and visual reviewer decision;
- Workbench geometry-review status for normal, all-active, and individual-hold
  states; and
- package validation, focused test, full package-suite, bounded
  build-for-testing, and simulator-review results.

The manifest never treats a generation prompt or output as factual evidence.
A kept asset still receives complete evidence, findings, comparator, accepted
hash, and validation records; generation-only fields are explicitly empty
arrays rather than omitted coverage.

## Generation and edit workflow

For each noncompliant presentation:

1. Resolve the exact revision and working surface from live sources before
   generating anything.
2. Select the material/form-factor baseline and record which source images
   establish silhouette, contact topology, material, component placement,
   color, and usable-surface orientation.
3. Use the built-in image-generation capability in generation or image-editing
   mode. Supply the minimum source set that establishes the product. The exact
   prompt names the revision, orthographic working-surface view, real materials,
   shared studio treatment, topology that must remain unchanged, and details
   that must not be introduced.
4. Store every input copy and candidate temporarily beneath a workspace-owned
   `.context/sincere-otter-*` path. Hash the untouched model output immediately;
   do not post-process it with cropping, registration, masks, contour tools,
   texture transfer, or vectorization.
5. Compare each candidate side by side with official imagery, independent
   imagery, the current asset, and the chosen catalog baseline. Record its hash
   and an evidence-specific accept or reject reason.
6. Promote only an accepted original output to the declared package asset path.
   Preserve the package's required PNG dimensions and aspect ratio through the
   generation request, not a later geometric transformation.
7. Review the package's existing canonical paths against primary evidence and
   the accepted presentation, then deliberately redraw any path that no longer
   matches the verified product or presentation.

Image editing is preferred when the current asset has verified topology and a
bounded change can correct material, perspective, or treatment without changing
the layout. Full regeneration is used when the silhouette, product revision,
or working-surface topology is wrong. A generated candidate is never accepted
merely because it is smoother or more attractive.

## Batching

Work proceeds in six reviewable batches:

1. Reclassify all 85 assets under this contract and complete their source,
   material, revision, working-surface, comparator, and decision records.
2. Repair non-wood fixed boards, grouping resin, urethane, plastic, metal,
   stone, and mixed-material products by their verified construction.
3. Repair wood fixed boards, preserving real grain direction, laminations,
   finish, and hold topology.
4. Repair portable and reversible boards, retaining every sourced working face
   and real identity-bearing hardware.
5. Repair genuine multi-orientation products, with each usable side or end
   orthographic to its own working surface.
6. Run the complete cross-catalog consistency review and correct any remaining
   composition, scale, lighting, or smoothing outlier without replacing a
   compliant product needlessly.

The classification manifest is complete before the first promotion. Later
batches may refine a finding when new evidence is discovered, but the change,
new source, and decision rationale remain auditable. Each asset belongs to one
repair batch even when it has multiple materials, preventing overlapping edits.

## Manual geometry review

The saved canonical path remains the sole source of rendering, highlighting,
and hit testing. An operator deliberately reviews every changed presentation
in Workbench against primary manufacturer evidence and the accepted simplified
asset. The operator inspects the normal image, all holds active, and each
logical hold individually, including every piece of a multi-piece hold.

When a path is wrong, it is drawn or refined directly in Workbench. Exact
left/right mirroring is used only when evidence establishes physical symmetry.
A supported shape constraint may be selected only by the operator for a contact
that is genuinely a circle, oval, pill, rounded rectangle, or rectangle; the
constraint is editing metadata and does not replace the saved path.

The remediation must not use image-driven hold detection, segmentation,
generated masks or contours, source alignment or registration, raster-to-vector
conversion, automatic path simplification, automatic cropping, or
proposal/refine/promote geometry workflows. Generation neither proposes nor
validates canonical geometry.

## Validation and simulator QA

A presentation is complete only after all of these checks pass:

1. Side-by-side human review confirms exact-revision likeness, material,
   topology, component inventory, orthographic working-surface view, framing,
   and material-appropriate smoothing against official and independent
   evidence and the chosen catalog baseline.
2. The manifest coverage validator accounts for all 61 packages and 85 PNGs,
   rejects duplicate or unknown asset records, verifies source and candidate
   hashes, and requires a final disposition and accepted hash for every asset.
3. Final-inventory package validation passes, including declared presentation
   paths, PNG validity, dimensions, aspect ratios, and package schema.
4. Targeted package tests pass for each changed batch, followed by the complete
   hangboard-package test suite.
5. Workbench review confirms normal, all-active, individual-hold, and hit-test
   alignment for every changed presentation.
6. A bounded `build-for-testing` succeeds and an isolated workspace-owned iOS
   Simulator inspection confirms catalog, plan, active-highlight, presentation
   selector, and hit-test rendering at representative device sizes.

Automated checks establish inventory and data integrity, not visual truth. The
human evidence comparison and Workbench/app review remain mandatory even when
all tests pass.

## Failure handling

- If official and independent sources conflict, identify the revision shown by
  the current package and obtain revision-specific evidence. Do not average or
  merge the images.
- If evidence cannot establish material, topology, or a usable surface, leave
  the existing asset unpromoted, mark that presentation blocked with the exact
  missing evidence, and continue independent assets. Unsupported presentations
  are removed only when the package inventory and source audit establish that
  the surface is not usable.
- If a candidate changes a verified contact, component, silhouette, or material,
  reject it and record the hash and reason. Retry with a narrower edit or a
  stricter generation request.
- If generation repeatedly cannot preserve exact topology, retain the verified
  current asset when it otherwise conforms or block that presentation for a
  later deliberate render. Approximate likeness is not accepted.
- If a changed presentation exposes incorrect canonical paths, stop promotion
  for that asset until an operator directly reviews and corrects them.
- If validation or simulator QA fails, revert only the candidate promotion for
  the affected presentation, retain its evidence and rejection record, and
  continue nondependent work.

## Resource ownership and cleanup

Temporary web inputs, comparison boards, generated candidates, Workbench review
captures, logs, and simulator artifacts live only under paths prefixed
`.context/sincere-otter-*`. Each work session records ownership immediately in
its workspace-owned context directory. Any external simulator or generation
resource name also includes `sincere-otter` so ownership is unambiguous.

The process installs an exit trap for every exact external resource it creates,
shuts those resources down, deletes them, and verifies deletion before reporting
completion. Shared, standard, and unknown resources are left untouched.
Rejected candidates and copied source inputs are removed after their hashes,
roles, URLs, and rejection reasons are recorded in the committed manifest.
Accepted final PNGs live only at their declared package paths; `.context`
artifacts are not committed.

## Deliverables

- A complete committed remediation manifest covering 61 packages and 85 PNGs.
- Updated source-audit narratives for any revision split, unsupported surface,
  or source conflict that requires product-level explanation.
- Repaired package presentation PNGs only where the manifest establishes a
  genuine failure.
- Deliberately reviewed and, where required, directly authored canonical paths
  for every changed presentation.
- Validator and focused test coverage for manifest completeness and integrity.
- Batch validation records and a final catalog report listing kept, repaired,
  removed, split, and evidence-blocked presentations with their accepted hashes.

## Non-goals

- Replacing the catalog with manufacturer photographs or branded replicas.
- Regenerating compliant assets solely to make every material visually
  identical.
- Inventing product geometry, material, color, hardware, usable surfaces, hold
  names, measurements, grip guidance, or training claims.
- Using local documentation as product evidence.
- Automated image analysis, geometry extraction, registration, vectorization,
  path simplification, cropping, or hold detection.
- Adding or changing training plans, timer behavior, product metadata unrelated
  to resolving an exact physical revision, or general app navigation.
- Treating passing tests, an image-generation output, or the current package as
  proof that a product depiction is correct.
