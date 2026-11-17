-- New postings collected per day (grows once the daily refresh is running).
SELECT
    first_seen_at::date AS day,
    COUNT(*)            AS new_jobs
FROM jobs
GROUP BY first_seen_at::date
ORDER BY day;
