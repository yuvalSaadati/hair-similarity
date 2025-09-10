# app/db.py
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/postgres"

conn = psycopg.connect(DATABASE_URL, autocommit=True)