import os
import psycopg2
from dotenv import load_dotenv

# 1. Load the database URL from .env
load_dotenv()
database_url = os.getenv("DATABASE_URL")

if database_url is None:
    raise SystemExit("DATABASE_URL not found. Check your .env file.")

# 2. Connect to the Neon database
conn = psycopg2.connect(database_url)

# 3. Create a cursor and run a query
cur = conn.cursor()
cur.execute("SELECT version();")

# 4. Get the result, print it, and clean up
result = cur.fetchone()
print("Connected! Database version:")
print(result[0])

cur.close()
conn.close()