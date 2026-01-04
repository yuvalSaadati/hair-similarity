import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector
from app.db import conn
from app.database import setup_database_schema
from app.routers import auth, creators, search, me, reviews

# Initialize database
# Note: Connection is lazy, so it will connect on first use
# The setup_database_schema() will trigger the connection
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
