"""Runtime compilation must work without any previously checked-in exports."""
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_assets


@pytest.fixture
def compiler(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    package = repository / "Hangboards" / "fixture"
    package.mkdir(parents=True)
    (package.parent / "fixture.FCStd").write_bytes(b"authored source")
    monkeypatch.setattr(prepare_assets, "REPOSITORY", repository)
    authoring = {"physics": None, "suspension": None}
    monkeypatch.setattr(prepare_assets.cad_source, "load_rope_physics_authoring", lambda source: authoring["physics"], raising=False)
    monkeypatch.setattr(prepare_assets.cad_source, "load_suspension_authoring", lambda source: authoring["suspension"], raising=False)
    targets = {"primary": ("primary.usdz", "primary.model.json")}
    monkeypatch.setattr(prepare_assets, "source_targets", lambda source: targets)

    def build(package, destination, freecad, extra_path, presentation_id=None):
        destination.mkdir(parents=True, exist_ok=True)
        asset_name, descriptor_name = targets[presentation_id or "primary"]
        data = asset_name.encode()
        (destination / asset_name).write_bytes(data)
        (destination / descriptor_name).write_text(json.dumps({
            "modelSHA256": hashlib.sha256(data).hexdigest(),
        }))
        if authoring["physics"] is not None:
            (destination / "primary.physics.json").write_text(json.dumps({
                "modelSHA256": hashlib.sha256(data).hexdigest(),
                "sourceSHA256": hashlib.sha256((repository / "Hangboards/fixture.FCStd").read_bytes()).hexdigest(),
            }))

    monkeypatch.setattr(prepare_assets, "_run_build", build)
    return package, targets, build, authoring


def test_compiles_without_any_committed_descriptor(compiler, tmp_path):
    package, _, _, _ = compiler
    out = tmp_path / "compiled"
    report = prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert report["package"] == "fixture"
    assert (out / "fixture/assets/primary.usdz").read_bytes() == b"primary.usdz"
    assert (out / "fixture/assets/primary.model.json").is_file()
    assert not (package / "assets").exists()


def test_carries_all_configurations(compiler, tmp_path):
    package, targets, _, _ = compiler
    targets["depth-10mm"] = ("depth-10mm.usdz", "depth-10mm.model.json")
    out = tmp_path / "compiled"
    prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert {p.name for p in (out / "fixture/assets").iterdir()} == {
        "primary.usdz", "primary.model.json",
        "depth-10mm.usdz", "depth-10mm.model.json",
    }


def test_carries_matching_physics_descriptor(compiler, tmp_path):
    package, _, _, authoring = compiler
    authoring["physics"] = {}
    out = tmp_path / "compiled"
    prepare_assets.prepare(package.name, out, Path("freecad"), "")
    physics = json.loads((out / "fixture/assets/primary.physics.json").read_text())
    assert physics["modelSHA256"] == hashlib.sha256(b"primary.usdz").hexdigest()


def test_rejects_mismatched_compiled_hash_before_publication(compiler, tmp_path, monkeypatch):
    package, _, build, _ = compiler

    def corrupt(*args):
        build(*args)
        (args[1] / "primary.model.json").write_text('{"modelSHA256":"wrong"}')

    monkeypatch.setattr(prepare_assets, "_run_build", corrupt)
    out = tmp_path / "compiled"
    with pytest.raises(RuntimeError, match="does not hash"):
        prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert not (out / "fixture/assets").exists()


def test_failed_configuration_leaves_previous_complete_outputs(compiler, tmp_path, monkeypatch):
    package, targets, build, _ = compiler
    targets["depth-10mm"] = ("depth-10mm.usdz", "depth-10mm.model.json")
    out = tmp_path / "compiled"
    existing = out / "fixture/assets/primary.usdz"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"previous")

    def fail(package, destination, freecad, extra_path, presentation_id=None):
        if presentation_id == "depth-10mm":
            raise RuntimeError("configuration failed")
        build(package, destination, freecad, extra_path, presentation_id)

    monkeypatch.setattr(prepare_assets, "_run_build", fail)
    with pytest.raises(RuntimeError, match="configuration failed"):
        prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert existing.read_bytes() == b"previous"


