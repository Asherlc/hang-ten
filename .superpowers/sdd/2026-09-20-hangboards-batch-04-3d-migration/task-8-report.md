# Task 8 — Crimptonite Helium Mobile

Owner: `learned-giraffe`. Initial clean HEAD/upstream:
`adc875d95c80f2e509d4ac403f93f30795d17350`.

## Evidence and authoring

Read the repository instructions, RTK contract, add-hangboard, model migration,
suspension audit and TDD skills/references, approved spec/Task 8 plan, progress
ledger, Task 7 report/register/audit, and Task 8 brief. Inspected both retained
full HE2/HE6 originals before authoring and rendered the delivered GLB from
front/reverse/two oblique views. Its `PARTIAL` and
`sourceFidelityApproval: false` status was retained. No delivered mesh was
promoted. The GLB SHA-256 is
`afae2ca4bff5a42af68820682a68a49e1235d4c5332759f9df461475424ab2a6`.

Front evidence SHA-256:
`9f5dea470c326d32c6bde1dd5427f2bfb95a81b99ae258c320ae9deec0384a40`.
Reverse evidence SHA-256:
`5d5c18d45ae6d30e6e951aa158a30b303d42d4583d18d4a6d82075ff5de50f6a`.
Both exact files have regular-file copies under the canonical cord snapshot
directory, preserving the retailer-hosted original photograph classification.
The canonical cord record cites the exact URLs, HE2/HE6 views, current Helium
revision, and Astra approval on 2026-09-20.

Authoring script and review evidence live in
`.context/learned-giraffe-task8-evidence/`. `author_helium.py` reads no images.
It directly constructs the capsule and recess sections in Blender's Z-up,
front -Y frame, cuts only the observed exterior mouths, and mirrors one
authored half with reversed counterpart winding. The complete shell is checked
manifold and positive-volume before partitioning actual surfaces into contact
nodes. Continuous authored normals are retained across partitions; no overlay
geometry is used. No tracing, segmentation, vectorization, contour extraction,
registration, cropping, image detection, or proposal/promotion tool was used.

| Evidence | Final decision |
| --- | --- |
| HE1 maker dimensions | 400 × 58 × 24 mm envelope; retailer 26 mm rejected. |
| HE1 nominal depths + HE2 front | Three separate pill recesses; 14/22 mm outer opposing lips and 10/18 mm center opposing lips. Recess widths, cross-section transitions and radii are `authored-display-estimate`. |
| HE2 rounded top | One continuous outer top-band contact, stopping before end mouths. |
| HE1 rear use + HE6 reverse | One broad smooth rear jug/sloper contact; no extra rear groove. |
| HE2/HE6 exterior openings | Two grouped front/reverse attachment nodes, each containing left/right clipped mouth surfaces. No connecting internal bore. A clipped mouth end is a display boundary, not a claim that the physical hole is blind. |
| HE1 supplied Beal 4 mm cord | 2 mm display radius; per-lead rest length, anchor, material, and pose/camera remain explicitly `authored-display-estimate`. |
| Unknown engraving/material metrology | No logo/engraving, wood-species assertion, raster texture, or claimed factory rounding radius. |

Source-marker conversion is `(x,y,z) -> (x,z,-y)`. Front endpoints become
`[-0.186,0,0.012]` and `[0.186,0,0.012]`; reverse mouths become
`[-0.186,0,-0.012]` and `[0.186,0,-0.012]`. Only the two front endpoints have
transient `pairedLeadCord` leads. Two schema-required point-only mouth records
repeat those exterior endpoints; there is no entry/exit bore, inferred interior
connection, `twoBranchCord`, baked cord, or visible anchor. Attachment nodes
are distinct from contact nodes; the shared runtime keeps transient cords out
of picking/accessibility.

| Source node(s) | Canonical contact |
| --- | --- |
| `he-L-lower-14`, `he-R-lower-14` | `edge-14` |
| `he-L-upper-22`, `he-R-upper-22` | `edge-22` |
| `he-C-lower-10` | `center-edge-10` |
| `he-C-upper-18` | `center-edge-18` |
| `he-outer-top-jug` | `top-jug` |
| `he-rear-jug-sloper` | `back-jug-sloper` |

## RED evidence

Before package/audit edits:

```text
rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k helium -q
2 failed, 34 deselected in 0.18s
```

Failures: four presentations instead of one; raster instead of model.
Log: `.context/learned-giraffe-task8-evidence/red-helium.log`.

```text
rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_cord_audit.py -k "helium or current_four" -q
2 failed, 34 deselected in 0.71s
```

