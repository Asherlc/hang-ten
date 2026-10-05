#!/usr/bin/env python3
"""Deferred Simulator #8 packet builder. No subprocesses or resource launches."""
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
TARGET = AUDIT / "jagged-review"
STAGE = PREP / "staged-packet"
PACKAGE = ROOT / "Hangboards" / SLUG
QUEUE = AUDIT.parent / "review-queue.json"
LOCK = ROOT / "docs/model-delivery-lock.json"
NAMES = {"sourceSHA256": SLUG + ".FCStd", "modelSHA256": "assets/primary.usdz",
         "descriptorSHA256": "assets/primary.model.json"}
PRIOR = {"sourceSHA256": "9449f932e98c23fc9115d7a2cd0cfe5aacb158fd574d7ba573287ef7c5b67222",
         "modelSHA256": "a1d2a2a5e0cc4cc955ecf9b25c47b049bd71d8c70b3b2269fa167b9defbe6d16",
         "descriptorSHA256": "1c485ce852b600cb69eb1bf4036f73245b03cb88715e46f8ee789f3601f5115e"}
SOURCES = {"product-01.jpg": "5ac1677d6280dc90242cb1dcef47691647fd3f5a9adc3c465838e930075f58a9",
           "product-03.jpg": "e9561ab3fb6d3a85014097dcbdb0bc3d9c4079f9cb0954bd87965d180329932a"}
