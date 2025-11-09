CREATE OR REPLACE VIEW public.vw_gk_xgot AS
SELECT
  m.season,
  p.player_id,
  pl.name AS player_name,
  p.team_id,
  -- aggregate goals_prevented across the season (positive = above expectation)
  COALESCE(SUM(p.goals_prevented), 0.0)::float AS xgot_delta,
  COALESCE(SUM(p.minutes), 0)                 AS minutes,
  COALESCE(SUM(p.goals_conceded), 0)          AS goals_conceded
FROM public.player_match_stats p
JOIN public.matches m ON m.match_id = p.match_id
JOIN public.players pl ON pl.player_id = p.player_id
WHERE p.is_goalkeeper = TRUE
GROUP BY m.season, p.player_id, pl.name, p.team_id
-- Optional: keep reasonably used keepers
HAVING COALESCE(SUM(p.minutes), 0) >= 180;
