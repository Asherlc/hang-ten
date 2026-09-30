# Validation notes

All 21 CAD packages have current-source independent fresh rebuild proofs. Every model and descriptor matches the current package. Individual geometry acceptance remains pending.

## Historical reports

The following initial compile reports are superseded for final source identity. They predate metadata-only edits; their model hashes remain current. Use each package’s `reproducibility.json` for the final source, model, and descriptor identity.

- [nature-stone-hanger-mini/compile.json](nature-stone-hanger-mini/compile.json) → [final proof](nature-stone-hanger-mini/reproducibility.json).
- [nature-stone-hanger-mini-karma8a/compile.json](nature-stone-hanger-mini-karma8a/compile.json) → [final proof](nature-stone-hanger-mini-karma8a/reproducibility.json).
- [yy-baguette/compile.json](yy-baguette/compile.json) → [final proof](yy-baguette/reproducibility.json).
- [plateau-lifting-edge/compile-10.json](plateau-lifting-edge/compile-10.json) → [final proof](plateau-lifting-edge/reproducibility.json).
- [plateau-lifting-edge/compile-15.json](plateau-lifting-edge/compile-15.json) → [final proof](plateau-lifting-edge/reproducibility.json).
- [plateau-lifting-edge/compile-18.json](plateau-lifting-edge/compile-18.json) → [final proof](plateau-lifting-edge/reproducibility.json).

The original reports are retained unchanged as historical records.

## Individual review revisions

The initial independent batch review applies to commit `583a2d08`. Cyclops’s shorter cord supersedes its prior suspension identity; [current cord proof](aelith-cyclops-011/cord-shortening-verification.json) and [runtime validation](aelith-cyclops-011/shorter-cord-runtime-validation.json) cover the change. Its CAD source, USDZ and descriptor remain identical. The current delivery digest covers the revised sidecar.

DUAL’s initial front-entry correction is historical evidence for sidecar `0c824dd…`: [native proof](captain-fingerfood-dual/cord-entry-verification.json), [runtime proof](captain-fingerfood-dual/cord-entry-runtime-validation.json), and [before/after views](captain-fingerfood-dual/front-mouth-review/index.html). Its recorded 569 Python and 1,258 iOS passes belong to that revision.

The current DUAL sidecar is `0d90fd3…`. The user accepted the general front-hole entry and immediately questioned the lower cord's sideways bow at 90°. [Current native proof](captain-fingerfood-dual/vertical-tightening-review/verification.json), [runtime proof](captain-fingerfood-dual/vertical-tightening-review/runtime-validation.json), [all four pose comparisons](captain-fingerfood-dual/vertical-tightening-review/index.html), and [fresh app captures](captain-fingerfood-dual/vertical-tightening-review/app-review/index.html) cover the subsequent local 3D tightening. Source, USDZ, descriptor, mouths, cord dimensions, rotations and cameras remain unchanged. Exact native apply/check reports are byte-identical; current test counts and cleanup are in the runtime report. Physical DUAL UI orbit remains unverified. The revised vertical shape awaits human review.
