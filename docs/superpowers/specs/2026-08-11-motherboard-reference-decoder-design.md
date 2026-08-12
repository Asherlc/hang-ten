# Motherboard Reference Decoder Design

## Goal

Match the `hangtime-grip-connect` Motherboard force interpretation internally while preserving Hang Ten's existing two-side balance UI.

## Scope

- Interpret only the first three 24-bit stream values as force channels.
- Treat those channels as left, center, and right respectively.
- Invert the calibrated readings for the center and right channels before tare correction.
- Exclude the fourth stream value from force, aggregate-load, and balance calculations.
- Preserve all four raw ADC values in `MotherboardMeasurement` for diagnostics and historical records.
- Continue requiring calibration rows for sensors `0...3`; calibration validation is unchanged.

## Data flow

The protocol parser continues to preserve the 16-byte payload as four 24-bit raw ADC values. The decoder derives force only from indices `0...2`:

1. Calibrate channel 0 as left.
2. Calibrate and negate channel 1 as center.
3. Calibrate and negate channel 2 as right.
4. Apply tare in that same signed coordinate system.
5. Sum left, center, and right for the aggregate load, with the existing finite-value and non-negative aggregate protections.

The current two-side presentation is a derived view of the reference channels:

```text
displayedLeft  = left + center / 2
displayedRight = right + center / 2
```

This assigns the center channel neutrally to both sides, so the displayed sides add to aggregate load and the current balance panel remains meaningful without introducing a new center-zone UI.

## Compatibility and error handling

- Existing persisted measurements remain decodable because the stored raw and calibrated arrays are unchanged in shape.
- The fourth calibrated channel remains available for calibration/tare lifecycle compatibility but has no effect on computed force.
- Non-finite calibration or tare values continue to use the existing safe handling. No new manual sign correction is added beyond the reference decoder's center/right inversion.

## Tests

- A deliberately asymmetric raw packet proves that only the first three values contribute to force.
- Tests prove that center and right polarity are inverted before tare is applied.
- A change to only channel 3 cannot alter aggregate force or balance.
- Balance tests prove the neutral center split and preserve `leftShare + rightShare == 1` for a positive measured load.
- Existing calibration validation tests continue to require sensors `0...3`.

## Out of scope

- Physical verification of the Motherboard wiring or polarity.
- Changing the visual balance panel to left/center/right zones.
- Changing calibration collection or validation.
- Exporting force magnitude through HealthKit/Dofek; that remains HT-3 work after this decoder change is established.

## Provenance

The decoding model intentionally follows the public, unofficial `hangtime-grip-connect` Motherboard implementation. Griptonite documents that library as a third-party developer API and does not officially support it. The mapping is therefore a compatibility choice, not a claim of manufacturer-verified physical channel wiring.

- https://github.com/Stevie-Ray/hangtime-grip-connect/blob/02dd6ff227ffb0fc521fd547a83e85453351eb3b/packages/core/src/models/device/motherboard.model.ts (retrieved 2026-08-11)
- https://griptonite.io/training/faq/
