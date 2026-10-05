"""Bind an authorized runtime arm to completed integrated build proofs; no app actions."""
from pathlib import Path
import argparse, hashlib, json, os, re, sys

D = Path(__file__).resolve().parent
N = D.parents[1]
WORKSPACE = N.parents[2]
OWNER = Path(os.environ.get('PASEO_WORKTREE_PATH', str(WORKSPACE))).name
assert OWNER == 'placid-badger-cad-second-half'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser()
parser.add_argument('mode', choices=['evo','pro','mini'])
parser.add_argument('proof_directory')
parser.add_argument('run_suffix', nargs='?', default='')
parser.add_argument('--confirmation-proof')
args=parser.parse_args()
mode=args.mode
assert not args.run_suffix or re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', args.run_suffix), 'Explicit run suffix must be a safe identifier'
run_label=mode+('-'+args.run_suffix if args.run_suffix else '')
proof_argument = Path(args.proof_directory)
confirmation=None
if args.confirmation_proof:
    confirmation_path=Path(args.confirmation_proof).resolve()
    assert confirmation_path.is_relative_to(N.resolve())
    confirmation=json.loads(confirmation_path.read_text())
    assert confirmation['passed'] and confirmation['confirmationHandledBeforeMeasurement'] and confirmation['cleanupPassed']
    confirmation=dict(path=str(confirmation_path),sha256=sha(confirmation_path),details=confirmation)
proof_directory = (N / proof_argument).resolve() if len(proof_argument.parts) == 1 else proof_argument.resolve()
assert proof_directory.is_dir() and proof_directory.is_relative_to(N.resolve()) and proof_directory != N.resolve(), 'Proof directory must exist inside this owned integration packet'
exit_proofs = {}
for action in ('build', 'install', 'container'):
    path = proof_directory / (action + '.exit.json')
    result = json.loads(path.read_text())
    assert result['exitStatus'] == result['processExitStatus'] == 0 and result['exception'] is None and result['childReaped'], (action, 'Successful final build/install proof required')
    exit_proofs[action] = dict(path=str(path), sha256=sha(path))
boards = {
    'evo': ('zlagboard.evo', 'Zlagboard.Evo'),
    'pro': ('zlagboard.pro', 'Zlagboard.Pro 2.0'),
    'mini': ('nature.stone-hanger-mini', 'Stone Hanger Mini'),
}
board_id, board_name = boards[mode]
if confirmation is not None:
    assert confirmation['details']['owner']==OWNER and confirmation['details']['boardID']==board_id
ownership_path = N / 'ios/ownership.json'
ownership = json.loads(ownership_path.read_text())
assert ownership['owner'] == OWNER
assert not (N / 'ios/cleanup-requested').exists()
source_path = proof_directory / 'source-reference.json'
parity_path = proof_directory / 'parity.json'
canonical_path = N / 'postmerge-canonical-preservation.json'
source = json.loads(source_path.read_text())
parity = json.loads(parity_path.read_text())
canonical = json.loads(canonical_path.read_text())
assert parity['allEqual'] and parity['sourceUnchanged']
assert parity['nativePackageCount'] == 66
assert parity['selectedCanonicalFileCount'] == source['selectedCanonicalFileCount'] == 81
assert canonical['allEqual'] and canonical['canonicalFileCount'] == 81
for x in source['files']:
    assert sha(WORKSPACE / x['path']) == x['sha256'], x['path']
for x in canonical['checks']:
    assert sha(WORKSPACE / x['path']) == x['contentSHA256'], x['path']
for x in parity['checks']:
    assert x['equal']
    for prefix in ('built', 'installed', 'source'):
        if prefix + 'Path' in x:
            assert sha(x[prefix + 'Path']) == x[prefix + 'SHA256']
binary = next((x for x in parity['checks'] if x['relativePath'] == 'HangTen.debug.dylib'), None)
if binary is None:
    binary = next(x for x in parity['checks'] if x['relativePath'] == 'HangTen')
