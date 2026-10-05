# Main integration — 2026-10-03

Owner and branch: `placid-badger-cad-second-half`.
The user requested bringing this branch up to date with Main. This integrates
`d53c019c43319a70b32e6dc654814de29e87ab89` into the saved branch tip
`e1cc8ff270ba1a0b16b621582f2fc8296b5dd64e`. It does not merge this workspace
into Main or the parent review branch.

Main's extracted workout views, hand-task selection, animated contact camera,
supported physical cord pivots, live-rope implementation, reflected-mesh fixes,
material finishes, and additional native packages are retained. Both schema-2
suspension sidecar layouts and the native CAD route authoring extensions remain
supported. Workout resolution retains position-specific contacts and
presentations alongside Main's per-hand tasks; recorded snapshots preserve
both position and hand-target metadata.

The six allocated packages (#16–21) retain all 22 source, model, descriptor,
and sidecar file bytes. Their review queue and human decisions are unchanged.
All 20,007 pre-existing review files retain their staged Git objects; raw proof
files accidentally targeted by Git's rename heuristic were restored rather
than rewritten as current metadata. All 66 FCStd files are real LFS archive
objects. Fourteen overlapping canonical sources received metadata-only
reconciliation; their non-Document.xml archive members are unchanged.
Mixed wood, granite, plastic, and neutral metal assignments follow retained
source evidence. No geometry was regenerated or measured from images.

Forge keeps the coherent native whole-pair package already on this branch,
with distinct left/right physical contact nodes, rather than combining that
source with Main's former single-half template representation. The generic
mirrored-instance behavior and tests remain for the other paired boards.
Native CAD routes retain the source-solved body and cord transforms during
camera orbit; the generic physical-pivot implementation remains for supported
suspension families. A merge defect that applied Penta's canonical hanging
pose twice was corrected by passing the unposed instance base to its CAD
adapter. Exact-once pose checks cover every Penta position.

Main intentionally retired the global delivery-lock tooling. The exact former
branch lock, checker, reproducibility helper, and tests are archived under
[retired-delivery-lock](retired-delivery-lock/README.md), explicitly inactive.
Native package validation and source-boundary checks remain active.

Validation:

- All 66 packages validate; 612 package tests, 93 focused CAD contracts, and
  79 isolated CI contracts pass. Native exports were not repeated.
- The merged app and test target compile. The final affected-contract run
  passes all 155 tests: nine renderer integration regressions, 73 suspension
  tests, and 73 workout recording tests.
- The earlier 527-test run failed eight cases with 66 assertion failures.
  Seven cases were corrected and pass in the final run. The unchanged Main
  live-physics test `testLiveScenePausesThenPublishesAcceptedSettledFrame`
  timed out at 30 seconds. Its repeat consumed CPU for an extended period
  and was explicitly stopped; it is incomplete, not passing. No full-suite
  success is claimed.
- Fresh installed app binaries match the built binaries. The Pro hold-detail
  view and a separate Evo launch show wood bodies and the red left 20 mm
  contact. Evo's first capture shows only the selected contact and is retained
  as a failure. A wrong Pro route is retained as invalid, with its correction
  separate. These are appearance checks, not workout-transition validation or
  new user acceptance.
- Exact owned Simulator `0C1CF662-98B1-43FF-9405-7AC58CD2132A`, DerivedData,
  and result directories were deleted and verified absent. Unknown/shared
  resources were untouched; this workspace and its agents remain available.

The experimental on-demand board renderer remains opt-in in DEBUG and disabled
by default and in Release. Main's camera animation and live physics have not
been validated with that experiment. The Evo/Pro workout rendering blocker,
fresh Pro user app approval, and eventual explicit combined integration remain
outstanding. No physical iPhone was available.

[Evidence](evidence/exact-copy-manifest.json) includes exact copies of raw logs,
screenshots, source freezes, failures, and member-hashed result archives.
The full staged whitespace check fails on retained raw log whitespace and
the frozen pre-resolution conflict markers; the source/non-raw check passes.
The Git index has no unresolved entries. Raw evidence is not normalized to
make a formatting check pass.
One evidence-handling error is disclosed separately: a worker overwrote two
intermediate analysis files (`native-fixture-test-corrections.json` and
`.patch`). Their original bytes could not be recovered. The replacement files
are explicitly marked as aliases; new analysis uses unique runtime-fixture
names. Raw test logs, source freezes, and the existing committed review proofs
were not overwritten. See the
[incident record](evidence/runtime-fixture-report-overwrite-incident.json).
