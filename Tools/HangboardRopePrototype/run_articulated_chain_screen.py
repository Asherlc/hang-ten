"""A bounded stock Bullet articulated-chain diagnostic, never an app acceptance gate."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import sys

sys.dont_write_bytecode = True
from run_native_contact_screen import OwnedCommands, REPO
from run_stock_chain_screen import CHECKPOINT_SHA, DESCRIPTOR_SHA, JSON_SHA, digest

REVISION = '63c4d67e337017f9d8b298c900e9aabdb69296e7'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--descriptor', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    workspace = Path(os.environ.get('PASEO_WORKTREE_PATH', REPO)).resolve()
    owner = workspace.name
    if workspace != REPO or owner != 'strong-owl-live-physics':
        parser.error('this frozen screen belongs only to strong-owl-live-physics')
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('label must contain only lowercase letters, digits and hyphens')
    checkpoint, descriptor = args.checkpoint.resolve(), args.descriptor.resolve()
    if digest(checkpoint) != CHECKPOINT_SHA or digest(descriptor) != DESCRIPTOR_SHA:
        parser.error('registered frozen Clavellium inputs required')
    fixture = json.loads(checkpoint.read_text())
    rope = fixture['ropes'][0]
    if (len(fixture['ropes']) != 1 or len(rope['positions']) != 280 or rope['radius'] != .0035
            or rope['attachments'] or set(rope['supports']) != {'0', '279'}
            or rope['supports']['0'] != rope['supports']['279']):
        parser.error('the screen supports only the retained single-loop fixture')
    context = REPO / '.context'
    root = context / f'{owner}-articulated-chain-{args.label}'
    if context.is_symlink() or root.exists() or root.is_symlink():
        parser.error('fresh workspace-owned output required')
    root.mkdir()
    tool = Path(__file__).resolve().parent
    for p in (tool / 'articulated_chain').iterdir():
        if p.is_file():
            shutil.copyfile(p, root / p.name)
    for name in ('Verify.swift', 'CheckpointAdapter.swift'):
        shutil.copyfile(tool / 'stock_chain' / name, root / name)
    shutil.copyfile(Path(__file__), root / 'driver-source.py')
    shutil.copyfile(tool / 'run_native_contact_screen.py', root / 'lifecycle-source.py')
    shutil.copyfile(tool / 'run_stock_chain_screen.py', root / 'stock-driver-dependency.py')
    commands = OwnedCommands(owner, root)
    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, commands.interrupted)

    def run(label, argv, timeout):
        status = commands.run('articulated-chain-' + label,
                              ['perl', '-e', f'alarm {timeout}; exec @ARGV', *map(str, argv)],
                              root / (label + '.log'), dict(os.environ))
        if status:
            raise RuntimeError((root / (label + '.log')).read_text()[-6000:])

    try:
        run('git-init', ['git', 'init', root / 'bullet3'], 30)
        run('git-fetch', ['git', '-C', root / 'bullet3', 'fetch', '--depth', '1',
                         'https://github.com/bulletphysics/bullet3.git', REVISION], 180)
        run('git-checkout', ['git', '-C', root / 'bullet3', 'checkout', '--detach', 'FETCH_HEAD'], 30)
        run('revision', ['git', '-C', root / 'bullet3', 'rev-parse', 'HEAD'], 30)
        assert (root / 'revision.log').read_text().strip() == REVISION
        run('json', ['curl', '--fail', '--location', '--max-time', '30',
                     'https://raw.githubusercontent.com/nlohmann/json/v3.12.0/single_include/nlohmann/json.hpp',
                     '-o', root / 'json.hpp'], 40)
        assert digest(root / 'json.hpp') == JSON_SHA
        run('configure', ['cmake', '-S', root, '-B', root / 'build', '-DCMAKE_BUILD_TYPE=Release'], 60)
        run('build', ['cmake', '--build', root / 'build', '--target',
                      owner + '-articulated', owner + '-articulated-static', '-j', '6'], 240)
        binary = root / 'build' / (owner + '-articulated')
        # RED: inherited dynamics-world defaults disable all required collisions.
        # Reject that exact setup before any step, rather than timing a silent failure.
        status = commands.run('articulated-chain-groups-red',
                              ['perl', '-e', 'alarm 45; exec @ARGV', str(binary), str(checkpoint),
                               str(descriptor), str(root / 'unexpected-default-groups.json'), '--default-groups'],
                              root / 'groups-red.log', dict(os.environ))
        assert status == 3 and 'Collider collision groups exclude required contacts' in (root / 'groups-red.log').read_text()
        assert not (root / 'unexpected-default-groups.json').exists()
        run('cold-step', [binary, checkpoint, descriptor, root / 'engine.json'], 45)
        reports = json.loads((root / 'engine.json').read_text())
        assert len(reports) == 2
        for i, r in enumerate(reports):
            assert r['initialEndpointError'] <= 1e-8 and math.isfinite(r['initialVelocityProjectionError'])
            assert abs(r['totalRopeMass'] - rope['linearMass'] * sum(rope['restLengths'])) < 1e-14
            (root / f'checkpoint-{i}.json').write_text(json.dumps(r['checkpoint'], indent=2))
            (root / f'capsules-{i}.json').write_text(json.dumps({'ropes': r['actualCapsules']}, indent=2))
        sources = root / 'swift-sources'
        sources.mkdir()
        names = ['RopePhysicsDescriptor.swift', 'RopeTriangleCollider.swift', 'RopeSimulationState.swift',
                 'RopeThreadedSeed.swift', 'RopeSimulationMetrics.swift', 'RopeCordContacts.swift',
                 'RopeContactSystem.swift', 'RopeBandedSystem.swift', 'RopeDynamicsSolver.swift']
        for name in names:
            text = (REPO / 'HangTen/Models' / name).read_text()
            if name == 'RopeDynamicsSolver.swift':
                text = 'import Foundation\n' + text + '\n' + (root / 'CheckpointAdapter.swift').read_text()
            (sources / name).write_text(text)
        shutil.copyfile(tool / 'native_contact/ExactCheckpointJSON.swift', sources / 'ExactCheckpointJSON.swift')
        shutil.copyfile(root / 'Verify.swift', sources / 'main.swift')
        verifier = root / (owner + '-articulated-verifier')
        run('verify-compile', ['xcrun', 'swiftc', '-O', '-whole-module-optimization', '-Xcc', '-DACCELERATE_NEW_LAPACK',
                               '-module-cache-path', root / 'module-cache', *sorted(sources.iterdir()), '-o', verifier], 150)
        run('verify', [verifier, root, checkpoint, descriptor], 45)
        # Fresh collision worlds; never mutate the measured dynamics world's caches.
        run('static-probe', [root / 'build' / (owner + '-articulated-static'), checkpoint,
                              descriptor, root / 'engine.json', root / 'static-contacts.json'], 45)
        checks = json.loads((root / 'physical-checks.json').read_text())['checks']
        identical = all(reports[0][k] == reports[1][k] for k in
                        ('checkpoint', 'actualCapsules', 'engineState', 'supportClosureGap', 'closureImpulse'))
        summary = {'owner': owner, 'engineRevision': REVISION, 'runtimeAdoption': False,
                   'scope': 'two cold copies of one loaded Clavellium step; host only',
                   'collisionGroupRedFixture': True, 'deterministicState': identical, 'reports': []}
        keys = ('initialEndpointError', 'initialVelocityProjectionError', 'totalRopeMass', 'internalEndpointGap',
                'supportClosureGap', 'setupSeconds', 'updateSeconds', 'woodContactManifolds', 'woodContactPoints',
                'positiveWoodImpulsePoints', 'totalWoodImpulse', 'selfManifolds', 'selfContactPoints',
                'emptySelfManifolds', 'broadphasePairs', 'solverIterations', 'closureImpulse')
        for r, check in zip(reports, checks):
            passed = (check['geometryAccepted'] and check['actualCapsuleClearance'] >= rope['radius'] - .00005
                      and not check['woodSweepFailures'] and check['selfSweepValid'] and check['interSweepValid']
                      and r['internalEndpointGap'] <= 1e-8 and r['supportClosureGap'] <= 1e-8
                      and r['updateSeconds'] <= .004 and identical)
            summary['reports'].append({**check, **{k: r[k] for k in keys}, 'screenPassed': passed})
        (root / 'summary.json').write_text(json.dumps(summary, indent=2))
        files = [checkpoint, descriptor, *sorted(sources.iterdir()),
                 *[p for p in root.iterdir() if p.is_file() and p.name != 'provenance.json'],
                 binary, root / 'build' / (owner + '-articulated-static')]
        (root / 'provenance.json').write_text(json.dumps({'owner': owner, 'engineRevision': REVISION,
            'hashes': {str(p.relative_to(REPO)): digest(p) for p in files}}, indent=2))
        print(json.dumps(summary, indent=2))
    finally:
        commands.cleanup()


if __name__ == '__main__':
    main()