Failures: missing canonical Helium record; represented count 8 instead of 9.
Log: `.context/learned-giraffe-task8-evidence/red-cord-audit.log`.

## Tooling/environment boundary

The compiler's old `_require_image_materials` gate rejected constant Principled
PBR. This conflicted with the explicit zero-raster-texture contract. The
controller authorized a separate fresh tooling task; this agent did not change
compiler or compiler tests and paused final export/staging pending its review.
No 1×1 swatch or validation bypass was used.

The independently reviewed compiler fix
`d7641de87efb9306603c100a2aeaecb310e67c0d` was pushed before final export.
The constant Principled material now passes the retained compiler unchanged;
the model-tool round-trip test also passes in host context. The controller's
nonblocking deferred compiler test-parameterization note is not board work.

Sandboxed Blender exited 139 before Python with its host USD cache-line warning
and crash report. The same owned host-context invocation reached Python and
rendered successfully. One early inspection run reached Python but its JSON
inventory serializer rejected Blender IDPropertyArray; using `default=list`
fixed that inspection-only serialization. Blender 5.2 emits deprecation notices
for `Material.use_nodes`/`World.use_nodes`; these do not prevent rendering.

Exact source/author/preview invocation, with final argument `source`, `author`,
or `preview` respectively:

```text
rtk proxy env BLENDER_USER_CONFIG=.context/learned-giraffe-task8-work/config XDG_CACHE_HOME=.context/learned-giraffe-task8-work/cache TMPDIR=.context/learned-giraffe-task8-work/tmp /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python .context/learned-giraffe-task8-evidence/author_helium.py -- source
```

## Visual review

Astra manually reviewed original front/reverse evidence and source-GLB renders,
then candidate front/reverse/oblique/rear-oblique and all six highlighted
contacts. The authored envelope remains recognizable and symmetric; three
recesses have inward relief and opposing lips, the rear is smooth, real mouth
openings are retained, and no mounting/screw hole or hardware exists. The
14/22 pairs highlight both outer recesses; 10/18 highlight only the center;
the top-band and rear surface highlight separately. The refined normal field
eliminates visible contact-partition seams. Native iOS selection/orbit/workout
acceptance remains Task 14 under the approved plan; Blender captures alone are
not presented as app-integration proof.

Final acceptance is based on the exported USDZ reimported into an empty Blender
scene, not only the source `.blend`. Final retained views are
`authored-front.png`, `authored-reverse.png`, `authored-oblique.png`,
`authored-rear-oblique.png`, and `authored-highlight-{14,22,center-10,center-18,top,rear}.png`.
Astra manually reviewed every final view. Broad faces show minor tessellation
shading in close oblique light, but no inverted relief, missing back, leaking
contact seam, or incorrect grip family. Geometry and contact appearance are
accepted against the retained manufacturer evidence without treating visual
comparison as dimensional metrology.

`cord-{front,reverse,oblique,rear-oblique}.png` render actual samples from the
native production suspension solver, captured in `solved-cords.json`. These
curves are review-only objects added after importing the USDZ; no cord was
exported. Astra reviewed the final front and both oblique views: both exterior
leads meet the front mouths, their free spans remain clear of the board, and
the rear mouths remain unconnected. An earlier oblique camera looked almost
along the suspension plane and collapsed the two leads in projection; the
final review-only camera reveals their separation. Neither the model nor the
pose was changed for that camera correction.

## Final export and verification

Final export and imported-preview commands (host context, exit 0):

```text
rtk proxy env BLENDER_USER_CONFIG=.context/learned-giraffe-task8-work/config XDG_CACHE_HOME=.context/learned-giraffe-task8-work/cache TMPDIR=.context/learned-giraffe-task8-work/tmp /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python .context/learned-giraffe-task8-evidence/author_helium.py -- compile
rtk proxy env BLENDER_USER_CONFIG=.context/learned-giraffe-task8-work/config XDG_CACHE_HOME=.context/learned-giraffe-task8-work/cache TMPDIR=.context/learned-giraffe-task8-work/tmp /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python .context/learned-giraffe-task8-evidence/author_helium.py -- preview
rtk proxy env BLENDER_USER_CONFIG=.context/learned-giraffe-task8-work/config XDG_CACHE_HOME=.context/learned-giraffe-task8-work/cache TMPDIR=.context/learned-giraffe-task8-work/tmp /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python .context/learned-giraffe-task8-evidence/author_helium.py -- cords
```

