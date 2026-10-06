# #16 La Baguette: smooth ends and exterior cords

The [human review record](../human-review.json) records acceptance of the shown revision with unsupported grooves removed, exterior cords on smooth rounded ends, wood finish and all six contacts.

## User correction and evidence

On 2026-10-01 the user said “there are no grooves”, reconsidered the wrap
direction (“oh i guess the cords can be either way”, “nvm”), and repeated
“but still, there are no grooves”. The follow-up allocation explicitly
confirmed “THEREA ARE NO GROOVES”: do not add or infer grooves; route the cord
on the real rounded end surfaces. This is a correction, not acceptance.

The [approved maker source register](../sources.json) and whole retained
front/rear/oblique images continue to support the rounded body and exposed
cord wraps. They do not establish the invented 4 mm by 1.5 mm groove cuts.
No new groove, bore, knot, or hidden connection is inferred. Exact source URLs
and hashes remain in that register; no retained source image was changed.

## Native correction

Removed all eight groove boxes and their eight Boolean cuts. The existing
`CavityMouthRounds` feature is now the exported `yy_body`. This restores the
pre-groove native solid; it does not regenerate the board from scratch.
The constrained outline, cavity cuts, mouth fillets, published dimensions and
five published depths are preserved. Native source remains self-contained
and editable; the throwaway correction script is under workspace scratch.

All five edge contact binders are reattached to exactly the same physical
faces on the restored solid. Native common-area checks find no lost edge
contact area. Tray now selects the upper plane and both longitudinal rim
rounds. Deleted groove floors/walls and the tiny end-cap slices formerly
separated by the grooves are excluded. This deliberately selects the upper
bearing surface rather than retaining contact patches on nonexistent cuts.
The contact inventory and factual metadata are unchanged.

The existing runtime `surfaceFinish: wood` remains enabled from the first
review. The retained maker product description identifies soft wood. Its
procedural appearance is a display adaptation, not a scanned texture. USDZ
meshes remain unbound and contain no materials or textures.

## Cord regeneration

The graph remains two exposed exterior wraps (`cadRoutedCord`). Cord length
0.9 m per represented loop, radius 1.2 mm, stations at x ±220 mm and lower
station height −10 mm remain estimates for the display. The front/rear
bearing-station depth is derived from the native 20 mm surface plus the
1.2 mm radius, 0.2 mm clearance and 0.001 mm numerical outside offset.
These are solver inputs, not hand-drawn routes or new manufacturer facts.

Routes and hanging height are generated against the restored native solid. The numerical outside offset is a solver parameter, not a new physical dimension.

## Verification and review

The independent native check reopens/recomputes one valid solid and six
surface-bound contacts, verifies eight fully constrained sketches, and finds
no groove objects or material metadata. A temporary edit to the left 25 mm
cavity changes the body and only that contact; restoring it returns the
original volume without saving. Eleven focused Python regression tests pass.
The native compiler validates and reimports the actual export, including
the published depths and exact contact inventory.

The [six-contact app captures and package parity](ios/captures/validation.json) and [picking, orbit and cord probes](ios/runtime-probes/validation.json) record the displayed revision.

- [Fresh app views](app-review.png) and [all six selections](six-contacts.png).
- [Prior committed/revised native front, side and top](prior-revised-front-side-top.png).
- [Original raster and initial native comparison](../individual-review-2026-10-01/original-native-comparison.png), retained as historical evidence.
- [Independent package/native checks](independent/) and [final model-bound cord check](final-cord-check.json).

This is a display model with estimated details, not manufacturer CAD or a
manufacturing, ergonomic or safety specification. The rope solver certifies
the generated static route against the native solid; it does not simulate
friction, knot behavior, dynamic loading or unconstrained sliding along the
smooth board. The linked human review records acceptance of the displayed revision.
