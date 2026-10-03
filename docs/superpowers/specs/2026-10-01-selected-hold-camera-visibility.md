# Selected-hold camera visibility

This is the current camera interaction contract for the RealityKit board viewer.
It supersedes the selection-driven camera reset rules in earlier suspended-board
and board-migration designs and plans. It does not change board geometry,
logical hold identity, authored board poses, or cord configuration.

Selecting a hold whose highlighted surface is difficult to see from the
canonical view chooses a small camera adjustment from the actual contact
triangles and surrounding board geometry in the current board pose. Exposed
surfaces use projected area. Recessed surfaces also use clear sight lines through
their openings: an upward-facing finger floor underneath a roof does not imply
that the camera should look down at it. Area-weighted surface samples detect
that enclosure within the contact's own geometric extent and test candidate
sight lines against the imported board meshes. Each mesh keeps a local spatial
index; pose changes transform rays and conservative bounds, without rebuilding
or transforming the board-wide triangle data.
Hold names and types never enter the calculation.

The search is limited to 20 degrees and uses the least-visible selected hold
for multiple selections. Prefer the front angle when it is readable; otherwise
choose the smallest readable adjustment or the best meaningful improvement in
that neighborhood. This is a bounded geometric heuristic, not a global
visibility optimum or an authored opening annotation.

- Every new selection sets the display to the computed angles and default zoom,
  including a zero adjustment that returns to the front angle. It animates over
  0.28 seconds when Reduce Motion is disabled.
- Unchanged contact selection and board position, physical same-hold retaps,
  and highlight-mode updates preserve manual orbit and zoom.
- Clearing an existing selection restores default camera framing.
- Position changes still apply the package's board pose and cord setup. The
  camera uses that position's framing and recomputes hold visibility.
- Automatic adjustment refits the complete board and cord bounds. For corded
  boards, pitch rotates the actual board about its own authored cord-point
  axis, keeping the entire cord fixed. Separate instances use separate axes.
  A single attachment uses the canonical view's horizontal axis through that
  point, since one authored point does not define a cord axis.
  The camera fits the local board rotation envelope at rest and does not move
  during pitch.
  Yaw retains the camera orbit; all-uncorded scenes retain camera pitch.
  Mixed scenes apply the equivalent pitch to their uncorded instances about
  the framing target, while the cord and camera remain fixed.
- Visibility is evaluated in the canonical pose before each new selection.
  Clearing restores the exact canonical board and cord transforms. Projected
  contact controls refresh during the board's 0.28-second animation; manual
  gestures, position changes and disposal cancel superseded animation.
- The normal viewer requires no live rope controller. This is a kinematic
  display hinge with unchanged cord geometry, rather than physical
  equilibrium. Live rope physics remains an explicit loader opt-in for tests.

Unit validation covers returning to front, front-opening recesses versus
exposed surfaces, edge-on top/side/underside surfaces, mirrored geometry,
multiple selections, whole-scene framing, clearing, and replacement contact meshes. UI validation waits for the expected selection's
rendered camera to reach its target before using projected hold coordinates.
Physical reselection tests require a new native pick receipt for the expected
hold before asserting that camera angles and projection remain unchanged.
