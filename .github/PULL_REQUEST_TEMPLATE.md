## What changed

<!-- One or two paragraphs describing the change. -->
<!-- List the user-visible behaviour change in one sentence first. -->

## How I verified

<!-- Paste the exact commands and their output. -->

- [ ] `python -m ruff check src tests` exits 0
- [ ] `python -m pytest -q --cov` reports the new coverage and exits 0
- [ ] `bash scripts/smoke.sh` ends with `app-factory-studio smoke PASS`
- [ ] If templates changed: re-built both `examples/*.md` and proved them
- [ ] If pyproject changed: `pip install -e '.[dev]'` from a fresh venv

## Boundary impact

<!-- Public boundary check per docs/public-boundary.md. -->

- [ ] No PII, secrets, customer data, or internal paths added
- [ ] No banned words (unlock, empower, synergy, leverage, disrupt, hustle,
  utilize, iterate, optimize) in the diff
- [ ] No machine paths like `/Users/...` or `~/Developer/...` left in tracked files
