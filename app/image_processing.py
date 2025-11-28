import io
import uuid
import os
import requests
from typing import Tuple, Optional
from PIL import Image
import torch
import clip
from pgvector import Vector
from app.config import MEDIA_IMAGES_DIR, MEDIA_AVATARS_DIR
from app.db import conn

# CLIP model will be loaded lazily
device = "cuda" if torch.cuda.is_available() else "cpu"
model = None
preprocess = None

def get_clip_model():
    global model, preprocess
    if model is None:
        model, preprocess = clip.load("ViT-B/32", device=device)
    return model, preprocess

def image_to_embedding(img: Image.Image) -> torch.Tensor:
    """Convert PIL Image to CLIP embedding vector"""
    model, preprocess = get_clip_model()
    image_input = preprocess(img).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
    return image_features[0]

def fetch_and_embed_image(url: str, image_id: uuid.UUID) -> Tuple[Image.Image, torch.Tensor, Tuple[int, int], str]:
    """Fetch image from URL and return embedding (no local storage)"""
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content))
    
    emb = image_to_embedding(img)
    # Return proxy URL instead of local URL
    proxy_url = f"/api/images/{image_id}/proxy"
    return img, emb, img.size, proxy_url

def fetch_and_embed_instagram_image(media_id: str, source_id: str) -> Tuple[Image.Image, torch.Tensor, Tuple[int, int], str]:
    """Fetch Instagram image by media ID, generate embedding, return proxy URL"""
    from app.image_proxy import fetch_instagram_image_by_id
    
    # Fetch image from Instagram
    result = fetch_instagram_image_by_id(media_id)
    if not result:
        raise Exception(f"Failed to fetch Instagram image {media_id}")
    
    img, original_url = result
    
    # Get dimensions
    width, height = img.size
    
    # Generate embedding
    embedding = image_to_embedding(img)
    
    # Return proxy URL instead of local file
    proxy_url = f"/api/images/{media_id}/proxy"
    
    return img, embedding, (width, height), proxy_url

def embed_image_from_url(media_url: str, media_id: str) -> Tuple[Image.Image, torch.Tensor, Tuple[int, int], str]:
    """
    Generate embedding from existing media URL (temporary URL)
    
    This function:
    1. Fetches image from temporary URL
    2. Generates embedding (stored in DB for similarity search)
    3. Returns proxy URL that uses media_id to fetch on-demand
    
    The image itself is NOT saved locally - it will be fetched from Instagram
    using media_id when needed via the proxy endpoint.
    """
    try:
        # Fetch image directly from the provided URL (temporary CDN URL)
        response = requests.get(media_url, timeout=30)
        response.raise_for_status()
        
        # Convert to PIL Image
        img = Image.open(io.BytesIO(response.content))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Get dimensions
        width, height = img.size
        
        # Generate embedding (this is what we store in DB for similarity search)
        embedding = image_to_embedding(img)
        
        # Return proxy URL that will fetch image by media_id when needed
        # The proxy endpoint uses fetch_instagram_image_by_id() which gets
        # a fresh URL from Instagram Graph API using the media_id
        proxy_url = f"/api/images/{media_id}/proxy"
        
        return img, embedding, (width, height), proxy_url
        
    except Exception as e:
        raise Exception(f"Failed to process image from URL {media_url}: {e}")

def insert_image_row(source: str, source_id: Optional[str], url: str,
                     hashtags: list, width: Optional[int], height: Optional[int],
                     embedding: Optional[torch.Tensor], caption: Optional[str] = None, 
                     media_id: Optional[str] = None, creator_username: Optional[str] = None):
    """
    Insert image data into database
    
    Stores:
    - embedding: For similarity search (this is the main purpose)
    - media_id: To fetch image from Instagram on-demand via proxy
    - url: Original permalink (for reference)
    - creator_username: Creator's username (for efficient filtering and grouping)
    - Other metadata: width, height, caption, hashtags
    
    The actual image is NOT stored - it's fetched on-demand using media_id
    """
    with conn.cursor() as cur:
        # Ensure creator_username column exists
        cur.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='images' AND column_name='creator_username'
                ) THEN
                    ALTER TABLE images ADD COLUMN creator_username TEXT;
                    CREATE INDEX IF NOT EXISTS idx_images_creator_username ON images(creator_username);
                END IF;
            END $$;
        """)
        
        # Extract creator username from hashtags if not provided
        if not creator_username and hashtags:
            # Look for hashtag starting with @ (creator username)
            for tag in hashtags:
                if tag and tag.startswith('@'):
                    creator_username = tag[1:]  # Remove @
                    break
        
        cur.execute(
            """
            INSERT INTO images (id, source, source_id, url, hashtags, width, height, embedding, caption, media_id, creator_username)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                width = EXCLUDED.width,
                height = EXCLUDED.height,
                caption = EXCLUDED.caption,
                media_id = EXCLUDED.media_id,
                creator_username = EXCLUDED.creator_username
            """,
            (uuid.uuid4(), source, source_id, url, hashtags, width, height, 
             Vector(embedding.tolist()) if embedding is not None else None, 
             caption, media_id, creator_username)
        )

def is_hair_related_caption(caption: str) -> bool:
    """Check if caption contains hair-related keywords"""
    if not caption:
        return False
    
    hair_keywords = [
        'hair', 'updo', 'half-up', 'ponytail', 'bun', 'braid', 'braids', 
        'waves', 'curls', 'curly', 'straight', 'sleek', 'bob', 'lob', 
        'pixie', 'shag', 'layers', 'fringe', 'bangs', 'wolf cut', 'fade', 
        'skin fade', 'שיער', 'תסרוקת', 'פן', 'עיצוב', 'מעצב', 'אסוף', 
        'חצי-אסוף', 'קוקו', 'קוקס', 'צמה', 'צמות', 'גלים', 'תלתלים', 
        'חלק', 'כלה', 'wedding', 'bridal', 'bride', 'תלתלים'
    ]
    
    caption_lower = caption.lower()
    return any(keyword in caption_lower for keyword in hair_keywords)

def generate_embedding_on_demand(media_id: str) -> Optional[torch.Tensor]:
    """
    Generate embedding for an image on-demand when needed for similarity search
    
    Args:
        media_id: Instagram media ID
    
    Returns:
        CLIP embedding tensor or None if failed
    """
    try:
        from app.image_proxy import fetch_instagram_image_by_id
        
        # Fetch image from Instagram
        result = fetch_instagram_image_by_id(media_id)
        if not result:
            return None
        
        img, _ = result
        
        # Generate embedding
        embedding = image_to_embedding(img)
        
        # Update database with embedding and dimensions
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE images 
                SET embedding = %s, width = %s, height = %s
                WHERE media_id = %s
            """, (Vector(embedding.tolist()), img.width, img.height, media_id))
        
        return embedding
        
    except Exception as e:
        print(f"Failed to generate embedding for {media_id}: {e}")
        return None