def test_removed_configuration_is_pruned_after_successful_build(compiler, tmp_path):
    package, targets, _, _ = compiler
    targets["depth-10mm"] = ("depth-10mm.usdz", "depth-10mm.model.json")
    out = tmp_path / "compiled"
    prepare_assets.prepare(package.name, out, Path("freecad"), "")
    authored = out / "fixture/assets/source-evidence.txt"
    authored.write_text("retain authored evidence")
    del targets["depth-10mm"]
    prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert {p.name for p in authored.parent.iterdir()} == {
        "primary.usdz", "primary.model.json", "source-evidence.txt",
    }
    assert authored.read_text() == "retain authored evidence"


def test_suspension_failure_preserves_previous_complete_package(compiler, tmp_path, monkeypatch):
    package, _, _, authoring = compiler
    authoring["suspension"] = {}
    out = tmp_path / "compiled"
    existing = out / "fixture/assets/primary.usdz"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"previous")

    def fail(*args):
        raise RuntimeError("native cord route could not be solved")

    monkeypatch.setattr(prepare_assets, "_run_suspension", fail, raising=False)
    with pytest.raises(RuntimeError, match="cord route"):
        prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert existing.read_bytes() == b"previous"


def test_complete_cache_builds_without_freecad(compiler, tmp_path, monkeypatch):
    package, _, _, _ = compiler
    cache = tmp_path / "cache"
    prepare_assets.prepare(package.name, tmp_path / "first", Path("freecad"), "", cache_dir=cache)
    monkeypatch.setattr(prepare_assets, "_run_build", lambda *args: pytest.fail("cache hit invoked FreeCAD"))
    report = prepare_assets.prepare(package.name, tmp_path / "second", Path("missing-freecad"), "", cache_dir=cache)
    assert report["cacheHit"] is True
    assert (tmp_path / "second/fixture/assets/primary.usdz").read_bytes() == b"primary.usdz"


def test_changed_source_rebuilds_only_its_cache_entry(compiler, tmp_path, monkeypatch):
    package, _, build, _ = compiler
    cache = tmp_path / "cache"
    (package.parent / "second.FCStd").write_bytes(b"second source")
    prepare_assets.prepare(package.name, tmp_path / "first", Path("freecad"), "", cache_dir=cache)
    prepare_assets.prepare("second", tmp_path / "first", Path("freecad"), "", cache_dir=cache)
    (package.parent / "fixture.FCStd").write_bytes(b"changed authoring")
    def changed_build(*args):
        build(*args)
        (args[1] / "primary.usdz").write_bytes(b"changed model")
        (args[1] / "primary.model.json").write_text(json.dumps({"modelSHA256": hashlib.sha256(b"changed model").hexdigest()}))
    monkeypatch.setattr(prepare_assets, "_run_build", changed_build)
    report = prepare_assets.prepare(package.name, tmp_path / "second", Path("freecad"), "", cache_dir=cache)
    assert report["cacheHit"] is False
    assert (tmp_path / "second/fixture/assets/primary.usdz").read_bytes() == b"changed model"
    monkeypatch.setattr(prepare_assets, "_run_build", lambda *args: pytest.fail("unchanged board rebuilt"))
    report = prepare_assets.prepare("second", tmp_path / "second", Path("freecad"), "", cache_dir=cache)
    assert report["cacheHit"] is True


@pytest.mark.parametrize("damage", ["model", "descriptor", "physics", "missing", "extra", "symlink", "manifest_array", "manifest_null", "files_array", "descriptor_array", "physics_null", "entry_file"])
def test_corrupt_or_incomplete_cache_is_rebuilt(compiler, tmp_path, damage):
    package, _, _, authoring = compiler
    authoring["physics"] = {}
    cache = tmp_path / "cache"
    prepare_assets.prepare(package.name, tmp_path / "first", Path("freecad"), "", cache_dir=cache)
    assets = cache / "fixture/assets"
    if damage == "model": (assets / "primary.usdz").write_bytes(b"corrupt")
    elif damage == "descriptor": (assets / "primary.model.json").write_text('{"modelSHA256":"wrong"}')
    elif damage == "physics": (assets / "primary.physics.json").write_text('{"sourceSHA256":"wrong"}')
    elif damage == "missing": (assets / "primary.usdz").unlink()
    elif damage == "extra": (assets / "obsolete.usdz").write_bytes(b"obsolete")
    elif damage == "symlink":
        (assets / "primary.usdz").unlink()
        (assets / "primary.usdz").symlink_to(tmp_path / "first/fixture/assets/primary.usdz")
    elif damage == "manifest_array": (cache / "fixture/manifest.json").write_text("[]")
    elif damage == "manifest_null": (cache / "fixture/manifest.json").write_text("null")
    elif damage == "files_array":
        path = cache / "fixture/manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"] = []
        path.write_text(json.dumps(manifest))
    elif damage == "descriptor_array": (assets / "primary.model.json").write_text("[]")
    elif damage == "physics_null": (assets / "primary.physics.json").write_text("null")
    elif damage == "entry_file":
        shutil.rmtree(cache / "fixture")
        (cache / "fixture").write_text("corrupt cache entry")
    report = prepare_assets.prepare(package.name, tmp_path / "second", Path("freecad"), "", cache_dir=cache)
    assert report["cacheHit"] is False
    assert (tmp_path / "second/fixture/assets/primary.usdz").read_bytes() == b"primary.usdz"


