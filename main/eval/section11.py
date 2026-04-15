"""Section 11-style aggregates over per-row eval records (pass rate, nominal cost savings score)."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from main.pricing import step_full_cost_usd, step_nominal_cost_usd
from main.tiers import ID_TO_TIER, TIER_HIGH, public_tier_to_id
from main.tokenizer import (
    estimate_output_tokens_from_delta,
    split_prompt_tokens_for_step,
)

# Baseline trajectory: always route at highest public tier (guide table "高").
_BASELINE_TIER_ID = public_tier_to_id(TIER_HIGH)
_BASELINE_TIER = TIER_HIGH

# Uniform completion tokens per routing step (public bank has no per-step counts).
_ASSUMED_COMPLETION_TOKENS_PER_ROUTING_STEP = 1_000_000

# Fallback output tokens when estimation from message delta is not possible
# (single-turn cases / last step of a trajectory with no internal references).
_FALLBACK_OUTPUT_TOKENS = 500


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


def _compute_path_step_cost(
    *,
    tier: str,
    prev_tier: str | None,
    msgs_curr: list[dict[str, Any]],
    msgs_prev: list[dict[str, Any]] | None,
    output_tokens: int,
) -> float:
    """Full cost (input + cache + output) for one step on a given routing path."""
    inp, cr, cw = split_prompt_tokens_for_step(
        prev_tier=prev_tier,
        curr_tier=tier,
        msgs_prev=msgs_prev,
        msgs_curr=msgs_curr,
    )
    return step_full_cost_usd(
        input_tokens=inp,
        cache_read_tokens=cr,
        cache_write_tokens=cw,
        output_tokens=output_tokens,
        tier=tier,
    )


def _estimate_trajectory_output_tokens(
    steps: list[dict[str, Any]],
) -> list[int]:
    """Return estimated output tokens for each step in a trajectory.

    For step N (N < len-1): estimated from the assistant-role delta between
    step N and step N+1.  For the last step (or if no delta available): uses
    the trajectory-internal average when available, else ``_FALLBACK_OUTPUT_TOKENS``.
    """
    n = len(steps)
    out: list[int | None] = [None] * n

    for i in range(n - 1):
        tier = ID_TO_TIER[steps[i]["gold_tier_id"]]
        out[i] = estimate_output_tokens_from_delta(
            steps[i]["messages"],
            steps[i + 1]["messages"],
            tier,
        )

    estimated = [t for t in out if t is not None and t > 0]
    avg = int(sum(estimated) / len(estimated)) if estimated else _FALLBACK_OUTPUT_TOKENS

    return [t if t is not None else avg for t in out]


def compute_router_accounting_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Trajectory-level accounting metrics with full cost model (input + cache + output).

    **Trajectory grouping**: rows are grouped by ``instance_id``.  Single-turn
    rows (``total_steps == 1``) each form their own trajectory.

    **Pass/fail at trajectory level**: a trajectory *fails* if any step has an
    ``error`` or any step's ``pred_tier_id < gold_tier_id``.

    **Cost model**: each step's cost = input + cache_read + cache_write + output,
    computed separately for baseline (always ``high``), gold, and pred paths.
    Tier switches between consecutive steps reset the cache (cold start = all
    input); same-tier continuation uses cache_read + cache_write.

    * ``pass_rate_percent``: trajectory-level pass rate (100 * passed_trajectories / total)
    * ``exact_match_rate_percent``: 100 * (all steps exact) / total trajectories
    * ``accounting_savings_score_percent``: 100 * N / D
      - D = sum over all evaluable steps of (baseline_cost - gold_cost)
      - N: pass trajectory steps contribute (baseline_cost - pred_cost);
            fail trajectory steps contribute -pred_cost
    * ``overall_score_percent``: mean of the three above; NaN if any is NaN.

    Returned keys include ``total_trajectories``, ``D_usd``, ``N_usd``, and
    ``fallback_output_tokens`` (see package README for semantics).
    """
    # -- group rows into trajectories by instance_id --
    traj_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        iid = r.get("instance_id", r["id"])
        traj_map[iid].append(r)

    # Sort each trajectory by step_index
    for iid in traj_map:
        traj_map[iid].sort(key=lambda r: r.get("step_index", 1))

    skipped_steps = sum(1 for r in rows if "error" in r)
    total_trajectories = len(traj_map)
    passed_trajectories = 0
    exact_trajectories = 0
    n_evaluable_steps = 0
    d_sum = 0.0
    n_sum = 0.0

    for iid, steps in traj_map.items():
        # Determine trajectory-level pass/fail
        has_error = any("error" in s for s in steps)
        all_step_pass = True
        all_step_exact = True

        evaluable_steps: list[dict[str, Any]] = []
        for s in steps:
            if "error" in s:
                all_step_pass = False
                all_step_exact = False
                continue
            pred = s.get("pred_tier_id")
            gold = s.get("gold_tier_id")
            if not isinstance(pred, int) or not isinstance(gold, int):
                raise ValueError(
                    "evaluable row must have int pred_tier_id and gold_tier_id "
                    f"(id={s.get('id')!r})"
                )
            if pred < gold:
                all_step_pass = False
                all_step_exact = False
            elif pred != gold:
                all_step_exact = False
            evaluable_steps.append(s)

        trajectory_passed = not has_error and all_step_pass
        trajectory_exact = not has_error and all_step_exact

        if trajectory_passed:
            passed_trajectories += 1
        if trajectory_exact:
            exact_trajectories += 1

        if not evaluable_steps:
            continue

        # Estimate output tokens for the full trajectory (including error steps
        # that we'll skip; indices in `steps` align with output_tokens list).
        output_tokens_list = _estimate_trajectory_output_tokens(steps)

        # Build a step_index -> position lookup for the sorted trajectory
        step_idx_to_pos = {s.get("step_index", 1): i for i, s in enumerate(steps)}

        for s in evaluable_steps:
            n_evaluable_steps += 1
            pos = step_idx_to_pos[s.get("step_index", 1)]
            pred_tier_id: int = s["pred_tier_id"]
            gold_tier_id: int = s["gold_tier_id"]
            pred_tier = ID_TO_TIER[pred_tier_id]
            gold_tier = ID_TO_TIER[gold_tier_id]
            msgs_curr: list[dict[str, Any]] = s.get("messages", [])
            output_tok = output_tokens_list[pos]

            # Previous step info (for cache logic)
            msgs_prev: list[dict[str, Any]] | None = None
            prev_baseline_tier: str | None = None
            prev_gold_tier: str | None = None
            prev_pred_tier: str | None = None
            if pos > 0:
                prev_s = steps[pos - 1]
                msgs_prev = prev_s.get("messages", [])
                prev_baseline_tier = _BASELINE_TIER
                prev_gold_tier = ID_TO_TIER[prev_s["gold_tier_id"]] if isinstance(prev_s.get("gold_tier_id"), int) else None
                prev_pred_tier = ID_TO_TIER[prev_s["pred_tier_id"]] if isinstance(prev_s.get("pred_tier_id"), int) else None

            # Baseline cost (always high tier)
            baseline_cost = _compute_path_step_cost(
                tier=_BASELINE_TIER,
                prev_tier=prev_baseline_tier,
                msgs_curr=msgs_curr,
                msgs_prev=msgs_prev,
                output_tokens=output_tok,
            )

            # Gold cost
            gold_cost = _compute_path_step_cost(
                tier=gold_tier,
                prev_tier=prev_gold_tier,
                msgs_curr=msgs_curr,
                msgs_prev=msgs_prev,
                output_tokens=output_tok,
            )

            # Pred cost
            pred_cost = _compute_path_step_cost(
                tier=pred_tier,
                prev_tier=prev_pred_tier,
                msgs_curr=msgs_curr,
                msgs_prev=msgs_prev,
                output_tokens=output_tok,
            )

            d_sum += baseline_cost - gold_cost

            if trajectory_passed:
                n_sum += baseline_cost - pred_cost
            else:
                n_sum -= pred_cost

    pass_rate_percent = (
        100.0 * passed_trajectories / total_trajectories
        if total_trajectories
        else float("nan")
    )
    exact_match_rate_percent = (
        100.0 * exact_trajectories / total_trajectories
        if total_trajectories
        else float("nan")
    )

    if d_sum > 0:
        accounting_savings_score_percent = 100.0 * n_sum / d_sum
        ratio_note = (
            "100 * N / D; trajectory-level pass/fail. "
            "Pass: N += baseline_cost - pred_cost; Fail: N -= pred_cost."
        )
    elif total_trajectories == 0:
        accounting_savings_score_percent = float("nan")
        ratio_note = "No trajectories."
    else:
        accounting_savings_score_percent = float("nan")
        ratio_note = "D == 0: no nominal savings vs always-high (e.g. all gold high)."

    overall_score_percent = _overall_router_score_percent(
        pass_rate_percent,
        exact_match_rate_percent,
        accounting_savings_score_percent,
    )

    return {
        "total_trajectories": total_trajectories,
        "passed_trajectories": passed_trajectories,
        "exact_match_trajectories": exact_trajectories,
        "evaluable_step_count": n_evaluable_steps,
        "skipped_step_count": skipped_steps,
        "D_usd": d_sum,
        "N_usd": n_sum,
        "pass_rate_percent": pass_rate_percent,
        "exact_match_rate_percent": exact_match_rate_percent,
        "accounting_savings_score_percent": accounting_savings_score_percent,
        "overall_score_percent": overall_score_percent,
        "fallback_output_tokens": _FALLBACK_OUTPUT_TOKENS,
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
