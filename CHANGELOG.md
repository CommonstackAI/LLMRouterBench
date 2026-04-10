# Changelog

All notable changes to the open-source **CommonRouterBench** Python distribution (import package **`main`**) are documented in this file.

## [0.1.0] - 2026-04-09

### Added

- **`LICENSE`**: Apache License 2.0 full text, bundled in wheel metadata (`*.dist-info/licenses/`).
- Tier-only routing supervision corpus (`data/question_bank.jsonl`) and per-source counts (`data/manifest.json`), included in wheels when those files are present at build time.
- Import package **`main`**: dataset iterators, nominal RouterBench v2 §11.2-style step metrics, **`main.eval`** question-bank runner (`run_question_bank_eval`, `evaluate_question_bank_rows`, `FunctionPredictor`, `LlmDigitClassifierPredictor`), and OpenAI-compatible chat helper for digit tier classification.
- Eval summary **`router_accounting`**: `pass_rate_percent`, `exact_match_rate_percent`, `accounting_savings_score_percent`, **`overall_score_percent`** (arithmetic mean of those three; NaN if any component is NaN), plus underlying `D_nominal_usd` / `N_mixed` (evaluable rows only).
- Console entry point **`CommonRouterBench`** → `main.cli:main` (also `python -m main.cli`).

### Changed

- **Publishing scope:** **`tests/`** and **`scripts/`** are **`.gitignore`d** and **pruned** from sdists (`MANIFEST.in`). Public releases contain **`main`**, **`data/`** (when present), and docs only—no pytest suite or HTTP smoke harness in the repository or on PyPI.
- **Documentation**: README describes **data distribution** (per-`benchmark` rows, gold `target_tier` counts) instead of model score tables.

### Notes

- PyPI / pip name is **`CommonRouterBench`**; Python imports use **`import main`** (see README).
