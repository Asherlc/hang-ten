# Validation notes

All 21 CAD packages have current-source independent fresh rebuild proofs. Every model and descriptor matches the current package. Individual review scopes are recorded separately; the remaining 18 boards await acceptance.

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

The current DUAL sidecar is `0d90fd3…`. The user accepted the general front-hole entry and immediately questioned the lower cord's sideways bow at 90°. [Current native proof](captain-fingerfood-dual/vertical-tightening-review/verification.json), [runtime proof](captain-fingerfood-dual/vertical-tightening-review/runtime-validation.json), [all four pose comparisons](captain-fingerfood-dual/vertical-tightening-review/index.html), and [fresh app captures](captain-fingerfood-dual/vertical-tightening-review/app-review/index.html) cover the subsequent local 3D tightening. Source, USDZ, descriptor, mouths, cord dimensions, rotations and cameras remain unchanged. Exact native apply/check reports are byte-identical; current test counts and cleanup are in the runtime report. Physical DUAL UI orbit remains unverified. The user subsequently replied “lgtm” to the inline front/side/top comparison, accepting the revised displayed vertical routing; [exact approval scope and shown hashes](captain-fingerfood-dual/human-review.json). Technical reports retain their dated pre-approval pending labels. Review then advanced to UNLEVEL (#3).

UNLEVEL’s current sidecar is `83d4fae…`. A manufacturer-reference audit found rear entry in three prior poses. [Current native proof](captain-fingerfood-unlevel/front-entry-review/verification.json), [runtime proof](captain-fingerfood-unlevel/front-entry-review/runtime-validation.json), [front/side/top comparisons](captain-fingerfood-unlevel/front-entry-review/index.html), and [fresh app captures](captain-fingerfood-unlevel/front-entry-review/app-review/index.html) cover the source-backed front-hole correction. Exact four-pose apply/check reports are byte-identical; 31 package tests and 1,258 iOS tests passed, with 3 iOS skips. Physical UI orbit remains unverified. CAD source, USDZ, descriptor and the other 205 package files remain unchanged. Root UNLEVEL cord/app reports describe the prior sidecar `d689a72…`; the revised packet retains before evidence separately. The user answered “Y” to the inline body/default/90° comparisons, accepting that displayed revision; [exact approval scope and shown hashes](captain-fingerfood-unlevel/human-review.json). Frozen technical reports retain their dated pre-approval pending labels. Review has advanced to Frictitious The NUG (#4).
