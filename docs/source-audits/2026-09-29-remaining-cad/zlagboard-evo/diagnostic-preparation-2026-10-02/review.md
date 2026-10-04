# Evo — diagnostic preparation, unrun

The workout highlight-transition defect remains unresolved. No production fix
or app source change ships with this appendix.

The earlier scene-only stdout trace is exactly 4,096 bytes and ends mid-record.
It confirms a blue CPU material assignment, but cannot exclude a later write or
scene replacement before the screenshot. It therefore does not establish a
persistent CPU/rendered-frame mismatch on the same visible scene.

The [temporary diagnostic patch](minimal-real-workout-diagnostic.patch) records
unique scene and view identifiers, actual content-root membership, semantic
highlight changes, and bounded 1 Hz weak-scene snapshots. Complete JSON lines
are written directly to a file with wall-clock and monotonic timestamps. It
proposes no material, camera, timer, selection or geometry changes. The earlier
scratch revision is retained separately.

`git apply --check` and DEBUG Swift parsing passed. The patch remains
**unapplied, untypechecked and unrun** because the isolated Simulator never
reached Home. Instrumentation may change timing; a nonreproducing trace would
not demonstrate a fix. Any future experiment must correlate actual screenshots
with complete state records before drawing conclusions.

The renewed shared-code reservation was explicitly released. All five reserved
app/test files remain unchanged. Coordinate again before applying diagnostics;
no fifth production fix or shared integration is authorized by this appendix.
The existing [geometry acceptance](../human-review.json) and all prior failed
experiments remain unchanged. This preparation creates no new app approval.
