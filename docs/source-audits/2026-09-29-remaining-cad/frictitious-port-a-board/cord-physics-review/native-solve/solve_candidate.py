from pathlib import Path
import sys,inspect,time,json
root=Path('/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger')
sys.path.insert(0,str(root/'Tools/HangboardCAD'))
import solve_threaded_rope as solver
import native_cord_routes as native
base=Path(__file__).resolve().parent;solver.ROOT=base/'isolated-root'
lines,first=inspect.getsourcelines(native._solve_native_routes)
start=next(first+i for i,line in enumerate(lines) if 'translation=np.asarray(pose[' in line)
end=next(first+i for i,line in enumerate(lines) if line.strip()=='if collar_ids:')
began=time.monotonic();progress=[]
def log_event(code,line):
 if line not in (start,end):return
 frame=sys._getframe(1);pid=frame.f_locals['pose_id'];kind='start' if line==start else 'certified'
 row={'pose':pid,'event':kind,'elapsedSeconds':time.monotonic()-began};progress.append(row)
 print(json.dumps(row),flush=True);(base/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
# Python 3.12 local monitoring targets this one existing function only; routing
# logic, stations, graph and weights remain exactly the imported production code.
sys.monitoring.use_tool_id(5,'placid-badger-port-cord-progress')
sys.monitoring.register_callback(5,sys.monitoring.events.LINE,log_event)
sys.monitoring.set_local_events(5,native._solve_native_routes.__code__,sys.monitoring.events.LINE)
try:solver.main()
finally:
 sys.monitoring.set_local_events(5,native._solve_native_routes.__code__,0)
 sys.monitoring.free_tool_id(5)
