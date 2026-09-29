# Stoak Board III Oak granite surface audit — 2026-09-29

The user approved the exact manufacturer front and oblique evidence and the
CAD material-partition design in chat before authoring. A third manufacturer
center close-up is retained as supporting evidence. This changes display
surface partitioning, not the physical silhouette or contact metadata.

- Publisher: Nature Climbing. [Front view: large center lower stone insert and symmetric outer lower side inserts; upper small center pocket is wood.](https://natureclimbing.com/cdn/shop/files/6_2a2069e0-b45e-4eca-aa65-59febfe7c958.png) SHA-256: `640afba4b4c148a155f97106676ee3632308480e28796c7e8059f5f796aba77d`.
- Publisher: Nature Climbing. [Oblique view: stone top/contact and front faces, wooden recess rear walls.](https://natureclimbing.com/cdn/shop/files/4_671cc28f-ab91-4566-ad88-887bace217be.png) SHA-256: `9bc53be5ae91a1572297728b3cef3d5b623b89d883ac0fe1105adaa00a03c055`.
- Publisher: Nature Climbing. [Center close-up: large center pocket stone floor/lip with wooden surrounding walls; small upper pocket remains wood.](https://natureclimbing.com/cdn/shop/files/17_174db9e0-f6f5-4cc3-9426-3f0fe1f10d7f.png) SHA-256: `4a6d3991180583517b440b476784a5e8c18f01c659a77711de5b6ceb814bb25e`.

## Explicit mapping and estimates

The approved sources show stone in the larger lower-center pocket and at the
outer ends of the lower side pockets. The small upper-center pocket is wood.
Existing legacy node names put “granite” on that small upper-center mesh, so
names cannot establish material placement.

Native CAD measurements establish side insert x spans -262..-180 mm and
180..262 mm, floor z=23 mm, and depth 20 mm; the center spans x=-52..52 mm,
floor z=36 mm, and depth 30 mm. These are measurements of the existing authored
CAD, not additional manufacturer dimension claims. A 6 mm front strip height
is deliberately selected as a display estimate from the approved configuration;
the manufacturer does not publish that thickness. Boolean tolerance is 0.001 mm
at front/floor boundaries to retain coincident faces, not additional geometry.

Granite nodes `granite_insert_left`, `granite_insert_right`, and
`granite_insert_center` bind respectively to `lower-composite-left`,
`lower-composite-right`, and `lower-composite-center`. They contain the existing
floor, rounded mouth and front-face surfaces within the explicit native boxes.
The corresponding wood shells lose exactly those surfaces and retain their
original wood-shell outlines/contact IDs. No new hold, depth, grip cue or training fact is
authored. Each original contact remains selectable as one identity across all
of its material pieces. The stone front-lip area previously belonged to the
nonselectable body; it now highlights/picks with its insert contact (about
332.75 mm² per side and 425.50 mm² at center). Logical contact inventory and
metadata stay unchanged, while complete insert surfaces become selectable.

The parametric `Body` solid is retained unchanged. `DisplayBody` is a static
surface copy partitioned along the three box boundaries so tessellation respects
the material seams. Original sketch/solid authoring remains intact. The source
must be re-partitioned deliberately if its geometry is edited later, consistent
with existing static contact shells. Volume and Boolean difference checks prove
the retained solid is unchanged; shell area conservation checks ensure complete
surface coverage. The pinned compiler separately validates triangle coverage,
contact depths, normals, bindings and unbound USDZ export.

Authoring script: throwaway `.context/author-stoak-granite.py`; generated
measurements: `.context/stoak-granite-partition-audit.json`. Runtime appearance
uses a matte charcoal base, derivative-filtered procedural mineral cells and
roughness variation. This is an artistic approximation of dark granite, not
an image texture or measured reflectance.

## Review evidence

Front, side and top comparisons of the newly compiled asset against the prior
committed asset are under `.context/stoak-granite-*-comparison.png`. Actual app
screenshots and the full test results are recorded in
`.context/stoak-granite-validation.md`. Completion requires both geometry
comparison review and unhighlighted/selected/restored material review.
