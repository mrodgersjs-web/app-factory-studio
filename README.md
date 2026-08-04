# app-factory-studio

> Spec paragraph → deterministic app scaffold with a prove gate (Definition of Done as files on disk).

![status](https://img.shields.io/badge/status-public-studio-blue)

## Employer summary

Generates a minimal scaffold from a markdown spec and seals an `proofs/init.json` packet. `app-factory prove` fails closed if required paths are missing. Full private generator corpora stay offline; this is the public control surface.

## Proof in 60 seconds

```bash
git clone https://github.com/mrodgersjs-web/app-factory-studio.git
cd app-factory-studio
python3 -m pip install -e ".[test]"
pytest -q
app-factory init --spec examples/sample-spec.md --out /tmp/app-factory-demo
app-factory prove /tmp/app-factory-demo
```

## Architecture

```text
spec.md → parse title/hash → write src/tests/proofs → prove paths exist
```

## Public boundary
See [docs/public-boundary.md](docs/public-boundary.md).

## Related
- [proof-studio](https://github.com/mrodgersjs-web/proof-studio) · [fde-portfolio](https://github.com/mrodgersjs-web/fde-portfolio)
