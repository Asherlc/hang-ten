"""Package current geometry only; replace stale hash-bound records instead of copying claims."""
from pathlib import Path
import sys,json,hashlib,zipfile,shutil
from configs import get
from asset_io import sha256
ROOT=Path(__file__).resolve().parents[1]
DATE='2026-09-15'
def dump(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2))
def finish(slug,notes,changes):
 d=ROOT/'models'/slug;cfg=get(slug);asset=d/(slug+'.glb');digest=sha256(asset)
 b=json.loads((d/'build-result.json').read_text());v=json.loads((d/'validation/structural-results.json').read_text());hm=json.loads((d/'hold-map.json').read_text());rp=json.loads((d/'renders/render-provenance.json').read_text())
 assert b['sha256']==v['assetSha256']==hm['assetSha256']==rp['assetSha256']==digest
 assert v['structuralPass']
 for r in rp['renders']:assert sha256(d/'renders'/r['path'])==r['sha256']
 sources=json.loads((d/'evidence/source-register.json').read_text())
 if slug=='moon-armstrong-ash':
  sources=[s for s in sources if s['id']!='MOON-ASH-PHOTO-V2']
  sources.append(dict(id='MOON-ASH-PHOTO-V2',reviewOf='I1',url=sources[1]['url'],publisher='Moon Climbing',evidenceTier='primary product photograph; exact Ash revision',accessDate=DATE,
   supports='Arched underside of central top lip, two central open shelves, asymmetric physical layout and daylight visible through the mono openings.',
   doesNotEstablish='Exact notch radius, rolled-lip cross-section, rear mono relief or which small apertures serve pulley interfaces.',review='Actual 700 x 700 original photo inspected through web reader in this revision; compared with front and oblique corrected GLB renders.',localOriginal=None,
   retentionStatus='Viewable through web; download into package failed. This record is an observation, not a retained original file.'))
 if slug=='metolius-wood-grips-ii-deluxe':
  sources=[s for s in sources if s['id']!='M-DIAGRAM-V2']
  sources.append(dict(id='M-DIAGRAM-V2',url='https://www.backcountry.com/images/items/1200/MET/MET007G/ONECOL_D3.jpg',page='https://www.backcountry.com/metolius-wood-grips-deluxe-training-board',publisher='Metolius-labelled depth diagram hosted by Backcountry',evidenceTier='product numbered diagram, retailer-hosted indexed preview',accessDate=DATE,
   supports='Deluxe arrangement; six small mounting holes; numbered depths 3=31,4=32,5=38,6=25,7=25,8=28,9=19,10=19,11=19,13=32,14=25,15=19 mm; top 2=55 and12=58 mm grip dimensions.',
   doesNotEstablish='Diagram does not dimension bore centres, bore diameters, 70 mm projection or exact section radii. Date/revision of the test sample that claimed uniform rows is unknown.',review='Readable 512 x 512 indexed original-product diagram visually inspected; direct original URL fetch failed.',localOriginal=None,
   retentionStatus='Original bytes unavailable; diagram observation and explicit numerical transcription retained, not a fabricated image.'))
  for h in hm['holds']:
   h['evidenceRefs']=list(dict.fromkeys(h['evidenceRefs']+['M-DIAGRAM-V2']))
  dump(d/'hold-map.json',hm)
 dump(d/'evidence/source-register.json',sources)
 dump(d/'evidence/feature-evidence-map.json',dict(schemaVersion=2,assetSha256=digest,features=[dict(holdId=h['holdId'],objectName=h['objectName'],evidenceRefs=h['evidenceRefs'],publishedDepthMm=h.get('publishedDepthMm'),sourceSelector=h['sourceSelector']) for h in hm['holds']],limitations=cfg['limitations']))
 src='\n\n'.join('### '+s['id']+' — '+s['publisher']+'\nURL: '+s['url']+'\n\nEvidence tier: '+s['evidenceTier']+'; accessed '+s.get('accessDate',DATE)+'.\n\nSupports: '+s['supports']+'\n\nDoes not establish: '+s['doesNotEstablish']+'\n\nOriginal file: **not retained**. '+s.get('retentionStatus','Unavailable.') for s in sources)
 ruling='''The Ash-specific photo controls topology. The prior blind central capsule, two closed centre pockets and blind mono caps contradicted that image and have been replaced. The mono passage is now visibly open, but its hidden straight rear continuation is explicitly an estimate; no pulley routing is claimed. Nominal 22 mm mono contact length is not asserted to be the total through-bore length.''' if slug=='moon-armstrong-ash' else '''The readable numbered Deluxe diagram supports the original NONUNIFORM depths. The prior audit's review-based uniform-row interpretation is not adopted. Six depicted mounting bores supersede the four-hole reconstruction. Their placement is estimated in the gap columns; it is not a drill template. The 610 x 216 mm dimensions come from the manufacturer; 70 mm projection remains a rounded retailer approximation. No claim is made that every historical sample has identical dimensions.'''
 (d/'sources.md').write_text('# Source register — '+cfg['name']+'\n\nNew geometry SHA-256: `'+digest+'`\n\n'+src+'\n\n## Conflict ruling and changes\n\n'+ruling+'\n\n## Reference rights\nPhotos/diagrams are research references, not licensed application textures. URL records and observations do not masquerade as retained images.\n')
 dump(d/'evidence/conflict-rulings.json',dict(assetSha256=digest,rulings=[ruling],changedFeatures=changes))
 dump(d/'mounting-decision.json',dict(schemaVersion=2,assetSha256=digest,mode='fixed wall-mounted',cordGeometry=False,cordMarkers=[],orientationMetadata='not applicable',boardBores=cfg['mounts'],coordinateUnits='mm source X-right Y-rear Z-up',borePlacementClassification='photo-derived estimate; not installation or manufacturing dimensions',purposeLimit='Moon lower small apertures may relate to pulley fittings; do not infer hidden routing.' if slug=='moon-armstrong-ash' else 'Six visible mounting apertures; dimensions are not a drill template.',externalHardware='No screws, walls, pulley fittings, hooks or ropes in export.'))
 dump(d/'validation/visual-review.json',dict(schemaVersion=2,assetSha256=digest,reviewDate=DATE,reviewedRenders=[r['path'] for r in rp['renders']],sourceComparison=notes,sourceFidelityCertified=False,displayApproximationLimits=cfg['limitations'],renderGeometryAuthentic=True))
 (d/'validation/report.md').write_text('# Current export verification\n\nAsset: `'+asset.name+'`\nSHA-256: `'+digest+'`\n\n'+str(sum(c['pass'] for c in v['checks']))+'/'+str(len(v['checks']))+' listed structural checks pass. See structural-results.json for actual measurements.\n\nVisual review: '+notes+'\n\nA structural pass is not a claim of factory CAD, metrology, manufacturer approval, or a fully source-verified replica.\n')
 status=dict(schemaVersion=2,name=cfg['name'],slug=slug,revision=cfg['revision'],glb=asset.name,bytes=asset.stat().st_size,structuralPass=v['structuralPass'],renders=len(rp['renders']),nativeBlender=False,status='PARTIAL',usableExport=True,sha256=digest,contactCount=len(hm['holds']),triangleCount=b['triangles'],nativeBlenderAvailable=False,changes=changes,remainingLimitations=cfg['limitations']+['Original reference-image bytes were not retained; download attempts failed.','Native Blender unavailable; actual editable GLB/PLY/NPZ and executed construction source provided under the allowed fallback.'])
 dump(d/'model-status.json',status)
 (d/'README.md').write_text(f'''# {cfg['name']} — geometry revision 2

**PARTIAL: corrected usable display model; not a fully source-verified replica.**

Exact product: {cfg['revision']}  
Export: `{asset.name}`  
SHA-256: `{digest}`  
{len(hm['holds'])} selectable contacts; {b['triangles']:,} triangles; {b['objects']} mesh objects.  
Nominal width × height × projection: {' × '.join(map(str,cfg['dimensionsMm']))} mm.  
Material: {cfg['material']}.

## Actual changes
'''+''.join('- '+x+'\n' for x in changes)+f'''
## Coordinates and selection
Source geometry is **metres, X right / Y rear / Z up**. Physical front points -Y; the canonical
source camera looks +Y, with +Z up. Origin/pivot is rear-bottom-centre (rear Y=0, bottom Z=0).
The export maps source `(x,y,z)` to glTF `(x,z,-y)`: glTF is Y-up, front is +Z, camera looks -Z.
Node transforms are identity; geometry is already transformed into metric glTF coordinates.
All production nodes are meshes. `body` is nonselectable. Each actual contact surface is a
separate `hold-<ID>` mesh, with `selectable` and `logicalHoldId` in node extras. `hold-map.json`
records the exact stable object names and the CURRENT node indices. Node indices may change
between revisions; bind interaction to logicalHoldId or objectName, not array indices.
The physical surface is partitioned, not overlaid. Individual patches are intentionally open;
only the assembled geometry is required to form a closed solid. No duplicate highlight shells.
No cords, walls, external screws, cameras, lights or rigs are included. This is a fixed board.

## Editing and rebuilding
`source/assembled-source-z-up.ply` is standard editable geometry in metres.
`source/editable-assembled-mesh.npz` adds face labels: zero=body; subsequent labels follow
`build-result.json` geometry.contactIds. The saved numeric profiles/cuts/pockets are in
`source/geometry-config.json`; no image segmentation or automatic tracing is used.

```sh
python -m pip install -r source/requirements.txt
python source/rebuild.py --output rebuilt --render
```

The source was executed and compared against this exact GLB; see validation/rebuild-results.json.
No `.blend` or Blender Outliner screenshot is included: Blender/bpy was unavailable after a
reasonable installation attempt. GLB/PLY/NPZ and executed authoring code are the permitted fallback,
not files disguised as native Blender. Python/VTK/trimesh versions are recorded under source/.

## Validation and visual review
All current structural checks, actual measurements and clean-import details are in validation/.
The {len(rp['renders'])} labelled images are genuine renders of THIS GLB after independent isolated VTK import;
render-provenance.json binds every image to the export hash. The separate visual review states
what matches the product and what remains an estimate. No source-certification is inferred
merely from a valid GLB or a passing ZIP check.

## Evidence and remaining limits
'''+''.join('- '+x+'\n' for x in status['remainingLimitations'])+'''
## Materials and rights
One neutral untextured PBR material is shared across body/contact boundaries. No invented grain,
logos or decorative textures. UVs are isometric per-triangle islands; there is no per-triangle
stretch but density and seams vary. Not suitable for seamless painted decals without reunwrapping.
Reference photos are research, not licensed shippable textures. No rights in trademarks/product
shapes are asserted. No font files are included. Display/interaction use only, not manufacturing,
load-bearing equipment, installation instructions or a measured physical replica.
''')
 # Remove stale contact sheet provenance: this fresh composite is made only from current renders.
 sheet=d/'renders/review-sheet.jpg'
 dump(d/'renders/review-sheet-provenance.json',dict(assetSha256=digest,output='review-sheet.jpg',sha256=sha256(sheet),inputs=[r['path'] for r in rp['renders']]))
 return status

