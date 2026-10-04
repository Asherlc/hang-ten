#!/usr/bin/env python3
"""Deferred Simulator #8 Opus and plastic packet builder. No subprocesses or resource launches."""
import argparse
import copy
import hashlib
import html
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PREP = Path(__file__).resolve().parent
ROOT = PREP.parents[3]
SLUG = "metolius-simulator-3d"
AUDIT = ROOT / "docs/source-audits/2026-09-29-remaining-cad" / SLUG
TARGET = AUDIT / "opus-and-plastic-review"
HISTORY = AUDIT / "jagged-review"
SCRATCH = PREP.parent
STAGE = PREP / "staged-packet"
PACKAGE = ROOT / "Hangboards" / SLUG
QUEUE = AUDIT.parent / "review-queue.json"
LOCK = ROOT / "docs/model-delivery-lock.json"
NAMES = {"sourceSHA256": SLUG + ".FCStd", "modelSHA256": "assets/primary.usdz",
         "descriptorSHA256": "assets/primary.model.json"}
ORIGINAL = {"sourceSHA256": "9449f932e98c23fc9115d7a2cd0cfe5aacb158fd574d7ba573287ef7c5b67222",
         "modelSHA256": "a1d2a2a5e0cc4cc955ecf9b25c47b049bd71d8c70b3b2269fa167b9defbe6d16",
         "descriptorSHA256": "1c485ce852b600cb69eb1bf4036f73245b03cb88715e46f8ee789f3601f5115e"}
SOURCES = {"product-01.jpg": "5ac1677d6280dc90242cb1dcef47691647fd3f5a9adc3c465838e930075f58a9",
           "product-03.jpg": "e9561ab3fb6d3a85014097dcbdb0bc3d9c4079f9cb0954bd87965d180329932a"}
NEUTRAL = {"sourceSHA256": "8fa07c203943d849101ba80926fb6c1d69c2ace7dff982a68f6e8a6476f618f7",
           "modelSHA256": "c87d2acf4226a3f31ce11fd2e086b891b3608bef58e74f40d50c82f2318e8628",
           "descriptorSHA256": "3aba3cf597f09d23339940711b6a13efe008431a60a8f84d292c173335c7da9d"}
INTERMEDIATE_SHA = "3c516ec27da90e124fd8397470cbba0f127d5929a1fa49c62c4c611992570777"
SUPERSEDED_NATIVE_SHA = "21ca3e79f2750bf9a501e5ace231411a633772b52f30bb1dc92ec453d61db73d"
SUPERSEDED_FUNCTIONAL_SHA = "46df0c88878d3f833c27c7cce12c637fba09572d9223290c850c0e866b4d1264"
ROLES = {"author", "independent-native", "independent-export", "compiler", "geometry-disposition",
         "ios-tests", "python-tests", "package", "staging", "build", "installed", "app-visual", "cleanup", "opus-final"}
HUMAN_FEEDBACK = ["Jagged", "It should be tagged as plastic so it gets colored", "And ask opus for its take",
                  "center jug has a weird ridge going down the back ... impossible to grab onto",
                  "sloper should extend all the way forward", "why does it look kind of... wavy?"]



def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def read_exact(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return handle.read()


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def local(value):
    require(isinstance(value, str) and value, "A source path is still unset")
    path = (ROOT / value).resolve()
    require(path.is_relative_to(ROOT), f"Path leaves workspace: {value}")
    require(path.is_file(), f"Missing input: {value}")
    return path


def destination(base, relative):
    path = (base / relative).resolve()
    require(path.is_relative_to(base.resolve()), f"Unsafe packet path: {relative}")
    return path


def retain(source, target, records):
    require(source.is_file() and not source.is_symlink(), f"Missing raw input: {source}")
    if target.exists():
        require(sha(source) == sha(target), f"Refusing to overwrite retained bytes: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    require(sha(source) == sha(target), f"Raw copy changed: {target}")
    if records is not None:
        records.append({"source": str(source.relative_to(ROOT)),
                        "retained": str(target.relative_to(STAGE)),
                        "sha256": sha(target), "bytes": target.stat().st_size})


def manifest(path):
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("Document.xml"))
    properties = {p.attrib["name"]: p for p in document.iter("Property")
                  if p.attrib.get("name") in {"HangTenBoardID", "HangTenBoardManifest"}}
    return (properties["HangTenBoardID"].find("String").attrib["value"],
            properties["HangTenBoardManifest"].find("String").attrib["value"])


def pointer(document, path):
    for part in path.strip("/").split("/") if path else []:
        part = part.replace("~1", "/").replace("~0", "~")
        document = document[int(part)] if isinstance(document, list) else document[part]
    return document


def json_spans(text):
    """Locate value spans so updates leave unrelated JSON bytes untouched."""
    decoder = json.JSONDecoder()
    spans = {}

    def whitespace(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    def parse(pos, path):
        pos = whitespace(pos)
        begin = pos
        if text[pos] == "{":
            pos = whitespace(pos + 1)
            while text[pos] != "}":
                key, pos = decoder.raw_decode(text, pos)
                pos = whitespace(pos)
                require(text[pos] == ":", "Invalid JSON member")
                pos = whitespace(parse(pos + 1, path + (key,)))
                if text[pos] == ",":
                    pos = whitespace(pos + 1)
            pos += 1
        elif text[pos] == "[":
            pos = whitespace(pos + 1)
            index = 0
            while text[pos] != "]":
                pos = whitespace(parse(pos, path + (index,)))
                index += 1
                if text[pos] == ",":
                    pos = whitespace(pos + 1)
            pos += 1
        else:
            _, pos = decoder.raw_decode(text, pos)
        spans[path] = (begin, pos)
        return pos

    require(whitespace(parse(0, ())) == len(text), "Trailing JSON content")
    return spans


def replace_json_value(text, path, value):
    begin, end = json_spans(text)[tuple(path)]
    line_start = text.rfind("\n", 0, begin) + 1
    indentation = re.match(r"\s*", text[line_start:begin]).group(0)
    lines = json.dumps(value, indent=2).splitlines()
    replacement = lines[0] + "".join("\n" + indentation + line for line in lines[1:])
    updated = text[:begin] + replacement + text[end:]
    json.loads(updated)
    return updated


def only_value_changed(before, after, path):
    a, b = json_spans(before)[tuple(path)], json_spans(after)[tuple(path)]
    require(before[:a[0]] == after[:b[0]] and before[a[1]:] == after[b[1]:],
            f"Unrelated JSON bytes changed: {path}")


def package_scope(identity, baseline_path):
    for key, name in NAMES.items():
        require(sha(PACKAGE / name) == identity[key], f"Canonical candidate changed: {name}")
    require(load(PACKAGE / NAMES["descriptorSHA256"])["modelSHA256"] == identity["modelSHA256"],
            "Descriptor does not bind candidate USDZ")
    require(not (PACKAGE / "board.json").exists(), "CAD package acquired board.json")
    data = load(baseline_path)
    files = data.get("files", data)
    outside = {name: item for name, item in files.items()
               if not name.startswith("Hangboards/" + SLUG + "/")}
    require(len(files) == 206 and len(outside) == 203, "Unexpected package baseline scope")
    require(all(sha(local(name)) == (item["sha256"] if isinstance(item, dict) else item) for name, item in outside.items()),
            "An unrelated baseline package file changed")


def check_app(path, identity, phase):
    report = load(path)
    require(report.get("boardID") == "metolius.simulator-3d" and report.get("phase") == phase,
            f"Wrong app identity/phase: {path}")
    require(all(report.get(k) == v for k, v in identity.items()), f"Stale app hashes: {path}")
    checks = report["checks"]
    require(len(checks) == 8 and len({c["contactID"] for c in checks}) == 5,
            f"Expected eight captures/five representative contacts: {path}")
    require(sum(bool(c.get("actualDragOrbit")) for c in checks) == 3,
            f"Expected three actual drag orbits: {path}")
    require(all(c.get("projectedContactFramesChanged") is True for c in checks if c.get("actualDragOrbit")),
            f"A claimed drag has no changed projected contact frames: {path}")
    for check in checks:
        require(check.get("selectionAXConfirmed") and check.get("contactsAvailable") == 30,
                f"Unconfirmed selection: {check}")
        image = path.parent / check["image"]
        require(image.is_file(), f"Missing app frame: {image}")
        ax = load(image.with_name(image.stem + "-accessibility.json"))
        require(any(row.get("AXUniqueId") == "boardDetail.selectedHold." + check["contactID"]
                    for row in ax), f"Missing selected AX marker: {image}")
        require(len({row["AXUniqueId"] for row in ax
                     if (row.get("AXUniqueId") or "").startswith("boardModel.contact.")}) == 30,
                f"AX contact inventory is not 30: {image}")
    return report


def app_binary(report, proof_path, identity):
    proof = load(proof_path)
    require(proof.get("owner") == ROOT.name and proof.get("binaryBytesMatch") is True,
            f"Build/install binary proof is incomplete: {proof_path}")
    require(proof.get("nativeSourceSHA256") == identity["sourceSHA256"] and
            proof.get("builtBinarySHA256") == proof.get("installedBinarySHA256") == report["builtBinarySHA256"],
            f"App captures and installed binary are not linked: {proof_path}")


def check_fairing_app(config, identity, after_app):
    rule = config.get("fairingApp")
    if not rule:
        return None
    snapshot_path = local(config["wavinessIntermediate"]["completeAppSnapshot"])
    snapshot = load(snapshot_path)
    before_identity = rule["beforeHashes"]
    require(before_identity == {key: snapshot[key] for key in NAMES} and
            before_identity["sourceSHA256"] != identity["sourceSHA256"],
            "Fairing app before must use the frozen intermediate 3ff3 identity")
    before_path, installed_path = local(rule["before"]), local(rule["beforeInstalled"])
    require(before_path.is_relative_to(snapshot_path.parent) and installed_path.is_relative_to(snapshot_path.parent),
            "Fairing app before must use immutable snapshots, not overwritten convenience paths")
    before = check_app(before_path, before_identity, rule["beforePhase"])
    app_binary(before, installed_path, before_identity)
    require(before.get("surfaceFinish") == after_app.get("surfaceFinish") == "plastic" and
            all(after_app.get(key) == value for key, value in identity.items()),
            "Fairing comparison must show plastic before and fresh final plastic after")
    require(rule["pairs"] and all(name + ".png" in {c["image"] for c in before["checks"]} and
                                  name + ".png" in {c["image"] for c in after_app["checks"]}
                                  for name in rule["pairs"]), "Fairing app comparison lacks exact raw frames")
    return {"path": before_path, "installed": installed_path, "report": before, "identity": before_identity}


def compose(rows, output, title, placements, app=False):
    from PIL import Image, ImageDraw, ImageFont
    cell_width, cell_height = (700, 1520) if app else (900, 540)
    gap, header, label_height = 24, 90, 48
    canvas = Image.new("RGB", (2 * cell_width + 3 * gap,
                               header + len(rows) * (cell_height + label_height + gap)), "#f5f5f2")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 28)
    draw.text((gap, 18), title, font=font, fill="#222")
    for row_index, (label, before, after) in enumerate(rows):
        y = header + row_index * (cell_height + label_height + gap)
        for column, source in enumerate((before, after)):
            x = gap + column * (cell_width + gap)
            draw.text((x, y), ("Left — " if column == 0 else "Right — ") + label,
                      font=font, fill="#222")
            with Image.open(source) as opened:
                image = opened.convert("RGBA")
                scale = min(cell_width / image.width, cell_height / image.height)
                size = (round(image.width * scale), round(image.height * scale))
                point = (x + (cell_width - size[0]) // 2,
                         y + label_height + (cell_height - size[1]) // 2)
                resized = image.resize(size, Image.Resampling.LANCZOS)
                canvas.paste(resized, point, resized)
                placements.append({"output": output.name,
                                   "input": str(source.relative_to(STAGE)), "inputSHA256": sha(source),
                                   "originalSize": list(image.size), "placedSize": list(size),
                                   "position": list(point), "uniformScale": scale,
                                   "crop": False, "registration": False})
    canvas.save(output)


def aliases(value, identity):
    if isinstance(value, str) and value.startswith("@"):
        require(value[1:] in identity, f"Unknown hash alias: {value}")
        return identity[value[1:]]
    return value


def validate_neutral_history(snapshot):
    require(snapshot["packet"] == str(HISTORY.relative_to(ROOT)), "Wrong historical packet")
    require(len(snapshot["files"]) >= 362, "Incomplete neutral packet snapshot")
    for rel, item in snapshot["files"].items():
        path = destination(HISTORY, rel)
        require(path.is_file() and not path.is_symlink() and sha(path) == item["sha256"],
                f"Immutable neutral history changed: {rel}")


def validate_neutral_records(snapshot):
    require(snapshot.get("owner") == ROOT.name and len(snapshot["files"]) == 7, "Wrong neutral record snapshot scope")
    for rel, item in snapshot["files"].items():
        path = local(rel)
        require(path.is_relative_to(SCRATCH / "before") and sha(path) == item["sha256"],
                f"Exact neutral source/review bytes changed: {rel}")


def archive_entries(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), f"Duplicate native archive member: {path}")
        return {name: archive.read(name) for name in names}


def check_superseded_snapshot(path, expected_source=SUPERSEDED_NATIVE_SHA):
    data = load(path)
    require(data.get("owner") == ROOT.name and data.get("sourceSHA256") == expected_source and
            data.get("humanAcceptance") == "pending review #8", "Wrong superseded native snapshot")
    require(data.get("rawCopies"), "Superseded native raw evidence is missing")
    for record in data["rawCopies"]:
        source = destination(path.parent, record["retained"])
        require(source.is_file() and not source.is_symlink() and sha(source) == record["sha256"],
                f"Superseded native bytes changed: {source}")
    return data


def check_diagnostic_snapshots(config, identity, packet=None):
    rules = config.get("diagnosticNativeSnapshots", [])
    require(rules, "Rejected diagnostic native snapshots are missing")
    checked, names = [], set()
    for rule in rules:
        digest = rule["sourceSHA256"]
        require(isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest),
                "Diagnostic native source hash is invalid")
        require(identity["sourceSHA256"] != digest, "An intermediate diagnostic source cannot satisfy final gates")
        name = Path(rule["snapshot"]).parent.name
        require(name not in names, "Diagnostic snapshot destinations collide")
        names.add(name)
        path = local(rule["snapshot"]) if packet is None else destination(
            packet, "before/diagnostic-native/" + name + "/snapshot.json")
        if packet is None:
            require(path.is_relative_to(PREP), "Diagnostic snapshot leaves preparation scratch")
        data = check_superseded_snapshot(path, digest)
        require(any(word in data.get("status", "").lower() for word in ("diagnostic", "held technical checkpoint")),
                "Historical diagnostic evidence is mislabeled as final")
        require(any(r["sha256"] == digest and Path(r["retained"]).suffix == ".FCStd"
                    for r in data["rawCopies"]), "Diagnostic snapshot lost its exact native source")
        checked.append((path, data))
    return checked


