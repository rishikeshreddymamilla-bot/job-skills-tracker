-- Pay by skill, using ONLY salaries the employer actually posted (not Adzuna's estimates).
-- Salary midpoint = average of min and max. Values under 15,000 are likely hourly rates, so they're excluded.
-- HAVING COUNT(*) >= 10 drops skills with too few jobs to trust an average.
WITH real_salary AS (
    SELECT
        job_id,
        (salary_min + COALESCE(salary_max, salary_min)) / 2 AS salary_mid
    FROM jobs
    WHERE salary_is_predicted = FALSE
      AND salary_min >= 15000
)
SELECT
    s.name                                                              AS skill,
    COUNT(*)                                                            AS jobs_with_real_salary,
    ROUND(AVG(r.salary_mid))::int                                       AS avg_salary,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY r.salary_mid))::int AS median_salary
FROM real_salary r
JOIN job_skills js ON js.job_id = r.job_id AND js.method = 'keyword'
JOIN skills s      ON s.skill_id = js.skill_id
GROUP BY s.name
HAVING COUNT(*) >= 10
ORDER BY median_salary DESC;
