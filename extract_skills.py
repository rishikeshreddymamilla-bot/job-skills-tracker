import re

from db import get_connection
from skills_dictionary import SKILLS

# Compile every pattern once, up front, instead of once per job.
compiled = []
for skill in SKILLS:
    flags = 0 if skill.get("case_sensitive") else re.IGNORECASE
    compiled.append((skill["name"], [re.compile(p, flags) for p in skill["patterns"]]))


def mentions(patterns, text):
    """True if any of the skill's patterns appears in the text."""
    return any(p.search(text or "") for p in patterns)


conn = get_connection()
cur = conn.cursor()

# 1. Make sure every skill in the dictionary has a row in the skills table.
for skill in SKILLS:
    cur.execute(
        "INSERT INTO skills (name, category) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING;",
        (skill["name"], skill["category"]),
    )
cur.execute("SELECT name, skill_id FROM skills;")
skill_ids = dict(cur.fetchall())

# 2. Clear old keyword results, so re-running gives the same answer (idempotent).
cur.execute("DELETE FROM job_skills WHERE method = 'keyword';")

# 3. Scan every job's title and description.
cur.execute("SELECT job_id, title, description FROM jobs;")
jobs = cur.fetchall()

rows = []
for job_id, title, description in jobs:
    for name, patterns in compiled:
        in_title = mentions(patterns, title)
        in_desc = mentions(patterns, description)
        if in_title and in_desc:
            found_in = "both"
        elif in_title:
            found_in = "title"
        elif in_desc:
            found_in = "description"
        else:
            continue
        rows.append((job_id, skill_ids[name], "keyword", found_in))

cur.executemany(
    "INSERT INTO job_skills (job_id, skill_id, method, found_in) VALUES (%s, %s, %s, %s);",
    rows,
)
conn.commit()

# 4. Summary.
cur.execute("""
    SELECT COUNT(DISTINCT job_id) FROM job_skills WHERE method = 'keyword';
""")
jobs_with_skills = cur.fetchone()[0]
print(f"Scanned {len(jobs)} jobs. {jobs_with_skills} had at least one skill. {len(rows)} skill mentions found.")

cur.execute("""
    SELECT s.name, COUNT(*) AS jobs
    FROM job_skills js
    JOIN skills s ON s.skill_id = js.skill_id
    WHERE js.method = 'keyword'
    GROUP BY s.name
    ORDER BY jobs DESC, s.name
    LIMIT 10;
""")
print("\nTop skills:")
for name, count in cur.fetchall():
    print(f"  {name:<20} {count}")

cur.close()
conn.close()
