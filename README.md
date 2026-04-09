# LLMRouterBench

Import the library as Python package **`main`** (e.g. `from main import …`). The **`LLMRouterBench`** name is the PyPI project and console script. Published trees and PyPI artifacts ship **`main`**, **`data/`**, and documentation only—**no** bundled test or smoke scripts.

**Version:** `0.1.0` (see [CHANGELOG.md](CHANGELOG.md)).

Chinese review copy: [README.zh.md](README.zh.md).

This directory is the **only** part of the repository intended for open source: the installable distribution **`LLMRouterBench`** (import package **`main`**; see **Python API**) and the public **tier-only** question bank under **`data/`**. Test and HTTP-smoke harnesses are **not** part of this release (see **`.gitignore`** / **`MANIFEST.in`**).

Python package for **routing supervision** items (LLM inputs plus **tier-only** targets — no vendor model IDs in the open corpus) and **evaluation metrics** aligned with the RouterBench v2 guide Section 11 (pass rate, nominal cost savings score, nominal money saved).

## Install

From this directory (editable, for development):

```bash
pip install -e .
```

After you publish to PyPI, consumers can run:

```bash
pip install LLMRouterBench
```

They still **`import main`** in code; the distribution name and the import package name differ on purpose.

The core package depends on **`requests`** for HTTP helpers (`main.router_llm`).

### Local tests (not pushed)

You may keep a **`tests/`** directory beside `pyproject.toml` for **pytest** or private harnesses; it is **`.gitignore`d** and **not** part of the public tree. Install **`pytest`** locally (e.g. `pip install pytest`) and run **`pytest tests`** from this directory.

## Project layout

| Path | Purpose |
|------|---------|
| `main/` | **Published** Python package (`import main`). |
| `data/` | **`question_bank.jsonl`** and **`manifest.json`** (bundled in wheels when present at build time). |

Regenerating **`data/`** from private benchmark exports is **out of scope** for the published package; keep your own merge tooling outside this tree if needed.

## Data layout

Artifacts under **`data/`**:

- **`data/question_bank.jsonl`** — all routing-step records in **one** file (no per-benchmark subdirectories).
- **`data/manifest.json`** — per-source line counts and schema metadata.

Each line includes a string field **`benchmark`** (e.g. `swebench`, `mtrag`) for filtering.

### Open corpus: tier-only targets (no model IDs)

The question bank **does not** include fields such as `optimal_model` or `baseline_model`. Supervision is **only** by capability tier, using **English** labels and a **numeric** id.

| `target_tier` (string) | `target_tier_id` (int) | Guide CN label |
|------------------------|-------------------------|----------------|
| `low`                  | 0                       | 低             |
| `mid`                  | 1                       | 中             |
| `mid_high`             | 2                       | 中高           |
| `high`                 | 3                       | 高             |

Each line includes at least: `id`, `benchmark`, `scenario`, `instance_id`, `step_index`, `total_steps`, `messages`, `target_tier`, `target_tier_id`.

## Data distribution

The following counts match the **`data/question_bank.jsonl`** and **`data/manifest.json`** shipped in this repository (**762** routing-step rows). Rebuilding the bank from private exports may change these figures.

### Rows by `benchmark`

| `benchmark` | Rows | Share of bank |
|-------------|-----:|--------------:|
| `swebench` | 336 | 44.1% |
| `mtrag` | 193 | 25.3% |
| `qmsum` | 145 | 19.0% |
| `pinchbench` | 88 | 11.5% |
| **Total** | **762** | **100%** |

### Gold `target_tier` (full bank)

| `target_tier` | `target_tier_id` | Rows | Share |
|---------------|-----------------|-----:|------:|
| `low` | 0 | 423 | 55.5% |
| `mid` | 1 | 63 | 8.3% |
| `mid_high` | 2 | 56 | 7.3% |
| `high` | 3 | 220 | 28.9% |
| **Total** | — | **762** | **100%** |

### Gold `target_tier` by `benchmark` (row counts)

