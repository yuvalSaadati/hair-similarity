# Hair Similarity Platform

A web application for discovering hair stylists and makeup artists based on image similarity. Users can upload a reference image to find creators with similar styles, filter by location and price, and view detailed creator profiles with reviews.

## Features

### 🔍 Image-Based Search
- Upload an image to find similar hairstyles and makeup looks
- Uses CLIP (Contrastive Language-Image Pre-Training) for semantic image similarity
- Real-time similarity scoring and ranking

### 👥 Creator Profiles
- Instagram integration for creator profiles
- Display creator information: bio, location, prices, contact details
- Multiple price fields:
  - Bride's hairstyle price
  - Bridesmaid's hairstyle price
  - Bride's makeup price
  - Bridesmaid's makeup price
  - Hairstyle + makeup combo price

### 📍 Location-Based Filtering
- Filter creators by departure location (where they're based)
- Filter by arrival locations (where they can travel to)
- Multi-select location filtering
- Hebrew location display

### 💰 Price Filtering
- Dynamic price display (only shows non-zero prices)
- Price range slider for filtering
- Prices displayed in Israeli Shekels (₪)

### ⭐ Reviews System
- View reviews for each creator
- Add reviews with ratings (1-5 stars)
- Review count displayed on creator cards

### 📅 Calendar Integration
- Google Calendar OAuth integration
- Calendar URL management for creators

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Database with JSONB for embeddings
- **CLIP (OpenAI)** - Image similarity model
- **PyTorch** - Deep learning framework
- **psycopg** - PostgreSQL adapter

### Frontend
- **Vanilla JavaScript** (ES6 modules)
- **CSS3** with responsive design
- **HTML5**

### Infrastructure
- **Docker** & **Docker Compose** - Containerization
- **pgvector** - Vector similarity search (optional)

## Prerequisites

- Python 3.9+
- PostgreSQL 12+ (or use Docker)
- Docker & Docker Compose (optional, for containerized setup)
- Instagram Business Account with Facebook Page connection
- Facebook App with Instagram Basic Display API access

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd hair-similarity
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres

# Instagram API Configuration
IG_ACCESS_TOKEN=your_instagram_access_token
IG_APP_ID=your_facebook_app_id
IG_APP_SECRET=your_facebook_app_secret
IG_USER_ID=your_instagram_business_account_id

# JWT Configuration (auto-generated if not provided)
JWT_SECRET=your_jwt_secret_key

# OAuth Configuration
IG_REDIRECT_URI=http://localhost:8000/auth/callback
```

### 3. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r app/requirements.txt
```

### 4. Set Up Database

#### Option A: Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port `5433`
- Adminer (database admin UI) on port `8080`
- API server on port `8000`

#### Option B: Local PostgreSQL

1. Install PostgreSQL locally
2. Create a database:
```sql
CREATE DATABASE postgres;
```
3. Run the application - the schema will be created automatically

### 5. Run the Application

```bash
# From the root directory
cd app
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or using Docker Compose:
```bash
docker-compose up
```

The application will be available at `http://localhost:8000`

## Instagram API Setup

### Getting an Access Token

1. **Create a Facebook App**
   - Go to [Facebook Developers](https://developers.facebook.com/)
   - Create a new app
   - Add "Instagram Basic Display" product

2. **Connect Instagram Account**
   - Your Instagram account must be a Business or Creator account
   - Connect it to a Facebook Page
   - Link the Page to your Facebook App

3. **Get Access Token**
   - Use the Graph API Explorer or your app's OAuth flow
   - Required permissions:
     - `instagram_basic`
     - `pages_read_engagement`
     - `business_discovery`
   - Exchange short-lived token for long-lived token (valid ~60 days)

4. **Get User ID**
   - Your Instagram Business Account ID (found in Facebook Page settings)

See `access token.ipynb` for detailed token generation instructions.

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /api/me/creator` - Get current user's creator profile
- `PUT /api/me/creator` - Update creator profile

### Creators
- `GET /api/creators` - Get all creators
- `GET /api/creators/with-display-images` - Get creators with display images
- `GET /api/creators/{username}/images` - Get creator's images

### Search
- `POST /search/upload` - Search by uploaded image
- `POST /search/upload/by-creator` - Search by image, grouped by creator
- `GET /search/random-photos` - Get random photos

### Reviews
- `GET /api/reviews/{creator_username}` - Get reviews for a creator
- `POST /api/reviews` - Create a new review (requires authentication)

### Display
- `GET /api/display/creator/{username}/image` - Get creator display image

## Project Structure

```
hair-similarity/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration and environment variables
│   ├── database.py             # Database schema and queries
│   ├── db.py                   # Database connection
│   ├── auth.py                 # Authentication utilities
│   ├── models.py               # Pydantic models
│   ├── instagram.py            # Instagram API integration
│   ├── image_processing.py     # CLIP embedding generation
│   ├── image_proxy.py          # Image proxy for Instagram
│   ├── image_display_manager.py # Image display logic
│   ├── calendar_oauth.py       # Google Calendar OAuth
│   ├── routers/                # API route handlers
│   │   ├── auth.py
│   │   ├── creators.py
│   │   ├── search.py
│   │   ├── me.py
│   │   ├── display.py
│   │   └── reviews.py
│   ├── static/                 # Frontend files
│   │   ├── index.html
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       ├── main.js
│   │       ├── api.js
│   │       ├── auth.js
│   │       ├── creators.js
│   │       ├── filters.js
│   │       ├── image-display.js
│   │       ├── ui.js
│   │       └── utils.js
│   └── requirements.txt
├── db/
│   └── init.sql                # Database initialization script
├── docker-compose.yml          # Docker Compose configuration
├── .env                        # Environment variables (create this)
└── README.md                   # This file
```

## Usage

### For Users

1. **Browse Creators**: View all available creators on the main page
2. **Filter**: Use filters to narrow down by location and price range
3. **Search by Image**: Upload an image to find creators with similar styles
4. **View Details**: Click on a creator card to see their Instagram profile
5. **Contact**: Use WhatsApp button to contact creators directly
6. **Leave Reviews**: Add reviews and ratings for creators

### For Creators

1. **Sign Up**: Register an account
2. **Create Profile**: Add your Instagram username, phone, location, and prices
3. **Manage Images**: Select your best work as display images
4. **View Reviews**: See what clients say about your work

## Troubleshooting

### Instagram API Errors

**403 Forbidden**
- Token expired - generate a new long-lived token
- Missing permissions - ensure all required scopes are granted
- Account not connected - verify Instagram is linked to Facebook Page

**Rate Limit (Error Code 4)**
- Too many requests - wait and retry
- Implement caching to reduce API calls
- Consider batch processing

### Database Issues

**Connection Errors**
- Verify PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Ensure database exists

**Schema Errors**
- Run `setup_database_schema()` manually
- Check database logs for specific errors

### Image Processing

**CLIP Model Loading**
- First run downloads the model (~350MB)
- Ensure sufficient disk space
- Check internet connection for model download

**Embedding Generation**
- Requires sufficient RAM (recommended 4GB+)
- GPU optional but recommended for faster processing

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project follows PEP 8 Python style guidelines.

### Database Migrations

Schema changes are handled automatically via `setup_database_schema()` which uses `ALTER TABLE` statements wrapped in `DO $$ BEGIN ... END $$;` blocks for safe schema evolution.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please open an issue on the repository.
