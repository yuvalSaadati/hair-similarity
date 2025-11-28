"""
Image Display Management System

Handles different image display modes:
1. Default: Show first/newest image
2. Similarity search: Show most similar image to query
"""

from typing import List, Dict, Any, Optional
from app.db import conn
from app.image_processing import image_to_embedding
from PIL import Image
import io

def get_creator_display_image(username: str, query_embedding: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """
    Get the appropriate display image for a creator
    
    Args:
        username: Creator's Instagram username
        query_embedding: CLIP embedding for similarity search (optional)
    
    Returns:
        Image data with URL and similarity score (if applicable)
    """
    try:
        with conn.cursor() as cur:
            if query_embedding is not None:
                # Similarity search mode: find most similar image
                cur.execute("""
                    SELECT 
                        i.id,
                        i.media_id,
                        CONCAT('/api/images/', i.media_id, '/proxy') as local_url,
                        i.url,
                        i.caption,
                        i.width,
                        i.height,
                        1 - (i.embedding <=> %s) as similarity_score
                    FROM images i
                    WHERE EXISTS (
                        SELECT 1 FROM unnest(i.hashtags) h 
                        WHERE h = '@' || %s
                    )
                    AND i.embedding IS NOT NULL
                    ORDER BY i.embedding <=> %s
                    LIMIT 1
                """, (query_embedding, username, query_embedding))
            else:
                # Default mode: show first/newest image
                cur.execute("""
                    SELECT 
                        i.id,
                        i.media_id,
                        CONCAT('/api/images/', i.media_id, '/proxy') as local_url,
                        i.url,
                        i.caption,
                        i.width,
                        i.height,
                        NULL as similarity_score
                    FROM images i
                    WHERE EXISTS (
                        SELECT 1 FROM unnest(i.hashtags) h 
                        WHERE h = '@' || %s
                    )
                    ORDER BY i.created_at DESC
                    LIMIT 1
                """, (username,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                "id": str(row[0]),
                "media_id": row[1],
                "proxy_url": row[2],  # /api/images/{media_id}/proxy
                "original_url": row[3],
                "caption": row[4],
                "width": row[5],
                "height": row[6],
                "similarity_score": float(row[7]) if row[7] is not None else None
            }
            
    except Exception as e:
        print(f"Error getting display image for {username}: {e}")
        return None

def get_creator_all_images_for_search(username: str) -> List[Dict[str, Any]]:
    """
    Get all images from a creator for similarity search
    
    Args:
        username: Creator's Instagram username
    
    Returns:
        List of all images with embeddings
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    i.id,
                    i.media_id,
                    CONCAT('/api/images/', i.media_id, '/proxy') as local_url,
                    i.url,
                    i.caption,
                    i.width,
                    i.height,
                    i.embedding
                FROM images i
                WHERE EXISTS (
                    SELECT 1 FROM unnest(i.hashtags) h 
                    WHERE h = '@' || %s
                )
                AND i.embedding IS NOT NULL
                ORDER BY i.created_at DESC
            """, (username,))
            
            rows = cur.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "media_id": row[1],
                    "proxy_url": row[2],
                    "original_url": row[3],
                    "caption": row[4],
                    "width": row[5],
                    "height": row[6],
                    "embedding": row[7]
                }
                for row in rows
            ]
            
    except Exception as e:
        print(f"Error getting all images for {username}: {e}")
        return []

def update_creator_sample_image(username: str, image_id: str) -> bool:
    """
    Update creator's sample image ID
    
    Args:
        username: Creator's Instagram username
        image_id: Image ID to set as sample
    
    Returns:
        Success status
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE creators 
                SET sample_image_id = %s 
                WHERE username = %s
            """, (image_id, username))
            return True
    except Exception as e:
        print(f"Error updating sample image for {username}: {e}")
        return False

def get_creator_sample_image(username: str) -> Optional[Dict[str, Any]]:
    """
    Get creator's designated sample image
    
    Args:
        username: Creator's Instagram username
    
    Returns:
        Sample image data or None
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    i.id,
                    i.media_id,
                    CONCAT('/api/images/', i.media_id, '/proxy') as local_url,
                    i.url,
                    i.caption,
                    i.width,
                    i.height
                FROM creators c
                JOIN images i ON i.id = c.sample_image_id
                WHERE c.username = %s
            """, (username,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                "id": str(row[0]),
                "media_id": row[1],
                "proxy_url": row[2],
                "original_url": row[3],
                "caption": row[4],
                "width": row[5],
                "height": row[6]
            }
            
    except Exception as e:
        print(f"Error getting sample image for {username}: {e}")
        return None

def set_creator_default_sample_image(username: str) -> bool:
    """
    Set creator's sample image to the first/newest image
    
    Args:
        username: Creator's Instagram username
    
    Returns:
        Success status
    """
    try:
        with conn.cursor() as cur:
            # Get the newest image
            cur.execute("""
                SELECT i.id 
                FROM images i
                WHERE EXISTS (
                    SELECT 1 FROM unnest(i.hashtags) h 
                    WHERE h = '@' || %s
                )
                ORDER BY i.created_at DESC
                LIMIT 1
            """, (username,))
            
            row = cur.fetchone()
            if not row:
                return False
            
            # Update creator's sample image
            cur.execute("""
                UPDATE creators 
                SET sample_image_id = %s 
                WHERE username = %s
            """, (row[0], username))
            
            return True
            
    except Exception as e:
        print(f"Error setting default sample image for {username}: {e}")
        return False
