from pathlib import Path
import hashlib
import json

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-plastic-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
agent_id = '918cc0e7-961d-4672-9f95-b4f2918098b7'
archive = load(scratch / 'opus-archive-raw.json')['structuredContent']
status = load(scratch / 'opus-archived-status-raw.json')['structuredContent']
assert archive['success']
assert status['status'] == 'closed' and status['snapshot']['id'] == agent_id
assert status['snapshot']['archivedAt'] and status['snapshot']['labels']['owner'] == root.name
assert status['snapshot']['cwd'] == str(root)
cleanup = {'status': 'pass', 'owner': root.name, 'advisorAgentID': agent_id,
           'exactOwnedAdvisorArchived': True, 'archivedAt': status['snapshot']['archivedAt'],
           'verifiedLifecycle': status['status'], 'unrelatedAgentsChanged': False,
           'fileSHA256': {name: sha(scratch / name) for name in ('opus-archive-raw.json', 'opus-archived-status-raw.json')}}
save(scratch / 'opus-cleanup.json', cleanup)
identity = load(scratch / 'integrated-package.json')
activity = load(scratch / 'opus-final-activity.json')['structuredContent']
assert activity['agentId'] == agent_id
body = activity['content'].split('\n\n', 1)[1] + '\n'
assert (scratch / 'opus-final-review.md').read_text() == body
assert body.startswith('## Verdict: ready for human review')
assert 'waviness fix works in the actual app' in body
first = sha(scratch / 'opus-first-review.md')
assert first == 'e8f76f3f115d62060a8bca10d03cf1fdf4984ee5a0ebc7a656db94c9c19c46e5'
report = {'status': 'pass', 'owner': root.name, 'advisorAgentID': agent_id,
          **{k: identity[k] for k in ('sourceSHA256', 'modelSHA256', 'descriptorSHA256')},
          'blockingFindings': [], 'firstResponseSHA256': first,
          'finalResponseSHA256': sha(scratch / 'opus-final-review.md'),
          'verdict': 'Ready for human review; waviness resolved in actual app; no source/app-supported blocker.',
          'humanAcceptance': False, 'wholeAppFramesInspectedByAdvisor': 16,
          'remainingLimits': ['Small jagged edges on selected top-contact highlights',
                              'Inherited outer-jug faceting and absent pocket mouth bevels',
                              'Estimated side profile, thickness, front rolls, forward anchors and rear return',
                              'Mint is the app palette; semantic internal mesh is not exactly welded'],
          'fileSHA256': {str((scratch / name).relative_to(root)): sha(scratch / name)
                         for name in ('opus-final-activity.json', 'opus-final-review.md',
                                      'opus-fairing-app-prompt.md', 'opus-fairing-app-send.json',
                                      'opus-cleanup.json', 'app-visual-review.json')}}
save(scratch / 'opus-final-disposition.json', report)
print(json.dumps({'status': 'pass', 'advisorArchived': True,
                  'finalResponseSHA256': report['finalResponseSHA256'],
                  'dispositionSHA256': sha(scratch / 'opus-final-disposition.json'),
                  'cleanupSHA256': sha(scratch / 'opus-cleanup.json')}, indent=2))
