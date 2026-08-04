#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m pip install -e ".[test]" -q
pytest -q
rm -rf /tmp/app-factory-smoke-out
app-factory init --spec examples/sample-spec.md --out /tmp/app-factory-smoke-out
app-factory prove /tmp/app-factory-smoke-out
echo "app-factory-studio smoke PASS"
