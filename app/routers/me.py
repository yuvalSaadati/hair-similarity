from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional
from app.auth import get_current_user
from app.database import get_creator_by_user_id, upsert_creator
from app.instagram import ig_get_creator_profile, ig_get_recent_media_by_creator, ig_expand_media_to_images
from app.image_processing import fetch_and_embed_image, insert_image_row, is_hair_related_caption
from app.db import conn
import uuid

router = APIRouter(prefix="/api/me", tags=["me"])

@router.get("/creator")
def get_my_creator(current_user: dict = Depends(get_current_user)):
    """Get current user's creator profile"""
    creator = get_creator_by_user_id(current_user["id"])
    return {"creator": creator}

@router.put("/creator")
def upsert_my_creator(current_user: dict = Depends(get_current_user),
                     username: str = Query(...), phone: Optional[str] = Query(None),
                     location: Optional[str] = Query(None), 
                     min_price: Optional[str] = Query(None),
                     max_price: Optional[str] = Query(None), 
                     calendar_url: Optional[str] = Query(None),
                     ingest_limit: int = Query(100, description="posts to fetch after save"),
                     background_tasks: BackgroundTasks = None):
    """Create or update current user's creator profile"""
    
    # Create profile data from form input (no Instagram API required)
    profile_data = {
        "profile_picture_url": None,
        "biography": f"Hair creator: {username}",
        "username": username
    }
    
    # Optional: Try to get Instagram profile data if credentials are available
    from app.config import IG_ACCESS_TOKEN, IG_USER_ID
    if IG_ACCESS_TOKEN and IG_USER_ID:
        try:
            instagram_data = ig_get_creator_profile(username)
            # Use Instagram data if available
            profile_data.update({
                "profile_picture_url": instagram_data.get("profile_picture_url"),
                "biography": instagram_data.get("biography", f"Hair creator: {username}")
            })
            print(f"Successfully fetched Instagram data for {username}")
        except Exception as e:
            print(f"Instagram API failed for {username}: {type(e).__name__}: {str(e)}")
            print(f"Using form data only (no Instagram integration)")
    else:
        print(f"No Instagram credentials available, using form data only")
    
    # Convert price strings to floats, handling empty strings
    min_price_float = None
    max_price_float = None
    if min_price and min_price.strip():
        try:
            min_price_float = float(min_price)
        except (ValueError, TypeError):
            min_price_float = None
    if max_price and max_price.strip():
        try:
            max_price_float = float(max_price)
        except (ValueError, TypeError):
            max_price_float = None
    
    # Check if creator already exists (to determine if this is a new signup)
    existing_creator = get_creator_by_user_id(current_user["id"])
    is_new_creator = existing_creator is None
    
    # Upsert creator
    upsert_creator(current_user["id"], username, phone, location, min_price_float, max_price_float, 
                   calendar_url, profile_data)
    
    # Only ingest images for NEW creators (on signup), not on updates
    if is_new_creator:
        # Schedule background ingest if Instagram credentials are available
        if background_tasks and IG_ACCESS_TOKEN and IG_USER_ID:
            background_tasks.add_task(ingest_instagram_creators, [username], ingest_limit)
            print(f"Scheduled Instagram content ingest for NEW creator {username}")
        else:
            print(f"Skipping Instagram content ingest - no credentials or background tasks")
    else:
        print(f"Skipping image ingestion - creator {username} already exists (update, not signup)")
    
    return {"status": "ok", "scheduled_ingest_for": username if is_new_creator else None, "limit": ingest_limit, "is_new_creator": is_new_creator}

def ingest_instagram_creators(usernames: List[str], limit_per_user: int = 20):
    """Background task to ingest Instagram content for creators"""
    added = 0
    skipped = 0
    errors = []
    
    for uname in usernames:
        try:
            # Get recent media
            media_items = ig_get_recent_media_by_creator(uname, limit_per_user)
            
            # Expand all media to individual images
            images = ig_expand_media_to_images(media_items)
            
            for im in images:
                    url = im["media_url"]
                    image_uuid = uuid.uuid4()
                    caption = im.get("caption", "")
                    try:
                        # Generate embedding from temporary media URL
                        # The embedding is stored in DB for similarity search
                        # The image itself will be fetched on-demand using media_id via proxy
                        from app.image_processing import embed_image_from_url
                        img, embedding, (w, h), proxy_url = embed_image_from_url(url, im["id"])
                        
                        # Insert image row with embedding and media_id
                        # The embedding enables similarity search
                        # The media_id enables fetching image from Instagram on-demand
                        image_id = insert_image_row(
                            source="instagram",
                            source_id=im["id"],
                            url=im.get("permalink", url),
                            hashtags=[f"@{uname}"],  # Store as @username in hashtags
                            width=w,
                            height=h,
                            embedding=embedding,  # Stored for similarity search
                            caption=caption,  # Already extracted from im.get("caption", "") on line 97
                            media_id=im["id"],  # Used to fetch image on-demand via /api/images/{media_id}/proxy
                            creator_username=uname,  # Store creator username for efficient filtering
                            media_type=im.get("media_type"),  # IMAGE, CAROUSEL_ALBUM, or VIDEO
                            media_url=im.get("media_url")  # Temporary CDN URL (different from permalink)
                        )
                        
                        added += 1
                        
                    except Exception as e:
                        print(f"Failed to process image {url}: {e}")
            
            # Note: Sample image update should be done separately with user context
            # This function runs in background without current_user
                        
        except Exception as e:
            print(f"Failed to ingest for {uname}: {e}")
            errors.append(f"{uname}: {str(e)}")
            skipped += 1
    
    print(f"Ingest complete: {added} added, {skipped} skipped, {len(errors)} errors")
    return {"added": added, "skipped": skipped, "errors": errors}
