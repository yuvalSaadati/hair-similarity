"""
Image Proxy System

Handles fetching images from Instagram on-demand using media IDs.
This avoids storing large files locally and prevents URL expiration issues.
"""

import requests
import io
import base64
from typing import Optional, Tuple, List
from PIL import Image
from app.config import IG_ACCESS_TOKEN, IG_USER_ID
from app.db import conn
import json
import re
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

# Global flag to track if we've warned about token issues
_token_warning_logged = False

def get_instagram_media_url(public_post_url: str) -> List[str]:
    """
    Get Instagram media URLs using Graph API query
    
    Args:
        public_post_url: Instagram public post URL (e.g., https://www.instagram.com/p/ABC123/)
    
    Returns:
        List of media URLs (image or video URLs). Returns empty list if failed.
    """
    try:
        # Fetch the HTML page to extract media_id
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                          "AppleWebKit/537.36 (KHTML, like Gecko) " +
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(public_post_url, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"Failed to fetch page {public_post_url}: {resp.status_code}")
            return []
        
        # Extract media_id from page source using regex (Instagram embeds it in script tags)
        # Look for media_id pattern in the HTML
        id_match = re.search(r'"media_id":"(\d+)"', resp.text)
        if not id_match:
            # Try alternative pattern
            id_match = re.search(r'"id":"(\d+)"', resp.text)
        
        media_id = id_match.group(1) if id_match else None
        
        if not media_id:
            print(f"Could not extract media_id from URL: {public_post_url}")
            return []
        # GET https://graph.facebook.com/{ig-media-id}?fields=children{media_url,media_type}&access_token={token}

        # Use the Graph API query pattern from line 91
        url = f"https://graph.facebook.com/v21.0/{media_id}"
        params = {
            "fields": "children{media_url,media_type},media_url,media_type",
            "access_token": IG_ACCESS_TOKEN
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        urls = []
        
        # Check if it's a carousel (has children)
        if "children" in data and "data" in data["children"]:
            for child in data["children"]["data"]:
                if child.get("media_url"):
                    urls.append(child["media_url"])
        # Otherwise, use the direct media_url
        elif data.get("media_url"):
            urls.append(data["media_url"])
        
        return urls
        
    except Exception as e:
        print(f"Failed to get Instagram media URLs from {public_post_url}: {e}")
        return []
   


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
    from fastapi import APIRouter, HTTPException, Query
    from fastapi.responses import StreamingResponse
    
    router = APIRouter(prefix="/api", tags=["images"])
    
    @router.get("/images/{media_id}/proxy")
    def proxy_image(media_id: str):
        """
        Proxy endpoint for Instagram images
        Fetches image using media_url stored in database, or falls back to Instagram Graph API
        """
        try:
            # First, try to get media_url from database
            media_url = None
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT media_url 
                    FROM images 
                    WHERE media_id = %s
                    LIMIT 1
                """, (media_id,))
                row = cur.fetchone()
                if row and row[0]:
                    media_url = row[0]
            
            # If not in database, fall back to Instagram Graph API
            if not media_url:
                result = fetch_instagram_image_by_id(media_id)
                if result:
                    img, fetched_url = result
                    # Convert to RGB if needed
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Convert image to bytes
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='JPEG', quality=85)
                    img_bytes.seek(0)
                    
                    return StreamingResponse(
                        io.BytesIO(img_bytes.getvalue()),
                        media_type="image/jpeg",
                        headers={
                            "Cache-Control": "public, max-age=3600",
                            "Content-Disposition": f"inline; filename=instagram_{media_id}.jpg"
                        }
                    )
                else:
                    raise HTTPException(404, f"No image found for media_id: {media_id}")
            
            # Fetch the image from the stored media_url
            img_response = requests.get(media_url, timeout=30)
            img_response.raise_for_status()
            img = Image.open(io.BytesIO(img_response.content))
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert image to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=85)
            img_bytes.seek(0)
            
            # Return as streaming response
            return StreamingResponse(
                io.BytesIO(img_bytes.getvalue()),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "public, max-age=3600",
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
