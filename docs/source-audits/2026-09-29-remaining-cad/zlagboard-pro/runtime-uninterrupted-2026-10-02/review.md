# Pro 2.0 — uninterrupted runtime attempt

Fresh app review remains **blocked, with 0/28 contacts captured**. One new,
workspace-owned iPhone 17 Pro Simulator on iOS 26.5 received an uninterrupted
900-second first boot. It remained in AddressBook migration and all 29 Home
accessibility checks were negative. The whole startup screenshot shows the
Apple logo and progress bar. No build, install, tests or Hang Ten captures ran.

This changes the prior experiment by allowing migration to continue beyond its
180-second cutoff without rebooting. It did not produce a usable Simulator
within the longer bound. The targeted migration-log query returned no matching
entries; neither that result nor the migration status establishes a root cause.
No shared service, unknown device or private migration data was changed.

The exact temporary UUID `87CE3964-139D-4FAE-B121-AB12237401DB`, DerivedData,
result paths and owned helper processes were verified absent after cleanup.
Raw commands, failures, screenshot, lifecycle scripts and hashes are retained.
See [the raw attempt](ios-uninterrupted/final-runtime-validation.json) and
[whole-screen inspection](independent/startup-screen-review.json).

**Native geometry remains accepted.** The user accepted the displayed native
geometry from `e28886489` in the record committed as `92cc4ca4f`.
The raw worker report's generic `humanAccepted: false` and pending wording
apply only to its unmet fresh-app review gate; they do not revoke or supersede
[the native geometry acceptance](../human-review.json). All earlier proof bytes
and statuses remain intact. No source geometry, package, renderer or test code
changed, and there is no new manufacturing or ergonomic accuracy claim.

A working isolated Simulator environment is needed to capture the 28 selections
and exercise app interaction/workout behavior. No additional human acceptance
is inferred from this failed attempt.
