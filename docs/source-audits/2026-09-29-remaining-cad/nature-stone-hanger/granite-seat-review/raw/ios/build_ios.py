import runpy,sys
sys.argv=['run_xcode.py','build']
runpy.run_path(str(__file__).replace('build_ios.py','run_xcode.py'),run_name='__main__')
