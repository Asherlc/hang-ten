"""Assemble current, hash-bound Batch 1 metadata and actual-render contact sheet."""
from pathlib import Path
import json,hashlib,shutil,html
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
SLUGS=['dewoodstok-woodbord','escape-unlimited-board','evolv-basic-training-board-long','metolius-wood-grips-ii-deluxe','moon-armstrong-ash','target10a-linebreaker-base']
def read(p):return json.loads(p.read_text())
def put(p,o):p.write_text(json.dumps(o,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for s in SLUGS:
 d=ROOT/'models'/s;st=read(d/'model-status.json');r=dict(st,directory='models/'+s,readme='models/'+s+'/README.md',statusFile='models/'+s+'/model-status.json')
 if st['usableExport']:
  asset=d/(s+'.glb');assert sha(asset)==st['sha256']
  for k,v in {'glb':s+'.glb','holdMap':'hold-map.json','source':'source/rebuild.py','validation':'validation/structural-results.json','reviewSheet':'renders/review-sheet.jpg'}.items():r[k]='models/'+s+'/'+v
  r['bytes']=asset.stat().st_size;r['renders']=len(read(d/'renders/render-provenance.json')['renders'])
 else:r['blockerReport']='models/'+s+'/blocker-report.md';r['renders']=0
 rows.append(r)
manifest=dict(schemaVersion=2,batch=1,packageRevision=2,productionAssetCount=5,requestedModelCount=6,fullyCompleteModelCount=0,partialModelCount=5,evidenceBlockedModelCount=1,allRequestedExportsPresent=False,allDeliverablesComplete=False,fullSourceVerificationPass=False,productionTriangleCount=sum(r.get('triangleCount') or 0 for r in rows),selectableContactCount=sum(r.get('contactCount') or 0 for r in rows),actualRenderCount=sum(r['renders'] for r in rows),nativeBlendCount=0,coordinateSource='metres; X-right Y-rear Z-up; front -Y; camera looks +Y',coordinateExport='metres; source (x,y,z)->(x,z,-y); Y-up; front +Z; camera looks -Z',geometryChangedModels=['moon-armstrong-ash','metolius-wood-grips-ii-deluxe'],models=rows)
put(ROOT/'batch-manifest.json',manifest)
# Only actual renders; the sixth panel is explicitly no-model status text.
sheet=Image.new('RGB',(2400,2250),'white');draw=ImageDraw.Draw(sheet)
try:big=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',34);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
except OSError:big=small=ImageFont.load_default()
provenance=[]
for i,r in enumerate(rows):
 x=(i%2)*1200;y=(i//2)*750
 if r['usableExport']:
  p=ROOT/r['directory']/'renders/03-oblique.png';im=Image.open(p).convert('RGB');im.thumbnail((1200,750));sheet.paste(im,(x,y))
  provenance.append(dict(slug=r['slug'],assetSha256=r['sha256'],path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
 else:
  draw.text((x+65,y+235),'Evolv Basic Training Board — Long',font=big,fill=(35,45,57))
  draw.text((x+65,y+310),'EVIDENCE-BLOCKED — no model supplied',font=small,fill=(95,52,36))
  draw.text((x+65,y+365),'Exact Long gallery images could not be loaded.',font=small,fill=(60,65,72))
  draw.text((x+65,y+415),'No Short-board substitution or guessed geometry.',font=small,fill=(60,65,72))
sheet.save(ROOT/'batch-contact-sheet.jpg',quality=93)
put(ROOT/'batch-contact-sheet-provenance.json',dict(schemaVersion=2,output='batch-contact-sheet.jpg',sha256=sha(ROOT/'batch-contact-sheet.jpg'),sources=provenance,blockedPanel='Text only; not a render or model.'))
# Human-readable report is generated from the current actual model statuses.
table='| Model | Status | Contacts | Triangles | Geometry change |\n|---|---|---:|---:|---|\n'
for r in rows:
 change=('Central arched jug, open shelves and mono passages' if r['slug']=='moon-armstrong-ash' else 'Six mounting apertures; depth-map conflict resolved' if r['slug']=='metolius-wood-grips-ii-deluxe' else 'No mesh supplied' if not r['usableExport'] else 'Unchanged mesh; fresh renders/validation')
 table+='| '+r['name']+' | '+r['status']+' | '+str(r.get('contactCount') or '—')+' | '+(f"{r['triangleCount']:,}" if r.get('triangleCount') else '—')+' | '+change+' |\n'
report='''# Batch 1 — corrected geometry, revision 2

**Five usable GLBs, two materially corrected meshes, 94 selectable contacts, 235,000 triangles, 32 current genuine renders. Five PARTIAL entries, one EVIDENCE-BLOCKED entry, zero COMPLETE entries.**

This is a geometry repair delivery, not the preceding unchanged audit. Moon and Metolius have new exports and authoring source. The other three meshes remain byte-identical; their current imports, renders and evidence notes were refreshed. Nothing is represented as fully source-verified merely because it is valid geometry.

'''+table+'''
## Corrections actually made

**Moon Armstrong, exact Ash revision.** The incorrect central pill-shaped blind pocket was replaced by an integral upper lip with an arched underside. The two centre capsule pockets became open horizontal shelves. Both mono apertures are now open rather than falsely capped at the rear. Their front nominal contact length is distinguished from the estimated continuation through the body. The 21 logical contact IDs remain stable; exported node indices are regenerated and should not be hard-coded by the app. Exact rear relief and pulley interfaces are not invented or certified.

**Metolius Wood Grips II Deluxe.** Four mounting apertures became six in three paired columns, consistent with the readable numbered Deluxe diagram. The diagram corroborates the nonuniform 31/32/38 and 25/25/28 mm rows; the earlier uniform-row review allegation is therefore not used to overwrite correct depth assignments. Bore centres remain photo-derived estimates, not a drilling guide. The final 65,000-triangle mesh passed the assembled topology check; an earlier over-decimated attempt failed and was not delivered.

## Current validation

The exact meshes were independently clean-imported for structural validation and by VTK for genuine render generation. Checks address metric scale, names, exact contact mappings, embedded material/no external references, finite nondegenerate geometry, duplicate faces, connected contact patches, assembled closed topology, real cavity-floor intersections and clear bores. Moon also has specific ray tests for its arch and open shelves. Structural validation remains distinct from photographic fidelity.

The delivered authoring sources were actually executed in isolated temporary directories without the original GLBs. The per-model rebuild records give exact source hashes and byte-identical export results. A combined repeat was interrupted by the execution timeout after two successes; the preserved successful per-model runs and separately executed remaining run are the evidence, not an assumed completion of that interrupted command.

`validation-v2/` contains red/green regressions, build/render logs, the sampling/decimation investigation, and the environment preflight. A passing test is not a claim of manufacturer approval. The final ZIP's readback and whole-file hashes are in the separately supplied archive-verification JSON, avoiding circular hashing of the ZIP inside itself.

## Source support and remaining gaps

The new numbered Metolius diagram and exact Moon Ash photo were actually inspected. Their URLs, publishers, interpretation and limits are recorded per model. The Moon new-review record refers to the same original photo as I1, not a second independent photograph. Woodbord manufacturer text now directly corroborates its nominal envelope/material/screws/depth families; its individual depth map remains unverified. Escape explicitly follows its dimensioned-photo revision rather than pretending the contradictory prose dimensions agree. Target10a pocket-depth assignment and sloper handedness remain estimates. See `research/source-coverage-v2.json` for all six.

**Original reference-image bytes are still missing.** Several original images were viewable in the web reader, but attempts to download into the artifact environment failed. Other galleries did not render at all. URL observations/transcriptions are not labelled as saved originals. No generated picture is substituted as research evidence. This is one reason the five existing assets remain PARTIAL.

**Evolv Long is the one missing mesh.** The exact Long page and MPN are known, but its front/side images could not be loaded. A shared Short/Long retailer photo and the 24-inch Kilter board are not accepted as proof of the Long geometry. Specific page: https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105 . The required help is a saved front and oblique/side image from that exact Long gallery, not another general research assignment. Additional retailer failures are in the Evolv evidence folder.

## Native authoring and allowed approximations

Blender/bpy was not available; the fresh installation attempt returned no matching bpy distribution. No native .blend or Blender Outliner screenshot is claimed. The supplied editable metre-scale PLY/NPZ plus executed numeric authoring code and self-contained GLB are the fallback permitted by the brief. Photo-derived local curvature and neutral untextured PBR appearance are documented display choices; those alone are not being treated as automatic failure of the allowed fallback.

No texture photographs, invented wood grain, logos, cords, external screws, walls, camera rigs or environments are in production GLBs. No font files are in the package. This is a display/interaction asset, not manufacturing CAD, load-bearing equipment, an installation template or a metrologically verified physical replica.

## Recheck or rebuild

Open index.html to browse the actual render sheets and model records. Per-model source/rebuild.py creates that model from the delivered numeric source. Run the package check after extraction:

```sh
python -m pip install -r requirements.txt
python tools/audit_archive.py --tree . --report /tmp/batch01-check.json
python -m pytest tests -q
```

An audit exit code of zero means the PARTIAL package is internally consistent and its delivered meshes pass the specified structural checks. It does not turn five partial models into six complete ones.
'''
(ROOT/'REPAIR-REPORT.md').write_text(report)
(ROOT/'README.md').write_text('# Hangboards Batch 1 — revision 2\n\n**Actual geometry repair: Moon and Metolius corrected. Five usable models; Evolv Long blocked; no fully source-verified batch claim.**\n\n'+table+'\nRead REPAIR-REPORT.md for exact changes and source limits. Open index.html for genuine previews. Every current mesh is mapped in batch-manifest.json; current source/renders/checksums are packaged per model. Native .blend is unavailable; GLB/PLY/NPZ and executed source are the permitted fallback.\n')
cards=[]
for r in rows:
 url=html.escape(r['directory']);title=html.escape(r['name']);status=html.escape(r['status'])
 preview=(f'<a href="{url}/renders/review-sheet.jpg"><img alt="Actual exported geometry renders" src="{url}/renders/03-oblique.png"></a>' if r['usableExport'] else '<div class="blocked">No model supplied: exact Long image evidence is missing.</div>')
 links=f'<a href="{url}/README.md">README</a> · <a href="{url}/model-status.json">Status</a>'
 if r['usableExport']:links+=f' · <a href="{url}/{html.escape(r["slug"])}.glb">GLB</a> · <a href="{url}/hold-map.json">Hold map</a> · <a href="{url}/source/rebuild.py">Source</a>'
 cards.append(f'<article><h2>{title}</h2><p><b>{status}</b></p>{preview}<p>{links}</p></article>')
(ROOT/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hangboards Batch 1 — corrected revision 2</title><style>body{font:16px system-ui,sans-serif;max-width:1240px;margin:30px auto;padding:0 22px;color:#263441;background:#f5f7fa}h1{font-size:30px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:22px}article{padding:18px;background:white;border:1px solid #dce2e8}img{width:100%;height:auto}.blocked{padding:90px 24px;background:#f1eae2}a{color:#12597d}h2{font-size:22px}</style><h1>Batch 1 — corrected geometry, revision 2</h1><p><b>Five usable GLBs · two corrected meshes · one evidence-blocked model · no complete source-verification claim.</b></p><p>All pictured assets are genuine renders of the delivered exports. This is an offline preview index, not a simulated 3D viewer.</p><p><a href="REPAIR-REPORT.md">Repair report</a> · <a href="batch-manifest.json">Exact six-entry manifest</a> · <a href="research/source-coverage-v2.json">Source coverage</a> · <a href="batch-contact-sheet.jpg">Comparison sheet</a></p><main>'''+''.join(cards)+'</main></html>')
# Remove obsolete prior-generation aggregate receipts; replace with a fresh checked report later.
for name in ['SHA256SUMS.txt','verification-results.json','individual-archive-verification.json']:
 p=ROOT/name
 if p.exists():p.unlink()
print('Manifest',len(rows),'entries;',manifest['productionTriangleCount'],'triangles;',manifest['actualRenderCount'],'renders')