def test_removed_authoring_prunes_old_cached_outputs(compiler, tmp_path):
    package, targets, _, authoring = compiler
    cache, out = tmp_path / "cache", tmp_path / "compiled"
    targets["depth-10mm"] = ("depth-10mm.usdz", "depth-10mm.model.json")
    prepare_assets.prepare(package.name, out, Path("freecad"), "", cache_dir=cache)
    del targets["depth-10mm"]
    authoring["physics"] = {}
    prepare_assets.prepare(package.name, out, Path("freecad"), "", cache_dir=cache)
    authoring["physics"] = None
    prepare_assets.prepare(package.name, out, Path("freecad"), "", cache_dir=cache)
    assert {p.name for p in (out / "fixture/assets").iterdir()} == {"primary.usdz", "primary.model.json"}


def test_cache_only_miss_does_not_publish_or_invoke_native_compiler(compiler, tmp_path, monkeypatch):
    package, _, _, _ = compiler
    monkeypatch.setattr(prepare_assets, "_run_build", lambda *args: pytest.fail("cache-only invoked FreeCAD"))
    with pytest.raises(RuntimeError, match="cache"):
        prepare_assets.prepare(package.name, tmp_path / "compiled", Path("freecad"), "", cache_dir=tmp_path / "empty", cache_only=True)
    assert not (tmp_path / "compiled/fixture/assets").exists()


def test_compiler_and_audit_changes_invalidate_cached_models(compiler, tmp_path, monkeypatch):
    package, _, _, _ = compiler
    cache = tmp_path / "cache"
    prepare_assets.prepare(package.name, tmp_path / "first", Path("freecad"), "", cache_dir=cache)
    audit = prepare_assets.REPOSITORY / "Tools/HangboardCAD/display_depth_audits.json"
    audit.parent.mkdir(parents=True)
    audit.write_text('{"changed":true}')
    report = prepare_assets.prepare(package.name, tmp_path / "second", Path("freecad"), "", cache_dir=cache)
    assert report["cacheHit"] is False
    helper = prepare_assets.REPOSITORY / "Tools/HangboardPackages/src/hangboard_packages/helper.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("# changed runtime validation\n")
    report = prepare_assets.prepare(package.name, tmp_path / "third", Path("freecad"), "", cache_dir=cache)
    assert report["cacheHit"] is False


def test_fingerprint_includes_helpers_under_a_tests_parent_and_ignores_installed_metadata(tmp_path, monkeypatch):
    repository = tmp_path / "tests/repository"
    helper = repository / "Tools/HangboardCAD/helper.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("# original compiler helper\n")
    monkeypatch.setattr(prepare_assets, "REPOSITORY", repository)
    original = prepare_assets.compiler_fingerprint()
    metadata = repository / "Tools/HangboardPackages/src/package.egg-info/dependencies.txt"
    metadata.parent.mkdir(parents=True)
    metadata.write_text("installed metadata\n")
    assert prepare_assets.compiler_fingerprint() == original
    helper.write_text("# changed compiler helper\n")
    assert prepare_assets.compiler_fingerprint() != original


