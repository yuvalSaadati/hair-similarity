from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.auth import hash_password, verify_password, create_jwt, get_current_user
from app.database import upsert_creator
from app.instagram import ig_get_creator_profile
from app.db import conn
import psycopg

router = APIRouter(prefix="/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(request: RegisterRequest):
    """Register a new user"""
    password_hash = hash_password(request.password)
    
    with conn.cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
                (request.email, password_hash)
            )
            user_id = cur.fetchone()[0]
        except psycopg.errors.UniqueViolation:
            raise HTTPException(status_code=400, detail="האימייל כבר רשום במערכת. אנא השתמשו באימייל אחר או התחברו.")
    
    token = create_jwt(str(user_id), request.email)
    return {"token": token, "user_id": str(user_id)}

@router.post("/login")
def login(request: LoginRequest):
    """Login user"""
    with conn.cursor() as cur:
        cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (request.email,))
        row = cur.fetchone()
    
    if not row or not verify_password(request.password, row[1]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_jwt(str(row[0]), request.email)
    return {"token": token, "user_id": str(row[0])}

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return current_user
