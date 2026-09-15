# Texture manifest
No texture image is used. Every rendered mesh uses one shared neutral PBR material.

| Item | Resolution / colour space | Assignment | Origin / rights | Approximation |
|---|---|---|---|---|
| neutral-product-material | No image; glTF baseColorFactor in linear RGB | All body/contact meshes | Original authored numeric material | Not measured colour or photographed wood grain |

No invented grain, logos, labels, stone pattern, lighting or shadows are embedded.
The GLB has no external material dependencies. Research images are not licensed app textures.
UVs are independent isometric triangle islands in a non-overlapping per-mesh atlas. Island
texel density varies; each mesh reuses the 0–1 atlas domain, so different mesh atlases overlap.
No texture is affected by this. Reunwrap for hand-painted or continuous grain textures.