def zip_model(slug):
 d=ROOT/'models'/slug
 for p in d.rglob('__pycache__'):shutil.rmtree(p)
 files=sorted(p for p in d.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
 assert not any(p.suffix.lower() in ('.ttf','.otf','.woff','.woff2') for p in files)
 (d/'SHA256SUMS.txt').write_text(''.join(sha256(p)+'  '+p.relative_to(d).as_posix()+'\n' for p in files))
 out=ROOT.parent/(slug+'-v2.zip')
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(d.rglob('*')):
   if p.is_file():z.write(p,slug+'/'+p.relative_to(d).as_posix())
 with zipfile.ZipFile(out) as z:
  assert z.testzip() is None
  for p in d.rglob('*'):
   if p.is_file():assert hashlib.sha256(z.read(slug+'/'+p.relative_to(d).as_posix())).hexdigest()==sha256(p)
 print('VERIFIED MODEL ZIP',out,out.stat().st_size)
 return out
if __name__=='__main__':
 slug=sys.argv[1]
 if slug=='moon-armstrong-ash':
  finish(slug,'Reviewed front, reverse, oblique, contact, material and side renders plus arched-jug and rear mono details. New centre is an arched upper lip and two open shelves, not three closed capsule recesses. Mono openings visibly pass through. Asymmetric layout and 21 stable contact IDs are retained. The authored side/rear profile remains approximate; some polygonal shading remains at relief transitions.',[
   'Replaced the central capsule recess with an integral upper lip and arched underside notch.',
   'Replaced the two central capsule pockets with continuous 22 mm and 18 mm nominal open shelves.',
   'Removed the false rear caps on both mono openings; front nominal grip length is distinguished from the estimated rear continuation.',
   'Kept all 21 logical IDs; regenerated current node indices, meshes, authoring source, mappings, validation and renders.'])
 elif slug=='metolius-wood-grips-ii-deluxe':
  finish(slug,'Reviewed all six clean-import renders against the readable Deluxe numbered diagram. Six mounting apertures and the 26-contact Deluxe inventory are present; nonuniform depths agree with the diagram transcription. Local tier sections, outer-jug profiles and bore centres remain photo-derived estimates. Some faceting remains on local radii.',[
   'Replaced the incorrect four-bore arrangement with six board apertures in three left/right pairs.',
   'Retained 31/32/38 mm and 25/25/28 mm nonuniform rows because the readable numbered diagram corroborates them.',
   'Resolved the earlier uniform-row audit allegation in favour of the numbered Deluxe diagram, with explicit provenance and limits.',
   'Regenerated geometry, exact mappings, source, validation, fresh renders and checksums.'])
