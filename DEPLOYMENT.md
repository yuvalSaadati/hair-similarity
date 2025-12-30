# Deployment Guide

This guide explains how to deploy the Hair Similarity Platform to make it accessible via a public URL.

## Option 1: Render (Recommended - Free Tier Available)

### Steps:

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/hair-similarity.git
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [render.com](https://render.com) and sign up
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: hair-similarity-api
     - **Environment**: Python 3
     - **Build Command**: `pip install -r app/requirements.txt`
     - **Start Command**: `cd app && uvicorn main:app --host 0.0.0.0 --port $PORT`
     - **Plan**: Free (or paid for better performance)

3. **Add PostgreSQL Database**
   - Click "New +" → "PostgreSQL"
   - Name: `hair-similarity-db`
   - Plan: Free
   - Copy the **Internal Database URL** (for Render services) or **External Database URL**

4. **Set Environment Variables**
   In your Web Service settings, add:
   ```
   DATABASE_URL=<from PostgreSQL service>
   IG_ACCESS_TOKEN=<your_token>
   IG_APP_ID=<your_app_id>
   IG_APP_SECRET=<your_app_secret>
   IG_USER_ID=<your_user_id>
   JWT_SECRET=<generate_random_string>
   PORT=8000
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - Your app will be available at: `https://hair-similarity-api.onrender.com`

**Note**: Free tier services spin down after 15 minutes of inactivity. First request may take 30-60 seconds.

---

## Option 2: Railway (Free Tier Available)

### Steps:

1. **Push to GitHub** (same as above)

2. **Deploy on Railway**
   - Go to [railway.app](https://railway.app) and sign up
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

3. **Add PostgreSQL**
   - Click "+ New" → "Database" → "Add PostgreSQL"
   - Railway automatically provides `DATABASE_URL` environment variable

4. **Set Environment Variables**
   - Go to your service → "Variables"
   - Add:
     ```
     IG_ACCESS_TOKEN=<your_token>
     IG_APP_ID=<your_app_id>
     IG_APP_SECRET=<your_app_secret>
     IG_USER_ID=<your_user_id>
     JWT_SECRET=<generate_random_string>
     ```

5. **Configure Build**
   - Railway auto-detects Python projects
   - If needed, set:
     - **Build Command**: `pip install -r app/requirements.txt`
     - **Start Command**: `cd app && uvicorn main:app --host 0.0.0.0 --port $PORT`

6. **Deploy**
   - Railway auto-deploys on git push
   - Your app will be available at: `https://your-project-name.up.railway.app`

---

## Option 3: Fly.io (Free Tier Available)

### Steps:

1. **Install Fly CLI**
   ```bash
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login and Initialize**
   ```bash
   fly auth login
   fly launch
   ```

3. **Configure fly.toml** (auto-generated, but verify):
   ```toml
   app = "your-app-name"
   primary_region = "iad"  # Choose closest region
   
   [build]
   
   [env]
     PORT = "8000"
   
   [[services]]
     internal_port = 8000
     protocol = "tcp"
   
     [[services.ports]]
       port = 80
       handlers = ["http"]
     [[services.ports]]
       port = 443
       handlers = ["tls", "http"]
   ```

4. **Add PostgreSQL**
   ```bash
   fly postgres create --name hair-similarity-db
   fly postgres attach --app your-app-name hair-similarity-db
   ```

5. **Set Secrets**
   ```bash
   fly secrets set IG_ACCESS_TOKEN=<your_token>
   fly secrets set IG_APP_ID=<your_app_id>
   fly secrets set IG_APP_SECRET=<your_app_secret>
   fly secrets set IG_USER_ID=<your_user_id>
   fly secrets set JWT_SECRET=<generate_random_string>
   ```

6. **Deploy**
   ```bash
   fly deploy
   ```

---

## Option 4: Docker + Any Cloud Provider

### Using Docker Compose on a VPS:

1. **Get a VPS** (DigitalOcean, Linode, AWS EC2, etc.)

2. **SSH into your server**
   ```bash
   ssh user@your-server-ip
   ```

3. **Install Docker & Docker Compose**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   sudo apt-get install docker-compose-plugin
   ```

4. **Clone your repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/hair-similarity.git
   cd hair-similarity
   ```

5. **Create .env file**
   ```bash
   nano .env
   # Add all your environment variables
   ```

6. **Start services**
   ```bash
   docker compose up -d
   ```

7. **Set up reverse proxy (Nginx)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

---

## Environment Variables Checklist

Make sure to set these in your deployment platform:

- ✅ `DATABASE_URL` - PostgreSQL connection string (usually auto-provided)
- ✅ `IG_ACCESS_TOKEN` - Instagram access token
- ✅ `IG_APP_ID` - Facebook App ID
- ✅ `IG_APP_SECRET` - Facebook App Secret
- ✅ `IG_USER_ID` - Instagram Business Account ID
- ✅ `JWT_SECRET` - Random secret for JWT tokens (generate with: `openssl rand -hex 32`)

---

## Post-Deployment Checklist

1. ✅ Verify database connection
2. ✅ Test API endpoints
3. ✅ Verify Instagram API integration
4. ✅ Test image upload and search
5. ✅ Set up custom domain (optional)
6. ✅ Enable HTTPS/SSL (most platforms do this automatically)
7. ✅ Set up monitoring/logging (optional)

---

## Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` is correctly set
- Check if database is accessible from your app service
- Ensure database is in the same region/network

### Instagram API Errors
- Verify access token is valid and not expired
- Check rate limits
- Ensure all required permissions are granted

### Build Failures
- Check Python version (requires 3.9+)
- Verify all dependencies in `requirements.txt`
- Check build logs for specific errors

---

## Recommended: Render or Railway

For easiest deployment, I recommend **Render** or **Railway**:
- ✅ Free tier available
- ✅ Easy GitHub integration
- ✅ Automatic PostgreSQL setup
- ✅ Automatic HTTPS
- ✅ Simple environment variable management
- ✅ Auto-deploy on git push


