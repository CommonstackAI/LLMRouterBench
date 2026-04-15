"""Per-tier token counting and prompt-token splitting for cost calculation.

Each public tier is bound to a representative model whose tokenizer determines
the token count.  Currently all tiers use ``tiktoken cl100k_base`` as a
documented offline approximation.  The mapping is centralised in
``TIER_TOKENIZER_ENCODING`` so that real tokenizers can be swapped in later
without touching call sites.

Representative models per tier
------------------------------
* high        — ``anthropic/claude-opus-4-6``
* mid_high    — ``anthropic/claude-haiku-4-5``
* mid         — ``minimax/minimax-m2.5``
* low         — ``deepseek/deepseek-v3.2``
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import tiktoken

from main.tiers import TIER_HIGH, TIER_LOW, TIER_MID, TIER_MID_HIGH

# ---------------------------------------------------------------------------
# Tier → tiktoken encoding name.
# All tiers currently fall back to cl100k_base because the vendors above do not
# publish a standalone offline tokenizer library.  Swap encoding names here when
# proper tokenizers become available.
# ---------------------------------------------------------------------------
TIER_TOKENIZER_ENCODING: dict[str, str] = {
    TIER_HIGH: "cl100k_base",
    TIER_MID_HIGH: "cl100k_base",
    TIER_MID: "cl100k_base",
    TIER_LOW: "cl100k_base",
}


@lru_cache(maxsize=8)
def _get_encoding(name: str) -> tiktoken.Encoding:
    return tiktoken.get_encoding(name)


def _encoding_for_tier(tier: str) -> tiktoken.Encoding:
    enc_name = TIER_TOKENIZER_ENCODING.get(tier)
    if enc_name is None:
        raise ValueError(f"No tokenizer encoding configured for tier {tier!r}")
    return _get_encoding(enc_name)


# ---------------------------------------------------------------------------
# Message-level token counting
# ---------------------------------------------------------------------------

def _message_text(msg: dict[str, Any]) -> str:
    """Extract all billable text from a single chat message.

    Handles both ``content: str`` and ``content: list[{type, text, ...}]``
    formats.  Also serialises ``tool_calls`` (function name + arguments) which
    count toward output tokens when the role is ``assistant``.
    """
    parts: list[str] = []

    content = msg.get("content")
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)

    tool_calls = msg.get("tool_calls")
    if tool_calls:
        for tc in tool_calls:
            fn = tc.get("function", tc) if isinstance(tc, dict) else tc
            if isinstance(fn, dict):
                parts.append(fn.get("name", ""))
                args = fn.get("arguments", "")
                if isinstance(args, dict):
                    parts.append(json.dumps(args, ensure_ascii=False))
                elif args:
                    parts.append(str(args))

    return "\n".join(parts)


def count_messages_tokens(messages: list[dict[str, Any]], tier: str) -> int:
    """Count total tokens in *messages* using the tokenizer bound to *tier*."""
    enc = _encoding_for_tier(tier)
    total = 0
    for msg in messages:
        total += len(enc.encode(_message_text(msg)))
        # ~4 tokens overhead per message for role / separators (OpenAI convention).
        total += 4
    total += 2  # priming tokens
    return total


def count_text_tokens(text: str, tier: str) -> int:
    """Count tokens for a raw text string."""
    enc = _encoding_for_tier(tier)
    return len(enc.encode(text))


# ---------------------------------------------------------------------------
# Semantic prefix check
# ---------------------------------------------------------------------------

_SEMANTIC_KEYS = ("role", "content", "tool_calls", "tool_call_id", "name")

_CONTENT_BLOCK_IGNORE_KEYS = frozenset({"cache_control"})


def _normalise_content(content: Any) -> str:
    """Normalise content to a plain text string for semantic comparison.

    Handles both ``str`` content and ``list[dict]`` (structured content blocks)
    as emitted by OpenClaw / Anthropic-style APIs.  OpenClaw may serialise the
    same message as a plain string in one turn and as
    ``[{"type": "text", "text": "..."}]`` in another; normalising to text makes
    the comparison format-agnostic.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content) if content is not None else ""


def _semantic_fingerprint(msg: dict[str, Any]) -> str:
    """Deterministic string capturing only the semantically meaningful fields."""
    parts: dict[str, Any] = {}
    for k in _SEMANTIC_KEYS:
        if k in msg:
            val = msg[k]
            if k == "content":
                val = _normalise_content(val)
            parts[k] = val
    return json.dumps(parts, sort_keys=True, ensure_ascii=False)


def is_semantic_prefix(msgs_short: list[dict], msgs_long: list[dict]) -> bool:
    """Return True if *msgs_short* is a semantic prefix of *msgs_long*.

    Compares only ``role``, ``content``, ``tool_calls``, ``tool_call_id``, and
    ``name`` — ignoring metadata like ``cache_control`` that OpenClaw may
    serialise inconsistently across turns.
    """
    if len(msgs_short) > len(msgs_long):
        return False
    for a, b in zip(msgs_short, msgs_long):
        if _semantic_fingerprint(a) != _semantic_fingerprint(b):
            return False
    return True


# ---------------------------------------------------------------------------
# Per-step prompt token splitting: input / cache_read / cache_write
# ---------------------------------------------------------------------------

def split_prompt_tokens_for_step(
    *,
    prev_tier: str | None,
    curr_tier: str,
    msgs_prev: list[dict[str, Any]] | None,
    msgs_curr: list[dict[str, Any]],
) -> tuple[int, int, int]:
    """Return ``(input_tokens, cache_read_tokens, cache_write_tokens)``.

    Rules
    -----
    * First step (``prev_tier is None``) or single-turn → all input.
    * Tier switch (``curr_tier != prev_tier``) → cold start, all input.
    * Same tier, semantic prefix match → cache_read for prefix, cache_write
      for delta.
    * Same tier, prefix mismatch → fallback to all input.
    """
    total = count_messages_tokens(msgs_curr, curr_tier)

    if prev_tier is None or msgs_prev is None:
        return (total, 0, 0)

    if curr_tier != prev_tier:
        return (total, 0, 0)

    if not is_semantic_prefix(msgs_prev, msgs_curr):
        return (total, 0, 0)

    prefix_tokens = count_messages_tokens(msgs_prev, curr_tier)
    delta_tokens = max(total - prefix_tokens, 0)
    return (0, prefix_tokens, delta_tokens)


# ---------------------------------------------------------------------------
# Output-token estimation from message deltas
# ---------------------------------------------------------------------------

def estimate_output_tokens_from_delta(
    msgs_curr: list[dict[str, Any]],
    msgs_next: list[dict[str, Any]],
    tier: str,
) -> int:
    """Estimate output tokens for the current step from the next step's delta.

    Only ``role=assistant`` messages in the delta count (including their
    ``tool_calls`` JSON).  ``role=tool`` / ``role=user`` messages in the delta
    are environment or user input, not model output.
    """
    enc = _encoding_for_tier(tier)
    n_curr = len(msgs_curr)
    delta = msgs_next[n_curr:]

    tokens = 0
    for msg in delta:
        if msg.get("role") == "assistant":
            tokens += len(enc.encode(_message_text(msg)))
            tokens += 4  # per-message overhead
    return tokens
