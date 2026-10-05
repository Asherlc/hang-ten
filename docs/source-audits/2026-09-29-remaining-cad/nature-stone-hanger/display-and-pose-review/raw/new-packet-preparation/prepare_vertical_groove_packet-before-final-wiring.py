#!/usr/bin/env python3
"""Deferred scratch assembly for the corrected vertical cord seats, review #9.

No native tools, application resources, tracked edits, or apply command.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

PREP = Path(__file__).resolve().parent
ROOT = PREP.parents[4]
SCRATCH = PREP.parent
AUDIT = ROOT / "docs/source-audits/2026-09-29-remaining-cad/nature-stone-hanger"
PACKAGE = ROOT / "Hangboards/nature-stone-hanger"
STAGE = PREP / "staged-packet"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Tools/HangboardPackages/src"))
from hangboard_packages import cad_source

REQUIRED_ROLES = {"source-facts", "metadata-preservation", "native-geometry",
                  "native-contacts", "exports", "pose-author", "pose-check", "pose-bearing",
                  "route-certificates", "support-reaction", "native-visual",
                  "author-cleanup", "installed-app", "captures", "app-visual",
                  "python-tests", "package-validation", "staging-parity",
                  "ios-tests", "ios-cleanup"}
FRESH_SOURCE_ROLES = {"metadata-preservation", "native-geometry", "native-contacts",
                      "exports", "pose-author", "pose-check", "route-certificates",
                      "support-reaction", "native-visual", "pose-bearing"}
INTERMEDIATE_SIDECARS = {"9520befe472f49778c32fd1747e25114fab5d9b8030b13f13359baf3dc874658",
                        "32c9cd6a1b5ef45796615392efb4382f1d557e2622f7d2aec21a4ec1153c15d3",
                        "7c24835c38c36ad16805c605970e939f02fa40007ee12b219a4d9da1860746fb"}
CONTACTS = {"edge-front-15mm-incut", "edge-front-15mm-flat",
            "edge-front-20mm-wood-flat", "edge-front-20mm-granite",
            "edge-reverse-10mm-incut", "edge-reverse-10mm-flat",
            "edge-reverse-06mm-flat", "edge-reverse-06mm-incut"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def source_path(value):
    require(isinstance(value, str) and value, "missing input path")
    path = Path(value)
    path = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    require(path.is_relative_to(ROOT), f"input outside this workspace: {value}")
    require(path.is_file() and not Path(value).is_symlink(), f"missing regular input: {value}")
    return path


def pointer(value, path):
    for part in path.strip("/").split("/") if path else []:
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def assertions(document, rules, label):
    require(rules, f"no schema assertions for {label}")
    for rule in rules:
        value = pointer(document, rule["pointer"])
        if "equals" in rule:
            require(value == rule["equals"], f"{label}: {rule['pointer']} differs")
        if "length" in rule:
            require(len(value) == rule["length"], f"{label}: {rule['pointer']} count differs")
        if "minimum" in rule:
            require(value >= rule["minimum"], f"{label}: {rule['pointer']} below minimum")
        if "maximum" in rule:
            require(value <= rule["maximum"], f"{label}: {rule['pointer']} above maximum")
        if "absoluteMaximum" in rule:
            require(abs(value) <= rule["absoluteMaximum"],
                    f"{label}: {rule['pointer']} absolute value above maximum")
        if "setEquals" in rule:
            require(set(value) == set(rule["setEquals"]), f"{label}: inventory differs")


def linked_hashes(document, report):
    """Check explicit file/hash pairs and published hash maps; no historical bypass."""
    def resolve(name):
        candidate = Path(name)
        options = [candidate] if candidate.is_absolute() else [ROOT / candidate, report.parent / candidate]
        existing = [p.resolve() for p in options if p.is_file()]
        require(existing, f"missing linked input {name} in {report.name}")
        path = existing[0]
        require(path.is_relative_to(ROOT), f"linked input outside workspace: {name}")
        return path

    def visit(value):
        if isinstance(value, dict):
            linked_name = value.get("path", value.get("image", value.get("report")))
            if isinstance(linked_name, str) and isinstance(value.get("sha256"), str):
                require(sha(resolve(linked_name)) == value["sha256"],
                        f"linked input hash differs: {linked_name}")
            for key, child in value.items():
                if key in {"fileSHA256", "linkedReports", "files", "evidence"} and isinstance(child, dict):
                    for name, digest in child.items():
                        require(sha(resolve(name)) == digest, f"fileSHA256 differs: {name}")
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(document)


def linked_hash_groups(document, groups, label):
    """Verify schema-specific image/report maps against their declared folder."""
    for group in groups:
        values = pointer(document, group["pointer"])
        require(isinstance(values, dict) and values, f"empty linked hash map: {label}")
        for name, digest in values.items():
            relative = Path(name)
            require(not relative.is_absolute() and ".." not in relative.parts,
                    f"unsafe linked hash name: {label}")
            require(isinstance(digest, str) and len(digest) == 64,
                    f"invalid linked hash value: {label}")
            path = source_path(str(Path(group["pathBase"]) / relative))
            require(sha(path) == digest, f"linked hash map differs: {label}: {name}")


def board(path):
    return json.loads(cad_source.render_board(cad_source.load_board(path)))


def metadata_check(config):
    """Preserve the complete manifest and facts while requiring changed geometry."""
    identity, before = config["identity"], config["before"]
    require(config["nativeBodyGeometryChanged"] is True,
            "corrected revision must declare the native geometry change")
    names = {"sourceSHA256": "source", "modelSHA256": "model",
             "descriptorSHA256": "descriptor", "sidecarSHA256": "sidecar"}
    current = {"sourceSHA256": PACKAGE / "nature-stone-hanger.FCStd",
               "modelSHA256": PACKAGE / "assets/primary.usdz",
               "descriptorSHA256": PACKAGE / "assets/primary.model.json",
               "sidecarSHA256": PACKAGE / "suspension.json"}
    old = {}
    for key, name in names.items():
        old[key] = source_path(before[name])
        require(sha(old[key]) == before["identity"][key], f"prior {name} differs")
        require(identity.get(key) and sha(current[key]) == identity[key],
                f"new {name} identity is unset or differs")
        require(identity[key] != before["identity"][key],
                f"superseded {name} bytes cannot be the corrected revision")
    require(not (PACKAGE / "board.json").exists(), "on-disk CAD board.json is forbidden")
    for descriptor, model in ((old["descriptorSHA256"], old["modelSHA256"]),
                              (current["descriptorSHA256"], current["modelSHA256"])):
        require(load(descriptor)["modelSHA256"] == sha(model), "descriptor model binding differs")
    payloads, members = [], []
    for path in (old["sourceSHA256"], current["sourceSHA256"]):
        with zipfile.ZipFile(path) as archive:
            tree = ET.fromstring(archive.read("Document.xml"))
            properties = tree.findall("./Properties/Property[@name='HangTenBoardManifest']")
            require(len(properties) == 1 and len(properties[0]) == 1,
                    "manifest property is not unique")
            payloads.append(properties[0][0].get("value"))
            members.append({n: hashlib.sha256(archive.read(n)).hexdigest()
                            for n in archive.namelist() if n.lower().endswith(".brp")})
    require(payloads[0] == payloads[1], "embedded manifest bytes changed")
    changed = sorted(n for n in set(members[0]) | set(members[1])
                     if members[0].get(n) != members[1].get(n))
    require(changed, "native geometry archive did not change")
    old_board, current_board = board(old["sourceSHA256"]), board(current["sourceSHA256"])
    require(old_board == current_board, "facts, finish, positions or other manifest metadata changed")
    require({c["id"] for c in current_board["contacts"]} == CONTACTS,
            "eight contact IDs differ")
    positions = current_board["positions"]
    require(len(positions) == 8 and {p["id"] for p in positions} == CONTACTS and
            all(p["contactIDs"] == [p["id"]] and p["presentationID"] == "primary"
                for p in positions), "eight singleton positions differ")
    finish = current_board["presentations"][0]["media"]["display"]
    require(finish["surfaceFinish"] == "wood" and
            finish["graniteNodeIDs"] == ["edge_front_20mm_granite_mesh_001"],
            "wood/granite metadata differs")
    return {"status": "pass", "nativeBodyGeometryChanged": True,
            "nativeGeometryMembersChanged": changed,
            "manifestBytesIdentical": True, "contactFactsUnchanged": True,
            "positionsUnchanged": True, "finishMetadataUnchanged": True,
            "contacts": 8, "positions": 8, "allFourPackageIdentitiesChanged": True,
            "scope": "Archive/manifest check; actual vertical-cut shape is a separate fresh native gate."}


def source_evidence_check(config):
    entry = config["sourceEvidenceInventory"]
    report = source_path(entry["path"])
    require(sha(report) == entry["sha256"], "retained source inventory differs")
    for name, digest in load(report).items():
        path = (report.parent / name).resolve()
        require(path.is_relative_to(ROOT) and path.is_file() and sha(path) == digest,
                f"retained whole source differs: {name}")


def final_check(config):
    require(config["finalReady"] is True, "root completion signal is still pending")
    source_evidence_check(config)
    result = metadata_check(config)
    identity = config["identity"]
    sidecar = PACKAGE / "suspension.json"
    require(identity.get("sidecarSHA256") and sha(sidecar) == identity["sidecarSHA256"],
            "final sidecar hash is unset or differs")
    require(identity["sidecarSHA256"] not in INTERMEDIATE_SIDECARS,
            "superseded short-cord/notch-bypass/prior-geometry sidecar cannot be promoted")
    setup = load(sidecar)
    require(setup["modelSHA256"] == identity["modelSHA256"], "sidecar model binding differs")
    require(set(setup["suspension"]["canonicalPoses"]) == CONTACTS, "final pose inventory differs")
    generated = cad_source.generate_board_json(PACKAGE / "nature-stone-hanger.FCStd")
    report_map = {}
    require(REQUIRED_ROLES <= {r["role"] for r in config["reports"]}, "required proof role omitted")
    for entry in config["reports"]:
        path = source_path(entry["path"])
        require(entry.get("sha256") and sha(path) == entry["sha256"], f"unfrozen report: {entry['role']}")
        document = load(path)
        if entry["role"] in FRESH_SOURCE_ROLES:
            require("sourceSHA256" in entry.get("identity", {}).values(),
                    f"fresh source binding omitted: {entry['role']}")
        assertions(document, entry["assertions"], entry["role"])
        for key, expected in entry.get("identity", {}).items():
            require(pointer(document, key) == identity[expected], f"{entry['role']} identity differs: {key}")
        if entry.get("linkedHashes", False):
            linked_hashes(document, path)
        linked_hash_groups(document, entry.get("linkedHashGroups", []), entry["role"])
        report_map[entry["role"]] = {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
    retained = {}
    for entry in config.get("retainedEvidence", []):
        path = source_path(entry["path"])
        require(sha(path) == entry["sha256"], f"retained evidence differs: {entry['label']}")
        if entry.get("assertions"):
            assertions(load(path), entry["assertions"], entry["label"])
        if entry.get("linkedHashes"):
            linked_hashes(load(path), path)
        linked_hash_groups(load(path), entry.get("linkedHashGroups", []), entry["label"])
        retained[entry["label"]] = {"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                                    "scope": entry["scope"]}
    feedback = load(source_path(config["feedbackRecord"]["path"]))
    require(sha(source_path(config["feedbackRecord"]["path"])) == config["feedbackRecord"]["sha256"],
            "raw feedback record changed; retain historical bytes before refreshing")
    require(config["humanFeedback"] == feedback["feedback"] and len(config["humanFeedback"]) == 6,
            "all six user comments must remain exact")
    require(config["routingClarification"]["status"] == "answered" and
            config["routingClarification"]["answer"] == "Enters side holes; notches guide it" and
            feedback["routingClarification"]["answer"] == config["routingClarification"]["answer"],
            "answered side-hole/notch topology was lost")
    installed = load(source_path(config["app"]["installedProvenance"]))
    require(installed["nativeSourceSHA256"] == identity["sourceSHA256"] and
            installed["sidecarSHA256"] == identity["sidecarSHA256"], "installed native metadata differs")
    require(installed["binaryBytesMatch"] and installed["generatedManifestBytesMatchSource"],
            "installed binary/manifest comparison failed")
    require(installed["generatedManifestSHA256"] == hashlib.sha256(generated).hexdigest(),
            "installed generated manifest differs")
    require(set(installed["contactIDs"]) == CONTACTS, "installed contact inventory differs")
    capture = load(source_path(config["app"]["validation"]))
    require(capture["installedProvenanceSHA256"] == sha(source_path(config["app"]["installedProvenance"])),
            "capture installed-binary provenance differs")
    require(capture["builtBinarySHA256"] == installed["builtBinarySHA256"], "capture binary identity differs")
    checks = pointer(capture, config["app"]["checksPointer"])
    key = config["app"]["contactIDField"]
    require(key and CONTACTS <= {c.get(key) for c in checks}, "fresh captures omit contact selections")
    geometry = config["geometryComparisons"]
    require({"front", "side", "top"} <= {e["view"] for e in geometry} <= {"front", "side", "top", "oblique"} and
            len(geometry) == len({e["view"] for e in geometry}),
            "fresh whole front/side/top comparisons are required")
    for entry in geometry:
        require(entry.get("sha256") and sha(source_path(entry["path"])) == entry["sha256"],
                f"unfrozen whole geometry comparison: {entry['view']}")
    require(config["summary"] and config["limits"], "root visual summary or limits unset")
    return {**result, "identity": identity, "reports": report_map, "retainedEvidence": retained,
            "geometryComparisons": geometry,
            "generatedManifestSHA256": hashlib.sha256(generated).hexdigest(),
            "humanAcceptance": "pending", "freshContactSelectionCount": 8,
            "snapshotAllowedByRoot": True, "canonicalMutations": False}


def readiness(config):
    pending = []
    if not config["finalReady"]:
        pending.append("root final completion signal")
    for key in ("sourceSHA256", "modelSHA256", "descriptorSHA256", "sidecarSHA256"):
        if not config["identity"].get(key):
            pending.append(key)
    for entry in config["reports"]:
        if not entry.get("path") or not (ROOT / entry["path"]).is_file():
            pending.append(entry["role"] + " report")
        if not entry.get("sha256"):
            pending.append(entry["role"] + " stable hash")
        if not entry.get("assertions"):
            pending.append(entry["role"] + " actual-schema assertions")
    for entry in config["geometryComparisons"]:
        if not entry.get("path") or not entry.get("sha256"):
            pending.append("whole geometry " + entry["view"] + " comparison")
    for pair in config["appPairs"]:
        if not pair.get("before") or not pair.get("after"):
            pending.append(pair["output"] + " actual whole app inputs")
    if not config["app"].get("installedProvenance") or not config["app"].get("validation"):
        pending.append("fresh app proof paths")
    if not config["app"].get("contactIDField"):
        pending.append("actual capture contact-ID field")
    if not config["summary"]:
        pending.append("root final visual summary")
    source_evidence_check(config)
    metadata = {"status": "pending-new-geometry-hashes", "nativeBodyGeometryChanged": True}
    if all(config["identity"].get(k) for k in
           ("sourceSHA256", "modelSHA256", "descriptorSHA256", "sidecarSHA256")):
        metadata = metadata_check(config)
    if not pending:
        final_check(config)
    return {"status": "pending" if pending else "ready", "pending": pending,
            "metadata": metadata, "snapshotCreated": False, "trackedMutation": False}


def raw_inputs(config):
    found = {}
    def add(path, target):
        require(not path.is_symlink() and path.is_file(), f"nonregular raw input: {path}")
        require(path.resolve().is_relative_to(ROOT), "raw input leaves workspace")
        name = Path(target)
        require(not name.is_absolute() and ".." not in name.parts, "unsafe raw destination")
        if str(name) in found:
            require(found[str(name)] == path, f"raw collision: {name}")
        found[str(name)] = path
    for entry in config["rawFiles"]:
        add(source_path(entry["path"]), entry["target"])
    for group in config["rawGroups"]:
        folder = (ROOT / group["path"]).resolve()
        require(folder.is_dir() and folder.is_relative_to(ROOT), f"missing raw group: {group['path']}")
        for path in sorted(folder.iterdir()):
            if path.is_file() and (path.suffix.lower() in group["suffixes"] or
                                   path.name in group.get("includeNames", [])):
                add(path, str(Path(group["target"]) / path.name))
    for entry in config["reports"]:
        path = source_path(entry["path"])
        add(path, "raw/" + str(path.relative_to(ROOT)))
    return found


def pair_image(before, after, labels, output):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    width, height, heading = 900, 900, 70
    canvas = Image.new("RGB", (width * 2, height + heading), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    sizes = []
    for index, path in enumerate((before, after)):
        with Image.open(path) as original:
            sizes.append(list(original.size))
            fitted = ImageOps.contain(original.convert("RGB"), (width, height))
            canvas.paste(fitted, (index * width + (width - fitted.width) // 2,
                                  heading + (height - fitted.height) // 2))
        draw.text((index * width + 20, 14), labels[index], fill="black", font=font)
    canvas.save(output)
    return {"beforeSHA256": sha(before), "afterSHA256": sha(after),
            "originalSizes": sizes, "sha256": sha(output),
            "method": "Whole-frame uniform aspect-fit with letterboxing; no crop or registration."}


def build(config, config_path):
    proof = final_check(config)
    require(config["appPairs"], "final shown-image pairs are unset")
    require(not STAGE.exists(), "scratch stage already exists; retain it before making a revision")
    inputs = raw_inputs(config)
    STAGE.mkdir()
    for target, source in inputs.items():
        output = STAGE / target
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
        require(sha(source) == sha(output), f"raw byte copy differs: {target}")
    shutil.copyfile(config_path, STAGE / "packet-config.json")
    shutil.copyfile(Path(__file__), STAGE / "prepare_vertical_groove_packet.py")
    write_json(STAGE / "runtime-validation.json", proof)
    human = {"reviewNumber": 9, "boardID": "nature.stone-hanger", "status": "pending",
             "question": config["humanQuestion"], "feedback": config["humanFeedback"],
             "routingClarification": config["routingClarification"],
             "identity": config["identity"], "reviewScope": config["reviewScope"],
             "approvalLimit": config["approvalLimit"],
             "globalRecordsUpdatedByThisBuilder": False}
    write_json(STAGE / "human-review-proposal.json", human)
    image_proofs, visual_lines = {}, []
    for pair in config["appPairs"]:
        output = STAGE / pair["output"]
        require(output.parent == STAGE and output.suffix == ".png", "unsafe comparison path")
        before, after = source_path(pair["before"]), source_path(pair["after"])
        image_proofs[pair["output"]] = pair_image(before, after, pair["labels"], output)
        visual_lines.append(f"![{pair['title']}]({pair['output']})")
    write_json(STAGE / "comparison-provenance.json", image_proofs)
    for entry in config["geometryComparisons"]:
        output = STAGE / ("native-" + entry["view"] + ".png")
        shutil.copyfile(source_path(entry["path"]), output)
        visual_lines.append(f"![Whole prior/corrected {entry['view']} geometry]({output.name})")
    review = ("# Nature Climbing Stone Hanger — vertical cord seats, review #9\n\n" + config["summary"] +
              "\n\nHuman acceptance is pending.\n\nOriginal user comments:\n\n" +
              "\n".join("- " + json.dumps(comment, ensure_ascii=False) for comment in config["humanFeedback"]) +
              "\n\nTopology answer: **" + config["routingClarification"]["answer"] + "**. "
              "The concealed connection remains unspecified.\n\n" + "\n\n".join(visual_lines) +
              "\n\nThe native body geometry now includes one vertical cord seat on each side, "
              "while all three transverse adjustment notches per side remain. The complete embedded "
              "manifest, all eight contact facts and positions, and wood/granite metadata are preserved. "
              "All four package identities are new and have fresh native, export, cord and runtime proof.\n\n" +
              "The prior body, mathematical and runtime checks remain historical and bound only to "
              "their former hashes. The full superseded packet is retained; its passes are not carried "
              "to the corrected shape. Prior app frames are exact historical captures, not a fresh old binary run.\n\n" +
              "\n".join("- " + text for text in config["limits"]) +
              "\n\nExact raw reports, commands, logs, accessibility records, images and cleanup evidence "
              "are retained under `raw/` and covered by `packet-hashes.json`. "
              "Root owns queue, delivery-lock, batch and acceptance updates.\n")
    (STAGE / "review.md").write_text(review)
    body = "<h1>Stone Hanger #9</h1><p>" + html.escape(config["summary"]) + "</p><p>Human acceptance pending.</p>"
    for pair in config["appPairs"]:
        body += "<h2>" + html.escape(pair["title"]) + "</h2><img src='" + html.escape(pair["output"]) + "'>"
    body += "<h2>Whole prior/corrected geometry</h2>"
    for entry in config["geometryComparisons"]:
        body += "<img src='native-" + html.escape(entry["view"]) + ".png'>"
    body += "<ul>"
    body += "".join("<li>" + html.escape(text) + "</li>" for text in config["limits"])
    body += "</ul><p><a href='review.md'>Review notes</a> · <a href='runtime-validation.json'>Proof index</a></p>"
    (STAGE / "index.html").write_text("<!doctype html><meta charset='utf-8'><style>body{font:16px system-ui;max-width:1300px;margin:24px auto;padding:16px}img{width:100%;height:auto}</style>" + body)
    write_json(STAGE / "raw-copy-manifest.json", {target: {"source": str(path.relative_to(ROOT)),
               "sha256": sha(path), "bytes": path.stat().st_size} for target, path in inputs.items()})
    require(final_check(config) == proof, "proof inputs changed during assembly")
    write_json(STAGE / "packet-hashes.json", {str(path.relative_to(STAGE)): sha(path)
               for path in sorted(STAGE.rglob("*")) if path.is_file()})
    print(json.dumps({"status": "built", "stage": str(STAGE.relative_to(ROOT)),
                      "rawFiles": len(inputs), "humanAcceptance": "pending", "trackedMutation": False}))


def verify(packet):
    manifest = load(packet / "packet-hashes.json")
    actual = {str(path.relative_to(packet)) for path in packet.rglob("*") if path.is_file()}
    require(actual == set(manifest) | {"packet-hashes.json"}, "packet inventory differs")
    for name, digest in manifest.items():
        require(sha(packet / name) == digest, f"packet bytes differ: {name}")
    for name, record in load(packet / "raw-copy-manifest.json").items():
        require(sha(packet / name) == record["sha256"] and
                (packet / name).stat().st_size == record["bytes"], "raw evidence differs")
    print(json.dumps({"status": "pass", "packetFiles": len(actual), "proof": "packet bytes only",
                      "trackedMutation": False, "liveReviewStateAsserted": False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("readiness", "build", "verify"))
    parser.add_argument("--config", type=Path, default=PREP / "packet-config.json")
    parser.add_argument("--packet", type=Path, default=STAGE)
    args = parser.parse_args()
    if args.command == "verify":
        verify(args.packet.resolve())
    else:
        config = load(args.config)
        require(config["owner"] == "placid-badger" and config["reviewNumber"] == 9, "wrong review owner")
        if args.command == "readiness":
            print(json.dumps(readiness(config), indent=2))
        else:
            build(config, args.config)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, IndexError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "trackedMutation": False}), file=sys.stderr)
        sys.exit(1)
