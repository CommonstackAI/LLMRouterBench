"""Section 11-style aggregates over per-row eval records (pass rate, nominal cost savings score)."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from main.pricing import step_nominal_cost_usd
from main.tiers import ID_TO_TIER, TIER_HIGH, public_tier_to_id

# Baseline trajectory: always route at highest public tier (guide table "高").
_BASELINE_TIER_ID = public_tier_to_id(TIER_HIGH)

# Uniform completion tokens per routing step (public bank has no per-step counts).
_ASSUMED_COMPLETION_TOKENS_PER_ROUTING_STEP = 1_000_000


def _step_nominal_usd(tier_id: int) -> float:
    return step_nominal_cost_usd(
        _ASSUMED_COMPLETION_TOKENS_PER_ROUTING_STEP,
        ID_TO_TIER[tier_id],
    )


def _overall_router_score_percent(a: float, b: float, c: float) -> float:
    """Mean of three 0–100 headline fields; NaN if any argument is NaN."""
    if math.isnan(a) or math.isnan(b) or math.isnan(c):
        return float("nan")
    return (a + b + c) / 3.0


def compute_section11(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Pass rate and cost savings score across rows.

    Pass: ``pred_tier_id >= gold_tier_id``. Rows with ``error`` count as not passed.

    Cost savings (§11.2), one routing step per row, uniform T.
    """
    passed = 0
    total = 0
    sum_save_gt = 0.0
    sum_save_test = 0.0
    cost_score_cases = 0

    baseline_cost = _step_nominal_usd(_BASELINE_TIER_ID)

    for r in rows:
        total += 1
        if "error" in r:
            continue
        pred = r["pred_tier_id"]
        gold = r["gold_tier_id"]
        if pred >= gold:
            passed += 1
            optimal_cost = _step_nominal_usd(gold)
            cost_test = _step_nominal_usd(pred)
            save_gt = baseline_cost - optimal_cost
            save_test = baseline_cost - cost_test
            if save_gt > 0:
                sum_save_gt += save_gt
                sum_save_test += save_test
                cost_score_cases += 1

    pass_rate = passed / total if total else float("nan")
    if sum_save_gt > 0:
        cost_savings_score = 100.0 * sum_save_test / sum_save_gt
    else:
        cost_savings_score = float("nan")

    return {
        "pass_rate": pass_rate,
        "passed": passed,
        "total": total,
        "cost_savings_score": cost_savings_score,
        "cost_score_cases_used": cost_score_cases,
        "sum_save_gt_usd": sum_save_gt,
        "sum_save_test_usd": sum_save_test,
        "assumed_completion_tokens_per_routing_step": _ASSUMED_COMPLETION_TOKENS_PER_ROUTING_STEP,
        "baseline_tier": TIER_HIGH,
        "baseline_nominal_cost_per_step_usd": baseline_cost,
        "cost_formula": "save_gt = baseline.cost - optimal_path.cost per §11.2 (nominal USD)",
        "note": "Sums are nominal USD under uniform T per step. If real completion_tokens v_i "
        "vary by case, §11.2 uses v_i in each cost; ratio equals current only when all v_i are equal.",
    }


def compute_router_accounting_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Evaluable-set metrics (rows without ``error`` with int ``pred_tier_id`` / ``gold_tier_id``).

    * ``pass_rate_percent``: 100 * (pred >= gold) / n_e
    * ``exact_match_rate_percent``: 100 * exact / n_e
    * ``accounting_savings_score_percent``: 100 * N / D where D = sum(baseline - gold cost),
      N sums (baseline - pred cost) on pass and ``-(pred + 1)`` on fail (pred < gold).
    * ``overall_score_percent``: arithmetic mean of the three fields above; NaN if any of them is NaN.

    Skipped rows (API/parse failure) are excluded from n_e, D, and N. Legacy ``compute_section11``
    remains unchanged. ``accounting_savings_score_percent`` mixes USD terms with integer penalties;
    it can be negative when N < 0. ``D == 0`` or ``n_e == 0`` yields NaN for the ratio fields.
    """
    skipped_count = sum(1 for r in rows if "error" in r)
    evaluable: list[dict[str, Any]] = []
    for r in rows:
        if "error" in r:
            continue
        pred = r.get("pred_tier_id")
        gold = r.get("gold_tier_id")
        if not isinstance(pred, int) or not isinstance(gold, int):
            raise ValueError(
                "evaluable row must have int pred_tier_id and gold_tier_id "
                f"(id={r.get('id')!r})"
            )
        evaluable.append(r)

    n_e = len(evaluable)
    baseline_cost = _step_nominal_usd(_BASELINE_TIER_ID)
    passed = 0
    exact = 0
    d_sum = 0.0
    n_sum = 0.0

    for r in evaluable:
        pred = r["pred_tier_id"]
        gold = r["gold_tier_id"]
        cost_gold = _step_nominal_usd(gold)
        d_sum += baseline_cost - cost_gold
        if pred >= gold:
            passed += 1
            if pred == gold:
                exact += 1
            n_sum += baseline_cost - _step_nominal_usd(pred)
        else:
            n_sum -= pred + 1

    pass_rate_percent = 100.0 * passed / n_e if n_e else float("nan")
    exact_match_rate_percent = 100.0 * exact / n_e if n_e else float("nan")
    if d_sum > 0:
        accounting_savings_score_percent = 100.0 * n_sum / d_sum
        ratio_note = "100 * N / D; N mixes USD savings on pass and integer penalty on fail."
    elif n_e == 0:
        accounting_savings_score_percent = float("nan")
        ratio_note = "n_e == 0: no evaluable rows."
    else:
        accounting_savings_score_percent = float("nan")
        ratio_note = "D == 0: no nominal savings vs always-high on evaluable set (e.g. all gold high)."

    overall_score_percent = _overall_router_score_percent(
        pass_rate_percent,
        exact_match_rate_percent,
        accounting_savings_score_percent,
    )

    return {
        "evaluable_count": n_e,
        "skipped_count": skipped_count,
        "passed_count": passed,
        "exact_match_count": exact,
        "D_nominal_usd": d_sum,
        "N_mixed": n_sum,
        "pass_rate_percent": pass_rate_percent,
        "exact_match_rate_percent": exact_match_rate_percent,
        "accounting_savings_score_percent": accounting_savings_score_percent,
        "overall_score_percent": overall_score_percent,
        "assumed_completion_tokens_per_routing_step": _ASSUMED_COMPLETION_TOKENS_PER_ROUTING_STEP,
        "note": ratio_note,
    }


def aggregate_by_benchmark(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | Any]]:
    """Per-benchmark buckets with tier accuracy, valid rate, and nested Section 11 fields."""
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by[r["benchmark"]].append(r)

    out: dict[str, dict[str, Any]] = {}
    for b in sorted(by.keys()):
        brows = by[b]
        s = len(brows)
        err = sum(1 for r in brows if "error" in r)
        ok_parse = s - err
        exact = sum(1 for r in brows if r.get("match"))
        s11 = compute_section11(brows)
        acct = compute_router_accounting_metrics(brows)
        out[b] = {
            "sampled": s,
            "exact_match": exact,
            "api_errors": err,
            "tier_match_accuracy": exact / ok_parse if ok_parse else float("nan"),
            "valid_response_rate": ok_parse / s if s else float("nan"),
            "pass_rate": s11["pass_rate"],
            "passed": s11["passed"],
            "cost_savings_score": s11["cost_savings_score"],
            "cost_score_cases_used": s11["cost_score_cases_used"],
            "router_accounting": acct,
        }
    return out
