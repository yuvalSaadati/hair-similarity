from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional
from app.auth import get_current_user
from app.database import get_creator_by_user_id, upsert_creator
from app.instagram import ig_get_creator_profile, ig_get_most_recent_image
from app.routers.creators import ingest_instagram_creators

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
                     arrival_location: Optional[str] = Query(None),
                     min_price: Optional[str] = Query(None),
                     max_price: Optional[str] = Query(None),
                     price_hairstyle_bride: Optional[str] = Query(None),
                     price_hairstyle_bridesmaid: Optional[str] = Query(None),
                     price_makeup_bride: Optional[str] = Query(None),
                     price_makeup_bridesmaid: Optional[str] = Query(None),
                     price_hairstyle_makeup_combo: Optional[str] = Query(None),
                     price_hairstyle_makeup_bridesmaid_combo: Optional[str] = Query(None),
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
    def parse_price(price_str):
        if price_str and price_str.strip():
            try:
                return float(price_str)
            except (ValueError, TypeError):
                return None
        return None
    
    min_price_float = parse_price(min_price)
    max_price_float = parse_price(max_price)
    price_hairstyle_bride_float = parse_price(price_hairstyle_bride)
    price_hairstyle_bridesmaid_float = parse_price(price_hairstyle_bridesmaid)
    price_makeup_bride_float = parse_price(price_makeup_bride)
    price_makeup_bridesmaid_float = parse_price(price_makeup_bridesmaid)
    price_hairstyle_makeup_combo_float = parse_price(price_hairstyle_makeup_combo)
    price_hairstyle_makeup_bridesmaid_combo_float = parse_price(price_hairstyle_makeup_bridesmaid_combo)
    
    # Get most recent image from Instagram
    recent_image_url = None
    if IG_ACCESS_TOKEN and IG_USER_ID:
        try:
            recent_image = ig_get_most_recent_image(username)
            if recent_image and recent_image.get("media_url"):
                recent_image_url = recent_image["media_url"]
        except Exception as e:
            print(f"Failed to get recent image for {username}: {e}")
            # Continue without recent_image if it fails
    
    # Check if creator already exists (to determine if this is a new signup)
    existing_creator = get_creator_by_user_id(current_user["id"])
    is_new_creator = existing_creator is None
    
    # Upsert creator
    try:
        upsert_creator(current_user["id"], username, phone, location, arrival_location, min_price_float, max_price_float, 
                       calendar_url, profile_data,
                       price_hairstyle_bride=price_hairstyle_bride_float,
                       price_hairstyle_bridesmaid=price_hairstyle_bridesmaid_float,
                       price_makeup_bride=price_makeup_bride_float,
                       price_makeup_bridesmaid=price_makeup_bridesmaid_float,
                       price_hairstyle_makeup_combo=price_hairstyle_makeup_combo_float,
                       price_hairstyle_makeup_bridesmaid_combo=price_hairstyle_makeup_bridesmaid_combo_float,
                       recent_image=recent_image_url)
    except ValueError as e:
        # User-friendly error message (already in Hebrew from upsert_creator)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Generic error handling
        raise HTTPException(status_code=500, detail=f"שגיאה בשמירת הפרופיל: {str(e)}")
    
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
