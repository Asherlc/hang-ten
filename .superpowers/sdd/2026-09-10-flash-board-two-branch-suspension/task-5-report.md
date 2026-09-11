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

The reviewed deterministic compiler was run in host context after one fresh
owned sandbox repro again terminated before Python with SIGSEGV. Two identical
host-context compiles of the retained
`.context/pretty-crocodile-tension-flash-board/flash-board.blend` produced
byte-identical assets:

```text
primary.usdz          4098ba4f8d8211683e6ec5c4466cd2725c0a040caae4a75e561d705315757524
primary.model.json    fd2c3e057c9feee1d6da57448bd9e4d58510ae8a6c60120282e51b13c228019c
```

The tracked review fixture now pins those exact hashes, and its focused
candidate regression was updated accordingly. The actual verifier was rerun
against the canonical package after hash binding. It passed hash validation,
isolated USDZ reimport, material/image checks, explicit-triangle checks,
surface rays, ligaments, and the four 33-sample cord-sized passage sweeps,
then failed closed on the first actual posed branch-clearance collision:

```text
actual mesh cord clearance probe failed for three-edge-upright branch left-branch:
0.002642211 < 0.003000000; node=flash_board_body_008 segment=17 fraction=0.5
```

An owned diagnostic scan found imported-body clearance violations in all
eight branch/pose paths. The required threshold remains 0.003 m (0.002 m cord
radius plus 0.001 m clearance); no verifier threshold, pose, cord estimate,
or geometry was relaxed or changed. The canonical package is retained at
`.context/pretty-crocodile-tension-flash-board/package/`, with the prior
package preserved at `package-before-task5-rerun/`. The durable diagnostic is
`export-verification.json`; it records commands, hashes, and the exact failure.

No board JSON or production package promotion was performed.
