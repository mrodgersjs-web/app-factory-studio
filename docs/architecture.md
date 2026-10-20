# Architecture — App Factory Studio

## One-liner
Spec paragraph to a generated, tested app behind a proof gate.

## What this is

`app-factory` is a small, deterministic CLI. You give it a paragraph; it
gives you a folder with a working Python app plus a pytest suite, and a
sealed `proofs/proof.json` proving the suite passed.

There is no model call. Every step is rule-based and pure, so two builds
of the same spec are byte-identical (verified by `test_generation_is_deterministic`).

## Flow

```
spec text
  -> spec.parse_spec        rule-based parser; refuses bad specs; records assumptions
  -> Plan                   name, template, entities, fields, spec sha256
  -> render.render          {path: text}; pure function of the Plan
  -> gate.write_app         files + app-factory.json (sha256 per file, tree hash, expected test count)
  -> gate.verify            runs the generated app's pytest suite (subprocess, this Python)
  -> proofs/proof.json      PASS only if exit 0, no failures, passed == expected
  -> gate.prove             proof PASS + tree unchanged (+ matches manifest)
```

## Why fail-closed

A scaffolder that says "your app is built" while the tests failed is worse
than no scaffolder. The rules:

1. Build exit code is 0 only when every generated test passes.
2. PASS requires `pytest exit 0`, zero failures or errors, and exactly as
   many passing tests as the factory generated. Deleting or skipping
   tests fails the gate.
3. `prove` requires a PASS proof whose tree hash equals the files on disk
   now, and (unless `--allow-modified`) that the files match the original
   generation manifest.
4. `--no-verify` makes `build` exit 1. An unverified build is never reported
   as success; the operator must run `app-factory verify` to seal a proof.

## What the parser does

`spec.parse_spec(text, template_override=None) -> Plan` is a rule-based
regex parser. The grammar (case-insensitive):

| Spec text | Effect |
| --- | --- |
| `# Heading`, `title:`, `name:` | app name (otherwise `<entity>-api` / `<entity>-cli`) |
| `each <entity> has <field>, <field> and <field>` | one entity and its fields |
| `entity: room(label: text, capacity: int)` | the same, as one line |
| `(text)`, `(int)`, `(float)`, `(bool)`, `(date)` and aliases | field type |
| no type given | type inferred from the name; recorded under `assumptions` |
| `optional` before a field or in brackets | field may be empty |
| `template: cli` / `template: rest-api`, or `--template` | template choice |
| words like "command line", "cli", "terminal" | `cli` template |
| words like "api", "rest", "http", "service" | `rest-api` template (also the default) |

Bad specs are refused with a reason and exit code 2: no entities,
unknown types, duplicate fields, a field named `id` or `help`, an entity
with no required field, an unknown template.

## Templates

| Template | What you get |
| --- | --- |
| `rest-api` | JSON CRUD HTTP service on `http.server` + `sqlite3`: `GET /health`, `GET/POST /<plural>` with `?field=value` filters, `GET/PUT/PATCH/DELETE /<plural>/<id>`, 400 with per-field errors, 404s. Tests start a real server on a free port. |
| `cli` | `argparse` CRUD tool on `sqlite3`: `<entity> add/list/show/update/delete`, JSON output, exit codes 0 ok / 1 not found / 2 invalid input. Tests drive `main()` and run the program as a module. |

Both share a schema with validation and type coercion, and a SQLite
store with create/get/list/update/delete. Generated apps use only the
standard library; their tests need pytest. Each generated app has a
`README.md`, a `pyproject.toml` with a console script, and a ruff
config; CI lints the generated code too.

## Determinism

No clocks, randomness or model calls in generation. The proof records
test counts and the pytest summary without timings. Two builds of the
same spec are byte-identical (checked in `tests/test_gate.py`). Adding a
clock or a timestamp would break this property, so we don't.

## Trust boundaries

- **Public, synthetic inputs only** in `examples/`. Real PII / customer
  dumps are out of scope; see `docs/public-boundary.md`.
- **Secrets never enter the repo.** A leaked token in a generated file
  would be embarrassing; the gate does not check for secrets in files,
  so we don't accept contributions that contain them.
- **Success claims come only from the gate.** A queued dispatch, a saved
  screenshot, or a green label is not success here; `proofs/proof.json`
  with verdict `PASS` is.
- **The factory is local.** Nothing here executes outward effects. The
  MCP server at `mcp/server.py` only exposes sealed proofs and a Gate-D
  request wrapper; it never sends or writes outside this directory.

## What the tests prove

`tests/test_spec.py` (8 tests): the parser's grammar, inference,
refusals, determinism.

`tests/test_cli.py` (3 tests): the CLI dispatch, plan output, templates
list, and that the program runs end-to-end.

`tests/test_gate.py` (12 tests): two real builds (rest-api and cli),
proof freshness, and refusal patterns.

The factory's tests build both sample specs end to end, check that two
builds are byte-identical, start the generated API and call it over
HTTP, run the generated CLI, and check that a deliberately broken app,
deleted tests, an unverified build and an edited app are all refused.

## Files

| Path | Purpose |
| --- | --- |
| `src/app_factory/spec.py` | spec text -> Plan (rules, refusals, assumptions) |
| `src/app_factory/render.py` | Plan -> `{path: text}`, sample data for tests |
| `src/app_factory/templates/common.py` | shared schema, store, conftest, sample constants |
| `src/app_factory/templates/rest_api.py` | `rest-api` template (HTTP service) |
| `src/app_factory/templates/cli_app.py` | `cli` template (argparse tool) |
| `src/app_factory/gate.py` | write app + manifest, run tests, seal / check proof |
| `src/app_factory/cli.py` | the `app-factory` command |
| `examples/sample-spec.md` | sample for the `rest-api` template |
| `examples/inventory-cli.md` | sample for the `cli` template |
| `scripts/smoke.sh` | the end-to-end check CI runs |

## Public boundary

See [docs/public-boundary.md](docs/public-boundary.md). Examples are synthetic.
