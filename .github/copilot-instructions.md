# app-factory-studio

Turns a short plain-English spec paragraph into a generated, tested Python app
behind a fail-closed proof gate. `app-factory` reads the spec, writes a plan
with fixed rules (no model calls, so the same spec always gives the same
files), writes a working Python app plus its own test suite, runs those tests,
and reports success only when every generated test passes. The result is
sealed in `proofs/proof.json`.

## Layout

- `src/` - the generator, plan rules, runner and proof gate.
- `tests/` - pytest suite for the generator and the gate.
- `examples/` - specs and generated-app examples. `docs/` - design notes.
- `scripts/smoke.sh` - the end-to-end run CI does. `mcp/` - MCP surface.

## Setup and test (exact commands)

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
bash scripts/smoke.sh
```

The end-to-end proof is `bash scripts/smoke.sh`: it generates an app from a
spec, runs the generated tests, and only then reports success.

## Lint

```bash
python -m ruff check src tests
```

Generated code is linted too. Keep the check clean before a PR.

## Conventions

- Conventional commit subjects (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Every change ships a test that can fail; generation is deterministic, so a
  test that pins output is legitimate, but it must assert real values.
- No secrets, tokens or credentials in tracked files. No machine-specific
  paths (`/Users/...`, `~/Developer/...`) in tracked files.
- Numbers in docs and README must come from a command you ran; quote the
  command, not a remembered figure. If a number changes, re-run the command.
