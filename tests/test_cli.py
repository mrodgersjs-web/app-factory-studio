from pathlib import Path
from app_factory.cli import main

def test_init_and_prove(tmp_path: Path):
    spec = tmp_path / "spec.md"
    spec.write_text("# demo\ntitle: demo-app\n")
    out = tmp_path / "out"
    assert main(["init", "--spec", str(spec), "--out", str(out)]) == 0
    assert (out / "proofs" / "init.json").exists()
    assert main(["prove", str(out)]) == 0
