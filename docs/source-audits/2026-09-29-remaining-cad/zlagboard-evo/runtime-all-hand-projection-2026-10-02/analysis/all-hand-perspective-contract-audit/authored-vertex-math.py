from pathlib import Path
import json,math,hashlib
root=Path(__file__).parent
assetPath=Path("HangTen/Resources/GripHand/hand-mesh.json")
asset=json.loads(assetPath.read_text())
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def norm(v):return math.sqrt(dot(v,v))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(v):return tuple(x/norm(v) for x in v)
rows=[]
# Aspects are explicit arithmetic examples, not asserted actual workflow viewports.
aspects={"fallback":.85,"singleExistingTest200x260":200/260,"pairExistingTest360x260":360/260,"retainedLandscapePair718x67.6667":718/(203/3)}
for pose,surface in asset["poses"].items():
 p=surface["positions"];raw=list(zip(p[0::3],p[1::3],p[2::3]))
 for kind in ["single-right","single-left","pair"]:
  if kind=="single-right":points=raw;offset=(-5.8,2.75,9.4)
  elif kind=="single-left":points=[(-x,y,z) for x,y,z in raw];offset=(5.8,2.75,9.4)
  else:points=[(-x-.82,y,z) for x,y,z in raw]+[(x+.82,y,z) for x,y,z in raw];offset=(0,2.75,9.4)
  low=[min(v[i] for v in points) for i in range(3)];high=[max(v[i] for v in points) for i in range(3)];center=tuple((a+b)/2 for a,b in zip(low,high));vectors=[sub(v,center) for v in points];radius=max(norm(v) for v in vectors)
  D=norm(offset);back=unit(offset);right=unit(cross((0,1,0),back));up=cross(back,right)
  camera=[(dot(right,v),dot(up,v),D-dot(back,v)) for v in vectors]
  nearBound=D/1.35-radius;farBound=D/.75+radius;fits=[]
  for label,a in aspects.items():
   tangent=1.08*max(max(abs(y)/d,abs(x)/(a*d)) for x,y,d in camera)
   fits.append({"aspectLabel":label,"aspect":a,"verticalFOVDegrees":2*math.atan(tangent)*180/math.pi,"maximumNormalizedCoordinate":max(max(abs(y)/(d*tangent),abs(x)/(a*d*tangent)) for x,y,d in camera)})
  relativeZoomFactors=[(D-z)/(D-1.35*z) for z in [-radius,radius]]
  rows.append({"pose":pose,"kind":kind,"vertices":len(points),"canonicalCenter":center,"boundingRadius":radius,"canonicalDistance":D,"minimumDistanceAtZoom1_35":D/1.35,"maximumDistanceAtZoom0_75":D/.75,"allAnglesNearDepthLowerBound":nearBound,"allAnglesFarDepthUpperBound":farBound,"insideFixedClipsAtEveryOrbitOrientationAndAllowedZoom":nearBound>.1 and farBound<100,"canonicalActualMinimumDepth":min(v[2] for v in camera),"canonicalActualMaximumDepth":max(v[2] for v in camera),"perspectiveZoomGainRelativeToOrthographicAtMaxZoomSphereBounds":relativeZoomFactors,"exampleCanonicalFits":fits})
summary=[]
for kind in ["single-right","single-left","pair"]:
 rs=[r for r in rows if r["kind"]==kind]
 summary.append({"kind":kind,"poses":len(rs),"maximumBoundingRadius":max(r["boundingRadius"] for r in rs),"largestRadiusPose":max(rs,key=lambda r:r["boundingRadius"])["pose"],"canonicalDistance":rs[0]["canonicalDistance"],"minimumCameraDistance":rs[0]["minimumDistanceAtZoom1_35"],"minimumAllAnglesNearDepthBound":min(r["allAnglesNearDepthLowerBound"] for r in rs),"maximumAllAnglesFarDepthBound":max(r["allAnglesFarDepthUpperBound"] for r in rs),"allAuthoredPosesClipsSafe":all(r["insideFixedClipsAtEveryOrbitOrientationAndAllowedZoom"] for r in rs),"relativeMaxZoomGainBounds":[min(r["perspectiveZoomGainRelativeToOrthographicAtMaxZoomSphereBounds"][0] for r in rs),max(r["perspectiveZoomGainRelativeToOrthographicAtMaxZoomSphereBounds"][1] for r in rs)]})
report={"scope":"Offline authored-vertex arithmetic audit, not an app test, build or runtime execution","assetPath":str(assetPath),"assetSHA256":hashlib.sha256(assetPath.read_bytes()).hexdigest(),"poses":len(asset["poses"]),"perPoseVertices":len(asset["digitIndices"]),"method":"Sphere around exact per-pose AABB center; camera aims at same center and remains distance D/zoom for every quaternion orientation. Triangle interiors lie inside the convex sphere. Thus every point depth lies between D/zoom-radius and D/zoom+radius regardless of orbit.","precision":"Python double arithmetic on authored JSON numbers; not bitwise RealityKit Float computation. Margins are several world units, far exceeding Float rounding.","summary":summary,"rows":rows,"limits":["No manufacturing or anatomical accuracy claim.","Near/far safety does not imply no horizontal/vertical screen-edge clipping during zoom or orbit.","Example aspects are labeled inputs, not a complete or measured runtime viewport inventory.","Conditional on unchanged root/hand transforms, exact source vertices, look-at canonicalCenter and current zoom clamp .75..1.35."]}
(root/"authored-vertex-math.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(summary,indent=2))
