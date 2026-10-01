"""Exact wood-penalty residual-cost discriminator; no tube or app adoption."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True
from run_native_contact_screen import OwnedCommands

REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent / 'native_geometry'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['fixtures', 'replay'])
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    workspace = Path(os.environ.get('PASEO_WORKTREE_PATH', REPO)).resolve()
    owner = workspace.name
    if workspace != REPO or owner != os.environ.get('HANGTEN_WOOD_MERIT_OWNER'):
        parser.error('use the owned launcher in this workspace')
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.label):
        parser.error('invalid evidence label')
    root = REPO / '.context' / f'{owner}-channel-threshold'
    output = root / f'{args.mode}-{args.label}'
    for path in [REPO / '.context', root, root / 'resources.jsonl', output]:
        if path.is_symlink():
            parser.error('owned output must not be a symlink')
    if output.exists():
        parser.error('refusing to overwrite retained evidence')
    root.mkdir(exist_ok=True)
    output.mkdir()
    snapshot = output / 'source-inputs'
    snapshot.mkdir()
    sources = [REPO / 'HangTen/Models/RopePhysicsDescriptor.swift',
               REPO / 'HangTen/Models/RopeTriangleCollider.swift',
               SOURCE / 'WoodMeritThreshold.swift',
               SOURCE / ('WoodMeritThresholdFixtures.swift' if args.mode == 'fixtures' else 'WoodMeritThresholdReplay.swift')]
    hashes = {}
    for source in sources + [Path(__file__), Path(__file__).with_suffix('.sh'),
                             Path(__file__).with_name('run_native_contact_screen.py')]:
        target = snapshot / source.name
        target.write_bytes(source.read_bytes())
        hashes[str(source.relative_to(REPO))] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / 'ColliderSnapshot.swift').write_text((snapshot / 'RopeTriangleCollider.swift').read_text()+'\n'+(snapshot / 'WoodMeritThreshold.swift').read_text())
    (output / 'main.swift').write_bytes((snapshot / sources[-1].name).read_bytes())
    binary = output / f'{owner}-wood-merit-probe'
    command = ['xcrun', 'swiftc', '-O', '-whole-module-optimization', '-module-cache-path', str(output / 'module-cache'),
               str(snapshot / 'RopePhysicsDescriptor.swift'), str(output / 'ColliderSnapshot.swift'), str(output / 'main.swift'), '-o', str(binary)]
    inputs = []
    if args.mode == 'replay':
        fixed = [('.context/strong-owl-live-physics-handoff/mini-seven-mm/candidate.physics.json', '071a553221179ef88fbeef9c1c8bbcddb1d8f5ae4ae039b6a30e87891c1473db'),
                 ('.context/strong-owl-live-physics-execution/mini-production-frozen/frozen-qp.json', 'c43720bccda76df9df92c9a155f3d4a5a11195011a9eca17b7ba42b1e27d1f97'),
                 ('.context/strong-owl-live-physics-sparse-ldl/captured-checkpoints/replay-sparse-ldl-corrected-pilot/replay.json', 'c26a2e4ac2b60358f27718a5e25bc3dccbc91034900acc0430cb096f99736ba2')]
        for path, expected in fixed:
            path = REPO / path
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if expected is not None and digest != expected:
                parser.error('fixed source input differs')
            captured = snapshot / path.name
            captured.write_bytes(data)
            inputs.append(captured)
            hashes[str(path.relative_to(REPO))] = digest
    (output / 'provenance.json').write_text(json.dumps(dict(owner=owner, runtimeAdoption=False,
        sourceAndInputSHA256=hashes, compileCommand=command), indent=2, sort_keys=True)+'\n')
    commands = OwnedCommands(owner, root)
    signal.signal(signal.SIGINT, commands.interrupted)
    signal.signal(signal.SIGTERM, commands.interrupted)
    try:
        status = commands.run('wood-merit-compile', command, output / 'compile.log', dict(os.environ))
        if status:
            print((output / 'compile.log').read_text())
            return status
        invocation = [str(binary)]
        if inputs:
            invocation += [*map(str, inputs), str(output / 'report.json')]
        status = commands.run('wood-merit-probe', invocation, output / 'run.log', dict(os.environ))
        print((output / 'run.log').read_text())
        return status
    finally:
        commands.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
