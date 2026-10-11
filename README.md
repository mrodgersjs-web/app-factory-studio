# app-factory-studio

[![ci](https://github.com/mrodgersjs-web/app-factory-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/mrodgersjs-web/app-factory-studio/actions/workflows/ci.yml)

> Spec paragraph to a generated, tested app, behind a proof gate.

![app-factory-studio](assets/app-factory-studio-hero.png)

`app-factory` reads a short plain-English spec, turns it into a plan with fixed rules
(no model calls, so the same spec always gives the same files), writes a working
Python app plus its own test suite, runs those tests, and only reports success if
every generated test passes. The result is sealed in `proofs/proof.json`.

## Proof in 60 seconds

```bash
git clone https://github.com/mrodgersjs-web/app-factory-studio.git
cd app-factory-studio
python3 -m pip install -e ".[dev]"
app-factory build --spec examples/sample-spec.md --out /tmp/sample-todo
app-factory prove /tmp/sample-todo
bash scripts/smoke.sh        # the same end-to-end run CI does
```

`build` prints a report like this (from a real run of the sample spec):

```json
{
  "app": "sample-todo",
  "assumptions": ["task.due_date: type 'date' inferred from the field name"],
  "expected_tests": 19,
  "ok": true,
  "pytest_summary": "19 passed",
  "template": "rest-api",
  "verdict": "PASS"
}
```

## Writing a spec

A spec is a paragraph (file, `--text`, or stdin with `--spec -`):

```text
# sample-todo

A small offline todo API for a team. Each task has a title (text), done (bool),
a priority (int), a due date and optional notes (text).
```

Rules the parser follows:

| Spec text | Effect |
| --- | --- |
| `# Heading`, `title:` or `name:` | app name (otherwise `<entity>-api` / `<entity>-cli`) |
| `Each <entity> has <field>, <field> and <field>.` (also `every`, `stores`, `tracks`, ...) | an entity and its fields |
| `entity: room(label: text, capacity: int)` | the same, as one line |
| `(text)`, `(int)`, `(float)`, `(bool)`, `(date)` and aliases such as `decimal`, `boolean`, `number` | field type |
| no type given | type inferred from the name (`is_*`/`done` bool, `*_date`/`due` date, `quantity`/`*_count` int, `price`/`*_amount` float, else text), listed under `assumptions` |
| `optional` before a field or inside the brackets | field may be empty |
| `template: cli` / `template: rest-api`, or `--template` | template choice |
| words like "command line", "cli", "terminal" | `cli` template |
| words like "api", "rest", "http", "service" | `rest-api` template (also the default, recorded as an assumption) |

Specs that cannot become an app are refused with a reason and exit code 2: no
entities, unknown types, duplicate fields, a field named `id` or `help`, an entity
with no required field, an unknown template.

## Templates

| Template | What you get |
| --- | --- |
| `rest-api` | JSON CRUD HTTP service on `http.server` + `sqlite3`: `GET /health`, `GET/POST /<plural>` with `?field=value` filters, `GET/PUT/PATCH/DELETE /<plural>/<id>`, 400 with per-field errors, 404s. Tests start a real server on a free port. |
| `cli` | `argparse` CRUD tool on `sqlite3`: `<entity> add/list/show/update/delete`, JSON output, exit codes 0 ok / 1 not found / 2 invalid input. Tests drive `main()` and run the program as a module. |

Both share a schema with validation and type coercion, and a SQLite store with
create/get/list/update/delete. Generated apps use only the standard library;
their tests need pytest. Each generated app has a README, `pyproject.toml` with a
console script, and a ruff config; CI lints the generated code too.

## The proof gate

| Command | What it does | Exit |
| --- | --- | --- |
| `app-factory plan --spec F` | print the plan (entities, types, template, assumptions) | 0, or 2 for a bad spec |
| `app-factory build --spec F --out D` | write the app and `app-factory.json` (sha256 of every file), run the app's tests, write `proofs/proof.json` | 0 only on PASS, 1 on FAIL, 2 bad input |
| `app-factory build ... --no-verify` | write files only | always 1: unverified is not success |
| `app-factory verify D` | re-run the tests and re-seal the proof | 0 PASS / 1 FAIL |
| `app-factory prove D` | check the sealed proof without running tests | 0 / 1 |
| `app-factory templates` | list templates | 0 |

PASS needs all of: pytest exit 0, no failures or errors, and exactly as many passing
tests as the factory generated (deleting or skipping tests fails the gate).
`prove` also fails if any file changed since the proof was sealed, or differs from
the generation manifest (allow hand edits with `--allow-modified` after a fresh
`verify`). `init` is kept as an alias of `build`. `build` refuses to write into a
non-empty directory it did not create.

## Development

```bash
python3 -m pip install -e ".[dev]"
python -m ruff check src tests
python -m pytest -q
bash scripts/smoke.sh
```

The factory's tests build both sample specs end to end, check that two builds are
byte-identical, start the generated API and call it over HTTP, run the generated
CLI, and check that a deliberately broken app, deleted tests, an unverified build
and an edited app are all refused.

## Layout

```text
src/app_factory/spec.py         spec text -> Plan (rules, refusals, assumptions)
src/app_factory/render.py       Plan -> {path: text}, sample data for tests
src/app_factory/templates/      common (schema, store, tests), rest_api, cli_app
src/app_factory/gate.py         write app + manifest, run tests, seal / check proof
src/app_factory/cli.py          the app-factory command
examples/                       sample specs used by tests and CI
```

## Roadmap

Not built yet:

- More templates (for example a web UI or a background worker) and non-Python targets.
- Relationships between entities (foreign keys) and uniqueness constraints.
- Field rules such as ranges, lengths and email format.
- A results MCP server is included at `mcp/server.py`; its `score` and
  `request_effect` tools depend on an external `rig-loop` tool that is not part of
  this repo, so only `results` works standalone.

## Public boundary

See [docs/public-boundary.md](docs/public-boundary.md). Examples are synthetic.

## Video walkthrough

- Script: [`docs/video-script.md`](docs/video-script.md)
- Recording: [`assets/demo.mp4`](assets/demo.mp4) (recorded for the earlier scaffold-only version)
- Preview: [`assets/demo.gif`](assets/demo.gif)

## Related

[proof-studio](https://github.com/mrodgersjs-web/proof-studio) · [fde-portfolio](https://github.com/mrodgersjs-web/fde-portfolio) · [profile](https://github.com/mrodgersjs-web)