Logs: `export.log`, `cord-render-final.log`; imported geometry findings:
`exported-structure.json`. The package has schema v3, one original/default
`primary` v1 model record, one `primary` position, exactly six unchanged
canonical contacts, one USDZ and one descriptor, and no PNG/raster,
`contactGeometry`, raster fallback, mounting/screw hole, screw, bracket,
cleat, hardware, logo, or embedded texture. The USDZ has exactly one archive
member, `primary.usdc`.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `assets/primary.usdz` | 324330 | `745f92fdafcfa26f3ff5fe77f1f993d5de68bf0a199173b6f7a43167eb56ba94` |
| `assets/primary.model.json` | 3380 | `7c0811e51c55603d698286511edb3146e34aaeda29a0cc6f6777f1670fcd71d7` |

Descriptor schema v1, `hang-ten-board-v1`, exact 0.4 × 0.058 × 0.024 m
envelope. Eleven mesh nodes, eight contact-bearing meshes mapping to six
contacts, two attachment meshes, and one body; 7102 triangles total. Exporter
sanitization converts source hyphens to underscores and appends `_001`, with
the following exact correspondence:

| Exported node | Contact/role | Triangles |
| --- | --- | ---: |
| `he_L_lower_14_001`, `he_R_lower_14_001` | `edge-14` | 540 each |
| `he_L_upper_22_001`, `he_R_upper_22_001` | `edge-22` | 539 each |
| `he_C_lower_10_001` | `center-edge-10` | 552 |
| `he_C_upper_18_001` | `center-edge-18` | 550 |
| `he_outer_top_jug_001` | `top-jug` | 100 |
| `he_rear_jug_sloper_001` | `back-jug-sloper` | 1030 |
| `front_lead_mouth_001` | attachment, two exterior mouths | 638 |
| `reverse_lead_mouth_001` | attachment, two exterior mouths | 636 |
| `helium_body_001` | body | 1438 |

Imported audit: zero image nodes, zero degenerate triangles, zero
normal/winding disagreements, all 10653 coordinate-welded edges have incidence
two, positive signed volume 0.0003908430194372255 m³. Exactly four exterior
mouths and three grip recesses; zero connecting internal passage geometry.

Commands and observed outcomes (logs are in the evidence directory):

```text
rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py Tools/HangboardPackages/tests/test_cord_audit.py -q
72 passed in 3.19s — focused-final.log

rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
exit 0; 63 boards, zero drafts — final-inventory-complete.log

rtk proxy scripts/hangboard-packages.sh status --root Hangboards
exit 0; 63 boards, zero drafts — package-status.log

rtk proxy scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
exit 0; 34 model packages, 9 represented, 25 excluded — global-cord-audit.log

rtk proxy env PYTHONPATH=Tools/HangboardModels BLENDER_USER_CONFIG=.context/learned-giraffe-task8-work/config XDG_CACHE_HOME=.context/learned-giraffe-task8-work/cache TMPDIR=.context/learned-giraffe-task8-work/tmp .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_descriptor.py Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py Tools/HangboardModels/test_verify_yy_baguette_evo.py -q
21 passed in 2.36s (host context) — model-tools-host.log
Final combined-state repeat: 21 passed in 2.03s — model-tools-host-final.log

rtk proxy ruby Tools/HangboardModels/check_production_cord_clearance.rb
exit 0; 27 real-USDZ poses plus two synthetic regressions — global-clearance.log

rtk proxy ruby .context/learned-giraffe-task8-evidence/check_helium_clearance.rb
exit 0; Helium primary real-USDZ pose plus two synthetic regressions — helium-clearance-capture.log

rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests -q
initial complete run: 3 failed, 650 passed in 130.88s — full-packages.log
final combined-state run: 653 passed in 126.82s (0:02:06), exit 0 — full-packages-final.log
```

The first model-tool run in sandbox had 20 passes and one Blender round-trip
failure caused by pre-Python host initialization exit -11, matching the
independent Blender launch failure. Rerunning the identical suite in host
context passed all 21; no test or model change was made to bypass it.
Final inventory, package status, and global cord audit commands were also
rerun after the integration release with unchanged passing counts. Logged
shell invocations wrap each exact command above with `rtk proxy zsh -o pipefail
-c '... 2>&1 | rtk proxy tee <evidence-log>'`, retaining the command's status.

Intermediate validation caught the schema-required `passages` field and
canonical member/contact ordering. Point-only exterior mouth bindings were
added without introducing entry/exit geometry, and the saved presentation
members and position contact IDs were canonicalized to the original contact
array. All final validation and focused assertions pass.

