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
    """Initialize CLIP model (lazy loading)"""
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



def embed_image_from_url(media_url: str, media_id: str, media_type: Optional[str] = None) -> Tuple[Image.Image, torch.Tensor, Tuple[int, int], str]:
    """
    Generate embedding from existing media URL (temporary URL)
    
    This function:
    1. Fetches image from temporary URL (for videos, thumbnail_url is already set as media_url)
    2. Generates embedding (stored in DB for similarity search)
    3. Returns proxy URL that uses media_id to fetch on-demand
    
    The image itself is NOT saved locally - it will be fetched from Instagram
    using media_id when needed via the proxy endpoint.
    
    Note: For videos, the thumbnail_url is already set as media_url in ig_expand_media_to_images,
    so this function just treats it as a regular image.
    
    Args:
        media_url: URL to the image or video thumbnail
        media_id: Instagram media ID
        media_type: Optional media type ("IMAGE", "VIDEO", "CAROUSEL_ALBUM")
    """
    try:
        # Fetch image directly from the provided URL (for videos, this is already the thumbnail_url)
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
    - embedding: For similarity search (REQUIRED - must be provided) as VECTOR type
    - media_id: To fetch image from Instagram on-demand via proxy
    - url: Original permalink (for reference)
    - creator_username: Creator's username (for efficient filtering and grouping)
    - media_type: Type of media (IMAGE, CAROUSEL_ALBUM, VIDEO)
    - Other metadata: width, height, caption, hashtags
    
    The actual image is NOT stored - it's fetched on-demand using media_id
    
    Args:
        embedding: REQUIRED torch.Tensor - CLIP embedding vector (512 dimensions)
                   Will be stored as pgvector VECTOR(512) type
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
        
        # Convert embedding tensor to numpy array for pgvector VECTOR type
        import numpy as np
        try:
            # Convert tensor to numpy array
            if hasattr(embedding, 'is_cuda') and embedding.is_cuda:
                embedding_np = embedding.detach().cpu().numpy()
            elif hasattr(embedding, 'detach'):
                embedding_np = embedding.detach().numpy()
            elif hasattr(embedding, 'cpu'):
                embedding_np = embedding.cpu().numpy()
            elif not isinstance(embedding, np.ndarray):
                embedding_np = np.array(embedding)
            else:
                embedding_np = embedding
            
            # Ensure it's 1D and float32
            if len(embedding_np.shape) > 1:
                embedding_np = embedding_np.flatten()
            embedding_np = embedding_np.astype(np.float32)
            
            # Convert to list for pgvector (it will handle the conversion to VECTOR type)
            embedding_value = embedding_np.tolist()
        except Exception as e:
            raise ValueError(f"Failed to convert embedding to array: {e}. Embedding is required.")
        
        # Insert with embedding (required) - pgvector will convert the list to VECTOR type automatically
        # The list is passed directly and pgvector (registered in db.py) handles the conversion
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
    """Check if caption contains hair or makeup-related keywords"""
    if not caption:
        return False
    
    caption_lower = caption.lower()
    
    # Hair-related keywords (English)
    hair_keywords_en = [
        'hair', 'hairstyle', 'hairstyles', 'hairstylist', 'hairstyling', 
        'hairdesign', 'hairdesigner', 'hairartist', 'hairart', 'hairgoals',
        'hairinspo', 'hairinspiration', 'hairmagic', 'hairtransformation',
        'updo', 'updohair', 'upstyle', 'half-up', 'ponytail', 'bun', 
        'braid', 'braids', 'braidedhair', 'waves', 'curls', 'curly', 
        'curlyhair', 'curlybride', 'curlyhairstyle', 'curlinspo',
        'straight', 'sleek', 'bob', 'lob', 'pixie', 'shag', 'layers', 
        'fringe', 'bangs', 'wolf cut', 'fade', 'skin fade',
        'bridalhair', 'bridalhairstyle', 'bridalhairstylist', 'bridalstylist',
        'weddinghair', 'weddinghairstyle', 'weddinghairstylist', 'bridehair',
        'bridehairstyle', 'bridesmaid', 'glamhair', 'softglamhair',
        'romanticupdo', 'editorialhair', 'fashionhair', 'luxuryhair',
        'beautyhair', 'hairtutorial', 'haircare', 'hairideas', 'hairtrends'
    ]
    
    # Makeup-related keywords (English)
    makeup_keywords_en = [
        'makeup', 'make-up', 'makeupartist', 'makeupforbride', 
        'bridalmakeup', 'weddingmakeup', 'bridalmakeuplook', 
        'makeupideas', 'makeupinspiration', 'beautymakeup',
        'glammakeup', 'editorialmakeup', 'fashionmakeup'
    ]
    
    # Hair-related keywords (Hebrew)
    hair_keywords_he = [
        'שיער', 'תסרוקת', 'תסרוקות', 'תסרוקותכלה', 'תסרוקותכלות',
        'שיערכלה', 'שיערכלות', 'שיערלחתונה', 'שיערחתונה',
        'עיצובשיער', 'עיצובשיערכלה', 'עיצובשיערמקצועי',
        'מעצבתשיער', 'מעצבשיער', 'מעצבתשיערכלה',
        'תלתלים', 'תלתליםזהאופי', 'מתולתלות', 'תלתליםוואו',
        'גלים', 'שיערגלי', 'שיערמתולתלות',
        'אסוף', 'חצי-אסוף', 'קוקו', 'קוקס', 'צמה', 'צמות',
        'חלק', 'החלקה', 'תספורת', 'גזירה',
        'כלה', 'כלות', 'כלה2025', 'כלותישראל', 'כלהמאושרת',
        'מלווה', 'תסרוקתמלווה',
        'חתונה', 'אירוע', 'אירועים', 'אירועיוקרה',
        'דיפיוזר', 'ג\'ל', 'מוס', 'קרםלחות', 'מסכה',
        'נפח', 'תנועה', 'עמידות', 'קלילות', 'קופצניות'
    ]
    
    # Makeup-related keywords (Hebrew)
    makeup_keywords_he = [
        'איפור', 'איפורכלה', 'איפורמלווה', 'מאפרת', 'מאפר',
        'איפורושיער', 'איפורעדין', 'איפורזוהר', 'איפורטבעי'
    ]
    
    # Wedding/event keywords (both languages)
    event_keywords = [
        'wedding', 'bridal', 'bride', 'bridesmaid', 'groom',
        'חתונה', 'כלה', 'כלות', 'מלווה', 'חתן'
    ]
    
    # Combine all keywords
    all_keywords = hair_keywords_en + makeup_keywords_en + hair_keywords_he + makeup_keywords_he + event_keywords
    
    # Method 1: Check if any keyword appears in caption (substring match)
    if any(keyword in caption_lower for keyword in all_keywords):
        return True
    
    # Method 2: Split caption into words and check if words match or contain keywords
    # Split by whitespace and common separators, handling both English and Hebrew
    import re
    # Split on whitespace, punctuation, but keep Hebrew characters together
    # This regex splits on spaces, punctuation, but preserves Hebrew words
    words = re.findall(r'[\u0590-\u05FF]+|[a-zA-Z0-9]+', caption_lower)
    
    for word in words:
        word_lower = word.lower()
        # Check if word exactly matches a keyword
        if word_lower in all_keywords:
            return True
        # Check if any keyword is contained in the word
        if any(keyword in word_lower for keyword in all_keywords):
            return True
        # Check if word is contained in any keyword (for partial matches)
        # if any(word_lower == keyword for keyword in all_keywords):
        #     return True
    
    return False
