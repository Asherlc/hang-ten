"""Actual process placement and immutable-source regressions for QP delegation."""
import importlib.util
import os
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_channel_contact_screen import run_native_checkpoint


def load_fixture(path):
    path.write_text('''import os,sys
from pathlib import Path
def main():
    output=Path(sys.argv[1]);output.mkdir(exist_ok=True)
    (output/'source-inputs').mkdir(exist_ok=True)
    (output/'source-inputs'/'real-source.swift').write_text('fixture source')
    (output/'compile.log').write_text('fixture compile log')
    (output/'pid').write_text(str(os.getpid()))
    return 7
if __name__=='__main__':raise SystemExit(main())
''')
    spec=importlib.util.spec_from_file_location('real_native_fixture',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_native_runs_in_same_process_so_cleanup_cannot_kill_inner_driver(tmp_path):
    module=load_fixture(tmp_path/'strong-owl-live-physics-native-fixture.py')
    native=tmp_path/'native';snapshot=tmp_path/'retained'
    status=run_native_checkpoint(module,[str(native)],native,snapshot)
    assert status==7
    assert int((native/'pid').read_text())==os.getpid()
    assert (snapshot/'source-inputs'/'real-source.swift').read_text()=='fixture source'
    assert (snapshot/'compile.log').read_text()=='fixture compile log'


def test_existing_native_evidence_is_rejected_before_any_overwrite(tmp_path):
    module=load_fixture(tmp_path/'strong-owl-live-physics-native-fixture.py')
    native=tmp_path/'native';native.mkdir()
    old=native/'source-inputs';old.mkdir()
    (old/'real-source.swift').write_text('older immutable evidence')
    with pytest.raises(FileExistsError):
        run_native_checkpoint(module,[str(native)],native,tmp_path/'retained')
    assert (old/'real-source.swift').read_text()=='older immutable evidence'
