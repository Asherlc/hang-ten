from pathlib import Path
import zipfile,re,hashlib,json
w=Path(__file__).resolve().parent;source=w/'validated-geometry-40e42/metolius-simulator-3d.FCStd';out=w/'uv-metadata-reproduced.FCStd';block=(w/'uv-flag-property.xml').read_text()
assert hashlib.sha256(source.read_bytes()).hexdigest()=='40e42ed072a72946d11756cd6f92047fd0d5acd79eb33946cb2188441babbbde'
with zipfile.ZipFile(source) as a:
 original=a.read('Document.xml').decode();assert 'HangTenUVNodeSurfaceNormals' not in original
 xml=re.sub(r'(<Properties Count=")(\d+)(")',lambda m:m[1]+str(int(m[2])+1)+m[3],original,count=1)
 index=xml.index('    </Properties>');xml=xml[:index]+block+xml[index:]
 with zipfile.ZipFile(out,'w') as b:
  for info in a.infolist():b.writestr(info,xml.encode() if info.filename=='Document.xml' else a.read(info.filename))
sha=hashlib.sha256(out.read_bytes()).hexdigest();assert sha==hashlib.sha256((w/'candidate/metolius-simulator-3d.FCStd').read_bytes()).hexdigest()
report={'status':'pass','metadataOnlySourceByteReproducibility':True,'sourceSHA256':sha,'nativeGeneratedPropertyBlock':'uv-flag-property.xml','originalGeometrySourceSHA256':'40e42ed072a72946d11756cd6f92047fd0d5acd79eb33946cb2188441babbbde'}
(w/'uv-metadata-reproducibility.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
