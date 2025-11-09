from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .schemas import (
    SummariseParams,
    SummariseResponse,
    RenderedOutputs,
    FactsPanel,
    FactItem,
)
from .deps import get_pool, fetch_dicts
from .render import render_template
from .llm import generate
from .guards import assert_numbers_in_facts


# --- App setup ---------------------------------------------------------------

APP_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = APP_ROOT / "prompts"

app = FastAPI(title="WSL Summariser")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in prod if needed
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    # Minimal, non-sensitive health info
    return {"ok": True}


# --- Helpers -----------------------------------------------------------------

def _get(m: dict, *keys, default=None):
    """Return first present key (handles DB/file-mode variants)."""
    for k in keys:
        if k in m and m[k] is not None:
            return m[k]
    return default

def _fmt_num(v, ndp: int = 2):
    """Format numbers neatly; return em dash for empty."""
    try:
        return f"{float(v):.{ndp}f}"
    except Exception:
        return "—"

def _expand_facts_round(rf, tf, leaders, shots, setp, gk):
    """Convert raw DB results into a facts panel (labels + values + source)."""
    facts: List[Dict[str, Any]] = []

    # Match facts
    for m in rf or []:
        home = _get(m, "home_team", "homeTeam", "home", default="Home")
        away = _get(m, "away_team", "awayTeam", "away", default="Away")
        home_score = _get(m, "home_score", "homeScore", "hs", default="")
        away_score = _get(m, "away_score", "awayScore", "as", default="")
        xg_home = _get(m, "xg_home", "xgHome", "xg_h", default="")
        xg_away = _get(m, "xg_away", "xgAway", "xg_a", default="")
        xgot_home = _get(m, "xgot_home", "xgotHome", default="")
        xgot_away = _get(m, "xgot_away", "xgotAway", default="")
        shots_home = _get(m, "shots_home", "shotsHome", default="")
        shots_away = _get(m, "shots_away", "shotsAway", default="")
        attendance = _get(m, "attendance", "att", default="")

        facts += [
            {"label": f"{home} vs {away} score", "value": f"{home_score}-{away_score}", "source": "vw_round_facts"},
            {"label": f"{home} xG",   "value": _fmt_num(xg_home),   "source": "vw_round_facts"},
            {"label": f"{away} xG",   "value": _fmt_num(xg_away),   "source": "vw_round_facts"},
            {"label": f"{home} xGOT", "value": _fmt_num(xgot_home), "source": "vw_round_facts"},
            {"label": f"{away} xGOT", "value": _fmt_num(xgot_away), "source": "vw_round_facts"},
            {"label": f"{home} shots", "value": f"{shots_home}", "source": "vw_round_facts"},
            {"label": f"{away} shots", "value": f"{shots_away}", "source": "vw_round_facts"},
            {"label": "Attendance", "value": f"{attendance}", "source": "vw_round_facts"},
        ]

    # Team form
    for r in tf or []:
        team = _get(r, "team", "team_name", default="Team")
        facts += [
            {"label": f"{team} points(5)", "value": f"{_get(r, 'pts_5', 'pts5', default='')}", "source": "vw_team_form_5"},
            {"label": f"{team} GF(5)",     "value": f"{_get(r, 'gf_5', 'gf5', default='')}",  "source": "vw_team_form_5"},
            {"label": f"{team} GA(5)",     "value": f"{_get(r, 'ga_5', 'ga5', default='')}",  "source": "vw_team_form_5"},
        ]

    # Player leaders (top 20)
    def _f(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    for L in (leaders or [])[:20]:
        player = _get(L, "player_name", "name", default="Player")
        facts += [
            {"label": f"{player} g/90",    "value": f"{_f(_get(L,'g90','g_90')):.2f}", "source": "vw_player_leaders_90"},
            {"label": f"{player} xG/90",   "value": f"{_f(_get(L,'xg90','xg_90')):.2f}", "source": "vw_player_leaders_90"},
            {"label": f"{player} minutes", "value": f"{int(_f(_get(L,'minutes','mins')))}", "source": "vw_player_leaders_90"},
        ]

    # Shot profiles
    for s in shots or []:
        tid = _get(s, "team_id", "teamId", default="T")
        facts += [
            {"label": f"Team {tid} box share",   "value": f"{_f(_get(s,'box_share','boxShare')):.2f}", "source": "vw_shot_profile"},
            {"label": f"Team {tid} big chances", "value": f"{_get(s,'big_chances','bigChances','')}",  "source": "vw_shot_profile"},
        ]

    # Set pieces
    for sp in setp or []:
        tid = _get(sp, "team_id", "teamId", default="T")
        facts += [
            {"label": f"Team {tid} xG set-pieces share", "value": f"{_f(_get(sp,'xg_sp_share','xgSetPieceShare')):.2f}", "source": "vw_set_piece_share"},
        ]

    # GK
    for gkr in (gk or [])[:10]:
        name = _get(gkr, "player_name", "name", default="GK")
        facts += [
            {"label": f"{name} xGOTΔ", "value": f"{_f(_get(gkr,'xgot_delta','xgotDelta')):.2f}", "source": "vw_gk_xgot"},
        ]

    return facts

def _headline_and_bullets(rf, is_preview: bool = False, round_no: str = "?"):
    if not rf:
        headline = "Round Preview" if is_preview else "Round Recap"
        bullets = ["No fixtures found."]
        return headline, bullets

    if not is_preview:
        def top_tuple(m):
            h = m.get("xg_home") or 0
            a = m.get("xg_away") or 0
            return max((h, m["home_team"]), (a, m["away_team"]), key=lambda t: t[0])

        best = max(rf, key=lambda m: top_tuple(m)[0])
        xg_val, team_name = top_tuple(best)
        headline = f"Margins matter in Round {round_no}"
        bullets = [
            f"Top xG in round: {team_name} ({xg_val:.2f})",
            "Best form over last five: see Facts Panel",
            "Set-piece signals emerging across the league.",
        ]
        return headline, bullets

    headline = f"Gameweek {round_no} Preview: fault lines & margins"
    bullets = ["Win probabilities & likely scorelines", "Key matchups & trends", "Form vs underlying metrics"]
    return headline, bullets


# --- Recap endpoint ----------------------------------------------------------

@app.post("/summarise/round", response_model=SummariseResponse)
async def summarise_round(p: SummariseParams):
    rf, tf, leaders, shots, setp, gk, h2h = (
        p.round_facts, p.team_form, p.leaders, p.shot_profiles, p.set_piece, p.gk, p.h2h
    )

    # DB-backed mode
    db_mode = bool(p.season and p.round and rf is None)
    if db_mode:
        pool = await get_pool()
        if pool is None:
            raise HTTPException(status_code=503, detail="DB not configured. Provide SUPABASE_DB_URL or send file-mode data.")

        # Round facts
        rf = await fetch_dicts(
            pool,
            "SELECT * FROM public.vw_round_facts WHERE season=$1 AND round=$2 ORDER BY utc_kickoff",
            p.season, p.round,
        )
        if not rf:
            raise HTTPException(status_code=404, detail=f"No matches found in vw_round_facts for season={p.season}, round={p.round}.")

        # Team form: pick latest row per team in this round
        tf = await fetch_dicts(
            pool,
            """
            WITH teams_in_round AS (
              SELECT DISTINCT home_team_id AS team_id FROM public.vw_round_facts WHERE season=$1 AND round=$2
              UNION
              SELECT DISTINCT away_team_id FROM public.vw_round_facts WHERE season=$1 AND round=$2
            )
            SELECT DISTINCT ON (t.team_id)
                   f.season, f.team_id, f.team, f.pts_avg, f.pts_5, f.gf_5, f.ga_5, f.utc_kickoff
            FROM   teams_in_round t
            JOIN   public.vw_team_form_5 f
                   ON f.season=$1 AND f.team_id=t.team_id
            ORDER BY t.team_id, f.utc_kickoff DESC;
            """,
            p.season, p.round,
        )

        # Leaders
        leaders = await fetch_dicts(pool, "SELECT * FROM public.vw_player_leaders_90 WHERE season=$1 LIMIT 50", p.season)

        # Shot profile for teams in round
        shots = await fetch_dicts(
            pool,
            """
            SELECT sp.* FROM public.vw_shot_profile sp
            WHERE season=$1 AND team_id IN (
                SELECT home_team_id FROM public.vw_round_facts WHERE season=$1 AND round=$2
                UNION 
                SELECT away_team_id FROM public.vw_round_facts WHERE season=$1 AND round=$2
            )
            """,
            p.season, p.round,
        )

        # Set-piece share
        setp = await fetch_dicts(
            pool,
            """
            SELECT * FROM public.vw_set_piece_share 
            WHERE season=$1 AND team_id IN (
                SELECT home_team_id FROM public.vw_round_facts WHERE season=$1 AND round=$2
                UNION 
                SELECT away_team_id FROM public.vw_round_facts WHERE season=$1 AND round=$2
            )
            """,
            p.season, p.round,
        )

        # GK xGOT
        gk = await fetch_dicts(pool, "SELECT * FROM public.vw_gk_xgot WHERE season=$1 LIMIT 30", p.season)
        h2h = []

    # File-mode guard
    if not rf:
        rendered = RenderedOutputs(
            substack_md="", thread_text="", alt_text="", seo_yaml="", facts_panel=FactsPanel(items=[])
        )
        return SummariseResponse(inputs=p, outputs=rendered, citations=[])

    # Build facts & prompt
    facts = _expand_facts_round(rf, tf, leaders, shots, setp, gk)
    jd = lambda o: json.dumps(o, default=str)
    ctx = {
        "angle": p.angle or "none",
        "round_facts_json": jd(rf),
        "team_form_json": jd(tf or []),
        "leaders_json": jd(leaders or []),
        "shot_profiles_json": jd(shots or []),
        "set_piece_json": jd(setp or []),
        "gk_json": jd(gk or []),
        "h2h_json": jd(h2h or []),
    }

    system = "You are a precise, citation-aware sports analyst for WSLAnalytics."
    prompt = (PROMPTS_DIR / "summarise_round.prompt").read_text(encoding="utf-8")
    user = (
        prompt
        .replace("{{ angle or 'none' }}", ctx["angle"])
        .replace("{{ round_facts_json }}", ctx["round_facts_json"])
        .replace("{{ team_form_json }}", ctx["team_form_json"])
        .replace("{{ leaders_json }}", ctx["leaders_json"])
        .replace("{{ shot_profiles_json }}", ctx["shot_profiles_json"])
        .replace("{{ set_piece_json }}", ctx["set_piece_json"])
        .replace("{{ gk_json }}", ctx["gk_json"])
        .replace("{{ h2h_json }}", ctx["h2h_json"])
    )

    body = await generate(settings.MODEL, system, user)

    # Validate numbers used
    missing = assert_numbers_in_facts(body, facts)
    if missing:
        body += "\n\n[Note: Certain figures omitted to maintain accuracy.]"

    round_no = p.round or rf[0].get("round", "?")
    headline, bullets = _headline_and_bullets(rf, is_preview=False, round_no=str(round_no))
    primary_teams = list({(m.get("home_team") or m.get("home")) for m in rf} | {(m.get("away_team") or m.get("away")) for m in rf})

    rendered = RenderedOutputs(
        substack_md=render_template("substack_recap.md.j2", round=round_no, headline=headline, body=body, facts=facts),
        thread_text=render_template("thread.txt.j2", headline=headline, bullets=bullets),
        alt_text=render_template("alt_text.txt.j2", round=round_no, primary_teams=primary_teams),
        seo_yaml=render_template("seo.yaml.j2", round=round_no, headline=headline),
        facts_panel=FactsPanel(items=[FactItem(**f) for f in facts]),
    )
    return SummariseResponse(inputs=p, outputs=rendered, citations=[f["source"] for f in facts])


# --- Preview endpoint (as you had) ------------------------------------------

@app.post("/summarise/preview", response_model=SummariseResponse)
async def summarise_preview(p: SummariseParams):
    fixtures = p.preview_fixtures

    if (p.season and p.round) and (fixtures is None):
        pool = await get_pool()
        if pool:
            rows = await fetch_dicts(
                pool,
                "SELECT rpc_round_fixtures_preview($1,$2,'WSL') as js",
                p.round, p.season
            )
            if rows and rows[0].get("js"):
                fixtures = rows[0]["js"] if isinstance(rows[0]["js"], list) else rows[0]["js"]

    if not fixtures:
        rendered = RenderedOutputs(
            substack_md="", thread_text="", alt_text="", seo_yaml="", facts_panel=FactsPanel(items=[])
        )
        return SummariseResponse(inputs=p, outputs=rendered, citations=[])

    facts: List[Dict[str, Any]] = []
    for f in fixtures:
        home, away = f.get("home"), f.get("away")
        wp = f.get("win_probabilities") or f.get("probabilities") or {}
        mls = f.get("most_likely_scorelines", [])[:3]
        venue = f.get("venue", "")
        broadcast = f.get("broadcast", "")
        facts += [
            {"label": f"{home} win %", "value": f"{wp.get('home','')}", "source": "rpc_round_fixtures_preview"},
            {"label": "Draw %", "value": f"{wp.get('draw','')}", "source": "rpc_round_fixtures_preview"},
            {"label": f"{away} win %", "value": f"{wp.get('away','')}", "source": "rpc_round_fixtures_preview"},
            {"label": "Top scoreline 1", "value": f"{mls[0] if len(mls)>0 else ''}", "source": "rpc_round_fixtures_preview"},
            {"label": "Top scoreline 2", "value": f"{mls[1] if len(mls)>1 else ''}", "source": "rpc_round_fixtures_preview"},
            {"label": "Top scoreline 3", "value": f"{mls[2] if len(mls)>2 else ''}", "source": "rpc_round_fixtures_preview"},
            {"label": "Venue", "value": f"{venue}", "source": "rpc_round_fixtures_preview"},
            {"label": "Broadcast", "value": f"{broadcast}", "source": "rpc_round_fixtures_preview"},
        ]

    system = "You are a precise, citation-aware sports analyst for WSLAnalytics."
    prompt = (PROMPTS_DIR / "summarise_preview.prompt").read_text(encoding="utf-8")
    user = (
        prompt
        .replace("{{ angle or 'none' }}", p.angle or "none")
        .replace("{{ preview_fixtures_json }}", json.dumps(fixtures, default=str))
    )

    body = await generate(settings.MODEL, system, user)
    missing = assert_numbers_in_facts(body, facts)
    if missing:
        body += "\n\n[Note: Certain figures omitted to maintain accuracy.]"

    round_no = p.round or "?"
    headline = f"Gameweek {round_no} Preview: fault lines & margins"
    bullets = ["Win probabilities & likely scorelines", "Key matchups & trends", "Form vs underlying metrics"]
    primary_teams = list({f.get("home") for f in fixtures} | {f.get("away") for f in fixtures})

    rendered = RenderedOutputs(
        substack_md=render_template("substack_preview.md.j2", round=round_no, headline=headline, body=body, facts=facts),
        thread_text=render_template("thread.txt.j2", headline=headline, bullets=bullets),
        alt_text=render_template("alt_text.txt.j2", round=round_no, primary_teams=primary_teams),
        seo_yaml=render_template("seo.yaml.j2", round=round_no, headline=headline),
        facts_panel=FactsPanel(items=[FactItem(**f) for f in facts]),
    )
    return SummariseResponse(inputs=p, outputs=rendered, citations=[f["source"] for f in facts])
