import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector

from app.db import conn
from app.database import setup_database_schema
from app.routers import auth, creators, search, me, reviews

# Initialize database
# Check if vector extension exists and try to create/register it
has_vector_extension = False
try:
    with conn.cursor() as cur:
        # Check if extension exists
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
        has_vector_extension = cur.fetchone()[0]
        
        # Try to create if it doesn't exist
        if not has_vector_extension:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                has_vector_extension = True
            except Exception as e:
                print(f"Warning: Could not create vector extension: {e}")
                print("The app will continue without vector support.")
        
        # Register vector type with psycopg if extension exists
        if has_vector_extension:
            try:
                register_vector(conn)
            except Exception as e:
                print(f"Warning: Could not register vector type: {e}")
                has_vector_extension = False
except Exception as e:
    print(f"Warning: Error checking vector extension: {e}")
    print("The app will continue without vector support.")

setup_database_schema()

# Create FastAPI app
app = FastAPI(title="Hair Similarity API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(creators.router)
app.include_router(me.router)
app.include_router(search.router)
app.include_router(reviews.router)

# Static file mounts
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
