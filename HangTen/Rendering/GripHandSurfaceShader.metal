#include <metal_stdlib>
#include <RealityKit/RealityKit.h>

using namespace metal;

[[visible]]
void gripHandSurfaceShader(realitykit::surface_parameters params) {
    params.surface().set_base_color(half3(params.geometry().color().rgb));
    params.surface().set_roughness(0.9h);
    params.surface().set_metallic(0.0h);
}
