"""app-factory CLI: spec -> plan -> generated app -> its tests run -> proof gate.

Commands
  plan       print the normalized plan for a spec (no files written)
  build      generate the app, run its tests, seal proofs/proof.json; exit 0 only on PASS
  init       same as build (kept for the original interface)
  verify     re-run a generated app's tests and re-seal the proof
  prove      check the sealed proof against the files on disk (no test run)
  templates  list available templates
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .gate import GateError, prove, verify, write_app
from .spec import SpecError, parse_spec
from .templates import TEMPLATE_DESCRIPTIONS

EXIT_OK, EXIT_GATE_FAILED, EXIT_BAD_INPUT = 0, 1, 2


def _emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _read_spec(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.spec == "-":
        return sys.stdin.read()
    return Path(args.spec).read_text(encoding="utf-8")


def _spec_args(p: argparse.ArgumentParser) -> None:
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--spec", help="spec file ('-' reads stdin)")
    src.add_argument("--text", help="spec paragraph given inline")
    p.add_argument("--template", choices=sorted(TEMPLATE_DESCRIPTIONS), help="override template choice")


def cmd_plan(args: argparse.Namespace) -> int:
    plan = parse_spec(_read_spec(args), args.template)
    _emit(plan.to_dict())
    return EXIT_OK


def cmd_build(args: argparse.Namespace) -> int:
    plan = parse_spec(_read_spec(args), args.template)
    out = Path(args.out or plan.name)
    manifest = write_app(plan, out)
    report = {
        "app": plan.name,
        "template": plan.template,
        "out": str(out),
        "files": len(manifest["files"]),
        "expected_tests": manifest["expected_tests"],
        "tree_sha256": manifest["tree_sha256"],
        "assumptions": plan.assumptions,
    }
    if args.no_verify:
        _emit({**report, "ok": False, "verdict": "UNVERIFIED",
               "note": "tests not run (--no-verify); this is not a success. Run app-factory verify."})
        return EXIT_GATE_FAILED
    proof = verify(out)
    ok = proof["verdict"] == "PASS"
    _emit({**report, "ok": ok, "verdict": proof["verdict"], "pytest_summary": proof["pytest_summary"],
           "reasons": proof["reasons"], **({} if ok else {"output_tail": proof.get("output_tail", "")})})
    return EXIT_OK if ok else EXIT_GATE_FAILED


def cmd_verify(args: argparse.Namespace) -> int:
    proof = verify(Path(args.path))
    ok = proof["verdict"] == "PASS"
    _emit({"ok": ok, **proof})
    return EXIT_OK if ok else EXIT_GATE_FAILED


def cmd_prove(args: argparse.Namespace) -> int:
    result = prove(Path(args.path), allow_modified=args.allow_modified)
    _emit(result)
    return EXIT_OK if result["ok"] else EXIT_GATE_FAILED


def cmd_templates(args: argparse.Namespace) -> int:
    _emit(TEMPLATE_DESCRIPTIONS)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app-factory", description="Spec paragraph to tested app, behind a proof gate.")
    p.add_argument("--version", action="version", version=f"app-factory {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("plan", help="print the plan for a spec")
    _spec_args(pl)
    pl.set_defaults(func=cmd_plan)

    for name in ("build", "init"):
        b = sub.add_parser(name, help="generate, test and prove an app")
        _spec_args(b)
        b.add_argument("--out", help="output directory (default: the app name)")
        b.add_argument("--no-verify", action="store_true", help="write files only; exits 1 (unverified)")
        b.set_defaults(func=cmd_build)

    v = sub.add_parser("verify", help="re-run a generated app's tests and reseal the proof")
    v.add_argument("path")
    v.set_defaults(func=cmd_verify)

    pr = sub.add_parser("prove", help="check the sealed proof")
    pr.add_argument("path")
    pr.add_argument("--allow-modified", action="store_true", help="accept files edited after generation")
    pr.set_defaults(func=cmd_prove)

    t = sub.add_parser("templates", help="list templates")
    t.set_defaults(func=cmd_templates)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (SpecError, GateError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return EXIT_BAD_INPUT


if __name__ == "__main__":
    raise SystemExit(main())
