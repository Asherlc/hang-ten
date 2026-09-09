# Task 2 fix 1 brief

Fix the Task 2 review findings without adding a board registry, a standalone
resource path, name normalization, or a model-to-raster route.

- Route `BoardMapView` exhaustively by typed media. Only the raster branch may
  construct an image/path surface; `BoardModelSurface` has no fallback closure.
- Give model loading an explicit non-interactive loading state and an explicit,
  non-interactive `boardModel.unavailable` state.
- Pass package `display.camera` and validated descriptor `modelBounds` through
  the loader. Derive the orthographic target, direction, basis, fit, and light
  placement from those values.
- Reject geometry attached to the imported root, since it cannot belong to an
  exact descriptor node path.
- Restore focused coverage for model surface states, exact bindings, root
  geometry, framing/rebind, cloned materials, closest native hit/body nil, the
  package store's model URL/image distinction, missing runtime bytes, and SHA
  cache-key separation.
