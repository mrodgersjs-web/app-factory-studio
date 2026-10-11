import json
from pathlib import Path

import pytest

from app_factory.cli import main

def test_init_and_prove(tmp_path: Path):
    spec = tmp_path / "spec.md"
    spec.write_text("# demo\ntitle: demo-app\n")
    out = tmp_path / "out"
    assert main(["init", "--spec", str(spec), "--out", str(out)]) == 0
    assert (out / "proofs" / "init.json").exists()
    assert main(["prove", str(out)]) == 0


def _prove_payload(capsys, root: Path) -> tuple[int, dict]:
    rc = main(["prove", str(root)])
    return rc, json.loads(capsys.readouterr().out)


def test_prove_reports_static_scope_for_good_files(tmp_path: Path, capsys):
    spec = tmp_path / "spec.md"
    spec.write_text("# demo\ntitle: demo-app\n")
    out = tmp_path / "out"
    assert main(["init", "--spec", str(spec), "--out", str(out)]) == 0
    capsys.readouterr()

    rc, payload = _prove_payload(capsys, out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["missing"] == []
    assert payload["not_files"] == []
    assert payload["scope"] == "structure-only"
    assert payload["runtime_verified"] is False
    assert payload["runtime_not_verified"] is True


REQUIRED_REL = [
    Path("src/main.py"),
    Path("tests/test_smoke.py"),
    Path("proofs/init.json"),
    Path("pyproject.toml"),
]


def _write_required_files(root: Path) -> None:
    for rel in REQUIRED_REL:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("static structure placeholder\n")


@pytest.mark.parametrize("rel", REQUIRED_REL)
def test_prove_rejects_each_required_path_that_is_a_directory(tmp_path: Path, capsys, rel: Path):
    _write_required_files(tmp_path)
    bad_path = tmp_path / rel
    bad_path.unlink()
    bad_path.mkdir()

    rc, payload = _prove_payload(capsys, tmp_path)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["missing"] == []
    assert payload["not_files"] == [str(bad_path)]
    assert payload["scope"] == "structure-only"
    assert payload["runtime_verified"] is False


@pytest.mark.parametrize("rel", REQUIRED_REL)
def test_prove_reports_each_missing_required_file(tmp_path: Path, capsys, rel: Path):
    _write_required_files(tmp_path)
    missing_path = tmp_path / rel
    missing_path.unlink()

    rc, payload = _prove_payload(capsys, tmp_path)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["missing"] == [str(missing_path)]
    assert payload["not_files"] == []


def test_prove_does_not_execute_runtime_or_tests(tmp_path: Path, capsys):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "proofs").mkdir()
    (tmp_path / "src" / "main.py").write_text("definitely not python !!!\n")
    (tmp_path / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert False\n")
    (tmp_path / "proofs" / "init.json").write_text("not parsed by prove\n")
    (tmp_path / "pyproject.toml").write_text("not parsed by prove\n")

    rc, payload = _prove_payload(capsys, tmp_path)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["scope"] == "structure-only"
    assert payload["runtime_verified"] is False
    assert payload["runtime_not_verified"] is True
