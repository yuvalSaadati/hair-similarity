# app/db.py
import os
import psycopg
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

load_dotenv()
# Use DATABASE_URL from environment, or default to port 5433 (Docker container with pgvector)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/postgres")

# Parse URL and ensure SSL mode is set for Render databases
def prepare_connection_url(url: str) -> str:
    """Prepare connection URL with proper SSL settings for Render"""
    parsed = urlparse(url)
    
    # Check if it's a Render database (contains 'render.com')
    is_render = 'render.com' in parsed.hostname if parsed.hostname else False
    
    # Parse existing query parameters
    query_params = parse_qs(parsed.query)
    
    # Set SSL mode for Render databases
    if is_render and 'sslmode' not in query_params:
        query_params['sslmode'] = ['require']
    
    # Rebuild query string
    new_query = urlencode(query_params, doseq=True)
    
    # Reconstruct URL
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)

# Prepare connection URL
prepared_url = prepare_connection_url(DATABASE_URL)

# Connect with timeout and SSL settings, with retry logic
# Note: For Render databases, make sure you're using the "External Database URL" 
# (not Internal) if connecting from outside Render's network
def create_connection(max_retries=3, retry_delay=2):
    """Create database connection with retry logic"""
    import time
    
    for attempt in range(max_retries):
        try:
            connection = psycopg.connect(
                prepared_url,
                autocommit=True,
                connect_timeout=30  # 30 second timeout for external connections
            )
            hostname = urlparse(prepared_url).hostname
            print(f"[OK] Connected to database: {hostname}")
            return connection
        except psycopg.OperationalError as e:
            error_msg = str(e)
            is_last_attempt = (attempt == max_retries - 1)
            
            if "timeout" in error_msg.lower():
                if not is_last_attempt:
                    print(f"[WARNING] Connection timeout (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[ERROR] Database connection failed after {max_retries} attempts: {error_msg}")
                    print("\nTroubleshooting tips:")
                    print("1. Make sure you're using the 'External Database URL' from Render (not Internal)")
                    print("2. Check if your firewall/network allows outbound connections to port 5432")
                    print("3. Verify the database is running in Render dashboard")
                    print("4. Try running: python test_render_connection.py")
                    raise
            else:
                # Non-timeout errors, fail immediately
                print(f"[ERROR] Database connection failed: {error_msg}")
                raise
        except Exception as e:
            print(f"[ERROR] Unexpected database connection error: {e}")
            raise
    
    # Should never reach here, but just in case
    raise Exception("Failed to create database connection")

# Lazy connection wrapper - only connects when actually used
class LazyConnection:
    """Connection wrapper that connects on first use"""
    _connection = None
    _vector_registered = False
    
    def __getattr__(self, name):
        """Delegate attribute access to the actual connection"""
        if self._connection is None:
            self._connection = create_connection()
            # Register vector extension on first connection
            self._register_vector()
        return getattr(self._connection, name)
    
    def _register_vector(self):
        """Register vector extension if available"""
        if self._vector_registered:
            return
        
        try:
            from pgvector.psycopg import register_vector
            with self._connection.cursor() as cur:
                cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
                has_vector = cur.fetchone()[0]
                if has_vector:
                    register_vector(self._connection)
                    self._vector_registered = True
        except Exception:
            # Vector extension not available - that's okay
            pass
    
    def cursor(self, *args, **kwargs):
        """Ensure connection before creating cursor"""
        if self._connection is None:
            self._connection = create_connection()
            self._register_vector()
        return self._connection.cursor(*args, **kwargs)
    
    def close(self):
        """Close the connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._vector_registered = False

# Create lazy connection - won't connect until first use
conn = LazyConnection()