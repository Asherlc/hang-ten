# Texture manifest

| Filename | Resolution | Color space | Assigned material | Source / origin | License | Evidence status |
|---|---:|---|---|---|---|---|
| `textures/neutral-rubberwood-basecolor-1k.png` | 1024 × 1024, RGB PNG | sRGB | `Rubberwood_Neutral_Original` | Original uniform RGB (196, 177, 137), authored for this model. No photograph pixels, grain, logos, text or lighting. | CC0-1.0 dedication for this original image | Neutral approximation of the light warm wood visible in YY Vertical images. Not a measured albedo. |

One PBR material is shared by the body and every contact surface. Base color is connected through UVMap. Roughness 0.67, metallic 0 and IOR 1.45 are original neutral rendering choices, not measured manufacturer values. There are no normal, displacement, roughness, AO, emission or reflection textures. The source photographs show grain, but provide no reusable calibrated PBR maps; no grain pattern was fabricated.

The base-color image is packed into the editable `.blend`, embedded in the GLB and supplied separately. All UV islands were generated before contact separation. Body and hold surfaces have matching coordinates and shading at shared boundaries; no overlay or duplicated contact skin is used. The uniform material has no directional texture to stretch or misalign.

Brand logo, end-cap Turn & Pull engraving and numerical depth engravings are visible in the evidence but omitted from the asset. No permission to redistribute manufacturer artwork or photograph-derived textures was established. Factual depths remain available in object names and metadata.

`renders/05-neutral-material-closeup.png` shows the original material under neutral lighting. Render labels and backgrounds are presentation-only and are not texture content. Reference photographs in `evidence/` retain their original rights and are not included in the material system.
