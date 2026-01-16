import os
import asyncio
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
    # Startup: Initialize database and pre-load CLIP model
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
    
    # Pre-load CLIP model in background (non-blocking)
    # This prevents 502 errors on first similarity search request
    # We do this in a background task so it doesn't block startup
    async def preload_clip_model():
        try:
            print("🔄 Pre-loading CLIP model (this may take 30-60 seconds)...")
            # Load model in background thread to avoid blocking startup
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _load_clip_model_sync)
            print("✅ CLIP model pre-loaded successfully")
        except Exception as e:
            print(f"⚠️  CLIP model pre-loading failed (non-critical): {e}")
            print("   The model will load on first use, which may cause a delay.")
    
    def _load_clip_model_sync():
        """Load CLIP model synchronously in background thread"""
        from app.image_processing import get_clip_model
        try:
            # This will load the model and cache it globally
            get_clip_model()
            print("   CLIP model loaded and cached")
        except Exception as e:
            print(f"   Error loading CLIP model: {e}")
            raise
    
    # Start pre-loading CLIP model in background (don't await - let it run async)
    # This allows the app to start serving requests while the model loads
    asyncio.create_task(preload_clip_model())
    
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
