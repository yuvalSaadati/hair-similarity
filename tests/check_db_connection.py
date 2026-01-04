"""
Script to check database connection and port
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Check what DATABASE_URL is being used
database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/postgres")
print(f"Database URL: {database_url}")

# Parse the URL to show details
try:
    from urllib.parse import urlparse
    parsed = urlparse(database_url)
    print(f"\nConnection Details:")
    print(f"  Host: {parsed.hostname}")
    print(f"  Port: {parsed.port}")
    print(f"  Database: {parsed.path[1:] if parsed.path else 'postgres'}")
    print(f"  User: {parsed.username}")
except Exception as e:
    print(f"Error parsing URL: {e}")

# Try to connect and check PostgreSQL version
try:
    import psycopg
    print(f"\nAttempting to connect...")
    conn = psycopg.connect(database_url, autocommit=True)
    
    with conn.cursor() as cur:
        # Get PostgreSQL version
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"[OK] Connected successfully!")
        print(f"\nPostgreSQL Version:")
        print(f"  {version}")
        
        # Check if vector extension exists
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """)
        has_vector = cur.fetchone()[0]
        print(f"\nVector Extension:")
        print(f"  Installed: {has_vector}")
        
        if has_vector:
            # Get vector extension version
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
            vector_version = cur.fetchone()[0]
            print(f"  Version: {vector_version}")
        
        # Check what port PostgreSQL is actually listening on
        cur.execute("SHOW port;")
        actual_port = cur.fetchone()[0]
        print(f"\nPostgreSQL Listening Port: {actual_port}")
        
        # Check if images table exists
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'images'
            );
        """)
        has_images_table = cur.fetchone()[0]
        print(f"\nImages Table:")
        print(f"  Exists: {has_images_table}")
        
        if has_images_table:
            cur.execute("SELECT COUNT(*) FROM images;")
            count = cur.fetchone()[0]
            print(f"  Row count: {count}")
    
    conn.close()
    
except Exception as e:
    print(f"\n[ERROR] Connection failed!")
    print(f"Error: {e}")
    print(f"\nTroubleshooting:")
    print(f"  1. Make sure PostgreSQL is running")
    print(f"  2. Check if Docker container is running: docker ps")
    print(f"  3. If using Docker, start it with: docker-compose up db")
    print(f"  4. Verify the DATABASE_URL in your .env file")

