# La Baguette — native CAD source audit

**2026-10-01 correction:** the user explicitly confirmed there are no grooves.
The [smooth-end review](groove-removal-review/review.md) supersedes all groove
dimensions and the grooved-end interpretation below. Eight native groove
tools/cuts are removed; the cord is re-solved on the restored smooth solid.
Historical reports and maker evidence remain unchanged. Human acceptance is
still pending the corrected app review.

Published 470×40×40 mm; front paired stepped 20/25 mm cavities; reverse five cavities 10/15/30/15/10 mm, plus outer tray. Retained loaded front/rear originals support exterior end wraps.

Body corner 19/outer round 2 mm. Front openings 155×21 mm centers x ±125, outer half  25/inner half  20. Reverse centers x ±166(width 78, depth 10), ±87(width 55, depth 15), 0(width 68, depth 30); all height  21/corner 9. External bandscenter x ±220, width 4, depth 1.5. Unpublished spacing, cavity widths and radii are display estimates.

All six contact records unchanged. Primary 3D physically locates 30 mm on the reverse, matching retained manufacturer views; historical raster association was not copied as a geometric fact.

The FCStd is the self-contained geometry and metadata authority: constrained Sketcher profiles, analytic Part extrusions/lofts, cuts/fusions/fillets, and native face SubShapeBinders. No imported facet solids, textures, materials, hardware, image tracing or geometry-generation scripts are retained. This is a display model; estimated dimensions are not manufacturing specifications. The schema label `native-parametric-measured-profile` identifies the supported native source type; these raster migrations did not measure an old display mesh.

Source authorization: the first six boards inherit September20 approval only for byte-identical retained primary visual sources. Refreshed HTML is separately authorized primary research and is explicitly distinguished in sources.json. YY exact packets were approved September29; additional primary search was expressly authorized by the user. No human CAD acceptance is implied.

[Visual comparison](review/index.html) includes every prior committed raster and current front/side/top/rear/oblique CAD view. There was no prior CAD side/top view. [Native cord evidence](native-cord-evidence.json) records known exposed routes and unknown hidden connections; source-visible topology governs and guessed hidden joins are omitted. Native cord solve reports and descriptor binding are recorded in validation.json. Human acceptance remains pending the requested one-at-a-time app review after the complete batch.

[Contact contract](contact-contract.json) compares retained logical fields to the frozen baseline. Native acceptance reopens/recomputes every source, verifies constrained sketches and valid actual body/contact surfaces, then changes a real dimension and checks both body and contact update without saving. Compile reports validate source SHA, descriptor/model pairing, contact inventory, exact supported grip depths, surface partition, and material-free output.

## Primary evidence

- [YY Vertical](https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-la-baguette-3.webp?v=1753695062) — Front view: rounded narrow body; two front stepped cavities, with engraved 20/25 mm on the right; end-wrapped cord. SHA-256 `1f6742bddbb63d5583952d8ae10bfe7fbca5ac5dc7990c8ccbc1695f4c5c9080`.
- [YY Vertical](https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-la-baguette-2.webp?v=1753695052) — Reverse oblique: five distinct recess regions, engraved 15/10 mm near one end; rounded thickness; cord wraps externally around both grooved ends. SHA-256 `ecdd7142686b82cc93b103292cc5fe75a923ab8bb0389dc437d40a75609c8214`.
- [YY Vertical](https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-la-baguette-1.webp?v=1753695041) — Front oblique: stepped 20/25 mm cavity floors, rounded end shape and visible external cord loop around end groove. No hidden bore is established. SHA-256 `ae8a640c88a520246b964bcb67285836ebd2e63eb593efe3e00a7cefe7467676`.
- [YY Vertical](https://www.yyvertical.com/en/products/la-baguette-poutre-escalade) — Exact product identity, gallery association, dimensions and listed contact depths; no training prescriptions are imported. SHA-256 `a7e4ad58ba8cbefd9fb3d2ef3ebeeeb74c467c3bf61f6bd8583f8ad7c89b7b22`.
- [YY Vertical](https://www.yyvertical.com/cdn/shop/files/6_-_YY_-_BAGUETTE.jpg?v=1749649955) — Manufacturer loaded-view corroboration of front/rear cavity layout and external end-wrapped suspension; no training prescription is imported. SHA-256 `714d3b1d806a647a57e1353cfcfd682f29864efc8cc063617d80a2ff708ef78f`.
- [YY Vertical](https://www.yyvertical.com/cdn/shop/files/4_-_YY_-_BAGUETTE.jpg?v=1749649954) — Manufacturer loaded-view corroboration of front/rear cavity layout and external end-wrapped suspension; no training prescription is imported. SHA-256 `edf1fe79e9e08e7d0329215ef372a4c0ef174ec4426d3226490d26dc6376d8bf`.
- [YY Vertical](https://www.yyvertical.com/cdn/shop/files/2_-_YY_-_BAGUETTE.jpg?v=1749649950) — Manufacturer loaded-view corroboration of front/rear cavity layout and external end-wrapped suspension; no training prescription is imported. SHA-256 `3a10846614985d0471b4edc23c6a614649eca322ad0e37c5411829aeb2b9979a`.
- [YY Vertical](https://www.yyvertical.com/cdn/shop/files/5_-_YY_-_BAGUETTE.jpg?v=1749649952) — Manufacturer loaded-view corroboration of front/rear cavity layout and external end-wrapped suspension; no training prescription is imported. SHA-256 `011b024d01d61a3ce22521d39eedf32ec086041c4d6846e719a27a450de894de`.

The [continuous cord certificate](cord-continuous-clearance.json) checks the exact rounded runtime routes, including fixed-support legs and final terminals, against the native collision solid using adaptive signed-distance bounds. Every route passes the explicit 0.01 mm numerical tolerance; reported values are conservative lower bounds, not sampled minima.

[Camera correction proof](camera-correction-proof.json) records local front/rear and inverted viewing directions. The correction changes camera metadata only; native assets, routes, heights and cord dimensions remain byte/value identical.

Initial compile reports predate metadata-only edits and are superseded for final source identity. [Current-source fresh rebuild proof](reproducibility.json); [batch validation notes](../validation-notes.md).