| `benchmark` | Rows | `low` | `mid` | `mid_high` | `high` |
|-------------|-----:|------:|------:|-----------:|-------:|
| `mtrag` | 193 | 183 | 8 | 1 | 1 |
| `pinchbench` | 88 | 65 | 10 | 6 | 7 |
| `qmsum` | 145 | 132 | 10 | 3 | 0 |
| `swebench` | 336 | 43 | 35 | 46 | 212 |

## Nominal pricing (Section 11.2)

| Public `target_tier` | USD / 1M output tokens |
|----------------------|-------------------------|
| `low`                | 0.5 |
| `mid`                | 1.2 |
| `mid_high`           | 3.0 |
| `high`               | 20.0 |

When computing costs from **concrete model endpoints** inside your harness, this library maps known model ids to these tiers and raises `ValueError` on unknown ids. That mapping lives in code only, not in the open JSONL.

## Benchmark usage: wiring predictors and scoring

Each line in `data/question_bank.jsonl` is **one routing supervision step**: a conversation prefix (`messages`) and a gold capability tier (`target_tier` / `target_tier_id`). Any router you plug in must produce a **tier id in {0,1,2,3}** for that step. The library scores predictions against gold using the rules below.

### Sampling

- **Full bank** — `run_question_bank_eval(..., n=None)`: every row, **file order** (~762 steps in the public build).
- **Fixed size, stratified by source** — pass `--n N` (CLI) or `n=N` (API): **largest-remainder** quotas by `data/manifest.json` `sources.*.line_count`, then **one-pass reservoir sampling** per benchmark stratum (`--seed` fixes RNG). This keeps the four logical benchmarks (`swebench`, `pinchbench`, `mtrag`, `qmsum`) in roughly the same ratio as the full corpus.

Report **`sample_mode`**, **`benchmark_counts`**, and **`by_benchmark`** from the eval JSON so others can reproduce your split.

### OpenAI-compatible chat hook (single-digit tier output)

For teams that **choose** to call a chat model behind an OpenAI-compatible HTTP API, this package exposes a **digit-tier** contract via `OpenAICompatRouterClassifier` and `LlmDigitClassifierPredictor`. That is a **reference integration only**—not a recommendation that LLM-based routing is preferable to rules, classical ML, or other designs.

The contract is:

1. Linearize the row’s `messages` into one user string (`question_bank_messages_to_classifier_prompt`).
2. Send **one** chat completion per row; the assistant message must be **parseable as a single digit** `0`–`3` (optional surrounding whitespace; **no** extra lines or prose — see `parse_tier_response_to_id`).
3. Call **`run_question_bank_eval`** / **`evaluate_question_bank_rows`** from `main.eval` from your own driver (load rows, call the predictor, aggregate JSON).

### Arbitrary predictors (rules, sklearn, etc.)

Implement a function `f(row: dict) -> int` that returns **`target_tier_id` in 0..3** from the raw row (you may ignore `messages` or engineer features from them). Wrap it with **`FunctionPredictor`** and pass it to **`run_question_bank_eval`** or **`evaluate_question_bank_rows`**. No HTTP and no chat template are required; the same JSON summary and **`by_benchmark`** breakdown apply.

## Scoring rules (routing-step evaluation)

These metrics are computed by **`main.eval`**. They evaluate **tier choice at a single supervised step**, using the **nominal output price per 1M tokens** by tier (table above). They are **aligned with the RouterBench v2 guide’s §11.2 nominal cost construction** on a **per-step** basis; they do **not** require running full benchmark tasks to completion.

| Metric | Definition |
|--------|------------|
| **`tier_match_accuracy`** | Fraction of **evaluable** rows (no `error`) where `pred_tier_id == gold_tier_id`. Skipped rows are excluded from the denominator. |
| **`valid_response_rate`** | Fraction of rows with a usable prediction (no recorded `error`). |
| **Pass (`passed`)** | `pred_tier_id >= gold_tier_id` (predicted tier is at least as capable as gold). Rows with `error` are **not** passed. |
| **`pass_rate`** | `passed / sampled` over all rows. |
| **`cost_savings_score`** | Let baseline be **always routing at `high` (tier id 3)**. For each **passed** row with gold strictly below `high`, define nominal step costs using a **uniform positive completion length** \(T\) for every row (public bank has no per-step token counts; the library uses one fixed \(T\) so ratios match §11.2 when all steps share the same \(T\)): `cost(tier) = T × (USD/1M for tier) / 10^6`. Then `save_gt = cost(high) - cost(gold)`, `save_test = cost(high) - cost(pred)`. **Score = `100 × Σ save_test / Σ save_gt`** over passed rows with `save_gt > 0`. |

