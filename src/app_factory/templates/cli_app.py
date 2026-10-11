"""Template ``cli``: an argparse CRUD command-line tool backed by SQLite."""

from __future__ import annotations

import json
import textwrap

from ..render import cli_value, sample
from ..spec import Plan
from .common import fill, header, pyproject, readme, sample_constants

CLI_PY = '''"""Command-line interface for __NAME__ (standard library only).

  __NAME__ [--db FILE] <entity> add --field value ...
  __NAME__ [--db FILE] <entity> list [--field value ...]
  __NAME__ [--db FILE] <entity> show ID
  __NAME__ [--db FILE] <entity> update ID --field value ...
  __NAME__ [--db FILE] <entity> delete ID

Output is JSON on stdout. Exit codes: 0 ok, 1 not found, 2 invalid input.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import models
from .store import Store

DB_ENV = "__ENV___DB"
DESCRIPTION = __DESCRIPTION__


def _option(name: str) -> str:
    return "--" + name.replace("_", "-")


def _add_field_options(parser: argparse.ArgumentParser, entity: str, verb: str) -> None:
    for f in models.fields(entity):
        need = " (required)" if f["required"] and verb == "set" else ""
        parser.add_argument(
            _option(f["name"]),
            dest=f"field_{f['name']}",
            metavar=f["type"].upper(),
            help=f"{verb} {f['name']} ({f['type']}){need}",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="__NAME__", description=DESCRIPTION)
    parser.add_argument(
        "--db",
        default=os.environ.get(DB_ENV, "__PKG__.db"),
        help=f"SQLite file (default: ${DB_ENV} or __PKG__.db)",
    )
    entities = parser.add_subparsers(dest="entity", required=True)
    for entity in models.entity_names():
        ep = entities.add_parser(entity, help=f"manage {models.SCHEMA[entity]['plural']}")
        actions = ep.add_subparsers(dest="action", required=True)
        _add_field_options(actions.add_parser("add", help=f"create a {entity}"), entity, "set")
        _add_field_options(actions.add_parser("list", help="list, optionally filtered"), entity, "filter by")
        actions.add_parser("show", help=f"show one {entity}").add_argument("id", type=int)
        upd = actions.add_parser("update", help=f"change fields of a {entity}")
        upd.add_argument("id", type=int)
        _add_field_options(upd, entity, "set")
        actions.add_parser("delete", help=f"delete a {entity}").add_argument("id", type=int)
    return parser


def _given(args: argparse.Namespace, entity: str) -> dict:
    values = {}
    for f in models.fields(entity):
        value = getattr(args, f"field_{f['name']}", None)
        if value is not None:
            values[f["name"]] = value
    return values


def _emit(payload: object) -> None:
    print(json.dumps(payload, sort_keys=True))


def run(args: argparse.Namespace, store: Store) -> int:
    entity, action = args.entity, args.action
    if action == "add":
        _emit(store.create(entity, _given(args, entity)))
        return 0
    if action == "list":
        _emit(store.list(entity, _given(args, entity) or None))
        return 0
    if action == "show":
        item = store.get(entity, args.id)
    elif action == "update":
        item = store.update(entity, args.id, _given(args, entity))
    else:
        item = {"deleted": args.id} if store.delete(entity, args.id) else None
    if item is None:
        print(json.dumps({"error": f"{entity} {args.id} not found"}), file=sys.stderr)
        return 1
    _emit(item)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = Store(args.db)
    try:
        return run(args, store)
    except models.ValidationError as exc:
        print(json.dumps({"error": "validation failed", "fields": exc.errors}, sort_keys=True), file=sys.stderr)
        return 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
'''

MAIN_PY = '''from .cli import main

raise SystemExit(main())
'''

TEST_CLI_HEAD = '''"""CLI tests (generated). Each test drives main() against a temporary SQLite file."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from __PKG__.cli import main

SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture
def run(tmp_path, capsys):
    db = str(tmp_path / "cli.db")

    def _run(*argv):
        code = main(["--db", db, *argv])
        captured = capsys.readouterr()
        out = json.loads(captured.out) if captured.out.strip() else None
        err = json.loads(captured.err) if captured.err.strip() else None
        return code, out, err

    return _run


def args_for(data):
    argv = []
    for name, value in data.items():
        text = ("true" if value else "false") if isinstance(value, bool) else str(value)
        argv += ["--" + name.replace("_", "-"), text]
    return argv


def test_runs_as_module(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "__PKG__", "--db", str(tmp_path / "m.db"), "__FIRST__", "list"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(SRC), "PATH": ""},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == []


def test_unknown_command_exits_2():
    with pytest.raises(SystemExit) as info:
        main(["no-such-entity", "list"])
    assert info.value.code == 2
'''


