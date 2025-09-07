import psycopg

# Connect to the Docker PostgreSQL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
    with conn.cursor() as cur:
        # Enable vector extension
        # cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create images table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id UUID PRIMARY KEY,
            source TEXT NOT NULL,
            source_id TEXT,
            url TEXT,
            hashtags TEXT[] DEFAULT '{}',
            width INT,
            height INT,
            created_at TIMESTAMPTZ DEFAULT now(),
        );
        """)
        print("Database setup complete!")
