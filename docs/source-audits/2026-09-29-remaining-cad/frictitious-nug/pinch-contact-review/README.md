# NUG pinch: upper/lower wraparound bands

The user clarified **upper and lower rims onto front/back**. The final compiled descriptor highlights those two wraparound bands for `pinch-60`, leaving the side/end rims, pocket interiors and cord wells excluded. The original upper `jug-40` patch remains shared with pinch and unchanged for jug selection.

- [Final USDZ front/rear/oblique extent](pinch-60-wraparound-overview.png)
- [Pinch before/after front, side, top and oblique](pinch-60-overview.png)
- [Full oblique comparison](pinch-60-oblique.png) and [rear comparison](pinch-60-rear.png)
- [Jug remains upper-only](jug-40-overview.png)
- [All ten full comparisons](index.html)
- [Render and geometry provenance](render-provenance.json), [overview provenance](overview-provenance.json), [inspection report](inspection-report.json)
- [Immutable before package and app evidence](before/snapshot-provenance.json)

These previews independently import the exact committed-before USDZ and the final published USDZ. Each pair shares its camera and numeric viewport scale. Red is preview-only shading derived exclusively from the corresponding descriptor's node memberships. One upper mesh is rendered once. No package materials, runtime files, geometry or cord paths are changed by this preview lane.

The before commit is `b3b5fe2b588c74bcb3ddd2d7b43478308f5a5ffb`. All 20 before files remain exact, including the original native source, USDZ, descriptor, sidecar and 16 prior app-review artifacts. Rejected top/bottom-only and whole-rim assumptions and provisional native diagnostics remain in workspace history; none are represented as final proof here.

Final SHA-256 values:

- Native source: `03ae5ecea7a1836b7c3aa695d1bd9618c0f5e36af3d05bba1cc62bebf45e7208`
- USDZ: `9b24f881059a7d79afd3b676da6324b3d0d65fb0977e2eab100b88bfa5a5e800`
- Descriptor: `c6ecc298e414726f5b543de89d7e22ee6d6180ff56dd71777f71a95624db3a9e`
- Sidecar: `8a3fdf291c1ef34588425a4a7a73524fab33abdbb5a561456d571ecdd86642fc`

Native face seams give the four return patches real mesh boundaries. The source-bound author proof reports a valid single solid, zero added/removed solid volume, zero added/removed boundary area, and zero boundary distance from the original wood. The retained original wood and jug BREP archive bytes are unchanged. Final combined triangulation differs, as recorded honestly in provenance; raw triangle identity is not claimed. Each planar return is 846 mm² with four native body triangles and zero triangles crossing its boundary. These are authored display-region boundaries, not manufacturer finger-placement measurements.

The cord sidecar differs only in `modelSHA256`; all route coordinates, radii and six poses are identical. These contact-only technical renders omit cords for clarity. Both contact overviews, the front/rear/oblique extent overview, full pinch oblique and jug rear comparisons were physically inspected. All ten pair hashes, three overview hashes and four frozen package hashes pass. Fresh app proof and integration validation remain root-owned. **Final human visual acceptance remains pending.**
