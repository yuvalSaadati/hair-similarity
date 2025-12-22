from typing import List, Optional, Dict, Any
from app.db import conn
from app.models import CreatorResponse

def setup_database_schema():
    """Initialize database schema and tables"""
    with conn.cursor() as cur:
        # Check if vector extension exists
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """)
        has_vector = cur.fetchone()[0]
        
        # Try to create vector extension if it doesn't exist
        if not has_vector:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                # Re-check
                cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
                has_vector = cur.fetchone()[0]
                if has_vector:
                    print("✅ Successfully created vector extension")
            except Exception as e:
                print(f"⚠️  Could not create vector extension: {e}")
                # Continue to check if it exists anyway (might have been created by another process)
                cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
                has_vector = cur.fetchone()[0]
        
        # Users table for authentication
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'creator',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """)
        
        # Creator profiles table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS creators (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID UNIQUE REFERENCES users(id),
            username TEXT UNIQUE NOT NULL,
            phone TEXT,
            location TEXT,
            min_price NUMERIC,
            max_price NUMERIC,
            calendar_url TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            instagram_bio TEXT,
            instagram_profile_picture TEXT,
            profile_picture_local TEXT,
            calendar_provider TEXT,        
            oauth_account_email TEXT,
            timezone TEXT DEFAULT 'Asia/Jerusalem',
            google_refresh_token TEXT,
            google_access_token TEXT,
            google_token_expiry TIMESTAMPTZ,
            sample_image_id UUID
        );
        """)
        
        # Images table - embedding is REQUIRED (NOT NULL) stored as JSONB (array of floats)
        # This stores the tensor/embedding as a JSON array, no pgvector needed
        cur.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id UUID PRIMARY KEY,
            source TEXT NOT NULL,
            source_id TEXT,
            url TEXT,
            hashtags TEXT[] DEFAULT '{}',
            width INT,
            height INT,
            created_at TIMESTAMPTZ DEFAULT now(),
            embedding JSONB NOT NULL,
            caption TEXT,
            media_id TEXT,
            UNIQUE(source, source_id)
        );
        """)
        
        # Create GIN index on embedding for faster queries
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_images_embedding_gin 
        ON images USING GIN (embedding);
        """)
        
        print("✅ Created images table with JSONB embedding column (stores tensor as array of floats)")
        
        # Add columns if they don't exist
        cur.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='images' AND column_name='caption'
          ) THEN
            ALTER TABLE images ADD COLUMN caption TEXT;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='images' AND column_name='media_type'
          ) THEN
            ALTER TABLE images ADD COLUMN media_type TEXT;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='creators' AND column_name='sample_image_id'
          ) THEN
            ALTER TABLE creators ADD COLUMN sample_image_id UUID;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='images' AND column_name='media_id'
          ) THEN
            ALTER TABLE images ADD COLUMN media_id TEXT;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='images' AND column_name='local_url'
          ) THEN
            ALTER TABLE images ADD COLUMN local_url TEXT;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='images' AND column_name='creator_username'
          ) THEN
            ALTER TABLE images ADD COLUMN creator_username TEXT;
            -- Create index for faster creator lookups
            CREATE INDEX IF NOT EXISTS idx_images_creator_username ON images(creator_username);
          END IF;
          -- Add unique constraint if it doesn't exist
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE table_name='images' AND constraint_type='UNIQUE' 
            AND constraint_name='images_source_source_id_key'
          ) THEN
            ALTER TABLE images ADD CONSTRAINT images_source_source_id_key UNIQUE (source, source_id);
          END IF;
        END $$;
        """)

