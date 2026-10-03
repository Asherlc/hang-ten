"""Feature census; evidence only, no numerical-method or timing acceptance."""
import argparse, collections, hashlib, json, math
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('result',type=Path)
parser.add_argument('baseline',type=Path)
args=parser.parse_args()
current=json.loads(args.result.read_text());baseline=json.loads(args.baseline.read_text())
assert current['completed'] and len(current['steps'])==len(baseline['steps'])==540
summary=collections.Counter();examples=[];penalties=[];transition_count=0
def feature_map(correction):
    rows=correction['contacts']
    ids=[row['id'] for row in rows]
    summary['unknownWoodRows']+=sum(id.startswith('wood:') and id.endswith(':-1') for id in ids)
    summary['duplicateFeatureKeys']+=len(ids)-len(set(ids))
    return {row['id']:row for row in rows}
for observed,prior in zip(current['steps'],baseline['steps']):
    assert observed['step']==prior['step'] and observed['bitIdentity']
    assert observed['QPs']==prior['trace']['correctionCount']
    assert observed['caps']==int(prior['trace']['capped']) and observed['retries']==prior['trace']['retries']
    assert observed['settled']==prior['settled']
    corrections=observed['corrections'];old=prior['trace']['corrections']
    assert len(corrections)==len(old)
    for c,p in zip(corrections,old):
        for key in ['alpha','movement','rows','strain']:assert c[key]==p[key],(observed['step'],key,c[key],p[key])
        assert len(c['activeIDs'])==p['active']
        penalties.append(c['penalty'])
        for missing in c['previousActiveMissing']:
            summary['missingActiveAtRadiusCutoff']+=missing['cutoff']
            summary['missingActiveAtEndpointFilter']+=missing['endpointFiltered']
            summary['missingActiveWithMergedSubstitute']+=bool(missing['mergedSubstitutes'])
            summary['missingActiveUnclassified']+=not (missing['cutoff'] or missing['endpointFiltered'] or missing['mergedSubstitutes'])
            if len(corrections)>=10 and c['movement']<0.00005:
                summary['longSmallCorrectionMissingAtCutoff']+=missing['cutoff']
                summary['longSmallCorrectionMissingAtEndpoint']+=missing['endpointFiltered']
                summary['longSmallCorrectionMissingWithSubstitute']+=bool(missing['mergedSubstitutes'])
    maps=[feature_map(c) for c in corrections]
    for index in range(1,len(corrections)):
        transition_count+=1
        a,b=corrections[index-1:index+1];am,bm=maps[index-1:index+1]
        active_a,active_b=set(a['activeIDs']),set(b['activeIDs'])
        dropped=active_a-set(bm);released=active_a-active_b
        summary['transitionsWithDiscoveryDrop']+=bool(dropped)
        summary['droppedActiveRows']+=len(dropped)
        summary['transitionsWithActiveChange']+=active_a!=active_b
        summary['transitionsWithPenaltyDecrease']+=b['penalty']<a['penalty']
        portal_changes=[]
        for r,(pa,pb) in enumerate(zip(a['portalsBefore'],b['portalsBefore'])):
            for key in pa.keys()|pb.keys():
                if key not in pa or key not in pb or pa[key]['segment']!=pb[key]['segment']:portal_changes.append([r,key])
        summary['transitionsWithPortalSegmentChange']+=bool(portal_changes)
        changed=[]
        for id in active_a&active_b:
            x,y=am[id],bm[id]
            if x['gradients']!=y['gradients'] or x['heightGradient']!=y['heightGradient']:
                changed.append(id)
        summary['transitionsWithSharedActiveGradientChange']+=bool(changed)
        returned=[]
        if index+1<len(maps):returned=sorted(dropped&set(corrections[index+1]['activeIDs']))
        summary['transitionsWithDroppedActiveReturn']+=bool(returned)
        if returned or portal_changes or (len(corrections)>=10 and (dropped or changed)):
            examples.append({'step':observed['step'],'fromCorrection':index,'toCorrection':index+1,
                'activeBefore':len(active_a),'activeAfter':len(active_b),'alphaBefore':a['alpha'],'alphaAfter':b['alpha'],
                'movementBefore':a['movement'],'movementAfter':b['movement'],
                'dropped':sorted(dropped),'released':sorted(released),'returnedNextCorrection':returned,
                'changedSharedGradients':sorted(changed),'portalSegmentChanges':portal_changes})
summary['transitions']=transition_count
output={'owner':'strong-owl-live-physics','instrumentationOnly':True,'adopted':False,
    'sameBinaryFullCheckpointIdentitySteps':540,'retainedTrajectoryCorrectionIdentitySteps':540,
    'summary':dict(summary),'penaltyMinimum':min(penalties),'penaltyMaximum':max(penalties),
    'uniquePenalties':sorted(set(penalties)), 'examples':examples,
    'hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.result,args.baseline,Path(__file__)]}}
destination=args.result.with_name('analysis.json');destination.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({k:v for k,v in output.items() if k not in ['examples','hashes']},indent=2))
