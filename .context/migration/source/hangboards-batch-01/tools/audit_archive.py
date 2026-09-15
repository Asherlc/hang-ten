"""Recheck actual batch files, not an earlier completion claim.

Usage: python tools/audit_archive.py --tree . --report /tmp/check.json
       python tools/audit_archive.py --zip hangboards-batch-01.zip --report check.json

An exit code of zero means the supplied partial package is internally consistent and
its delivered GLBs pass these structural checks. It does NOT mean all six models
or all original deliverables are complete. That distinction is explicit in JSON.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, stat, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
import numpy as np
import trimesh
from validate import validate

SLUGS=['dewoodstok-woodbord','escape-unlimited-board','evolv-basic-training-board-long',
       'metolius-wood-grips-ii-deluxe','moon-armstrong-ash','target10a-linebreaker-base']
FONT_SUFFIXES={'.ttf','.otf','.woff','.woff2','.ttc','.eot'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path: Path) -> Any:
    return json.loads(path.read_text())

def within(root: Path, name: str) -> Path:
    rel=PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or '\\' in name:
        raise ValueError('Unsafe relative path: '+name)
    p=root.joinpath(*rel.parts)
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes root: '+name)
    return p

def check_checksums(root: Path) -> dict[str, Any]:
    root=Path(root); manifest=root/'SHA256SUMS.txt';failed=[];count=0;paths=[]
    if not manifest.is_file():
        return {'passed':False,'checked':0,'failures':[{'path':'SHA256SUMS.txt','reason':'missing'}],'paths':[]}
    for line in manifest.read_text().splitlines():
        if not line.strip():continue
        expected,name=line.split('  ',1);p=within(root,name);paths.append(name);count+=1
        if len(expected)!=64 or not p.is_file() or sha(p)!=expected:
            failed.append({'path':name,'reason':'missing or hash mismatch'})
    if len(paths)!=len(set(paths)):failed.append({'path':'SHA256SUMS.txt','reason':'duplicate entries'})
    return {'passed':not failed,'checked':count,'failures':failed,'paths':paths}

def safe_extract(archive: Path, destination: Path) -> list[dict[str,Any]]:
    destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate ZIP members')
        for i in z.infolist():
            within(destination,i.filename)
            if stat.S_ISLNK(i.external_attr>>16):raise ValueError('Symlink member rejected')
            if PurePosixPath(i.filename).suffix.lower() in FONT_SUFFIXES:raise ValueError('Font file in delivery')
        bad=z.testzip()
        if bad is not None:raise ValueError('CRC failure: '+bad)
        z.extractall(destination)
        return [{'path':i.filename,'bytes':i.file_size,'sha256':sha(within(destination,i.filename))}
                for i in z.infolist() if not i.is_dir()]

def verify_model(directory: Path) -> dict[str,Any]:
    d=Path(directory);s=read(d/'model-status.json');checks=[]
    def check(name: str, ok: Any, detail: Any=None) -> None:
        checks.append({'check':name,'pass':bool(ok),'detail':detail})
    sums=check_checksums(d);check('per_model_checksums',sums['passed'],{'files':sums['checked'],'failures':sums['failures']})
    actual={p.relative_to(d).as_posix() for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='SHA256SUMS.txt'}
    check('per_model_checksum_coverage',set(sums['paths'])==actual,sorted(actual-set(sums['paths'])))
    if not s['usableExport']:
        check('blocked_entry_has_no_invented_glb',not list(d.rglob('*.glb')))
        check('blocker_report_present',(d/'blocker-report.md').is_file())
        check('blocked_counts_are_unknown',s.get('contactCount') is None and s.get('triangleCount') is None)
        return {'slug':d.name,'status':s['status'],'usableExport':False,'checks':checks,'passed':all(c['pass'] for c in checks)}
    p=d/s['glb'];h=sha(p);cfg=read(d/'source/geometry-config.json');hm=read(d/'hold-map.json')
    v=validate(p,cfg,hm)
    check('fresh_geometry_validation',v['structuralPass'],v['checks'])
    check('current_status_hash',h==s['sha256'])
    check('status_geometry_counts',v['triangleCount']==s['triangleCount'] and v['contactCount']==s['contactCount'])
    for rel in ['build-result.json','hold-map.json','validation/structural-results.json','validation/visual-review.json','renders/render-provenance.json','renders/review-sheet-provenance.json']:
        obj=read(d/rel);check('hash_binding_'+rel,h in (obj.get('sha256'),obj.get('assetSha256')))
    references={x['id'] for x in read(d/'evidence/source-register.json')}
    check('every_hold_evidence_reference_resolves',all(set(x['evidenceRefs'])<=references for x in hm['holds']))
    prov=read(d/'renders/render-provenance.json');check('at_least_five_actual_render_records',len(prov['renders'])>=5)
    for r in prov['renders']:
        check('render_'+r['path'],sha(d/'renders'/r['path'])==r['sha256'] and r['assetSha256']==h)
    sheet=read(d/'renders/review-sheet-provenance.json')
    check('review_sheet_hash',sha(d/'renders'/sheet['output'])==sheet['sha256'])
    rb=read(d/'validation/rebuild-results.json')
    check('executed_source_reproduced_current_glb',rb['byteIdentical'] and rb['exitCode']==0 and rb['rebuiltSha256']==h and rb['assetSha256']==h)
    check('reproduction_source_hashes_current',all((d/'source'/n).is_file() and sha(d/'source'/n)==expected for n,expected in rb['sourceFilesSha256'].items()))
    # A new isolated read using both independent consumers; only this GLB is copied.
    with tempfile.TemporaryDirectory(prefix='hangboard-audit-import-') as tmp:
        isolated=Path(tmp)/'asset.glb';shutil.copyfile(p,isolated)
        scene=trimesh.load(isolated,force='scene',process=False);components={}
        for name,g in scene.geometry.items():
            if name=='body':continue
            verts,inv=np.unique(np.asarray(g.vertices),axis=0,return_inverse=True)
            patch=trimesh.Trimesh(vertices=verts,faces=inv[np.asarray(g.faces)],process=False)
            groups=trimesh.graph.connected_components(patch.face_adjacency,nodes=np.arange(len(patch.faces)),min_len=1)
            components[name]=len(groups)
        check('each_contact_one_connected_surface',all(n==1 for n in components.values()) and len(components)==s['contactCount'],components)
        import vtk
        win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1)
        importer=vtk.vtkGLTFImporter();importer.SetFileName(str(isolated));importer.SetRenderWindow(win);importer.Update()
        actors=importer.GetRenderer().GetActors();actors.InitTraversal();triangles=0;actor_count=0
        while True:
            actor=actors.GetNextActor()
            if actor is None:break
            mesh=actor.GetMapper().GetInput();triangles+=mesh.GetNumberOfPolys();actor_count+=1
        check('fresh_isolated_vtk_import',actor_count==s['contactCount']+1 and triangles==s['triangleCount'],
              {'reader':vtk.vtkVersion.GetVTKVersion(),'actors':actor_count,'triangles':triangles,'directoryContents':sorted(x.name for x in Path(tmp).iterdir())})
        win.Finalize()
    return {'slug':d.name,'status':s['status'],'usableExport':True,'sha256':h,
            'contactCount':v['contactCount'],'triangleCount':v['triangleCount'],
            'structuralCheckCount':len(v['checks']),'checks':checks,'passed':all(c['pass'] for c in checks)}

def audit_tree(root: Path) -> dict[str,Any]:
    root=Path(root);m=read(root/'batch-manifest.json');checks=[]
    def ck(name: str,ok: Any,detail: Any=None)->None:checks.append({'check':name,'pass':bool(ok),'detail':detail})
    ck('exact_six_requested_entries',[r['slug'] for r in m['models']]==SLUGS)
    rows=[]
    for r in m['models']:
        for key in ['directory','readme','statusFile','glb','holdMap','source','validation','reviewSheet','blockerReport']:
            if r.get(key):ck('path_'+r['slug']+'_'+key,within(root,r[key]).exists(),r[key])
        result=verify_model(root/r['directory']);rows.append(result)
        if r['usableExport']:ck('manifest_asset_hash_'+r['slug'],r['sha256']==result['sha256'])
    available=[r for r in rows if r['usableExport']]
    actual=list((root/'models').rglob('*.glb'))
    ck('only_declared_production_glbs',len(actual)==len(available)==m['productionAssetCount'])
    ck('production_triangle_total',sum(r['triangleCount'] for r in available)==m['productionTriangleCount'])
    ck('contact_total',sum(r['contactCount'] for r in available)==m['selectableContactCount'])
    ck('no_font_files',not any(p.suffix.lower() in FONT_SUFFIXES for p in root.rglob('*') if p.is_file()))
    ck('six_model_completeness_not_misrepresented',m['allRequestedExportsPresent']==(len(available)==6) and m['allDeliverablesComplete']==all(r['status']=='COMPLETE' for r in rows))
    sums=check_checksums(root)
    if (root/'SHA256SUMS.txt').is_file():ck('root_checksums',sums['passed'],{'files':sums['checked'],'failures':sums['failures']})
    return {'schemaVersion':1,'auditUtc':datetime.now(timezone.utc).isoformat(),'meaning':'Structural and package consistency, not manufacturer fidelity certification.',
            'passed':all(c['pass'] for c in checks) and all(r['passed'] for r in rows),
            'allDeliveredAssetsStructurallyValid':all(r['passed'] for r in available),
            'allRequestedExportsPresent':len(available)==6,'allDeliverablesComplete':all(r['status']=='COMPLETE' for r in rows),
            'productionAssetCount':len(available),'fullyCompleteModelCount':sum(r['status']=='COMPLETE' for r in rows),
            'partialModelCount':sum(r['status']=='PARTIAL' for r in rows),'evidenceBlockedModelCount':sum(r['status']=='EVIDENCE-BLOCKED' for r in rows),
            'checks':checks,'models':rows}

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    g=parser.add_mutually_exclusive_group(required=True);g.add_argument('--tree',type=Path);g.add_argument('--zip',type=Path)
    parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    if args.zip:
        with tempfile.TemporaryDirectory(prefix='hangboards-archive-readback-') as temp:
            members=safe_extract(args.zip,Path(temp));roots=list(Path(temp).glob('**/batch-manifest.json'))
            if len(roots)!=1:raise ValueError('Expected one batch manifest')
            result=audit_tree(roots[0].parent)
            result['archive']={'path':args.zip.name,'bytes':args.zip.stat().st_size,'sha256':sha(args.zip),'crcPass':True,'members':members}
    else:result=audit_tree(args.tree)
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','models','archive')},indent=2))
    if not result['passed']:
        print(json.dumps({'batchFailures':[c for c in result['checks'] if not c['pass']],
              'modelFailures':{r['slug']:[c for c in r['checks'] if not c['pass']] for r in result['models'] if not r['passed']}},indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
