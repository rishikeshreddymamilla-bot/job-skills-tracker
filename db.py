import os
import psycopg2
from dotenv import load_dotenv


def get_connection():
    """Open a connection to the database in DATABASE_URL (from .env)."""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if database_url is None:
        raise SystemExit("DATABASE_URL not found. Check your .env file.")
    return psycopg2.connect(database_url)
