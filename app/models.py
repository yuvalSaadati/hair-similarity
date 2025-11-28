from typing import List, Optional
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class CreatorCreate(BaseModel):
    username: str
    phone: Optional[str] = None
    location: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    calendar_url: Optional[str] = None

class CreatorUpdate(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    calendar_url: Optional[str] = None

class ImageUpload(BaseModel):
    file: bytes

class SearchRequest(BaseModel):
    image: bytes

class ImageResponse(BaseModel):
    id: str
    url: str
    local_url: Optional[str] = None
    caption: Optional[str] = None
    similarity: Optional[float] = None
    created_at: Optional[str] = None

class CreatorResponse(BaseModel):
    creator_id: str
    username: str
    phone: Optional[str] = None
    location: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    calendar_url: Optional[str] = None
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    post_count: int = 0
    sample_image: Optional[str] = None
    sample_image_id: Optional[str] = None
    profile_url: Optional[str] = None
