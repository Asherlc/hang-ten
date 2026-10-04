import subprocess,sys
from pathlib import Path
script=Path(__file__).with_name("physical.py")
steps=[("01-canonical","launch","edge-20-left"),("02-orbit","orbit"),("03-reset","tap-contact","edge-20-left"),("04-pick-jug-right","tap-contact","top-jug-right"),("05-pick-flat15","tap-contact","edge-15-left"),("06-pick-incut15","tap-contact","edge-incut-15-left"),("07-pick-center-incut10","tap-contact","edge-incut-10-center")]
for step in steps:
 r=subprocess.run(["rtk","proxy",sys.executable,str(script),*step],timeout=180)
 r.check_returncode()
