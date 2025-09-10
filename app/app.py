import io, os, uuid, json, secrets
from typing import List, Optional
from dotenv import load_dotenv

import torch
import clip
from PIL import Image
import requests

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pgvector.psycopg import register_vector
from pgvector import Vector
import psycopg
from app.calendar_oauth import router as cal_router

load_dotenv()

# --- Config (env only; never hardcode secrets) ---
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_APP_ID = os.getenv("IG_APP_ID")
IG_APP_SECRET = os.getenv("IG_APP_SECRET")
IG_USER_ID = os.getenv("IG_USER_ID")

# OAuth config
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
IG_REDIRECT_URI = os.getenv("IG_REDIRECT_URI", "http://localhost:8000/auth/callback")
import psycopg


from app.db import conn
from pgvector.psycopg import register_vector

# --- DB ---
register_vector(conn)

# --- Utils ---

# Creator profiles table (contact/pricing/calendar)
with conn.cursor() as cur:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS creators (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
        calendar_provider TEXT,        
        oauth_account_email TEXT,
        timezone TEXT DEFAULT 'Asia/Jerusalem',
        google_refresh_token TEXT,
        google_access_token TEXT,
        google_token_expiry TIMESTAMPTZ
    );
    """)
    
    # Ensure caption column on images exists
    cur.execute("""
    DO $$ BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='images' AND column_name='caption'
      ) THEN
        ALTER TABLE images ADD COLUMN caption TEXT;
      END IF;
    END $$;
    """)

# --- Model ---
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# --- App ---
app = FastAPI(title="Hairstyle Similarity Search", version="1.0")
app.include_router(cal_router)

# Open CORS for now (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Serve simple frontend (moved to end to avoid intercepting API routes)

# ---------- Utils ----------
def image_to_embedding(img: Image.Image):
    img = img.convert("RGB")
    tensor = preprocess(img).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(tensor)
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.squeeze(0).cpu().numpy()  # 512-d

def insert_image_row(source: str, source_id: Optional[str], url: str,
                     hashtags: List[str], width: Optional[int], height: Optional[int],
                     embedding, caption: Optional[str] = None):
    with conn.cursor() as cur:
        # Conflict on (source, source_id) to avoid duplicates from IG/user
        cur.execute(
            """
            INSERT INTO images (id, source, source_id, url, hashtags, width, height, embedding, caption)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO NOTHING
            """,
            (uuid.uuid4(), source, source_id, url, hashtags, width, height, Vector(embedding.tolist()), caption)
        )

def fetch_and_embed_image(url: str):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content))
    emb = image_to_embedding(img)
    return img, emb, img.size

# ---------- Caption Filtering ----------
def is_hair_related_caption(caption: str) -> bool:
    """Check if caption contains any hair-related keywords"""
    if not caption:
        return False
    
    # Define hair-related keywords (English and Hebrew)
    hair_keywords = [
        # English keywords
        "hair", "updo", "half-up", "ponytail", "bun", "braid", "braids", 
        "waves", "curls", "curly", "straight", "sleek", "bob", "lob", 
        "pixie", "shag", "layers", "fringe", "bangs", "wolf", "cut", "fade", 
        "skin", "wedding", "bridal", "bride",
        # Hebrew keywords
        "שיער", "תסרוקת", "פן", "עיצוב", "מעצב", "אסוף", "חצי", "קוקו", 
        "קוקס", "צמה", "צמות", "גלים", "תלתלים", "חלק", "כלה", "מסרקת","כלות","ערב"
    ]
    
    # Split caption into words (handle punctuation and whitespace)
    import re
    words = re.findall(r'\b\w+\b', caption.lower())
    
    # Check if any word matches our keywords
    return any(word in hair_keywords for word in words)

# ---------- Instagram Hashtag Ingest ----------
def ig_get_hashtag_id(hashtag: str):
    resp = requests.get(
        "https://graph.facebook.com/v21.0/ig_hashtag_search",
        params={"user_id": IG_USER_ID, "q": hashtag, "access_token": IG_ACCESS_TOKEN},
        timeout=20
    ).json()
    data = resp.get("data", [])
    return data[0]["id"] if data else None

def ig_get_recent_media_by_hashtag(hashtag_id: str, limit: int = 30):
    fields = "id,media_type,media_url,permalink,caption"
    resp = requests.get(
        f"https://graph.facebook.com/v21.0/{hashtag_id}/recent_media",
        params={"user_id": IG_USER_ID, "fields": fields, "access_token": IG_ACCESS_TOKEN, "limit": limit},
        timeout=30
    ).json()
    return resp.get("data", [])

# Business Discovery: fetch creator profile info
def ig_get_creator_profile(username: str):
    """Get Instagram creator profile information including profile picture"""
    try:
        fields = f"business_discovery.username({username}){{profile_picture_url,biography}}"
        resp = requests.get(
            f"https://graph.facebook.com/v21.0/{IG_USER_ID}",
            params={"fields": fields, "access_token": IG_ACCESS_TOKEN},
            timeout=30,
        ).json()
        bd = resp.get("business_discovery")
        if bd:
            return {
                "profile_picture_url": bd.get("profile_picture_url"),
                "biography": bd.get("biography", "")
            }
    except Exception as e:
        print(f"Failed to fetch profile for {username}: {e}")
    return {"profile_picture_url": None, "biography": ""}

# Business Discovery: fetch recent media by creator username
def ig_get_recent_media_by_creator(username: str, limit: int = 30):
    # See https://developers.facebook.com/docs/instagram-api/reference/ig-user/business_discovery
    # Ask for media and, when available, expand carousel children inline
    fields = (
        f"business_discovery.username({username})"
        "{media.limit(" + str(limit) + ")"
        "{id,media_type,media_url,permalink,caption,children{media_type,media_url,permalink,id}}}"
    )
    resp = requests.get(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}",
        params={"fields": fields, "access_token": IG_ACCESS_TOKEN},
        timeout=30,
    ).json()
    bd = resp.get("business_discovery") or {}
    media = (bd.get("media") or {}).get("data", [])
    return media

# Expand a media item to one or more image items (handles CAROUSEL_ALBUM)
def ig_expand_media_to_images(media_item):
    mtype = media_item.get("media_type")
    if mtype == "IMAGE":
        return [media_item]
    if mtype == "CAROUSEL_ALBUM":
        mid = media_item.get("id")
        try:
            resp = requests.get(
                f"https://graph.facebook.com/v21.0/{mid}/children",
                params={
                    "fields": "id,media_type,media_url,permalink,caption",
                    "access_token": IG_ACCESS_TOKEN,
                },
                timeout=30,
            ).json()
            children = resp.get("data", [])
            return [c for c in children if c.get("media_type") == "IMAGE"]
        except Exception:
            return []
    return []

@app.post("/ingest/instagram/creators")
def ingest_instagram_creators(usernames: List[str] = Query(..., description="creator usernames"),
                              limit_per_user: int = 100):
    if not (IG_ACCESS_TOKEN and IG_USER_ID):
        raise HTTPException(500, "Instagram credentials not configured")

    added = 0
    skipped = 0
    errors = []

    for uname in usernames:
        try:
            media = ig_get_recent_media_by_creator(uname, limit=limit_per_user)
            for m in media:
                # Prefer children returned inline from Business Discovery when present
                children = (m.get("children") or {}).get("data") if isinstance(m.get("children"), dict) else None
                if children:
                    images = [c for c in children if c.get("media_type") == "IMAGE"]
                else:
                    images = ig_expand_media_to_images(m)
                for im in images:
                    url = im["media_url"]
                    try:
                        caption = (m.get("caption") or im.get("caption") or "")
                        
                        # Only process images with hair-related captions
                        if not is_hair_related_caption(caption):
                            skipped += 1
                            continue
                            
                        img, emb, (w, h) = fetch_and_embed_image(url)
                        insert_image_row("instagram", im["id"], im.get("permalink", url),
                                         [f"@{uname}"], w, h, emb, caption=caption)
                        added += 1
                    except Exception as e:
                        skipped += 1
                        errors.append(str(e))
        except Exception as e:
            errors.append(f"{uname}: {e}")

    return {"status": "ok", "added": added, "skipped": skipped, "errors": errors[:5]}

@app.post("/ingest/instagram/hashtags")
def ingest_instagram_hashtags(hashtags: List[str] = Query(..., description="hashtags without #"),
                              limit_per_tag: int = 20):
    if not (IG_ACCESS_TOKEN and IG_USER_ID):
        raise HTTPException(500, "Instagram credentials not configured")

    added = 0
    skipped = 0
    errors = []

    for tag in hashtags:
        try:
            hid = ig_get_hashtag_id(tag)
            if not hid:
                continue
            media = ig_get_recent_media_by_hashtag(hid, limit=limit_per_tag)
            for m in media:
                if m.get("media_type") != "IMAGE":
                    continue
                url = m["media_url"]
                try:
                    img, emb, (w, h) = fetch_and_embed_image(url)
                    caption = m.get("caption", "")
                    insert_image_row("instagram", m["id"], m.get("permalink", url),
                                     [f"#{tag}"], w, h, emb, caption=caption)
                    added += 1
                except Exception as e:
                    skipped += 1
                    errors.append(str(e))
        except Exception as e:
            errors.append(f"{tag}: {e}")

    return {"status": "ok", "added": added, "skipped": skipped, "errors": errors[:5]}

# ---------- Upload & Search ----------
@app.post("/search/upload")
async def search_by_upload(file: UploadFile = File(...), top_k: int = 12):
    try:
        img = Image.open(io.BytesIO(await file.read()))
    except Exception:
        raise HTTPException(400, "Invalid image")

    query_emb = image_to_embedding(img)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, source, source_id, url, hashtags, width, height,
                   1 - (embedding <#> %s) AS cosine_similarity
            FROM images
            ORDER BY embedding <#> %s
            LIMIT %s
            """,
            (Vector(query_emb.tolist()), Vector(query_emb.tolist()), top_k)
        )
        rows = cur.fetchall()

    return {"matches": [
        {
            "id": str(r[0]),
            "source": r[1],
            "source_id": r[2],
            "url": r[3],
            "hashtags": r[4],
            "width": r[5],
            "height": r[6],
            "similarity": float(r[7])
        } for r in rows
    ]}

