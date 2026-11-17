-- Headline numbers: how many jobs, how many had a detectable skill, salary coverage, date range.
WITH jobs_with_skill AS (
    SELECT DISTINCT job_id
    FROM job_skills
    WHERE method = 'keyword'
)
SELECT
    COUNT(*)                                                    AS total_jobs,
    COUNT(w.job_id)                                             AS jobs_with_a_skill,
    ROUND(100.0 * COUNT(w.job_id) / NULLIF(COUNT(*), 0), 1)     AS pct_with_a_skill,
    COUNT(*) FILTER (WHERE j.salary_is_predicted = FALSE
                       AND j.salary_min IS NOT NULL)            AS jobs_with_real_salary,
    MIN(j.first_seen_at)::date                                  AS first_collected,
    MAX(j.first_seen_at)::date                                  AS last_collected
FROM jobs j
LEFT JOIN jobs_with_skill w ON w.job_id = j.job_id;
