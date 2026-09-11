# Task 5 report — actual-export verifier and two-branch probes

## Scope

Updated only the Flash Board actual-export verifier and its pure-contract
tests. The verifier now requires:

- one body and exactly seven unique selectable hold bindings;
- four passage correspondences to importer-visible body/attachment nodes,
  rejecting passage or ledge meshes with a hold role;
- material/image evidence for every imported board/contact mesh;
- exact model and descriptor hashes, coordinate frame, source-image isolation,
  and explicit triangle evidence;
- front-to-back surface ray results for every active hold in all four poses;
- two branch clearance results per pose, with sampled centerlines, passage
  interfaces, radius-plus-clearance thresholds, nearest-mesh diagnostics, and
  exact sample counts;
- a deterministic cord-sized swept-tube passage probe: 33 cross-section
  samples at the declared cord radius plus clearance tolerance, each checked
  by full-depth mesh intersections in both directions.

The verifier uses the actual imported mesh BVHs. It does not use camera masks,
source-image detection, generated geometry, or physical geometry edits.

## Test-first evidence

The new report-contract and branch-probe tests were written first and failed
because the verifier accepted missing passage/ray/branch fields. After the
minimal implementation:

```text
python3 -m unittest -v Tools.HangboardModels.test_verify_tension_flash_board
```

Result: 11 tests passed.

## Recovery follow-up

The interrupted follow-up was preserved and completed without changing the
board document, model source, geometry, or package assets. The tracked
review-only candidate in
`Tools/HangboardModels/fixtures/tension_flash_board_two_branch_review_candidate.json`
is now bound by
the verifier to the exact four named passage points, two ordered branch pairs,
and all four canonical poses. Its report contract also requires five ordered
actual-mesh surface rays for every active hold (center plus four interior
surface samples), exact exterior/inter-pocket ligament IDs, four swept-tube
passage results, and two posed branch-clearance results per position.

The added repeated-sample regression first failed because five copies of the
center probe were accepted. After requiring each hold's ordered sample indices
`0...4`, the fresh standard-library suite passed:

```text
Ran 17 tests in 0.040s
OK
```

`python3 -m py_compile` for both verifier files and `git diff --check` also
completed successfully. `pytest` remains unavailable in the host Python, so
the standard-library invocation is the executable focused equivalent.

Additional checks:

```text
python3 -m py_compile Tools/HangboardModels/verify_tension_flash_board.py Tools/HangboardModels/test_verify_tension_flash_board.py
git diff --check
```

Both passed. The requested `pytest` executable is not installed in this
environment, so the equivalent standard-library unittest module was used.

## Aperture-proof follow-up

The former centerline plus four-boundary passage rays were replaced with a
fixed 33-sample radial sweep: center, 0.5-radius/8-way, 0.75-radius/8-way,
and full required-radius/16-way samples. Every sample casts front-to-rear and
rear-to-front through the complete imported mesh span. The required radius is
the tracked cord radius plus the tracked clearance tolerance. A body hit at
any sample fails the passage; this aperture proof applies no attachment
interface exception. The separate branch clearance exception now requires
both the sampled point and nearest triangle to be within the documented
interface tolerance, so it cannot waive a nearby body collision.

The new regression keeps the centerline clear while blocking one required
outer-radius sample and confirms the swept probe fails. The candidate hashes,
fixture, board document, model source, geometry, and truthful
`no two-branch USDZ export has passed this contract` status are unchanged.

## Actual Blender verification boundary

The requested compile command was attempted exactly through the managed RTK
Blender entrypoint. Blender 5.2.0 terminated with SIGSEGV before Python ran in
the Metal backend (`gpu::MTLBackend::metal_is_supported`); the retained
diagnostic is:

`.context/pretty-crocodile-tension-flash-board/task5-blender-fresh-config/tmp/blender.crash.txt`

Per the brief, one owned fresh-config minimal repro was then run and reproduced
the same pre-Python SIGSEGV. One identical host-context minimal repro reached
Python and exited successfully. This isolates an environment/runtime boundary;
it is not evidence of a geometry defect. Consequently no new actual-export
`export-verification.json` could be produced from this branch's current
single-cord board metadata. The prior owned package was retained at
`package-prior-task5/` and was not treated as a two-branch pass.

No compiler, descriptor, board JSON, geometry, or package-promotion files were
changed.
