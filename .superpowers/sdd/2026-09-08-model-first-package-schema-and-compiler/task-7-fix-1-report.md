# Task 7 fix round 1 report

## Result

Resolved the sole Important Task 7 review finding in `README.md`. The README
no longer describes every board as a flat PNG plus canonical 2D paths or
claims that every package contains `assets/primary.png`.

## Documentation changes

- The opening package description now identifies schema-v2 typed presentation
  media: raster-only packages own a PNG and `media.holdGeometry`, while
  model-only packages own a USDZ and generated hash-bound `.model.json`
  descriptor.
- Logical holds are documented as identity/metadata records without spatial
  fields; the selected raster paths or model mesh/descriptor supplies the
  presentation data for rendering, highlighting, and interaction.
- The package-layout paragraph now describes typed media ownership instead of
  prescribing `assets/primary.png` for every board.
- The Workbench paragraph distinguishes editable raster geometry from
  read-only model geometry.

The detailed Task 7 staging characterization section remains unchanged. No
staging script, test, board package, or app/server/simulator code was modified.

## Verification evidence

README-focused consistency searches found no remaining universal claims for
`assets/primary.png`, a flat package, or canonical hold paths. The expected
schema-v2 terms and raster/model distinctions are present in the opening and
package-layout sections.

```text
rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest \
  Tools/HangboardPackages/tests/test_board_package_staging.py \
  Tools/HangboardPackages/tests/test_model_first_packages.py -q
40 passed in 0.31s

rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
exit 0; 61 complete packages; drafts: []
```

Final diff checks and the commit-scoped file inventory are run immediately
before commit. This documentation fix creates no persistent resource and does
not require a server, tunnel, simulator, or generated output cleanup.

## Commit

Commit message: `docs: align board package media contract`.
The immutable commit hash is reported to the controller after commit because a
commit cannot contain its own final hash.
