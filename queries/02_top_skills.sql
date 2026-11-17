-- Skill demand: how many jobs mention each skill, and what share of all jobs that is.
-- jobs_in_description excludes title-only matches, which reduces search-term bias.
SELECT
    s.name                                                         AS skill,
    s.category,
    COUNT(*)                                                       AS jobs_mentioning,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM jobs), 1)       AS pct_of_jobs,
    COUNT(*) FILTER (WHERE js.found_in IN ('description', 'both')) AS jobs_in_description
FROM job_skills js
JOIN skills s ON s.skill_id = js.skill_id
WHERE js.method = 'keyword'
GROUP BY s.name, s.category
ORDER BY jobs_mentioning DESC;
