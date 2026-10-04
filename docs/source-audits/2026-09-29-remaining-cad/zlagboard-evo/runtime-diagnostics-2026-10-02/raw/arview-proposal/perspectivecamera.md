<!--
{
  "availability" : [
    "iOS: 13.0.0 -",
    "iPadOS: 13.0.0 -",
    "macCatalyst: 13.0.0 -",
    "macOS: 10.15.0 -",
    "tvOS: 26.0.0 -",
    "visionOS: -"
  ],
  "documentType" : "symbol",
  "framework" : "RealityKit",
  "identifier" : "/documentation/RealityKit/PerspectiveCamera",
  "metadataVersion" : "0.1.0",
  "role" : "Class",
  "symbol" : {
    "kind" : "Class",
    "modules" : [
      "RealityKit"
    ],
    "preciseIdentifier" : "s:17RealityFoundation17PerspectiveCameraC"
  },
  "title" : "PerspectiveCamera"
}
-->

# PerspectiveCamera

A virtual camera that establishes the rendering perspective.

```
@MainActor @preconcurrency class PerspectiveCamera
```

## Overview

During an AR session, RealityKit automatically uses the device’s camera to
define the perspective from which to render the scene. When rendering a
scene outside of an AR session (with the view’s
[`cameraMode`](/documentation/RealityKit/ARView/cameraMode-swift.property) property set to
[`ARView.CameraMode.nonAR`](/documentation/RealityKit/ARView/CameraMode-swift.enum/nonAR)), RealityKit uses a
[`PerspectiveCamera`](/documentation/RealityKit/PerspectiveCamera) instead. You can add a perspective camera anywhere in
your scene to control the point of view. If you don’t explicitly provide
one, RealityKit creates a default camera for you.

## Topics

### Creating a camera

[`init()`](/documentation/RealityKit/PerspectiveCamera/init())

Creates a perspective camera entity.

## Relationships

### Conforms To

[`Hashable`](/documentation/Swift/Hashable)

[`CoordinateSpace3DFloat`](/documentation/Spatial/CoordinateSpace3DFloat)

[`HasHierarchy`](/documentation/RealityKit/HasHierarchy)

[`HasSynchronization`](/documentation/RealityKit/HasSynchronization)

[`HasTransform`](/documentation/RealityKit/HasTransform)

[`SendableMetatype`](/documentation/Swift/SendableMetatype)

[`RealityCoordinateSpace`](/documentation/RealityKit/RealityCoordinateSpace)

[`Equatable`](/documentation/Swift/Equatable)

[`EventSource`](/documentation/RealityKit/EventSource)

[`Observable`](/documentation/Observation/Observable)

[`Sendable`](/documentation/Swift/Sendable)

[`HasPerspectiveCamera`](/documentation/RealityKit/HasPerspectiveCamera)

[`Identifiable`](/documentation/Swift/Identifiable)

[`CustomDebugStringConvertible`](/documentation/Swift/CustomDebugStringConvertible)

[`CoordinateSpace3D`](/documentation/Spatial/CoordinateSpace3D)

### Inherits From

[`Entity`](/documentation/RealityKit/Entity)

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)