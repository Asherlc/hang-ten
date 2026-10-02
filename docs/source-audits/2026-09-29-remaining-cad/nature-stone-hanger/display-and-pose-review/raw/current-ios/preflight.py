from pathlib import Path
import json,hashlib
p=Path(__file__).resolve().parent
assert (p/'final-inputs.json').exists(), 'Root final hash-ready authorization has not arrived'
e=json.loads((p/'final-inputs.json').read_text());assert e['rootFinalHashReady'] is True
for path,digest in e['packageSHA256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
assert not (p/'simulator-ready').exists(), 'Do not reuse a simulator session'
print('Final source and sidecar match authorized frozen inputs')
