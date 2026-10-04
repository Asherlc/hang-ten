# Port-A-Board runtime cord review

The approximately **12.258° seam is in the saved native path**. Swift rigidly transforms cached points, prepends the fixed anchor, and draws straight cylinder spans. The actual world support is `[0, 0.17, 0]`, because the 100 mm anchor value is an offset above the model’s 70 mm maximum Y.

Every one of the 24 lead/pose paths changes from a center-support span into a constant-X section at X = ±50 mm. The first free span is 235.564 mm; its out-of-section angle is 12.255°, whereas its projected YZ bend is only 0.270°. The first cached seam is each path’s largest interior turn. These figures can be tested directly from saved coordinates, without a simulator.

The relevant trace is `BoardPackageStore.swift:1786` → `SuspendedBoardPresentation.swift:443–475` → `BoardModelRealityTypes.swift:951–960`. Native fixed-section projection is in `native_cord_routes.py:116–144`; section selection is at `:634–668`, and cache support stripping at `:704`.

No Swift correction is indicated. Test native routing in a plane containing the real support and mouth, retain source-backed entry constraints, re-settle length/height, and certify complete solid and interstrand clearance. If needed, use the bounded native coupled3D shortening mechanism, not renderer smoothing. This runtime review does not establish the seam’s precise distance from wood or prove that every turn is unsupported; the native lane must distinguish contact bearings from certifiably unnecessary corners. Collision-free does not imply physical equilibrium.

Material and non-pickable transient-cord behavior are unchanged. No code or packages were edited; no simulator, native solve, test, or external resource was started.
