"""
Image Proxy System

Handles fetching images from Instagram on-demand using media IDs.
This avoids storing large files locally and prevents URL expiration issues.
"""

import requests
import io
from typing import Optional, Tuple
from PIL import Image
from app.config import IG_ACCESS_TOKEN, IG_USER_ID
from app.db import conn

def fetch_instagram_image_by_id(media_id: str) -> Optional[Tuple[Image.Image, str]]:
    """
    Fetch image from Instagram using media ID
    
    Args:
        media_id: Instagram media ID
    
    Returns:
        Tuple of (PIL Image, original URL) or None if failed
    """
    try:
        # Get media URL from Facebook Graph API (same as other functions)
        url = f"https://graph.facebook.com/v21.0/{media_id}"
        params = {
            "fields": "media_url,media_type",
            "access_token": IG_ACCESS_TOKEN
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        media_url = data.get("media_url")
        media_type = data.get("media_type")
        
        if not media_url or media_type not in ["IMAGE", "VIDEO"]:
            return None
        
        # Fetch the actual image
        img_response = requests.get(media_url, timeout=30)
        img_response.raise_for_status()
        
        # Convert to PIL Image
        img = Image.open(io.BytesIO(img_response.content))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return img, media_url
        
    except Exception as e:
        print(f"Failed to fetch Instagram image {media_id}: {e}")
        return None

def get_image_proxy_url(media_id: str) -> str:
    """
    Get proxy URL for an image (for frontend display)
    
    Args:
        media_id: Instagram media ID
    
    Returns:
        Proxy URL for the image
    """
    return f"/api/images/{media_id}/proxy"

def fetch_instagram_profile_picture(username: str) -> Optional[Tuple[Image.Image, str]]:
    """
    Fetch profile picture from Instagram using username
    Also saves it locally to avoid URL expiration issues
    
    Args:
        username: Instagram username
    
    Returns:
        Tuple of (PIL Image, original URL) or None if failed
    """
    try:
        # Get profile picture URL from Instagram API
        url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}"
        params = {
            "fields": f"business_discovery.username({username}){{profile_picture_url}}",
            "access_token": IG_ACCESS_TOKEN
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        profile_picture_url = data.get("business_discovery", {}).get("profile_picture_url")
        
        if not profile_picture_url:
            return None
        
        # Fetch the actual image
        img_response = requests.get(profile_picture_url, timeout=30)
        img_response.raise_for_status()
        
        # Convert to PIL Image
        img = Image.open(io.BytesIO(img_response.content))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return img, profile_picture_url
        
    except Exception as e:
        print(f"Failed to fetch Instagram profile picture for {username}: {e}")
        return None

def create_image_proxy_endpoint():
    """
    Create FastAPI endpoint for image proxy
    This should be called from the main app
    """
    from fastapi import APIRouter, HTTPException
    from fastapi.responses import StreamingResponse
    
    router = APIRouter()
    
    @router.get("/images/{media_id}/proxy")
    def proxy_image(media_id: str):
        """
        Proxy endpoint for Instagram images
        Fetches image on-demand and streams it to client
        """
        try:
            result = fetch_instagram_image_by_id(media_id)
            if not result:
                raise HTTPException(404, "Image not found")
            
            img, original_url = result
            
            # Convert image to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=85)
            img_bytes.seek(0)
            
            # Return as streaming response
            return StreamingResponse(
                io.BytesIO(img_bytes.getvalue()),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                    "Content-Disposition": f"inline; filename=instagram_{media_id}.jpg"
                }
            )
            
        except Exception as e:
            raise HTTPException(500, f"Failed to proxy image: {str(e)}")
    
    @router.get("/profile-pictures/{username}/proxy")
    def proxy_profile_picture(username: str):
        """
        Proxy endpoint for Instagram profile pictures
        Fetches profile picture on-demand and streams it to client
        """
        try:
            result = fetch_instagram_profile_picture(username)
            if not result:
                raise HTTPException(404, "Profile picture not found")
            
            img, original_url = result
            
            # Convert image to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=85)
            img_bytes.seek(0)
            
            # Return as streaming response
            return StreamingResponse(
                io.BytesIO(img_bytes.getvalue()),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                    "Content-Disposition": f"inline; filename=profile_{username}.jpg"
                }
            )
            
        except Exception as e:
            raise HTTPException(500, f"Failed to proxy profile picture: {str(e)}")
    
    return router

def update_images_table_schema():
    """
    Update images table to store only essential data
    """
    with conn.cursor() as cur:
        # Add media_id column if it doesn't exist
        cur.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='images' AND column_name='media_id'
                ) THEN
                    ALTER TABLE images ADD COLUMN media_id TEXT;
                END IF;
            END $$;
        """)
        
        # Create index on media_id for faster lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_images_media_id 
            ON images(media_id);
        """)

def store_image_metadata_only(media_id: str, source: str, source_id: str, 
                            hashtags: list, width: int, height: int, 
                            embedding, caption: str = None) -> str:
    """
    Store only image metadata and embedding, not the actual image
    
    Args:
        media_id: Instagram media ID
        source: Source type (instagram/user_upload)
        source_id: Original source ID
        hashtags: List of hashtags
        width: Image width
        height: Image height
        embedding: CLIP embedding vector
        caption: Image caption
    
    Returns:
        Database ID of the stored record
    """
    import uuid
    
    with conn.cursor() as cur:
        image_id = uuid.uuid4()
        
        cur.execute("""
            INSERT INTO images (
                id, source, source_id, media_id, hashtags, 
                width, height, embedding, caption
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE SET
                media_id = EXCLUDED.media_id,
                width = EXCLUDED.width,
                height = EXCLUDED.height,
                embedding = EXCLUDED.embedding,
                caption = EXCLUDED.caption
            RETURNING id
        """, (
            image_id, source, source_id, media_id, hashtags,
            width, height, embedding, caption
        ))
        
        result = cur.fetchone()
        return str(result[0]) if result else str(image_id)
