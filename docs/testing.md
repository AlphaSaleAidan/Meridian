# Testing

## Running the suite

Run pytest from the repo root with the default `sys.path`:

```bash
.venv/bin/python -m pytest tests src/tests -q
```

Tests must import application code via `from src.x import ...`.

`pytest.ini` sets `testpaths = tests`, so a bare `pytest` never looks in
`src/tests` — hence the explicit second path above. Note that even with it,
`src/tests/test_ai_engine.py` contributes **zero** collected tests: its body is
a single `async def run_tests()` with no `test_` prefix, so it only runs as a
script (`python src/tests/test_ai_engine.py`). New tests belong in `tests/`.

## Landmine: never use `PYTHONPATH=src`

Do **not** put `src` on `sys.path` (e.g. `PYTHONPATH=src pytest`). The repo has a
`src/email/` package, and once `src` is on the path it shadows Python's stdlib
`email` module. That shadowing breaks `httpx` and `pytest` themselves with errors
like `ModuleNotFoundError: No module named 'email.parser'`. Always run from the
repo root with the default path and import via `from src.x import ...`.

## Async tests

Async test functions are enabled via `asyncio_mode = auto` in `pytest.ini`
(pytest-asyncio). No per-test `@pytest.mark.asyncio` decorator is required.
