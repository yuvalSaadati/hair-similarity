from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from app.db import conn
from app.auth import get_current_user

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

class ReviewCreate(BaseModel):
    creator_username: str
    reviewer_name: Optional[str] = None
    comment: str
    rating: Optional[int] = None

class ReviewResponse(BaseModel):
    id: str
    creator_username: str
    reviewer_name: Optional[str] = None
    comment: str
    rating: Optional[int] = None
    created_at: str

@router.get("/{creator_username}")
def get_reviews(creator_username: str):
    """Get all reviews for a creator (public endpoint, no auth required)"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, creator_username, reviewer_name, comment, rating, created_at
            FROM reviews
            WHERE creator_username = %s
            ORDER BY created_at DESC
        """, (creator_username,))
        rows = cur.fetchall()
    
    reviews = []
    for row in rows:
        reviews.append(ReviewResponse(
            id=str(row[0]),
            creator_username=row[1],
            reviewer_name=row[2],
            comment=row[3],
            rating=row[4],
            created_at=row[5].isoformat() if row[5] else None
        ))
    
    return {"reviews": reviews}

@router.post("")
def create_review(review: ReviewCreate, current_user: dict = Depends(get_current_user)):
    """Create a new review for a creator"""
    # Validate rating if provided
    if review.rating is not None and (review.rating < 1 or review.rating > 5):
        raise HTTPException(400, "Rating must be between 1 and 5")
    
    if not review.comment or not review.comment.strip():
        raise HTTPException(400, "Comment is required")
    
    # Verify creator exists
    with conn.cursor() as cur:
        cur.execute("SELECT username FROM creators WHERE username = %s", (review.creator_username,))
        if not cur.fetchone():
            raise HTTPException(404, f"Creator {review.creator_username} not found")
    
    # Insert review
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO reviews (creator_username, reviewer_name, comment, rating)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """, (review.creator_username, review.reviewer_name, review.comment, review.rating))
        row = cur.fetchone()
        conn.commit()
    
    return {
        "id": str(row[0]),
        "created_at": row[1].isoformat() if row[1] else None,
        "message": "Review created successfully"
    }
