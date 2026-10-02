# Zlagboard Evo native correction

Whole approved manufacturer images product-01 and product-02 were compared with the retained prior/current native previews and fresh native oblique. They support fourteen pockets, seven top contacts, published pocket depths and 20°/32° top planes. The previous native model had sharp top trough/lip intersections where the manufacturer shows rounded transitions. Its two jug contact binders also omitted the flat crest strips and outer rounded top-corner skin.

The existing native history is preserved. Two native Part::Fillet features add 2 mm trough-side and 1 mm front-lip rounds. These radii are explicitly operator-selected display estimates. All21 logical contact IDs remain. Every binder references actual faces on the final solid, including jug crests and new rounds, with no face assigned twice. All14 pocket contact geometries and factual depths remain unchanged. Root retained nested wood finish metadata and adopted the display camera direction[0,-0.35,-1]; no body rotation or cord was introduced.

Reopening and recomputation pass with one valid solid and78fully constrained sketches. Editing the trough radius2→2.2mm changes the physical solid and all7topcontacts; restoration recovers volume exactly and contactareas within9.1e-13mm². Tests did not save source changes. Before/after whole front/side/top proof is `before-after-front-side-top.png`; fresh corrected oblique is `rounded-oblique.png`.

Candidate and promoted source SHA-256: `6f44115b879b6a2214dff04f13477ec1bf949627dfccc4319f1f9da6ec28b58c`. Final package compiler/app acceptance belongs to root and the package worker. Raw failed fillet combinations, probe errors and termination status are retained. The costly initial full-shell Boolean probe was stopped; final exact membership evidence comes from binders referencing explicit final solid faces.

No image measurement, crop or tracing was used. Published source facts remain distinct from the estimated700×120×42mm display envelope, pocket mouth dimensions, jug curves and rounding radii. Native BSpline bounds can overestimate depth around the new blends; actual source/candidate tessellations share the same envelope.
