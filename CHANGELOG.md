# Changelog

All notable changes to the open-source **CommonRouterBench** Python distribution (import package **`main`**) are documented in this file.

## [Unreleased]

### Changed

- **PinchBench data rebuild**: replaced baseline (gpt-5.4) conversation context with validated mixed-model context from actual cascade search runs. Messages now reflect the real optimal-path model responses at each step.
- PinchBench reduced from 16 tasks / 88 rows to 12 tasks / 48 rows: removed 4 tasks with incomplete mixed-model data (task_10_workflow, task_17_email_search, task_20_eli5_pdf_summary, task_21_openclaw_comprehension).
- Corrected 3 PinchBench GT tier labels after last-step downgrade validation: task_05_summary step 4 (high→low), task_11_clawdhub step 4 (mid→low), task_12_skill_search step 6 (high→low). These final steps are text-reply summaries where low-tier models score equivalently.
- **SWE-bench last-step 3-model validation**: tested all 33 non-low last steps with 3 models per tier (full cascade). Downgraded 13 additional last-step GT labels (28 total counterexamples, 5 confirmed correct). New SWE-bench tier distribution: low 94, mid 33, mid_high 41, high 168.
- Total question bank: **970** rows (was 1010).
- `build_open_data.py` now reads PinchBench from `test/pinchbench/mixed_model_data/` instead of upstream baseline-only export.
- Updated README/README.zh distribution tables to match new counts.

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