def check_plastic_intermediate(source):
    before = SCRATCH / "before" / NAMES["sourceSHA256"]
    require(sha(before) == NEUTRAL["sourceSHA256"] and sha(source) == INTERMEDIATE_SHA,
            "Neutral or plastic-tag intermediate source changed")
    a, b = archive_entries(before), archive_entries(source)
    require(set(a) == set(b), "Plastic tagging added or removed archive members")
    changed = [name for name in a if a[name] != b[name]]
    require(changed == ["Document.xml"], "Plastic tagging changed native geometry/archive members")
    breps = [name for name in a if name.lower().endswith(".brp")]
    require(len(breps) == 387, "Neutral native BRep count changed")
    documents = [ET.fromstring(entries["Document.xml"]) for entries in (a, b)]
    for document in documents:
        properties = [p for p in document.iter("Property") if p.get("name") == "HangTenBoardManifest"]
        require(len(properties) == 1, "Ambiguous native board manifest")
        properties[0].find("String").set("value", "__manifest__")
    require(ET.tostring(documents[0]) == ET.tostring(documents[1]),
            "Plastic tagging changed Document.xml outside the embedded manifest")
    before_id, before_text = manifest(before)
    after_id, after_text = manifest(source)
    old, new = json.loads(before_text), json.loads(after_text)
    expected = copy.deepcopy(old)
    expected["presentations"][0]["media"]["display"]["surfaceFinish"] = "plastic"
    require(before_id == after_id == "metolius.simulator-3d" and new == expected,
            "Pure tag changed a field other than display.surfaceFinish")
    require(old == load(SCRATCH / "before-manifest.json") and new == load(SCRATCH / "after-manifest.json"),
            "Retained manifest JSON does not match its native source")
    return {"status": "pass", "previousSourceSHA256": NEUTRAL["sourceSHA256"],
            "sourceSHA256": INTERMEDIATE_SHA, "geometryChanged": False,
            "onlyChangedArchiveMember": "Document.xml", "unchangedBRepMembers": len(breps),
            "onlyChangedManifestField": "/presentations/0/media/display/surfaceFinish",
            "modelSHA256": NEUTRAL["modelSHA256"], "descriptorSHA256": NEUTRAL["descriptorSHA256"]}


def queue_scope(current, previous):
    a, b = json.loads(current), json.loads(previous)
    require([row["number"] for row in a["boards"]] == list(range(1, 22)) and
            [row["number"] for row in b["boards"]] == list(range(1, 22)), "Queue order or count changed")
    require(all(str(row["humanReview"]).startswith("reviewed") for row in a["boards"][:7]),
            "The first seven reviews are not accepted")
    sa, sb = json_spans(current), json_spans(previous)
    for index, row in enumerate(a["boards"]):
        require(row["package"] == b["boards"][index]["package"], "Queue package/order changed")
        if row["number"] != 8:
            require(current[slice(*sa[("boards", index)])] == previous[slice(*sb[("boards", index)])],
                    f"Unrelated queue row bytes changed: #{row['number']}")
    return next(index for index, row in enumerate(a["boards"]) if row["number"] == 8)


def lock_scope(current, previous):
    a, b = json.loads(current), json.loads(previous)
    require(set(a["migratedPackages"]) == set(b["migratedPackages"]), "Lock package inventory changed")
    sa, sb = json_spans(current), json_spans(previous)
    for slug in a["migratedPackages"]:
        if slug != SLUG:
            path = ("migratedPackages", slug)
            require(current[slice(*sa[path])] == previous[slice(*sb[path])],
                    f"Unrelated delivery-lock package bytes changed: {slug}")


def final_measurements(config, identity):
    rule = config["measurements"]
    native_path = local(rule["nativeReport"])
    native = load(native_path)
    require(native["sourceSHA256"] == identity["sourceSHA256"], "Native measurement source is stale")
    envelope = pointer(native, rule.get("envelopePointer", "/envelopeXYZMM"))
    depths = pointer(native, rule.get("depthsPointer", "/publishedDepthChecks"))
    rows = list(depths.values()) if isinstance(depths, dict) else depths
    require(len(envelope) == 3 and abs(envelope[0] - 711) < 0.02 and abs(envelope[2] - 222) < 0.02,
            "Final face dimensions failed their strict 711 × 222 mm gate")
    require(len(rows) == 27 and all(abs(d["expected"] - d["actual"]) < 0.02 for d in rows),
            "Final 27 published hold depths failed their strict gates")
    thickness = rule["measuredThicknessMM"]
    require(isinstance(thickness, (int, float)) and thickness == envelope[1],
            "Thickness wording is not sourced from the final native measurement")
    paths = [native_path]
    angle = rule.get("maximumResidualRoofNormalAngleDegrees")
    continuity_path = rule.get("continuityReport")
    if continuity_path:
        continuity_path = local(continuity_path)
        continuity = load(continuity_path)
        require(continuity["sourceSHA256"] == identity["sourceSHA256"], "Continuity measurement source is stale")
        require(isinstance(angle, (int, float)) and angle == pointer(continuity, rule["normalAnglePointer"]),
                "Normal-angle wording is not sourced from the final report")
        epsilon = rule.get("normalAngleProbeEpsilonMM")
        if epsilon is not None:
            probe = pointer(continuity, rule["normalAnglePointer"].rsplit("/", 1)[0])
            require(probe.get("epsilonMM") == epsilon, "Normal-angle wording uses the wrong probe distance")
            angles = [p["maximumNormalAngleDegrees"] for join in continuity["localJoins"] for p in join["probes"]
                      if p["epsilonMM"] == epsilon and isinstance(p.get("maximumNormalAngleDegrees"), (int, float))]
            require(angles and angle == max(angles), "Normal-angle wording is not the sampled maximum at its stated distance")
        paths.append(continuity_path)
    else:
        require(angle is None, "A normal-angle claim has no final report")
    thickness_text = (f"Overall thickness is measured {thickness:.7f} mm, a display estimate. "
                      "Published 711 × 222 mm face dimensions and all 27 hold-depth checks retain their strict gates. "
                      "Exact 94 mm thickness preservation is not claimed.")
    probe_scope = (f"At the retained ±{rule['normalAngleProbeEpsilonMM']:g} mm seam probes, "
                   if rule.get("normalAngleProbeEpsilonMM") is not None else "At the retained finite seam probes, ")
    continuity_text = (probe_scope + f"sampled normal changes reach {angle:.4f}°. "
                       if angle is not None else "No global continuity claim is made. ")
    continuity_text += "Finite probes do not establish global roof G1 or C1 continuity. Estimated transitions, rounding, loft controls and thickness remain display geometry."
    return thickness, angle, thickness_text, continuity_text, paths