The initial authored cord anchor `[0,0.12,0.11]`/rest length `0.262` put a
free-span sample only 0.0019481566 m from `helium_body_001`, below the production
0.003 m clearance requirement. Diagnosis used the actual native production
solver and mesh. The final anchor `[0,0.12,0.34]` and per-lead rest length
`0.41` coherently cover the approximately 0.406 m displayed endpoint distance
and leave the tiny observed mouths clear. These are labeled
`authored-display-estimate`; the USDZ, observed mouth size, and source facts
were not changed. The clean final native gate passes. The retained wrapper
uses the existing Ruby/Swift production harness with only the package inventory
and expected pose count changed to Helium/one; it also captures solved samples.
Production solver and clearance logic remain unchanged. Diagnostic logs include
intentional synthetic collisions; the clean final capture exits zero.

### Integration follow-up boundary

Systematic debugging of the complete suite identified exactly:

| Failing test | Evidence/cause | Controller ruling |
| --- | --- | --- |
| `test_batch04_supersedes_historical_audits_without_opening_the_cord_manifest` | Old Markdown assertion says all Batch 04 remains outside the closed manifest; this task explicitly promotes Helium. | Separate integration agent updates the exact assertion. |
| `test_xcode_assigns_each_live_model_to_its_own_safe_odr_tag` | Xcode lacks `HangTenModelODR/crimptonite-helium-mobile/Hangboards`. | Separate integration agent adds scoped USDZ ODR wiring. |
| `test_discovered_model_inventory_matches_current_packages` | Static model ID inventory omits `crimptonite.helium-mobile`. | Separate integration agent updates exact inventory. |

These are not presentation-remediation failures. This agent did not edit the
three integration files and paused staging/commit for separate review/push.
The historical presentation-remediation manifest is untouched as explicitly
deferred to Task 14. No failed full-suite assertion is waived for Task 8.
Integration commit `8793654b4c8ec7fb8bb7abd80f904acca6352069` is pushed and
HEAD/upstream equality was verified. Its independent review correctly found
that the new inventory and ODR declarations rely on the concurrent Task 8
package files; it is not standalone-green. The controller explicitly ruled
that this integration commit and the Task 8 package commit form one atomic
combined change, released final testing of the combined state, and will
fresh-review the combined range. None of the three integration files is staged
again by this agent. The exact 653-test suite completed on the combined state:
653 passed in 126.82s, exit 0. There are no waived or deferred test failures.
The final report is included with the Task 8 package, exact tests, canonical
audit and two regular snapshots in commit `feat: migrate helium to 3d`;
the commit is pushed immediately as directed. The combined range still needs
the controller's fresh independent review. Native iOS UI review and historical
presentation-remediation conversion remain Task 14, not claims of this task.

## Owned resources and cleanup

Retained: `.context/learned-giraffe-task8-evidence/` (explicit review evidence)
and this task report. Temporary:
`.context/learned-giraffe-task8-work/` (Blender config/cache/temp/blend/compiler
staging). Foreground Blender sessions 12824 (serializer failure), 53712
(source), 63034/3275 (author refinements), 77344 (highlight review), and 66384
(exact mirror authoring) exited. No HTTP server, tunnel, simulator, app build,
or shared external resource was created. Final cord-render session 90288 also
exited 0. All other command sessions have completed. `finish_owned.zsh` owns an
EXIT/INT/TERM cleanup trap targeting only the exact Task 8 work directory;
it was invoked successfully after the full suite, removing the 5.9 MB temporary
work directory including config/cache/temp/blend/compiler staging and four
retired package PNG backups. Independent `test ! -e` succeeded. Original PNGs
remain recoverable from git; source evidence and final assets were not removed.
The retained local evidence directory is approximately 28 MB and is explicitly
owned review material, not bundled product data. No owned native clearance
temporary directory remains, and host process inspection found no Task 8-owned
authoring/clearance process. No shared resource was stopped or deleted.

Final cleanup and integrity commands, each exit 0:

```text
rtk proxy zsh .context/learned-giraffe-task8-evidence/finish_owned.zsh
rtk proxy test ! -e /Users/asherlc/.paseo/worktrees/0h78jp9r/learned-giraffe/.context/learned-giraffe-task8-work
rtk proxy git diff --check
rtk proxy shasum -a 256 Hangboards/crimptonite-helium-mobile/assets/primary.usdz Hangboards/crimptonite-helium-mobile/assets/primary.model.json
```

The final hashes exactly match the table above. Original contact definitions,
dimensions, and revision ID were compared with the clean starting commit and
remain unchanged. Staging is limited to this report, Helium package paths,
the two exact test files, canonical cord JSON/Markdown, and the two Helium
snapshots. Integration and presentation-remediation files are excluded.
