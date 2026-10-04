<!--
{
  "availability" : [
    "iOS: 13.0.0 -",
    "iPadOS: 13.0.0 -",
    "macCatalyst: 13.0.0 -",
    "macOS: 10.15.0 -",
    "tvOS: 26.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "RealityKit",
  "identifier" : "/documentation/RealityKit/ARView/entity(at:)",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "RealityKit"
    ],
    "preciseIdentifier" : "s:10RealityKit6ARViewC6entity2at0A10Foundation6EntityCSgSo7CGPointV_tF"
  },
  "title" : "entity(at:)"
}
-->

# entity(at:)

Finds the entity in the AR scene closest to the specified point.

```
@MainActor @preconcurrency func entity(at point: CGPoint) -> Entity?
```

## Parameters

`point`

A point in the view’s coordinate system.

## Return Value

The entity at `point`, or `nil` if no entity is found.

## Discussion

The method ignores entities that lack a [`CollisionComponent`](/documentation/RealityKit/CollisionComponent).

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)