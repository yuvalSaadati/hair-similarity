import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector
from app.db import conn
from app.database import setup_database_schema
from app.routers import auth, creators, search, me, reviews

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database (CLIP model loads lazily to save memory)
    print("🚀 Starting Hair Similarity API...")
    
    # Initialize database
    try:
        setup_database_schema()
        print("✅ Database schema initialized successfully")
    except Exception as e:
        print(f"⚠️  Warning: Database initialization failed: {e}")
        print("   The app will continue, but database operations may fail.")
    
    # Pre-warm database connection
    try:
        print("🔄 Pre-warming database connection...")
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        print("✅ Database connection pre-warmed successfully")
    except Exception as e:
        print(f"⚠️  Database pre-warming failed (non-critical): {e}")
    
    # Note: CLIP model is loaded lazily on first use to save memory
    # Pre-loading causes out-of-memory errors on Render's free tier (512MB limit)
    # The first similarity search request will take longer, but the app will stay within memory limits
    
    yield
    
    # Shutdown: Clean up if needed
    print("👋 Shutting down Hair Similarity API...")

# Create FastAPI app with lifespan events
app = FastAPI(
    title="Hair Similarity API", 
    version="1.0.0",
    lifespan=lifespan
)

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
