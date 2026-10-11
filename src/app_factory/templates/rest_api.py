"""Template ``rest-api``: a JSON CRUD HTTP service on the standard library."""

from __future__ import annotations

import json

from ..render import pylit, sample
from ..spec import Plan
from .common import fill, header, pyproject, readme, sample_constants

API_PY = '''"""HTTP JSON API for __NAME__ (standard library only).

Routes, for each entity (plural path):
  GET    /health                 status and resource list
  GET    /<plural>?field=value   list records, optional equality filters
  POST   /<plural>               create (201), 400 on validation errors
  GET    /<plural>/<id>          read one, 404 when missing
  PUT    /<plural>/<id>          replace all fields
  PATCH  /<plural>/<id>          change some fields
  DELETE /<plural>/<id>          delete (204)
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

from . import models
from .store import Store

ROUTES = {spec["plural"]: name for name, spec in models.SCHEMA.items()}
MAX_BODY = 1_000_000


class AppHandler(BaseHTTPRequestHandler):
    server_version = "__PKG__/0.1"

    def log_message(self, format: str, *args: object) -> None:
        if getattr(self.server, "verbose", False):
            super().log_message(format, *args)

    def _send(self, status: int, payload: object = None) -> None:
        body = b"" if payload is None else json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _body(self) -> object:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise models.ValidationError({"_": "body too large"})
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw or b"null")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise models.ValidationError({"_": "body must be JSON"}) from None

    def _dispatch(self, method: str) -> None:
        url = urlsplit(self.path)
        parts = [p for p in url.path.split("/") if p]
        store: Store = self.server.store
        if parts == ["health"]:
            if method != "GET":
                return self._send(405, {"error": "method not allowed"})
            return self._send(200, {"status": "ok", "resources": sorted(ROUTES)})
        if not parts or parts[0] not in ROUTES or len(parts) > 2:
            return self._send(404, {"error": "not found"})
        entity = ROUTES[parts[0]]
        try:
            if len(parts) == 1:
                if method == "GET":
                    filters = dict(parse_qsl(url.query))
                    return self._send(200, {"items": store.list(entity, filters or None)})
                if method == "POST":
                    return self._send(201, store.create(entity, self._body()))
                return self._send(405, {"error": "method not allowed"})
            try:
                item_id = int(parts[1])
            except ValueError:
                return self._send(404, {"error": "not found"})
            if method == "GET":
                item = store.get(entity, item_id)
            elif method in ("PUT", "PATCH"):
                item = store.update(entity, item_id, self._body(), partial=method == "PATCH")
            elif method == "DELETE":
                if store.delete(entity, item_id):
                    return self._send(204)
                item = None
            else:
                return self._send(405, {"error": "method not allowed"})
            if item is None:
                return self._send(404, {"error": "not found"})
            return self._send(200, item)
        except models.ValidationError as exc:
            return self._send(400, {"error": "validation failed", "fields": exc.errors})

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")


def make_server(host: str = "127.0.0.1", port: int = 8000, db: str = ":memory:") -> ThreadingHTTPServer:
    """Build a server. ``port=0`` picks a free port (see ``server.server_address``)."""
    server = ThreadingHTTPServer((host, port), AppHandler)
    server.store = Store(db)
    server.verbose = False
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="__NAME__", description="Run the __NAME__ JSON API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="__PKG__.db", help="SQLite file (':memory:' for none)")
    parser.add_argument("--verbose", action="store_true", help="log each request")
    args = parser.parse_args(argv)
    server = make_server(args.host, args.port, args.db)
    server.verbose = args.verbose
    print(f"__NAME__ serving on http://{args.host}:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

MAIN_PY = '''from .api import main

