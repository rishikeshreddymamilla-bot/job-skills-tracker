import glob
import json

from db import get_connection

INSERT_SQL = """
    INSERT INTO jobs (
        job_id, title, company, location, state, category, description,
        salary_min, salary_max, salary_is_predicted,
        contract_type, contract_time, posted_at, redirect_url
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (job_id) DO NOTHING;
"""


def flatten(job):
    """Turn one nested Adzuna job into a flat tuple matching INSERT_SQL."""
    company = job.get("company") or {}
    location = job.get("location") or {}
    category = job.get("category") or {}
    area = location.get("area") or []

    # area looks like ["US", "Virginia", "Norfolk"]; nationwide jobs are just ["US"]
    state = area[1] if len(area) > 1 else None

    predicted = job.get("salary_is_predicted")
    salary_is_predicted = None if predicted is None else str(predicted) == "1"

    return (
        str(job["id"]),
        job.get("title"),
        company.get("display_name"),
        location.get("display_name"),
        state,
        category.get("label"),
        job.get("description"),
        job.get("salary_min"),
        job.get("salary_max"),
        salary_is_predicted,
        job.get("contract_type"),
        job.get("contract_time"),
        job.get("created"),
        job.get("redirect_url"),
    )


conn = get_connection()
cur = conn.cursor()

inserted = 0
skipped = 0

for path in sorted(glob.glob("raw/*.json")):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    for job in data.get("results", []):
        cur.execute(INSERT_SQL, flatten(job))
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

conn.commit()

cur.execute("SELECT COUNT(*) FROM jobs;")
total = cur.fetchone()[0]
print(f"Inserted {inserted} new jobs, skipped {skipped} duplicates. Total in database: {total}")

cur.close()
conn.close()
