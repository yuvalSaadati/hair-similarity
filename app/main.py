import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector

from app.config import MEDIA_IMAGES_DIR, MEDIA_AVATARS_DIR
from app.db import conn
from app.database import setup_database_schema
from app.routers import auth, creators, search, ingest, me, display
from app.image_proxy import create_image_proxy_endpoint
from app.calendar_oauth import router as cal_router

# Initialize database
register_vector(conn)
setup_database_schema()

# Ensure media directories exist
os.makedirs(MEDIA_IMAGES_DIR, exist_ok=True)
os.makedirs(MEDIA_AVATARS_DIR, exist_ok=True)

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
app.include_router(ingest.router)
app.include_router(display.router)
app.include_router(create_image_proxy_endpoint())
app.include_router(cal_router)

# Static file mounts
app.mount("/media", StaticFiles(directory=os.path.join(os.path.dirname(__file__), 'media')), name="media")
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
