import io
import uuid
import os
import requests
from typing import Tuple, Optional
from PIL import Image
import torch
import clip
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
             
        return img, embedding, (width, height)
        
    except Exception as e:
        raise Exception(f"Failed to process image from URL {media_url}: {e}")

def insert_image_row(source: str, source_id: Optional[str], url: str,
                     hashtags: list, width: Optional[int], height: Optional[int],
                     embedding: torch.Tensor, caption: Optional[str] = None, 
                     media_id: Optional[str] = None, creator_username: Optional[str] = None,
                     media_type: Optional[str] = None, media_url: Optional[str] = None):
    """
    Insert image data into database
    
    Stores:
    - embedding: For similarity search (REQUIRED - must be provided)
    - media_id: To fetch image from Instagram on-demand via proxy
    - url: Original permalink (for reference)
    - creator_username: Creator's username (for efficient filtering and grouping)
    - media_type: Type of media (IMAGE, CAROUSEL_ALBUM, VIDEO)
    - Other metadata: width, height, caption, hashtags
    
    The actual image is NOT stored - it's fetched on-demand using media_id
    
    Args:
        embedding: REQUIRED torch.Tensor - CLIP embedding vector (512 dimensions)
    """
    if embedding is None:
        raise ValueError("embedding is required and cannot be None")
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
        
        # Ensure media_type column exists
        cur.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='images' AND column_name='media_type'
                ) THEN
                    ALTER TABLE images ADD COLUMN media_type TEXT;
                END IF;
            END $$;
        """)
        
        # Ensure media_url column exists (stores temporary CDN URL, separate from permalink)
        cur.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='images' AND column_name='media_url'
                ) THEN
                    ALTER TABLE images ADD COLUMN media_url TEXT;
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
        
        # Convert embedding tensor to JSONB (array of floats) - REQUIRED
        import json
        try:
            # Convert tensor to list of floats
            if hasattr(embedding, 'is_cuda') and embedding.is_cuda:
                embedding_list = embedding.detach().cpu().numpy().tolist()
            else:
                embedding_list = embedding.detach().numpy().tolist() if hasattr(embedding, 'detach') else embedding.tolist()
            
            # Store as JSONB (array of floats) - this is the "tensor" format
            embedding_value = json.dumps(embedding_list)
        except Exception as e:
            raise ValueError(f"Failed to convert embedding to JSON: {e}. Embedding is required.")
        
        # Insert with embedding (required)
        cur.execute(
            """
            INSERT INTO images (id, source, source_id, url, hashtags, width, height, embedding, caption, media_id, creator_username, media_type, media_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                width = EXCLUDED.width,
                height = EXCLUDED.height,
                caption = EXCLUDED.caption,
                media_id = EXCLUDED.media_id,
                creator_username = EXCLUDED.creator_username,
                media_type = EXCLUDED.media_type,
                media_url = EXCLUDED.media_url
            """,
            (uuid.uuid4(), source, source_id, url, hashtags, width, height, 
             embedding_value, 
             caption, media_id, creator_username, media_type, media_url)
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
