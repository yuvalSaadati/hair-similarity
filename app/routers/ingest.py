from fastapi import APIRouter, Query, BackgroundTasks
from typing import List
from app.instagram import ig_expand_media_to_images
from app.image_processing import fetch_and_embed_image, insert_image_row, is_hair_related_caption
from app.db import conn
import uuid

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/instagram/creators")
def ingest_instagram_creators(usernames: List[str] = Query(..., description="creator usernames"),
                            limit_per_user: int = 100):
    """Ingest Instagram content by creator usernames"""
    added = 0
    skipped = 0
    errors = []
    
    for uname in usernames:
        try:
            from app.instagram import ig_get_recent_media_by_creator
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
                                       [f"@{uname}"], w, h, emb, caption=caption, media_id=im["id"], creator_username=uname)
                        added += 1
                    except Exception as e:
                        skipped += 1
                        errors.append(str(e))
                        
        except Exception as e:
            errors.append(f"Failed to ingest {uname}: {str(e)}")
    
    return {
        "status": "ok",
        "added": added,
        "skipped": skipped,
        "errors": errors
    }
