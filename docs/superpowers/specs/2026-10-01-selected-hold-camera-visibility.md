# Selected-hold camera visibility

This is the current camera interaction contract for the RealityKit board viewer.
It supersedes the selection-driven camera reset rules in earlier suspended-board
and board-migration designs and plans. It does not change board geometry,
logical hold identity, authored board poses, or cord configuration.

Selecting a hold whose highlighted surface is difficult to see from the
canonical view chooses a small camera adjustment from the actual contact
triangles in the current board pose. The search is limited to 20 degrees and
uses the least-visible selected hold for multiple selections. An adjustment
must provide a meaningful visibility improvement.

- A nonzero adjustment sets the camera to the computed angles and default zoom.
  It animates over 0.28 seconds when Reduce Motion is disabled.
- If the selected surfaces need no adjustment, preserve the current camera
  angles and zoom, including a prior manual inspection view.
- Unchanged contact selection and board position, physical same-hold retaps,
  and highlight-mode updates preserve manual orbit and zoom.
- Clearing an existing selection restores default camera framing.
- Position changes still apply the package's board pose and cord setup. The
  camera uses that position's framing and recomputes hold visibility.
- Automatic adjustment keeps the framing target fixed and refits the complete
  board and cord bounds. Manual gestures remain available afterward.

Unit validation covers visible-front preservation, edge-on top/side/underside
surfaces, mirrored geometry, multiple selections, whole-scene framing, clearing,
and replacement contact meshes. UI validation waits for the expected selection's
rendered camera to reach its target before using projected hold coordinates.
Physical reselection tests require a new native pick receipt for the expected
hold before asserting that camera angles and projection remain unchanged.
