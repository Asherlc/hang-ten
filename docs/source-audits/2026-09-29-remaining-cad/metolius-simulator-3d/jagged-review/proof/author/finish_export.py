from pathlib import Path
import json,hashlib,shutil
w=Path(__file__).resolve().parent
check=json.loads((w/'compile-check.json').read_text());build=json.loads((w/'compile.json').read_text());repeat=json.loads((w/'reproduce.json').read_text())
expected=json.loads((w/'uv-source-preservation.json').read_text())['sourceSHA256']
assert check['sourceSHA256']==build['sourceSHA256']==repeat['sourceSHA256']==expected
assert check['sourceUnchanged'] and build['sourceUnchanged']
assert not check['published'] and build['published']
for key in ['modelSHA256','triangles','contacts','nodes','measuredRegionDepthsMM','assetBytes','tessellationDeflectionMM']:
 assert check[key]==build[key]==repeat[key],key
source=w/'candidate/metolius-simulator-3d.FCStd'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
for name in ['primary.usdz','primary.model.json']:
 src=w/'export-run/assets'/name;dst=w/'candidate/assets'/name
 assert src.is_file()
 assert src.read_bytes()==(w/'reproduce/assets'/name).read_bytes(),name
 shutil.copy2(src,dst)
files={str(p.relative_to(w)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in [source,w/'candidate/assets/primary.usdz',w/'candidate/assets/primary.model.json']}
assert files['candidate/assets/primary.usdz']['sha256']==build['modelSHA256']
report={'status':'pass','sourceFrozen':True,'independentCompilerRuns':'check-only and export in isolated assets/TMPDIR directories','modelByteReproducibility':True,'descriptorByteReproducibility':True,'completedCandidateCompilerRuns':3,'twoNormalExportsByteIdentical':True,'files':files,'triangles':build['triangles'],'nodes':len(build['nodes']),'contacts':len(build['contacts']),'tessellationDeflectionMM':build['tessellationDeflectionMM'],'estimatedNativeThicknessMM':94.11832462653064,'publishedFaceMM':[711,222],'nativeReports':'../independent-validation/','surfaceContinuityLimit':'G1 silhouette; positionally continuous roof bridges with endpoint normal changes up to 6.77 degrees','humanAcceptance':False}
(w/'reproducibility.json').write_text(json.dumps(report,indent=2)+'\n')
(w/'candidate-status.json').write_text(json.dumps({'state':'native and deterministic compiler checks passed; exact export visual review pending','sourceSHA256':expected,'modelSHA256':build['modelSHA256']},indent=2)+'\n')
print(json.dumps(report,indent=2))
