"""
Script to fetch image data and embedding from database by image ID
and display the actual image (embeddings cannot be decoded to images)
"""
import sys
import os
import requests
import json
import numpy as np
from PIL import Image
import io
import re

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import conn
from app.config import IG_ACCESS_TOKEN

def get_image_and_embedding(image_id: str):
    """
    Fetch image data and embedding from database, then display the actual image
    
    Args:
        image_id: UUID of the image in the database
    """
    print(f"🔍 Fetching image data for ID: {image_id}\n")
    
    with conn.cursor() as cur:
        # Query the database for image data and embedding
        cur.execute("""
            SELECT 
                id,
                source,
                source_id,
                url,
                hashtags,
                width,
                height,
                caption,
                media_id,
                creator_username,
                media_type,
                embedding,
                CASE 
                    WHEN embedding IS NOT NULL THEN 'Yes'
                    ELSE 'No'
                END as has_embedding
            FROM images
            WHERE id = %s
        """, (image_id,))
        
        row = cur.fetchone()
        
        if not row:
            print(f"❌ Image with ID {image_id} not found in database")
            return None
        
        # Unpack row data
        (db_id, source, source_id, url, hashtags, width, height, 
         caption, media_id, creator_username, media_type, embedding, has_embedding) = row
        
        print("✅ Image found in database!")
        print(f"\n📋 Image Details:")
        print(f"  ID: {db_id}")
        print(f"  Source: {source}")
        print(f"  Source ID: {source_id}")
        print(f"  URL: {url}")
        print(f"  Hashtags: {hashtags}")
        print(f"  Dimensions: {width}x{height}")
        print(f"  Caption: {caption[:100] if caption else 'None'}...")
        print(f"  Media ID: {media_id}")
        print(f"  Creator: {creator_username}")
        print(f"  Media Type: {media_type}")
        print(f"  Has Embedding: {has_embedding}")
        
        # Display embedding information
        if has_embedding == 'Yes' and embedding:
            print(f"\n📊 Embedding Information:")
            
            # Parse JSONB embedding
            if isinstance(embedding, str):
                emb_array = json.loads(embedding)
            else:
                emb_array = embedding
            
            emb_np = np.array(emb_array, dtype=np.float32)
            
            print(f"  Embedding dimension: {len(emb_array)}")
            print(f"  Embedding shape: {emb_np.shape}")
            print(f"  Embedding min: {emb_np.min():.6f}")
            print(f"  Embedding max: {emb_np.max():.6f}")
            print(f"  Embedding mean: {emb_np.mean():.6f}")
            print(f"  Embedding std: {emb_np.std():.6f}")
            print(f"\n  ⚠️  Note: Embeddings are vector representations for similarity search.")
            print(f"  They cannot be decoded back into images.")
            print(f"  They are 512-dimensional CLIP embeddings (float arrays).")
        
        # Fetch and display the actual image
        print(f"\n📷 Fetching actual image...")
        
        # Check if URL is an Instagram post URL first (most reliable method)
        if url and ('instagram.com/p/' in url or 'instagram.com/reel/' in url):
            print(f"  Using Instagram post URL: {url}")
            return fetch_image_from_instagram_url(url)
        
        # Try using media_id (Instagram proxy)
        if media_id:
            print(f"  Using media_id: {media_id}")
            try:
                from app.image_proxy import fetch_instagram_image_by_id
                result = fetch_instagram_image_by_id(media_id)
                if result:
                    img, fetched_url = result
                    print(f"  ✅ Successfully fetched image from Instagram!")
                    print(f"  Image size: {img.size}")
                    print(f"  Image mode: {img.mode}")
                    print(f"  Fetched from: {fetched_url}")
                    
                    # Save image to file
                    output_path = f"image_{image_id[:8]}.jpg"
                    img.save(output_path, "JPEG")
                    print(f"  💾 Saved image to: {output_path}")
                    
                    # Display image
                    img.show()
                    return img
                else:
                    raise Exception("Failed to fetch from Instagram")
            except Exception as e:
                print(f"  ⚠️  Failed to fetch via media_id: {e}")
                # Fall back to URL
                if url:
                    print(f"  Trying URL fallback...")
                    return fetch_image_from_url(url, image_id)
        elif url:
            print(f"  Using URL: {url}")
            return fetch_image_from_url(url, image_id)
        else:
            print(f"  ❌ No media_id or URL available to fetch image")
            return None

