from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional
from app.auth import get_current_user
from app.database import get_creators, get_creator_by_user_id, upsert_creator
from app.image_display_manager import get_creator_display_image
from app.instagram import ig_get_creator_profile, ig_get_recent_media_by_creator, ig_expand_media_to_images
from app.image_processing import fetch_and_embed_image, insert_image_row, is_hair_related_caption
from app.db import conn
import uuid

router = APIRouter(prefix="/api/creators", tags=["creators"])

@router.get("")
def get_creators_endpoint():
    """Get all creators"""
    return {"creators": get_creators()}

@router.get("/with-display-images")
def get_creators_with_display_images():
    """Get all creators with their display images"""
    try:
        creators = get_creators()
        
        # Convert Pydantic models to dicts and add display image for each creator
        creators_with_images = []
        for creator in creators:
            # Convert Pydantic model to dict (works with both Pydantic v1 and v2)
            if hasattr(creator, 'model_dump'):
                creator_dict = creator.model_dump()  # Pydantic v2
            elif hasattr(creator, 'dict'):
                creator_dict = creator.dict()  # Pydantic v1
            else:
                # Fallback: access attributes directly
                creator_dict = {
                    "creator_id": getattr(creator, 'creator_id', None),
                    "username": getattr(creator, 'username', None),
                    "phone": getattr(creator, 'phone', None),
                    "location": getattr(creator, 'location', None),
                    "min_price": getattr(creator, 'min_price', None),
                    "max_price": getattr(creator, 'max_price', None),
                    "calendar_url": getattr(creator, 'calendar_url', None),
                    "profile_picture": getattr(creator, 'profile_picture', None),
                    "bio": getattr(creator, 'bio', None),
                    "post_count": getattr(creator, 'post_count', 0),
                    "sample_image": getattr(creator, 'sample_image', None),
                    "sample_image_id": getattr(creator, 'sample_image_id', None),
                    "profile_url": getattr(creator, 'profile_url', None),
                }
            
            username = creator_dict.get("username")
            if username:
                # Fetch profile picture from Instagram API (fresher than database)
                from app.instagram import ig_get_creator_profile, ig_get_most_recent_image
                
                # Get profile picture from Instagram API (keep database value as fallback)
                try:
                    profile_data = ig_get_creator_profile(username)
                    if profile_data.get("profile_picture_url"):
                        creator_dict["profile_picture"] = profile_data["profile_picture_url"]
                except Exception as e:
                    print(f"Failed to get profile picture for {username}: {e}")
                    # Keep the profile_picture from database as fallback
                
                # Try to get most recent Instagram image from API (fresher than database)
                try:
                    recent_image = ig_get_most_recent_image(username)
                    creator_dict["display_image"] = recent_image["media_url"]
                    # Use proxy URL for recent image from Instagram API
                    creator_dict["recent_image"] = recent_image["media_url"]
                except Exception as e:
                    print(f"Failed to get display image for {username}: {e}")
                    import traceback
                    print(traceback.format_exc())
                    creator_dict["display_image"] = None
                    creator_dict["recent_image"] = None
            else:
                creator_dict["display_image"] = None
                creator_dict["recent_image"] = None
            
            creators_with_images.append(creator_dict)
        
        return {"creators": creators_with_images}
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_creators_with_display_images: {error_details}")
        raise HTTPException(500, f"Failed to get creators with display images: {str(e)}")

@router.get("/me")
def get_my_creator(current_user: dict = Depends(get_current_user)):
    """Get current user's creator profile"""
    creator = get_creator_by_user_id(current_user["id"])
    return {"creator": creator}

