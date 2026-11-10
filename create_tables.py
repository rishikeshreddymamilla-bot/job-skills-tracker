from db import get_connection

with open("schema.sql", encoding="utf-8") as f:
    schema_sql = f.read()

conn = get_connection()
cur = conn.cursor()
cur.execute(schema_sql)
conn.commit()

cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' ORDER BY table_name;
""")
print("Tables in the database:", [row[0] for row in cur.fetchall()])

cur.close()
conn.close()
