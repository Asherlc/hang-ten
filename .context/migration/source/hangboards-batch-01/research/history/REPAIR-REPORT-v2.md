# Batch 1 — corrected geometry, revision 2

**Five usable GLBs, two materially corrected meshes, 94 selectable contacts, 235,000 triangles, 32 current genuine renders. Five PARTIAL entries, one EVIDENCE-BLOCKED entry, zero COMPLETE entries.**

This is a geometry repair delivery, not the preceding unchanged audit. Moon and Metolius have new exports and authoring source. The other three meshes remain byte-identical; their current imports, renders and evidence notes were refreshed. Nothing is represented as fully source-verified merely because it is valid geometry.

| Model | Status | Contacts | Triangles | Geometry change |
|---|---|---:|---:|---|
| deWoodstok Woodbord | PARTIAL | 17 | 42,000 | Unchanged mesh; fresh renders/validation |
| Escape Unlimited Board | PARTIAL | 7 | 36,000 | Unchanged mesh; fresh renders/validation |
| Evolv Basic Training Board (Long) | EVIDENCE-BLOCKED | — | — | No mesh supplied |
| Metolius Wood Grips II Deluxe | PARTIAL | 26 | 65,000 | Six mounting apertures; depth-map conflict resolved |
| Moon Armstrong | PARTIAL | 21 | 46,000 | Central arched jug, open shelves and mono passages |
| target10a Linebreaker BASE | PARTIAL | 23 | 46,000 | Unchanged mesh; fresh renders/validation |

## Corrections actually made

**Moon Armstrong, exact Ash revision.** The incorrect central pill-shaped blind pocket was replaced by an integral upper lip with an arched underside. The two centre capsule pockets became open horizontal shelves. Both mono apertures are now open rather than falsely capped at the rear. Their front nominal contact length is distinguished from the estimated continuation through the body. The 21 logical contact IDs remain stable; exported node indices are regenerated and should not be hard-coded by the app. Exact rear relief and pulley interfaces are not invented or certified.

**Metolius Wood Grips II Deluxe.** Four mounting apertures became six in three paired columns, consistent with the readable numbered Deluxe diagram. The diagram corroborates the nonuniform 31/32/38 and 25/25/28 mm rows; the earlier uniform-row review allegation is therefore not used to overwrite correct depth assignments. Bore centres remain photo-derived estimates, not a drilling guide. The final 65,000-triangle mesh passed the assembled topology check; an earlier over-decimated attempt failed and was not delivered.

## Current validation

The exact meshes were independently clean-imported for structural validation and by VTK for genuine render generation. Checks address metric scale, names, exact contact mappings, embedded material/no external references, finite nondegenerate geometry, duplicate faces, connected contact patches, assembled closed topology, real cavity-floor intersections and clear bores. Moon also has specific ray tests for its arch and open shelves. Structural validation remains distinct from photographic fidelity.

The delivered authoring sources were actually executed in isolated temporary directories without the original GLBs. The per-model rebuild records give exact source hashes and byte-identical export results. A combined repeat was interrupted by the execution timeout after two successes; the preserved successful per-model runs and separately executed remaining run are the evidence, not an assumed completion of that interrupted command.

`validation-v2/` contains red/green regressions, build/render logs, the sampling/decimation investigation, and the environment preflight. A passing test is not a claim of manufacturer approval. The final ZIP's readback and whole-file hashes are in the separately supplied archive-verification JSON, avoiding circular hashing of the ZIP inside itself.

## Source support and remaining gaps

The new numbered Metolius diagram and exact Moon Ash photo were actually inspected. Their URLs, publishers, interpretation and limits are recorded per model. The Moon new-review record refers to the same original photo as I1, not a second independent photograph. Woodbord manufacturer text now directly corroborates its nominal envelope/material/screws/depth families; its individual depth map remains unverified. Escape explicitly follows its dimensioned-photo revision rather than pretending the contradictory prose dimensions agree. Target10a pocket-depth assignment and sloper handedness remain estimates. See `research/source-coverage-v2.json` for all six.

**Original reference-image bytes are still missing.** Several original images were viewable in the web reader, but attempts to download into the artifact environment failed. Other galleries did not render at all. URL observations/transcriptions are not labelled as saved originals. No generated picture is substituted as research evidence. This is one reason the five existing assets remain PARTIAL.

**Evolv Long is the one missing mesh.** The exact Long page and MPN are known, but its front/side images could not be loaded. A shared Short/Long retailer photo and the 24-inch Kilter board are not accepted as proof of the Long geometry. Specific page: https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105 . The required help is a saved front and oblique/side image from that exact Long gallery, not another general research assignment. Additional retailer failures are in the Evolv evidence folder.

## Native authoring and allowed approximations

Blender/bpy was not available; the fresh installation attempt returned no matching bpy distribution. No native .blend or Blender Outliner screenshot is claimed. The supplied editable metre-scale PLY/NPZ plus executed numeric authoring code and self-contained GLB are the fallback permitted by the brief. Photo-derived local curvature and neutral untextured PBR appearance are documented display choices; those alone are not being treated as automatic failure of the allowed fallback.

No texture photographs, invented wood grain, logos, cords, external screws, walls, camera rigs or environments are in production GLBs. No font files are in the package. This is a display/interaction asset, not manufacturing CAD, load-bearing equipment, an installation template or a metrologically verified physical replica.

## Recheck or rebuild

Open index.html to browse the actual render sheets and model records. Per-model source/rebuild.py creates that model from the delivered numeric source. Run the package check after extraction:

```sh
python -m pip install -r requirements.txt
python tools/audit_archive.py --tree . --report /tmp/batch01-check.json
python -m pytest tests -q
```

An audit exit code of zero means the PARTIAL package is internally consistent and its delivered meshes pass the specified structural checks. It does not turn five partial models into six complete ones.
