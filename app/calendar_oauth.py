# calendar_oauth.py
import os, json, datetime as dt
from urllib.parse import urlencode

import httpx
from authlib.integrations.starlette_client import OAuth
from dateutil.tz import UTC
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from psycopg.rows import dict_row
from pytz import timezone

from app.db import conn
router = APIRouter()

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REDIRECT_BASE = os.environ.get("OAUTH_REDIRECT_BASE", "http://localhost:8000")
REDIRECT_URI = f"{REDIRECT_BASE}/oauth/google/callback"

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        # ask for offline access so we receive a refresh_token
        "scope": "openid email https://www.googleapis.com/auth/calendar.readonly",
        "prompt": "consent",       # ensure refresh_token on first connect
        "access_type": "offline",
    },
)

# ---- 1) Start OAuth
@router.get("/oauth/google/start")
async def google_start(request: Request, creator_id: str):
    redirect_uri = REDIRECT_URI
    # pass creator_id in 'state' so we know who to attach tokens to
    return await oauth.google.authorize_redirect(request, redirect_uri, state=creator_id)

# ---- 2) OAuth callback
@router.get("/oauth/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)  # exchanges code
    if not token:
        raise HTTPException(400, "No token returned from Google")

    # token contains: access_token, expires_at, refresh_token (on first consent), id_token, ...
    # get the user's email to display/store
    async with httpx.AsyncClient() as client:
        # 'userinfo' is in OIDC discovery
        resp = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            timeout=15,
        )
    resp.raise_for_status()
    userinfo = resp.json()
    email = userinfo.get("email")

    # which creator was connecting?
    state = request.query_params.get("state")
    if not state:
        raise HTTPException(400, "Missing state")
    creator_id = state

    # store tokens on the creator
    expires_at = dt.datetime.fromtimestamp(token["expires_at"], tz=UTC)
    refresh_token = token.get("refresh_token")  # may be None on re-consent if Google didn't send it
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE creators
               SET calendar_provider = 'google',
                   oauth_account_email = %s,
                   google_access_token = %s,
                   google_token_expiry = %s,
                   google_refresh_token = COALESCE(%s, google_refresh_token),
                   updated_at = now()
             WHERE id = %s
            """,
            (email, token["access_token"], expires_at, refresh_token, creator_id),
        )
    return RedirectResponse(url=f"/creator/{creator_id}?connected=google")

# ---- helper: ensure valid access token (refresh when needed)
async def google_access_token_for_creator(creator_id: str) -> str:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT google_access_token, google_token_expiry, google_refresh_token
                 FROM creators WHERE id=%s""",
            (creator_id,),
        )
        row = cur.fetchone()
    if not row or not row["google_refresh_token"]:
        raise HTTPException(400, "Creator has not connected Google Calendar")

    # if access token exists and is still valid for >60s, reuse it
    now = dt.datetime.now(tz=UTC)
    if row["google_access_token"] and row["google_token_expiry"] and row["google_token_expiry"] > now + dt.timedelta(seconds=60):
        return row["google_access_token"]

    # refresh
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": row["google_refresh_token"],
        }
        resp = await client.post("https://oauth2.googleapis.com/token", data=data, timeout=15)
    if resp.status_code != 200:
        raise HTTPException(400, f"Failed to refresh token: {resp.text}")
    tok = resp.json()
    access_token = tok["access_token"]
    expires_in = int(tok.get("expires_in", 3600))
    expires_at = dt.datetime.now(tz=UTC) + dt.timedelta(seconds=expires_in)

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE creators SET google_access_token=%s, google_token_expiry=%s, updated_at=now() WHERE id=%s",
            (access_token, expires_at, creator_id),
        )
    return access_token

# ---- 3) Busy slots via Google FreeBusy
@router.get("/api/creators/{creator_id}/busy")
async def creator_busy(creator_id: str, start: str, end: str):
    """
    Returns busy intervals between ISO datetimes `start` and `end` (UTC or with timezone).
    Example: /api/creators/UUID/busy?start=2025-09-10T00:00:00Z&end=2025-09-17T00:00:00Z
    """
    access_token = await google_access_token_for_creator(creator_id)

    payload = {
        "timeMin": start,
        "timeMax": end,
        "items": [{"id": "primary"}],  # or a specific calendar ID
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://www.googleapis.com/calendar/v3/freeBusy",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
            timeout=20,
        )
    r.raise_for_status()
    data = r.json()
    # structure: data["calendars"]["primary"]["busy"] -> [{start,end}, ...]
    busy = data.get("calendars", {}).get("primary", {}).get("busy", [])
    return {"creator_id": creator_id, "busy": busy}

# ---- 4) Availability (free slots), combining busy + working hours + slot length
@router.get("/api/creators/{creator_id}/availability")
async def creator_availability(creator_id: str, start_date: str, end_date: str, slot_minutes: int = 60):
    """
    Returns bookable slots (local) by subtracting busy times from creator working hours.
    Dates are yyyy-mm-dd.
    """
    # fetch creator settings
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT timezone FROM creators WHERE id=%s", (creator_id,))
        row = cur.fetchone()
    tzname = (row and row["timezone"]) or "Asia/Jerusalem"
    tz = timezone(tzname)

    # day windows (customize to your UI)
    work = {
        "mon": ["09:00-18:00"], "tue": ["09:00-18:00"], "wed": ["09:00-18:00"],
        "thu": ["09:00-18:00"], "fri": ["09:00-14:00"], "sat": [], "sun": []
    }

    # get busy in UTC for the full range
    start_utc = f"{start_date}T00:00:00Z"
    end_utc = f"{end_date}T23:59:59Z"
    busy_resp = await creator_busy(creator_id, start_utc, end_utc)
    busy = [
        (dt.datetime.fromisoformat(b["start"].replace("Z","+00:00")),
         dt.datetime.fromisoformat(b["end"].replace("Z","+00:00")))
        for b in busy_resp["busy"]
    ]

    slots = []
    d0 = dt.date.fromisoformat(start_date)
    d1 = dt.date.fromisoformat(end_date)
    delta = dt.timedelta(minutes=slot_minutes)
    day = d0
    while day <= d1:
        key = ["mon","tue","wed","thu","fri","sat","sun"][day.weekday()]
        for rng in work.get(key, []):
            t1s, t2s = rng.split("-")
            start_local = tz.localize(dt.datetime.combine(day, dt.time.fromisoformat(t1s))).astimezone(UTC)
            end_local   = tz.localize(dt.datetime.combine(day, dt.time.fromisoformat(t2s))).astimezone(UTC)
            t = start_local
            while t + delta <= end_local:
                conflict = any(not (t+delta <= b0 or t >= b1) for b0, b1 in busy)
                if not conflict:
                    slots.append({
                        "start": t.astimezone(tz).isoformat(timespec="minutes"),
                        "end":   (t+delta).astimezone(tz).isoformat(timespec="minutes"),
                    })
                t += delta
        day += dt.timedelta(days=1)

    return {"creator_id": creator_id, "slots": slots}
