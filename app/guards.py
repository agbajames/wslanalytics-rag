# app/guards.py
"""
Guardrails: numeric fact-checking for generated text.

Ensures every number in the model output is present in the provided facts,
reducing the risk of numeric hallucinations.

Notes:
- Tolerates formatting differences (commas, percent signs, rounding).
- Understands scorelines like "3-1" or "2–2" and indexes both sides.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Set, Tuple

# Integers/decimals with optional comma grouping and optional percent sign
_NUM_RE = re.compile(r"""
    (?<![A-Za-z])             # avoid parts of words
    -?                        # optional sign
    \d{1,3}                   # 1-3 digits
    (?:,\d{3})*               # optional thousand groups
    (?:\.\d+)?                # optional decimal part
    %?                        # optional percent
    (?![A-Za-z])              # avoid parts of words
""", re.VERBOSE)

# Scorelines like "2-1", "3 – 3" (hyphen/en dash)
_SCORE_RE = re.compile(r"\b(\d+)\s*[-–]\s*(\d+)\b")

# Whitelist numbers often referenced but not "facts"
ALLOW: Set[str] = {
    # minutes / common intervals
    "120","90","75","60","45","30","25","20","15","10","5","3","2","1",
    # extra time markers, jersey odds & ends, etc. keep small
    # years (a small rolling window)
    "2019","2020","2021","2022","2023","2024","2025","2026",
}

# ---------------------------------------------------------------------------

def numbers_from_text(text: str) -> List[str]:
    """
    Extract numeric tokens and percent-bearing numbers from text.
    Includes plain numbers and '23%' but NOT scorelines; see scorelines_from_text.
    """
    return _NUM_RE.findall(text or "")

def scorelines_from_text(text: str) -> List[Tuple[str, str]]:
    """
    Extract scorelines like '2-1' or '3–3' and return pairs ('2','1').
    """
    return _SCORE_RE.findall(text or "")

def _normalize_number_token(tok: str) -> str:
    """
    Normalize number token:
    - strip commas and percent signs
    - keep sign and decimal
    - keep leading zeros behavior consistent via float round-trip where safe
    """
    s = tok.replace(",", "").rstrip("%")
    # leave as-is if it's just a bare integer/float after cleanup
    return s

def _variants(n: str) -> Set[str]:
    """
    Generate tolerant variants for a numeric string:
    - raw
    - rounded to 0, 1, 2 dp (string)
    This improves matching when facts/text differ by minor rounding.
    """
    out = {n}
    try:
        f = float(n)
    except Exception:
        return out
    # integer and rounded forms
    out.add(str(int(round(f))))                      # 0 dp integer-ish
    out.add(f"{round(f, 1):.1f}")
    out.add(f"{round(f, 2):.2f}")
    # Preserve raw without trailing .0 if present
    if "." in n and n.rstrip("0").rstrip("."):
        out.add(n.rstrip("0").rstrip("."))
    return out

def _index_fact_numbers(facts: Iterable[Dict[str, Any]]) -> Set[str]:
    """
    Build a set of normalized/tolerant numeric strings from facts' 'value' fields.
    - Parses simple numbers and scorelines.
    - Adds tolerant variants for matching.
    """
    bag: Set[str] = set()
    for f in facts or []:
        v = str(f.get("value", "") or "")
        # 1) scorelines: index both numbers
        for a, b in scorelines_from_text(v):
            for part in (a, b):
                norm = _normalize_number_token(part)
                bag.update(_variants(norm))
        # 2) standalone numbers (percents included)
        for tok in numbers_from_text(v):
            norm = _normalize_number_token(tok)
            bag.update(_variants(norm))
    return bag

def _unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

# ---------------------------------------------------------------------------

def assert_numbers_in_facts(body: str, facts: List[Dict[str, Any]]) -> List[str]:
    """
    Return a list of problematic numeric tokens found in `body`
    that are NOT present in `facts`.

    Strategy:
    - Extract scoreline numbers and plain numbers from body.
    - Normalise and compare against an index built from facts' values.
    - Allow a small ALLOW-set (e.g., minutes/years).
    - Output unique tokens in appearance order for easy debugging.

    Parameters
    ----------
    body : str
        Generated article text.
    facts : List[Dict[str, Any]]
        Facts panel entries (label/value/source). Only 'value' is used.

    Returns
    -------
    List[str]
        Unique numeric tokens from `body` that are not found in the facts.
        Empty list => all numeric content is grounded.
    """
    fact_index = _index_fact_numbers(facts)

    missing: List[str] = []

    # 1) scorelines in body
    for a, b in scorelines_from_text(body or ""):
        for part in (a, b):
            norm = _normalize_number_token(part)
            if norm not in ALLOW and not (_variants(norm) & fact_index):
                missing.append(part)

    # 2) standalone tokens in body
    for tok in numbers_from_text(body or ""):
        raw = tok
        norm = _normalize_number_token(tok)
        # If this is a percentage like "28%", also try raw percent-less
        if norm in ALLOW or raw.rstrip("%") in ALLOW:
            continue
        if not (_variants(norm) & fact_index):
            missing.append(raw)

    return _unique_preserve_order(missing)
