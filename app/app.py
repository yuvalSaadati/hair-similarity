import io, os, uuid, json
from typing import List, Optional
from dotenv import load_dotenv

import torch
import clip
from PIL import Image
import requests

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pgvector.psycopg import register_vector
from pgvector import Vector
import psycopg

load_dotenv()

# --- Config (env only; never hardcode secrets) ---
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_APP_ID = os.getenv("IG_APP_ID")
IG_APP_SECRET = os.getenv("IG_APP_SECRET")
IG_USER_ID = os.getenv("IG_USER_ID")
import psycopg

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

try:
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    print("Connected successfully!")
except Exception as e:
    print("Connection failed:", e)

# --- DB ---
register_vector(conn)

# --- Model ---
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# --- App ---
app = FastAPI(title="Hairstyle Similarity Search", version="1.0")

# Open CORS for now (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Serve simple frontend
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

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
                     embedding):
    with conn.cursor() as cur:
        # Conflict on (source, source_id) to avoid duplicates from IG/user
        cur.execute(
            """
            INSERT INTO images (id, source, source_id, url, hashtags, width, height, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO NOTHING
            """,
            (uuid.uuid4(), source, source_id, url, hashtags, width, height, Vector(embedding.tolist()))
        )

def fetch_and_embed_image(url: str):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content))
    emb = image_to_embedding(img)
    return img, emb, img.size

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
                              limit_per_user: int = 20):
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
                        img, emb, (w, h) = fetch_and_embed_image(url)
                        insert_image_row("instagram", im["id"], im.get("permalink", url),
                                         [f"@{uname}"], w, h, emb)
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
                    insert_image_row("instagram", m["id"], m.get("permalink", url),
                                     [f"#{tag}"], w, h, emb)
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

@app.post("/ingest/upload")
async def ingest_user_upload(file: UploadFile = File(...), hashtags_json: Optional[str] = None):
    try:
        img = Image.open(io.BytesIO(await file.read()))
    except Exception:
        raise HTTPException(400, "Invalid image")

    tags = []
    if hashtags_json:
        try:
            tags = json.loads(hashtags_json)
        except Exception:
            pass

    emb = image_to_embedding(img)
    insert_image_row("user", str(uuid.uuid4()), "uploaded://local", tags, img.width, img.height, emb)
    return {"status": "ok"}
