"""
Image Display API

Handles different image display modes for creator cards.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from typing import List, Dict, Any, Optional
from app.auth import get_current_user
from app.image_display_manager import (
    get_creator_display_image, 
    get_creator_all_images_for_search,
    update_creator_sample_image,
    get_creator_sample_image,
    set_creator_default_sample_image
)
from app.image_processing import image_to_embedding
from PIL import Image
import io

router = APIRouter(prefix="/api/display", tags=["display"])

@router.get("/creator/{username}/image")
def get_creator_card_image(
    username: str,
    mode: str = Query("default", description="Display mode: 'default' or 'similarity'"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get image for creator card display
    
    Args:
        username: Creator's Instagram username
        mode: Display mode ('default' or 'similarity')
        current_user: Current authenticated user
    
    Returns:
        Image data for creator card
    """
    try:
        if mode == "default":
            # Show default sample image
            image_data = get_creator_display_image(username)
        else:
            # For similarity mode, we need a query embedding
            raise HTTPException(400, "Similarity mode requires a query image")
        
        if not image_data:
            raise HTTPException(404, f"No images found for creator {username}")
        
        return {
            "username": username,
            "mode": mode,
            "image": image_data
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get creator image: {str(e)}")

@router.post("/creator/{username}/similar-image")
async def get_creator_similar_image(
    username: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Get most similar image from creator based on uploaded query image
    
    Args:
        username: Creator's Instagram username
        file: Uploaded query image
        current_user: Current authenticated user
    
    Returns:
        Most similar image from the creator
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Read and process query image
        contents = await file.read()
        img = Image.open(io.BytesIO(contents))
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Generate query embedding
        query_embedding = image_to_embedding(img)
        
        # Find most similar image from creator
        image_data = get_creator_display_image(username, query_embedding)
        
        if not image_data:
            raise HTTPException(404, f"No images found for creator {username}")
        
        return {
            "username": username,
            "mode": "similarity",
            "query_image": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(contents)
            },
            "similar_image": image_data
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to find similar image: {str(e)}")

@router.get("/creator/{username}/sample-image")
def get_creator_sample_image_endpoint(
    username: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get creator's designated sample image
    
    Args:
        username: Creator's Instagram username
        current_user: Current authenticated user
    
    Returns:
        Sample image data
    """
    try:
        image_data = get_creator_sample_image(username)
        
        if not image_data:
            raise HTTPException(404, f"No sample image found for creator {username}")
        
        return {
            "username": username,
            "sample_image": image_data
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get sample image: {str(e)}")

@router.put("/creator/{username}/sample-image")
def set_creator_sample_image_endpoint(
    username: str,
    image_id: str = Query(..., description="Image ID to set as sample"),
    current_user: dict = Depends(get_current_user)
):
    """
    Set creator's sample image
    
    Args:
        username: Creator's Instagram username
        image_id: Image ID to set as sample
        current_user: Current authenticated user
    
    Returns:
        Success status
    """
    try:
        success = update_creator_sample_image(username, image_id)
        
        if not success:
            raise HTTPException(400, f"Failed to update sample image for {username}")
        
        return {
            "username": username,
            "sample_image_id": image_id,
            "status": "updated"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to set sample image: {str(e)}")

@router.post("/creator/{username}/reset-sample")
def reset_creator_sample_image(
    username: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Reset creator's sample image to the newest image
    
    Args:
        username: Creator's Instagram username
        current_user: Current authenticated user
    
    Returns:
        Success status
    """
    try:
        success = set_creator_default_sample_image(username)
        
        if not success:
            raise HTTPException(400, f"Failed to reset sample image for {username}")
        
        return {
            "username": username,
            "status": "reset_to_newest"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to reset sample image: {str(e)}")

@router.get("/creator/{username}/all-images")
def get_creator_all_images(
    username: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all images from a creator (for admin/management purposes)
    
    Args:
        username: Creator's Instagram username
        current_user: Current authenticated user
    
    Returns:
        List of all creator images
    """
    try:
        images = get_creator_all_images_for_search(username)
        
        return {
            "username": username,
            "total_images": len(images),
            "images": images
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get creator images: {str(e)}")
