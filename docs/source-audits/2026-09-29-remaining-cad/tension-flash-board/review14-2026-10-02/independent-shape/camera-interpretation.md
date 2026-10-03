# Offline camera interpretation

The upright whole-cord oblique sheets are fixed-world inspection views. Their opposite-face appearance does not establish a grip-orientation error, and the passed physical geometry/cord gate remains unchanged.

`render-cord-views.py:55–99` rotates the model and routes by the selected pose, then applies a fixed world projection; it does not read `pose.camera`. Oblique uses a fixed 30-degree Y rotation. The painter renders larger projected Z last. `reverse-oblique` inspects the other side and is where the upright legal contacts were reviewed.

The current app source declares different semantics: `SuspendedBoardPresentation.swift:1426–1430` rotates the unposed-model camera direction with the board, and `BoardModelRealityTypes.swift:953–960` places the camera opposite that direction. Three-edge upright uses model direction −Z with a 180-degree X pose; two-edge upright uses +Z with identity. Both yield world viewing direction +Z (camera on −Z), whereas the fixed offline oblique looks from the +Z side. Consequently the global three-edge-upright sheet shows the native reverse/two-well face, while the two-edge-upright sheet shows the native front/three-well face. The prior asset uses the same inspection convention.

This is a read-only interpretation of the offline script, retained pose metadata, and existing camera code. It does not establish current app rendering or human acceptance. No production source, pose, package, or prior verdict was changed.
