-- Player Leaders View: Per-90 statistics
-- Purpose: Compare players fairly regardless of minutes played

CREATE OR REPLACE VIEW public.vw_player_leaders_90 AS
SELECT
    m.season,
    s.player_id,
    p.name AS player_name,
    s.team_id,
    t.name AS team,
    SUM(s.minutes) AS minutes,
    SUM(s.goals) AS goals,
    SUM(s.assists) AS assists,
    SUM(s.shots_total) AS shots,
    SUM(s.shots_on_target) AS shots_on_target,
    SUM(s.xg) AS xg,
    SUM(s.xa) AS xa,
    CASE WHEN SUM(s.minutes) > 0 
         THEN (SUM(s.goals) * 90.0 / SUM(s.minutes)) 
         ELSE 0 END AS g90,
    CASE WHEN SUM(s.minutes) > 0 
         THEN (SUM(s.assists) * 90.0 / SUM(s.minutes)) 
         ELSE 0 END AS a90,
    CASE WHEN SUM(s.minutes) > 0 
         THEN (SUM(s.xg) * 90.0 / SUM(s.minutes)) 
         ELSE 0 END AS xg90,
    CASE WHEN SUM(s.minutes) > 0 
         THEN (SUM(s.xa) * 90.0 / SUM(s.minutes)) 
         ELSE 0 END AS xa90
FROM player_match_stats s
JOIN matches m ON m.match_id = s.match_id
JOIN players p ON p.player_id = s.player_id
JOIN teams t ON t.team_id = s.team_id
GROUP BY m.season, s.player_id, p.name, s.team_id, t.name
HAVING SUM(s.minutes) >= 300;