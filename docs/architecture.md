# Architecture — App Factory Studio

## One-liner
Spec paragraph to a generated, tested app behind a proof gate.

## Flow
```text
spec text
  -> spec.parse_spec      rules only; refuses bad specs; records assumptions
  -> Plan                 name, template, entities, fields, spec sha256
  -> render.render        {path: text}; pure function of the Plan
  -> gate.write_app       files + app-factory.json (sha256 per file, tree hash, expected test count)
  -> gate.verify          runs the generated app's pytest suite
  -> proofs/proof.json    PASS only if exit 0, no failures, passed == expected
  -> gate.prove           proof PASS + tree unchanged (+ matches manifest)
```

## Determinism
No clocks, randomness or model calls in generation. The proof records test counts
and the pytest summary without timings. Two builds of the same spec are
byte-identical (checked in `tests/test_gate.py`).

## Trust boundaries
- Public, synthetic inputs only in `examples/`.
- Secrets never enter the repo.
- Success claims come only from the gate.
