from pathlib import Path
import argparse,re,json
from common import ROOT,OWNER,IOS,write_new,ownership,register_resource,run,verify_controller,archive_bundle
parser=argparse.ArgumentParser();parser.add_argument('--name',default='unit-tests');parser.add_argument('--only',action='append',default=[])
args=parser.parse_args();assert re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*',args.name)
for identifier in args.only:assert identifier.startswith(('HangTenTests','HangTenUITests')) and re.fullmatch(r'[a-zA-Z0-9_/]+',identifier)
out=ROOT/args.name;out.mkdir(exist_ok=False);d=ownership();verify_controller(d,out)
result=IOS/(('tests-'+OWNER) if args.name=='unit-tests' else ('tests-'+OWNER+'-'+args.name));result=result.with_suffix('.xcresult')
assert not result.exists();register_resource(result,'resultBundle',out)
cmd=['xcodebuild','-project','HangTen.xcodeproj','-scheme','HangTen','-configuration','Debug','-destination','platform=iOS Simulator,id='+d['simulatorUUID'],'-derivedDataPath',d['derivedData'],'-resultBundlePath',str(result),'-parallel-testing-enabled','NO','-collect-test-diagnostics','never','-maximum-concurrent-test-simulator-destinations','1']
cmd += ['-only-testing:'+x for x in (args.only or ['HangTenTests'])]
cmd += ['test-without-building']
status=1
try:status=run(out,'tests',cmd,1800,required=False)
finally:archive_bundle(result,out)
print('TEST_EXIT',status,flush=True)
raise SystemExit(status)
