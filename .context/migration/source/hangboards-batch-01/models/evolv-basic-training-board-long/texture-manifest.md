# Texture/material manifest

No texture maps are used or required. The GLB is self-contained and has one shared neutral material, `neutral-product-material`, on all five meshes. Linear RGBA base factor [0.07, 0.073, 0.078, 1], metallic 0, roughness 0.87. These are authored charcoal-resin display choices, not measured reflectance.

UVs use separate isometric triangle islands packed in [0,1] per mesh. Individual islands do not stretch; texel density varies. Different meshes reuse the same UV domain. A future seamless painted texture requires a new cross-object UV layout.

`evidence/originals/*.png` contains reference photographs only. They are not application textures, have no established commercial licence, and are not embedded as color/normal/roughness maps. No grain, logo, AO, light, reflection or shadow is baked into base color.

The eight actual-geometry renders use neutral uncalibrated lights, VTK review shading and an explicit sRGB output transfer. This affects render display only, not production material factors.
