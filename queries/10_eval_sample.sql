-- Pick 50 random postings for the hand-labeled evaluation set.
-- Random from ALL postings (not only ones the regex matched), so the test isn't rigged in the regex's favor.
SELECT job_id, title, description
FROM jobs
WHERE description IS NOT NULL
ORDER BY random()
LIMIT 50;
