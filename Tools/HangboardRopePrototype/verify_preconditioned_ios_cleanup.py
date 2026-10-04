import pathlib,json,subprocess,os
root=pathlib.Path(__import__('sys').argv[1]).resolve()
logs=root/'strong-owl-live-physics/.context'
record=json.loads((logs/'ownership.json').read_text()) if (logs/'ownership.json').exists() else None
devices=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))
uuids={d['udid'] for group in devices['devices'].values() for d in group}
assert not record or record['uuid'] not in uuids
checks=[]
for manifest in logs.rglob('resources.jsonl'):
    rows=[json.loads(x) for x in manifest.read_text().splitlines()]
    for group in sorted({r['group'] for r in rows if 'group' in r}):
        try:os.killpg(group,0)
        except ProcessLookupError:checks.append({'manifest':str(manifest),'group':group,'absent':True})
        else:raise RuntimeError(('Owned group still exists',group))
assert not (logs/'DerivedData').exists()
(logs/'cleanup-verified.json').write_text(json.dumps({'simulator':record,'simulatorAbsent':not record or record['uuid'] not in uuids,'groups':checks,'derivedDataAbsent':True},indent=2))
print('Exact fresh resources deleted and independently verified')
