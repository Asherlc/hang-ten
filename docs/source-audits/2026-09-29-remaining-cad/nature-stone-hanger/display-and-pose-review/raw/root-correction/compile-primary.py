from pathlib import Path
import sys
w=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'))
import compile_board
sys.argv=['compile_board.py','--package','nature-stone-hanger','--source',str(w/'native-author/nature-stone-hanger.FCStd'),'--assets',str(w/'assets'),'--report',str(w/'compile-primary.json')]
compile_board.main()
