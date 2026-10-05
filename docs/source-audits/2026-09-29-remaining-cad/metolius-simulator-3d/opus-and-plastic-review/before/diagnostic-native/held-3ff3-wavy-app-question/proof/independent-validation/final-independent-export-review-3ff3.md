# Independent export review

The frozen source `3ff3a891…`, USDZ `78fd9fa2…` and descriptor `e93ca8f6…` pass the independent metadata, contact, sourced-depth, envelope, unbound-material and finite geometry-coverage checks. All 30 contacts and 31 mesh nodes match; all 27 exported depth spans pass the original 0.02 mm gate (maximum error 0.000614 mm). All 203 unrelated package files are unchanged.

The actual X47 split, forward sloper spans and upper jug roll remain represented. One retained vertical-ray failure measured Z error on a steep surface; the correct Euclidean distance is 0.187846 mm, below the unchanged 0.28 mm deflection. Full native-vertex/triangle-center and reverse exported-center distances are at most 0.265723 mm. The raw failure and supplemental proof remain linked in the JSON.

The complete native tessellation is watertight. The independently tessellated semantic USDZ union is **not exactly welded watertight**: 2,973 boundary edges and 62 nonmanifold edges remain. Paired-edge winding is consistent, but 1,087 small triangles (total 6.893 mm²) contain opposing corner normals. No claim of universal normal alignment is made. Full front, side, top, high-front and rear-center images were inspected; faint center and outer seam marks remain for actual-app/Opus disposition.

No native source, exported assets or canonical files were changed. All owned native jobs exited and temporary resources were cleaned. Root app review and human acceptance remain pending. Exact hashes, raw diagnostics, measurement dispositions and image paths are in `final-independent-export-review-3ff3.json`.
