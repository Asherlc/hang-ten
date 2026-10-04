# Independent Metolius Contact pinch-rail verification

**Pass: no technical blockers found in the frozen revised source and export. Human acceptance remains pending.**

The raw embedded manifest and all 33 contact facts are unchanged. All 31 non-pinch regions retain their areas and bounds within numerical tolerance; 29 published depth checks and the 826 × 67 × 279 mm native envelope pass. The source opens and recomputes cleanly with one valid solid. Contact surface and overlap checks pass. An independent 15 → 17 → 15 mm center-edge edit changes the final fused solid and exactly the intended contact, then restores all 33 regions without saving or altering source bytes.

Five stations per side independently show mirrored opposed, outward-facing pinch surfaces at native Y = −55 mm, where the old solid had no material. Forward projection relative to the old shell is 23.54–38.45 mm. The final exported mesh reproduces all ten witnesses with at most 0.07615 mm endpoint difference and 0.05627 mm projection difference. These figures measure the authored display model; they are not manufacturer rail dimensions or proof of hand clearance.

The USDZ contains 34 coherent meshes, 36,299 triangles and no materials, shaders or material bindings. Descriptor node memberships preserve all 33 logical contacts. Exactly the intended Contact FCStd, USDZ and descriptor changed; all 203 other package files remain byte-identical. Integrated files match the independently checked candidate.

Frozen identities:

- FCStd: `b25efa337a9ac5def16392aa574c1ec0a0659daec0f27465fb2c7d2339a1f351`
- USDZ: `d313a7162db78c57650e91b1b35338eba38290a83d4209a640afa04504e16f07`
- Descriptor: `c1ed94c1a777d7bd0d349e213e75fe907574fd61d25eff7c3e5adec142213d0f`

Evidence: [native checks](native-check.json), [export checks](export-check.json), [exported section witnesses](export-section-check.json), [package scope](final-package-scope.json), and [full hash inventory](final-independent-review.json).

Limits: native shell membership is sampled per face/vertex and supplemented by surface-overlap and standard compiler checks; five local sections do not certify all possible hand placements. Source interpretation remains the native author's responsibility. App interaction and visual acceptance are outside this technical check and remain parent-owned.
