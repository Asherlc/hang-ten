import json, math
from pathlib import Path
root = Path(__file__).parent
capture = [0.25, 1.0, 3.0, 5.0]
snapshots = [0.15, 0.85, 1.75, 2.85, 3.75, 4.85, 5.85, 6.75]
records = {}
for name, durations in [('short', [8,7,8,7,8]), ('long', [8,7,180,7,8])]:
    starts = [sum(durations[:i]) for i in range(len(durations))]
    total = sum(durations)
    assert len(durations) == 5 and all(math.isfinite(v) and v > 0 for v in durations)
    assert all(0 < offset < duration for duration in durations for offset in capture + snapshots)
    assert all(any(s < offset for s in snapshots) and any(s > offset for s in snapshots) for offset in capture)
    assert starts[1] == 8 and starts[2] == 15
    assert total + 2 > starts[-1] + max(capture)
    records[name] = dict(durations=durations, starts=starts, total=total, tail=total+2,
        captures=[dict(phase=i,offset=o,time=starts[i]+o) for i in range(5) for o in capture],
        snapshotOffsets=snapshots, snapshotCount=5*len(snapshots)+1)
assert records['short']['durations'][:2] == records['long']['durations'][:2]
assert records['short']['durations'][3:] == records['long']['durations'][3:]
assert records['long']['starts'][3]-records['short']['starts'][3] == 172
assert records['short']['total'] == 38 and records['long']['total'] == 210
assert all(len(r['captures']) == 20 for r in records.values())
print(json.dumps({'staticArithmeticPassed': True, 'runtimeOrCPUBracketClaim': False, 'arms': records}, indent=2))
