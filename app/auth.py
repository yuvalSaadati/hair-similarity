from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
import jwt as pyjwt
from datetime import datetime, timedelta
from typing import Dict
from app.config import JWT_SECRET
from app.db import conn

security = HTTPBearer()

def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit, so truncate if necessary
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    # Use bcrypt directly instead of passlib
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    # Use bcrypt directly instead of passlib
    password_bytes = password.encode('utf-8')
    hash_bytes = password_hash.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hash_bytes)

def create_jwt(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    token = credentials.credentials
    try:
        data = pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token payload")
    with conn.cursor() as cur:
        cur.execute("SELECT id, email, role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(401, "User not found")
    return {"id": str(row[0]), "email": row[1], "role": row[2]}
