#!/usr/bin/env bash
# End-to-end smoke: factory tests, then build both sample specs (each build runs the
# generated app's own tests and must PASS the proof gate), lint the generated code,
# and exercise the generated programs for real.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
if [[ "$PY" == */* ]]; then PY="$(cd "$(dirname "$PY")" && pwd)/$(basename "$PY")"; fi
if [ "${SKIP_INSTALL:-0}" != "1" ]; then
  "$PY" -m pip install -q -e ".[dev]"
fi
OUT="$(mktemp -d)"
trap 'kill "${SERVER_PID:-}" 2>/dev/null || true; rm -rf "$OUT"' EXIT

"$PY" -m ruff check src tests
"$PY" -m pytest -q

"$PY" -m app_factory.cli build --spec examples/sample-spec.md --out "$OUT/sample-todo"
"$PY" -m app_factory.cli build --spec examples/inventory-cli.md --out "$OUT/shop-inventory"
"$PY" -m app_factory.cli prove "$OUT/sample-todo"
"$PY" -m app_factory.cli prove "$OUT/shop-inventory"
(cd "$OUT/sample-todo" && "$PY" -m ruff check .)
(cd "$OUT/shop-inventory" && "$PY" -m ruff check .)

# Generated CLI: add a record, read it back.
PYTHONPATH="$OUT/shop-inventory/src" "$PY" -m shop_inventory --db "$OUT/shop.db" \
  product add --name Widget --sku W-1 --quantity 4 --price 2.5 --in-stock yes
PYTHONPATH="$OUT/shop-inventory/src" "$PY" -m shop_inventory --db "$OUT/shop.db" product list \
  | grep -q '"sku": "W-1"'

# Generated API: start it, create a task over HTTP, read it back.
PORT="$("$PY" -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])")"
PYTHONPATH="$OUT/sample-todo/src" "$PY" -m sample_todo --port "$PORT" --db "$OUT/todo.db" &
SERVER_PID=$!
for _ in $(seq 1 50); do
  "$PY" - "$PORT" <<'PYEOF' && break || sleep 0.2
import sys, urllib.request
urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/health", timeout=1)
PYEOF
done
"$PY" - "$PORT" <<'PYEOF'
import json, sys, urllib.request
base = f"http://127.0.0.1:{sys.argv[1]}"
body = json.dumps({"title": "Smoke", "done": False, "priority": 1, "due_date": "2026-11-02"}).encode()
req = urllib.request.Request(f"{base}/tasks", data=body, method="POST", headers={"Content-Type": "application/json"})
created = json.loads(urllib.request.urlopen(req, timeout=5).read())
items = json.loads(urllib.request.urlopen(f"{base}/tasks", timeout=5).read())["items"]
assert items == [created], items
print("api smoke ok:", created)
PYEOF

# The gate must refuse a broken app.
"$PY" -m app_factory.cli build --spec examples/sample-spec.md --out "$OUT/broken" --no-verify >/dev/null || true
sed -i.bak 's/return cur.rowcount > 0/return True/' "$OUT/broken/src/sample_todo/store.py"
rm -f "$OUT/broken/src/sample_todo/store.py.bak"
if "$PY" -m app_factory.cli verify "$OUT/broken" >/dev/null; then
  echo "gate accepted a broken app" >&2
  exit 1
fi
echo "app-factory-studio smoke PASS"
