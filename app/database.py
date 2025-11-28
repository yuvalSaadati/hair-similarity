from typing import List, Optional, Dict, Any
from app.db import conn
from app.models import CreatorResponse

def setup_database_schema():
    """Initialize database schema and tables"""
    with conn.cursor() as cur:
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
        
        # Images table
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
            embedding VECTOR(512),
            caption TEXT,
            media_id TEXT,
            UNIQUE(source, source_id)
        );
        """)
        
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
    """Search for similar images using vector similarity"""
    with conn.cursor() as cur:
        # Generate proxy URL from media_id if available, otherwise use url
        cur.execute("""
            SELECT id,
                   CASE 
                       WHEN media_id IS NOT NULL THEN CONCAT('/api/images/', media_id, '/proxy')
                       ELSE url
                   END as image_url,
                   caption,
                   1 - (embedding <=> %s) as similarity
            FROM images
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT %s
        """, (embedding, embedding, limit))
        rows = cur.fetchall()
    
    return [
        {
            "id": str(r[0]),
            "url": r[1],
            "caption": r[2],
            "similarity": float(r[3])
        } for r in rows
    ]

def search_similar_images_by_creator(embedding) -> List[Dict]:
    """
    Find the most similar image for EACH creator
    
    Returns a list where each entry contains:
    - creator_username: The creator's username
    - image: The most similar image data for that creator
    - similarity_score: The similarity score (0-1)
    
    Results are sorted by similarity score (highest first)
    """
    with conn.cursor() as cur:
        # For each creator, find their most similar image
        # Using DISTINCT ON to get one image per creator (the most similar one)
        cur.execute("""
            SELECT DISTINCT ON (creator_username)
                creator_username,
                id,
                media_id,
                CASE 
                    WHEN media_id IS NOT NULL THEN CONCAT('/api/images/', media_id, '/proxy')
                    ELSE url
                END as image_url,
                caption,
                width,
                height,
                1 - (embedding <=> %s) as similarity_score
            FROM images
            WHERE embedding IS NOT NULL 
              AND creator_username IS NOT NULL
            ORDER BY creator_username, embedding <=> %s
        """, (embedding, embedding))
        rows = cur.fetchall()
    
    # Convert to list of dicts
    results = [
        {
            "creator_username": row[0],
            "image": {
                "id": str(row[1]),
                "media_id": row[2],
                "url": row[3],
                "caption": row[4],
                "width": row[5],
                "height": row[6]
            },
            "similarity_score": float(row[7])
        }
        for row in rows
    ]
    
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
