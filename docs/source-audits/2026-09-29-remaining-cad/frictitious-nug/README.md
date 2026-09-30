# The NUG — review #4

The native CAD body is 130 × 60 × 40 mm, with 20/25/8/13 mm edges, a 40 mm jug and a 60 mm opposing pinch span. The [retained manufacturer product page](evidence/product-page-current.html) also specifies **6 mm rated climbing cord**; [manufacturer URL](https://frictitiousclimbing.com/products/the-nug). Unlisted body dimensions and the 300 mm per-lead length remain display estimates.

The cord diameter is corrected from 3 mm to 6 mm. Four exposed leads retain their actual entrance wells, with unknown hidden connections left unspecified. The native solver regenerated all six poses. Body/source/model/descriptor, contacts, topology, anchor, terminal positions, lengths, rotations and cameras are unchanged. All 205 other files in the retained package-file baseline remain identical.

- [Body beside prior committed raster, with front/side/top/oblique views](cord-diameter-review/body-prior-raster-overview.png)
- [Current cord comparisons](cord-diameter-review/index.html)
- [Fresh app views](cord-diameter-review/app-review/index.html)
- [Native verification](cord-diameter-review/verification.json), [runtime verification](cord-diameter-review/runtime-validation.json), [current identities](final-hash-closure.json)
- [Exact source/body audit](native-authoring.md), [unchanged body rebuild](reproducibility.json)

Fresh native apply/check reports are byte-identical across six poses. All 24 complete rounded routes pass native solid, tube, actual entrance and length checks. The corrected package passed 31 Python package checks and 239 focused iOS tests. Installed delivery matches all 64 generated packages and 60 ODR models. The owned simulator, DerivedData and result bundle were removed, and deletion was verified.

The original source/body packet remains unchanged. Its radius-dependent cord certificates, camera rebinding, `validation.json` and original app captures describe the prior 3 mm cord and are historical; use the current cord packet linked above. Preview inspection records describe their capture-time state. Only the six canonical app views were checked; physical UI orbit remains unverified. Human acceptance is pending the requested one-by-one review.
