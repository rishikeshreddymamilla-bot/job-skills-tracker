-- Bias check: where was each skill found? A high pct_title_only means the count
-- mostly comes from job titles, which our search terms influence (selection bias).
SELECT
    s.name                                                       AS skill,
    COUNT(*) FILTER (WHERE js.found_in = 'title')                AS title_only,
    COUNT(*) FILTER (WHERE js.found_in = 'description')          AS description_only,
    COUNT(*) FILTER (WHERE js.found_in = 'both')                 AS both_places,
    ROUND(100.0 * COUNT(*) FILTER (WHERE js.found_in = 'title') / COUNT(*), 1) AS pct_title_only
FROM job_skills js
JOIN skills s ON s.skill_id = js.skill_id
WHERE js.method = 'keyword'
GROUP BY s.name
ORDER BY COUNT(*) DESC;
