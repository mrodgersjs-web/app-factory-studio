"""Template registry. Each template adds an interface (HTTP or CLI) plus its tests
on top of the shared schema, validation and SQLite store in ``common``."""

from __future__ import annotations

from . import cli_app, rest_api

TEMPLATE_RENDERERS = {
    "rest-api": rest_api.render,
    "cli": cli_app.render,
}

TEMPLATE_DESCRIPTIONS = {
    "rest-api": "JSON CRUD HTTP service (stdlib http.server + sqlite3), with HTTP tests",
    "cli": "argparse CRUD command-line tool backed by sqlite3, with CLI tests",
}
