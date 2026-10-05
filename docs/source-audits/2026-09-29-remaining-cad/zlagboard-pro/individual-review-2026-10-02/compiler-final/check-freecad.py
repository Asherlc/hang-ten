import sys,os,json,traceback
from pathlib import Path
sys.path.insert(0,'/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger-cad-second-half/Tools/HangboardCAD')
import FreeCAD,Part
print('Pinned FreeCAD',FreeCAD.Version(),'OCCT',Part.OCC_VERSION,flush=True)
code=0
try:
 import compile_board
 code=compile_board.main(['--package', 'zlagboard-pro', '--report', '/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger-cad-second-half/.context/placid-badger-cad-second-half/zlagboard-pro/compiler-final/check.json', '--check', '--assets', '/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger-cad-second-half/.context/placid-badger-cad-second-half/zlagboard-pro/compiler-final/temporary-placid-badger-cad-second-half-check/assets'])
except BaseException:
 traceback.print_exc()
 code=3
finally:
 Path('/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger-cad-second-half/.context/placid-badger-cad-second-half/zlagboard-pro/compiler-final/check-inner-status.json').write_text(json.dumps({'exitCode':code})+'\n')
 sys.stdout.flush();sys.stderr.flush()