# @app.post("/ingest/upload")
# async def ingest_user_upload(file: UploadFile = File(...), hashtags_json: Optional[str] = None):
#     try:
#         img = Image.open(io.BytesIO(await file.read()))
#     except Exception:
#         raise HTTPException(400, "Invalid image")

#     tags = []
#     if hashtags_json:
#         try:
#             tags = json.loads(hashtags_json)
#         except Exception:
#             pass

#     emb = image_to_embedding(img)
#     insert_image_row("user", str(uuid.uuid4()), "uploaded://local", tags, img.width, img.height, emb, caption=None)
#     return {"status": "ok"}

# ---------- Random Photos & Creator Management ----------
@app.get("/api/random-photos")
def get_random_photos(limit: int = 12, keywords: Optional[str] = None):
    """Get random photos from the dataset"""
    with conn.cursor() as cur:
        if keywords:
            tokens = [k.strip() for k in keywords.split(',') if k.strip()]
            # Simple ILIKE match against caption
            where = " OR ".join(["caption ILIKE %s" for _ in tokens])
            params = [f"%{t}%" for t in tokens] + [limit]
            cur.execute(f"""
                SELECT id, source, source_id, url, hashtags, width, height, created_at
                FROM images
                WHERE {where}
                ORDER BY RANDOM()
                LIMIT %s
            """, params)
        else:
            cur.execute("""
                SELECT id, source, source_id, url, hashtags, width, height, created_at
                FROM images
                ORDER BY RANDOM()
                LIMIT %s
            """, (limit,))
        rows = cur.fetchall()
    
    return {"photos": [
        {
            "id": str(r[0]),
            "source": r[1],
            "source_id": r[2],
            "url": r[3],
            "hashtags": r[4],
            "width": r[5],
            "height": r[6],
            "created_at": r[7].isoformat() if r[7] else None
        } for r in rows
    ]}

