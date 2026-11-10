from db import get_connection

conn = get_connection()
cur = conn.cursor()
cur.execute("TRUNCATE job_skills, jobs;")
conn.commit()
print("Cleared jobs and job_skills.")
cur.close()
conn.close()