@router.put("/me")
def upsert_my_creator(request: dict, current_user: dict = Depends(get_current_user),
                     background_tasks: BackgroundTasks = None):
    """Create or update current user's creator profile"""
    
    # Extract data from request
    username = request.get("username")
    phone = request.get("phone")
    location = request.get("location")
    min_price = request.get("min_price")
    max_price = request.get("max_price")
    calendar_url = request.get("calendar_url")
    ingest_limit = request.get("ingest_limit", 100)
    
    if not username:
        raise HTTPException(400, "Username is required")
    
    # Get Instagram profile data
    try:
        profile_data = ig_get_creator_profile(username)
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch Instagram profile: {str(e)}")
    
    # Validate creator (check if bio contains hair-related terms)
    bio = profile_data.get("biography", "")
    if not is_hair_related_caption(bio) and not is_hair_related_caption(username):
        raise HTTPException(400, "Creator profile must contain hair-related content")
    
    # Check if creator already exists (to determine if this is a new signup)
    from app.database import get_creator_by_user_id
    existing_creator = get_creator_by_user_id(current_user["id"])
    is_new_creator = existing_creator is None
    
    # Upsert creator
    upsert_creator(current_user["id"], username, phone, location, min_price, max_price, 
                   calendar_url, profile_data)
    
    # Only ingest images for NEW creators (on signup), not on updates
    if is_new_creator:
        # Trigger background task to ingest Instagram images
        if background_tasks:
            background_tasks.add_task(ingest_instagram_creators, [username], ingest_limit)
            print(f"Scheduled Instagram content ingest for NEW creator {username} (limit: {ingest_limit})")
        else:
            # If no background tasks available, run synchronously (not recommended for production)
            print(f"Running Instagram content ingest synchronously for NEW creator {username}")
            ingest_instagram_creators([username], ingest_limit)
    else:
        print(f"Skipping image ingestion - creator {username} already exists (update, not signup)")
    
    return {"status": "ok", "scheduled_ingest_for": username if is_new_creator else None, "limit": ingest_limit, "is_new_creator": is_new_creator}

@router.get("/{username}/images")
def get_creator_images(username: str, current_user: dict = Depends(get_current_user)):
    """Get all images for a specific creator"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, url, local_url, caption, created_at
            FROM images
            WHERE EXISTS (
                SELECT 1 FROM unnest(hashtags) h
                WHERE h = '@' || %s
            )
            ORDER BY created_at DESC
        """, (username,))
        rows = cur.fetchall()
    
    return {"images": [
        {
            "id": str(r[0]),
            "url": r[1],
            "local_url": r[2],
            "caption": r[3],
            "created_at": r[4].isoformat() if r[4] else None
        } for r in rows
    ]}

@router.post("/{username}/set-default-image")
def set_default_image(username: str, image_data: dict, current_user: dict = Depends(get_current_user)):
    """Set a default image for a creator"""
    image_id = image_data.get("image_id")
    if not image_id:
        raise HTTPException(400, "image_id is required")
    
    with conn.cursor() as cur:
        # Verify the image belongs to this creator
        cur.execute("""
            SELECT id FROM images
            WHERE id = %s AND EXISTS (
                SELECT 1 FROM unnest(hashtags) h
                WHERE h = '@' || %s
            )
        """, (image_id, username))
        
        if not cur.fetchone():
            raise HTTPException(404, "Image not found for this creator")
        
        # Update the creator's sample image preference
        cur.execute("""
            UPDATE creators 
            SET sample_image_id = %s, updated_at = now()
            WHERE username = %s
        """, (image_id, username))
        
        if cur.rowcount == 0:
            raise HTTPException(404, "Creator not found")
    
    return {"status": "ok", "message": "Default image updated"}

def ingest_instagram_creators(usernames: List[str], limit_per_user: int = 100):
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
                    
                    try:
                        caption = im.get("caption") or ""
                        if not is_hair_related_caption(caption):
                            skipped += 1
                            continue
                            
                        from app.image_processing import embed_image_from_url
                        img, emb, (w, h), proxy_url = embed_image_from_url(url, im["id"])
                        insert_image_row("instagram", im["id"], im.get("permalink", url),
                                       [f"@{uname}"], w, h, emb, caption=caption, media_id=im["id"], creator_username=uname, media_type=im.get("media_type"))
                        added += 1
                    except Exception as e:
                        skipped += 1
                        errors.append(str(e))
                        
        except Exception as e:
            errors.append(f"Failed to ingest {uname}: {str(e)}")
    
    print(f"Ingest complete: {added} added, {skipped} skipped, {len(errors)} errors")
    if errors:
        print("Errors:", errors)