@app.get("/api/creators")
def get_creators():
    """Return creators from the creators table with their profile details.

    Additionally returns a lightweight post_count derived from images that mention
    the creator as an @username in hashtags (best-effort, optional).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 
                c.username,
                c.phone,
                c.location,
                c.min_price,
                c.max_price,
                c.calendar_url,
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
                ) AS post_count
            FROM creators c
            ORDER BY c.updated_at DESC
            """
        )
        rows = cur.fetchall()

    creators = []
    for r in rows:
        username = r[0]
        creators.append({
            "creator_id": username,
            "username": username,
            "phone": r[1],
            "location": r[2],
            "min_price": float(r[3]) if r[3] is not None else None,
            "max_price": float(r[4]) if r[4] is not None else None,
            "calendar_url": r[5],
            "profile_picture": r[6],
            "bio": r[7],
            "updated_at": r[8].isoformat() if r[8] else None,
            "post_count": int(r[9]) if r[9] is not None else 0,
            "profile_url": f"https://instagram.com/{username}" if username else None,
        })

    return {"creators": creators}

@app.post("/api/creators")
def upsert_creator(username: str = Query(...), phone: Optional[str] = None,
                   location: Optional[str] = None,
                   min_price: Optional[float] = None,
                   max_price: Optional[float] = None,
                   calendar_url: Optional[str] = None,
                   ingest_limit: int = Query(100, description="posts to fetch after save"),
                   background_tasks: BackgroundTasks = None):
    
    # Fetch Instagram profile information
    profile_data = {"profile_picture_url": None, "biography": ""}
    if IG_ACCESS_TOKEN and IG_USER_ID:
        profile_data = ig_get_creator_profile(username)
    
    # Check if bio or username contains hair-related keywords
    bio = profile_data.get("biography", "")
    username_lower = username.lower()
    
    # Check for professional terms in bio or username
    professional_terms = [
        "artist", "artists", "hairstyles", "hairstylist", "hairstylists","hair"
        "מעצב", "מעצבת", "מעצב שיער", "מעצבת שיער", "מסרקת", "מסרקים"
    ]
    
    has_professional_term = any(term.lower() in bio.lower() or term.lower() in username_lower 
                               for term in professional_terms)
    
    has_hair_keywords = is_hair_related_caption(bio) or is_hair_related_caption(username)
    
    if not (has_hair_keywords or has_professional_term):
        return {
            "status": "rejected", 
            "reason": "Bio and username do not contain hair-related keywords or professional terms",
            "bio": bio,
            "username": username
        }
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO creators (username, phone, location, min_price, max_price, calendar_url, 
                                instagram_profile_picture, instagram_bio, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (username) DO UPDATE SET
                phone = EXCLUDED.phone,
                location = EXCLUDED.location,
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                calendar_url = EXCLUDED.calendar_url,
                instagram_profile_picture = EXCLUDED.instagram_profile_picture,
                instagram_bio = EXCLUDED.instagram_bio,
                updated_at = now()
        """, (username, phone, location, min_price, max_price, calendar_url, 
              profile_data["profile_picture_url"], profile_data["biography"]))
    try:
        if background_tasks is not None:
            background_tasks.add_task(ingest_instagram_creators, [username], ingest_limit)
    except Exception as e:
        print(f"Failed to schedule ingest for {username}: {e}")
    return {"status": "ok", "scheduled_ingest_for": username, "limit": ingest_limit}

# ---------- Hashtag Search ----------
@app.get("/search/hashtags")
def search_by_hashtags(hashtags: List[str] = Query(..., description="hashtags to search for"),
                      top_k: int = 12):
    """Search images by hashtags"""
    with conn.cursor() as cur:
        # Search for images containing any of the hashtags
        hashtag_conditions = " OR ".join(["%s = ANY(hashtags)" for _ in hashtags])
        cur.execute(f"""
            SELECT id, source, source_id, url, hashtags, width, height, created_at
            FROM images
            WHERE {hashtag_conditions}
            ORDER BY created_at DESC
            LIMIT %s
        """, hashtags + [top_k])
        rows = cur.fetchall()
    
    return {"matches": [
        {
            "id": str(r[0]),
            "source": r[1],
            "source_id": r[2],
            "url": r[3],
            "hashtags": r[4],
            "width": r[5],
            "height": r[6],
            "created_at": r[7].isoformat() if r[7] else None
        } for r in rows
    ]}

# Serve simple frontend (mounted at the end to avoid intercepting API routes)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
