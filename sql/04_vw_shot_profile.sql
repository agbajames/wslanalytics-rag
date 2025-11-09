CREATE OR REPLACE VIEW public.vw_shot_profile AS
WITH per_side AS (
  SELECT
    m.season,
    m.home_team_id AS team_id,
    ms.shots_inside_box_home  AS shots_ib,
    (ms.shots_home)           AS shots_total,
    ms.big_chances_home       AS big_chances
  FROM public.matches m
  JOIN public.match_stats ms ON ms.match_id = m.match_id

  UNION ALL
  SELECT
    m.season,
    m.away_team_id AS team_id,
    ms.shots_inside_box_away  AS shots_ib,
    (ms.shots_away)           AS shots_total,
    ms.big_chances_away       AS big_chances
  FROM public.matches m
  JOIN public.match_stats ms ON ms.match_id = m.match_id
)
SELECT
  season,
  team_id,
  CASE WHEN SUM(shots_total) > 0
       THEN SUM(shots_ib)::float / SUM(shots_total)::float
       ELSE 0.0
  END AS box_share,
  COALESCE(SUM(big_chances), 0) AS big_chances
FROM per_side
GROUP BY season, team_id;
