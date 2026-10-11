"""End-to-end: spec -> generated app -> its own tests -> proof gate (fail closed)."""

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from app_factory.cli import main
from app_factory.gate import MANIFEST, PROOF, tree_files, tree_hash

ROOT = Path(__file__).resolve().parents[1]
TODO_SPEC = ROOT / "examples" / "sample-spec.md"
CLI_SPEC = ROOT / "examples" / "inventory-cli.md"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def todo_app(tmp_path_factory):
    out = tmp_path_factory.mktemp("apps") / "todo"
    assert main(["build", "--spec", str(TODO_SPEC), "--out", str(out)]) == 0
    return out


@pytest.fixture(scope="module")
def cli_app(tmp_path_factory):
    out = tmp_path_factory.mktemp("apps") / "inventory"
    assert main(["build", "--spec", str(CLI_SPEC), "--out", str(out)]) == 0
    return out


def test_rest_api_build_passes_gate(todo_app):
    proof = read_json(todo_app / PROOF)
    manifest = read_json(todo_app / MANIFEST)
    assert proof["verdict"] == "PASS"
    assert proof["template"] == "rest-api"
    assert proof["tests"]["passed"] == manifest["expected_tests"] > 10
    assert proof["tests"]["failed"] == 0
    assert proof["tree_sha256"] == manifest["tree_sha256"]
    assert {"src/sample_todo/api.py", "src/sample_todo/store.py", "tests/test_api.py"} <= set(manifest["files"])
    assert main(["prove", str(todo_app)]) == 0


def test_cli_build_passes_gate(cli_app):
    proof = read_json(cli_app / PROOF)
    assert proof["verdict"] == "PASS"
    assert proof["template"] == "cli"
    assert proof["tests"]["passed"] == read_json(cli_app / MANIFEST)["expected_tests"]
    assert (cli_app / "tests" / "test_cli.py").exists()
    assert main(["prove", str(cli_app)]) == 0


def test_generation_is_deterministic(tmp_path, todo_app):
    other = tmp_path / "again"
    assert main(["build", "--spec", str(TODO_SPEC), "--out", str(other), "--no-verify"]) == 1
    assert read_json(other / MANIFEST) == read_json(todo_app / MANIFEST)
    for rel in read_json(todo_app / MANIFEST)["files"]:
        assert (other / rel).read_bytes() == (todo_app / rel).read_bytes()


def test_generated_api_serves_real_http(todo_app):
    env = dict(os.environ, PYTHONPATH=str(todo_app / "src"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "sample_todo", "--port", "0", "--db", ":memory:"],
        stdout=subprocess.PIPE, text=True, env=env,
    )
    try:
        line = proc.stdout.readline()
        port = int(re.search(r":(\d+)$", line.strip()).group(1))
        base = f"http://127.0.0.1:{port}"
        body = json.dumps({"title": "Ship it", "done": False, "priority": 1, "due_date": "2026-11-02"}).encode()
        req = urllib.request.Request(f"{base}/tasks", data=body, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 201
            created = json.loads(resp.read())
        assert created["id"] == 1
        assert created["notes"] is None
        with urllib.request.urlopen(f"{base}/tasks?done=false", timeout=10) as resp:
            assert json.loads(resp.read())["items"] == [created]
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_generated_cli_runs_as_program(cli_app, tmp_path):
    env = dict(os.environ, PYTHONPATH=str(cli_app / "src"))
    db = str(tmp_path / "shop.db")
    base = [sys.executable, "-m", "shop_inventory", "--db", db]
    add = subprocess.run(
        [*base, "product", "add", "--name", "Widget", "--sku", "W-1", "--quantity", "4",
         "--price", "2.5", "--in-stock", "yes"],
        capture_output=True, text=True, env=env, check=False,
    )
    assert add.returncode == 0, add.stderr
    assert json.loads(add.stdout)["in_stock"] is True
    bad = subprocess.run([*base, "product", "add", "--name", "X"], capture_output=True, text=True, env=env, check=False)
    assert bad.returncode == 2
    assert "sku" in json.loads(bad.stderr)["fields"]


def test_broken_app_is_refused(tmp_path):
    out = tmp_path / "broken"
    assert main(["build", "--spec", str(TODO_SPEC), "--out", str(out), "--no-verify"]) == 1
    store = out / "src" / "sample_todo" / "store.py"
    store.write_text(store.read_text().replace("return cur.rowcount > 0", "return True"))
    assert main(["verify", str(out)]) == 1
    proof = read_json(out / PROOF)
    assert proof["verdict"] == "FAIL"
    assert proof["tests"]["failed"] >= 1
    assert proof["drift"] == ["src/sample_todo/store.py"]
    assert main(["prove", str(out), "--allow-modified"]) == 1


def test_deleted_tests_do_not_count_as_passing(tmp_path):
    out = tmp_path / "fewer"
    main(["build", "--spec", str(TODO_SPEC), "--out", str(out), "--no-verify"])
    (out / "tests" / "test_api.py").unlink()
    assert main(["verify", str(out)]) == 1
    proof = read_json(out / PROOF)
    assert proof["tests"]["failed"] == 0
    assert any("but the factory generated" in r for r in proof["reasons"])


def test_unverified_build_cannot_be_proven(tmp_path):
    out = tmp_path / "unverified"
    assert main(["build", "--spec", str(TODO_SPEC), "--out", str(out), "--no-verify"]) == 1
    assert main(["prove", str(out)]) == 1


def test_edits_after_proof_break_the_seal(tmp_path, capsys):
    out = tmp_path / "edited"
    assert main(["build", "--spec", str(CLI_SPEC), "--out", str(out)]) == 0
    readme = out / "README.md"
    readme.write_text(readme.read_text() + "\nLocal note.\n")
    capsys.readouterr()
    assert main(["prove", str(out)]) == 1
    assert "files changed since the proof was sealed" in capsys.readouterr().out
    assert main(["verify", str(out)]) == 0
    assert main(["prove", str(out)]) == 1
    assert main(["prove", str(out), "--allow-modified"]) == 0


def test_refuses_to_overwrite_foreign_directory(tmp_path):
    out = tmp_path / "taken"
    out.mkdir()
    (out / "keep.txt").write_text("not ours")
    assert main(["build", "--spec", str(TODO_SPEC), "--out", str(out)]) == 2
    assert (out / "keep.txt").read_text() == "not ours"


def test_bad_spec_exits_2(capsys):
    assert main(["build", "--text", "An app with no entities.", "--out", "/nonexistent/x"]) == 2
    assert "no entities found" in capsys.readouterr().err


def test_tree_hash_ignores_caches_and_proofs(todo_app):
    files = tree_files(todo_app)
    assert not any("__pycache__" in p or p.startswith("proofs/") or p == MANIFEST for p in files)
    assert tree_hash(files) == read_json(todo_app / MANIFEST)["tree_sha256"]