def fetch_image_from_url(url: str, image_id: str = None):
    """Fetch image from direct image URL"""
    try:
        # Check if it's an Instagram URL first
        if 'instagram.com' in url:
            print(f"  ⚠️  URL appears to be an Instagram post, trying Instagram extraction...")
            return fetch_image_from_instagram_url(url)
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'image' not in content_type:
            print(f"  ⚠️  URL doesn't appear to be a direct image (content-type: {content_type})")
            # Try to parse as HTML and look for image
            if 'instagram.com' in url:
                return fetch_image_from_instagram_url(url)
            return None
        
        img = Image.open(io.BytesIO(response.content))
        print(f"  ✅ Successfully fetched image from URL!")
        print(f"  Image size: {img.size}")
        print(f"  Image mode: {img.mode}")
        
        # Save image to file
        if image_id:
            output_path = f"image_{image_id[:8]}.jpg"
        else:
            output_path = "image_from_url.jpg"
        img.save(output_path, "JPEG")
        print(f"  💾 Saved image to: {output_path}")
        
        # Display image
        img.show()
        return img
    except Exception as e:
        print(f"  ❌ Failed to fetch image from URL: {e}")
        # If it's an Instagram URL, try the Instagram extraction method
        if 'instagram.com' in url:
            print(f"  Trying Instagram URL extraction as fallback...")
            return fetch_image_from_instagram_url(url)
        return None

def fetch_image_from_instagram_url(instagram_url: str):
    """
    Extract and fetch image from Instagram post URL
    
    Args:
        instagram_url: Instagram post URL (e.g., https://www.instagram.com/p/DHBg6FvsxnK/)
    
    Returns:
        PIL Image or None if failed
    """
    import requests
    from bs4 import BeautifulSoup

    url = "https://www.instagram.com/p/DNgOQE1M_Eq/"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")

    # Instagram embeds the image in OpenGraph meta tags
    meta_image = soup.find("meta", property="og:image")
    if meta_image:
        print("Image URL:", meta_image["content"])


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch image from database or Instagram URL")
    parser.add_argument("--image-id", type=str, help="Database image ID (UUID)")
    parser.add_argument("--instagram-url", type=str, help="Instagram post URL")
    
    args = parser.parse_args()
    
    if args.instagram_url:
        # Fetch from Instagram URL
        result = fetch_image_from_instagram_url(args.instagram_url)
        if result:
            print(f"\n✅ Successfully retrieved and displayed image from Instagram!")
        else:
            print(f"\n❌ Failed to retrieve image from Instagram URL")
    elif args.image_id:
        # Fetch from database
        result = get_image_and_embedding(args.image_id)
        if result:
            print(f"\n✅ Successfully retrieved and displayed image!")
        else:
            print(f"\n❌ Failed to retrieve image")
    else:
        # Default: use the hardcoded image ID
        image_id = "047dc0ed-8e5b-4e84-a4f1-05305e7ad282"
        print("No arguments provided, using default image ID")
        print("Usage examples:")
        print("  python get_image_from_embedding.py --image-id <uuid>")
        print("  python get_image_from_embedding.py --instagram-url https://www.instagram.com/p/DHBg6FvsxnK/")
        print()
        
        result = get_image_and_embedding(image_id)
        if result:
            print(f"\n✅ Successfully retrieved and displayed image!")
        else:
            print(f"\n❌ Failed to retrieve image")
