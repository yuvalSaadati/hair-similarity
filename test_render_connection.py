"""
Test script to diagnose Render database connection issues
"""
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

database_url = os.getenv("DATABASE_URL", "")
if not database_url:
    print("[ERROR] DATABASE_URL not found in .env file")
    exit(1)

# Parse the URL
parsed = urlparse(database_url)
hostname = parsed.hostname or ""

print("=" * 60)
print("DATABASE CONNECTION DIAGNOSTICS")
print("=" * 60)
print(f"\nDatabase URL: {parsed.scheme}://{parsed.username}@{hostname}:{parsed.port}{parsed.path}")
print(f"\nConnection Details:")
print(f"  Hostname: {hostname}")
print(f"  Port: {parsed.port}")
print(f"  Database: {parsed.path[1:] if parsed.path else 'N/A'}")
print(f"  Username: {parsed.username}")
print(f"  SSL Mode: {'require' if 'sslmode=require' in database_url else 'NOT SET'}")

# Check if it's Render
is_render = 'render.com' in hostname.lower()
is_internal = '-a' in hostname or 'internal' in hostname.lower()

print(f"\nRender Database: {is_render}")
if is_render:
    if is_internal:
        print("\n[WARNING] This looks like an INTERNAL Database URL!")
        print("Internal URLs only work from within Render's network.")
        print("You need to use the EXTERNAL Database URL from Render dashboard.")
    else:
        print("[OK] This looks like an EXTERNAL Database URL")

# Try to connect
print("\n" + "=" * 60)
print("ATTEMPTING CONNECTION...")
print("=" * 60)

try:
    import psycopg
    print("\nConnecting...")
    conn = psycopg.connect(
        database_url,
        autocommit=True,
        connect_timeout=10
    )
    print("[SUCCESS] Connected to database!")
    
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"\nPostgreSQL Version: {version.split(',')[0]}")
        
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
        has_vector = cur.fetchone()[0]
        print(f"Vector Extension: {'Installed' if has_vector else 'NOT Installed'}")
    
    conn.close()
    print("\n[OK] Connection test successful!")
    
except psycopg.OperationalError as e:
    error_msg = str(e)
    print(f"\n[ERROR] Connection failed: {error_msg}")
    
    if "timeout" in error_msg.lower():
        print("\n" + "=" * 60)
        print("TROUBLESHOOTING TIMEOUT ISSUES")
        print("=" * 60)
        print("\n1. Check if you're using EXTERNAL Database URL:")
        print("   - Go to Render Dashboard → Your Database → Info")
        print("   - Use 'External Database URL' (NOT Internal)")
        print("   - External URL should NOT contain '-a' in hostname")
        
        print("\n2. Check your network/firewall:")
        print("   - Some networks block outbound PostgreSQL connections")
        print("   - Try from a different network (mobile hotspot, etc.)")
        
        print("\n3. Verify database is running:")
        print("   - Check Render dashboard - database should show 'Available'")
        
        print("\n4. Test connection from Render:")
        print("   - Use Render's PSQL Command in dashboard")
        print("   - If that works, the issue is network-related")
    
    elif "password" in error_msg.lower() or "authentication" in error_msg.lower():
        print("\n[ERROR] Authentication failed - check your password in DATABASE_URL")
    
    else:
        print(f"\n[ERROR] Connection error: {error_msg}")
    
    exit(1)
    
except Exception as e:
    print(f"\n[ERROR] Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

