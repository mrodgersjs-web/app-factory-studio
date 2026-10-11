import json
from pathlib import Path

from app_factory.cli import main


def test_init_and_prove(tmp_path: Path):
    spec = tmp_path / "spec.md"
    spec.write_text("# demo\ntitle: demo-app\nEach item has a name (text) and a count (int).\n")
    out = tmp_path / "out"
    assert main(["init", "--spec", str(spec), "--out", str(out)]) == 0
    assert (out / "proofs" / "proof.json").exists()
    assert main(["prove", str(out)]) == 0


def test_plan_prints_json(capsys):
    assert main(["plan", "--text", "A command line tool. Each pet has a name and an age."]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["template"] == "cli"
    assert [f["name"] for f in plan["entities"][0]["fields"]] == ["name", "age"]


def test_templates_lists_both(capsys):
    assert main(["templates"]) == 0
    assert sorted(json.loads(capsys.readouterr().out)) == ["cli", "rest-api"]
