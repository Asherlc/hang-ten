# Blender background startup diagnostic

Date: 2026-09-09
Owner: `shaky-rat` (workspace `0h78jp9r/shaky-rat`)
Scope: establish a reliable Blender 5.2 background invocation for the Beastmaker compiler. No board source, geometry, Astra assets, evidence packet, or Compact II resource was changed or run.

## Root cause

Blender 5.2.0 LTS (`fbe6228777e7`, built 2026-07-14) crashes during factory-startup graphics initialization when invoked in this workspace's shell sandbox. The failure occurs before Blender loads a `.blend` file or executes a `--python` script, so it is infrastructure-bound rather than a compiler, fixture, or board-data failure.

The exact minimal sandbox reproduction was:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python-expr "print('BLENDER_FACTORY_STARTUP_PYTHON_OK')"
```

It exited `139` and printed:

```text
ArchWarn: ARCH_CACHE_LINE_SIZE != Arch_ObtainCacheLineSize()
Function: Arch_ValidateAssumptions
File: .../pxr/base/arch/assumptions.cpp
Line: 140
Writing: /var/folders/b4/95kqjtzd7zlc75ndbg2_svpr0000gp/T/blender.crash.txt
[rtk] blender: process terminated by signal 11
```

This agrees with the retained prior failure at `.context/shaky-rat-beastmaker-1000/compiler-invalid-rerun-infrastructure-failure.txt`, including its `supports_barycentric_whitelist` Metal-backend stage. The warning from `Arch_ValidateAssumptions` appears even for `blender --version`, but only the sandboxed factory-startup path segfaults.

## Validated invocation boundary

Run Blender through the documented command unchanged, but in the approved host environment (outside this workspace shell sandbox) whenever it needs factory-startup graphics initialization:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python-expr "print('BLENDER_FACTORY_STARTUP_PYTHON_OK')"
```

The approved-host result was exit `0`:

```text
BLENDER_FACTORY_STARTUP_PYTHON_OK
Blender 5.2.0 LTS (hash fbe6228777e7 built 2026-07-14 01:31:22)
Blender quit
```

No environment-variable workaround, alternate backend, or source change was introduced. The documented `rtk proxy blender --background --factory-startup` form in `Tools/HangboardModels/README.md` and `Tools/HangboardPackages/README.md` is therefore still the correct entrypoint; the caller's execution boundary is the differentiator. A script cannot grant itself host graphics access. If a future automation layer calls Blender from a sandbox, it must request the corresponding approved/unsandboxed execution there. No repository command/document change is warranted by this test.

## Semantic compiler proof

The documented Beastmaker negative fixture was then run only in that approved host environment:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/compile_model_package.py -- \
  --blend .context/shaky-rat-beastmaker-1000/invalid-unknown-hold.blend \
  --board-json Hangboards/beastmaker-1000/board.json \
  --output-directory .context/shaky-rat-beastmaker-1000/compiler-scratch-invalid
```

It exited `1` after reading the fixture and reached the intended semantic rejection:

```text
ValueError: hold mesh InvalidUnknownHold has unknown hold_id: unknown
Error: script failed, file: 'Tools/HangboardModels/compile_model_package.py', exiting.
Blender quit
```

The exact owned scratch directory `.context/shaky-rat-beastmaker-1000/compiler-scratch-invalid` was absent after the command, and so was `assets/primary.model.json`; no descriptor or package was left behind. This is consistent with the retained successful evidence in `.context/shaky-rat-beastmaker-1000/compiler-invalid-validation.txt`.

## Resource lifecycle

The single bounded sandbox reproduction created the exact transient crash file `/var/folders/b4/95kqjtzd7zlc75ndbg2_svpr0000gp/T/blender.crash.txt` (1,293 bytes). Its diagnostic output is recorded above; the file was deleted after capture and verified absent. No HTTP server, tunnel, simulator, temporary directory, geometry output, or external resource was created. Durable evidence under `.context/shaky-rat-beastmaker-1000` was preserved.
