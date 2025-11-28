# app/db.py
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
# Use DATABASE_URL from environment, or default to port 5433 (Docker container with pgvector)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/postgres")

conn = psycopg.connect(DATABASE_URL, autocommit=True)