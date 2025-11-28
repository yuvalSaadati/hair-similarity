import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# Instagram API Configuration
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_APP_ID = os.getenv("IG_APP_ID")
IG_APP_SECRET = os.getenv("IG_APP_SECRET")
IG_USER_ID = os.getenv("IG_USER_ID")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
IG_REDIRECT_URI = os.getenv("IG_REDIRECT_URI", "http://localhost:8000/auth/callback")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

# Media Directories
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')
MEDIA_IMAGES_DIR = os.path.join(MEDIA_ROOT, 'images')
MEDIA_AVATARS_DIR = os.path.join(MEDIA_ROOT, 'avatars')
