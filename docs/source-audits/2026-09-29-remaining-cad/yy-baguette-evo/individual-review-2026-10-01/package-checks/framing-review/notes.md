# Independent framing diagnosis

Keep the existing >100pt regression assertion. The failure reveals an actual metadata coordinate-frame error. BoardMapView.aspectRatio uses the full native cord solver camera framing; SuspendedBoardPresentation.makeCameraFraming rotates pose.camera.viewDirection by the board transform because that field is in unposed model coordinates. Newly authored recommendation directions were intended in world coordinates but stored directly.

With the exact frozen nine-pose package, descriptor bounds and bounds-relative world anchor conversion from BoardPackageStore, independent projection reproduces80.769598pt and97.300549pt at334pt width. For each pose, convert intended world camera direction to local using inverse quaternion. The same projections become185.947203pt and231.365617pt; all nine corrected views exceed100pt (minimum185.9472). Other cases restore intended viewing side even where height happens unchanged.

No renderer/schema or test weakening needed. Main agent owns metadata correction after native shape authoring copy is finished. camera-frame-correction-check.json gives exact proposed local values and before/after evidence; camera_frame_check.py and raw log are retained. This script is a numeric diagnosis, not an app validation. Fresh Simulator test and visual review remain necessary.

Historical test intent: commit583a2d08 replaced body-only orientation aspect-ratio assertions with native suspension-framing equality and minimum height, explicitly guarding thin bar maps shrinking to32pt despite visible hanging cords. The current failure therefore should be fixed in camera metadata rather than ignored.

An initial exploratory projection used the raw authoring anchor offset as the world anchor; its output is retained as framing-projection.json and is superseded by camera-frame-correction-check.json, which includes bounds.maximumY in the anchor exactly as runtime does.
