import json, os, signal, subprocess, sys, time
from pathlib import Path
seconds, record_path, *args = sys.argv[1:]
record_path = Path(record_path)
cmd = ['rtk', 'proxy', *args]
start = time.monotonic()
outfile=record_path.with_suffix('.stdout');errfile=record_path.with_suffix('.stderr')
outstream=outfile.open('xb');errstream=errfile.open('xb')
proc=subprocess.Popen(cmd,stdout=outstream,stderr=errstream,start_new_session=True)
timed_out=False;interrupted_signal=None
def stop():
 if proc.poll() is None:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
def interrupted(signum,_):
 global interrupted_signal
 interrupted_signal=signum;stop();raise SystemExit(128+signum)
signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
try:
 try:proc.wait(timeout=float(seconds))
 except subprocess.TimeoutExpired:timed_out=True;stop()
finally:
 outstream.close();errstream.close()
 record_path.write_text(json.dumps({'command':cmd,'boundSeconds':float(seconds),'timedOut':timed_out,'interruptedBySignal':interrupted_signal,'exitStatus':proc.poll(),'elapsedSeconds':time.monotonic()-start},indent=2)+'\n')
sys.stdout.buffer.write(outfile.read_bytes());sys.stderr.buffer.write(errfile.read_bytes())
raise SystemExit(124 if timed_out else proc.returncode)
