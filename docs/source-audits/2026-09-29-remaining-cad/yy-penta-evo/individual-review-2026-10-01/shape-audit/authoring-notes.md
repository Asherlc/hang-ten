# YY Penta Evo native shape and pose review

Scope: #18 only. The accepted #17 Baguette Evo was not changed. Candidate source is `corrected.FCStd`, SHA-256 `4fe277d3fedd3252a28d8c6b752eda98cd3c8740bf27167cc5db645c7603a69e`.

## Evidence and demonstrated issues

The exact approved whole manufacturer originals are retained in `docs/source-audits/2026-09-29-remaining-cad/yy-penta-evo/evidence/yy-penta-evo-front-reverse.webp` (SHA-256 `83b95adc297d634659654f6f27bb43ebae1c53b171b747568ac5e022754e6571`) and `yy-penta-evo-close-up.webp` (`1107039ef6d2877cd68a293683c72ec93f3166633199d45484f58c13b48aa2fc`). Publisher reference URL: https://www.yyvertical.com/en/products/penta-evo . The exact original image binary URLs remain unknown; this product URL is a reference, not a claimed binary origin.

The whole front/reverse source shows an enclosed rear 10 mm slot aligned along the lower side band. Before correction, the native rear slot tilts across that band and breaks through the outer perimeter; its upper end also collides with the central opening rim. The native rear preview clearly establishes the defect. The loaded close-up shows the selected 20 mm grip along the bottom of the rotated unit; the previous two face-only poses do not express per-grip loading orientation.

The seven retained grip types are four edges, mono, duo and tray. No additional pinch is identified by either retained source. No pinch identity or training prescription was invented.

## Narrow native correction

Only the four existing `edge_10Section0...3` sketch placements were rotated by +36 degrees about native Y around their unchanged individual centers. This changes the undirected capsule axis from the incorrect native XZ -72-degree alignment to the band-aligned +72-degree alignment (equivalently -108 degrees). It preserves the existing capsule dimensions, depths, constraints, loft/cut history, and all contact IDs. These numeric angles are display adaptations from the existing analytic CAD, not manufacturer-specified angles.

The two editable region helpers `Region_central_ring_001` and `Region_upper_band_exterior_001` remain in the document, but their NodeID and NodeRole export properties were removed as authorized. They are physical wood, not separate attachment media. Their surfaces remain in the complete exported body and can receive the existing wood finish. No helper geometry was deleted and no material was added. Export now has one body and seven reusable contact slots.

## Native verification

`correction-report.json` records a valid single solid, seven open valid contact regions, all seven regions exactly on the final skin, all sketches constrained, and exact geometric equality of all six unaffected contact regions. The corrected edge retains 10 mm depth. `metadata-check.json` proves the embedded manifest and its 14 physical contact identities are unchanged and the actual package source remains untouched.

`editability.json` reopens the candidate, changes all four corrected sketch angles by a further 2 degrees, and verifies a valid single solid with a 945.8164 mm3 changed region. Restoring the placements exactly restores volume. Changing PocketDepthScale from 1 to 1.04 gives a measured 10.4 mm rear depth, remains valid, and restores with approximately 1.2e-10 mm3 volume drift. Candidate bytes remain unchanged throughout.

`before-after-front-side-top-rear.png` presents whole-board views and was visually reviewed. Front geometry remains unchanged; the rear 10 mm opening is enclosed and aligned along the band. The side-view perimeter breakthrough disappears. The painter preview is shape evidence; final acceptance still needs the compiled asset and app.

## Pose and station proposal

`manifest-pose-proposal.json` preserves primary for the 25 mm pair and reverse for the 10 mm pair, adding edge-20, edge-15, mono, duo and tray. `bearing-check.json` verifies the selected native bearing normal transforms to world +Y for every grip, and each selected contact is below the model center. All rotations, cameras, station coordinates and planes are display adaptations, not maker measurements. Cameras are inverse-transformed into unposed model space.

`pose-stations.json` measures the new upper bearing band for each pose. It intersects the native solid from its center along inverse-rotated world up, selects the first inner wall, and obtains actual surface points at native Y=-10 and +10 mm in the central flat depth region. Each station offsets along the actual outward normal (incident-normal bisector at the inner apex seam); a native full-solid distance search chooses the least offset giving 2.200001 mm clearance for a 2 mm cord plus 0.2 mm margin. `station-bridge-check.json` proves the entire straight span between each station pair has that same clearance. The failed initial tray one-face-normal construction, with only 1.99048 mm clearance, is retained as `pose-stations-first-attempt.json`; it was rejected and replaced by the symmetric apex bisector.

These are attachment/bearing stations, not drawn route centerlines. Full route generation must still certify actual-solid and tube clearance and physical support. The initial planes use the inverse-up ray and depth axis; the coordinator tested native surface-normal planes for 25/20 after strict full-route certificates rejected the radial planes. The measured-normal planes passed both routes and now appear in the recommendation; the other five retain their passing radial planes. All seven scratch routes passed the coordinator's strict native clearance/length checks. Previous proposals remain as `*-radial-planes.json`. Final bound package solver reports remain the coordinator's responsibility.

`corrected-collider.json` uses the retained exporter algorithm: native Cut6, tessellation deflection 0.25 mm, runtime mapping (X,Z,-Y)/1000, 35,042 vertices and 70,092 triangles. It binds the exact candidate source SHA. No committed USDZ, sidecar, delivery lock, package source or shared solver was changed by this audit.
