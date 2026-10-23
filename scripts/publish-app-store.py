#!/usr/bin/env python3
"""Promote an exact processed CI build; leave ongoing App Review untouched."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


LIVE = {"READY_FOR_DISTRIBUTION", "READY_FOR_SALE"}
HISTORICAL = LIVE | {"REPLACED_WITH_NEW_VERSION", "REMOVED_FROM_SALE", "DEVELOPER_REMOVED_FROM_SALE"}
IN_FLIGHT = {
    "WAITING_FOR_REVIEW", "IN_REVIEW", "PENDING_DEVELOPER_RELEASE",
    "PENDING_APPLE_RELEASE", "PROCESSING_FOR_APP_STORE", "PROCESSING_FOR_DISTRIBUTION",
    "WAITING_FOR_EXPORT_COMPLIANCE", "PREORDER_READY_FOR_SALE",
}
EDITABLE = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "METADATA_REJECTED"}


def asc(*args):
    command = ["asc", *args, "--output", "json"]
    print("+ " + " ".join(command), flush=True)
    # Keep the executable fixed and pass all values as literal arguments.
    result = subprocess.run(
        ["asc", *args, "--output", "json"],
        shell=False, check=False, text=True, stdout=subprocess.PIPE,
    )
    if result.returncode:
        print(result.stdout, flush=True)
        result.check_returncode()
    return json.loads(result.stdout)


def state(version):
    attributes = version["attributes"]
    return attributes.get("appVersionState") or attributes.get("appStoreState")


def report(message):
    print(message, flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
            summary.write(message + "\n")


def publish(app, version, build_number, ipa, confirm=False):
    versions = asc("versions", "list", "--app", app, "--platform", "IOS", "--paginate")["data"]
    target = next((item for item in versions if item["attributes"]["versionString"] == version), None)
    active = [item for item in versions if state(item) not in HISTORICAL]
    for item in active:
        if state(item) in IN_FLIGHT:
            report(f"Production submission deferred: {item['attributes']['versionString']} is {state(item)}. "
                   f"Build {version} ({build_number}) remains uploaded; no existing review was changed.")
            return
        if item != target or state(item) not in EDITABLE:
            raise RuntimeError(f"Resolve existing App Store version {item['attributes']['versionString']} "
                               f"({state(item)}) before submitting {version}.")
    if target and state(target) in HISTORICAL:
        report(f"Version {version} is already released or historical; no submission created.")
        return
    live = sorted((item for item in versions if state(item) in LIVE),
                  key=lambda item: tuple(int(part) for part in item["attributes"]["versionString"].split(".")))
    if not live:
        raise RuntimeError("No live iOS listing to copy. Prepare the first release in App Store Connect.")
    source = live[-1]["attributes"]["versionString"]
    if tuple(map(int, version.split("."))) <= tuple(map(int, source.split("."))):
        raise RuntimeError(f"Version {version} must be newer than live version {source}.")
    builds = asc("builds", "list", "--app", app, "--platform", "IOS", "--version", version,
                 "--build-number", build_number, "--processing-state", "VALID", "--paginate")["data"]
    if len(builds) != 1:
        raise RuntimeError(f"Expected one processed build for {version} ({build_number}), found {len(builds)}.")
    build_id = builds[0]["id"]
    # Fail closed on product readiness before creating or modifying a version.
    asc("validate", "iap", "--app", app, "--strict")
    asc("validate", "subscriptions", "--app", app, "--strict")
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).name
    checkpoint = Path(".context") / f"{owner}-app-store-publish" / "stage.json"
    stage = ("release", "stage", "--app", app, "--version", version, "--platform", "IOS",
             "--build-id", build_id, "--copy-metadata-from", source,
             "--checkpoint-file", str(checkpoint))
    plan = asc(*stage, "--dry-run")
    print(json.dumps(plan, indent=2), flush=True)
    if not confirm:
        report(f"Dry run: stage {version} ({build_number}) from listing {source}, "
               "validate, then submit with automatic release after approval.")
        return
    asc(*stage, "--confirm")
    prepared = asc("versions", "list", "--app", app, "--platform", "IOS", "--version", version)["data"]
    if len(prepared) != 1 or state(prepared[0]) not in EDITABLE:
        raise RuntimeError("Staged version is no longer editable; inspect App Store Connect before retrying.")
    version_id = prepared[0]["id"]
    asc("versions", "update", "--version-id", version_id, "--release-type", "AFTER_APPROVAL")
    # IPA verification additionally gates required iPad screenshots and checks
    # the uploaded bundle's version and build against the attached build.
    asc("validate", "--app", app, "--version-id", version_id, "--platform", "IOS", "--ipa", ipa)
    review = ("review", "submit", "--app", app, "--version-id", version_id, "--build-id", build_id)
    print(json.dumps(asc(*review, "--dry-run"), indent=2), flush=True)
    submission = asc(*review, "--confirm")
    print(json.dumps(submission, indent=2), flush=True)
    report(f"Submitted iOS {version} ({build_number}) to App Review. "
           "Apple will release it automatically after approval. "
           f"Version ID: {version_id}; build ID: {build_id}; "
           f"submission ID: {submission.get('submissionId', 'see workflow log')}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-number", required=True)
    parser.add_argument("--ipa", required=True)
    parser.add_argument("--confirm", action="store_true", help="Stage and submit; otherwise preview only")
    args = parser.parse_args()
    try:
        publish(args.app, args.version, args.build_number, args.ipa, args.confirm)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"App Store publication failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
