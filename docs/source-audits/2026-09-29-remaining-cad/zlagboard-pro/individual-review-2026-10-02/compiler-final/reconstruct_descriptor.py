from pathlib import Path
import sys,json,zipfile,xml.etree.ElementTree as ET,hashlib,datetime
root=Path.cwd();out=Path(__file__).parent;pkg=root/'Hangboards/zlagboard-pro'
sys.path[:0]=[str(root/'Tools/HangboardCAD'),str(root/'Tools/HangboardModels')]
import usdz_writer
from contact_model_descriptor import compile_descriptor,NodeBinding
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=pkg/'zlagboard-pro.FCStd';asset=pkg/'assets/primary.usdz';descriptor=pkg/'assets/primary.model.json'
tree=ET.fromstring(zipfile.ZipFile(source).read('Document.xml'))
manifest=json.loads(next(p.find('String').get('value') for p in tree.findall('./Properties/Property') if p.get('name')=='HangTenBoardManifest'))
bindings=[];outlines={};native=[]
for obj in tree.findall('./ObjectData/Object'):
 props={p.get('name'):p for p in obj.findall('./Properties/Property')}
 def string(k):
  v=props.get(k);x=None if v is None else v.find('String');return '' if x is None else x.get('value','')
 node=string('NodeID')
 if not node:continue
 role=string('NodeRole');contact=(string('ContactID') or string('Label')) if role=='contact' else None
 assert 'AdditionalContactIDs' not in props and 'ContactSlotID' not in props
 assert string('HangTenPresentationID') in ('','primary')
 bindings.append(NodeBinding(node,role,contact))
 native.append({'object':obj.get('name'),'nodeID':node,'role':role,'contactID':contact})
 outline=string('HangTenHoldOutline')
 if outline:outlines[contact]=tuple((float(x)/1000,float(z)/1000) for x,z in json.loads(outline))
reopened=usdz_writer.read_usdz(asset)
rebuilt=compile_descriptor(asset.read_bytes(),bindings,{node:data['points_m'] for node,data in reopened['nodes'].items()},frozenset(c['id'] for c in manifest['contacts']),outlines)
rebuilt_bytes=(json.dumps(rebuilt.to_json(),indent=2,sort_keys=False)+'\n').encode();rebuilt_path=out/'independently-reconstructed-primary.model.json';assert not rebuilt_path.exists();rebuilt_path.write_bytes(rebuilt_bytes)
check=json.loads((out/'check.json').read_bytes());publish=json.loads((out/'publish.json').read_bytes());keys=['sourceSHA256','modelSHA256','assetBytes','contacts','nodes','triangles','measuredRegionDepthsMM','tessellationDeflectionMM']
report={'timestampUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceSHA256':sha(source),'modelSHA256':sha(asset),'descriptorSHA256':sha(descriptor),'rebuiltDescriptorSHA256':sha(rebuilt_path),'nativeTwoRunReportFactsEqual':{k:check[k]==publish[k] for k in keys},'nativeUSDZOutputsExactSHA256':check['modelSHA256']==publish['modelSHA256']==sha(asset),'descriptorIndependentlyReconstructedBytesExact':rebuilt_bytes==descriptor.read_bytes(),'nativeBindings':native,'nativeBindingSource':'Actual FCStd XML NodeID/NodeRole/ContactID properties; no bindings copied from descriptor','pointsSource':'Reopened actual published USDZ point arrays through retained usdz_writer.read_usdz','contactIDsSource':'Actual embedded HangTenBoardManifest','thirdNativeExportPerformed':False,'verificationMethod':'Two independent FreeCAD native exports (--check and publish), identical USDZ SHA/bytes and measurement reports; separately reconstruct complete descriptor bytes from final actual USD and native binding properties.'}
report['passed']=all(report['nativeTwoRunReportFactsEqual'].values()) and report['nativeUSDZOutputsExactSHA256'] and report['descriptorIndependentlyReconstructedBytesExact']
assert report['passed']
(out/'two-export-reproduction.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='nativeBindings'},indent=2))
