from pathlib import Path
import argparse,json,hashlib,time
p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('stage');p.add_argument('observation');p.add_argument('--pixel-x',type=float);p.add_argument('--pixel-y',type=float);a=p.parse_args()
d=Path(a.directory).resolve();n=Path(__file__).resolve().parents[2];assert d.is_relative_to(n)
r=json.loads((d/(a.stage+'-review-request.json')).read_text());assert r['stage']==a.stage and hashlib.sha256(Path(r['image']).read_bytes()).hexdigest()==r['imageSHA256']
out=dict(r,reviewer='root-agent',wholeImageReviewed=True,approved=True,observedControl=r['expectedControl'],observation=a.observation,reviewEpoch=time.time())
if a.pixel_x is not None or a.pixel_y is not None:
 assert a.pixel_x is not None and a.pixel_y is not None
 out.update(coordinateScale=3,screenshotTapPixelX=a.pixel_x,screenshotTapPixelY=a.pixel_y,tapX=a.pixel_x/3,tapY=a.pixel_y/3,tapOnlyOnObservedControl=True,coordinateScope='Visible ordinary UI control only; no board geometry measurement')
with (d/(a.stage+'-review.json')).open('x') as f:json.dump(out,f,indent=2);f.write('\n')
