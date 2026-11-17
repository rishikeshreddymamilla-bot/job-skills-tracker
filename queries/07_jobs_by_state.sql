-- Where the jobs are. SUM(COUNT(*)) OVER () is a window over the grouped rows: the grand total.
SELECT
    COALESCE(state, 'Nationwide / not specified')               AS state,
    COUNT(*)                                                    AS jobs,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)          AS pct_of_jobs
FROM jobs
GROUP BY COALESCE(state, 'Nationwide / not specified')
ORDER BY jobs DESC;