**Relation to the full guide:** RouterBench v2 **§11.1 task pass rate** (e.g. SWE-Bench resolved) needs an **end-to-end** harness with executed trajectories. The question-bank eval here is the **routing-supervision** slice: it measures whether your router’s **tier choice** is sufficient (`pass_rate`) and how much **nominal money** it saves versus always using the highest tier (`cost_savings_score`), under the stated assumptions.

### Router accounting metrics (`router_accounting`)

The eval summary and each **`by_benchmark`** block include **`router_accounting`**, computed only on **evaluable** rows (no `error`, with int `pred_tier_id` / `gold_tier_id`). Skipped rows are excluded from **`n_e`**, from **`D`**, and from **`N`**. Three component fields use a **0–100** scale (float), plus one **composite** derived from them:

| Field | Definition |
|-------|------------|
| **`pass_rate_percent`** | `100 × (pred ≥ gold) / n_e`. NaN if `n_e = 0`. |
| **`exact_match_rate_percent`** | `100 × (pred == gold) / n_e`. Same as `tier_match_accuracy × 100` on the evaluable set. NaN if `n_e = 0`. |
| **`accounting_savings_score_percent`** | `100 × N / D`. **D** = Σ nominal `(cost(high) − cost(gold))` over evaluable rows (same \(T\) as §11). **N** = on pass, add `(cost(high) − cost(pred))`; on fail (`pred < gold`), add **`−(pred + 1)`** (dimensionless penalty). **Always-high routing** ⇒ `N = 0` ⇒ **0** when `D > 0`. Can be **negative** if failures dominate. **NaN** if `D = 0` (e.g. all gold is `high`) or `n_e = 0`. |
| **`overall_score_percent`** | **`(pass_rate_percent + exact_match_rate_percent + accounting_savings_score_percent) / 3`**. **NaN** if **any** of the three components is **NaN**. |

`N` mixes USD-consistent savings on passed rows with integer penalties on failed rows; treat **`accounting_savings_score_percent`** as an **interpretive** index, **not** comparable to legacy **`cost_savings_score`**. Implementations: `compute_router_accounting_metrics` in `main.eval.section11`.

Top-level **`tier_match_accuracy`** (0–1) and **`accuracy_excluding_errors`** both use **evaluable / sampled** semantics for the ratio of exact matches (same value).

## Python API

```python
from main import iter_question_bank, iter_routing_supervision

# Full bank (single file data/question_bank.jsonl)
for row in iter_question_bank():
    ...

# Only rows whose benchmark field is "swebench" (same as iter_routing_supervision("swebench"))
for row in iter_routing_supervision("swebench"):
    messages = row["messages"]
    tier = row["target_tier"]
    tier_id = row["target_tier_id"]
```

```python
from main.metrics import CaseMetrics, aggregate_routerbench_metrics

cases = [
    CaseMetrics(
        case_id="a",
        task_passed=True,
        baseline_cost_nominal=1.0,
        optimal_cost_nominal=0.4,
        test_cost_nominal=0.5,
    ),
]
summary = aggregate_routerbench_metrics(cases)
```

```python
from main.metrics import routing_supervision_accuracy

acc = routing_supervision_accuracy(gold_rows, predictions_by_id)
```

## Router LLM API (OpenAI-compatible chat completions)

`OpenAICompatRouterClassifier` sends **one case per request**: `system` (plain string, or Anthropic-style cached block list when `system_prompt_cache` is `on` / `auto`+Claude) plus **one `user` message** whose `content` is a **string** (your full case text). The model must reply with **exactly one character** `0`–`3` (`target_tier_id`: low→0, mid→1, mid_high→2, high→3). Responses containing newlines or extra text raise `ValueError` on parse.

