import os
import psycopg

# Database URL (override with env var if needed, e.g. 5433 if you remapped the port)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
# Read the SQL file
with open("./db/init.sql", "r", encoding="utf-8") as f:
    sql = f.read()

# Connect and execute
with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        # Quick verification: list installed extensions
        cur.execute("select extname from pg_extension order by 1;")
        exts = [r[0] for r in cur.fetchall()]
        print("SQL script executed successfully! Extensions:", exts)