def test_boards_compile_concurrently_in_separate_directories(compiler, tmp_path, monkeypatch):
    package, _, build, _ = compiler
    (package.parent / "second.FCStd").write_bytes(b"second source")
    barrier = threading.Barrier(2, timeout=3)
    def simultaneous_build(*args):
        barrier.wait()
        build(*args)
    monkeypatch.setattr(prepare_assets, "_run_build", simultaneous_build)
    freecad = tmp_path / "freecad"
    freecad.touch()
    subprocess.run(["git", "init", "-q", str(prepare_assets.REPOSITORY)], check=True)
    subprocess.run(["git", "-C", str(prepare_assets.REPOSITORY), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-q", "--allow-empty", "-m", "fixture"], check=True)
    out = tmp_path / "compiled"
    assert prepare_assets.main(["--out", str(out), "--freecad", str(freecad), "--jobs", "2"]) == 0
    assert (out / "fixture/assets/primary.usdz").read_bytes() == b"primary.usdz"
    assert (out / "second/assets/primary.usdz").read_bytes() == b"primary.usdz"


def test_shards_cover_new_boards_once_without_moving_existing_boards():
    initial = ["first", "second", "third"]
    shards = [prepare_assets.shard_packages(initial, index, 4) for index in range(4)]
    added = [prepare_assets.shard_packages(initial + ["new-board"], index, 4) for index in range(4)]
    assert sorted(package for shard in added for package in shard) == ["first", "new-board", "second", "third"]
    assert [[package for package in shard if package != "new-board"] for shard in added] == shards


def test_cancellation_reaps_native_process_before_removing_scratch(compiler, tmp_path):
    package, _, _, _ = compiler
    pid_file = tmp_path / "native.pid"
    freecad = tmp_path / "freecad"
    freecad.write_text(f"#!{sys.executable}\nimport os,time\nfrom pathlib import Path\nPath({str(pid_file)!r}).write_text(str(os.getpid()))\ntime.sleep(60)\n")
    freecad.chmod(0o755)
    launcher = tmp_path / "launch.py"
    launcher.write_text(
        "import sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(Path(prepare_assets.__file__).parent)!r})\n"
        "import prepare_assets as compiler\n"
        f"compiler.REPOSITORY = Path({str(prepare_assets.REPOSITORY)!r})\n"
        "compiler.source_targets = lambda source: {'primary': ('primary.usdz', 'primary.model.json')}\n"
        "compiler.cad_source.load_rope_physics_authoring = lambda source: None\n"
        "compiler.cad_source.load_suspension_authoring = lambda source: None\n"
        f"raise SystemExit(compiler.main(['--out', {str(tmp_path / 'compiled')!r}, '--freecad', {str(freecad)!r}, '--jobs', '2']))\n"
    )
    process = subprocess.Popen([sys.executable, str(launcher)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 10
        while not pid_file.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert pid_file.is_file()
        native_pid = int(pid_file.read_text())
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 130, (stdout, stderr)
        with pytest.raises(ProcessLookupError):
            os.kill(native_pid, 0)
        assert list((prepare_assets.REPOSITORY / ".context").glob("*-prepare-*")) == []
        assert not (tmp_path / "compiled/fixture/assets").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_empty_cached_shard_skips_native_setup_and_installs_successfully(tmp_path):
    repository = tmp_path / "repository"
    source_repository = Path(prepare_assets.__file__).resolve().parents[2]
    for relative in ["scripts/build-board-assets.sh", "Tools/HangboardCAD/prepare_assets.py",
                     "Tools/HangboardCAD/presentation_targets.py", "Tools/HangboardCAD/use_hangboard_packages.py"]:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_repository / relative, path)
    shutil.copytree(source_repository / "Tools/HangboardPackages/src", repository / "Tools/HangboardPackages/src")
    (repository / "Hangboards").mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-q", "--allow-empty", "-m", "fixture"], check=True)
    report = repository / ".context/reports/shard-0.json"
    result = subprocess.run(["bash", str(repository / "scripts/build-board-assets.sh"),
                             "--shard-index", "0", "--shard-count", "8", "--report", str(report)], cwd=repository,
                            env={**os.environ, "HANGBOARD_PYTHON": sys.executable,
                                 "HANGTEN_CAD_CACHE_DIR": str(repository / ".context/cache"),
                                 "HANGTEN_FREECAD_CMD": str(repository / "missing-freecad")},
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(report.read_text())["prepared"] == []
    assert json.loads(report.read_text())["failures"] == []
    assert list((repository / ".context").glob("*-board-build.*")) == []
