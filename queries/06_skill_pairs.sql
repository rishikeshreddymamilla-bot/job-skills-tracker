-- Self-join: which skills are asked for together in the same posting?
-- a.skill_id < b.skill_id keeps each pair once (SQL+Python, not also Python+SQL) and skips a skill paired with itself.
SELECT
    sa.name  AS skill_a,
    sb.name  AS skill_b,
    COUNT(*) AS jobs_together
FROM job_skills a
JOIN job_skills b
  ON  a.job_id   = b.job_id
  AND a.skill_id < b.skill_id
  AND a.method   = 'keyword'
  AND b.method   = 'keyword'
JOIN skills sa ON sa.skill_id = a.skill_id
JOIN skills sb ON sb.skill_id = b.skill_id
GROUP BY sa.name, sb.name
ORDER BY jobs_together DESC
LIMIT 15;