```python
from main import OpenAICompatRouterClassifier, question_bank_messages_to_classifier_prompt

clf = OpenAICompatRouterClassifier(
    base_url="https://api.example.com/v1",
    api_key="...",
    model="deepseek/deepseek-v3.2",
    system_prompt_cache="auto",
)
prompt = question_bank_messages_to_classifier_prompt(row["messages"])
result = clf.predict_tier_id(prompt)
assert result.tier_id == row["target_tier_id"]
```

Lower-level helpers: `parse_tier_response_to_id`, `build_system_content`, `post_chat_completions`, `chat_completions_url`. Default instructions live in `DEFAULT_ROUTER_SYSTEM_INSTRUCTION`.

### Question-bank evaluation (`main.eval`)

Programmatic entry point for **sampling**, **scoring**, and pluggable predictors (`FunctionPredictor`, `LlmDigitClassifierPredictor`, or any **`QuestionBankRouterPredictor`**). See **Benchmark usage** and **Scoring rules** for semantics.

Implement **`QuestionBankRouterPredictor`** (method `predict(row) -> TierPrediction`) or use:

- **`FunctionPredictor`**: wraps any `callable(row: dict) -> int` (heuristics, sklearn `predict`, etc.); no chat prompt.
- **`LlmDigitClassifierPredictor`**: optional OpenAI-compat chat wrapper around `OpenAICompatRouterClassifier` and `question_bank_messages_to_classifier_prompt`.

```python
from main.eval import (
    FunctionPredictor,
    LlmDigitClassifierPredictor,
    run_question_bank_eval,
    evaluate_question_bank_rows,
    build_eval_summary,
    select_question_bank_rows,
)

# Rules / sklearn-style: tier_id only from the row (example: always use gold — not a real model)
oracle = FunctionPredictor(lambda row: row["target_tier_id"])
rows, sample_mode, quotas = select_question_bank_rows(n=20, seed=1)
per_row, errors, correct = evaluate_question_bank_rows(
    oracle, rows, predictor_label="oracle_gold"
)
summary = build_eval_summary(
    per_row=per_row,
    errors=errors,
    correct=correct,
    predictor_label="oracle_gold",
    shard="data/question_bank.jsonl",
    sample_mode=sample_mode,
    seed=1,
    proportional_quotas=quotas,
)

# One-shot (loads bank from package data paths):
# summary = run_question_bank_eval(oracle, predictor_label="oracle_gold", n=20, seed=1)
```

Public helpers also include `manifest_proportional_quotas`, `proportional_reservoir_sample`, `load_all_question_bank_rows`, `compute_section11`, and `aggregate_by_benchmark`.

## CLI

```bash
python -m main.cli metrics --cases path/to/cases.json
LLMRouterBench metrics --cases path/to/cases.json
```

When calling **`OpenAICompatRouterClassifier`** from your application, configure the API with environment variables or your own config layer. **`.env.example`** lists common variable names (**`OPENROUTER_*`** or **`OPENAI_*`** / **`API_KEY`** + **`BASE_URL`**); the client expects a base URL that already includes **`/v1`**.

## Publishing (maintainers)

1. Add **`[project.urls]`** to `pyproject.toml` (`Homepage`, `Repository`, etc.) before uploading to PyPI so the project page links resolve.
2. Ensure **`data/question_bank.jsonl`** and **`data/manifest.json`** exist if you want them inside the built wheel (see `[tool.setuptools.package-data]` in `pyproject.toml`).
3. Bump **`version`** in `pyproject.toml` and append a section to **`CHANGELOG.md`**.
4. Build and upload:

```bash
pip install build twine
python -m build
twine check dist/*
twine upload dist/*
```


**Naming reminder:** the PyPI / pip distribution is **`LLMRouterBench`**; the only shipped import top-level package is **`main`**. Avoid shadowing `main` in small throwaway scripts (e.g. do not name your module `main.py` next to snippets that `import main`).

## License

Apache-2.0 (see `LICENSE` and `pyproject.toml`). Third-party benchmark data may carry separate licenses.
