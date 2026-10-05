# Poker #12 package validation preparation

Prepared only. No package check, test, staging job, or iOS build has run.

Root must supply the final promoted FCStd, USDZ, and descriptor SHA-256 values in a copy of `frozen-input.template.json`; an optional generated-manifest hash can also pin its exact bytes. Pending hashes are rejected before any process/resource allocation. `baseline-board.json` is the hash-pinned preflight snapshot. The manifest comparison permits only `primary.media.display.surfaceFinish: wood`, preserving all 34 contact facts, all four ordered positions and rotations, and the existing absence of suspension.

After root supplies the frozen final input, execute from this exact workspace:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 python3 .context/placid-badger/poker-review12/package-validation-2026-10-02/run_validation.py --frozen-input .context/placid-badger/poker-review12/package-validation-2026-10-02/frozen-input.json
```

The driver runs the retained descriptor/package/import/YY model-tool tests; board_manifest, cad_sidecars, board_catalog and pose_camera_facing tests; the canonical package CLI directly through its module to avoid modifying a shared venv; actual Android staging byte parity; and one generic iOS Simulator `build-for-testing`. Each step retains raw logs and provenance, owns a bounded process group, and deletes its exact owner-prefixed TMP/staging/Derived Data resource paths after capturing evidence. The iOS helper records an attempt before spawning, so it cannot silently retry the single build.

No simulator guest is created, booted, installed, launched, or accessed. No HTTP server is started. No app frame is captured. Zero iOS unit test cases run; the test bundle is compiled only. The runtime environment was previously blocked and current appearance remains unverified. No geometry or human acceptance is inferred from compile/package checks.

See `preparation.json` for planned scopes, bounds, script hashes and the frozen-input contract. See generated `package-validation.json`, per-job ownership/cleanup/log files and `ios-build/build-validation.json` only after authorized execution.
