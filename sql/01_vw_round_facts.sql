-- Round Facts View: Match results with team names and stats
-- Purpose: Provides complete match data for a given season and round

CREATE OR REPLACE VIEW public.vw_round_facts AS
SELECT
    m.season,
    m.round,
    m.match_id,
    m.utc_kickoff,
    m.stadium_name,
    m.attendance,
    ht.team_id AS home_team_id,
    at.team_id AS away_team_id,
    ht.name     AS home_team,
    at.name     AS away_team,

    m.home_score,
    m.away_score,

    /* avoid NULLs showing up blank in the API */
    COALESCE(ms.xg_home,   0.0) AS xg_home,
    COALESCE(ms.xg_away,   0.0) AS xg_away,
    COALESCE(ms.xgot_home, 0.0) AS xgot_home,
    COALESCE(ms.xgot_away, 0.0) AS xgot_away,

    COALESCE(ms.shots_home, 0)  AS shots_home,
    COALESCE(ms.shots_away, 0)  AS shots_away,

    m.finished
FROM matches m
JOIN teams ht ON ht.team_id = m.home_team_id
JOIN teams at ON at.team_id = m.away_team_id
LEFT JOIN match_stats ms ON ms.match_id = m.match_id;

