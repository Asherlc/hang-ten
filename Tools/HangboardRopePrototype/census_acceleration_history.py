#!/usr/bin/env python3
"""Read-only necessary count-eligibility screen; it does not propose physics states."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
assert repo.name == 'strong-owl-live-physics'
output = args.output.resolve()
assert output.is_relative_to(repo/'.context') and repo.name in output.parent.name
assert not output.exists() and not args.input.is_symlink()
source = json.loads(args.input.read_text())
assert source['completed'] and len(source['steps']) == 540
records = []
for step in source['steps']:
    trace = step['trace']
    corrections = trace['corrections']
    count = trace['correctionCount']
    assert count == len(corrections) and not trace['capped'] and trace['retries'] == 0
    eligible = []
    for index in range(2, count):
        block = corrections[index-2:index+1]
        if len({(item['rows'], item['active']) for item in block}) == 1:
            eligible.append(index)
    # Three map evaluations form depth-two history; a fresh ordinary QP must
    # check the accelerated state. No restoration/merit overhead is charged.
    saved = max(0, count-(eligible[0]+2)) if eligible else 0
    records.append({'step': step['step'], 'corrections': count,
                    'firstCountStableMapIndex': eligible[0] if eligible else None,
                    'optimisticallyRemovableCorrections': saved})
total = sum(item['corrections'] for item in records)
absolute = sum(max(0, item['corrections']-4) for item in records)
stable = sum(item['optimisticallyRemovableCorrections'] for item in records)
result = {'owner': repo.name, 'inputSHA256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
          'completedSteps': len(records), 'controlCorrections': total,
          'correctionDistribution': dict(sorted(Counter(item['corrections'] for item in records).items())),
          'ignoringAllSignaturesRemovableCorrections': absolute,
          'ignoringAllSignaturesRemovableFraction': absolute/total,
          'countStableRemovableCorrections': stable,
          'countStableRemovableFraction': stable/total,
          'steps': records, 'fullFeatureIdentityProven': False, 'candidateImplemented': False,
          'scope': 'Necessary counts-only ceiling for depth-two within-step acceleration with fresh verification; no wall-time bound, state proposal, or performance acceptance'}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({key: value for key, value in result.items() if key != 'steps'}, indent=2))
