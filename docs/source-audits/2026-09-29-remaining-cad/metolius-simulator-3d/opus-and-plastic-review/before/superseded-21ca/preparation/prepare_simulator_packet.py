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
ROLES = {"author", "independent-native", "independent-export", "compiler", "geometry-disposition",
         "ios-tests", "python-tests", "package", "staging", "build", "installed", "app-visual", "cleanup", "opus-final"}
HUMAN_FEEDBACK = ["Jagged", "It should be tagged as plastic so it gets colored", "And ask opus for its take"]



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
        paths.append(continuity_path)
    else:
        require(angle is None, "A normal-angle claim has no final report")
    thickness_text = (f"Overall thickness is measured {thickness:.7f} mm, a display estimate. "
                      "Published 711 × 222 mm face dimensions and all 27 hold-depth checks retain their strict gates. "
                      "Exact 94 mm thickness preservation is not claimed.")
    continuity_text = (f"Finite continuity probes measure residual roof normal changes up to {angle:.4f}°. "
                       if angle is not None else "No global continuity claim is made. ")
    continuity_text += "Finite probes do not establish global roof G1 or C1 continuity. Estimated transitions, rounding, loft controls and thickness remain display geometry."
    return thickness, angle, thickness_text, continuity_text, paths


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
                    require(sha(local(rel)) == digest, f"Linked {rule['role']} proof bytes changed: {rel}")
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
            data.get("allFiveWholeAfterImagesInspected") is True,
            "Final native preview provenance is stale or lacks whole-image inspection")
    directory = (ROOT / config["cadPreviewDirectory"]).resolve()
    require(directory.is_relative_to(ROOT) and directory.is_dir(), "Wrong final native preview directory")
    for name, digest in data["imageHashes"].items():
        require(sha(destination(directory, name)) == digest, f"Final native preview image changed: {name}")
    for comparison in config["cadPairs"].values():
        for pair in comparison.values():
            for phase in ("before", "after"):
                image = local(pair[phase])
                require(data["imageHashes"].get(image.name) == sha(image),
                        f"Paired native frame is absent from the final source-bound provenance: {image}")
    return path


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
    require(identity["sourceSHA256"] not in {NEUTRAL["sourceSHA256"], INTERMEDIATE_SHA},
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
    for group in config["rawGroups"]:
        path = (ROOT / group["source"]).resolve()
        require(path.is_relative_to(ROOT) and path.is_dir(), f"Missing targeted raw group: {path}")
        destination(STAGE, group["destination"])
    for record in config["rawFiles"]:
        path = local(record["source"])
        if record.get("sha256"):
            require(sha(path) == record["sha256"], f"Pinned raw input changed: {path}")
        destination(STAGE, record["destination"])
    require(set(config["cadPairs"]) == {"original", "neutral"}, "Both original and neutral native comparisons are required")
    for comparison in config["cadPairs"].values():
        require(set(comparison) == {"front", "side", "top"}, "Front/side/top comparison is incomplete")
        for pair in comparison.values():
            local(pair["before"])
            local(pair["after"])
    cad_preview = check_cad_preview(config, identity)
    require(config["appPairs"], "No app comparison selected")
    for name in config["appPairs"]:
        require(name + ".png" in {c["image"] for c in before_app["checks"]} and
                name + ".png" in {c["image"] for c in after_app["checks"]}, "App comparison is not in both raw capture reports")
    for key in ("summary", "question", "reviewScope", "approvalLimit", "limits", "cleanupLogProvenance", "revisionBaseCommit"):
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
    retain(baseline, STAGE / "proof/all-hangboards-baseline.json", copies)
    retain(before_installed, STAGE / "proof/neutral-installed-app-provenance.json", copies)
    retain(cleanup_devices, STAGE / "proof/final-devices-after-cleanup.json", copies)
    retain(cad_preview, STAGE / "proof/final-native-preview-provenance.json", copies)
    for key, name in NAMES.items():
        retain(PACKAGE / name, STAGE / "candidate" / name, copies)
    for name in SOURCES:
        retain(AUDIT / "sources" / name, STAGE / "sources" / name, copies)
    for group in config["rawGroups"]:
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
        compose(rows, STAGE / name, f"Simulator 3-D — {comparison_name} geometry left / corrected candidate right", placements)
        comparison_names.append(name)
    app_rows = [(name, STAGE / "app/before" / (name + ".png"), STAGE / "app/after" / (name + ".png")) for name in config["appPairs"]]
    compose(app_rows, STAGE / "app-before-after.png", "Simulator 3-D — neutral prior left / corrected plastic right", placements, app=True)
    comparison_names.append("app-before-after.png")
    save(STAGE / "metadata-intermediate-check.json", tag_check)
    runtime = {"schemaVersion": 1, "owner": ROOT.name, "reviewNumber": 8, "package": SLUG, **identity,
               "status": "final technical/Opus evidence retained; human acceptance pending", "surfaceFinish": "plastic",
               "originalHashes": ORIGINAL, "neutralHashes": NEUTRAL, "plasticTagIntermediateSHA256": INTERMEDIATE_SHA,
               "revisionBaseCommit": config["revisionBaseCommit"], "feedback": HUMAN_FEEDBACK, "reports": reports,
               "app": {"historicalNeutral": before_app, "freshCorrectedPlastic": after_app},
               "displayThicknessEstimateMM": thickness, "maximumResidualRoofNormalAngleDegrees": angle,
               "measurements": config["measurements"], "publishedChecks": {"faceEnvelopeMM": [711, 222], "holdDepthChecks": 27, "logicalContacts": 30},
               "geometryAndFinishBothChangedInAppComparison": True, "paletteScope": "Existing app mint palette; not a manufacturer color or texture claim.",
               "unchangedHistoricalPacket": str(HISTORY.relative_to(ROOT)), "limits": config["limits"],
               "cleanupLogProvenance": config["cleanupLogProvenance"], "noFreshRunByAssemblyScript": True}
    save(STAGE / "runtime-validation.json", runtime)
    save(STAGE / "raw-retention.json", {"owner": ROOT.name, "byteIdenticalCopies": copies})
    save(STAGE / "composition-provenance.json", {"method": "Complete rectangles; uniform aspect-fit and letterboxing only. No crop, registration, tracing, pixel measurements or content edits.", "placements": placements})
    text = ("# Metolius Simulator 3-D — Opus corrections and plastic, review #8\n\n" + config["summary"] + "\n\n"
            "![Original committed geometry and corrected final](original-front-side-top-comparison.png)\n\n"
            "![Prior neutral candidate and corrected final](neutral-front-side-top-comparison.png)\n\n"
            "![Historical neutral app and fresh corrected plastic app](app-before-after.png)\n\n"
            "The app comparison includes **both geometry and finish changes**. The neutral frames are retained historical evidence, not a fresh run. "
            "All eight neutral and eight corrected plastic frames and AX records are retained; five selected contacts and three actual drags represent this review. "
            "The mint appearance uses the existing app palette, not a manufacturer color or swirl reproduction. The USDZ remains unbound.\n\n"
            "Original **Jagged** feedback, the plastic instruction, the full initial Opus center-jug regression finding and subsequent Opus responses remain exact. "
            "The neutral [jagged review](../jagged-review/index.html) is immutable history superseded by the source-supported center-jug feedback. Neither prior nor final #8 is accepted.\n\n"
            + thickness_text + " " + continuity_text + "\n\n" + config["cleanupLogProvenance"] + "\n\n"
            "[Technical proofs](runtime-validation.json) · [Raw copy hashes](raw-retention.json) · [First Opus take](proof/opus/" + Path(config["opus"]["firstMarkdown"]).name + ") · "
            "[Final Opus take](proof/opus/" + Path(config["opus"]["finalMarkdown"]).name + "). Human acceptance remains pending; #1–7 and #9 onward are unchanged.\n")
    (STAGE / "review.md").write_text(text)
    image_html = "".join('<img src="' + name + '" alt="Complete ' + html.escape(name) + '">' for name in comparison_names)
    (STAGE / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Simulator 3-D — review #8</title><style>body{font:17px/1.55 system-ui;max-width:1500px;margin:2rem auto;padding:0 1rem}img{width:100%;height:auto}code{overflow-wrap:anywhere}</style><h1>Simulator 3-D — Opus corrections and plastic, review #8</h1><p>' + html.escape(config["summary"]) + '</p><p>Human acceptance pending. App comparison: historical neutral prior left, corrected geometry and plastic finish right. Mint is the app palette.</p>' + image_html + '<p>' + html.escape(thickness_text + " " + continuity_text) + '</p><p>Representative coverage: eight complete frames per revision, five selected contacts and three actual drags. Historical neutral frames are retained exactly.</p><p><a href="review.md">Review details and Opus takes</a> · <a href="runtime-validation.json">Technical proof</a> · <a href="raw-retention.json">Raw hashes</a> · <a href="sources/product-01.jpg">Manufacturer photograph</a> · <a href="sources/product-03.jpg">Numbered source diagram</a> · <a href="../jagged-review/index.html">Immutable neutral history</a></p></html>\n')
    human = copy.deepcopy(neutral_human)
    for key in ("answer", "acceptedScope", "revisionCommit"):
        human.pop(key, None)
    packet_name = TARGET.name
    human.update(identity, status="awaiting revised review #8; not accepted", currentRevision=packet_name + "/index.html",
                 revisionBaseCommit=config["revisionBaseCommit"], appReview=packet_name + "/app/after/validation.json",
                 runtimeValidation=packet_name + "/runtime-validation.json", feedback=HUMAN_FEEDBACK,
                 question=config["question"], reviewScope=config["reviewScope"], approvalLimit=config["approvalLimit"],
                 shownImages={packet_name + "/" + name: sha(STAGE / name) for name in comparison_names},
                 history=neutral_human.get("history", []) + [{"displayedRevision": neutral_human,
                          "userSteering": HUMAN_FEEDBACK[1:], "advisorFeedback": "Opus source-supported center-jug regression blocker and recommended flat/round sloper join smoothing; exact responses retained.",
                          "result": "Neutral candidate superseded; no human acceptance recorded."}])
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
    notice = ("# Metolius Simulator 3-D — current Opus corrections and plastic revision\n\n" + config["summary"] + "\n\n"
              "[Current review packet](" + packet_name + "/review.md) and [hash-bound technical/Opus proof](" + packet_name + "/runtime-validation.json) supersede the prior neutral candidate after the source-supported center-jug feedback. "
              "Human acceptance remains pending. The existing app mint palette reflects `display.surfaceFinish=plastic`; no manufacturer color or texture claim is made.\n\n"
              + thickness_text + " " + continuity_text + "\n\n"
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
    require(pending_human["history"][-1]["displayedRevision"] == load(SCRATCH / "before/human-review.json"),
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
    check_plastic_intermediate(PREP / "plastic-tag-intermediate" / NAMES["sourceSHA256"])
    validate_neutral_history(load(PREP / "neutral-packet-snapshot.json"))
    validate_neutral_records(load(PREP / "before-records-snapshot.json"))
    print(json.dumps({"selfTest": "passed", "trackedMutation": False, "externalResources": []}))


def readiness(config_path):
    config = load(config_path)
    pending = []

    def inspect(value, path):
        if value is None:
            if path not in {"/measurements/continuityReport", "/measurements/normalAnglePointer",
                            "/measurements/maximumResidualRoofNormalAngleDegrees"}:
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
