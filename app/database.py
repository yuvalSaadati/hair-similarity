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
            arrival_location TEXT[],
            min_price NUMERIC,
            max_price NUMERIC,
            price_hairstyle_bride NUMERIC,
            price_hairstyle_bridesmaid NUMERIC,
            price_makeup_bride NUMERIC,
            price_makeup_bridesmaid NUMERIC,
            price_hairstyle_makeup_combo NUMERIC,
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
            sample_image_id UUID,
            recent_image TEXT,
            display_image TEXT
        );
        """)
        
        # Add recent_image column if it doesn't exist (for existing databases)
        cur.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'creators' AND column_name = 'recent_image'
                ) THEN
                    ALTER TABLE creators ADD COLUMN recent_image TEXT;
                END IF;
            END $$;
        """)
        
        # Images table - embedding is REQUIRED (NOT NULL) stored as VECTOR(512) using pgvector
        # Check if vector extension exists
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
        has_vector = cur.fetchone()[0]
        
        if not has_vector:
            # Try to create vector extension
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                has_vector = True
            except Exception as e:
                print(f"⚠️  Warning: Could not create vector extension: {e}")
                print("   Falling back to JSONB storage. Install pgvector for better performance.")
                has_vector = False
        
        if has_vector:
            # Use VECTOR type with pgvector
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
                embedding VECTOR(512) NOT NULL,
                caption TEXT,
                media_id TEXT,
                UNIQUE(source, source_id)
            );
            """)
            
            # Create IVFFlat index for fast similarity search (cosine distance)
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_images_embedding 
            ON images USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """)
            
            print("✅ Created images table with VECTOR(512) embedding column (pgvector)")
        else:
            # Fallback to JSONB if pgvector is not available
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
            
            print("✅ Created images table with JSONB embedding column (fallback mode)")
        
        # Reviews/Comments table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            creator_username TEXT NOT NULL REFERENCES creators(username) ON DELETE CASCADE,
            reviewer_name TEXT,
            comment TEXT NOT NULL,
            rating INT CHECK (rating >= 1 AND rating <= 5),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """)
        
        # Create index on creator_username for faster lookups
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reviews_creator_username 
        ON reviews(creator_username);
        """)
        
        print("✅ Created reviews table")
        
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
          -- Add new price columns if they don't exist
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='creators' AND column_name='price_hairstyle_bride'
          ) THEN
            ALTER TABLE creators ADD COLUMN price_hairstyle_bride NUMERIC;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='creators' AND column_name='price_hairstyle_bridesmaid'
          ) THEN
            ALTER TABLE creators ADD COLUMN price_hairstyle_bridesmaid NUMERIC;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='creators' AND column_name='price_makeup_bride'
          ) THEN
            ALTER TABLE creators ADD COLUMN price_makeup_bride NUMERIC;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='creators' AND column_name='price_makeup_bridesmaid'
          ) THEN
            ALTER TABLE creators ADD COLUMN price_makeup_bridesmaid NUMERIC;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='creators' AND column_name='price_hairstyle_makeup_combo'
          ) THEN
            ALTER TABLE creators ADD COLUMN price_hairstyle_makeup_combo NUMERIC;
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='creators' AND column_name='arrival_location'
          ) THEN
            ALTER TABLE creators ADD COLUMN arrival_location TEXT[];
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
                c.arrival_location,
                c.min_price,
                c.max_price,
                c.price_hairstyle_bride,
                c.price_hairstyle_bridesmaid,
                c.price_makeup_bride,
                c.price_makeup_bridesmaid,
                c.price_hairstyle_makeup_combo,
                c.calendar_url,
                c.profile_picture_local,
                c.instagram_profile_picture,
                c.instagram_bio,
                c.recent_image,
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
                  SELECT COUNT(*)
                  FROM reviews r
                  WHERE r.creator_username = c.username
                ) AS review_count,
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
        profile_picture_url = r[13]    # instagram_profile_picture (shifted due to new columns)
        
        # Handle arrival_location as array
        arrival_locations = r[3]
        if arrival_locations is None:
            arrival_locations = []
        elif isinstance(arrival_locations, list):
            arrival_locations = arrival_locations
        elif isinstance(arrival_locations, str):
            arrival_locations = [loc.strip() for loc in arrival_locations.split(',') if loc.strip()]
        else:
            arrival_locations = []
        
        creators.append(CreatorResponse(
            creator_id=r[0],
            username=r[0],
            phone=r[1],
            location=r[2],
            arrival_location=','.join(arrival_locations) if arrival_locations else None,  # Convert array to comma-separated string for API
            min_price=float(r[4]) if r[4] is not None else None,
            max_price=float(r[5]) if r[5] is not None else None,
            price_hairstyle_bride=float(r[6]) if r[6] is not None else None,
            price_hairstyle_bridesmaid=float(r[7]) if r[7] is not None else None,
            price_makeup_bride=float(r[8]) if r[8] is not None else None,
            price_makeup_bridesmaid=float(r[9]) if r[9] is not None else None,
            price_hairstyle_makeup_combo=float(r[10]) if r[10] is not None else None,
            calendar_url=r[11],
            profile_picture=profile_picture_url,
            bio=r[14],
            recent_image=r[15] if r[15] is not None else None,
            post_count=int(r[17]) if r[17] is not None else 0,  # post_count is at index 17 (after updated_at at 16)
            review_count=int(r[18]) if r[18] is not None else 0,  # review_count is at index 18
            sample_image=r[19] if r[19] is not None else None,  # sample_image is at index 19
            sample_image_id=str(r[20]) if r[20] else None,  # sample_image_id is at index 20
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
    """Search for similar images using pgvector cosine distance"""
    import numpy as np
    
    # Convert PyTorch tensor to numpy array
    if hasattr(embedding, 'detach'):
        embedding_np = embedding.detach().cpu().numpy()
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
    
    # Normalize the query embedding
    query_norm = np.linalg.norm(embedding_np)
    if query_norm == 0:
        return []
    embedding_np = embedding_np / query_norm
    
    # Convert to list for pgvector
    embedding_list = embedding_np.tolist()
    
    with conn.cursor() as cur:
        # Check if vector extension is available
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
        has_vector = cur.fetchone()[0]
        
        if has_vector:
            # Use pgvector native cosine distance operator (<=>)
            # 1 - distance gives similarity (distance is 0 for identical, 1 for orthogonal)
            cur.execute("""
                SELECT id,
                       CASE 
                           WHEN media_id IS NOT NULL THEN CONCAT('/api/images/', media_id, '/proxy')
                           ELSE url
                       END as image_url,
                       caption,
                       1 - (embedding <=> %s::vector) as similarity
                FROM images
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (embedding_list, embedding_list, limit))
            
            rows = cur.fetchall()
            
            return [
                {
                    "id": str(row[0]),
                    "url": row[1],
                    "caption": row[2],
                    "similarity": float(row[3])
                }
                for row in rows
            ]
        else:
            # Fallback to manual calculation if pgvector is not available
            import json
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
    Find the most similar image for EACH creator using pgvector
    
    Returns a list where each entry contains:
    - creator_username: The creator's username
    - image: The most similar image data for that creator
    - similarity_score: The similarity score (0-1)
    
    Results are sorted by similarity score (highest first)
    """
    import numpy as np
    
    # Convert PyTorch tensor to numpy array
    if hasattr(embedding, 'detach'):
        embedding_np = embedding.detach().cpu().numpy()
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
    
    # Normalize the query embedding
    query_norm = np.linalg.norm(embedding_np)
    if query_norm == 0:
        return []
    embedding_np = embedding_np / query_norm
    
    # Convert to list for pgvector
    embedding_list = embedding_np.tolist()
    
    with conn.cursor() as cur:
        # Check if vector extension is available
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
        has_vector = cur.fetchone()[0]
        
        if has_vector:
            # Use pgvector native cosine distance operator (<=>)
            # Get the most similar image for each creator using DISTINCT ON
            cur.execute("""
                SELECT DISTINCT ON (creator_username)
                       creator_username,
                       id,
                       media_id,
                       url,
                       caption,
                       width,
                       height,
                       media_url,
                       1 - (embedding <=> %s::vector) as similarity_score
                FROM images
                WHERE embedding IS NOT NULL 
                  AND creator_username IS NOT NULL
                ORDER BY creator_username, embedding <=> %s::vector
            """, (embedding_list, embedding_list))
            
            rows = cur.fetchall()
            
            results = [
                {
                    "creator_username": row[0],
                    "image": {
                        "id": str(row[1]),
                        "media_id": row[2],
                        "url": row[3],
                        "caption": row[4],
                        "width": row[5],
                        "height": row[6],
                        "media_url": row[7]
                    },
                    "similarity_score": float(row[8])
                }
                for row in rows
            ]
            
            # Sort by similarity score (highest first)
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return results
        else:
            # Fallback to manual calculation if pgvector is not available
            import json
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
            SELECT username, phone, location, arrival_location, min_price, max_price, 
                   price_hairstyle_bride, price_hairstyle_bridesmaid, 
                   price_makeup_bride, price_makeup_bridesmaid, price_hairstyle_makeup_combo,
                   calendar_url, instagram_profile_picture, instagram_bio
            FROM creators
            WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
    
    if not row:
        return None
    
    # Handle arrival_location as array - convert to list if it's an array, or parse comma-separated string
    arrival_locations = row[3]
    if arrival_locations is None:
        arrival_locations = []
    elif isinstance(arrival_locations, list):
        arrival_locations = arrival_locations
    elif isinstance(arrival_locations, str):
        arrival_locations = [loc.strip() for loc in arrival_locations.split(',') if loc.strip()]
    else:
        arrival_locations = []
    
    return {
        "username": row[0],
        "phone": row[1],
        "location": row[2],
        "arrival_location": ','.join(arrival_locations) if arrival_locations else None,  # Convert array to comma-separated string for frontend
        "min_price": float(row[4]) if row[4] is not None else None,
        "max_price": float(row[5]) if row[5] is not None else None,
        "price_hairstyle_bride": float(row[6]) if row[6] is not None else None,
        "price_hairstyle_bridesmaid": float(row[7]) if row[7] is not None else None,
        "price_makeup_bride": float(row[8]) if row[8] is not None else None,
        "price_makeup_bridesmaid": float(row[9]) if row[9] is not None else None,
        "price_hairstyle_makeup_combo": float(row[10]) if row[10] is not None else None,
        "calendar_url": row[11],
        "profile_picture": row[12],
        "bio": row[13]
    }

def upsert_creator(user_id: str, username: str, phone: Optional[str] = None,
                   location: Optional[str] = None, arrival_location: Optional[str] = None,
                   min_price: Optional[float] = None,
                   max_price: Optional[float] = None, calendar_url: Optional[str] = None,
                   instagram_data: Optional[Dict] = None,
                   price_hairstyle_bride: Optional[float] = None,
                   price_hairstyle_bridesmaid: Optional[float] = None,
                   price_makeup_bride: Optional[float] = None,
                   price_makeup_bridesmaid: Optional[float] = None,
                   price_hairstyle_makeup_combo: Optional[float] = None,
                   recent_image: Optional[str] = None):
    """Create or update creator profile"""
    # Convert arrival_location string (comma-separated) to array
    arrival_location_array = None
    if arrival_location:
        if isinstance(arrival_location, str):
            arrival_location_array = [loc.strip() for loc in arrival_location.split(',') if loc.strip()]
        elif isinstance(arrival_location, list):
            arrival_location_array = arrival_location
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO creators (user_id, username, phone, location, arrival_location, min_price, max_price, 
                                price_hairstyle_bride, price_hairstyle_bridesmaid, 
                                price_makeup_bride, price_makeup_bridesmaid, price_hairstyle_makeup_combo,
                                calendar_url, instagram_profile_picture, instagram_bio, profile_picture_local, recent_image, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, now())
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                phone = EXCLUDED.phone,
                location = EXCLUDED.location,
                arrival_location = EXCLUDED.arrival_location,
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                price_hairstyle_bride = EXCLUDED.price_hairstyle_bride,
                price_hairstyle_bridesmaid = EXCLUDED.price_hairstyle_bridesmaid,
                price_makeup_bride = EXCLUDED.price_makeup_bride,
                price_makeup_bridesmaid = EXCLUDED.price_makeup_bridesmaid,
                price_hairstyle_makeup_combo = EXCLUDED.price_hairstyle_makeup_combo,
                calendar_url = EXCLUDED.calendar_url,
                instagram_profile_picture = EXCLUDED.instagram_profile_picture,
                instagram_bio = EXCLUDED.instagram_bio,
                profile_picture_local = NULL,
                recent_image = EXCLUDED.recent_image,
                updated_at = now()
        """, (user_id, username, phone, location, arrival_location_array, min_price, max_price, 
              price_hairstyle_bride, price_hairstyle_bridesmaid, 
              price_makeup_bride, price_makeup_bridesmaid, price_hairstyle_makeup_combo,
              calendar_url,
              instagram_data.get("profile_picture_url") if instagram_data else None,
              instagram_data.get("biography") if instagram_data else None,
              recent_image))
