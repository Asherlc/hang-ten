# Nature Stone Hanger native geometry

Native 105 × 105 × 35 mm body with four opposed cavities, eight selectable grip regions, adjustment grooves and a separate rounded stone insert.

The final wood solid is Port_RightVisibleMouth. The stone insert is an analytic box with a 2.4 mm native edge fillet, retained as visible geometry with no material or texture. Explicit face references on native PartDesign::SubShapeBinder objects expose the body and stone exterior shells; contact regions are open true-surface intersections. The 15/20/10/6 mm published depths remain intact, including distinct flat/incut selections. Three lateral adjustment grooves on each side are native cylindrical voids at Z 24, −2.4, −22.8 mm, radius 1.75 mm. Short radius-2 mm native lateral recesses at Y 0, Z −2.4 mm represent only the visible mouths; the inner cutoff at X ±47 mm is the display representation boundary, not evidence of a physical stopped hole. Exterior mouth planes are X ±52.5 mm with outward axes ±X. The source set does not show the concealed connection, which is therefore omitted from the cord graph. Two separately terminated visible exterior leads are generated against the native solid.

Exact source bytes, URLs, approval and support mappings are retained in source-register.json. Native Sketcher/Part/PartDesign features are editable and use the documented X-right, Z-up, front-negative-Y millimeter frame. Approved mesh sections come from Git d0e4e95191e4a76822815bb4eeef3a32caa6fea0; no pixels were traced. No materials, textures or mounting hardware are present.

The embedded manifest replaces the physically removed board.json. Native reopen/recompute and meaningful edit/restore validation passes; final compile and cord reports are retained separately. Front/side/top comparisons in geometry-review.html are the geometry review artifact and do not claim human final app approval.

Cord radius is a 1.5 mm display estimate, visually reviewed against retained manufacturer Stone_Hanger_Granite_3.jpg. The previous 2 mm estimate equaled the modeled mouth radius and left no centerline clearance. The estimate is reduced while native geometry and actual mouth remain unchanged; this is not a maker rope specification.

Front/side/top comparison reviewed individually. Same outer bounds and eight-grip arrangement remain. The stone lip is rounded geometry rather than material contrast. The prior side render showed daylight through a hidden full passage; the native source shows only the evidenced recess and therefore no daylight connection. This is an intentional evidence correction, not a missing visible cord.

Native generated visible-lead solve and subsequent --check both pass all canonical poses with strict three-dimensional clearance sampled every 0.5 mm. Native/source/model hashes are retained in both reports. Final human app review remains separate.

Native edit limitation: FreeCAD emitted two BodySkin topological-reference warnings while exercising FrontDepthScale; every bound region remained valid, the body stayed one solid, and restoration passed. The published source reopens and compiles successfully. Future edits that change face topology should recheck the explicit binder support lists; see native-edit-warnings.json.

Final continuous clearance certification passes for every exact rounded runtime cache and reconstructed support endpoint. The adaptive signed-distance certificate retains the 10 µm numerical tolerance and also checks between the earlier 0.5 mm samples; see continuous-cord-clearance.json.
