"""One owned, isolated channel-row/production-QP checkpoint; never the app."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import contextlib
import shutil

sys.dont_write_bytecode = True
from run_native_contact_screen import OwnedCommands

REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
FROZEN = REPO/'.context/strong-owl-live-physics-execution/mini-production-frozen/frozen-qp.json'
TILES = REPO/'.context/strong-owl-live-physics-parametric-tiles/proof-hundred-micrometre-first/tiles.json'
MESH = REPO/'.context/strong-owl-live-physics-handoff/mini-seven-mm/candidate.physics.json'
CONTROL = REPO/'.context/strong-owl-live-physics-native-contact/replay-global-schur-reviewed-production/replay.json'


def run_native_checkpoint(native, arguments, native_output, snapshot_output):
    """The native checkpoint must share the coordinator and freeze its evidence."""
    if native_output.exists() or native_output.is_symlink():
        raise FileExistsError('Native checkpoint label already exists')
    if snapshot_output.exists() or snapshot_output.is_symlink():
        raise FileExistsError('Retained native evidence already exists')
    old_arguments=sys.argv
    old_owner=os.environ.get('HANGTEN_CONTACT_SCREEN_OWNER')
    old_handlers={s:signal.getsignal(s) for s in [signal.SIGINT,signal.SIGTERM]}
    sys.argv=[native.__file__,*arguments]
    os.environ['HANGTEN_CONTACT_SCREEN_OWNER']=REPO.name
    try:
        # A single coordinator owns cleanup; there is no inner driver process
        # for an outer TERM/KILL grace period to race against.
        with (snapshot_output.parent/'qp.log').open('w') as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                return native.main()
    finally:
        sys.argv=old_arguments
        if old_owner is None:os.environ.pop('HANGTEN_CONTACT_SCREEN_OWNER',None)
        else:os.environ['HANGTEN_CONTACT_SCREEN_OWNER']=old_owner
        for signum,handler in old_handlers.items():signal.signal(signum,handler)
        if native_output.exists():
            snapshot_output.mkdir()
            for p in native_output.iterdir():
                if p.is_symlink():raise ValueError('Native evidence is a symlink')
                if p.name=='source-inputs':shutil.copytree(p,snapshot_output/p.name)
                elif p.is_file() and p.suffix in ['.json','.log','.swift']:
                    shutil.copyfile(p,snapshot_output/p.name)
            provenance=snapshot_output/'provenance.json'
            if provenance.exists():
                doc=json.loads(provenance.read_text())
                doc['originalNativeSourceSnapshots']=doc['sourceSnapshots']
                doc['sourceSnapshots']={k:str((snapshot_output/'source-inputs'/Path(v).name).relative_to(REPO))
                                        for k,v in doc['sourceSnapshots'].items()}
                provenance.write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n')


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['fixtures','suite','checkpoint'])
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.label):
        parser.error('Use a unique lowercase label')
    owner=Path(os.environ.get('PASEO_WORKTREE_PATH',REPO)).resolve()
    if owner!=REPO or os.environ.get('HANGTEN_CHANNEL_OWNER')!=owner.name:
        parser.error('Use the owned shell launcher')
    root=REPO/'.context'/f'{owner.name}-channel-screen'
    output=root/f'{args.mode}-{args.label}'
    for p in [REPO/'.context',root,output]:
        if p.is_symlink():parser.error('Owned output cannot be a symlink')
    output.mkdir()  # Immutable evidence: do not overwrite a checkpoint.
    snapshot=output/'source-inputs';snapshot.mkdir()
    paths=[Path(__file__),Path(__file__).with_suffix('.sh'),SOURCE/'channel_contact.py',
           SOURCE/'tests/test_channel_contact.py',SOURCE/'run_native_contact_screen.py',
           SOURCE/'tests/test_channel_coordinator.py',
           SOURCE/'run_native_contact_screen.sh',SOURCE/'native_geometry/ChannelCheck.swift',
           REPO/'HangTen/Models/RopeTriangleCollider.swift',REPO/'HangTen/Models/RopePhysicsDescriptor.swift']
    for p in paths:(snapshot/p.name).write_bytes(p.read_bytes())
    provenance=dict(owner=owner.name,runtimeAdoption=False,
                    sourceSHA256={str(p.relative_to(REPO)):digest(snapshot/p.name) for p in paths})
    env=dict(os.environ,HANGTEN_NATIVE_SCREEN_PYTHON=sys.executable)
    commands=OwnedCommands(owner.name,root)
    signal.signal(signal.SIGINT,commands.interrupted)
    signal.signal(signal.SIGTERM,commands.interrupted)
    try:
        if args.mode in ['fixtures','suite']:
            (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
            tests = snapshot/'test_channel_contact.py' if args.mode=='fixtures' else SOURCE/'tests'
            status=commands.run('channel-fixtures',[sys.executable,'-m','pytest',str(tests),'-q',
                '--basetemp',str(output/f'{owner.name}-pytest-temp')],output/'fixtures.log',env)
            print((output/'fixtures.log').read_text())
            return status
        expected=[(FROZEN,'c43720bccda76df9df92c9a155f3d4a5a11195011a9eca17b7ba42b1e27d1f97'),
                  (TILES,'37a8bbfca168943da9176754427358073db3566a49af9fc7b62ebac9131d8fe2'),
                  (MESH,'071a553221179ef88fbeef9c1c8bbcddb1d8f5ae4ae039b6a30e87891c1473db'),
                  (CONTROL,'7fccac859b66a02def86765143f959407955977e2d0d82c77487ddf1893dc3b0')]
        for p,sha in expected:
            if digest(p)!=sha:raise ValueError(f'Fixed input changed: {p}')
        provenance['inputSHA256']={str(p.relative_to(REPO)):sha for p,sha in expected}
        (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        spec=importlib.util.spec_from_file_location('captured_channel_contact',snapshot/'channel_contact.py')
        model=importlib.util.module_from_spec(spec);sys.modules[spec.name]=model;spec.loader.exec_module(model)
        frozen=json.loads(FROZEN.read_text());tiles=json.loads(TILES.read_text())
        descriptor=json.loads(MESH.read_text())
        # No fixed/tied board attachments in this frozen checkpoint.
        if any(frozen['attachments']):raise ValueError('Unsupported attached frozen state')
        mouth=min(p['center'][2] for p in descriptor['portals'])-.0002
        channels=[model.UChannel(tuple(p['center']),p['majorRadius'],p['minorRadius'],mouth,float(p['decimalUpperBound']))
                  for p in tiles['patches'] if p['id'] in [13,14]]
        candidate,report=model.build_rows(frozen,channels)
        report['channels']=[vars(c) for c in channels]
        # Portal supports cannot be in the candidate domain. This protects all
        # original rows on any portal-plane crossing, including coincidences.
        removed=set(report['removedOriginalRowIDs'])
        for n,row in enumerate(frozen['rows']):
            if not row['contact'] or len(row['particles'])!=2:continue
            a,b=[frozen['positions'][row['rope']][i] for i in row['particles']]
            for p in descriptor['portals']:
                da=sum((a[k]-(frozen['boardHeight'] if k==1 else 0)-p['center'][k])*p['normal'][k] for k in range(3))
                db=sum((b[k]-(frozen['boardHeight'] if k==1 else 0)-p['center'][k])*p['normal'][k] for k in range(3))
                if da*db<=0 and n in removed:raise ValueError('Candidate removed a portal crossing row')
        report['rowCountCheckpointAccepted']=report['candidateContacts']<=3000
        (output/'candidate.json').write_text(json.dumps(candidate,separators=(',',':'),allow_nan=False)+'\n')
        (output/'builder-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print({k:report[k] for k in ['originalContacts','candidateContacts','removedRows','tubeRows','builderSeconds','rowCountCheckpointAccepted']},flush=True)
        if not report['rowCountCheckpointAccepted']:return 3
        qp_label=f'channel-{args.label}'
        qp=REPO/'.context'/f'{owner.name}-native-contact'/f'replay-{qp_label}'
        import run_native_contact_screen as native
        status=run_native_checkpoint(native,['replay','--frozen',str(output/'candidate.json'),
            '--runs','1','--global-schur','--packed','--label',qp_label],qp,output/'qp-artifacts')
        for name in ['replay.json','validation.json','provenance.json']:
            if (qp/name).exists():(output/f'qp-{name}').write_bytes((qp/name).read_bytes())
        if status not in [0,3] or not json.loads((qp/'validation.json').read_text())['numericalAccepted']:
            print((output/'qp.log').read_text());return 1
        main=output/'main.swift';main.write_bytes((snapshot/'ChannelCheck.swift').read_bytes())
        binary=output/f'{owner.name}-channel-check'
        command=['xcrun','swiftc','-O','-whole-module-optimization','-module-cache-path',str(output/'module-cache'),
                 str(snapshot/'RopePhysicsDescriptor.swift'),str(snapshot/'RopeTriangleCollider.swift'),str(main),'-o',str(binary)]
        status=commands.run('channel-check-compile',command,output/'compile.log',env)
        if status:print((output/'compile.log').read_text());return status
        status=commands.run('channel-original-mesh-check',[str(binary),str(MESH),str(FROZEN),str(qp/'replay.json'),str(CONTROL),str(output/'physical-check.json')],output/'physical.log',env)
        print((output/'qp.log').read_text());print((output/'physical.log').read_text())
        # A single cold run, unproved region, or new-row numerical success can
        # never make this a green app/performance gate.
        return status if status else 3
    finally:
        commands.cleanup()


if __name__=='__main__':raise SystemExit(main())
