-- How many skills does a typical posting mention?
-- The method filter sits in the JOIN, not in WHERE: a WHERE filter would drop jobs with zero skills.
WITH per_job AS (
    SELECT j.job_id, COUNT(js.skill_id) AS n_skills
    FROM jobs j
    LEFT JOIN job_skills js
           ON js.job_id = j.job_id
          AND js.method = 'keyword'
    GROUP BY j.job_id
)
SELECT n_skills, COUNT(*) AS jobs
FROM per_job
GROUP BY n_skills
ORDER BY n_skills;
