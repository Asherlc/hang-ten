# PR #542 CI fixture corrections

The failing run on `4d010a76003a24c8f6d22f02e5b159eea1ee7d92` had three stale test expectations. This correction changes tests only; production code, source facts, native geometry, models and descriptors remain unchanged.

| Failing job | Cause and correction |
| --- | --- |
| [Python](https://github.com/Asherlc/hang-ten/actions/runs/37151709739/job/111286912547) | Forge's single full-pair display asset represents two physical equipment objects. Assert `left-half`/`right-half` and the exact mapping of all 20 contacts, retaining the native geometry, binding, mirror and paired-fact checks. |
| [iOS unit tests](https://github.com/Asherlc/hang-ten/actions/runs/37151709739/job/111286912572) | Penta's authored X bounds midpoint is approximately 4.381 micrometres. Expect that midpoint, reflected with the selected pose, instead of an exact zero. The `1e-6` tolerance and ownership, spacing, orientation and instance-count assertions remain. |
| [Board UI tests](https://github.com/Asherlc/hang-ten/actions/runs/37151709739/job/111286912623) | The Mini now has one presentation. The multi-presentation viewport test uses Plateau's three presentations; the separate square-board test remains. All viewport and selector assertions and timeouts remain. |

The original unit CI run completed its strict Clavellium physics tests and live settled-frame test successfully. Its current failure was the Penta camera expectation. The older local physics timeout is a separate retained historical attempt.

Fresh local verification:

- Full Python package suite: **612 passed**, zero failures/errors/skips. [Result and exact evidence hashes](python/final-result.json).
- Suspended-board unit class: **73 passed**. Board-interaction UI class: **6 passed**, including the corrected multi-presentation case and the retained square-board case. [Combined 79-test summary](affected-ios-summary.json), [exact command](commands/affected-unit-and-ui-tests.json), and [raw test log](commands/affected-unit-and-ui-tests.log).
- [Verified source identities](verified-inputs.json) bind the test changes to these results. The owned Simulator, result bundle and DerivedData were removed; [cleanup](ios-cleanup.json) records that verification.

Remote CI rerun is still required. This packet does not claim combined-branch integration, workout completion or new human geometry acceptance.
