CREATE OR REPLACE VIEW public.vw_set_piece_share AS
WITH per_side AS (
  SELECT
    m.season,
    m.home_team_id AS team_id,
    ms.xg_set_play_home AS xg_sp,
    ms.xg_home          AS xg_total
  FROM public.matches m
  JOIN public.match_stats ms ON ms.match_id = m.match_id

  UNION ALL
  SELECT
    m.season,
    m.away_team_id AS team_id,
    ms.xg_set_play_away AS xg_sp,
    ms.xg_away          AS xg_total
  FROM public.matches m
  JOIN public.match_stats ms ON ms.match_id = m.match_id
)
SELECT
  season,
  team_id,
  CASE WHEN SUM(xg_total) > 0
       THEN SUM(xg_sp)::float / SUM(xg_total)::float
       ELSE 0.0
  END AS xg_sp_share
FROM per_side
GROUP BY season, team_id;
