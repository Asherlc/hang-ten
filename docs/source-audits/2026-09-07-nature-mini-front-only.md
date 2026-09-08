# Nature Stone Hanger Mini front-only presentation audit

Reviewed 2026-09-07. The user selected one `Front` presentation for
`nature-stone-hanger-mini`; the former `Side` presentation and its declared
asset were removed. This is a presentation cleanup, not a new physical board
revision or a change to the frozen hold inventory.

## Manufacturer evidence

- The current [Stone Hanger Mini - Beech product page](https://natureclimbing.com/products/stone-hanger-mini-beech)
  states `10 x 6 x 2.5 cm` and a `60 mm pinch`. Its downloaded HTML has SHA-256
  `d2e6a38fec2a2a089ff15f07064e062bfeb86d90c8140194e1a37da65d4786b9`.
- [Beechminihanger1.png](https://natureclimbing.com/cdn/shop/files/Beechminihanger1.png?v=1774526917),
  SHA-256 `5bde3f95ced551ba5980deb44222f80b5ddcffd480f71a2c6ca272837b299423`,
  establishes the broad front and exterior body.
- [Beechminihanger3.png](https://natureclimbing.com/cdn/shop/files/Beechminihanger3.png?v=1774526917),
  SHA-256 `d71d396bf3611aee1a90a33209e56b83a8b14a3e4a8adb1f9c8043e366765f33`,
  establishes the narrow end profile and opposed pinch dimension.
- [Beechminihanger4.png](https://natureclimbing.com/cdn/shop/files/Beechminihanger4.png?v=1774534186),
  SHA-256 `9c6bd7bc6f38c9ff22220427a5e87ec6f83375c91bfed6555dcf0d0730dde794`,
  and [Beechminihanger7.png](https://natureclimbing.com/cdn/shop/files/Beechminihanger7.png?v=1774534186),
  SHA-256 `8949ba7cdcb3eb3c9931a980881ef9537cd9f6a8f470bca81a2c26c55e7d6b12`,
  corroborate body thickness, rounded exterior, front cavity, and cord channel.

The retained `assets/primary.png` is unchanged at SHA-256
`215b2e4ab39225ba3725b7637fc26328accffd1cf8c77bf670321bde7f8752ae`.

## Explicit front-view adaptation

The physical `pinch-60` ID, name, kind, hand capacity, and 60 mm size remain
unchanged. Its presentation ownership and availability move to `primary`.
An operator manually authored two disconnected smooth path pieces on the
existing front image: one follows the exterior top contact and one follows the
exterior bottom contact. They remain one logical pinch.

This is an explicit 2D front-view contact adaptation. The 60 mm source value is
the opposed top-to-bottom dimension of the 6 cm-tall product; it is not the
10 cm lateral span. The paths therefore do not claim that the left and right
broad-face perimeter is a 60 mm contact, and they do not reuse the removed end
view's coordinates. The KARMA8A package's four-piece perimeter mapping is only
a structural precedent; no product coordinates were copied. No new physical
face, hold, measurement, or coaching claim was invented, and the saved paths
remain the rendering, highlighting, and hit-testing source of truth.
