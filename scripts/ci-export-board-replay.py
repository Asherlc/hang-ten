#!/usr/bin/env python3
"""Temporary diagnostic: encrypt exact XCTest products for native replay."""
import hashlib
import io
import json
import os
import plistlib
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile


def export_products(products, certificate, output, metadata):
    products, certificate, output = map(Path, (products, certificate, output))
    assert products.is_dir() and certificate.is_file()
    assert not output.exists(), "Refusing to overwrite an existing export"
    openssl = shutil.which("openssl")
    if not openssl or not subprocess.check_output([openssl, "version"]).startswith(b"OpenSSL 3."):
        openssl = "/opt/homebrew/opt/openssl@3/bin/openssl"
    assert subprocess.check_output([openssl, "version"]).startswith(b"OpenSSL 3.")
    inventory = {}
    for path in sorted(products.rglob("*")):
        if path.is_file() and not path.is_symlink():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            inventory[str(path.relative_to(products))] = digest.hexdigest()
    manifest = json.dumps({"metadata": metadata, "fileSHA256": inventory}, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as encrypted:
        os.chmod(output, 0o600)
        process = subprocess.Popen([
            openssl, "cms", "-encrypt", "-binary", "-aes-256-gcm", "-outform", "DER",
            "-recip", str(certificate), "-keyopt", "rsa_padding_mode:oaep",
            "-keyopt", "rsa_oaep_md:sha256",
        ], stdin=subprocess.PIPE, stdout=encrypted)
        try:
            with tarfile.open(fileobj=process.stdin, mode="w|gz", dereference=False) as archive:
                archive.add(products, arcname="Products")
                entry = tarfile.TarInfo("replay-manifest.json")
                entry.size = len(manifest)
                entry.mode = 0o600
                archive.addfile(entry, io.BytesIO(manifest))
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError("Product encryption failed")
        except BaseException:
            if process.poll() is None:
                process.terminate()
                process.wait()
            output.unlink(missing_ok=True)
            raise
    return len(inventory)


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    root = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).resolve()
    owner = root.name
    result = root / ".context" / f"{owner}-board-replay-export"
    assert not result.exists(), "Owned export directory already exists"
    result.mkdir(parents=True)
    receipt_path = result / "receipt.json"
    output = result / "products.cms"
    receipt = {"owner": owner, "run": os.environ["GITHUB_RUN_ID"],
               "attempt": os.environ["GITHUB_RUN_ATTEMPT"],
               "purpose": "Exact CI products; never a rendering fix", "encrypted": False}
    receipt_path.write_text(json.dumps(receipt, indent=2))
    try:
        products = Path(os.environ["XCTEST_DERIVED_DATA"]) / "Build" / "Products"
        assert list(products.glob("*.xctestrun")), "No XCTest run manifest"
        assert (products / "Debug-iphonesimulator" / "HangTen.app").is_dir()
        executable_uuids = {}
        for bundle in products.rglob("*.app"):
            info = bundle / "Info.plist"
            if info.is_file():
                executable = bundle / plistlib.loads(info.read_bytes())["CFBundleExecutable"]
                executable_uuids[str(executable.relative_to(products))] = subprocess.check_output(["xcrun", "dwarfdump", "--uuid", str(executable)], text=True)
        metadata = {
            "executableUUIDs": executable_uuids,
            "head": os.environ["GITHUB_SHA"], "run": os.environ["GITHUB_RUN_ID"],
            "onlyTesting": os.environ["XCTEST_ONLY_TESTING"],
            "destination": os.environ["XCTEST_DESTINATION"],
            "xcode": subprocess.check_output(["xcodebuild", "-version"], text=True),
            "runtimes": json.loads(subprocess.check_output(["xcrun", "simctl", "list", "runtimes", "--json"])),
            "devices": json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"])),
        }
        count = export_products(products, root / ".github" / "diagnostics" / "supreme-zebra-replay-recipient.pem", output, metadata)
        digest = hashlib.sha256()
        with output.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        receipt.update(encrypted=True, fileCount=count, ciphertextSHA256=digest.hexdigest(), bytes=output.stat().st_size)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        print("Exact board products encrypted; only products.cms and receipt.json may be uploaded.")
    except BaseException:
        output.unlink(missing_ok=True)
        receipt.update(partialCiphertextDeletedVerified=not output.exists())
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        raise