def check_legacy_normal_reference(config, identity, data):
    raw_reference = data["rawLegacyComparison"]
    raw_path = local(raw_reference["path"])
    raw = load(raw_path)
    require(sha(raw_path) == raw_reference["sha256"] and
            raw.get("status") == raw_reference["status"] == "review-required" and
            raw.get("sourceSHA256") == data["sourceSHA256"] == identity["sourceSHA256"] and
            raw.get("compilerSHA256") == data["compilerSHA256"] == config["compilerSHA256"],
            "Same-owner normal supplement lost the unchanged raw comparison or source/compiler identity")
    require(raw["allPositionsExact"] is True and raw["maxNormalAngleDegrees"] == raw_reference["maxAngleDegrees"] and
            data["cornersCompared"] == raw["cornersCompared"] == len(data["comparisons"]) and
            data["legacyAgreementCorners"] + data["actualOwnerDispositionCorners"] == data["cornersCompared"] and
            all(row["passed"] is True for row in data["comparisons"]),
            "Same-owner normal supplement is incomplete or changes the raw diagnostic result")


def check_reports(config, identity):
    rules = config["reports"]
    require({rule["role"] for rule in rules} == ROLES, "Required final technical/Opus report roles are missing")
    reports = []
    for rule in rules:
        source = local(rule["source"])
        data = load(source)
        require(rule.get("equals"), f"No pass assertions configured for {rule['role']}")
        for path, expected in rule["equals"].items():
            require(pointer(data, path) == aliases(expected, identity), f"Failed {rule['role']} assertion: {path}")
        if rule.get("validateLinkedHashes"):
            for key in ("fileSHA256", "imageSHA256"):
                for rel, digest in data.get(key, {}).items():
                    historical = rule.get("historicalLinkedInputs", {}).get(rel)
                    if historical:
                        reviewed = "8d5abbed70d8a18a80a7f411ca5556cf85e271a4489cb041a2b798c206baa51e"
                        queue_digest = "e0adef45f0c0436dcfc2409645c7f0b0b213d10f905c4db24ce19722a5d39f0d"
                        snapshot = local(historical["snapshot"])
                        proof_path = local(historical["disposition"])
                        proof = load(proof_path)
                        require(sha(source) == rule.get("reviewedSnapshotSHA256") == reviewed and
                                local(rel) == QUEUE and digest == historical["sha256"] == queue_digest and
                                snapshot == SCRATCH / "before-front-fairing-integration/review-queue.json" and
                                sha(snapshot) == digest and sha(proof_path) == historical["dispositionSHA256"] and
                                proof.get("status") == "pass" and proof.get("originalReviewSHA256") == reviewed and
                                proof.get("reviewedQueueSHA256") == digest and
                                proof.get("currentQueueSHA256") == sha(QUEUE) and
                                proof.get("sourceSHA256") == identity["sourceSHA256"] and
                                proof.get("onlyTopLevelReviewStateChangedFromReviewedSnapshot") is True and
                                proof.get("otherQueueRowsChanged") == [] and
                                proof.get("allOtherPackageFilesUnchanged") == 203,
                                "Historical compiler review queue pin lacks its exact snapshot and scoped prepare disposition")
                    else:
                        require(sha(local(rel)) == digest, f"Linked {rule['role']} proof bytes changed: {rel}")
        if rule.get("validateEvidenceEntries"):
            require(data.get("evidence"), f"Final {rule['role']} evidence entries are missing")
            for entry in data["evidence"].values():
                require(sha(local(entry["path"])) == entry["sha256"], f"Linked evidence entry changed: {entry['path']}")
        if rule.get("validateLegacyNormalReference"):
            check_legacy_normal_reference(config, identity, data)
        if rule.get("validateExportDispositionReferences"):
            refs = [(data["topologyDisposition"]["rawReport"], data["topologyDisposition"]["rawStatus"]),
                    (data["rearWatchDisposition"]["report"], "pass"),
                    (data["rearWatchDisposition"]["exactCorrespondenceSupplement"], "pass")]
            for name, status in refs:
                raw_path = (source.parent / name).resolve()
                require(raw_path.is_relative_to(ROOT) and raw_path.is_file(), "Missing raw export disposition input")
                rel = str(raw_path.relative_to(ROOT))
                require(data["fileSHA256"].get(rel) == sha(raw_path) and load(raw_path).get("status") == status,
                        "Export disposition lost its exact raw status or pinned bytes")
        if rule.get("validateCleanupOwnershipHashes"):
            require({job["name"] for job in data["jobs"]} == {"compile", "compile-check", "reproduce"},
                    "Final export cleanup does not identify the three completed jobs")
            for job in data["jobs"]:
                owned_path = source.parent / (job["name"] + "-ownership.json")
                require(job["processGroupAbsent"] is True and job["tempDirectoryDeleted"] is True and
                        sha(owned_path) == job["ownershipReportSHA256"],
                        "Final export cleanup does not match its actual owned job proof")
        if rule.get("validateCompilerJobs"):
            require(set(data.get("jobs", {})) == {"compile", "compile-check", "reproduce"},
                    "Final compiler job evidence is incomplete")
            for job in data["jobs"].values():
                require(sha(local(job["report"])) == job["reportSHA256"], "Raw compiler report changed")
                owned = load(local(job["ownership"]))
                require(owned.get("workspaceOwner") == ROOT.name and owned.get("exitCode") == 0 and
                        owned.get("ownedProcessGroupExited") is True and owned.get("compilerBytesUnchanged") is True and
                        owned.get("compilerSHA256") == owned.get("compilerSHA256After") == config["compilerSHA256"],
                        "Final compiler ownership or frozen compiler proof failed")
        if rule.get("validateRawFailureDispositions"):
            pinned = {item["source"]: item["sha256"] for item in config["rawFiles"] if item.get("sha256")}
            pinned.update(data.get("fileSHA256", {}))
            require(data.get("rawFailureDispositions"), "Exact raw failure dispositions are missing")
            for item in data["rawFailureDispositions"]:
                paths = [item["report"]] + ([item["supplement"]] if item.get("supplement") else []) + item.get("supplements", [])
                for rel in paths:
                    require(rel in pinned and sha(local(rel)) == pinned[rel],
                            f"Raw failure or supplement is no longer hash-bound: {rel}")
        if "rawCheckReport" in data:
            raw = (source.parent / data["rawCheckReport"]).resolve()
            require(raw.is_relative_to(ROOT) and raw.is_file() and sha(raw) == data["rawCheckSHA256"],
                    f"Final disposition lost its exact raw check: {source}")
        reports.append({"role": rule["role"], "source": str(source.relative_to(ROOT)),
                        "sha256": sha(source), "assertions": rule["equals"]})
    for role in ("author", "independent-native", "compiler", "package", "installed", "app-visual", "opus-final"):
        require(any("@sourceSHA256" in r["equals"].values() for r in rules if r["role"] == role),
                f"Final {role} gate is not bound to the native source")
    export_rules = [r for r in rules if r["role"] == "independent-export"]
    require(any("@modelSHA256" in r["equals"].values() and "@descriptorSHA256" in r["equals"].values()
                for r in export_rules), "Independent final export gate is not bound to both shipped assets")
    dispositions = [r for r in rules if r["role"] == "geometry-disposition"]
    require(all(r["equals"].get("/blockingFindings") == [] and "@sourceSHA256" in r["equals"].values()
                for r in dispositions), "Final geometry dispositions must be nonblocking and source-bound")
    opus = next(r for r in rules if r["role"] == "opus-final")
    require(opus["equals"].get("/blockingFindings") == [], "The final Opus finding disposition is unset/blocking")
    return reports


def check_cad_preview(config, identity):
    path = local(config["cadPreviewReport"])
    data = load(path)
    require(data["sourceSHA256"] == identity["sourceSHA256"] and
            set(data.get("reviewViews", [])) >= {"front", "side", "top", "oblique", "raking"},
            "Final native preview provenance is stale or lacks all five whole views")
    if "allFiveWholeAfterImagesInspected" in data:
        require(data["allFiveWholeAfterImagesInspected"] is True, "Author native-image inspection is incomplete")
    directory = (ROOT / config["cadPreviewDirectory"]).resolve()
    require(directory.is_relative_to(ROOT) and directory.is_dir(), "Wrong final native preview directory")
    image_hashes = data.get("imageHashes", data.get("images", {}))
    require(image_hashes, "Final native preview has no image hashes")
    require(data.get("nativeBodyMeshSHA256") == sha(local(config["functionalGraspNativeProof"]["bodyMesh"])),
            "Whole native previews and critical grasp proof use different body meshes")
    for name, digest in image_hashes.items():
        require(sha(destination(directory, name)) == digest, f"Final native preview image changed: {name}")
    by_path = {destination(directory, name): digest for name, digest in image_hashes.items()}
    history_hashes = load(local(config["neutralPacketSnapshot"]))["files"]
    if config.get("fairingApp"):
        require(data.get("beforeSourceSHA256") == config["fairingApp"]["beforeHashes"]["sourceSHA256"],
                "Fairing native comparison before is not the frozen intermediate 3ff3 source")
    for comparison_name, comparison in config["cadPairs"].items():
        for pair in comparison.values():
            for phase in ("before", "after"):
                image = local(pair[phase])
                if comparison_name == "neutral" and phase == "before":
                    require(image.is_relative_to(HISTORY), "Neutral before must come from the immutable true8fa packet")
                    rel = str(image.relative_to(HISTORY))
                    require(rel.startswith("previews/after-") and history_hashes[rel]["sha256"] == sha(image),
                            "Neutral before is not the true hash-bound8fa/c87 frame")
                    continue
                require(by_path.get(image) == sha(image),
                        f"Paired native frame is absent from the final source-bound provenance: {image}")
    return path


def check_grasp_native(config, identity):
    rule = config["functionalGraspNativeProof"]
    require(rule.get("sourceSHA256") == "@sourceSHA256", "Critical native grasp proof is not final-source bound")
    path, sections, body_mesh = (local(rule[key]) for key in ("source", "sections", "bodyMesh"))
    data = load(path)
    require(data.get("sourceSHA256") == identity["sourceSHA256"] and
            sha(local(data["sourcePath"])) == identity["sourceSHA256"], "Critical native grasp provenance is stale")
    require(data.get("sectionsSHA256") == sha(sections) and
            load(sections).get("sourceSHA256") == identity["sourceSHA256"],
            "Critical native sections are absent, changed or bound to another source")
    require(data.get("nativeBodyMeshSHA256") == sha(body_mesh), "Critical native body mesh changed")
    images = data.get("images", {})
    require({"grasp-review/high-front.png", "grasp-review/native-grasp-sections.png",
             "grasp-review/rear-center.png", "grasp-review/rear-oblique.png"} <= set(images),
            "Critical native grasp views are incomplete")
    directory = path.parent.parent
    image_paths = []
    for name, digest in images.items():
        image = destination(directory, name)
        require(image.is_file() and not image.is_symlink() and sha(image) == digest,
                f"Critical native grasp image changed: {name}")
        image_paths.append(image)
    return {"path": path, "report": data, "sections": sections, "bodyMesh": body_mesh, "images": image_paths}


