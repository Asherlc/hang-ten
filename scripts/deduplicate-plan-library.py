#!/usr/bin/env python3
"""Factor audited source prescriptions without changing expanded plan content."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re


def expanded_steps(library, plan):
    blocks = {block["id"]: block["steps"] for block in library["blocks"]}
    result = []
    for reference in plan["blocks"]:
        pattern = blocks[reference["blockID"]]
        count = reference.get("repeatCount", 1)
        ids = reference.get("stepIDs", [])
        titles = reference.get("stepTitles", [])
        if count < 1:
            raise ValueError("Repeat count must be positive")
        for overrides in (ids, titles):
            if overrides and len(overrides) not in (len(pattern), len(pattern) * count):
                raise ValueError("Overrides must describe one pattern or every expanded step")
        for repetition in range(count):
            for index, template in enumerate(pattern):
                step = deepcopy(template)
                if count > 1 and len(ids) == len(pattern) * count:
                    step["id"] = ids[repetition * len(pattern) + index]
                else:
                    stem = ids[index] if ids else step["id"]
                    step["id"] = f"{stem}-{repetition + 1}" if count > 1 else stem
                if titles:
                    step["title"] = titles[index if len(titles) == len(pattern) else repetition * len(pattern) + index]
                result.append(step)
    return result


def template_title(title):
    """Remove explicit source position labels during authoring, never in the UI.

    Original labels remain in stepTitles. Hold sizes, exercise counts, optional
    cues and every other qualifier remain part of the prescription signature.
    """
    components = []
    for component in title.split(" · "):
        phrases = []
        for phrase in component.split(", "):
            if re.fullmatch(r"(?:set|rep|round|effort|interval) [1-9][0-9]*(?: of [1-9][0-9]*)?", phrase, re.I):
                continue
            phrase = re.sub(r"^(minute|ladder) [1-9][0-9]*( rest)?$", r"\1\2", phrase, flags=re.I)
            phrase = re.sub(r"^(hang|repeater) [1-9][0-9]* of [1-9][0-9]*$", r"\1", phrase, flags=re.I)
            phrases.append(phrase)
        if phrases:
            components.append(", ".join(phrases))
    return " · ".join(components) or title.split(" ")[0]


def prescription(step):
    value = {key: value for key, value in step.items() if key != "id"}
    value["title"] = template_title(step["title"])
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deduplicated(library):
    result = deepcopy(library)
    result["blocks"] = []
    shared = {}
    for original_plan, plan in zip(library["plans"], result["plans"]):
        steps = expanded_steps(library, original_plan)
        signatures = [prescription(step) for step in steps]
        plan["blocks"] = []
        index = 0
        while index < len(steps):
            length, count = 1, 1
            # Keep the smallest repeated source unit. Longer rounds then reuse
            # the same references rather than copying their inner prescriptions.
            for candidate in range(1, (len(steps) - index) // 2 + 1):
                pattern = signatures[index:index + candidate]
                if pattern != signatures[index + candidate:index + 2 * candidate]:
                    continue
                length, count = candidate, 2
                while signatures[index + count * length:index + (count + 1) * length] == pattern:
                    count += 1
                break
            key = tuple(signatures[index:index + length])
            if key not in shared:
                pattern = deepcopy(steps[index:index + length])
                for step in pattern:
                    step["title"] = template_title(step["title"])
                block = {
                    "id": f"{plan['id']}.sequence-{index + 1}",
                    "title": pattern[0]["title"],
                    "steps": pattern,
                }
                shared[key] = block
                result["blocks"].append(block)
            block = shared[key]
            occurrences = steps[index:index + length * count]
            reference = {"blockID": block["id"]}
            if count > 1:
                reference["repeatCount"] = count
            ids = [step["id"] for step in occurrences]
            generated_ids = [f"{step['id']}-{repeat + 1}" if count > 1 else step["id"]
                             for repeat in range(count) for step in block["steps"]]
            if ids != generated_ids:
                reference["stepIDs"] = ids
            titles = [step["title"] for step in occurrences]
            if titles != [step["title"] for _ in range(count) for step in block["steps"]]:
                reference["stepTitles"] = titles
            plan["blocks"].append(reference)
            index += length * count
        if expanded_steps(result, plan) != steps:
            raise ValueError(f"Deduplication changed source steps for {plan['id']}")
    return result


def verify_equivalent(before, after):
    if before["metadata"] != after["metadata"]:
        raise ValueError("Library metadata changed")
    if len(before["plans"]) != len(after["plans"]):
        raise ValueError("Plan count changed")
    for original, current in zip(before["plans"], after["plans"]):
        if {k: v for k, v in original.items() if k != "blocks"} != {k: v for k, v in current.items() if k != "blocks"}:
            raise ValueError(f"Plan identity, metadata or board changed: {original['id']}")
        if expanded_steps(before, original) != expanded_steps(after, current):
            raise ValueError(f"Expanded prescription changed: {original['id']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[1] / "HangTen/Resources/PlanLibrary.json")
    parser.add_argument("--write", action="store_true", help="Write only after exact expanded equivalence passes")
    parser.add_argument("--check", action="store_true", help="Require the library to already be factored")
    parser.add_argument("--against", type=Path, help="Also verify against a previous canonical document")
    args = parser.parse_args()
    original_bytes = args.library.read_bytes()
    original = json.loads(original_bytes)
    result = deduplicated(original)
    verify_equivalent(original, result)
    if args.against:
        verify_equivalent(json.loads(args.against.read_text(encoding="utf-8")), result)
    if args.check and result != original:
        raise SystemExit("Canonical library still contains unfactored prescriptions")
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        args.library.write_text(encoded, encoding="utf-8")
    print(json.dumps({
        "plans": len(result["plans"]),
        "stepsBefore": sum(len(b["steps"]) for b in original["blocks"]),
        "stepsAfter": sum(len(b["steps"]) for b in result["blocks"]),
        "blocksAfter": len(result["blocks"]),
        "declaredRepeats": sum(r.get("repeatCount", 1) > 1 for p in result["plans"] for r in p["blocks"]),
        "bytesBefore": len(original_bytes),
        "bytesAfter": len(encoded.encode()),
        "expandedPrescriptionsUnchanged": True,
    }, indent=2))


if __name__ == "__main__":
    main()
