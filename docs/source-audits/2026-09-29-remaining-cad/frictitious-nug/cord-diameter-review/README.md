# NUG cord-diameter correction previews

Retained manufacturer evidence specifies **6 mm cord**. The prior sidecar modeled 3 mm diameter; the corrected sidecar uses 6 mm and native-solved routes for all six poses. Human acceptance remains pending.

- [Prior raster beside current native body](body-prior-raster-overview.png)
- [Six saved-camera pose comparisons](six-pose-overview.png)
- [Default and inverted front/side/top comparisons](default-inverted-three-view-overview.png)
- [All 48 comparisons and six after views](index.html)
- [Render provenance](render-provenance.json), [overview provenance](overview-provenance.json), [inspection report](inspection-report.json)
- [Immutable before evidence](before/snapshot-provenance.json)

The body overview retains complete prior primary/reverse raster images next to existing unchanged native front, side, top and oblique renders. No prior CAD side/top existed. Images are independently fitted, never cropped or registered; body-overview cells do not share a physical scale.

Every cord before/after pair shares a body-centered scale. Front, side, top and the exact saved canonical camera each have full-support and body-detail views for every pose. Actual mesh z-buffer occlusion is used. Analytic constant-radius spheres close interior route joints and disk caps close segment ends in the preview mesh only. Every source route point and radius is unchanged. Earlier uncapped previews were retained in workspace scratch. Top-view projected crossings collapse height and are not 3D collision certificates.

Before SHA-256: `c5b9d494d8a7d0de6c955db08f8449051216d474736a1d9b08e81f9665fd4088`, from commit `47d472b57ff86cfbea2dafbe87e40b9e5c3ad4ee`. After: `4f2971de05766f9d20f6eb8dde0cd311d03d5c0c6845b586725af0d689aa1ef3`. All six Y translations change from −163.570590 mm to −162.422559 mm, raising the body 1.148031 mm. CAD, USDZ and descriptor hashes remain unchanged. All 46 before files and 45 original audit files were reverified.

These are technical geometry previews, not Simulator captures or clearance certificates. Root/portable own independent native certificates and app proof. This lane changes only preview artifacts.
