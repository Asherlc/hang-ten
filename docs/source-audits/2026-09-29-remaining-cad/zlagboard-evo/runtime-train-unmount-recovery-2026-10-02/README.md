The attempted reversal stopped before app launch because the exact owned Simulator unexpectedly reported Shutdown. This is an interrupted setup, not a rendering result. No screenshots or workout sequence were captured in that failed trial. Its first get_app_container command exited 149 with CoreSimulator error 405, and the capture process exited 1. The cause of the shutdown is unknown.

The original two-arm evidence remains separate and unchanged in [runtime-train-unmount-2026-10-02](../runtime-train-unmount-2026-10-02/README.md). The failed reversal's original status and logs are retained exactly; its report's no-retry/no-boot statements describe that attempt before the later recovery.

Recovery preflight found exact device `BDCA0D77-94C2-4A97-900B-443F75C64691` in Shutdown. Tool session 90373 was no longer recognized by write_stdin, while OS controller PID 96137 remained alive with the exact workspace lifecycle argv. The existing lifecycle traps and ownership manifests remained authoritative; there was no cleanup marker. Loss of the tool session does not demonstrate controller exit or resource cleanup.

Root booted only that exact owned UUID. The bounded boot command returned 0, followed by bootstatus returning 0 and reporting that the device was already booted. This begins a new validation environment epoch. It does not establish app readiness, successful rendering or the reason for the earlier shutdown. No frontend or shared-resource operation was performed as part of this recovery.

This packet includes the 11-file failed reversal freeze, its original manifest, and exactly seven recovery records: preflight plus bounded boot/bootstatus JSON, stdout and stderr. `recovery-frozen-manifest.json` binds those seven bytes. Later postboot control and any conditional action belong to separate evidence and are excluded here. Source, installed assets and binary were not changed by this packaging task.

The Simulator and DerivedData remain under the original live lifecycle owner. No resource deletion or completed cleanup is claimed. There is no production inference, fix or new human acceptance.
