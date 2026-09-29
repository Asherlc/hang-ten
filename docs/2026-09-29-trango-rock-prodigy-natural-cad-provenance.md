# Trango Rock Prodigy Natural CAD provenance

This record covers `trango-rock-prodigy-natural.FCStd`. The FreeCAD document is
the geometry and metadata source. Its `HangTenBoardManifest` generates
`board.json` at build time; the USDZ and descriptor are compiled outputs.

## Evidence

The product is the two-piece Rock Prodigy Natural, not another Rock Prodigy
revision. [Trango's product page](https://trango.com/products/rock-prodigy-natural)
states 7.5 × 6 × 1.5 inches per half, two variable-depth rails (10–33 mm),
three pockets (27–38 mm), and a 10 mm closed crimp. The following distinct
manufacturer photographs were retained under workspace scratch for visual
review. Hashes are of the downloaded original JPEG bytes.

| Photograph | SHA-256 | Evidence used |
| --- | --- | --- |
| [Top-down image with markings](https://cdn.shopify.com/s/files/1/0282/7557/2841/products/22850_RockProdigyNatural_MainImage_TopDownMarkings.jpg?v=1755037315) | `5c2d801f7b749a8efa14cf4507c67f37ec2ecd0b14de131938e91f1d53bebd12` | Front silhouette and hold arrangement; printed 20/33, 10/24, 10, 38, 30, 27, and 27 mm marks. |
| [Side image](https://cdn.shopify.com/s/files/1/0282/7557/2841/products/22850_RockProdigyNatural_AltImage4_Side.jpg?v=1664571868) | `a188c75b8333c6a5ab031f4d8da159bf441beda23cf38b6bf7c5ff1d2efb443d` | Top jug profile and rear relief. |
| [Rail close-up](https://cdn.shopify.com/s/files/1/0282/7557/2841/products/22850_RockProdigyNatural_AltImage2_Rails.jpg?v=1724692982) | `99c36994b3a6ac049536b4b9b4d1f75b63c46b8bf72910b3c7616941d43de0f8` | Closed-crimp tongue, knob, and surrounding recess. |
| [Pocket close-up](https://cdn.shopify.com/s/files/1/0282/7557/2841/products/22850_RockProdigyNatural_AltImage1_Pockets.jpg?v=1724692982) | `619f8806c276f00b07308a1c466f3c6c6ba04427105016a390f6af6ed0471257` | Pocket topology and supported-pocket lobes. |
| [Oblique product photo](https://cdn.shopify.com/s/files/1/0282/7557/2841/products/RPShootBaker_Natural_11.jpg?v=1724692982) | `6f53af1b8a920d026bdb34d12f45d944594cca0a7b2fb43e43b55fc476e6e9ac` | Front face meeting the jug and relief behind it. |

The pre-migration display model is retained in Git at `649c41c93` (USDZ
SHA-256 `f913ecd901834c9e000ecc660144625c70e453856e150de9dd119b5bf6a0f17e`).
It was used for qualitative comparison, not as the authority for the front
layout. The photographs and old model disagree by several millimetres around
the rails, lower pockets, lower tier, and jug profile.

## Authoring decisions and limits

The operator read the front coordinates from gridded crops of the top-down
photograph and deliberately drew each sketch path. The front calibration used
the 190.5 mm half-width at 4.911 px/mm, vertical correction 1.0302, and an
origin of (1237.2, 983.4) pixels. The source holds two exactly mirrored halves.
The product photo places the halves close together, while the app presentation
uses a 100 mm gap; overlays against that photo assess one half at a time.
The side profile was read from the side photograph at 18.09 px/mm, normalized
to the 38.1 mm published thickness. These are display-geometry estimates, not
manufacturer CAD dimensions or load-bearing specifications.

The rail floors interpolate between the printed 20→33 and 10→24 mm endpoints.
The three pocket openings use the printed 38, 27, and 27 mm depths; the outer
lobe of the supported pocket reaches the printed 30 mm mark. Its photographed
three-lobe shape is simplified to a 27 mm stadium with one 30 mm outer lobe.
The crimp recess is 10 mm deep, with its tongue and knob drawn from the
top-down and rail photographs. The jug uses a quarter-ellipse at the front, a
rounded crest, and a relieved rear shelf drawn from the side view. Its
published 40 mm label exceeds the 38.1 mm board thickness; its contact region
therefore spans the full board thickness as required by the compiler gate.

The 1 mm mouth and 2 mm floor round-overs are display estimates. The supported
pocket floor uses 1 mm because 2 mm made an invalid OCCT solid. Mounting bores
and hardware are omitted from this display model, including the bore in the
supported pocket and three upper fastener holes. Their omission says nothing
about the physical product.

The photos show tier lines near native z ≈ −40 mm, while the side photograph
suggests a front step of about 7.9 mm. The available views do not resolve which
tier projects, so the CAD source keeps the old display model's flush front.
That detail needs physical-board confirmation before claiming product fidelity.

All 14 existing physical contact IDs are retained. Each contact region copies
faces from the final body solid and has an operator-authored outline. The
compiled asset has unbound meshes, with no materials or textures. The copied
regions are static; a later geometry edit must re-author those regions before
recompiling, so sketch edit propagation is not claimed for contact bindings.
All 14 contact node IDs also remain unchanged. The prior two body nodes and
two bottom-edge `pinch_thumb` body-surface nodes are consolidated into one
`body_001` node; the bottom faces remain part of the body solid.

## Verification

The generated manifest parses identically to the former committed
`board.json`, including all 14 contact IDs. The compiler reopened the saved
source, passed its published-depth and region partition gates, and exported
15 nodes (one body plus 14 contacts). The two mirrored rails measure 32.831
and 23.816 mm maximum exported depth after round-overs; the paired pockets and
crimp measure 38, 30, 27, and 10 mm. The jug spans the 38.1 mm board thickness.
The exported USDZ contains no Material or Shader prims, material bindings, or
texture assets.

The front, side, and top renders were compared with the prior committed asset;
the left front was also overlaid on the manufacturer photo. The iPhone 17 Pro
simulator built and loaded the compiled package, and selecting `top-jug-left`
highlighted its exported contact surface. The workspace-owned simulator was
deleted after its screenshots were captured. The package validator and Android
staging passed; Android staging generated `board.json`, excluded the FCStd,
and copied the exact compiled asset and descriptor bytes. The retained Python
tool suites passed with 445 tests and 11 skips using the pinned meshoptimizer
v1.0 native library built in workspace scratch.
An independent rebuild produced the USDZ and descriptor byte-identically on
the pinned macOS FreeCAD toolchain
(USDZ SHA-256 `7d45a021e670877c5fe00f79b036df3e1bb7cfd5ac784f3e4132b968278e9355`).
