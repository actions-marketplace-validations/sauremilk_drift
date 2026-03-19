# Contributing to Drift

Thanks for your interest in contributing! Drift is under active development and welcomes bug fixes, new signals, and documentation improvements.

## Quick start

```bash
git clone https://github.com/sauremilk/drift.git
cd drift
pip install -e ".[dev]"
pytest
```

## What to work on

Check the [open issues](https://github.com/sauremilk/drift/issues) — issues labelled **`good first issue`** are a good entry point.

High-value contributions:

- **New detection signals** — see `src/drift/signals/base.py` for the interface
- **TypeScript support** — tree-sitter integration (see roadmap in README)
- **False positive fixes** — signal quality improvements are always welcome
- **Documentation** — usage examples, configuration how-tos

## Adding a new signal

1. Create `src/drift/signals/your_signal.py` implementing `BaseSignal`
2. Register it in `src/drift/analyzer.py`
3. Add a weight entry in `src/drift/config.py` (default `0.0` until stable)
4. Write tests in `tests/signals/test_your_signal.py`

Signals must be:

- **Deterministic** — same input always produces same output
- **LLM-free** — the core pipeline uses only AST analysis and statistics
- **Fast** — target < 500ms per 1 000 functions

## Code conventions

- Python 3.11+, type annotations everywhere
- `ruff check src/ tests/` must pass
- `pytest` must pass

## Submitting a PR

1. Open an issue first for non-trivial changes (saves everyone time)
2. Keep PRs focused — one concern per PR
3. Add tests for new behaviour
4. Update the README if you add a feature

## Versioning

Drift follows **Semantic Versioning (SemVer)**: `MAJOR.MINOR.PATCH`

| Typ               | Wann                                             | Beispiel            |
| ----------------- | ------------------------------------------------ | ------------------- |
| **PATCH** `x.x.↑` | Bugfix, kein neues Feature, kein Breaking Change | `v1.1.0` → `v1.1.1` |
| **MINOR** `x.↑.0` | Neues Feature, rückwärtskompatibel               | `v1.1.0` → `v1.2.0` |
| **MAJOR** `↑.0.0` | Breaking Change, inkompatible API-Änderung       | `v1.1.0` → `v2.0.0` |

### GitHub Actions Major-Version-Tag

Da Drift eine GitHub Action ist (`uses: sauremilk/drift@v1`), gibt es eine zusätzliche Konvention:
den **Major-Version-Tag** (`v1`, `v2`) als beweglichen Zeiger. Das bedeutet:

- Nutzer referenzieren `@v1` und bekommen automatisch alle Minor/Patch-Updates
- Der `v1`-Tag wird nach jedem Minor/Patch-Release auf den neuen Commit verschoben
- Bei einem **Breaking Change** wird `v2` erstellt und `@v2` zum neuen Tag

Der CI/CD-Workflow (`publish.yml`) verschiebt den Major-Tag **automatisch** nach jedem
GitHub-Release. Manuell ist das nicht nötig – außer bei außerplanmäßigen Hotfixes:

```bash
git tag -f v1 && git push -f origin v1
```

### Release-Prozess

Jeder sinnvolle Commit-Batch (Feature, Fix, Konfigurationsänderung) sollte einen eigenen
versionierten Release bekommen, damit das Changelog sauber bleibt und Nutzer auf bestimmte
Versionen pinnen können.

1. Version in `pyproject.toml` erhöhen (z. B. `1.1.0` → `1.1.1`)
2. Commit: `git commit -m "chore: bump version to v1.1.1"`
3. Tag erstellen: `git tag v1.1.1`
4. Push tag: `git push origin v1.1.1`
5. GitHub Release aus dem Tag erstellen → CI verschiebt `v1` automatisch

## Reporting issues

Use the [issue templates](.github/ISSUE_TEMPLATE/) — they help reproduce problems quickly.

## License

By contributing you agree that your contributions will be licensed under the [MIT License](LICENSE).
