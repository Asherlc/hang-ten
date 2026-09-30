# Mouth well export diagnosis

The USDZ contains all four modeled mouth wells. Front and rear center/interior rays first hit the native body floor 4 mm behind the outer face. Every tested first hit belongs to the body node, not a contact binder. Native/export disagreement is below 0.000001 mm.

The floor and surrounding face have essentially identical authored normals; cylindrical walls are edge-on from a straight front view. Normal-only flat lighting therefore gives little or no mouth contrast. This is a shading limitation, not an exported cap. The 4 mm well depth remains an audited display estimate; no hidden channel is implied.

[Exact ray results and hashes](mouth-well-export-rays.json) · [Native/export section comparison](review/mouth-well-native-export-sections.png)

No source, asset, sidecar, geometry or renderer file was changed for this diagnosis.
