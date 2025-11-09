# app/llm.py
"""
LLM wrapper: OpenAI async client with focused retry + timeout.

Why this exists:
- Centralizes model calls.
- Retries only transient failures (rate limits, timeouts, network hiccups).
- Keeps defaults (temperature/tokens) in one place for consistency.
"""

from __future__ import annotations

from typing import Optional

from openai import (
    AsyncOpenAI,
    APIError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from .settings import settings


# --- Basic validation (fail fast if no key) ---------------------------------
if not settings.OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Provide it in your .env to run generation."
    )

# --- Client (async) ----------------------------------------------------------
# Per-request timeouts are passed on each call; client holds base config.
_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

_DEFAULT_TEMPERATURE: float = 0.2
_DEFAULT_TIMEOUT: float = 30.0  # seconds


# --- Generate ---------------------------------------------------------------
@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=6),
    retry=retry_if_exception_type((
        APIConnectionError,  # network/DNS/TLS
        APITimeoutError,     # request timed out
        RateLimitError,      # 429s
        APIError,            # 5xx
    )),
)
async def generate(
    model: Optional[str],
    system: str,
    user: str,
    *,
    temperature: float = _DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = None,
    request_timeout: float = _DEFAULT_TIMEOUT,
) -> str:
    """
    Call OpenAI chat completions and return the top message content.

    Raises on persistent failure after retries.
    """
    use_model = (model or settings.MODEL).strip()
    use_max_tokens = max_tokens if max_tokens is not None else settings.MAX_TOKENS

    resp = await _client.chat.completions.create(
        model=use_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,       # lower == more deterministic
        max_tokens=use_max_tokens,
        timeout=request_timeout,       # hard per-request timeout
    )

    # Defensive: handle empty choices/messages gracefully.
    if not resp.choices:
        return ""
    msg = resp.choices[0].message
    return (msg.content or "").strip()
