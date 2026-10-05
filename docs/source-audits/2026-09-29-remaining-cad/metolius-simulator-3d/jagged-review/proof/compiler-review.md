# Simulator compiler opt-in review

No blocking code findings remain for compiler `f4c0d4c2a9c79c02d349be2f71a14962fde3c5c2fa13b24b0b34d425272fc50d`. Review of the initial `0f3c473c…` version led to two resolved findings: invalid-normal UV records now remain ambiguity witnesses, and test cleanup always terminates the exact owned process group before removing scratch. The author also added a native C0-knot regression and guard; unsafe knot vertices retain the original inverse evaluator.

Exact face-facet ownership, spatial UV correspondence, analytic-normal winding/remap, missing-data fallback, boolean metadata validation and unchanged default dispatch were reviewed. No geometry, materials, node identity or tessellation-policy changes were introduced by this diff.

Retained proof reports nine native cases through one passing host test and 84 adjacent passing tests. I did not rerun them. The final source-bound comparison covers 71 triangles/213 corners, including the previously failing boundaries, with exact positions and maximum normal angle difference `8.537736462515939e-07` degrees. The default-false report binds the final compiler and original 9449 source; I verified the retained USDZ/descriptor bytes equal the original hashes.

Source `8fa07c20…` differs from validated geometry source `40e42ed0…` only in `Document.xml`; I independently compared all archive members and confirmed 387 exact B-reps. The old source header is superseded by the opt-in bool; its geometry was not rejected.

Final check/export, current independent mesh proof, Python/iOS/app validation and human review #8 remain separate gates. No tracked edits or external resources were made. Exact input/proof hashes and resolved findings are in [compiler-review.json](compiler-review.json).
