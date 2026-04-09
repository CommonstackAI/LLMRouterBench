"""Nominal output-token pricing (RouterBench v2 guide Section 11.2). Model->tier mapping is for harness code only."""

from __future__ import annotations

from dataclasses import dataclass

from main.tiers import PUBLIC_TIERS, TIER_HIGH, TIER_LOW, TIER_MID, TIER_MID_HIGH

# USD per 1M completion (output) tokens, by public English tier label.
TIER_OUTPUT_USD_PER_1M: dict[str, float] = {
    TIER_LOW: 0.5,
    TIER_MID: 1.2,
    TIER_MID_HIGH: 3.0,
    TIER_HIGH: 20.0,
}

_MODEL_TO_TIER: dict[str, str] = {
    "anthropic/claude-opus-4-6": TIER_HIGH,
    "openai/gpt-5.4": TIER_HIGH,
    "openai/gpt-5.4-2026-03-05": TIER_HIGH,
    "anthropic/claude-haiku-4-5": TIER_MID_HIGH,
    "google/gemini-3-flash-preview": TIER_MID_HIGH,
    "gemini/gemini-3-flash-preview": TIER_MID_HIGH,
    "qwen/qwen3.5-397b-a17b": TIER_MID_HIGH,
    "minimax/minimax-m2.5": TIER_MID,
    "qwen/qwen3.5-27b": TIER_MID,
    "qwen/qwen3-coder": TIER_MID,
    "deepseek/deepseek-v3.2": TIER_LOW,
    "z-ai/glm-4.5-air": TIER_LOW,
    "qwen/qwen3.5-9b": TIER_LOW,
}


def model_to_tier(model_id: str) -> str:
    if model_id not in _MODEL_TO_TIER:
        raise ValueError(f"Unknown model_id for tier mapping: {model_id!r}")
    return _MODEL_TO_TIER[model_id]


@dataclass(frozen=True)
class StepCost:
    completion_tokens: int
    model: str | None = None
    tier: str | None = None

    def resolved_tier(self) -> str:
        if self.tier is not None:
            if self.tier not in TIER_OUTPUT_USD_PER_1M:
                raise ValueError(f"Unknown tier: {self.tier!r}")
            return self.tier
        if self.model is None:
            raise ValueError("StepCost requires either model or tier")
        return model_to_tier(self.model)


def step_nominal_cost_usd(completion_tokens: int, tier: str) -> float:
    if tier not in TIER_OUTPUT_USD_PER_1M:
        raise ValueError(f"Unknown tier: {tier!r}; expected one of {PUBLIC_TIERS}")
    if completion_tokens < 0:
        raise ValueError("completion_tokens must be non-negative")
    return completion_tokens * TIER_OUTPUT_USD_PER_1M[tier] / 1_000_000


def path_nominal_cost_usd(steps: list[StepCost]) -> float:
    total = 0.0
    for s in steps:
        total += step_nominal_cost_usd(s.completion_tokens, s.resolved_tier())
    return total