def get_creators() -> List[CreatorResponse]:
    """Get all creators with their details"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                c.username,
                c.phone,
                c.location,
                c.min_price,
                c.max_price,
                c.calendar_url,
                c.profile_picture_local,
                c.instagram_profile_picture,
                c.instagram_bio,
                c.updated_at,
                (
                  SELECT COUNT(*)
                  FROM images i
                  WHERE EXISTS (
                    SELECT 1 FROM unnest(i.hashtags) h
                    WHERE h = '@' || c.username
                  )
                ) AS post_count,
                (
                  SELECT CASE 
                             WHEN i2.media_id IS NOT NULL THEN CONCAT('/api/images/', i2.media_id, '/proxy')
                             ELSE i2.url
                         END AS sample_image
                  FROM images i2
                  WHERE i2.id = c.sample_image_id OR (
                    i2.id != c.sample_image_id AND EXISTS (
                      SELECT 1 FROM unnest(i2.hashtags) h2 WHERE h2 = '@' || c.username
                    )
                  )
                  ORDER BY CASE WHEN i2.id = c.sample_image_id THEN 0 ELSE 1 END, random()
                  LIMIT 1
                ) AS sample_image,
                (
                  SELECT i2.id AS sample_image_id
                  FROM images i2
                  WHERE i2.id = c.sample_image_id OR (
                    i2.id != c.sample_image_id AND EXISTS (
                      SELECT 1 FROM unnest(i2.hashtags) h2 WHERE h2 = '@' || c.username
                    )
                  )
                  ORDER BY CASE WHEN i2.id = c.sample_image_id THEN 0 ELSE 1 END, random()
                  LIMIT 1
                ) AS sample_image_id
            FROM creators c
            ORDER BY c.updated_at DESC
            """
        )
        rows = cur.fetchall()

    creators = []
    for r in rows:
        # Use Instagram profile picture URL directly
        profile_picture_url = r[7]    # instagram_profile_picture
        
        creators.append(CreatorResponse(
            creator_id=r[0],
            username=r[0],
            phone=r[1],
            location=r[2],
            min_price=float(r[3]) if r[3] is not None else None,
            max_price=float(r[4]) if r[4] is not None else None,
            calendar_url=r[5],
            profile_picture=profile_picture_url,
            bio=r[8],
            post_count=int(r[10]) if r[10] is not None else 0,
            sample_image=r[11],
            sample_image_id=str(r[12]) if r[12] else None,
            profile_url=f"https://instagram.com/{r[0]}" if r[0] else None,
        ))
    
    return creators

def get_random_photos(limit: int = 12, keywords: Optional[str] = None) -> List[Dict]:
    """Get random photos, optionally filtered by keywords"""
    with conn.cursor() as cur:
        if keywords:
            # Filter by keywords in caption
            # Generate proxy URL from media_id if available, otherwise use url
            cur.execute("""
                SELECT id, 
                       CASE 
                           WHEN media_id IS NOT NULL THEN CONCAT('/api/images/', media_id, '/proxy')
                           ELSE url
                       END as image_url, 
                       caption
                FROM images
                WHERE caption ILIKE %s
                ORDER BY random()
                LIMIT %s
            """, (f"%{keywords}%", limit))
        else:
            cur.execute("""
                SELECT id,
                       CASE 
                           WHEN media_id IS NOT NULL THEN CONCAT('/api/images/', media_id, '/proxy')
                           ELSE url
                       END as image_url,
                       caption
                FROM images
                ORDER BY random()
                LIMIT %s
            """, (limit,))
        
        rows = cur.fetchall()
    
    return [
        {
            "id": str(r[0]),
            "url": r[1],
            "caption": r[2]
        } for r in rows
    ]

def search_similar_images(embedding, limit: int = 12) -> List[Dict]:
    """Search for similar images using cosine similarity"""
    import numpy as np
    import json
    
    # Convert PyTorch tensor to numpy array
    if hasattr(embedding, 'detach'):
        embedding_np = embedding.detach().cpu().numpy()
    elif hasattr(embedding, 'cpu'):
        embedding_np = embedding.cpu().numpy()
    elif not isinstance(embedding, np.ndarray):
        embedding_np = np.array(embedding)
    else:
        embedding_np = embedding
    
    # Ensure it's 1D
    if len(embedding_np.shape) > 1:
        embedding_np = embedding_np.flatten()
    
    # Normalize the query embedding
    query_norm = np.linalg.norm(embedding_np)
    if query_norm == 0:
        return []
    embedding_np = embedding_np / query_norm
    
    with conn.cursor() as cur:
        # Get all images with embeddings
        cur.execute("""
            SELECT id,
                   CASE 
                       WHEN media_id IS NOT NULL THEN CONCAT('/api/images/', media_id, '/proxy')
                       ELSE url
                   END as image_url,
                   caption,
                   embedding
            FROM images
            WHERE embedding IS NOT NULL
        """)
        rows = cur.fetchall()
    
    # Calculate cosine similarity for each image
    similarities = []
    for row in rows:
        try:
            # Parse JSONB embedding (array of floats)
            emb_json = row[3]
            if isinstance(emb_json, str):
                emb_array = json.loads(emb_json)
            else:
                emb_array = emb_json
            
            # Convert to numpy array and normalize
            emb_np = np.array(emb_array, dtype=np.float32)
            emb_norm = np.linalg.norm(emb_np)
            if emb_norm == 0:
                continue
            emb_np = emb_np / emb_norm
            
            # Calculate cosine similarity
            similarity = float(np.dot(embedding_np, emb_np))
            
            similarities.append({
                "id": str(row[0]),
                "url": row[1],
                "caption": row[2],
                "similarity": similarity
            })
        except Exception as e:
            print(f"Error calculating similarity for image {row[0]}: {e}")
            continue
    
    # Sort by similarity and return top results
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:limit]

