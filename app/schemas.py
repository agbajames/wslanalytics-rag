# app/schemas.py
"""
Data schemas: type-safe models for API requests/responses.

Design:
- Pydantic v2 with strict config (extra fields forbidden).
- Clear descriptions for API docs.
- Backwards-compatible field names for existing code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypeAlias

from pydantic import BaseModel, Field, ConfigDict

# Reusable alias for arbitrary JSON objects in lists
JSONDict: TypeAlias = Dict[str, Any]


class _StrictModel(BaseModel):
    """Base: forbid unknown fields, strip whitespace in strings."""
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
        arbitrary_types_allowed=False,
    )


class SummariseParams(_StrictModel):
    """Input parameters for article generation."""

    # Database mode (fetch from Supabase views)
    season: Optional[str] = Field(
        default=None,
        description="Season label (e.g., '2024-25'). When set with 'round', enables DB mode.",
        examples=["2024-25", "2023-24"],
    )
    round: Optional[int] = Field(
        default=None,
        ge=1,
        description="Round number (>=1). When set with 'season', enables DB mode.",
        examples=[1, 2, 3],
    )
    match_id: Optional[str] = Field(
        default=None,
        description="Optional match identifier (reserved for future single-match endpoints).",
    )
    angle: Optional[str] = Field(
        default=None,
        description="Optional editorial 'angle' to steer the summary tone/focus.",
        examples=["set-pieces focus", "form vs xG"],
    )

    # File mode (caller supplies data directly; DB is skipped)
    round_facts: Optional[List[JSONDict]] = Field(
        default=None,
        description="Match facts rows for the round (shape mirrors vw_round_facts).",
    )
    team_form: Optional[List[JSONDict]] = Field(
        default=None,
        description="Team form rows (shape mirrors vw_team_form_5).",
    )
    leaders: Optional[List[JSONDict]] = Field(
        default=None,
        description="Per-90 player leaders (shape mirrors vw_player_leaders_90).",
    )
    shot_profiles: Optional[List[JSONDict]] = Field(
        default=None,
        description="Team shot profile rows (shape mirrors vw_shot_profile).",
    )
    set_piece: Optional[List[JSONDict]] = Field(
        default=None,
        description="Set-piece share rows (shape mirrors vw_set_piece_share).",
    )
    gk: Optional[List[JSONDict]] = Field(
        default=None,
        description="Goalkeeper xGOT delta rows (shape mirrors vw_gk_xgot).",
    )
    h2h: Optional[List[JSONDict]] = Field(
        default=None,
        description="Optional head-to-head details for fixtures.",
    )
    preview_fixtures: Optional[List[JSONDict]] = Field(
        default=None,
        description="For /summarise/preview: fixtures with probabilities/scorelines.",
    )


class FactItem(_StrictModel):
    """A single fact with source attribution."""
    label: str = Field(..., description="Human-readable stat label (e.g., 'Arsenal xG').")
    value: str = Field(..., description="Value as text (e.g., '1.80', '3-1', '28%').")
    source: str = Field(..., description="Origin of the fact (e.g., 'vw_round_facts').")


class FactsPanel(_StrictModel):
    """Collection of facts used in article generation."""
    items: List[FactItem] = Field(default_factory=list, description="Ordered facts.")


class RenderedOutputs(_StrictModel):
    """All rendered formats for the generated article."""
    substack_md: str = Field(..., description="Markdown body for Substack.")
    thread_text: str = Field(..., description="Social thread text.")
    alt_text: str = Field(..., description="Alt-text for header/hero image.")
    seo_yaml: str = Field(..., description="SEO/front-matter metadata (YAML).")
    facts_panel: FactsPanel = Field(..., description="Ground-truth facts panel.")


class SummariseResponse(_StrictModel):
    """Complete API response payload."""
    inputs: SummariseParams = Field(..., description="Echo of input parameters.")
    outputs: RenderedOutputs = Field(..., description="All generated artifacts.")
    citations: List[str] = Field(default_factory=list, description="Source identifiers used.")
