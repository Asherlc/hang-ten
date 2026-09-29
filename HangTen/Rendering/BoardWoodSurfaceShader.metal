#include <metal_stdlib>
#include <RealityKit/RealityKit.h>

using namespace metal;

[[visible]]
void boardWoodSurfaceShader(realitykit::surface_parameters params) {
    // CAD meshes share board-space coordinates in metres. A volume pattern
    // stays aligned across body/contact boundaries, inside recesses, and while
    // orbiting; no UVs, textures, or geometry changes are needed.
    float3 p = params.geometry().model_position();
    float warp = 1.4f * sin(p.x * 9.0f + p.y * 13.0f)
               + 0.35f * sin(p.x * 31.0f + p.z * 23.0f);
    float radius = length(float2(p.y + 0.18f, p.z + 0.06f));
    float phase = radius * 1500.0f + warp;
    // Filter fine fibres as the board shrinks into a picker thumbnail.
    float bandFilter = 1.0f - smoothstep(0.5f, 3.0f, fwidth(phase));
    float fibrePhase = phase * 3.7f + sin(p.x * 45.0f);
    float fibreFilter = 1.0f - smoothstep(0.5f, 3.0f, fwidth(fibrePhase));
    float broad = sin(p.y * 43.0f + sin(p.x * 6.0f) + p.z * 17.0f);
    float variation = 0.035f * broad
                    + 0.025f * sin(phase) * bandFilter
                    + 0.008f * sin(fibrePhase) * fibreFilter;
    half3 tint = half3(params.material_constants().base_color_tint());
    params.surface().set_base_color(tint * half(1.0f + variation));
    params.surface().set_roughness(0.82h);
    params.surface().set_metallic(0.0h);
}
