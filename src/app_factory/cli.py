"""app-factory CLI — init scaffold from spec, prove structure exists."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

def _parse_spec(text: str) -> dict:
    title = "app"
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("title:"):
            title = re.sub(r"[^a-zA-Z0-9_-]+", "-", line.split(":", 1)[1].strip()).strip("-").lower() or "app"
            break
        if line.startswith("# "):
            title = re.sub(r"[^a-zA-Z0-9_-]+", "-", line[2:].strip()).strip("-").lower() or "app"
            break
    return {"title": title, "spec_sha256": hashlib.sha256(text.encode()).hexdigest()}

def cmd_init(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    text = spec_path.read_text()
    meta = _parse_spec(text)
    out = Path(args.out or f"scaffold-{meta['title']}")
    (out / "src").mkdir(parents=True, exist_ok=True)
    (out / "tests").mkdir(parents=True, exist_ok=True)
    (out / "proofs").mkdir(parents=True, exist_ok=True)
    (out / "src" / "main.py").write_text(
        f'"""Generated scaffold for {meta["title"]}."""\n\ndef main() -> None:\n    print("ok:{meta["title"]}")\n\n\nif __name__ == "__main__":\n    main()\n'
    )
    (out / "tests" / "test_smoke.py").write_text(
        "from pathlib import Path\nimport runpy\n\ndef test_main_runs(capsys):\n    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'src' / 'main.py'), run_name='__main__')\n    assert 'ok:' in capsys.readouterr().out\n"
    )
    (out / "pyproject.toml").write_text(f'[project]\nname = "{meta["title"]}"\nversion = "0.0.1"\nrequires-python = ">=3.10"\n')
    packet = {"studio": "app-factory", "title": meta["title"], "spec_sha256": meta["spec_sha256"],
              "files": sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())}
    (out / "proofs" / "init.json").write_text(json.dumps(packet, indent=2) + "\n")
    print(json.dumps({"ok": True, "out": str(out), "packet": packet}, indent=2))
    return 0

def cmd_prove(args: argparse.Namespace) -> int:
    root = Path(args.path)
    required = [root/"src"/"main.py", root/"tests"/"test_smoke.py", root/"proofs"/"init.json", root/"pyproject.toml"]
    missing = [str(p) for p in required if not p.exists()]
    print(json.dumps({"ok": not missing, "missing": missing, "path": str(root)}, indent=2))
    return 0 if not missing else 1

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="app-factory")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("--spec", required=True); i.add_argument("--out"); i.set_defaults(func=cmd_init)
    pr = sub.add_parser("prove"); pr.add_argument("path"); pr.set_defaults(func=cmd_prove)
    args = p.parse_args(argv)
    return int(args.func(args))

if __name__ == "__main__":
    raise SystemExit(main())
