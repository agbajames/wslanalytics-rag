-- Team Form View: Last 5 games statistics
-- Purpose: Rolling window of points, goals for/against

CREATE OR REPLACE VIEW public.vw_team_form_5 AS
WITH past AS (
    SELECT
        m.season,
        m.utc_kickoff,
        t.team_id,
        t.name AS team,
        CASE WHEN t.team_id = m.home_team_id THEN m.home_score ELSE m.away_score END AS gf,
        CASE WHEN t.team_id = m.home_team_id THEN m.away_score ELSE m.home_score END AS ga,
        CASE
            WHEN (t.team_id = m.home_team_id AND m.home_score > m.away_score)
                OR (t.team_id = m.away_team_id AND m.away_score > m.home_score) THEN 3
            WHEN m.home_score = m.away_score THEN 1
            ELSE 0
        END AS pts
    FROM matches m
    JOIN teams t ON t.team_id IN (m.home_team_id, m.away_team_id)
    WHERE m.finished = true
)
SELECT
    p.season,
    p.team_id,
    p.team,
    AVG(p.pts) OVER w AS pts_avg,
    SUM(p.pts) OVER w AS pts_5,
    SUM(p.gf) OVER w AS gf_5,
    SUM(p.ga) OVER w AS ga_5
FROM past p
WINDOW w AS (
    PARTITION BY p.season, p.team_id
    ORDER BY p.utc_kickoff
    ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
);
