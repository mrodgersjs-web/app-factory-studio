# Evaluation strategy — App Factory Studio

## Gates
| Gate | Command | Pass |
| --- | --- | --- |
| Lint | `python -m ruff check src tests` | exit 0 |
| Factory tests | `python -m pytest -q` | exit 0 |
| Generated app tests | `app-factory build --spec <spec> --out <dir>` | verdict PASS, exit 0 |
| Sealed proof | `app-factory prove <dir>` | exit 0 |
| End to end | `bash scripts/smoke.sh` | prints `smoke PASS` |

CI runs all of these on Python 3.10 and 3.12 for every push and pull request.

## Failure policy
If smoke fails, README promises are considered false until fixed. The gate is
fail-closed: an unverified, failing, test-deleted or edited app is never reported
as a success.

## Human approval
Required before any outward or customer action in real deployments. This repo only
generates and tests local apps.