def check_export_previews(config, identity):
    rule = config["exportPreview"]
    directory = (ROOT / rule["directory"]).resolve()
    require(directory.is_relative_to(ROOT) and directory.is_dir(), "Wrong exact-export preview directory")
    checked = []
    for key in ("source", "graspSource"):
        path = local(rule[key])
        data = load(path)
        if key == "source":
            require(data.get("status") == rule.get("sourceStatus", "pass"),
                    "Exact exported whole-preview report has the wrong raw status")
        elif rule.get("graspStatusMode") != "per-version-complete-images":
            require(data.get("status") == "pass", "Exact exported grasp report has the wrong raw status")
        if rule.get("identityMode") != "per-version":
            require(all(data.get(k) == v for k, v in identity.items()),
                    "Exact exported preview provenance is stale or incomplete")
        require(data.get("images"), "Exact exported preview images are missing")
        for name, digest in data["images"].items():
            require(sha(destination(directory, name)) == digest, f"Exact exported image changed: {name}")
        if key == "source":
            require(set(data.get("reviewViews", [])) >= {"front", "side", "top", "oblique", "raking"},
                    "Exact exported whole-board views are incomplete")
            for version, expected in (("candidate", identity), ("original-9449", ORIGINAL)):
                require(data[version]["hashes"] == {NAMES[k]: v for k, v in expected.items()},
                        f"Exact exported {version} input identity changed")
            if rule.get("identityMode") == "per-version":
                require(data["candidate"].get("nodeCount") == 31 and
                        data["candidate"].get("materialCount") == data["candidate"].get("shaderCount") == 0,
                        "Exact exported whole-preview lacks all31 unbound semantic nodes")
            require(set(rule["pairs"]) == {"front", "side", "top"}, "Exact export comparison is incomplete")
            for pair in rule["pairs"].values():
                for phase in ("before", "after"):
                    image = local(pair[phase])
                    require(image.is_relative_to(directory) and
                            data["images"].get(str(image.relative_to(directory))) == sha(image),
                             "Exact export comparison is absent from its hash-bound report")
            if rule.get("fairingPairs"):
                require(data["frozen-3ff3"]["hashes"] == {NAMES[k]: v for k, v in rule["fairingHashes"].items()} and
                        rule["fairingHashes"] == config["fairingApp"]["beforeHashes"] and
                        set(rule["fairingPairs"]) == {"front", "side", "top"},
                        "Fairing exact-export before identity or comparison is incomplete")
                for pair in rule["fairingPairs"].values():
                    for phase in ("before", "after"):
                        image = local(pair[phase])
                        require(image.is_relative_to(directory) and
                                data["images"].get(str(image.relative_to(directory))) == sha(image),
                                "Fairing exact-export frame is absent from its hash-bound report")
        else:
            require(all(data["candidate"].get(k) == v for k, v in identity.items()) and
                    all(data["original-9449"].get(k) == v for k, v in ORIGINAL.items()),
                     "Exact exported grasp input identities changed")
            if rule.get("graspStatusMode") == "per-version-complete-images":
                require(data["candidate"].get("meshCount") == 31 and
                        data["candidate"].get("completeShellTriangleCount", 0) > data["candidate"].get("bodyNodeTriangleCount", 0) > 0,
                        "Exact exported grasp preview lacks the complete semantic shell")
            require({"export-grasp-review/candidate-" + view + ".png" for view in
                     ("grasp-sections", "high-front", "rear-center", "rear-oblique")} <= set(data["images"]),
                    "Exact exported critical grasp views are incomplete")
        checked.append(path)
    return checked


def check_extra_apps(config, identity, after_app):
    phases = config.get("extraAppPhases", [])
    require({p["name"] for p in phases} == {"finish", "grasp"}, "Fresh finish and critical center-jug phases are required")
    checked = []
    for phase in phases:
        path = local(phase["source"])
        data = load(path)
        require(data.get("owner") == ROOT.name and data.get("boardID") == "metolius.simulator-3d" and
                data.get("phase") == phase["phase"] and data.get("surfaceFinish") == "plastic" and
                data.get("simulator") == after_app["simulator"] and
                data.get("builtBinarySHA256") == after_app["builtBinarySHA256"] and
                all(data.get(key) == value for key, value in identity.items()), f"Stale/wrong additional app phase: {path}")
        checks = data["checks"]
        require(len(checks) == phase["expectedCaptures"] and len({c["image"] for c in checks}) == len(checks),
                f"Wrong additional capture inventory: {path}")
        selected, cleared = 0, 0
        for check in checks:
            image = destination(path.parent, check["image"])
            require(image.is_file(), "Additional app capture is missing")
            ax = load(image.with_name(image.stem + "-accessibility.json"))
            ids = {(r.get("AXUniqueId") or "") for r in ax}
            cid = check.get("contactID")
            if cid:
                require(check.get("contactsAvailable") == 30 and
                        len({value for value in ids if value.startswith("boardModel.contact.")}) == 30 and
                        check.get("selectionAXConfirmed") is True and "boardDetail.selectedHold." + cid in ids,
                        "Additional selected contact lacks exact AX proof")
                selected += 1
            else:
                require(check.get("unselectedTrainCard") is True and check.get("selectionAXConfirmed") is False and
                        not any(value.startswith("boardDetail.selectedHold.") for value in ids),
                        "Unselected Train card lacks absent-selected-marker proof")
                cleared += 1
        if phase["name"] == "grasp":
            require(phase["expectedCaptures"] == 4 and phase["requiredContactID"] == "jug-14-center" and
                    all(c.get("contactID") == "jug-14-center" for c in checks), "Critical center-jug captures are missing")
            drags = [command for command in data.get("commands", [])
                     if isinstance(command, list) and "swipe" in command]
            require(phase.get("minimumActualDrags") >= 5 and len(drags) >= phase["minimumActualDrags"] and
                    all("--udid" in command and command[command.index("--udid") + 1] == after_app["simulator"]
                        for command in drags), "Critical center-jug phase lacks five actual owned swipe commands")
            witnesses = data.get("actualDragChecks", [])
            require(len(witnesses) == len(drags) and len({w["index"] for w in witnesses}) == len(witnesses),
                    "Critical center-jug swipe commands lack distinct per-drag witnesses")
            for witness in witnesses:
                require(witness.get("contactID") == "jug-14-center" and witness.get("selectionAXConfirmed") is True and
                        witness.get("contactsAvailable") == 30 and witness.get("actualDragOrbit") is True and
                        witness.get("projectedContactFramesChanged") is True, "A critical center-jug drag is unverified")
                ax = load(path.parent / f"grasp-drag-{witness['index']}-accessibility.json")
                ids = {(row.get("AXUniqueId") or "") for row in ax}
                require("boardDetail.selectedHold.jug-14-center" in ids and
                        len({value for value in ids if value.startswith("boardModel.contact.")}) == 30,
                        "Critical center-jug drag AX proof lacks preserved selection/contact inventory")
            require(sum(bool(c.get("actualDragOrbit")) for c in checks) >= 3 and
                    all(c.get("projectedContactFramesChanged") is True for c in checks if c.get("actualDragOrbit")),
                    "Critical center-jug rear view needs an actual drag with changed frames")
        else:
            require(phase["expectedCaptures"] == 4 and selected and cleared,
                    "Finish phase must retain selected and deselected actual-app frames")
            require(any(c.get("sameInstanceSelectionChange") is True and c.get("previousContactID") == "jug-1-left" and
                        c.get("contactID") == "flat-sloper-2-left" for c in checks),
                    "Finish phase lacks same-instance jug-to-sloper selection restoration")
        checked.append({"name": phase["name"], "path": path, "report": data})
    return checked


def check_additional_sources(config):
    rule = config["additionalSources"]
    directory = (ROOT / rule["directory"]).resolve()
    require(directory.is_relative_to(ROOT) and directory.is_dir(), "Wrong additional primary-source directory")
    for name, item in rule["files"].items():
        require(sha(destination(directory, name)) == item["sha256"], f"Additional primary-source bytes changed: {name}")
    review_path, manifest_path = local(rule["review"]), local(rule["manifest"])
    require(sha(review_path) == rule["reviewSHA256"] and sha(manifest_path) == rule["manifestSHA256"],
            "Additional primary-source review/manifest changed")
    review, sources = load(review_path), load(manifest_path)
    require(review.get("owner") == sources.get("owner") == ROOT.name and review.get("status") == "inspected",
            "Additional primary sources lack retained whole-source inspection")
    for rel, digest in review["fileSHA256"].items():
        require(sha(local(rel)) == digest, f"Primary inspection input changed: {rel}")
    for source in sources["sources"]:
        require(sha(destination(directory, source["file"])) == source["sha256"], "Retrieved primary-source bytes changed")
    return review_path


def check_opus_retention(config, identity):
    opus = config["opus"]
    require(opus["advisorAgentID"] == "918cc0e7-961d-4672-9f95-b4f2918098b7", "Unexpected Opus advisor identity")
    first = local(opus["firstMarkdown"])
    require(sha(first) == opus["firstMarkdownSHA256"], "Original Opus response changed")
    require("center jug" in first.read_text().lower() and "corrections needed" in first.read_text().lower(),
            "Initial Opus findings are not retained")
    require(opus["rawRecords"] and opus["finalMarkdown"] and opus["finalActivity"], "Final Opus evidence is still pending")
    paths = [first, local(opus["firstActivity"]), local(opus["finalMarkdown"]), local(opus["finalActivity"])]
    for item in opus["rawRecords"]:
        path = local(item["source"])
        if item.get("sha256"):
            require(sha(path) == item["sha256"], f"Pinned Opus evidence changed: {path}")
        paths.append(path)
    disposition = load(local(next(r["source"] for r in config["reports"] if r["role"] == "opus-final")))
    require(disposition.get("sourceSHA256") == identity["sourceSHA256"] and disposition.get("blockingFindings") == [],
            "Final Opus disposition is stale or blocking")
    require(disposition.get("firstResponseSHA256") == sha(first) and
            disposition.get("finalResponseSHA256") == sha(local(opus["finalMarkdown"])),
            "Final Opus disposition lost its exact first or final response")
    cleanup_path = local(opus["cleanupReport"])
    cleanup = load(cleanup_path)
    require(opus.get("cleanupEquals"), "Opus advisor archive/deletion proof is still pending")
    for path, expected in opus["cleanupEquals"].items():
        require(pointer(cleanup, path) == expected, f"Opus cleanup assertion failed: {path}")
    require(opus["advisorAgentID"] in opus["cleanupEquals"].values(), "Opus cleanup proof is not bound to the owned advisor")
    paths.append(cleanup_path)
    return list(dict.fromkeys(paths))


