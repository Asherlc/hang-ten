# Catalog finger capacity

Reviewed 2026-10-06. The user requested a capacity on every hold and authorized
reviewed estimates when manufacturers do not publish counts. The
[contact mappings](2026-10-06-finger-capacity.json) identify each newly authored
value, its native source, product evidence URL, basis, and reasoning.

Capacity means the practical number of non-thumb fingers from one hand that can
engage the physical contact, capped at four. It does not describe the number of
hands, prescribe a workout grip, or guarantee fit for every hand size. Physical
hold geometry and identity govern review; small highlighted contact regions do
not necessarily bound the usable hold.

The audit fills 626 previously unspecified contacts across 63 boards. The 252
existing counts retain their prior source mappings and values. All 878 contacts
across 66 catalog boards now specify an integer from 1 through 4.

The mappings distinguish `reviewedEstimate` from `manufacturerDefinition`.
Product URLs establish retained hold identity and geometry; they are not a
claim that the manufacturer publishes an estimated count. Retired or changed
pages retain their provenance through the existing board source audits and
native documents.

| Reviewed hold family | Capacity | Evidence and decision |
| --- | --- | --- |
| Open edges, jugs, slopers and broad pinch faces | 4 | Retained board geometry and physical hold identity reviewed as whole-hand surfaces. This includes all Grindstone Mk2 edges and its top jug. |
| Captain Fingerfood DUAL / UNLEVEL short pocket end walls | 1 | Retained native cavity end walls are approximately 26 / 22 mm across; these small contacts are distinct from the broad cavity floor. |
| deWoodstok Woodbord narrow upper/lower slots 2 and 5 | 2 | [Product inventory](https://www.dewoodstok.nl/product/hangboard-woodbord/) publishes two-finger and four-finger depth families; the position mapping is reviewed against retained native slots. Other broad pockets receive 4. |
| Frictitious Doormount Pro compact pockets 6 and 7 | 2 | Reviewed estimate for the retained approximately 36 mm pockets; [product evidence](https://frictitiousclimbing.com/en-ca/products/doormount-pro) establishes hold identity. |
| Lattice MXEdge Lift mono, both sizes | 1 | [Manufacturer catalogue](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf), page 2, explicitly identifies a mono: 28 mm large / 25 mm small. |
| Mammut Diamond Finger mono / upper inset / broad upper pockets | 1 / 2 / 4 | Reviewed estimates from the retained native regions and [manufacturer manual](https://static.mammut.com/file/2060-00020_man_en_070420_DiamondFingerHangboard_Manual.pdf). The manual does not publish these counts. |
| So iLL Training Tiles broad top pockets | 4 | Reviewed whole-hand estimate from retained geometry and [product evidence](https://soill.ca/products/training-tiles-so-ill-x-meagan-martin). |
| Trango Rock Prodigy Training Center shallow slots / paired finger pockets | 3 / 2 | Retained cavity geometry and [manufacturer instructions](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155) reviewed together. The detailed mapping conservatively labels the assignments as estimates. |

All edits use `set_board_manifest.py`. It verifies that every archive member
except `Document.xml` is byte-identical; geometry, contact IDs, bindings, and
training prescriptions do not change. Native assets are rebuilt because their
descriptors and suspension metadata bind to the complete source hash. Package
validation and the iOS reader require explicit capacities, and regression tests
check that the authored values agree with these mappings.
