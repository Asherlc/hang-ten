# Independent Python shared-contact review

One P2 finding remains: `compile_board.py::_depth_regions` globally groups all contacts after any shared membership appears. That lets unrelated unshared multi-node contacts bypass their former per-node depth checks. The retained lightweight actual-function probe demonstrates an unshared 20 mm + 20 mm edge spaced over 60 mm failing before and passing after an unrelated jug/pinch pair is added. Aggregate only recipient IDs named in `additionalContactIDs`, retaining per-node checks for all other contact IDs.

The current NUG properties match the explicit native protocol. Contract strictness, logical node union, shared outline rejection, primary axis/witness authority, and unchanged physical mesh export are consistent in the inspected code. The regression tests target malformed memberships, two opposed bounds, preserved jug ownership, stale node lists, outline masking, and conflicting/missing primary authority. Current NUG primary IDs are unique, so the finding does not invalidate its intended 60 mm Z pinch and 40 mm Y jug measurements.

This was read-only review. No package, code, Git, or documentation files were changed. No heavy tests, simulator, compiler, solver, or external resource was started. Full validation and runtime review remain owned by root and runtime worker. Reviewed file hashes and exact finding are in `python-review.json`.

## Closure

P2 resolved in compiler SHA-256 `34b0a92874d739c70b6bb48c63e8730297b6fda6f610f34c90ccb895c23fe167`. Independent rerun of the original actual-function probe confirms unrelated 20 mm components fail both before and after unrelated sharing, while NUG remains pinch 60 mm / jug 40 mm. New tests also check input ordering, independent unrelated axes, and incomplete primary witnesses. No Python findings remain open.