def search_similar_images_by_creator(embedding) -> List[Dict]:
    """
    Find the most similar image for EACH creator
    
    Returns a list where each entry contains:
    - creator_username: The creator's username
    - image: The most similar image data for that creator
    - similarity_score: The similarity score (0-1)
    
    Results are sorted by similarity score (highest first)
    """
    import numpy as np
    import json
    
    # Convert PyTorch tensor to numpy array
    if hasattr(embedding, 'detach'):
        embedding_np = embedding.detach().cpu().numpy()
    elif hasattr(embedding, 'cpu'):
        embedding_np = embedding.cpu().numpy()
    elif not isinstance(embedding, np.ndarray):
        embedding_np = np.array(embedding)
    else:
        embedding_np = embedding
    
    # Ensure it's 1D
    if len(embedding_np.shape) > 1:
        embedding_np = embedding_np.flatten()
    
    # Normalize the query embedding
    query_norm = np.linalg.norm(embedding_np)
    if query_norm == 0:
        return []
    embedding_np = embedding_np / query_norm
    
    with conn.cursor() as cur:
        # Get all images with embeddings and creator usernames
        cur.execute("""
            SELECT creator_username,
                   id,
                   media_id,
                   url,
                   caption,
                   width,
                   height,
                   embedding,
                   media_url
            FROM images
            WHERE embedding IS NOT NULL 
              AND creator_username IS NOT NULL
        """)
        rows = cur.fetchall()
    
    # Group by creator and find most similar for each
    creator_best = {}
    for row in rows:
        creator = row[0]
        try:
            # Parse JSONB embedding (array of floats)
            emb_json = row[7]
            if isinstance(emb_json, str):
                emb_array = json.loads(emb_json)
            else:
                emb_array = emb_json
            
            # Convert to numpy array and normalize
            emb_np = np.array(emb_array, dtype=np.float32)
            emb_norm = np.linalg.norm(emb_np)
            if emb_norm == 0:
                continue
            emb_np = emb_np / emb_norm
            
            # Calculate cosine similarity
            similarity = float(np.dot(embedding_np, emb_np))
            
            # Keep the best match for each creator
            if creator not in creator_best or similarity > creator_best[creator]["similarity_score"]:
                creator_best[creator] = {
                    "creator_username": creator,
                    "image": {
                        "id": str(row[1]),
                        "media_id": row[2],
                        "url": row[3],
                        "caption": row[4],
                        "width": row[5],
                        "height": row[6],
                        "media_url": row[8]
                    },
                    "similarity_score": similarity
                }
        except Exception as e:
            print(f"Error calculating similarity for image {row[1]}: {e}")
            continue
    
    results = list(creator_best.values())
    
    # Sort by similarity score (highest first)
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return results

def get_creator_by_user_id(user_id: str) -> Optional[Dict]:
    """Get creator data by user ID"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT username, phone, location, min_price, max_price, calendar_url,
                   instagram_profile_picture, instagram_bio
            FROM creators
            WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
    
    if not row:
        return None
    
    return {
        "username": row[0],
        "phone": row[1],
        "location": row[2],
        "min_price": float(row[3]) if row[3] is not None else None,
        "max_price": float(row[4]) if row[4] is not None else None,
        "calendar_url": row[5],
        "profile_picture": row[6],
        "bio": row[7]
    }

def upsert_creator(user_id: str, username: str, phone: Optional[str] = None,
                   location: Optional[str] = None, min_price: Optional[float] = None,
                   max_price: Optional[float] = None, calendar_url: Optional[str] = None,
                   instagram_data: Optional[Dict] = None):
    """Create or update creator profile"""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO creators (user_id, username, phone, location, min_price, max_price, calendar_url,
                                instagram_profile_picture, instagram_bio, profile_picture_local, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, now())
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                phone = EXCLUDED.phone,
                location = EXCLUDED.location,
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                calendar_url = EXCLUDED.calendar_url,
                instagram_profile_picture = EXCLUDED.instagram_profile_picture,
                instagram_bio = EXCLUDED.instagram_bio,
                profile_picture_local = NULL,
                updated_at = now()
        """, (user_id, username, phone, location, min_price, max_price, calendar_url,
              instagram_data.get("profile_picture_url") if instagram_data else None,
              instagram_data.get("biography") if instagram_data else None))
