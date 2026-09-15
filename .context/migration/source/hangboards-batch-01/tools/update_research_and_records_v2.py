"""Update current-source observations and render records without silently changing meshes."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
DATE='2026-09-15'
def read(p):return json.loads(p.read_text())
def put(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

for slug in ['dewoodstok-woodbord','escape-unlimited-board','target10a-linebreaker-base']:
 d=ROOT/'models'/slug;h=sha(d/(slug+'.glb'));rp=read(d/'renders/render-provenance.json')
 assert rp['assetSha256']==h
 review=read(d/'validation/visual-review.json');review.update(reviewDate=DATE,geometryChanged=False,renderSha256={r['path']:r['sha256'] for r in rp['renders']})
 review['notes'].append('Fresh six-view render set reviewed during revision 2. The GLB is byte-identical to the preceding delivery; this review is not an assertion of newly resolved physical dimensions.')
 if slug=='dewoodstok-woodbord':
  review['notes'].append('Woodbord original photographs could not be reloaded during this revision. Previously reported photographic layout support is historical rather than newly independently corroborated.')
 put(d/'validation/visual-review.json',review)
 put(d/'renders/review-sheet-provenance.json',dict(assetSha256=h,output='review-sheet.jpg',sha256=sha(d/'renders/review-sheet.jpg'),sources=rp['renders'],method='Composite of current clean-import actual renders; no fabricated source images.'))
 st=read(d/'model-status.json');st['schemaVersion']=2;st['changes']=['Production geometry preserved byte-for-byte; fresh independent validation, six actual renders and updated evidence observations.'];st['renders']=len(rp['renders']);put(d/'model-status.json',st)

# Primary Woodbord text improves dimensional provenance, not the individual depth map.
d=ROOT/'models/dewoodstok-woodbord'
sources=read(d/'evidence/source-register.json')
sources=[s for s in sources if s['id']!='P3']
sources.append(dict(id='P3',url='https://www.dewoodstok.nl/product/hangboard-woodbord/',publisher='deWoodstok',evidenceTier='manufacturer product text',accessDate=DATE,supports='SKU DWS-07; bamboo; 590 x 148 x 40 mm; 1900 g; four mounting screws 5 x 90 mm; declining upper rim; four-finger depth families 13/16/20/25/30/35 mm; two-finger families 20/35 mm.',doesNotEstablish='No per-position pocket-depth map, exact pocket outlines or rim angle. Text does not independently establish the sixteen-position layout.',review='Manufacturer text actually read; image gallery did not yield readable originals.',localOriginal=None,retentionStatus='Text observations recorded. Original page/image bytes not downloaded.'))
for s in sources:
 if s['id'] in ['I1','I2']:
  s['previousReview']=s.get('review');s['review']='Historical authoring observation preserved. Re-fetch failed during revision 2; not newly corroborated.'
put(d/'evidence/source-register.json',sources)
with (d/'sources.md').open('a') as f:
 f.write('\n\n## Revision 2: stronger dimensional source, unresolved photographic map\n\nP3: https://www.dewoodstok.nl/product/hangboard-woodbord/ — manufacturer text, read 2026-09-15. Confirms 590 × 148 × 40 mm, bamboo, four screws and the published depth families. It does not assign depths to positions. Previous I1/I2 visual observations are historical; their original images could not be reloaded in this revision. No new physical-layout certification is made.\n')
with (d/'README.md').open('a') as f:
 f.write('\n\n## Revision 2 evidence update\nManufacturer source P3 now directly supports the nominal envelope/material/depth families. Original product photos could not be reloaded, so the previous layout observation is not newly independently verified. Geometry is unchanged; all six views were freshly rendered and checked.\n')

# A page that actually failed, and what exact data is needed; not a request for arbitrary research.
d=ROOT/'models/evolv-basic-training-board-long';st=read(d/'model-status.json')
access=[
 {'publisher':'Evolv','url':'https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105','result':'Exact Long product text loads; all four actual Long gallery-image fetches failed.','usefulUserAction':'Save or screenshot the front and oblique/side photographs from this exact Long gallery, preserving product identity.'},
 {'publisher':'Outland USA','url':'https://www.outlandusa.com/p/evolv-basictraining-board-black-long','result':'Long name, MPN 66-0000082105 and UPC 849948023883 verified; image link resolves to incomplete Cloudinary URL and returns 400.'},
 {'publisher':'Wilderness Exchange','url':'https://www.wildernessx.com/products/basic-training-board-long','result':'Long-specific named gallery files found (Long, Side and Side2); image fetches failed.'},
 {'publisher':'Alpenglow','url':'https://www.alpenglowgear.com/basic-training-board-long.html','result':'Long textual listing retrieved; CDN image fetches failed.'},
 {'publisher':'Backcountry','url':'https://www.backcountry.com/evolv-basic-training-board','result':'Shared Short/Long listing and one black board photo accessible. Cannot independently assign that shared photo to Long; not used to transplant the Short geometry.'},
 {'publisher':'Kilter / Setter Closet','url':'https://settercloset.com/en-ca/products/ku007','result':'24-inch Kilter/Evolv board identified; deliberately not accepted as exact Long.'},
 {'publisher':'Vertimania','url':'https://www.vertimania.com/evolv','result':'Search exposes distinct Long/Short items; page fetch returns 403.'}
]
put(d/'evidence/revision-2-access-log.json',dict(accessDate=DATE,entries=access,originalImageFilesRetained=False))
with (d/'blocker-report.md').open('a') as f:
 f.write('\n\n## Revision 2 attempts and specific unblock request\n\nThe manufacturer Long gallery at https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105 is the specific page requested for user inspection. Its text loads but its Long image assets do not. A saved front photograph and one side/oblique view are the highest-value evidence. Exact-MPN retailer attempts and exclusion of shared Short/Long photos are recorded in `evidence/revision-2-access-log.json`. The missing asset has NOT been substituted with KU007/Short or a guessed four-rail model.\n')

# One explicit current source-coverage record for all six; structural success is separate.
rows=[
 ('dewoodstok-woodbord','PARTIAL','Manufacturer text supports dimensions, material, screws and depth families.','Pocket-by-pocket depths and upper rim angle remain estimates; original photographs not reloaded; original source bytes not retained.'),
 ('escape-unlimited-board','PARTIAL','Seven contacts and paired 45/20/15 mm labels corroborated by original manufacturer guide. Asset explicitly follows dimensioned-photo revision.','Manufacturer text/image envelope disagreement unresolved; local profile estimates and missing retained source files.'),
 ('evolv-basic-training-board-long','EVIDENCE-BLOCKED','Exact Long identity/MPN and textual grip classes established.','No independently usable exact-Long front/side images; no validated model.'),
 ('metolius-wood-grips-ii-deluxe','PARTIAL','Readable numbered Deluxe diagram corroborates nonuniform depths and six board apertures. Both are represented in the corrected mesh.','Bore centres, local profile/curvature and projection remain estimates; original diagram bytes not retained.'),
 ('moon-armstrong-ash','PARTIAL','Exact Ash photograph supports arched central lip, open centre shelves and open mono apertures; these have been rebuilt.','Rear continuation of mono holes and pulley interfaces unmeasured/unresolved; radii/profile are photo estimates; original photo bytes not retained.'),
 ('target10a-linebreaker-base','PARTIAL','Fixed BASE identity, 23-contact inventory and depth/angle families supported by earlier references.','Exact pocket-depth placement and sloper handedness remain estimates; original source images not retained.')]
coverage=[]
for slug,status,yes,no in rows:
 p=ROOT/'models'/slug;glb=p/(slug+'.glb')
 coverage.append(dict(slug=slug,status=status,assetSha256=sha(glb) if glb.exists() else None,established=yes,unresolved=no))
put(ROOT/'research/source-coverage-v2.json',dict(schemaVersion=2,accessDate=DATE,fullSourceVerificationPass=False,models=coverage))
put(ROOT/'research/additional-unavailable-pages.json',dict(accessDate=DATE,entries=[
 {'url':'https://www.dewoodstok.nl/media-kits/','result':'Media labels accessible; original Woodbord assets not exposed/downloadable through reader.'},
 {'url':'https://lebe-scharnitz.at/en/top-6-2/','result':'Owner/in-use photo caption identifies Woodbord; photo link returned internal error. Caption not used to infer geometry.'},
 {'url':'https://www.outdoor-magazin.com/klettern/fingertraining-am-trainingsboard-do-s-dont-s/','result':'Text and manufacturer photo captions retrieved; actual Woodbord/BASE photos returned internal errors. Other product diagrams were not substituted.'},
 {'url':'https://www.holdsmarket.com/cs/trenink/2070-dewoodstok-hangboard-7426870707987.html','result':'Exact Woodbord text/EAN found; four original gallery images returned cache misses.'},
 {'url':'https://www.backcountry.com/images/items/1200/MET/MET007G/ONECOL_D3.jpg','result':'Readable 512-pixel indexed diagram inspected, but direct original URL fetch failed. Six bores and depths transcribed with provenance, not a fabricated reference picture.'}]))
(ROOT/'research/README.md').write_text('''# Research provenance, revision 2

No original image/PDF/page files are claimed retained. Actual accessible photographs/diagrams were inspected through the web reader and their specific observations, URL, publisher, evidence tier, date and limits are recorded in each model's evidence/source-register.json. Failed pages are distinguished from viewable images whose bytes could not be downloaded. Observations are not disguised originals or application textures.

The accepted Metolius diagram is a Metolius-labelled numbered Deluxe diagram hosted by Backcountry, not the generic Compact drawing. Its nonuniform depths take precedence over the older uniform-row review allegation; six illustrated mounting apertures control topology, with unmeasured centres still estimates.

The accepted Moon image is the manufacturer's 60-112-ASH product photo. It controls visible central and mono topology, not unseen pulley routing. The added MOON-ASH-PHOTO-V2 record is a new review of source I1, NOT an independent second photograph.

Evolv Long remains blocked rather than guessed from the shared Short/Long listing. See that model's revision-2-access-log.json for the specific gallery and failures.
''')
print('Updated current research and visual provenance.')
