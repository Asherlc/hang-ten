#!/usr/bin/env python3
"""Owned RED/GREEN scalar fixture runner for typed clearance bounds."""
import argparse, json, os, signal, sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_native_contact_screen import OwnedCommands,REPO
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
assert a.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.label)
root=REPO/'.context'/f'{REPO.name}-clearance-bounds-{a.label}';root.mkdir()
(root/'Math.swift').write_bytes(Path(__file__).with_name('Math.swift').read_bytes())
(root/'main.swift').write_text('import Foundation\nenum RopePhysicsError:Error {case invalid(String)}\ndo {try clearanceBoundFixtures()} catch {print("FAIL",error);exit(2)}\n')
c=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
try:
    status=c.run('bounds-fixture-compile',['xcrun','swiftc','-O','-whole-module-optimization','-module-cache-path',str(root/'module-cache'),str(root/'Math.swift'),str(root/'main.swift'),'-o',str(root/f'{REPO.name}-fixture')],root/'compile.log',dict(os.environ))
    if not status:status=c.run('bounds-fixture',[str(root/f'{REPO.name}-fixture')],root/'run.log',dict(os.environ))
    print((root/('run.log' if (root/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
