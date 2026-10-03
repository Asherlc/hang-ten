#!/usr/bin/env python3
"""Owned RED/GREEN scalar fixture runner for typed clearance bounds."""
import argparse, json, os, signal, sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_native_contact_screen import OwnedCommands,REPO
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--axis',action='store_true');p.add_argument('--free-balls',action='store_true');p.add_argument('--union',action='store_true');p.add_argument('--plane-cache',action='store_true');a=p.parse_args()
assert a.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.label)
root=REPO/'.context'/f'{REPO.name}-clearance-bounds-{a.label}';root.mkdir()
(root/'Math.swift').write_bytes(Path(__file__).with_name('Math.swift').read_bytes())
if a.axis:(root/'Axis.swift').write_bytes(Path(__file__).with_name('Axis.swift').read_bytes())
if a.free_balls:(root/'FreeBall.swift').write_bytes(Path(__file__).resolve().parents[1].joinpath('free_balls/Math.swift').read_bytes())
if a.plane_cache:(root/'PlaneCache.swift').write_bytes(Path(__file__).resolve().parents[1].joinpath('plane_reuse/Math.swift').read_bytes())
(root/'main.swift').write_text('import Foundation\nenum RopePhysicsError:Error {case invalid(String)}\ndo {try clearanceBoundFixtures();'+('try axisBoundFixtures();' if a.axis else '')+('try freeBallFixtures();' if a.free_balls else '')+('try unionSupportFixtures();' if a.union else '')+('try planeCacheFixtures();' if a.plane_cache else '')+'} catch {print("FAIL",error);exit(2)}\n')
c=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
try:
    status=c.run('bounds-fixture-compile',['xcrun','swiftc','-O','-whole-module-optimization','-module-cache-path',str(root/'module-cache'),*map(str,sorted(root.glob('*.swift'))),'-o',str(root/f'{REPO.name}-fixture')],root/'compile.log',dict(os.environ))
    if not status:status=c.run('bounds-fixture',[str(root/f'{REPO.name}-fixture')],root/'run.log',dict(os.environ))
    print((root/('run.log' if (root/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
