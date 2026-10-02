"""Stock triangle discovery followed by unchanged original rope kernels and solve."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import signal
import sys

sys.dont_write_bytecode = True
from run_native_contact_screen import OwnedCommands, REPO
from run_stock_chain_screen import CHECKPOINT_SHA, DESCRIPTOR_SHA, JSON_SHA, REVISION, digest
from contact_discovery.snapshot import capture_sources
from contact_discovery.certificate import reference_certificate


def coverage(reference, candidates):
    if len(reference['queries']) != len(candidates['queries']):
        raise ValueError('query count differs')
    return [(i, h['triangle']) for i, (q, c) in enumerate(zip(reference['queries'], candidates['queries']))
            for h in q['hits'] if h['triangle'] < 0 or h['triangle'] not in c['triangles']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    workspace = Path(os.environ.get('PASEO_WORKTREE_PATH', REPO)).resolve()
    owner = workspace.name
    if workspace != REPO or owner != 'strong-owl-live-physics':
        parser.error('this frozen diagnostic belongs only to strong-owl-live-physics')
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('label must contain only lowercase letters, digits and hyphens')
    checkpoint = REPO / '.context/strong-owl-live-physics-solver-foundation/clav-contact-step/checkpoint.json'
    descriptor = REPO / 'Hangboards/clavellium-training-block/assets/primary.physics.json'
    control = REPO / '.context/strong-owl-live-physics-accepted-profile/native/after-1.json'
    if digest(checkpoint) != CHECKPOINT_SHA or digest(descriptor) != DESCRIPTOR_SHA:
        parser.error('registered frozen Clavellium inputs required')
    fixture = json.loads(checkpoint.read_text())
    context = REPO / '.context'
    root = context / f'{owner}-candidate-discovery-{args.label}'
    if context.is_symlink() or root.exists() or root.is_symlink():
        parser.error('fresh workspace-owned output required')
    root.mkdir()
    tool = Path(__file__).resolve().parent
    for p in (tool / 'contact_discovery').iterdir():
        if p.is_file():
            shutil.copyfile(p, root / p.name)
    for source, name in [(Path(__file__), 'driver-source.py'),
                         (tool / 'run_native_contact_screen.py', 'lifecycle-source.py'),
                         (tool / 'run_stock_chain_screen.py', 'stock-driver-dependency.py')]:
        shutil.copyfile(source, root / name)
    stage = root / 'capture'
    stage.mkdir()
    sources = capture_sources(root, stage)
    commands = OwnedCommands(owner, root)
    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, commands.interrupted)

    def run(label, argv, timeout):
        status = commands.run('candidate-discovery-' + label,
                              ['perl', '-e', f'alarm {timeout}; exec @ARGV', *map(str, argv)],
                              root / (label + '.log'), dict(os.environ))
        if status:
            raise RuntimeError((root / (label + '.log')).read_text()[-6000:])

    try:
        verifier = stage / (owner + '-discovery-capture')
        run('capture-compile', ['xcrun', 'swiftc', '-O', '-whole-module-optimization', '-Xcc',
                                '-DACCELERATE_NEW_LAPACK', '-module-cache-path', stage / 'module-cache',
                                *sources, '-o', verifier], 150)
        run('capture', [verifier, stage, stage / 'frozen.json', checkpoint, descriptor, control], 30)
        reference = json.loads((stage / 'frozen.json').read_text())
        baseline_certificate = reference_certificate(reference, fixture)
        # Identity can be measured despite the ORIGINAL staged-gap failure.
        # Keep that failure visible, and require unchanged force/equality gates.
        checks = baseline_certificate['checks']
        assert checks['stationarity'] <= 1e-10 and checks['equality'] <= 1e-8
        run('git-init', ['git', 'init', root / 'JoltPhysics'], 30)
        run('git-fetch', ['git', '-C', root / 'JoltPhysics', 'fetch', '--depth', '1',
                         'https://github.com/jrouwe/JoltPhysics.git', REVISION], 180)
        run('git-checkout', ['git', '-C', root / 'JoltPhysics', 'checkout', '--detach', 'FETCH_HEAD'], 30)
        run('revision', ['git', '-C', root / 'JoltPhysics', 'rev-parse', 'HEAD'], 30)
        assert (root / 'revision.log').read_text().strip() == REVISION
        run('source-status', ['git', '-C', root / 'JoltPhysics', 'status', '--porcelain'], 30)
        assert not (root / 'source-status.log').read_text().strip()
        run('json', ['curl', '--fail', '--location', '--max-time', '30',
                     'https://raw.githubusercontent.com/nlohmann/json/v3.12.0/single_include/nlohmann/json.hpp',
                     '-o', root / 'json.hpp'], 40)
        assert digest(root / 'json.hpp') == JSON_SHA
        run('configure', ['cmake', '-S', root, '-B', root / 'build', '-DCMAKE_BUILD_TYPE=Release'], 60)
        run('build', ['cmake', '--build', root / 'build', '--target', owner + '-jolt-discovery', '-j', '6'], 240)
        binary = root / 'build' / (owner + '-jolt-discovery')
        run('query', [binary, stage / 'frozen.json', descriptor, root / 'candidates.json'], 30)
        candidates = json.loads((root / 'candidates.json').read_text())
        missing = coverage(reference, candidates)
        (root / 'coverage.json').write_text(json.dumps({'missing': missing, 'passed': not missing}, indent=2))
        assert not missing, 'native proposal omitted an original triangle witness; STOP'
        # RED: omit a returned wood witness associated with an actual compressive
        # reference row. Reject before reconstruction/solving; no adaptive repair.
        red = copy.deepcopy(candidates)
        removed = None
        for row, multiplier in zip(reference['rows'], reference['reference']['rowMultipliers']):
            if not row['contact'] or multiplier >= 0 or len(row['particles']) not in (1, 2):
                continue
            query = 2 * row['particles'][0] + (len(row['particles']) == 2)
            for hit in reference['queries'][query]['hits']:
                if row['residual'] == .00005 - hit['depth']:
                    removed = (query, hit['triangle'], multiplier)
                    red['queries'][query]['triangles'].remove(hit['triangle'])
                    break
            if removed:
                break
        assert removed is not None, 'no compressive wood witness available for RED'
        rejected = coverage(reference, red)
        assert rejected == [removed[:2]], rejected
        (root / 'missing-witness-red.json').write_text(json.dumps({'removedQueryTriangleMultiplier': removed,
            'missing': rejected, 'rejectedBeforeSolve': True}, indent=2))
        reconstruction = root / 'reconstruction'
        reconstruction.mkdir()
        run('reconstruct', [verifier, reconstruction, reconstruction / 'frozen.json', checkpoint,
                            descriptor, control, root / 'candidates.json'], 30)
        reconstructed = json.loads((reconstruction / 'frozen.json').read_text())
        keys = ('queries', 'rows', 'weights', 'positions', 'prediction', 'distanceTension',
                'boardMass', 'boardHeight', 'predictionHeight', 'regularization', 'reference')
        assert reference['candidateQueriesConsumed'] == 0
        assert reconstructed['candidateQueriesConsumed'] == len(candidates['queries'])
        identity = {k: reference[k] == reconstructed[k] for k in keys}
        assert all(identity.values()), 'original kernel rows/correction changed; STOP'
        assert (stage / 'after.json').read_bytes() == (reconstruction / 'after.json').read_bytes()
        candidate_certificate = reference_certificate(reconstructed, fixture)
        assert candidate_certificate == baseline_certificate
        (root / 'certificates.json').write_text(json.dumps({'reference': baseline_certificate,
            'candidate': candidate_certificate}, indent=2))
        summary = {'owner': owner, 'runtimeAdoption': False, 'engineRevision': REVISION,
                   'scope': 'first frozen original Clav correction; host only', 'identity': identity,
                   'acceptedStateByteIdentity': True, 'missingCompressiveWitnessRed': True,
                   'strictCertificatePassed': baseline_certificate['passed'],
                   'sourceRows': len(reference['rows']), 'queries': len(reference['queries']),
                   'candidateQueriesConsumed': reconstructed['candidateQueriesConsumed'],
                   'woodWitnesses': sum(len(q['hits']) for q in reference['queries']),
                   'candidateTriangles': sum(len(q['triangles']) for q in candidates['queries']),
                   'nativeSetupSeconds': candidates['setupSeconds'],
                   'nativeQuerySeconds': candidates['querySeconds'],
                   'baselineAssemblySeconds': reference['assemblySeconds'],
                   'candidateOriginalAssemblySeconds': reconstructed['assemblySeconds'],
                   'baselineSolveSeconds': reference['solveSeconds'],
                   'candidateSolveSeconds': reconstructed['solveSeconds']}
        (root / 'summary.json').write_text(json.dumps(summary, indent=2))
        files = [checkpoint, descriptor, control, *sources, verifier, binary,
                 *[p for p in root.iterdir() if p.is_file()],
                 *[p for p in stage.iterdir() if p.is_file()],
                 *[p for p in reconstruction.iterdir() if p.is_file()],
                 tool / 'stock_chain/CheckpointAdapter.swift', tool / 'native_contact/ExactCheckpointJSON.swift']
        (root / 'provenance.json').write_text(json.dumps({'owner': owner, 'engineRevision': REVISION,
            'hashes': {str(p.relative_to(REPO)): digest(p) for p in files}}, indent=2))
        print(json.dumps(summary, indent=2))
    finally:
        commands.cleanup()


if __name__ == '__main__':
    main()