def build(config_path):
    require(config_path.is_relative_to(PREP), "Configuration must be in the designated preparation scratch")
    config = load(config_path)
    identity = config["candidateHashes"]
    require(set(identity) == set(NAMES) and all(isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
                                              for v in identity.values()), "Final candidate hashes are still pending")
    require(identity["sourceSHA256"] not in {NEUTRAL["sourceSHA256"], INTERMEDIATE_SHA, SUPERSEDED_NATIVE_SHA, SUPERSEDED_FUNCTIONAL_SHA},
            "Final corrected source cannot be a pre-correction revision")
    require(not STAGE.exists(), "Stage already exists; inspect it before creating another revision")
    before = SCRATCH / "before"
    for key, name in NAMES.items():
        require(sha(before / name) == NEUTRAL[key], f"Frozen neutral asset changed: {name}")
        require(sha(HISTORY / "before" / name) == ORIGINAL[key], f"Frozen original asset changed: {name}")
    for name, digest in SOURCES.items():
        require(sha(AUDIT / "sources" / name) == digest, f"Approved manufacturer image changed: {name}")
    historical_snapshot = local(config["neutralPacketSnapshot"])
    validate_neutral_history(load(historical_snapshot))
    neutral_records = local(config["neutralRecordSnapshot"])
    validate_neutral_records(load(neutral_records))
    superseded_snapshot = local(config["superseded21caSnapshot"])
    superseded = check_superseded_snapshot(superseded_snapshot)
    additional_superseded = [(local(path), check_superseded_snapshot(local(path)))
                             for path in config.get("superseded21caAdditionalSnapshots", [])]
    superseded_functional_path = local(config["superseded46Snapshot"])
    superseded_functional = check_superseded_snapshot(superseded_functional_path, SUPERSEDED_FUNCTIONAL_SHA)
    diagnostic_snapshots = check_diagnostic_snapshots(config, identity)
    primary_review = check_additional_sources(config)
    intermediate = local(config["plasticTagSource"])
    tag_check = check_plastic_intermediate(intermediate)
    baseline = local(config["packageBaseline"])
    package_scope(identity, baseline)
    final_id, final_text = manifest(PACKAGE / NAMES["sourceSHA256"])
    intermediate_id, intermediate_text = manifest(intermediate)
    require(final_id == intermediate_id == "metolius.simulator-3d" and
            json.loads(final_text) == json.loads(intermediate_text),
            "Final correction changed the plastic manifest, logical contacts or source-backed facts")
    require(len(json.loads(final_text)["contacts"]) == 30, "Final logical contact inventory is not 30")
    current_human_path = AUDIT / "human-review.json"
    require(sha(current_human_path) == sha(before / "human-review.json") and
            sha(AUDIT / "source-audit.md") == sha(before / "source-audit.md"),
            "The neutral human/audit history changed; inspect the new state instead of overwriting it")
    neutral_human = load(before / "human-review.json")
    require(neutral_human.get("feedback") == ["Jagged"] and
            neutral_human.get("sourceSHA256") == NEUTRAL["sourceSHA256"] and
            "not accepted" in neutral_human.get("status", ""), "Neutral pending review history is missing")
    queue_text, lock_text = read_exact(QUEUE), read_exact(LOCK)
    row_index = queue_scope(queue_text, read_exact(before / "review-queue.json"))
    lock_scope(lock_text, read_exact(before / "model-delivery-lock.json"))
    reports = check_reports(config, identity)
    thickness, angle, thickness_text, continuity_text, measurement_paths = final_measurements(config, identity)
    opus_paths = check_opus_retention(config, identity)
    before_app_path, after_app_path = local(config["beforeApp"]), local(config["afterApp"])
    before_app = check_app(before_app_path, NEUTRAL, config["beforeAppPhase"])
    after_app = check_app(after_app_path, identity, config["afterAppPhase"])
    extra_apps = check_extra_apps(config, identity, after_app)
    fairing_app = check_fairing_app(config, identity, after_app)
    require(before_app.get("surfaceFinish") == "neutral (unchanged)" and after_app.get("surfaceFinish") == "plastic",
            "App captures must identify historical neutral and fresh plastic finishes")
    require(before_app["simulator"] != after_app["simulator"], "Fresh app proof reused the deleted neutral Simulator")
    before_installed = local(config["beforeInstalled"])
    after_installed = local(next(r["source"] for r in config["reports"] if r["role"] == "installed"))
    app_binary(before_app, before_installed, NEUTRAL)
    app_binary(after_app, after_installed, identity)
    cleanup = load(local(next(r["source"] for r in config["reports"] if r["role"] == "cleanup")))
    cleanup_devices = local(config["cleanupDevices"])
    require(cleanup.get("simulator") == after_app["simulator"] and
            cleanup.get("exactSimulatorAbsent") is True and cleanup.get("derivedDataRemoved") is True and
            cleanup.get("xcresultRemoved") is True and
            not any(d["udid"] == after_app["simulator"] for group in load(cleanup_devices)["devices"].values() for d in group),
            "Fresh retained cleanup does not prove deletion of the reviewed Simulator/build/test resources")
    raw_groups = config["rawGroups"] + config.get("pendingFunctionalRawGroups", [])
    for group in raw_groups:
        path = (ROOT / group["source"]).resolve()
        require(path.is_relative_to(ROOT) and path.is_dir(), f"Missing targeted raw group: {path}")
        destination(STAGE, group["destination"])
    for record in config["rawFiles"]:
        path = local(record["source"])
        if record.get("sha256"):
            require(sha(path) == record["sha256"], f"Pinned raw input changed: {path}")
        destination(STAGE, record["destination"])
    required_comparisons = {"original", "neutral"} | ({"front-fairing"} if fairing_app else set())
    require(set(config["cadPairs"]) == required_comparisons,
            "Original, neutral and current fairing native comparisons are required")
    for comparison in config["cadPairs"].values():
        require(set(comparison) == {"front", "side", "top"}, "Front/side/top comparison is incomplete")
        for pair in comparison.values():
            local(pair["before"])
            local(pair["after"])
    cad_preview = check_cad_preview(config, identity)
    native_grasp = check_grasp_native(config, identity)
    export_previews = check_export_previews(config, identity)
    require(config["appPairs"], "No app comparison selected")
    for name in config["appPairs"]:
        require(name + ".png" in {c["image"] for c in before_app["checks"]} and
                name + ".png" in {c["image"] for c in after_app["checks"]}, "App comparison is not in both raw capture reports")
    for key in ("summary", "question", "reviewScope", "approvalLimit", "limits", "adaptationLimits", "cleanupLogProvenance", "revisionBaseCommit"):
        require(isinstance(config[key], str) and config[key].strip(), f"Final review field is unset: {key}")
    require(re.fullmatch(r"[a-f0-9]{40}", config["revisionBaseCommit"]), "Revision base commit is invalid")
    require(sha(local("Tools/HangboardCAD/compile_board.py")) == config["compilerSHA256"], "Frozen compiler source changed")
    STAGE.mkdir()
    copies = []
    for directory, phase in ((before, "neutral"), (HISTORY / "before", "original")):
        for name in list(NAMES.values()) + ["human-review.json", "source-audit.md", "review-queue.json", "model-delivery-lock.json"]:
            retain(directory / name, STAGE / "before" / phase / name, copies)
    retain(intermediate, STAGE / "before/plastic-tag-intermediate" / NAMES["sourceSHA256"], copies)
    for name in ("before-manifest.json", "after-manifest.json", "metadata-preservation.json", "manifest-update.log", "apply_plastic_finish.py"):
        retain(SCRATCH / name, STAGE / "before/plastic-tag-intermediate" / name, copies)
    retain(historical_snapshot, STAGE / "proof/neutral-packet-snapshot.json", copies)
    retain(neutral_records, STAGE / "proof/neutral-record-snapshot.json", copies)
    retain(superseded_snapshot, STAGE / "before/superseded-21ca/snapshot.json", copies)
    for record in superseded["rawCopies"]:
        retain(destination(superseded_snapshot.parent, record["retained"]),
               destination(STAGE / "before/superseded-21ca", record["retained"]), copies)
    for path, snapshot in additional_superseded:
        base = STAGE / "before/superseded-21ca/additional" / path.parent.name
        retain(path, base / "snapshot.json", copies)
        for record in snapshot["rawCopies"]:
            retain(destination(path.parent, record["retained"]), destination(base, record["retained"]), copies)
    retain(superseded_functional_path, STAGE / "before/superseded-46df/snapshot.json", copies)
    for record in superseded_functional["rawCopies"]:
        retain(destination(superseded_functional_path.parent, record["retained"]),
               destination(STAGE / "before/superseded-46df", record["retained"]), copies)
    for path, snapshot in diagnostic_snapshots:
        base = STAGE / "before/diagnostic-native" / path.parent.name
        retain(path, base / "snapshot.json", copies)
        for record in snapshot["rawCopies"]:
            retain(destination(path.parent, record["retained"]), destination(base, record["retained"]), copies)
    retain(baseline, STAGE / "proof/all-hangboards-baseline.json", copies)
    retain(before_installed, STAGE / "proof/neutral-installed-app-provenance.json", copies)
    if fairing_app:
        retain(fairing_app["installed"], STAGE / "proof/3ff3-installed-app-provenance.json", copies)
    retain(cleanup_devices, STAGE / "proof/final-devices-after-cleanup.json", copies)
    retain(cad_preview, STAGE / "proof/final-native-preview-provenance.json", copies)
    retain(native_grasp["path"], STAGE / "proof/final-native-grasp/provenance.json", copies)
    retain(native_grasp["sections"], STAGE / "proof/final-native-grasp/native-sections.json", copies)
    retain(native_grasp["bodyMesh"], STAGE / "proof/final-native-grasp/native-body-mesh.json", copies)
    for image in native_grasp["images"]:
        retain(image, STAGE / "proof/final-native-grasp" / image.name, copies)
    for path in export_previews:
        retain(path, STAGE / "proof/exact-export-previews" / path.name, copies)
    retain(primary_review, STAGE / "sources/additional-primary/source-review.json", copies)
    for key, name in NAMES.items():
        retain(PACKAGE / name, STAGE / "candidate" / name, copies)
    for name in SOURCES:
        retain(AUDIT / "sources" / name, STAGE / "sources" / name, copies)
    for group in raw_groups:
        source_dir = (ROOT / group["source"]).resolve()
        for source in sorted(source_dir.iterdir()):
            if source.is_file() and source.suffix in group["suffixes"]:
                retain(source, destination(STAGE, group["destination"]) / source.name, copies)
    for record in config["rawFiles"]:
        retain(local(record["source"]), destination(STAGE, record["destination"]), copies)
    for index, rule in enumerate(config["reports"]):
        retain(local(rule["source"]), STAGE / "proof/reports" / (f"{index:02d}-{rule['role']}.json"), copies)
    for path in measurement_paths:
        retain(path, STAGE / "proof/final-measurements" / path.name, copies)
    for path in opus_paths:
        retain(path, STAGE / "proof/opus" / path.name, copies)
    retain(config_path, STAGE / "proof/assembly-config.json", copies)
    retain(Path(__file__), STAGE / "proof/prepare_simulator_packet.py", copies)
    for app_path, phase in ((before_app_path, "before"), (after_app_path, "after")):
        for source in sorted(app_path.parent.iterdir()):
            if source.is_file():
                retain(source, STAGE / "app" / phase / source.name, copies)
    for extra in extra_apps:
        for source in sorted(extra["path"].parent.iterdir()):
            if source.is_file():
                retain(source, STAGE / "app" / extra["name"] / source.name, copies)
    if fairing_app:
        for source in sorted(fairing_app["path"].parent.iterdir()):
            if source.is_file():
                retain(source, STAGE / "app/fairing-before" / source.name, copies)
    placements = []
    comparison_names = []
    for comparison_name, pairs in config["cadPairs"].items():
        rows = []
        for view in ("front", "side", "top"):
            images = []
            for phase in ("before", "after"):
                dest = STAGE / "previews" / f"{comparison_name}-{phase}-{view}.png"
                retain(local(pairs[view][phase]), dest, copies)
                images.append(dest)
            rows.append((view, *images))
        name = comparison_name + "-front-side-top-comparison.png"
        label = config.get("cadPairLabels", {}).get(comparison_name,
                 comparison_name + " geometry left / corrected candidate right")
        compose(rows, STAGE / name, "Simulator 3-D — " + label, placements)
        comparison_names.append(name)
    export_rows = []
    for view, pair in config["exportPreview"]["pairs"].items():
        images = []
        for phase in ("before", "after"):
            dest = STAGE / "previews" / f"exact-export-{phase}-{view}.png"
            retain(local(pair[phase]), dest, copies)
            images.append(dest)
        export_rows.append((view, *images))
    compose(export_rows, STAGE / "exact-export-front-side-top-comparison.png",
            "Simulator 3-D — original exported model left / corrected export right", placements)
    comparison_names.append("exact-export-front-side-top-comparison.png")
    if config["exportPreview"].get("fairingPairs"):
        fairing_export_rows = []
        for view, pair in config["exportPreview"]["fairingPairs"].items():
            images = []
            for phase in ("before", "after"):
                dest = STAGE / "previews" / f"fairing-exact-export-{phase}-{view}.png"
                retain(local(pair[phase]), dest, copies)
                images.append(dest)
            fairing_export_rows.append((view, *images))
        compose(fairing_export_rows, STAGE / "fairing-exact-export-front-side-top-comparison.png",
                "Simulator 3-D — prior 3ff3 export left / fairing export right", placements)
        comparison_names.append("fairing-exact-export-front-side-top-comparison.png")
    app_rows = [(name, STAGE / "app/before" / (name + ".png"), STAGE / "app/after" / (name + ".png")) for name in config["appPairs"]]
    compose(app_rows, STAGE / "app-before-after.png", "Simulator 3-D — neutral prior left / corrected plastic right", placements, app=True)
    comparison_names.append("app-before-after.png")
    if fairing_app:
        rows = [(name, STAGE / "app/fairing-before" / (name + ".png"), STAGE / "app/after" / (name + ".png"))
                for name in config["fairingApp"]["pairs"]]
        compose(rows, STAGE / "app-front-fairing-before-after.png",
                "Simulator 3-D — prior mint left / fairing mint right", placements, app=True)
        comparison_names.append("app-front-fairing-before-after.png")
    save(STAGE / "metadata-intermediate-check.json", tag_check)
    runtime = {"schemaVersion": 1, "owner": ROOT.name, "reviewNumber": 8, "package": SLUG, **identity,
               "status": "final technical/Opus evidence retained; human acceptance pending", "surfaceFinish": "plastic",
               "originalHashes": ORIGINAL, "neutralHashes": NEUTRAL, "plasticTagIntermediateSHA256": INTERMEDIATE_SHA,
               "revisionBaseCommit": config["revisionBaseCommit"], "feedback": HUMAN_FEEDBACK, "reports": reports,
               "supersedingUserFeedback": {"sourceSHA256": SUPERSEDED_NATIVE_SHA,
                   "relayedExcerpts": superseded["userFeedbackRelayedByRoot"], "scope": superseded["feedbackScope"]},
               "supersededFunctionalNativePass": {"sourceSHA256": SUPERSEDED_FUNCTIONAL_SHA,
                   "nativeGate": superseded_functional["nativeGate"], "remainingHistoricalGate": superseded_functional["reason"]},
               "historicalNativeDiagnostics": [{"sourceSHA256": data["sourceSHA256"], "status": data["status"],
                   "reason": data["reason"], "evidence": "before/diagnostic-native/" + path.parent.name + "/snapshot.json"}
                   for path, data in diagnostic_snapshots],
               "criticalNativeGraspProof": {"provenance": "proof/final-native-grasp/provenance.json",
                   "sourceSHA256": identity["sourceSHA256"], "scope": "Hash and source closure only; no shape judgment by the assembly script."},
               "exactExportPreviewProof": {"provenance": "proof/exact-export-previews/package-verification.json",
                   "graspProvenance": "proof/exact-export-previews/export-grasp-provenance.json", **identity},
               "exportLimitations": config["exportLimitations"],
                "app": {"historicalNeutral": before_app, "freshCorrectedPlastic": after_app,
                        "historical3ff3Plastic": fairing_app["report"] if fairing_app else None},
                "frontFairing": {"historicalFeedback": config.get("wavinessIntermediate"),
                                 "nativeLimits": config.get("nativeFairingLimits"),
                                 "plasticFinishUnchangedInFairingComparison": bool(fairing_app)},
                "normalComparisonDisposition": config.get("normalComparisonDisposition"),
                "stoppedCompilerAttempts": config.get("stoppedCompilerAttempts"),
               "additionalAppPhases": {extra["name"]: extra["report"] for extra in extra_apps},
               "displayThicknessEstimateMM": thickness, "maximumResidualRoofNormalAngleDegrees": angle,
               "measurements": config["measurements"], "publishedChecks": {"faceEnvelopeMM": [711, 222], "holdDepthChecks": 27, "logicalContacts": 30},
               "geometryAndFinishBothChangedInAppComparison": True, "paletteScope": "Existing app mint palette; not a manufacturer color or texture claim.",
               "unchangedHistoricalPacket": str(HISTORY.relative_to(ROOT)), "limits": config["limits"],
               "additionalPrimarySources": config["additionalSources"], "adaptationLimits": config["adaptationLimits"],
               "cleanupLogProvenance": config["cleanupLogProvenance"], "noFreshRunByAssemblyScript": True}
    save(STAGE / "runtime-validation.json", runtime)
    save(STAGE / "raw-retention.json", {"owner": ROOT.name, "byteIdenticalCopies": copies})
    save(STAGE / "composition-provenance.json", {"method": "Complete rectangles; uniform aspect-fit and letterboxing only. No crop, registration, tracing, pixel measurements or content edits.", "placements": placements})
    fairing_images = ("![Prior 3ff3 exported geometry and fairing native solid](front-fairing-front-side-top-comparison.png)\n\n"
                      "![Prior 3ff3 exact export and fairing exact export](fairing-exact-export-front-side-top-comparison.png)\n\n"
                      "![Historical mint app and fresh fairing mint app](app-front-fairing-before-after.png)\n\n"
                      "The separate fairing app comparison retains the plastic finish on both sides. Prior 3ff3 images are immutable historical captures; "
                      "the final side is a fresh actual-app run. It visually isolates this geometry revision.\n\n") if fairing_app else ""
    grasp_prefix = config.get("exportGraspReviewDestination", "proof/lip-export-grasp-review")
    text = ("# Metolius Simulator 3-D — Opus corrections, fairing and plastic, review #8\n\n" + config["summary"] + "\n\n"
            "![Original committed geometry and corrected final](original-front-side-top-comparison.png)\n\n"
            "![Prior neutral candidate and corrected final](neutral-front-side-top-comparison.png)\n\n"
            "![Original exact export and corrected exact export](exact-export-front-side-top-comparison.png)\n\n"
            "![Historical neutral app and fresh corrected plastic app](app-before-after.png)\n\n"
            + fairing_images + "The neutral-to-plastic app comparison includes **both geometry and finish changes**. The neutral frames are retained historical evidence, not a fresh run. "
            "All eight neutral and eight corrected plastic frames and AX records are retained; five selected contacts and three actual drags represent this review. "
            "Four fresh finish frames include selection and deselection; four additional critical center-jug frames retain front, high-front, end-on and rear-leaning views with at least five actual swipes. "
            "The mint appearance uses the existing app palette, not a manufacturer color or swirl reproduction. The USDZ remains unbound.\n\n"
            "Original **Jagged** feedback, the plastic instruction, the full initial Opus center-jug regression finding and subsequent Opus responses remain exact. "
            "The neutral [jagged review](../jagged-review/index.html) is immutable history superseded by the source-supported center-jug feedback. Neither prior nor final #8 is accepted.\n\n"
            "The later `21ca…` native-gated candidate was also superseded by the user's rear-ridge and forward-sloper feedback. "
            "Its earlier Opus native pass is historical. The exact candidate/proof bytes and relayed feedback excerpts remain in `before/superseded-21ca/`; final app and Opus gates apply only to the latest corrected hashes.\n\n"
            "The later `46df…` candidate genuinely passed strict native depth/edit/restore checks and fixed the rear ridge/front setback. "
            "Opus still requested two local junction fixes before export. Its native pass is retained in `before/superseded-46df/`, separate from the unwaived21ca failure; no final acceptance is carried forward.\n\n"
            "The intermediate `ec348…` lip carrier failed independent C0/contact clipping checks at the X47 split. "
            "Its exact source, partial diagnostics and completed rejected clipping review remain in `before/diagnostic-native/`; no final gate uses that source. "
            "[Final-source native grasp sections and views](proof/final-native-grasp/provenance.json) are retained separately.\n\n"
            "Additional checkpoints retain the failed `65e…` cubic approximation and `d4f…` trim BOP diagnosis. "
            "The `31bec…` checkpoint retains genuine strict native/functional passes alongside its blocked off-station seam gate. "
            "These exact historical statuses remain separate; no tolerance waiver or final acceptance is carried forward.\n\n"
            "The later 3ff3 candidate retains technical native/export/reproducibility passes and completed mint app captures. "
            "The user's waviness question and Opus identified unsupported broad front bands requiring this fairing correction. "
            "Its raw technical passes, app frames, original feedback and corrected v2 swipe bookkeeping remain immutable in `before/diagnostic-native/`. "
            "Human review remained pending; no human rejection or acceptance is recorded.\n\n"
            + config.get("nativeFairingLimits", "") + "\n\n" + config["exportLimitations"] + "\n\n"
            + config.get("normalComparisonScope", "") + "\n\n"
            "[Exact exported high-front comparison](" + grasp_prefix + "/comparison-high-front.png) · "
            "[Rear-center comparison](" + grasp_prefix + "/comparison-rear-center.png) · "
            "[Rear-oblique comparison](" + grasp_prefix + "/comparison-rear-oblique.png) · "
            "[Grasp sections](" + grasp_prefix + "/comparison-grasp-sections.png).\n\n"
            + config["adaptationLimits"] + "\n\n"
            + thickness_text + " " + continuity_text + "\n\n" + config["cleanupLogProvenance"] + "\n\n"
            "[Technical proofs](runtime-validation.json) · [Raw copy hashes](raw-retention.json) · [First Opus take](proof/opus/" + Path(config["opus"]["firstMarkdown"]).name + ") · "
            "[Final Opus take](proof/opus/" + Path(config["opus"]["finalMarkdown"]).name + "). Human acceptance remains pending; #1–7 and #9 onward are unchanged.\n")
    (STAGE / "review.md").write_text(text)
    image_html = "".join('<img src="' + name + '" alt="Complete ' + html.escape(name) + '">' for name in comparison_names)
    (STAGE / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Simulator 3-D — review #8</title><style>body{font:17px/1.55 system-ui;max-width:1500px;margin:2rem auto;padding:0 1rem}img{width:100%;height:auto}code{overflow-wrap:anywhere}</style><h1>Simulator 3-D — Opus corrections, fairing and plastic, review #8</h1><p>' + html.escape(config["summary"]) + '</p><p>Human acceptance pending. Historical neutral-to-plastic app views include geometry and finish changes. The separate prior 3ff3-to-fairing app views keep the plastic finish on both sides. Mint is the app palette.</p>' + image_html + '<p>' + html.escape(thickness_text + " " + continuity_text) + '</p><p>' + html.escape(config.get("nativeFairingLimits", "")) + '</p><p>' + html.escape(config["adaptationLimits"]) + '</p><p>Representative coverage: eight complete frames per revision, five selected contacts and three actual drags. Historical neutral and 3ff3 frames are retained exactly.</p><p><a href="review.md">Review details and Opus takes</a> · <a href="runtime-validation.json">Technical proof</a> · <a href="raw-retention.json">Raw hashes</a> · <a href="sources/product-01.jpg">Manufacturer photograph</a> · <a href="sources/product-03.jpg">Numbered source diagram</a> · <a href="sources/additional-primary/source-review.json">Additional primary-source review</a> · <a href="../jagged-review/index.html">Immutable neutral history</a></p></html>\n')
    human = copy.deepcopy(neutral_human)
    for key in ("answer", "acceptedScope", "revisionCommit"):
        human.pop(key, None)
    packet_name = TARGET.name
    human.update(identity, status="awaiting revised review #8; not accepted", currentRevision=packet_name + "/index.html",
                 revisionBaseCommit=config["revisionBaseCommit"], appReview=packet_name + "/app/after/validation.json",
                 runtimeValidation=packet_name + "/runtime-validation.json", feedback=HUMAN_FEEDBACK,
                 feedbackProvenance={"functionalExcerpts": HUMAN_FEEDBACK[3:5], "scope": superseded["feedbackScope"],
                     "functionalAdvisorReview": packet_name + "/proof/opus/opus-functional-feedback-review.md",
                     "wavinessQuestion": HUMAN_FEEDBACK[5],
                     "wavinessAdvisorReview": packet_name + "/proof/opus/opus-waviness-review.md",
                     "wavinessMeaning": "Geometry correction requested; human review remained pending, with no rejection or acceptance recorded."},
                 adaptationLimits=config["adaptationLimits"],
                 question=config["question"], reviewScope=config["reviewScope"], approvalLimit=config["approvalLimit"],
                 shownImages={packet_name + "/" + name: sha(STAGE / name) for name in comparison_names},
                 history=neutral_human.get("history", []) + [{"displayedRevision": neutral_human,
                          "userSteering": HUMAN_FEEDBACK[1:3], "advisorFeedback": "Opus source-supported center-jug regression blocker and recommended flat/round sloper join smoothing; exact responses retained.",
                          "result": "Neutral candidate superseded; no human acceptance recorded."},
                          {"displayedNativeCandidate": {"sourceSHA256": SUPERSEDED_NATIVE_SHA,
                              "status": "Historical native gate only; no final app or human acceptance"},
                           "relayedUserFeedback": superseded["userFeedbackRelayedByRoot"],
                           "feedbackScope": superseded["feedbackScope"],
                           "evidence": packet_name + "/before/superseded-21ca/snapshot.json",
                           "result": "Superseded by further functional correction; no human acceptance recorded."},
                          {"displayedNativeCandidate": {"sourceSHA256": SUPERSEDED_FUNCTIONAL_SHA,
                              "status": "Strict native pass; rear ridge/front setback resolved; pre-export local junction correction requested"},
                           "advisorFeedback": superseded_functional["reason"],
                           "evidence": packet_name + "/before/superseded-46df/snapshot.json",
                           "result": "Superseded by local junction correction; no final export/app/human acceptance recorded."}] +
                         [{"diagnosticNativeCandidate": {"sourceSHA256": data["sourceSHA256"], "status": data["status"]},
                           "reason": data["reason"],
                           "evidence": packet_name + "/before/diagnostic-native/" + path.parent.name + "/snapshot.json",
                           "result": "Historical diagnostic checkpoint; its exact pass/blocked statuses remain distinct, with no final acceptance carried forward."}
                          for path, data in diagnostic_snapshots])
    current_queue = json.loads(queue_text)
    row = copy.deepcopy(current_queue["boards"][row_index])
    queue_prefix = SLUG + "/" + packet_name
    row.update(sourceSHA256=identity["sourceSHA256"], humanReview="awaiting revised review #8; not accepted",
               reviewPage=queue_prefix + "/index.html", latestRevision=queue_prefix + "/review.md",
               appReview=queue_prefix + "/app/after/validation.json", appReviewPage=queue_prefix + "/index.html",
               runtimeRevision=queue_prefix + "/runtime-validation.json", reviewFeedback=HUMAN_FEEDBACK,
               comparisons=[queue_prefix + "/" + name for name in comparison_names])
    row["presentations"]["primary"].update(modelSHA256=identity["modelSHA256"], descriptorSHA256=identity["descriptorSHA256"])
    entry = copy.deepcopy(json.loads(lock_text)["migratedPackages"][SLUG])
    require(entry["sourceSHA256"] == identity["sourceSHA256"] and entry["assetSHA256"] == identity["modelSHA256"] and
            entry["descriptorSHA256"] == identity["descriptorSHA256"], "Root delivery-hash integration is incomplete")
    prefix = str(TARGET.relative_to(ROOT))
    previous_app = entry.get("nativeAppValidation")
    history = entry.get("nativeAppHistory", [])
    if previous_app and previous_app not in history and previous_app != prefix + "/app/after/validation.json":
        history = history + [previous_app]
    entry.update(provenance=prefix + "/review.md", comparison=prefix + "/original-front-side-top-comparison.png",
                 nativeAppValidation=prefix + "/app/after/validation.json", nativeAppHistory=history,
                 individualReview=prefix + "/index.html", runtimeValidation=prefix + "/runtime-validation.json",
                 geometryAcceptance="pending revised human review #8", geometryAcceptanceRecord=str(current_human_path.relative_to(ROOT)))
    notice = ("# Metolius Simulator 3-D — current Opus corrections, fairing and plastic revision\n\n" + config["summary"] + "\n\n"
              "[Current review packet](" + packet_name + "/review.md) and [hash-bound technical/Opus proof](" + packet_name + "/runtime-validation.json) supersede the prior neutral candidate after the source-supported center-jug feedback. "
              "Human acceptance remains pending. The existing app mint palette reflects `display.surfaceFinish=plastic`; no manufacturer color or texture claim is made.\n\n"
              + thickness_text + " " + continuity_text + "\n\n"
               + config["adaptationLimits"] + "\n\n"
               "The later 3ff3 technical pass and mint app checkpoint remain exact historical evidence. The user's waviness question and retained Opus finding prompted the new front-profile fairing; that checkpoint carried no human acceptance or rejection. "
               + config.get("nativeFairingLimits", "") + "\n\n"
              "The neutral audit and exact review state below are historical; its [jagged packet](jagged-review/index.html) remains immutable. "
              "Both initial and neutral candidates and raw feedback are preserved in [before/](" + packet_name + "/before/).\n\n---\n\n")
    updates = {str((AUDIT / "source-audit.md").relative_to(ROOT)): notice + read_exact(before / "source-audit.md"),
               str(current_human_path.relative_to(ROOT)): json.dumps(human, indent=2) + "\n",
               str(QUEUE.relative_to(ROOT)): replace_json_value(queue_text, ("boards", row_index), row),
               str(LOCK.relative_to(ROOT)): replace_json_value(lock_text, ("migratedPackages", SLUG), entry)}
    save(PREP / "planned-record-updates.json", {"inputSHA256": {rel: sha(ROOT / rel) for rel in updates}, "updates": updates})
    save(STAGE / "provenance.json", {"owner": ROOT.name, "package": SLUG, "reviewNumber": 8, **identity,
         "originalHashes": ORIGINAL, "neutralHashes": NEUTRAL, "plasticTagIntermediateSHA256": INTERMEDIATE_SHA,
         "originalFeedback": "Jagged", "humanAcceptance": "pending", "assemblyProgramSHA256": sha(__file__),
         "createdAtUTC": datetime.now(timezone.utc).isoformat()})
    save(STAGE / "retained-files.json", {"files": {str(p.relative_to(STAGE)): {"sha256": sha(p), "bytes": p.stat().st_size}
                                               for p in sorted(STAGE.rglob("*")) if p.is_file()}})
    print(json.dumps({"stage": str(STAGE.relative_to(ROOT)), "rawCopies": len(copies), "trackedMutation": False, "humanAcceptance": "pending"}))


def verify(base, installed=False):
    provenance = load(base / "provenance.json")
    identity = {key: provenance[key] for key in NAMES}
    package_scope(identity, base / "proof/all-hangboards-baseline.json")
    validate_neutral_history(load(base / "proof/neutral-packet-snapshot.json"))
    check_superseded_snapshot(base / "before/superseded-21ca/snapshot.json")
    check_superseded_snapshot(base / "before/superseded-46df/snapshot.json", SUPERSEDED_FUNCTIONAL_SHA)
    check_diagnostic_snapshots(load(base / "proof/assembly-config.json"), identity, packet=base)
    for rel, item in load(base / "retained-files.json")["files"].items():
        require(sha(destination(base, rel)) == item["sha256"], f"Packet bytes changed: {rel}")
    for record in load(base / "raw-retention.json")["byteIdenticalCopies"]:
        require(sha(destination(base, record["retained"])) == record["sha256"], f"Raw retained bytes changed: {record}")
    for phase, hashes in (("neutral", NEUTRAL), ("original", ORIGINAL)):
        for key, name in NAMES.items():
            require(sha(base / "before" / phase / name) == hashes[key], f"Prior {phase} source/export bytes changed")
    if installed:
        expected = load(PREP / "planned-record-updates.json")["updates"]
        require(all(read_exact(ROOT / rel) == text for rel, text in expected.items()), "Applied review records differ")
    print(json.dumps({"packet": str(base.relative_to(ROOT)), "passed": True, "humanAcceptance": "pending"}))


def apply():
    verify(STAGE)
    proposals = load(PREP / "planned-record-updates.json")
    allowed = {str((AUDIT / "source-audit.md").relative_to(ROOT)), str((AUDIT / "human-review.json").relative_to(ROOT)),
               str(QUEUE.relative_to(ROOT)), str(LOCK.relative_to(ROOT))}
    require(set(proposals["updates"]) == set(proposals["inputSHA256"]) == allowed, "Mutation escapes the four approved review records")
    for rel, digest in proposals["inputSHA256"].items():
        require(sha(ROOT / rel) == digest, f"Review record changed since build: {rel}")
    queue_index = next(i for i, row in enumerate(load(QUEUE)["boards"]) if row["number"] == 8)
    only_value_changed(read_exact(QUEUE), proposals["updates"][str(QUEUE.relative_to(ROOT))], ("boards", queue_index))
    only_value_changed(read_exact(LOCK), proposals["updates"][str(LOCK.relative_to(ROOT))], ("migratedPackages", SLUG))
    audit_update = proposals["updates"][str((AUDIT / "source-audit.md").relative_to(ROOT))]
    require(audit_update.endswith(read_exact(SCRATCH / "before/source-audit.md")), "Historical source-audit bytes changed")
    pending_human = json.loads(proposals["updates"][str((AUDIT / "human-review.json").relative_to(ROOT))])
    require(pending_human["status"] == "awaiting revised review #8; not accepted" and "answer" not in pending_human,
            "The deferred updater cannot accept review #8")
    require(any(item.get("displayedRevision") == load(SCRATCH / "before/human-review.json")
                for item in pending_human["history"]),
            "The neutral human review was not preserved")
    files = [p for p in sorted(STAGE.rglob("*")) if p.is_file()]
    for source in files:
        require(not source.is_symlink(), "Stage contains a symlink")
        target = destination(TARGET, str(source.relative_to(STAGE)))
        require(not target.exists() or sha(target) == sha(source), f"Existing packet differs: {target}")
    for rel in proposals["updates"]:
        require(not (ROOT / rel).with_name(Path(rel).name + ".placid-badger-review-tmp").exists(), "A review temporary file already exists")
    for source in files:
        target = destination(TARGET, str(source.relative_to(STAGE)))
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for rel, text in proposals["updates"].items():
        target = ROOT / rel
        temporary = target.with_name(target.name + ".placid-badger-review-tmp")
        temporary.write_bytes(text.encode("utf-8"))
        temporary.replace(target)
    verify(TARGET, installed=True)


def self_test():
    old = '{\r\n  "boards": [{"number":7,"note":"brace } ["},{"number":8},{"number":9}],\r\n  "other":{"k":true}\r\n}\r\n'
    changed = replace_json_value(old, ("boards", 1), {"number": 8, "status": "pending"})
    only_value_changed(old, changed, ("boards", 1))
    try:
        only_value_changed(old, changed.replace('"k":true', '"k":false'), ("boards", 1))
    except ValueError:
        pass
    else:
        raise AssertionError("Unrelated JSON mutation escaped the guard")
    require(pointer({"a/b": {"~c": [0, 2]}}, "/a~1b/~0c/1") == 2, "JSON pointer escaping failed")
    with tempfile.TemporaryDirectory(prefix="placid-badger-plastic-packet-test-", dir=PREP) as temp:
        temp = Path(temp)
        q = temp / "queue.json"
        q.write_bytes(old.encode())
        require(read_exact(q) == old, "Exact reads normalized CRLF")
        retained = temp / "retained.json"
        retain(q, retained, None)
        digest = sha(retained)
        q.write_text('{"changed":true}\n')
        try:
            retain(q, retained, None)
        except ValueError:
            pass
        else:
            raise AssertionError("A changed raw file overwrote its frozen snapshot")
        require(sha(retained) == digest, "Failed retain mutated historical evidence")
        try:
            destination(temp, "../escape.json")
        except ValueError:
            pass
        else:
            raise AssertionError("Packet destination escaped its owner")
        author = temp / "native-author"
        grasp = author / "grasp-review"
        grasp.mkdir(parents=True)
        source, body_mesh = author / "source.FCStd", author / "native-body-mesh.json"
        source.write_bytes(b"source-bound native fixture")
        body_mesh.write_text('{"nativeMeshFixture":true}\n')
        digest = sha(source)
        sections = grasp / "native-sections.json"
        save(sections, {"sourceSHA256": digest, "sections": []})
        images = {}
        for name in ("high-front.png", "native-grasp-sections.png", "rear-center.png", "rear-oblique.png"):
            image = grasp / name
            image.write_bytes(("hash fixture " + name).encode())
            images["grasp-review/" + name] = sha(image)
        proof = grasp / "provenance.json"
        save(proof, {"sourcePath": str(source.relative_to(ROOT)), "sourceSHA256": digest,
                     "sectionsSHA256": sha(sections), "nativeBodyMeshSHA256": sha(body_mesh), "images": images})
        grasp_config = {"functionalGraspNativeProof": {"source": str(proof.relative_to(ROOT)),
                        "sourceSHA256": "@sourceSHA256", "sections": str(sections.relative_to(ROOT)),
                        "bodyMesh": str(body_mesh.relative_to(ROOT))}}
        check_grasp_native(grasp_config, {"sourceSHA256": digest})
        body_mesh.write_text('{"nativeMeshFixture":"stale"}\n')
        try:
            check_grasp_native(grasp_config, {"sourceSHA256": digest})
        except ValueError:
            pass
        else:
            raise AssertionError("Changed critical native mesh escaped its provenance guard")
    check_plastic_intermediate(PREP / "plastic-tag-intermediate" / NAMES["sourceSHA256"])
    validate_neutral_history(load(PREP / "neutral-packet-snapshot.json"))
    validate_neutral_records(load(PREP / "before-records-snapshot.json"))
    config = load(PREP / "packet-config.json")
    if config.get("normalComparisonDisposition"):
        disposition = config["normalComparisonDisposition"]
        normal = load(local(disposition["supplement"]))
        require(sha(local(disposition["supplement"])) == disposition["supplementSHA256"],
                "Same-face supplement changed after its reviewed snapshot")
        check_legacy_normal_reference(config, {"sourceSHA256": disposition["sourceSHA256"]}, normal)
        stale = copy.deepcopy(normal)
        stale["rawLegacyComparison"]["sha256"] = "0" * 64
        try:
            check_legacy_normal_reference(config, {"sourceSHA256": disposition["sourceSHA256"]}, stale)
        except ValueError:
            pass
        else:
            raise AssertionError("Changed raw normal evidence escaped its supplemental hash guard")
    check_diagnostic_snapshots(config, {"sourceSHA256": ORIGINAL["sourceSHA256"]})
    for rule in config["diagnosticNativeSnapshots"]:
        try:
            check_diagnostic_snapshots(config, {"sourceSHA256": rule["sourceSHA256"]})
        except ValueError:
            pass
        else:
            raise AssertionError("A rejected diagnostic source escaped the final-source guard")
    export_config, export_identity = config, config["candidateHashes"]
    preview = config["exportPreview"]
    if (any(v is None for v in export_identity.values()) or
            not all(preview.get(k) for k in ("source", "graspSource", "directory")) or
            any(pair.get(phase) is None for pairs in (preview["pairs"], preview.get("fairingPairs", {}))
                for pair in pairs.values() for phase in ("before", "after"))):
        frozen = PREP / "held-3ff3-wavy-app-question"
        data = load(frozen / "snapshot.json")
        export_identity = {k: data[k] for k in NAMES}
        directory = frozen / "proof"
        export_config = {"exportPreview": {"directory": str(directory.relative_to(ROOT)),
                         "source": str((directory / "package-verification.json").relative_to(ROOT)),
                         "graspSource": str((directory / "export-grasp-provenance.json").relative_to(ROOT)),
                         "pairs": {view: {"before": str((directory / "export-review" / ("original-9449-" + view + ".png")).relative_to(ROOT)),
                                          "after": str((directory / "export-review" / ("candidate-" + view + ".png")).relative_to(ROOT))}
                                   for view in ("front", "side", "top")}}}
    check_export_previews(export_config, export_identity)
    stale_identity = dict(export_identity, modelSHA256="0" * 64)
    try:
        check_export_previews(export_config, stale_identity)
    except ValueError:
        pass
    else:
        raise AssertionError("A stale shipped model escaped the exported-image provenance guard")
    print(json.dumps({"selfTest": "passed", "trackedMutation": False, "externalResources": []}))


def readiness(config_path):
    config = load(config_path)
    pending = []

    def inspect(value, path):
        if value is None:
            if path not in {"/measurements/continuityReport", "/measurements/normalAnglePointer",
                            "/measurements/maximumResidualRoofNormalAngleDegrees", "/measurements/normalAngleProbeEpsilonMM"}:
                pending.append(path)
        elif isinstance(value, dict):
            for key, item in value.items():
                inspect(item, path + "/" + key.replace("~", "~0").replace("/", "~1"))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                inspect(item, path + "/" + str(index))

    inspect(config, "")
    print(json.dumps({"readyForBuild": not pending, "pendingFields": pending,
                      "allProofPathsStillValidatedAtBuild": True, "trackedMutation": False}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "apply", "verify", "self-test", "readiness"))
    parser.add_argument("--config", type=Path, default=PREP / "packet-config.json")
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    if args.action == "build":
        build(args.config.resolve())
    elif args.action == "apply":
        apply()
    elif args.action == "verify":
        verify(TARGET if args.installed else STAGE, args.installed)
    elif args.action == "readiness":
        readiness(args.config.resolve())
    else:
        self_test()
