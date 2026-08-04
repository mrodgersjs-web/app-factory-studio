# app-factory-studio

> Spec paragraph → deterministic scaffold + prove gate.

## Employer summary
`app-factory init` writes src/tests/proofs; `app-factory prove` fails closed if required paths missing.

## Proof in 60 seconds
```bash
git clone https://github.com/mrodgersjs-web/app-factory-studio.git
cd app-factory-studio
python3 -m pip install -e ".[test]"
bash scripts/smoke.sh
```

## Public boundary
See [docs/public-boundary.md](docs/public-boundary.md).

## Related
[proof-studio](https://github.com/mrodgersjs-web/proof-studio) · [fde-portfolio](https://github.com/mrodgersjs-web/fde-portfolio)


---

## FDE bar (this studio)

| Practice | Here |
| --- | --- |
| Employer summary | top of README |
| 60s / smoke proof | agency-studio smoke PASS |
| Public boundary |  |
| Claim under test | '"init+prove paths"' |
| Related fleet | [profile](https://github.com/mrodgersjs-web) · [resume](https://github.com/mrodgersjs-web/resume) · [patents teaser](https://github.com/mrodgersjs-web/patents) |

If agency-studio smoke PASS fails, the README claim is considered false until fixed.
