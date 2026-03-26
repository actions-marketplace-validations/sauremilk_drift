# Contributing

See [CONTRIBUTING.md](https://github.com/sauremilk/drift/blob/main/CONTRIBUTING.md) for the full contributing guide.

## Quick Start

```bash
git clone https://github.com/sauremilk/drift.git
cd drift
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

## Good First Issues

Look for issues labelled [`good first issue`](https://github.com/sauremilk/drift/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) — these are scoped to be completable in a few hours.

## Adding a New Signal

1. Create `src/drift/signals/your_signal.py` implementing `BaseSignal`
2. Register it in `src/drift/analyzer.py`
3. Add a weight entry in `src/drift/config.py` (default `0.0` until stable)
4. Write tests in `tests/signals/test_your_signal.py`

Signals must be deterministic, LLM-free, and fast (< 500ms per 1,000 functions).
