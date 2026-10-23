"""Exercise production promotion decisions without contacting Apple."""

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "publish_app_store", Path(__file__).resolve().parents[1] / "publish-app-store.py"
)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def version(number="1.0.474", status="READY_FOR_DISTRIBUTION"):
    return {"id": number, "attributes": {"versionString": number, "appVersionState": status}}


class PublishTests(unittest.TestCase):
    def run_publish(self, versions=None, confirm=True, fail=None, builds=None):
        self.calls = []

        def asc(*args):
            self.calls.append(args)
            if fail and fail(args):
                raise subprocess.CalledProcessError(1, ["asc", *args])
            if args[:2] == ("versions", "list"):
                if "--version" in args:
                    return {"data": [version("1.0.500", "PREPARE_FOR_SUBMISSION")]}
                return {"data": [version()] if versions is None else versions}
            if args[:2] == ("builds", "list"):
                return {"data": [{"id": "exact-build"}] if builds is None else builds}
            return {}

        with patch.object(publisher, "asc", side_effect=asc), patch.object(publisher, "report"), patch("builtins.print"):
            publisher.publish("app", "1.0.500", "500001", "release.ipa", confirm)

    def submissions(self):
        return [call for call in self.calls if call[:2] == ("review", "submit") and "--confirm" in call]

    def test_exact_build_and_automatic_release_before_submission(self):
        self.run_publish()
        lookup = next(call for call in self.calls if call[:2] == ("builds", "list"))
        self.assertEqual(lookup[lookup.index("--version") + 1], "1.0.500")
        self.assertEqual(lookup[lookup.index("--build-number") + 1], "500001")
        self.assertEqual(len(self.submissions()), 1)
        submission = self.submissions()[0]
        self.assertEqual(submission[submission.index("--build-id") + 1], "exact-build")
        update = next(call for call in self.calls if call[:2] == ("versions", "update"))
        self.assertIn("AFTER_APPROVAL", update)
        self.assertLess(self.calls.index(update), self.calls.index(submission))
        self.assertTrue(any("--ipa" in call for call in self.calls))
        self.assertEqual(self.calls[-2][-1], "--dry-run")

    def test_preview_does_not_mutate(self):
        self.run_publish(confirm=False)
        self.assertFalse(self.submissions())
        self.assertFalse(any("--confirm" in call or "update" in call for call in self.calls))

    def test_pending_review_is_untouched(self):
        for status in publisher.IN_FLIGHT:
            with self.subTest(status=status):
                self.run_publish([version(), version("1.0.499", status)])
                self.assertEqual(len(self.calls), 1)

    def test_same_version_pending_review_is_not_submitted_twice(self):
        self.run_publish([version(), version("1.0.500", "IN_REVIEW")])
        self.assertEqual(len(self.calls), 1)

    def test_unrelated_editable_or_unknown_version_blocks(self):
        for status in ("PREPARE_FOR_SUBMISSION", "REJECTED", "NEW_UNKNOWN_STATE"):
            with self.subTest(status=status), self.assertRaises(RuntimeError):
                self.run_publish([version(), version("1.0.499", status)])
            self.assertFalse(self.submissions())

    def test_rerun_reuses_same_editable_train(self):
        self.run_publish([version(), version("1.0.500", "PREPARE_FOR_SUBMISSION")])
        self.assertEqual(len(self.submissions()), 1)

    def test_already_live_version_is_not_resubmitted(self):
        self.run_publish([version(), version("1.0.500")])
        self.assertEqual(len(self.calls), 1)

    def test_semantic_version_order_ignores_response_order(self):
        self.run_publish([version("1.0.99"), version("1.0.474"), version("1.0.100")])
        stage = next(call for call in self.calls if call[:2] == ("release", "stage"))
        self.assertEqual(stage[stage.index("--copy-metadata-from") + 1], "1.0.474")

    def test_stale_train_missing_live_listing_and_ambiguous_build_fail(self):
        for versions, builds in (([version("1.0.501")], None), ([], None),
                                 ([version()], []), ([version()], [{"id": "a"}, {"id": "b"}])):
            with self.subTest(versions=versions, builds=builds), self.assertRaises(RuntimeError):
                self.run_publish(versions, builds=builds)
            self.assertFalse(self.submissions())

    def test_every_failed_gate_prevents_submission(self):
        gates = [
            lambda call: call[:2] == ("validate", "iap"),
            lambda call: call[:2] == ("validate", "subscriptions"),
            lambda call: call[:2] == ("release", "stage") and "--dry-run" in call,
            lambda call: call[:2] == ("release", "stage") and "--confirm" in call,
            lambda call: call[:2] == ("versions", "update"),
            lambda call: "--ipa" in call,
            lambda call: call[:2] == ("review", "submit") and "--dry-run" in call,
        ]
        for gate in gates:
            with self.subTest(gate=gate), self.assertRaises(subprocess.CalledProcessError):
                self.run_publish(fail=gate)
            self.assertFalse(self.submissions())


if __name__ == "__main__":
    unittest.main()
