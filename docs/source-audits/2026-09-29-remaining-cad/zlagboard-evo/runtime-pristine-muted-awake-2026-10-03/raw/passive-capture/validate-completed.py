"""Read completed evidence only; print a new assessment, never rewrite raw records."""
from pathlib import Path
import sys,json,hashlib
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=Path(sys.argv[1]);checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
def read(name):return json.loads((r/name).read_text())
try:
 release=read('runtime-release.json');schedule=read('schedule.json');captures=read('captures.json');commands=read('commands.json');completion=read('completion.json');cleanup=read('cleanup.json');clock=read('host-clock-stability.json');anchor=read('external-anchor.json')['routeCompleted']
 expected=[*range(1,19),90,*range(183,208)]
 check('fixed44Schedule',schedule['offsetSeconds']==expected and len(captures)==44 and [c['scheduledOffset'] for c in captures]==expected)
 check('releaseAuthorization',release['runtimeAuthorized'] is True and release['exclusiveRuntimeOwnership'] is True)
 check('scheduleReleaseHash',sha(r/'schedule.json')==release['scheduleSHA256'])
 parityPath=Path(release['parityPath']);parity=json.loads(parityPath.read_text());check('bound27PathParity',sha(parityPath)==release['paritySHA256'] and parity['allEqual'] and len(parity['checks'])==27 and all(x['equal'] for x in parity['checks']))
 check('rawCompletion',completion['captureCompleted'] is True and completion['actualCaptures']==44 and not completion['errors'] and completion['CPUBracketsAvailable'] is False and completion['phaseTimingsKnown'] is False)
 check('exactCleanup',cleanup['passed'] is True and cleanup['appPIDAbsent'] is True and cleanup['awakeChildReaped'] is True and cleanup['awakePIDAbsent'] is True)
 check('appBinary',read('installed-binary-gate.json')['sha256']==release['binarySHA256'])
 env=read('launch-review-environment.json');check('onlyPristineReviewFlags',env=={'HANGTEN_REVIEW_BOARD_ID':release['boardID'],'HANGTEN_REVIEW_PLAN_ID':'research.max-hangs','HANGTEN_REVIEW_LANDSCAPE':'1'})
 check('volatileMuteArguments',read('launch-app-arguments.json')==['-workoutAudioCuesEnabled','NO'])
 windows=[]
 for c in captures:
  p=Path(c['path']);p=p if p.exists() else r/p.name
  matching=[q for q in commands if q.get('command',[])[2:6]==['xcrun','simctl','io',release['simulatorUUID']] and q['command'][-1]==c['path']]
  ok=len(matching)==1
  if ok:
   q=matching[0];ok=q['exitStatus']==0 and all(q[k]==c[k] for k in ('startEpoch','endEpoch','startMonotonic','endMonotonic'))
  target=anchor['monotonic']+c['scheduledOffset'];late=c['startMonotonic']-target
  windows.append(dict(offset=c['scheduledOffset'],passed=ok and sha(p)==c['sha256'] and abs(c['targetMonotonic']-target)<1e-6 and abs(c['latenessSeconds']-late)<1e-6 and 0<=late<=.25 and c['endMonotonic']>=c['startMonotonic'],latenessSeconds=late))
 check('all44RawHashesAndFixedStartDeadlines',len(windows)==44 and all(x['passed'] for x in windows),windows)
 offsets=[q[k+'Epoch']-q[k+'Monotonic'] for q in commands for k in ('start','end') if k+'Epoch' in q];spread=max(offsets)-min(offsets)
 check('reconstructedHostClockGate',spread<=.1 and clock['passed'] is True and abs(clock['spreadSeconds']-spread)<1e-6,dict(spreadSeconds=spread,thresholdSeconds=.1))
 route=[i for i,q in enumerate(commands) if 'openurl' in q['command']];check('oneProductionRoute',len(route)==1 and commands[route[0]]['command'][-1]=='hangten://plan/research.max-hangs/workout')
 if len(route)==1:
  later=commands[route[0]+1:];allowed=all(('screenshot' in q['command']) or ('terminate' in q['command']) or q['command'][2]=='ps' for q in later);check('noMeasurementAXOrInput',allowed)
 check('noRecordedCommandFailureBeforeCleanup',all(q.get('exitStatus')==0 and not q.get('notLaunched') and not q.get('error') for q in commands if 'terminate' not in q['command'] and q['command'][2]!='ps'))
 check('noFailureRecord',not (r/'failure.txt').exists())
except Exception as exc:check('evidenceReadable',False,repr(exc))
print(json.dumps(dict(passed=all(c['passed'] for c in checks),checks=checks,scope='Offline schedule, hashes, provenance and cleanup only',visualJudgment='NOT_PERFORMED',CPUBracketsAvailable=False,actualAppPhaseBoundariesMeasured=False,originalRecordsRewritten=False),indent=2))
sys.exit(0 if all(c['passed'] for c in checks) else 1)
