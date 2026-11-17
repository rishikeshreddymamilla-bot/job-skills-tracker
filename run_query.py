import sys

from db import get_connection

if len(sys.argv) != 2:
    raise SystemExit("Usage: python run_query.py queries/<file>.sql")

with open(sys.argv[1], encoding="utf-8") as f:
    sql = f.read()

conn = get_connection()
cur = conn.cursor()
cur.execute(sql)

if cur.description is None:
    # Statements like UPDATE return no rows. This script never commits, so it can't change data.
    print("Query ran but returned no rows.")
else:
    columns = [col[0] for col in cur.description]
    rows = cur.fetchall()
    # Make each column as wide as its longest value, so the output lines up.
    widths = [max(len(str(c)), *(len(str(r[i])) for r in rows)) if rows else len(str(c))
              for i, c in enumerate(columns)]
    print("  ".join(str(c).ljust(w) for c, w in zip(columns, widths)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(row, widths)))
    print(f"\n{len(rows)} rows")

cur.close()
conn.close()
