import requests
import os
import json
from typing import Dict, List, Optional
from PIL import Image
import io
from app.config import IG_ACCESS_TOKEN, IG_USER_ID

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

def ig_get_video_thumbnail_url(media_id: str) -> Optional[str]:
    """
    Get thumbnail URL for a video media item (as shown on Instagram page)
    
    Args:
        media_id: Instagram media ID
        
    Returns:
        Thumbnail URL if available, None otherwise
    """
    try:
        url = f"https://graph.instagram.com/v18.0/{media_id}"
        params = {
            "fields": "thumbnail_url,media_type"
        }
        r = make_instagram_request(url, params)
        data = r.json()
        
        # Check if it's a video and has thumbnail_url
        if data.get("media_type") == "VIDEO" and data.get("thumbnail_url"):
            return data["thumbnail_url"]
        return None
    except Exception as e:
        print(f"Failed to get thumbnail URL for media {media_id}: {e}")
        return None

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

def ig_get_recent_media_by_creator(username: str, limit: int = 30) -> List[Dict]:
    """Get recent media by creator username"""
    url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}"
    params = {
        "fields": f"business_discovery.username({username}){{media{{id,media_type,media_url,thumbnail_url,permalink,caption}}}}"
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
            # For videos, try to get thumbnail_url (Instagram's official thumbnail as shown on page)
            thumbnail_url = media.get("thumbnail_url")
            
            # If not in initial response, try fetching it separately
            if not thumbnail_url:
                media_id = media.get("id")
                if media_id:
                    thumbnail_url = ig_get_video_thumbnail_url(media_id)
            
            if thumbnail_url:
                # Use Instagram's official thumbnail (as shown on Instagram page)
                video_with_thumbnail = media.copy()
                video_with_thumbnail["media_url"] = thumbnail_url  # Use thumbnail as media_url for processing
                video_with_thumbnail["original_media_url"] = media.get("media_url")  # Keep original video URL
                images.append(video_with_thumbnail)
            # If no thumbnail_url available, skip the video (we only use Instagram's official thumbnails)
        elif mtype == "CAROUSEL_ALBUM":
            # Use the media_url directly from the carousel album
            # No need to fetch children - the media_url is already available
            if media.get("media_url"):
                images.append(media)
     
    return images

def ig_get_most_recent_image(username: str) -> Optional[Dict]:
    """
    Get the most recent Instagram image for a creator.
    Prefers IMAGE or CAROUSEL_ALBUM, falls back to VIDEO thumbnail if no images found.
    
    Args:
        username: Creator's Instagram username
    
    Returns:
        Dict with media_id, media_url, caption, or None if no media found
    """
    try:
        # Get recent media (fetch more to find first image if first is a video)
        media_items = ig_get_recent_media_by_creator(username, limit=30)
        if not media_items:
            return None
        
        # First, try to find IMAGE or CAROUSEL_ALBUM
        for media in media_items:
            mtype = media.get("media_type")
            if mtype == "IMAGE" or mtype == "CAROUSEL_ALBUM":
                # Only return if it has a media_url (images should have this)
                if media.get("media_url"):
                    return {
                        "media_id": media.get("id"),
                        "media_url": media.get("media_url"),
                        "caption": media.get("caption", ""),
                        "permalink": media.get("permalink", ""),
                        "media_type": mtype
                    }
        
        # No images found - fall back to first VIDEO and use its thumbnail
        for media in media_items:
            mtype = media.get("media_type")
            if mtype == "VIDEO":
                # Try to get thumbnail_url from the media object first
                thumbnail_url = media.get("thumbnail_url")
                
                # If not in initial response, try fetching it separately
                if not thumbnail_url:
                    media_id = media.get("id")
                    if media_id:
                        thumbnail_url = ig_get_video_thumbnail_url(media_id)
                
                # If we have a thumbnail, return it
                if thumbnail_url:
                    return {
                        "media_id": media.get("id"),
                        "media_url": thumbnail_url,  # Use thumbnail as media_url
                        "caption": media.get("caption", ""),
                        "permalink": media.get("permalink", ""),
                        "media_type": "VIDEO"
                    }
        
        # No images or videos with thumbnails found
        return None
    except Exception as e:
        print(f"Error getting most recent image for {username}: {e}")
        return None