ROLES = {"author", "independent", "compiler", "ios-tests", "python-tests",
         "package", "staging", "build", "installed", "cleanup"}


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
    files = load(baseline_path)["files"]
    outside = {name: item for name, item in files.items()
               if not name.startswith("Hangboards/" + SLUG + "/")}
    require(len(files) == 206 and len(outside) == 203, "Unexpected package baseline scope")
    require(all(sha(local(name)) == item["sha256"] for name, item in outside.items()),
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
            draw.text((x, y), ("Before — " if column == 0 else "After — ") + label,
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


def build(config_path):
    require(config_path.is_relative_to(ROOT), "Configuration must belong to this workspace")
    config = load(config_path)
    identity = config["candidateHashes"]
    require(set(identity) == set(NAMES) and all(isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
                                               for v in identity.values()), "Final candidate hashes are unset")
    require(not STAGE.exists(), "staged-packet already exists; use a new preparation directory or inspect it")
    before = TARGET / "before"
    require(all(sha(AUDIT / "sources" / name) == digest for name, digest in SOURCES.items()),
            "An approved retained manufacturer image changed")
    for key, name in NAMES.items():
        require(sha(before / name) == PRIOR[key], f"Wrong retained prior asset: {name}")
        require(sha(PACKAGE / name) == identity[key], f"Canonical candidate is not integrated: {name}")
    baseline = local(config["packageBaseline"])
    package_scope(identity, baseline)
    require(manifest(before / NAMES["sourceSHA256"]) == manifest(PACKAGE / NAMES["sourceSHA256"]),
            "Raw native manifest changed")
    require(len(json.loads(manifest(PACKAGE / NAMES["sourceSHA256"])[1])["contacts"]) == 30,
            "Contact inventory changed")
    original_human = load(before / "human-review.json")
    require(original_human.get("feedback") == ["Jagged"], "Original Jagged feedback is not frozen")
    current_queue, original_queue = load(QUEUE), load(before / "review-queue.json")
    require(len(current_queue["boards"]) == len(original_queue["boards"]) == 21 and
            all(a == b for a, b in zip(current_queue["boards"], original_queue["boards"])
                if a["number"] != 8), "Another queue row changed")
    require([row["number"] for row in current_queue["boards"]] == list(range(1, 22)),
            "Review numbers or order changed")
    require(all(str(row["humanReview"]).startswith("reviewed") for row in current_queue["boards"][:7]),
            "First seven review records are not accepted")
    assertions = config["reports"]
    require({r["role"] for r in assertions} == ROLES, "Required technical report roles are missing")
    reports = []
    for rule in assertions:
        source = local(rule["source"])
        data = load(source)
        require(rule.get("equals"), f"No pass assertions configured for {rule['role']}")
        for path, expected in rule["equals"].items():
            expected = identity[expected[1:]] if isinstance(expected, str) and expected.startswith("@") else expected
            require(pointer(data, path) == expected, f"Failed {rule['role']} assertion: {path}")
        if rule.get("validateLinkedHashes"):
            for rel, digest in data.get("fileSHA256", {}).items():
                require(sha(local(rel)) == digest, f"Linked technical proof changed: {rel}")
            for rel, digest in data.get("imageSHA256", {}).items():
                require(sha(local(rel)) == digest, f"Reviewed image bytes changed: {rel}")
        if "candidateSHA256" in data:
            require(set(data["candidateSHA256"].values()) == set(identity.values()),
                    f"Independent export report hashes are stale: {source}")
        reports.append({"role": rule["role"], "source": str(source.relative_to(ROOT)),
                        "sha256": sha(source), "assertions": rule["equals"]})
    # A disposition is a gate; it never erases or alters the raw failed measurement.
    disposition_paths = [local(p) for p in config["dispositions"]]
    require(len(disposition_paths) == 2, "Both native and continuity dispositions are required")
    for path in disposition_paths:
        data = load(path)
        require(data["sourceSHA256"] == identity["sourceSHA256"] and data["blockingFindings"] == [],
                f"Disposition is stale or blocking: {path}")
        if "rawCheckReport" in data:
            require(sha(path.parent / data["rawCheckReport"]) == data["rawCheckSHA256"],
                    "Native disposition lost its exact raw failure")
        for rel, digest in data.get("fileSHA256", {}).items():
            require(sha(local(rel)) == digest, f"Continuity raw evidence changed: {rel}")
    measurements = config["measurements"]
    native_path, continuity_path = local(measurements["nativeReport"]), local(measurements["continuityReport"])
    native, continuity = load(native_path), load(continuity_path)
    require(native["sourceSHA256"] == continuity["sourceSHA256"] == identity["sourceSHA256"],
            "Final measurement reports are stale")
    thickness = measurements["measuredThicknessMM"]
    normal_angle = measurements["maximumResidualRoofNormalAngleDegrees"]
    require(isinstance(thickness, (int, float)) and thickness == native["envelopeXYZMM"][1],
            "Thickness wording is not sourced from the final native report")
    require(isinstance(normal_angle, (int, float)) and normal_angle ==
            continuity["remainingDerivativeCreases"]["maximumMeasuredInteriorNormalAngleDegrees"],
            "Residual roof normal wording is not sourced from the final continuity report")
    require(len(native["publishedDepthChecks"]) == 27 and
            all(abs(d["expected"] - d["actual"]) < 0.02 for d in native["publishedDepthChecks"].values()) and
            abs(native["envelopeXYZMM"][0] - 711) < 0.02 and abs(native["envelopeXYZMM"][2] - 222) < 0.02,
            "Published face or depth checks no longer meet their strict original gates")
    difference = thickness - 94.0
    thickness_wording = (f"Authored overall thickness is measured {thickness:.7f} mm, a display estimate "
                         f"with a {difference:+.7f} mm difference from the former ~94 mm estimate. "
                         "Exact 94 mm preservation is not claimed. Published 711 × 222 mm face dimensions "
                         "and 27 hold-depth checks retain their strict original gates.")
    continuity_wording = (f"The final continuity report measures residual roof normal changes up to "
                          f"{normal_angle:.4f}°. Finite probes do not establish global roof G1 or C1 continuity.")
    before_app_path, after_app_path = local(config["beforeApp"]), local(config["afterApp"])
    before_app = check_app(before_app_path, PRIOR, "before")
    after_app = check_app(after_app_path, identity, "after")
    before_installed = local(config["beforeInstalled"])
    after_installed = local(next(r["source"] for r in assertions if r["role"] == "installed"))
    app_binary(before_app, before_installed, PRIOR)
    app_binary(after_app, after_installed, identity)
    cleanup = load(local(next(r["source"] for r in assertions if r["role"] == "cleanup")))
    cleanup_devices = local(config["cleanupDevices"])
    require(cleanup.get("simulator") == after_app["simulator"] and
            not any(d["udid"] == after_app["simulator"]
                    for group in load(cleanup_devices)["devices"].values() for d in group),
            "Retained device list does not prove deletion of the exact reviewed Simulator")
    # Check deferred paths before creating the scratch stage.
    for record in config["rawFiles"]:
        source = local(record["source"])
        if record.get("sha256") is not None:
            require(sha(source) == record["sha256"], f"Pinned raw input changed: {source}")
        destination(STAGE, record["destination"])
    for group in config["rawGroups"]:
        path = (ROOT / group["source"]).resolve()
        require(path.is_relative_to(ROOT) and path.is_dir(), f"Missing raw group: {path}")
        destination(STAGE, group["destination"])
    for pair in config["cadPairs"].values():
        for phase in ("before", "after"):
            local(pair[phase])
    for name in config["appPairs"]:
        require((before_app_path.parent / (name + ".png")).is_file() and
                (after_app_path.parent / (name + ".png")).is_file(), f"Missing paired app frame: {name}")
    summary = config["summary"]
    require(isinstance(summary, str) and summary.strip(), "Root-authored review summary is unset")
    STAGE.mkdir()
    copies = []
    for source in sorted(before.rglob("*")):
        if source.is_file():
            retain(source, STAGE / "before" / source.relative_to(before), copies)
    # Freeze original audit artifacts as raw data; only the current audit prefix is authored later.
    for source in sorted(AUDIT.iterdir()):
        if source.is_file():
            retain(source, STAGE / "before/original-audit" / source.name, copies)
    for child in ("sources", "review", "app-review"):
        for source in sorted((AUDIT / child).iterdir()):
            if source.is_file():
                retain(source, STAGE / "before/original-audit" / child / source.name, copies)
    for key, name in NAMES.items():
        retain(PACKAGE / name, STAGE / "candidate" / name, copies)
    for group in config["rawGroups"]:
        source_dir = (ROOT / group["source"]).resolve()
        require(source_dir.is_relative_to(ROOT) and source_dir.is_dir(), f"Missing raw group: {source_dir}")
        for source in sorted(source_dir.iterdir()):
            if source.is_file() and source.suffix in group["suffixes"]:
                retain(source, destination(STAGE, group["destination"]) / source.name, copies)
    for record in config["rawFiles"]:
        retain(local(record["source"]), destination(STAGE, record["destination"]), copies)
    retain(baseline, STAGE / "proof/all-hangboards-baseline.json", copies)
    retain(before_installed, STAGE / "proof/before-installed-app-provenance.json", copies)
    retain(cleanup_devices, STAGE / "proof/final-devices-after-cleanup.json", copies)
    retain(native_path, STAGE / "proof/independent/final-native-measurements.json", copies)
    retain(continuity_path, STAGE / "proof/independent/final-continuity-measurements.json", copies)
    for path in disposition_paths:
        retain(path, STAGE / "proof/independent" / path.name, copies)
    for index, rule in enumerate(assertions):
        retain(local(rule["source"]), STAGE / "proof/reports" / (f"{index:02d}-{rule['role']}.json"), copies)
    retain(config_path, STAGE / "proof/assembly-config.json", copies)
    retain(Path(__file__), STAGE / "proof/prepare_simulator_packet.py", copies)
    for app_path, phase in ((before_app_path, "before"), (after_app_path, "after")):
        for source in sorted(app_path.parent.iterdir()):
            if source.is_file():
                retain(source, STAGE / "app" / phase / source.name, copies)
    placements = []
    rows = []
    for view in ("front", "side", "top"):
        pair = config["cadPairs"][view]
        retained = []
        for phase in ("before", "after"):
            dest = STAGE / "previews" / (phase + "-" + view + ".png")
            retain(local(pair[phase]), dest, copies)
            retained.append(dest)
        rows.append((view, *retained))
    compose(rows, STAGE / "front-side-top-comparison.png", "Simulator 3-D — native before / candidate", placements)
    app_rows = [(name, STAGE / "app/before" / (name + ".png"), STAGE / "app/after" / (name + ".png"))
                for name in config["appPairs"]]
    require(app_rows, "No app comparisons selected")
    compose(app_rows, STAGE / "app-before-after.png", "Simulator 3-D — fresh actual app before / candidate", placements, app=True)
    runtime = {"schemaVersion": 1, "owner": ROOT.name, "reviewNumber": 8, "package": SLUG,
               "status": "technical proofs retained; revised human acceptance pending", **identity,
               "revisionBaseCommit": config["revisionBaseCommit"], "originalFeedback": "Jagged",
               "reports": reports, "app": {"before": before_app, "after": after_app},
               "displayThicknessEstimateMM": thickness, "priorDisplayThicknessEstimateMM": 94.0,
               "differenceFromPriorDisplayEstimateMM": difference,
               "maximumResidualRoofNormalAngleDegrees": normal_angle,
               "measurements": measurements,
               "publishedChecks": {"faceEnvelopeMM": [711, 222], "holdDepthChecks": 27},
               "limits": config["limits"], "noFreshRunByAssemblyScript": True}
    runtime["cleanupLogProvenance"] = config["cleanupLogProvenance"]
    save(STAGE / "runtime-validation.json", runtime)
    save(STAGE / "raw-retention.json", {"owner": ROOT.name, "byteIdenticalCopies": copies})
    save(STAGE / "composition-provenance.json", {"method": "Complete rectangles; uniform aspect-fit and letterboxing only. No crop, registration, tracing, pixel measurements or content edits.", "placements": placements})
    text = ("# Metolius Simulator 3-D — revised review #8\n\n" + summary + "\n\n"
            "![Native before and candidate: front, side, top](front-side-top-comparison.png)\n\n"
            "![Fresh actual app before and candidate](app-before-after.png)\n\n"
            "The original **Jagged** feedback and exact prior source/model/descriptor bytes are preserved in `before/`. "
            "Fresh captures cover five representative selected IDs and three real drag orbits, not every contact visually. "
            "Native continuity measurements do not certify manufacturer accuracy or final app appearance.\n\n"
            + thickness_wording + " " + continuity_wording + " "
            "Loft widths, guards and control poles remain display estimates. "
            "The exact thickness finding and its final disposition remain visible; the standard 0.28 mm tessellation deflection is unchanged.\n\n"
            + config["cleanupLogProvenance"] + "\n\n"
            "[Exact technical proofs](runtime-validation.json) · [Raw copy hashes](raw-retention.json). "
            "Human acceptance is pending. Reviews #1–7 and #9 onward remain unchanged.\n")
    (STAGE / "review.md").write_text(text)
    (STAGE / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Simulator 3-D — review #8</title><style>body{font:17px/1.55 system-ui;max-width:1500px;margin:2rem auto;padding:0 1rem}img{width:100%;height:auto}code{overflow-wrap:anywhere}</style><h1>Simulator 3-D — revised review #8</h1><p>' + html.escape(summary) + '</p><p>Candidate awaits human acceptance after the original “Jagged” feedback.</p><img src="front-side-top-comparison.png" alt="Full native front, side and top: before left, candidate right"><img src="app-before-after.png" alt="Complete fresh app frames: before left, candidate right"><p>' + html.escape(thickness_wording + " " + continuity_wording) + '</p><p>App images are representative, not an all-contact sweep. All eight before and eight after frames and AX records are retained.</p><p><a href="review.md">Review details</a> · <a href="runtime-validation.json">Technical proof</a> · <a href="raw-retention.json">Raw hashes</a> · <a href="before/original-audit/sources/product-01.jpg">Manufacturer photograph</a> · <a href="before/original-audit/sources/product-03.jpg">Manufacturer numbered diagram</a></p></html>\n')
    # Stage exact, guarded proposals. Queue and lock lexical edits touch only their Simulator objects.
    human = copy.deepcopy(original_human)
    for key in ("answer", "acceptedScope", "revisionCommit"):
        human.pop(key, None)
    human.update(identity, status="awaiting revised review #8; not accepted", currentRevision="jagged-review/index.html",
                 revisionBaseCommit=config["revisionBaseCommit"], appReview="jagged-review/app/after/validation.json",
                 runtimeValidation="jagged-review/runtime-validation.json", feedback=["Jagged"],
                 question="Does this look smoother now?",
                 reviewScope="Shown complete native before/after front, side and top views and fresh actual-app view; estimated transitions, rounding and thickness, with representative selected contacts and orbit coverage.",
                 approvalLimit="Any later human acceptance applies to this displayed candidate and representative selection coverage. It does not certify manufacturer-exact estimated geometry, global roof G1/C1 continuity or a visual sweep of all contacts.",
                 shownImages={"jagged-review/" + name: sha(STAGE / name) for name in
                              ("front-side-top-comparison.png", "app-before-after.png")},
                 history=original_human.get("history", []) + [{"displayedRevision": original_human,
                           "feedback": "Jagged", "result": "Superseded candidate offered; no acceptance recorded."}])
    row_index = next(i for i, row in enumerate(current_queue["boards"]) if row["number"] == 8)
    row = copy.deepcopy(current_queue["boards"][row_index])
    row.update(sourceSHA256=identity["sourceSHA256"], humanReview="awaiting revised review #8; not accepted",
               reviewPage=SLUG + "/jagged-review/index.html", latestRevision=SLUG + "/jagged-review/review.md",
               appReview=SLUG + "/jagged-review/app/after/validation.json", appReviewPage=SLUG + "/jagged-review/index.html",
               runtimeRevision=SLUG + "/jagged-review/runtime-validation.json", reviewFeedback=["Jagged"],
               comparisons=[SLUG + "/jagged-review/" + name for name in
                            ("front-side-top-comparison.png", "app-before-after.png")])
    row["presentations"]["primary"].update(modelSHA256=identity["modelSHA256"], descriptorSHA256=identity["descriptorSHA256"])
    lock_data = load(LOCK)
    entry = copy.deepcopy(lock_data["migratedPackages"][SLUG])
    require(entry["sourceSHA256"] == identity["sourceSHA256"] and entry["assetSHA256"] == identity["modelSHA256"]
            and entry["descriptorSHA256"] == identity["descriptorSHA256"], "Root delivery integration is incomplete")
    prefix = str(TARGET.relative_to(ROOT))
    entry.update(provenance=prefix + "/review.md", comparison=prefix + "/front-side-top-comparison.png",
                 nativeAppValidation=prefix + "/app/after/validation.json", individualReview=prefix + "/index.html",
                 runtimeValidation=prefix + "/runtime-validation.json", geometryAcceptance="pending revised human review #8",
                 geometryAcceptanceRecord=str((AUDIT / "human-review.json").relative_to(ROOT)))
    notice = ("# Metolius Simulator 3-D — current native revision\n\n" + summary + "\n\n"
              "The correction responding to **Jagged** is shown in [jagged-review/review.md](jagged-review/review.md). "
              "Current source/model/descriptor identities and technical evidence are pinned in "
              "[runtime-validation.json](jagged-review/runtime-validation.json). Human acceptance remains pending. "
              + thickness_wording + " " + continuity_wording + "\n\n"
              "The original audit below is historical. Its exact bytes and original raw proofs are retained in "
              "[before/](jagged-review/before/); original reports continue to describe that earlier revision.\n\n---\n\n")
    updates = {str((AUDIT / "source-audit.md").relative_to(ROOT)): notice + read_exact(before / "source-audit.md"),
               str((AUDIT / "human-review.json").relative_to(ROOT)): json.dumps(human, indent=2) + "\n",
               str(QUEUE.relative_to(ROOT)): replace_json_value(read_exact(QUEUE), ("boards", row_index), row),
               str(LOCK.relative_to(ROOT)): replace_json_value(read_exact(LOCK), ("migratedPackages", SLUG), entry)}
    save(PREP / "planned-record-updates.json", {"inputSHA256": {rel: sha(ROOT / rel) for rel in updates},
                                                "updates": updates})
    save(STAGE / "provenance.json", {"owner": ROOT.name, "package": SLUG, "reviewNumber": 8, **identity,
         "priorHashes": PRIOR, "originalFeedback": "Jagged", "humanAcceptance": "pending",
         "assemblyProgramSHA256": sha(__file__), "createdAtUTC": datetime.now(timezone.utc).isoformat()})
    save(STAGE / "retained-files.json", {"files": {str(p.relative_to(STAGE)): {"sha256": sha(p), "bytes": p.stat().st_size}
                                               for p in sorted(STAGE.rglob("*")) if p.is_file()}})
    print(json.dumps({"stage": str(STAGE.relative_to(ROOT)), "rawCopies": len(copies),
                      "trackedMutation": False, "humanAcceptance": "pending"}))


def verify(base, installed=False):
    identity = {key: load(base / "provenance.json")[key] for key in NAMES}
    package_scope(identity, base / "proof/all-hangboards-baseline.json")
    for rel, item in load(base / "retained-files.json")["files"].items():
        require(sha(base / rel) == item["sha256"], f"Packet hash changed: {rel}")
    for record in load(base / "raw-retention.json")["byteIdenticalCopies"]:
        require(sha(base / record["retained"]) == record["sha256"], f"Raw bytes changed: {record}")
    for key, name in NAMES.items():
        require(sha(base / "before" / name) == PRIOR[key], f"Prior source bytes changed: {name}")
    if installed:
        expected = load(PREP / "planned-record-updates.json")["updates"]
        require(all(read_exact(ROOT / rel) == text for rel, text in expected.items()), "Applied review records differ")
    print(json.dumps({"packet": str(base.relative_to(ROOT)), "passed": True, "humanAcceptance": "pending"}))


def apply():
    verify(STAGE)
    proposals = load(PREP / "planned-record-updates.json")
    allowed = {str((AUDIT / "source-audit.md").relative_to(ROOT)),
               str((AUDIT / "human-review.json").relative_to(ROOT)),
               str(QUEUE.relative_to(ROOT)), str(LOCK.relative_to(ROOT))}
    require(set(proposals["updates"]) == set(proposals["inputSHA256"]) == allowed,
            "Record mutation escapes the four approved files")
    for rel, value in proposals["inputSHA256"].items():
        require(sha(ROOT / rel) == value, f"Review record changed since build; rebuild proposals: {rel}")
    queue_index = next(i for i, row in enumerate(load(QUEUE)["boards"]) if row["number"] == 8)
    only_value_changed(read_exact(QUEUE), proposals["updates"][str(QUEUE.relative_to(ROOT))], ("boards", queue_index))
    only_value_changed(read_exact(LOCK), proposals["updates"][str(LOCK.relative_to(ROOT))], ("migratedPackages", SLUG))
    # Preflight every merge collision before writing; frozen before files are never replaced.
    files = [p for p in sorted(STAGE.rglob("*")) if p.is_file()]
    for source in files:
        target = TARGET / source.relative_to(STAGE)
        require(not target.exists() or sha(target) == sha(source), f"Existing packet differs: {target}")
    for source in files:
        target = TARGET / source.relative_to(STAGE)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for rel, text in proposals["updates"].items():
        target = ROOT / rel
        temporary = target.with_name(target.name + ".placid-badger-review-tmp")
        temporary.write_text(text)
        temporary.replace(target)
    verify(TARGET, installed=True)


def self_test():
    # Meaningful scope regression: arbitrary field order, arrays, braces inside strings, and CRLF.
    old = '{\r\n  "boards": [{"number": 7, "note":"brace } ["}, {"number":8}, {"number":9}],\r\n  "other": {"k":true}\r\n}\r\n'
    changed = replace_json_value(old, ("boards", 1), {"number": 8, "status": "pending"})
    old_spans, new_spans = json_spans(old), json_spans(changed)
    for path in (("boards", 0), ("boards", 2), ("other",)):
        require(old[slice(*old_spans[path])] == changed[slice(*new_spans[path])], "Unrelated raw JSON changed")
    only_value_changed(old, changed, ("boards", 1))
    try:
        only_value_changed(old, changed.replace('"k":true', '"k":false'), ("boards", 1))
    except ValueError:
        pass
    else:
        raise AssertionError("An unrelated record mutation escaped the scope guard")
    require(json.loads(changed)["boards"][1]["status"] == "pending", "Target JSON did not change")
    require(pointer({"a/b": {"~c": [0, 2]}}, "/a~1b/~0c/1") == 2, "JSON pointer escaping failed")
    with tempfile.TemporaryDirectory(prefix="placid-badger-packet-test-", dir=PREP) as temp:
        q = Path(temp) / "queue.json"
        q.write_bytes(old.encode("utf-8"))
        require(read_exact(q) == old, "Exact JSON read normalized unrelated CRLF bytes")
        p = Path(temp) / "proof.json"
        save(p, {"pass": True})
        digest = sha(p)
        p.write_text('{"pass": false}\n')
        require(sha(p) != digest, "Changed raw proof was not detected")
    print(json.dumps({"selfTest": "passed", "trackedMutation": False, "externalResources": []}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "apply", "verify", "self-test"))
    parser.add_argument("--config", type=Path, default=PREP / "packet-config.json")
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    if args.action == "build":
        build(args.config.resolve())
    elif args.action == "apply":
        apply()
    elif args.action == "verify":
        verify(TARGET if args.installed else STAGE, installed=args.installed)
    else:
        self_test()
