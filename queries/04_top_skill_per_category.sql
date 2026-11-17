-- Window function: rank skills inside each category (languages, BI tools, cloud...).
WITH counts AS (
    SELECT s.category, s.name, COUNT(*) AS jobs
    FROM job_skills js
    JOIN skills s ON s.skill_id = js.skill_id
    WHERE js.method = 'keyword'
    GROUP BY s.category, s.name
)
SELECT
    category,
    name AS skill,
    jobs,
    RANK() OVER (PARTITION BY category ORDER BY jobs DESC) AS rank_in_category
FROM counts
ORDER BY category, rank_in_category;
