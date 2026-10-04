"""Read-only branch evidence; no pixel inference, no general input-correlation claim."""
import math, re
LIMITS=["No pose/finger/side identity emitted by image events. Revision is not semantic proof; fixed half-crimp source and whole screenshots require review.","Publication/callback/census are sampled CPU evidence, not proof of presenting pixels or GPU inactivity.","Current LIVE hand attachment uses sparse recorded checkpoints; final before/after brackets remain separately required."]
def require(ok,message):
    if not ok: raise AssertionError(message)
def image_rows(rows): return [r for r in rows if r.get('event')=='hand-image']
def arviews(census):
    return [p for s in census.get('windowScenes',[]) for w in s.get('windows',[]) for p in w.get('rendererPlacements',[]) if p.get('class')=='RealityKit.ARView']
def protocol(rows,role):
    events=image_rows(rows)
    require(role in ('live','image'),'Unknown role')
    if role=='live':
        require(not events,'LIVE emitted image events')
        return dict(current=[],sessions={},events=0)
    require(not any(r.get('event')=='hand-lifecycle' and r.get('lifecycleEvent')=='make-entry' for r in rows),'IMAGE created live hand host')
    sessions={}; stages={}; publications=[]
    for r in events:
        sid=r['sessionID'];rev=r['revision'];event=r['imageEvent'];k=(sid,rev)
        require(re.fullmatch(r'[A-Fa-f0-9-]{36}',sid) and isinstance(rev,int) and rev>0,'Invalid session/revision')
        s=sessions.setdefault(sid,dict(latest=0,active=False,inFlight=None,requests={},environment=False,environmentPending=None,environmentInactiveCompletion=None))
        if event=='requested':
            require(rev>s['latest'],'Non-increasing request revision');s.update(latest=rev,active=True)
            s['requests'][rev]=r
        elif event=='waiting-for-viewport':
            require(rev in s['requests'] and s['inFlight'] is None,'Waiting without request or during same-session frame')
            q=s['requests'][rev];v=list(map(float,q['requestedViewport']));scale=float(q['requestedDisplayScale'])
            require(len(v)==2 and math.isfinite(scale) and scale>0 and all(math.isfinite(x) and x>=0 and x*scale<=4096 for x in v) and 0 in v,'Invalid waiting dimensions')
            stages[k]={'waiting':r}
        elif event in ('environment-preparation-begun','environment-preparation-completed'):
            require(rev in s['requests'],'Environment without request')
            require(r['resourceName']=='placid-badger-cad-second-half-hand-image-neutral-'+sid,'Wrong per-session environment resource')
            require(r['environmentMode']=='fixed-neutral-white-adaptation' and r['sourceRGB']==[1,1,1] and r['sourceAlpha']==1 and r['intensityExponent']==0,'Unexpected neutral adaptation')
            require(r['sourceColorSpace']=='sRGB' and r['sourceWidth']==32 and r['sourceHeight']==16 and r['sourceBitsPerComponent']==8,'Unexpected environment source representation')
            if event=='environment-preparation-begun':
                require(s['environmentPending'] is None and not s['environment'],'Duplicate environment preparation')
                s['environmentPending']=rev
            else:
                require(s['environmentPending']==rev,'Environment completion without its begun revision')
                require(r['currentRevision']==s['latest'] and r['active'] is s['active'],'Environment completion context mismatch')
                s['environmentPending']=None
                if r['active']:s['environment']=True
                else:s['environmentInactiveCompletion']=rev
        elif event=='environment-preparation-discarded':
            require(s['environmentInactiveCompletion']==rev and not s['active'],'Discard without inactive completion')
            s['environmentInactiveCompletion']=None
        elif event=='submitted':
            require(s['inFlight'] is None and rev in s['requests'] and k not in stages,'Invalid concurrent/submitted revision')
            q=s['requests'][rev];v=list(map(float,q['requestedViewport']));scale=float(q['requestedDisplayScale'])
            require(s['environment'] and len(v)==2 and math.isfinite(scale) and scale>0 and all(math.isfinite(x) and x>0 and x*scale<=4096 for x in v),'Invalid submitted dimensions/environment')
            require(r['viewport']==v and r['displayScale']==scale,'Request/submitted dimensions differ')
            require(r['kind'] in ('single','pair') and r['orthographic'] is True and r['perspective'] is False,'Wrong kind/projection')
            require(r['textureWidth']==math.ceil(v[0]*scale) and r['textureHeight']==math.ceil(v[1]*scale),'Texture dimensions differ')
            require(r['textureFormat']=='bgra8Unorm_srgb' and r['inputColorSpace']=='sRGB','Unexpected color format')
            require(r['orientationConversion']=='CIImage.downMirrored; UIImage.up','Unexpected orientation conversion')
            require(r['environmentLightingResourcePresent'] and r['environmentLightingMode']=='fixed-neutral-white-adaptation' and r['environmentLightingIntensityExponent']==0 and r['environmentResourceName']=='placid-badger-cad-second-half-hand-image-neutral-'+sid,'Unexpected lighting/resource')
            s['inFlight']=rev;stages[k]={'submitted':r}
        elif event=='gpu-completion-callback':
            require(s['inFlight']==rev and k in stages and 'gpu-completion-callback' not in stages[k],'Callback without unique submission')
            require(r['metalCommandBufferStatusAvailable'] is False and stages[k]['submitted']['uptime']<=r['callbackUptime']<=r['uptime'],'Invalid callback timing')
            stages[k][event]=r
        elif event=='conversion-complete':
            require(s['inFlight']==rev and 'gpu-completion-callback' in stages[k],'Conversion without callback')
            sub=stages[k]['submitted']
            require(r['eagerMaterialization'] and r['orientation']=='up' and r['ciOrientationConversion']=='downMirrored','Invalid conversion')
            require(r['cgWidth']==sub['textureWidth'] and r['cgHeight']==sub['textureHeight'] and r['cgBitsPerComponent']==8 and r['cgAlphaInfo'] in (1,2,3,4),'Invalid CG image')
            stages[k][event]=r
        elif event=='published':
            require(s['inFlight']==rev and 'conversion-complete' in stages[k] and s['active'] and r['currentRevision']==rev==s['latest'],'Stale/invalid publication')
            require(re.fullmatch(r'[a-f0-9]{64}',r['pngSHA256']) and r['pngByteCount']>0,'Invalid PNG metadata')
            # A workout board ARView is expected. Keep the entire census for independent mapping;
            # absence of all ARViews is NOT the hand-image contract here.
            require(isinstance(r['applicationCensus'],dict),'Missing publication census')
            stages[k][event]=r;publications.append(r);s['inFlight']=None
        elif event=='stale-completion-discarded':
            require(s['inFlight']==rev and 'gpu-completion-callback' in stages[k],'Discard without callback');s['inFlight']=None
        elif event=='disappear':
            require(rev>s['latest'],'Non-increasing disappear revision');s.update(latest=rev,active=False)
        elif event=='failed': raise AssertionError('Prototype failed: '+r['error'])
        else: raise AssertionError('Unknown image event: '+event)
    current=[dict(publication=p,submission=stages[(p['sessionID'],p['revision'])]['submitted']) for p in publications if sessions[p['sessionID']]['active'] and p['revision']==sessions[p['sessionID']]['latest']]
    return dict(current=current,sessions=sessions,events=len(events))
