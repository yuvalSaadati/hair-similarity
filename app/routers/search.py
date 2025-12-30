from fastapi import APIRouter, File, UploadFile, Query, HTTPException
from typing import List, Optional
from app.image_processing import image_to_embedding
from app.database import search_similar_images, search_similar_images_by_creator, get_random_photos
from PIL import Image
import io

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/upload")
def search_by_upload(file: UploadFile = File(...), limit: int = 12):
    """Search for similar images by uploading an image"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    try:
        # Read and process image
        contents = file.file.read()
        img = Image.open(io.BytesIO(contents))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        embedding = image_to_embedding(img)
        
        # Search for similar images
        results = search_similar_images(embedding, limit)
        
        return {"matches": results}
    except Exception as e:
        raise HTTPException(400, f"Error processing image: {str(e)}")

@router.post("/upload/by-creator")
async def search_by_upload_by_creator(file: UploadFile = File(...), limit: int = 10):
    """
    Search for similar images grouped by creator
    
    Returns the most similar image for EACH creator, sorted by similarity score.
    This is used for displaying creator cards with their best matching images.
    Limited to top 10 creators by default.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    try:
        # Read and process image
        contents = await file.read()
        img = Image.open(io.BytesIO(contents))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        embedding = image_to_embedding(img)
        
        # Find most similar image for each creator
        results = search_similar_images_by_creator(embedding)
        
        # Limit to top N creators (default 10)
        limited_results = results[:limit]
        
        return {
            "matches": limited_results,
            "total_creators": len(limited_results),
            "total_found": len(results)
        }
    except Exception as e:
        import traceback
        print(f"Error in search_by_upload_by_creator: {traceback.format_exc()}")
        raise HTTPException(500, f"Error processing image: {str(e)}")

