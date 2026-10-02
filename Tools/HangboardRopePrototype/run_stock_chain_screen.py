"""One isolated stock Jolt rigid-link step; a completed diagnostic can FAIL gates."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import sys

sys.dont_write_bytecode = True
from run_native_contact_screen import OwnedCommands, REPO

REVISION = '5830c342b90fa087f118aa0f086d541a4950b1d9'
JSON_SHA = 'aaf127c04cb31c406e5b04a63f1ae89369fccde6d8fa7cdda1ed4f32dfc5de63'
CHECKPOINT_SHA = 'cad349812c3c0c33384378fe368abff97411f2a0c9aeb385d99edebef151c464'
DESCRIPTOR_SHA = 'c60fbd6dfaf59bfd5fb7e6aa8d806f78af7e828a7f64074d326865e08f13e853'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True, type=Path)
    parser.add_argument('--descriptor', required=True, type=Path)
    parser.add_argument('--label', required=True)
    parser.add_argument('--units-per-metre', type=int, choices=(1,), default=1)
    args = parser.parse_args()
    workspace = Path(os.environ.get('PASEO_WORKTREE_PATH', REPO)).resolve()
    owner = workspace.name
    if workspace != REPO or owner != 'strong-owl-live-physics':
        parser.error('this frozen diagnostic belongs only to strong-owl-live-physics')
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('label must be lowercase letters, digits and hyphens')
    context = REPO / '.context'
    root = context / f'{owner}-stock-chain-{args.label}'
    if context.is_symlink() or root.exists() or root.is_symlink():
        parser.error('fresh workspace-owned output directory required')
    root.mkdir()
    checkpoint, descriptor = args.checkpoint.resolve(), args.descriptor.resolve()
    if digest(checkpoint) != CHECKPOINT_SHA or digest(descriptor) != DESCRIPTOR_SHA:
        parser.error('checkpoint/descriptor differ from the registered frozen Clavellium inputs')
    fixture = json.loads(checkpoint.read_text())
    if (fixture['profileID'] != 'front' or len(fixture['ropes']) != 1 or fixture['ropes'][0]['id'] != 'sling'
            or len(fixture['ropes'][0]['positions']) != 280 or fixture['ropes'][0]['radius'] != .0035
            or fixture['ropes'][0]['attachments']):
        parser.error('this bounded screen supports only the retained 280-particle Clavellium sling fixture')
    source = Path(__file__).resolve().parent / 'stock_chain'
    for p in source.iterdir():
        if p.is_file():
            shutil.copyfile(p, root / p.name)
    shutil.copyfile(Path(__file__), root / 'driver-source.py')
    shutil.copyfile(REPO / 'Tools/HangboardRopePrototype/run_native_contact_screen.py', root / 'lifecycle-source.py')
    commands = OwnedCommands(owner, root)
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, commands.interrupted)

    def run(label, argv, timeout):
        status = commands.run('stock-chain-' + label,
                              ['perl', '-e', f'alarm {timeout}; exec @ARGV', *argv],
                              root / (label + '.log'), dict(os.environ))
        if status:
            raise RuntimeError((root / (label + '.log')).read_text()[-6000:])

    try:
        run('git-init', ['git', 'init', str(root / 'JoltPhysics')], 30)
        run('git-fetch', ['git', '-C', str(root / 'JoltPhysics'), 'fetch', '--depth', '1',
                         'https://github.com/jrouwe/JoltPhysics.git', REVISION], 180)
        run('git-checkout', ['git', '-C', str(root / 'JoltPhysics'), 'checkout', '--detach', 'FETCH_HEAD'], 30)
        run('json', ['curl', '--fail', '--location', '--max-time', '30',
                     'https://raw.githubusercontent.com/nlohmann/json/v3.12.0/single_include/nlohmann/json.hpp',
                     '-o', str(root / 'json.hpp')], 40)
        assert digest(root / 'json.hpp') == JSON_SHA
        run('configure', ['cmake', '-S', str(root), '-B', str(root / 'build'), '-DCMAKE_BUILD_TYPE=Release'], 60)
        run('build', ['cmake', '--build', str(root / 'build'), '--target', 'strong-owl-live-physics-jolt-chain', '-j', '6'], 240)
        # RED fixture: the same installed-tensor guard must reject the earlier
        # metre-unit substitution before any measured update.
        status = commands.run('stock-chain-inertia-red', ['perl', '-e', 'alarm 30; exec @ARGV',
            str(root / 'build/strong-owl-live-physics-jolt-chain'), str(checkpoint), str(descriptor),
            str(root / 'unexpected-inertia-output.json'), '1', 'constructor'], root / 'inertia-red.log', dict(os.environ))
        assert status and 'SETUP FAIL: installed mass/inertia differs' in (root / 'inertia-red.log').read_text()
        assert not (root / 'unexpected-inertia-output.json').exists()
        run('cold-step', [str(root / 'build/strong-owl-live-physics-jolt-chain'), str(checkpoint),
                          str(descriptor), str(root / 'engine.json'), str(args.units_per_metre), 'install'], 30)
        reports = json.loads((root / 'engine.json').read_text())
        for i, r in enumerate(reports):
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
        shutil.copyfile(REPO / 'Tools/HangboardRopePrototype/native_contact/ExactCheckpointJSON.swift', sources / 'ExactCheckpointJSON.swift')
        shutil.copyfile(root / 'Verify.swift', sources / 'main.swift')
        run('verify-compile', ['xcrun', 'swiftc', '-O', '-whole-module-optimization', '-Xcc', '-DACCELERATE_NEW_LAPACK',
                               '-module-cache-path', str(root / 'module-cache'), *map(str, sorted(sources.iterdir())),
                               '-o', str(root / (owner + '-jolt-verifier'))], 150)
        run('verify', [str(root / (owner + '-jolt-verifier')), str(root), str(checkpoint), str(descriptor)], 45)
        checks = json.loads((root / 'physical-checks.json').read_text())['checks']
        identical = (reports[0]['checkpoint'] == reports[1]['checkpoint'] and reports[0]['actualCapsules'] == reports[1]['actualCapsules']
                     and reports[0]['engineState'] == reports[1]['engineState'])
        original = json.loads(checkpoint.read_text())['ropes']
        summary = {'owner': owner, 'engineRevision': REVISION, 'runtimeAdoption': False,
                   'deterministicState': identical, 'unitsPerMetre': args.units_per_metre,
                   'inertiaSubstitutionRedFixture': True, 'scope': 'one cold loaded Clavellium step, host only', 'reports': []}
        for r, check in zip(reports, checks):
            for initial, rope in zip(r['initial'], original):
                assert abs(initial['totalMass'] - rope['linearMass'] * sum(rope['restLengths'])) < 1e-14
                assert initial['maxEndpointMappingError'] <= 1e-8
                assert initial['maxInstalledMassInertiaRelativeError'] <= 1e-5
                arc = [0.0]
                for length in rope['restLengths']:
                    arc.append(arc[-1] + length)
                shared = rope['supports'].get('0') == rope['supports'].get(str(len(arc) - 1)) and '0' in rope['supports']
                expected = {(i, j) for i in range(len(arc) - 1) for j in range(i + 1, len(arc) - 1)
                            if j == i + 1 or arc[j] - arc[i + 1] < math.pi * rope['radius'] or
                            (shared and min(arc[i], arc[-1] - arc[i + 1]) < 4 * rope['radius'] and
                             min(arc[j], arc[-1] - arc[j + 1]) < 4 * rope['radius'])}
                assert set(map(tuple, initial['excludedPairs'])) == expected
            accepted = (check['geometryAccepted'] and check['actualCapsuleClearance'] >= max(p['radius'] for p in original) - .00005
                        and not check['woodSweepFailures'] and check['selfSweepValid'] and check['interSweepValid']
                        and r['jointEndpointGap'] <= 1e-8 and r['updateSeconds'] <= .004 and r['updateError'] == 0 and identical)
            summary['reports'].append({**check, 'updateSeconds': r['updateSeconds'], 'setupSeconds': r['setupSeconds'],
                                       'jointEndpointGap': r['jointEndpointGap'], 'initialEndpointError': r['initial'][0]['maxEndpointMappingError'],
                                       'installedMassInertiaRelativeError': r['initial'][0]['maxInstalledMassInertiaRelativeError'],
                                       'woodContactManifolds': r['woodContactManifolds'], 'ropeContactManifolds': r['ropeContactManifolds'],
                                       'screenPassed': accepted})
        (root / 'summary.json').write_text(json.dumps(summary, indent=2))
        files = [checkpoint, descriptor, *sorted(sources.iterdir()), *[p for p in root.iterdir() if p.is_file()]]
        (root / 'provenance.json').write_text(json.dumps({'owner': owner, 'engineRevision': REVISION,
            'hashes': {str(p.relative_to(REPO)): digest(p) for p in files}}, indent=2))
        print(json.dumps(summary, indent=2))
    finally:
        commands.cleanup()


if __name__ == '__main__':
    main()
