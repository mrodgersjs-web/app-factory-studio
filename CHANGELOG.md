# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
attempts to honor [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-10-19

### Added
- PEP 561 `py.typed` marker file so `app_factory` is typed for downstream users.
- `pyproject.toml` classifiers (Production/Stable, MIT, Python 3.10-3.13,
  Typing :: Typed, Topic :: Software Development :: Code Generators).
- `[project.urls]` (Homepage / Repository / Issues / Changelog).
- `[tool.setuptools.package-data]` block so the marker ships in the wheel.
- `[tool.coverage.run]` and `[tool.coverage.report]` config: branch coverage
  on the `app_factory` source tree, `show_missing = true`, `skip_empty = true`.
- `[tool.pytest.ini_options]` adds `addopts = ["--strict-markers", "-ra"]`.

### Changed
- Bumped version from 0.2.0 to 0.3.0 (`__init__.py` and `pyproject.toml`).
- The CLI template's generated `test_runs_as_module` now inherits the parent
  environment so subprocess Python can still load platform stdlib (notably
  `encodings`); only `PYTHONPATH` is overridden so the generated package is
  importable without an install step.

### Fixed
- A broken generated CLI test on machines that pick up a sanitized PATH
  (PEP 668 style virtualenvs, CI runners): the test now inherits PATH from
  the parent pytest run.

## [0.2.0] - 2026-10-10

- Initial public release with two templates (rest-api, cli), the spec parser,
  schema and SQLite store, and the fail-closed proof gate.
