# app/db.py
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
# Use DATABASE_URL from environment, or default to port 5433 (Docker container with pgvector)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/postgres")

conn = psycopg.connect(DATABASE_URL, autocommit=True)

# Try to register vector extension if available
try:
    from pgvector.psycopg import register_vector
    # Check if vector extension exists before registering
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
        has_vector = cur.fetchone()[0]
        if has_vector:
            register_vector(conn)
except Exception:
    # Vector extension not available - that's okay, will be handled elsewhere
    pass