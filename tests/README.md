# tests/

Stdlib `unittest` only — no third-party dependencies.

## Run

```bash
# All tests
python3 -m unittest discover tests -v

# Single module
python3 -m unittest tests.test_migrations -v
```

## What's tested

| File | Covers |
|------|--------|
| `test_migrations.py` | Migration runner: fresh DB, idempotency, v0.1.0 upgrade, duplicate-column tolerance, new migration discovery, filename pattern enforcement |

More tests land in v0.2.3 (judgment logic).