installed_app = Path(ownership['installedApp'])
assert Path(binary['installedPath']).parent == installed_app
assert '/Devices/' + ownership['simulatorUUID'] + '/' in str(installed_app)
if confirmation is not None:
    details=confirmation['details']
    assert details['simulatorUUID']==ownership['simulatorUUID']
    assert details['binarySHA256']==binary['installedSHA256']
    assert details['sourceReferenceSHA256']==sha(source_path) and details['paritySHA256']==sha(parity_path)
    assert details['normalWorkoutConfirmed'] and details['physicalOpenCount']==1 and details['noRetries']

# Copy the authored plan records from the current library, preserving every field.
library_path = WORKSPACE / 'HangTen/Resources/PlanLibrary.json'
library = json.loads(library_path.read_text())
plan = next(x for x in library['plans'] if x['id'] == 'research.max-hangs')
block_ids = {x['blockID'] for x in plan['blocks']}
blocks = [x for x in library['blocks'] if x['id'] in block_ids]
assert len(blocks) == len(block_ids)
first = blocks[0]['steps'][0]
assert first['segments'][0]['duration'] == 10 and first['segments'][1]['duration'] == 180
routine_path = N / ('runtime-' + run_label + '-routine-reference.json')
routine = dict(planLibraryPath=str(library_path), planLibrarySHA256=sha(library_path),
               authoredRecords=blocks + [plan], sourceFiles={x['path']: x['sha256'] for x in source['files']
               if x['path'].startswith('HangTen/') and x['path'].endswith('.swift')},
               cadence=dict(hangSeconds=10, betweenSetRestSeconds=180, initialCountdownSeconds=3),
               qualification='Exact authored MaxHangs records. Mini uses current source two-hand tasks and the production two-board adaptation; no hand side, routine fields, or targets are changed.')
with routine_path.open('x') as f:
    json.dump(routine, f, indent=2); f.write('\n')
published_path=proof_directory/'published-source-binding.json'
published=json.loads(published_path.read_text())
assert published['allFrozenFilesMatchCurrentCommittedWorktree'] and published['trackedWorktreeClean']
release = dict(publishedSourceBindingPath=str(published_path), publishedSourceBindingSHA256=sha(published_path), publishedSourceCommit=published['publishedCommit'], runtimeAuthorized=True, exclusiveRuntimeOwnership=True, owner=OWNER,
               mode=mode, boardID=board_id, boardName=board_name, planID='research.max-hangs',
               simulatorUUID=ownership['simulatorUUID'], controllerPID=ownership['controllerPID'],
               ownershipPath=str(ownership_path), ownershipSHA256=sha(ownership_path),
               proofDirectory=str(proof_directory), successfulCommandProofs=exit_proofs,
               sourceCommit=source['commit'], sourceReferencePath=str(source_path), sourceReferenceSHA256=sha(source_path),
               parityPath=str(parity_path), paritySHA256=sha(parity_path), parityCheckCount=len(parity['checks']),
               canonicalPreservationPath=str(canonical_path), canonicalPreservationSHA256=sha(canonical_path),
               binaryRelativePath=binary['relativePath'], binarySHA256=binary['installedSHA256'],
               installedApp=str(installed_app), helperSHA256=sha(D / 'capture-auto-route.py'), scheduleSHA256=sha(D / 'schedule-auto-route.json'),
               planLibrarySHA256=sha(library_path), routineReferencePath=str(routine_path), routineReferenceSHA256=sha(routine_path),
               runID=OWNER + '-combined-' + run_label, runLabel=run_label, runSuffix=args.run_suffix,
               systemConfirmationSetup=confirmation, outputDirectory=str(N / ('runtime-' + run_label)),
               appArguments=['-workoutAudioCuesEnabled', 'NO'],
               launchReviewFlags={'HANGTEN_REVIEW_BOARD_ID': board_id, 'HANGTEN_REVIEW_PLAN_ID': 'research.max-hangs', 'HANGTEN_REVIEW_LANDSCAPE': '1'},
               miniSetupAuthorized=mode == 'mini')
release_path = N / ('runtime-' + run_label + '-release.json')
with release_path.open('x') as f:
    json.dump(release, f, indent=2); f.write('\n')
print(release_path)
