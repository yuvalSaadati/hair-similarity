import requests
import os
import json
from typing import Dict, List, Optional
from PIL import Image
import io
from app.config import IG_ACCESS_TOKEN, IG_APP_ID, IG_APP_SECRET, IG_USER_ID, MEDIA_AVATARS_DIR

def make_instagram_request(url, params=None):
    """Make an Instagram API request with current token"""
    if params is None:
        params = {}
    params["access_token"] = IG_ACCESS_TOKEN
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response

def ig_get_hashtag_id(hashtag: str) -> str:
    """Get Instagram hashtag ID from hashtag name"""
    url = f"https://graph.instagram.com/v18.0/ig_hashtag_search"
    params = {
        "user_id": IG_USER_ID,
        "q": hashtag
    }
    r = make_instagram_request(url, params)
    return r.json()["data"][0]["id"]

def ig_get_recent_media_by_hashtag(hashtag_id: str, limit: int = 30) -> List[Dict]:
    """Get recent media by hashtag ID"""
    url = f"https://graph.instagram.com/v18.0/{hashtag_id}/recent_media"
    params = {
        "user_id": IG_USER_ID,
        "fields": "id,media_type,media_url,permalink,caption"
    }
    r = make_instagram_request(url, params)
    return r.json()["data"][:limit]

def ig_get_media_url_by_id(media_id: str) -> str:
    """Get media URL by media ID"""
    url = f"https://graph.instagram.com/v18.0/{media_id}"
    params = {
        "fields": "media_url"
    }
    r = make_instagram_request(url, params)
    return r.json()["media_url"]

def ig_get_creator_profile(username: str) -> Dict:
    """Get Instagram creator profile data"""
    url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}"
    params = {
        "fields": f"business_discovery.username({username}){{profile_picture_url,biography}}"
    }
    r = make_instagram_request(url, params)
    
    bd = r.json()["business_discovery"]
    profile_picture_url = bd.get("profile_picture_url")
    
    return {
        "profile_picture_url": profile_picture_url,
        "biography": bd.get("biography", "")
    }

def ig_get_recent_media_by_creator(username: str, limit: int = 20) -> List[Dict]:
    """Get recent media by creator username"""
    url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}"
    params = {
        "fields": f"business_discovery.username({username}){{media{{id,media_type,media_url,permalink,caption}}}}"
    }
    r = make_instagram_request(url, params)
    
    try:
        media_data = r.json()["business_discovery"]["media"]["data"]
        return media_data[:limit]
    except KeyError:
        return []

def ig_expand_media_to_images(media_list: List[Dict]) -> List[Dict]:
    """Expand media list to individual images"""
    images = []
    for media in media_list:
        mtype = media.get("media_type")
        if mtype == "IMAGE":
            images.append(media)
        elif mtype == "VIDEO":
            # Include videos as well (they have media_url)
            # images.append(media)
            continue
        elif mtype == "CAROUSEL_ALBUM":
            # Use the media_url directly from the carousel album
            # No need to fetch children - the media_url is already available
            if media.get("media_url"):
                images.append(media)
     
    return images

def ig_get_most_recent_image(username: str) -> Optional[Dict]:
    """
    Get the most recent Instagram image for a creator
    
    Args:
        username: Creator's Instagram username
    
    Returns:
        Dict with media_id, media_url, caption, or None if no images found
    """
    try:
        # Get the most recent media (limit to 1 for efficiency)
        media_items = ig_get_recent_media_by_creator(username, limit=1)
        if not media_items:
            return None
        
        # Expand to images (handles carousel posts)
        # images = ig_expand_media_to_images(media_items)
        
        # Return the first (most recent) image
        first_image = media_items[0]
        return {
            "media_id": first_image.get("id"),
            "media_url": first_image.get("media_url"),
            "caption": first_image.get("caption", ""),
            "permalink": first_image.get("permalink", "")
        }
    except Exception as e:
        print(f"Error getting most recent image for {username}: {e}")
        return None