def render_test_cli(plan: Plan) -> str:
    subs = header(plan)
    subs["__FIRST__"] = plan.entities[0].name
    out = [fill(TEST_CLI_HEAD, subs), sample_constants(plan)]
    for e in plan.entities:
        n, up = e.name, e.name.upper()
        out.append(f'''
def test_{n}_cli_add_list_show(run):
    code, created, _ = run("{n}", "add", *args_for({up}_A))
    assert code == 0
    assert {{k: created[k] for k in {up}_A}} == {up}_A
    assert run("{n}", "list") == (0, [created], None)
    assert run("{n}", "show", str(created["id"])) == (0, created, None)


def test_{n}_cli_filter(run):
    run("{n}", "add", *args_for({up}_A))
    _, b, _ = run("{n}", "add", *args_for({up}_B))
    flag = "--" + {up}_KEY.replace("_", "-")
    code, items, _ = run("{n}", "list", flag, {up}_KEY_TEXT_B)
    assert code == 0
    assert [r["id"] for r in items] == [b["id"]]


def test_{n}_cli_update_delete(run):
    _, created, _ = run("{n}", "add", *args_for({up}_A))
    item_id = str(created["id"])
    code, updated, _ = run("{n}", "update", item_id, *args_for({{{up}_KEY: {up}_B[{up}_KEY]}}))
    assert code == 0
    assert updated[{up}_KEY] == {up}_B[{up}_KEY]
    assert run("{n}", "delete", item_id) == (0, {{"deleted": created["id"]}}, None)
    assert run("{n}", "show", item_id)[0] == 1


def test_{n}_cli_invalid_input_exits_2(run):
    code, out, err = run("{n}", "add", *args_for({up}_BAD))
    assert code == 2
    assert out is None
    assert sorted(err["fields"]) == sorted({up}_BAD)
    assert run("{n}", "list") == (0, [], None)


def test_{n}_cli_missing_record_exits_1(run):
    code, out, err = run("{n}", "show", "999")
    assert code == 1
    assert out is None
    assert "not found" in err["error"]
''')
    return "\n".join(out).rstrip() + "\n"


def usage(plan: Plan) -> str:
    e = plan.entities[0]
    flags = " ".join(f"--{k.replace('_', '-')} {cli_value(v)!r}" for k, v in sample(e, 0).items())
    key = e.fields[0].name
    return f"""```bash
pip install -e .
{plan.name} --db {plan.package}.db {e.name} add {flags}
{plan.name} --db {plan.package}.db {e.name} list --{key.replace('_', '-')} {cli_value(sample(e, 0)[key])!r}
{plan.name} --db {plan.package}.db {e.name} update 1 --{key.replace('_', '-')} {cli_value(sample(e, 1)[key])!r}
{plan.name} --db {plan.package}.db {e.name} delete 1
# or without installing: PYTHONPATH=src python -m {plan.package} {e.name} list
```

Entities: {", ".join(f"`{x.name}`" for x in plan.entities)}. Each has `add`, `list`, `show`,
`update` and `delete`. Output is JSON. Exit codes: 0 ok, 1 not found, 2 invalid input.
The database path can also come from `${plan.package.upper()}_DB`."""


def wrapped_string(text: str) -> str:
    """A string literal that stays under the line limit, split into parts if needed."""
    if len(text) <= 80:
        return json.dumps(text)
    parts = textwrap.wrap(text, 72, drop_whitespace=False)
    return "(\n" + "\n".join(f"    {json.dumps(p)}" for p in parts) + "\n)"


def render(plan: Plan) -> dict[str, str]:
    subs = header(plan)
    subs["__ENV__"] = plan.package.upper()
    subs["__DESCRIPTION__"] = wrapped_string(plan.description)
    pkg = f"src/{plan.package}"
    return {
        f"{pkg}/cli.py": fill(CLI_PY, subs),
        f"{pkg}/__main__.py": MAIN_PY,
        "tests/test_cli.py": render_test_cli(plan),
        "pyproject.toml": pyproject(plan, "cli"),
        "README.md": readme(plan, usage(plan)),
    }
