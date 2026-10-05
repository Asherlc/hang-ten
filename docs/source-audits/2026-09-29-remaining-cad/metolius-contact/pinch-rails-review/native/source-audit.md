# Metolius Contact forward pinch rails — review candidate

Scope: Metolius Contact only. This candidate corrects the two outer variable pinch rails after the user identified that the previous smooth-envelope contact bands offered no forward-projecting feature to pinch. It is awaiting individual human visual review; it is not accepted by these technical checks.

## Retained primary evidence

The exact approved evidence set remains the complete manufacturer product photograph and complete numbered manufacturer depth diagram retained under `docs/source-audits/2026-09-29-remaining-cad/metolius-contact/sources/`.

- `product-01.jpg`: Metolius product photograph, https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Contact-Hangboard-black-white.jpg?v=1759459002, SHA-256 `b9cf153d82f0072ae2e4b0064821dee1d666ff1d8b34ba21fed1fcfd6944c055`. Supports the continuous outer rails, their forward relief and widening rounded lower ends.
- `product-02.jpg`: Metolius numbered diagram, https://cdn.shopify.com/s/files/1/0955/0030/4457/files/con-num-dep_341f2901-a11e-4256-a4c3-0531110c730e.jpg?v=1762201170, SHA-256 `6c824af42552a9ed12f7e336dac47d9a2c61441b6f90515d196f3484ad0a1202`. Identifies feature 1 as variable pinches and supports the original published pocket, edge and sloper facts.

No pixels were measured, traced, segmented, vectorized, aligned or cropped. No reference mesh geometry was used to generate the rails.

## Construction and estimates

The exact current committed FCStd, USDZ and descriptor were frozen from commit `5cfd5b6386b283b2eb8daefc054a42823fdf852b`; see `frozen-reference.json`. These are the before assets in all comparison panels.

Five fully constrained native Sketcher sections deliberately describe the right rail using eight cubic Bezier spans in each section. The analytic loft intersects the existing CAD silhouette envelope, mirrors exactly to the left, and fuses with the unchanged already-pocketed native solid. `BodyWithPinchRails` is the final tagged body; `BodySolid` remains the untagged original parametric pocket construction. The original 31 non-pinch native contacts and embedded board manifest are unchanged.

Pinch contacts are the exposed boundary of each rail. Native surface binders reference every stable face of the authored loft and existing silhouette envelope. Intersections and a union produce the clipped rail skin; subtraction of the original pocketed solid removes buried surfaces. The left contact mirrors the right. Thus the contact regions follow native rail-depth changes, remain surface-only and lie on the final solid. They are neither independent floating sheets nor smooth-envelope highlight bands.

Every new Bezier pole, rail width, section scale, corner treatment and depth placement is an operator-selected display estimate. The front rail surface reaches the existing 67 mm envelope; this does not claim a manufacturer-published rail projection. `authored-design.json` records the exact authored profile and stations. `rail-access-check.json` measures local projection and opposing surface normals from the candidate CAD and labels those as display estimates. These are geometric accessibility checks, not ergonomic or manufacturing validation.

The original 826 × 279 × 67 mm envelope and all published pocket, edge and sloper depth facts are retained. The metadata inventory remains 33 contact IDs. Mounting holes, screws and hardware remain omitted under repository display-model policy. The runtime asset must contain no materials, textures, shader prims or material bindings.

## Review and limitations

`review/comparison-{front,side,top,oblique}.png` use the same renderer and matched camera/size on the exact before and after USDZ assets. CPU previews shade triangle face normals; final app appearance and picking remain parent integration work. Native checks, deterministic export reports and the independent review report provide technical evidence; none substitutes for the user's individual visual acceptance.
