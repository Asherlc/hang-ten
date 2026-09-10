# Task 3 report — deterministic suspended-presentation solver

Implemented the pure Swift suspended-presentation math in
`HangTen/Views/SuspendedBoardPresentation.swift` and focused XCTest coverage
in `HangTenTests/SuspendedBoardPresentationTests.swift`.

## Contract covered

- Canonical quaternion/translation transforms, including identity and
  quarter-turn attachment transforms, with normalized-pose rejection.
- Fixed 32-sample cord output with exact endpoints, strict `1e-5 m` taut
  tolerance, gravity-plane catenary solving, bounded `1e-6 m` bisection,
  finite tangent samples, analytical and sampled arc lengths, and deterministic
  repeatability.
- Invalid short cords and zero-horizontal slack rejection.
- Self-intersection detection/throwing validation hook independent of any
  mesh or screen mask.
- Immutable tube radius/required-clearance output and canonical camera-space
  framing containing board bounds, fixed anchor, transformed attachment, and
  every cord sample.

The Xcode project source/test groups include both new files so the focused
test target can discover them.

## Verification

Passed:

- Swift type-check of the solver against temporary stubs matching the existing
  Task 2 model types.
- Standalone Swift smoke executable covering taut/slack samples, exact
  endpoints, finite sag, deterministic framing inclusion, and a quarter-turn
  transform.
- `git diff --check`.

Round 1 review fix: self-intersection validation now requires a genuine
interior segment crossing (or an exact repeated non-adjacent vertex), so
valid very short taut cords are not rejected merely because their samples are
within the numerical proximity tolerance. The regression suite also measures
the returned sampled polyline length directly for slack cords and covers an
8e-6 m taut segment.

Unavailable in this environment:

- Focused `xcodebuild test ... -only-testing:HangTenTests/SuspendedBoardPresentationTests`.
  CoreSimulatorService is unavailable, and Xcode attempted to clone the
  Amplitude/Sentry package dependencies but DNS/network access failed. The
  command therefore stopped during package resolution before compiling the
  focused test.
