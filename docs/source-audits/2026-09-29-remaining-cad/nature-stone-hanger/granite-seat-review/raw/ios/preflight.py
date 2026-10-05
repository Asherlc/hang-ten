from pathlib import Path
import json
import hashlib
import os

root = Path(os.environ.get('PASEO_WORKTREE_PATH', Path.cwd())).resolve()
lane = Path(__file__).resolve().parent
assert lane.is_relative_to(root / '.context' / root.name)
assert (lane / 'final-inputs.json').exists(), 'Root final hash-ready authorization has not arrived'
inputs = json.loads((lane / 'final-inputs.json').read_text())
assert inputs['rootFinalHashReady'] is True
expected_paths = {
    'Hangboards/nature-stone-hanger/nature-stone-hanger.FCStd',
    'Hangboards/nature-stone-hanger/assets/primary.usdz',
    'Hangboards/nature-stone-hanger/assets/primary.model.json',
    'Hangboards/nature-stone-hanger/suspension.json',
}
assert set(inputs['packageSHA256']) == expected_paths
for rel, digest in inputs['packageSHA256'].items():
    assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest, rel
assert not (lane / 'simulator-ready').exists(), 'Do not reuse a simulator session'
print('All four canonical files match authorized frozen inputs')
