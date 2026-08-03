# Motherboard balance and bodyweight calibration

## Goal

Make Motherboard workouts show the left/right load split and a live percentage of the user’s captured bodyweight, with a short guided setup before the routine begins.

## User flow

When a Motherboard is streaming and the user starts a routine, Hang Ten presents a setup sequence before starting the workout timer:

1. **Tare the board.** The user removes their hands and starts the existing unloaded sample window. The current default remains 15 samples.
2. **Capture bodyweight.** The user hangs relaxed on the jugs for the configured duration, defaulting to 5 seconds. Hang Ten averages the received aggregate loads over that window and displays the captured value.
3. **Start the routine.** The normal three-second workout countdown begins only after the user confirms the bodyweight reading.

If the sensor is not streaming, the existing sensor-optional workout path remains available. The setup can also be skipped so the routine still works without a bodyweight baseline; force and left/right readings remain visible, while the bodyweight percentage is omitted.

## Measurements

`MotherboardMeasurement` exposes derived, non-persisted side metrics:

- left load: calibrated channels 0 and 2 summed and clamped at zero;
- right load: calibrated channels 1 and 3 summed and clamped at zero;
- left/right shares: each side divided by the positive left-plus-right total;
- bodyweight percentage: positive current aggregate divided by the captured bodyweight baseline.

The channel grouping is isolated in the model so it can be corrected without changing UI or recorder code if hardware validation identifies a different board revision mapping. The aggregate load continues to use the existing calibrated sensor vector.

The service owns the five-second capture lifecycle, publishes progress state, averages only finite streamed samples, cancels on disconnect/session reset, and keeps the completed bodyweight baseline available for the workout. A captured bodyweight value is included in saved session records for later review.

## UI

The live Motherboard meter gains:

- a left/right split display with percentages;
- a dynamic “% bodyweight” line when a baseline is available;
- bodyweight capture progress/status during setup.

Motherboard settings gain a bodyweight capture duration control (3–10 seconds, one-second steps, default 5 seconds). The existing force unit, threshold, tare, connection, summary, and history behavior remain intact.

The workout setup is a focused sheet/view, not a new timer mode. DEBUG autostart review routes bypass the setup so automated screenshots continue to reach the workout surface.

## DEBUG simulation

The simulator must make the sensor-backed experience inspectable without a physical Motherboard. Its deterministic stream provides near-zero unloaded samples for tare, a stable aggregate load during the bodyweight hang, and a changing, intentionally uneven left/right profile once the workout is active. This lets development and automated review exercise the setup flow, balance display, and live bodyweight percentage line end to end.

## Persistence and compatibility

`WorkoutSessionRecord.bodyweightKGF` is optional so existing persisted session history decodes unchanged. Derived left/right shares are calculated from the current measurement and are not duplicated in stored records.

## Testing

Tests cover side grouping/shares, bodyweight averaging and cancellation, duration setting persistence/normalization, saved bodyweight compatibility, and the preflight state transitions. Existing Bluetooth, parser, recorder, history, and full-app tests must remain green.