raise SystemExit(main())
'''

TEST_API_HEAD = '''"""HTTP API tests (generated). A real server runs on a free local port."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from __PKG__.api import make_server


@pytest.fixture
def base_url():
    server = make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    server.store.close()


def call(method, url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as err:
        body = err.read()
        return err.code, json.loads(body) if body else None


def test_health(base_url):
    status, body = call("GET", f"{base_url}/health")
    assert status == 200
    assert body == {"status": "ok", "resources": __RESOURCES__}


def test_unknown_route_404(base_url):
    assert call("GET", f"{base_url}/no-such-thing")[0] == 404


def test_malformed_json_400(base_url):
    req = urllib.request.Request(
        f"{base_url}/__FIRST_PLURAL__", data=b"{not json", method="POST"
    )
    with pytest.raises(urllib.error.HTTPError) as info:
        urllib.request.urlopen(req, timeout=10)
    assert info.value.code == 400
'''


def render_test_api(plan: Plan) -> str:
    subs = header(plan)
    subs["__RESOURCES__"] = pylit(sorted(e.plural for e in plan.entities))
    subs["__FIRST_PLURAL__"] = plan.entities[0].plural
    out = [fill(TEST_API_HEAD, subs), sample_constants(plan)]
    for e in plan.entities:
        n, up, p = e.name, e.name.upper(), e.plural
        out.append(f'''
def test_{n}_crud_over_http(base_url):
    status, created = call("POST", f"{{base_url}}/{p}", {up}_A)
    assert status == 201
    item_url = f"{{base_url}}/{p}/{{created['id']}}"
    assert call("GET", item_url) == (200, created)
    assert call("GET", f"{{base_url}}/{p}") == (200, {{"items": [created]}})
    status, patched = call("PATCH", item_url, {{{up}_KEY: {up}_B[{up}_KEY]}})
    assert status == 200
    assert patched[{up}_KEY] == {up}_B[{up}_KEY]
    status, replaced = call("PUT", item_url, {up}_B)
    assert status == 200
    assert {{k: replaced[k] for k in {up}_B}} == {up}_B
    assert call("DELETE", item_url) == (204, None)
    assert call("GET", item_url)[0] == 404


def test_{n}_invalid_payload_400(base_url):
    status, body = call("POST", f"{{base_url}}/{p}", {up}_BAD)
    assert status == 400
    assert sorted(body["fields"]) == sorted({up}_BAD)
    assert call("GET", f"{{base_url}}/{p}") == (200, {{"items": []}})


def test_{n}_missing_id_404(base_url):
    assert call("GET", f"{{base_url}}/{p}/999")[0] == 404
    assert call("PATCH", f"{{base_url}}/{p}/999", {{{up}_KEY: {up}_B[{up}_KEY]}})[0] == 404
    assert call("DELETE", f"{{base_url}}/{p}/999")[0] == 404
    assert call("GET", f"{{base_url}}/{p}/not-an-id")[0] == 404


def test_{n}_filter_by_query(base_url):
    call("POST", f"{{base_url}}/{p}", {up}_A)
    _, b = call("POST", f"{{base_url}}/{p}", {up}_B)
    query = urllib.parse.urlencode({{{up}_KEY: {up}_KEY_TEXT_B}})
    status, body = call("GET", f"{{base_url}}/{p}?{{query}}")
    assert status == 200
    assert [r["id"] for r in body["items"]] == [b["id"]]
''')
    text = "\n".join(out).rstrip() + "\n"
    return text.replace("import urllib.error\n", "import urllib.error\nimport urllib.parse\n", 1)


def usage(plan: Plan) -> str:
    e = plan.entities[0]
    body = json.dumps(sample(e, 0))
    routes = "\n".join(
        f"- `GET|POST /{x.plural}`, `GET|PUT|PATCH|DELETE /{x.plural}/<id>`" for x in plan.entities
    )
    return f"""```bash
pip install -e .
{plan.name} --port 8000 --db {plan.package}.db
# or without installing: PYTHONPATH=src python -m {plan.package} --port 8000
curl -s localhost:8000/health
curl -s -X POST localhost:8000/{e.plural} -H 'Content-Type: application/json' \\
  -d '{body}'
curl -s localhost:8000/{e.plural}
```

Routes:

- `GET /health`
{routes}

List routes accept `?field=value` equality filters. Validation errors return 400
with a `fields` object naming each bad field."""


def render(plan: Plan) -> dict[str, str]:
    subs = header(plan)
    pkg = f"src/{plan.package}"
    return {
        f"{pkg}/api.py": fill(API_PY, subs),
        f"{pkg}/__main__.py": MAIN_PY,
        "tests/test_api.py": render_test_api(plan),
        "pyproject.toml": pyproject(plan, "api"),
        "README.md": readme(plan, usage(plan)),
    }