def capture_evidence(rows,role):
    state=protocol(rows,role)
    if role=='image':
        active=[sid for sid,s in state['sessions'].items() if s['active']]
        require(len(active)==1 and len(state['current'])==1,'IMAGE missing unique current published coordinator at mandatory capture')
        c=state['current'][0];require(c['submission']['kind']=='pair','Workout publication is not pair')
        require(all(state['sessions'][sid]['inFlight'] is None for sid in active),'IMAGE render pending at capture')
        return dict(role=role,publication=c['publication'],submission=c['submission'],publicationARViews=arviews(c['publication']['applicationCensus']),limits=LIMITS)
    make={r['handLifetimeToken']:r for r in rows if r.get('event')=='hand-lifecycle' and r.get('lifecycleEvent')=='make-entry'}
    latest=next((r for r in reversed(rows) if 'handLifetimeCensus' in r),None)
    require(latest is not None,'No LIVE hand census')
    attached=[]
    for h in latest['handLifetimeCensus']:
        if h['kind']!='pair' or h['handLifetimeToken'] not in make:continue
        a,b=h['root'],h['camera']
        if all(x.get('alive') and x.get('enabled') and x.get('isActive') and x.get('realitySceneID') not in (None,'nil') and x.get('parentEntityID') not in (None,'nil') for x in (a,b)) and a['realitySceneID']==b['realitySceneID']:
            require(b['orthographicComponent'] and not b['perspectiveComponent'],'LIVE camera not orthographic');attached.append(h)
    require(len(attached)==1,'No unique LIVE attached pair in latest sparse census')
    return dict(role=role,censusSequence=latest['sequence'],censusEpoch=latest['epoch'],hand=attached[0],limits=LIMITS)
def published_artifacts(rows):
    return [dict(path=r['pngPath'],sha256=r['pngSHA256'],bytes=r['pngByteCount'],sessionID=r['sessionID'],revision=r['revision'],sequence=r['sequence']) for r in image_rows(rows) if r['imageEvent']=='published']
