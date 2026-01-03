# Production Deployment Guide - Cheap Options

## 🏆 Recommended: Render (Best Balance of Price & Ease)

**Cost**: FREE for 90 days, then ~$7/month (web service) + $7/month (database) = **$14/month total**

### Why Render?
- ✅ 90-day free trial (no credit card needed initially)
- ✅ Very easy setup
- ✅ Automatic HTTPS/SSL
- ✅ Automatic deployments from GitHub
- ✅ Built-in PostgreSQL with pgvector support

### Step-by-Step Deployment

#### 1. Prepare Your Repository
Make sure your code is pushed to GitHub.

#### 2. Create Render Account
- Go to [render.com](https://render.com)
- Sign up with GitHub (free)

#### 3. Create PostgreSQL Database
1. Dashboard → "New +" → "PostgreSQL"
2. Name: `hair-similarity-db`
3. Database: `postgres`
4. User: `postgres`
5. Region: Choose closest to you
6. Plan: **Free** (for testing) or **Starter** ($7/month for production)
7. Click "Create Database"
8. **Save the connection string** - you'll need it!

#### 4. Deploy Web Service
1. Dashboard → "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: `hair-similarity-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r app/requirements.txt`
   - **Start Command**: `cd app && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: **Free** (for testing) or **Starter** ($7/month for production)

#### 5. Set Environment Variables
In your web service settings, go to "Environment" and add:

```env
DATABASE_URL=<paste the connection string from step 3>
IG_ACCESS_TOKEN=your_instagram_token
IG_APP_ID=your_app_id
IG_APP_SECRET=your_app_secret
IG_USER_ID=your_user_id
JWT_SECRET=<generate a random string>
IG_REDIRECT_URI=https://your-app-name.onrender.com/auth/callback
```

**To generate JWT_SECRET**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 6. Deploy!
- Click "Create Web Service"
- Render will build and deploy automatically
- First deployment takes ~5-10 minutes
- Your app will be available at: `https://your-app-name.onrender.com`

---

## 🆓 Alternative: Fly.io (Free Tier Available)

**Cost**: FREE tier available (with limitations), then ~$5-10/month

### Why Fly.io?
- ✅ Generous free tier
- ✅ Good for small projects
- ✅ Global edge network

### Setup Steps

1. **Install Fly CLI**:
   ```bash
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Create Fly App**:
   ```bash
   fly launch
   ```
   - Follow prompts
   - Choose region
   - Don't deploy yet

4. **Create PostgreSQL Database**:
   ```bash
   fly postgres create --name hair-similarity-db
   ```
   - Choose region
   - Choose plan (free tier available)

5. **Attach Database to App**:
   ```bash
   fly postgres attach --app hair-similarity-api hair-similarity-db
   ```

6. **Set Environment Variables**:
   ```bash
   fly secrets set IG_ACCESS_TOKEN=your_token
   fly secrets set IG_APP_ID=your_app_id
   fly secrets set IG_APP_SECRET=your_secret
   fly secrets set IG_USER_ID=your_user_id
   fly secrets set JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

7. **Deploy**:
   ```bash
   fly deploy
   ```

---

## 💰 Cheapest Option: Hetzner VPS (Most Setup Required)

**Cost**: ~€4-5/month (~$4-5/month)

### Why Hetzner?
- ✅ Very cheap
- ✅ Full control
- ✅ Good performance
- ❌ Requires more technical knowledge

### Setup Steps

1. **Create Hetzner Account**: [hetzner.com](https://hetzner.com)
2. **Create VPS**:
   - Choose "CPX11" (€4.75/month) or "CPX21" (€6.29/month)
   - OS: Ubuntu 22.04
   - Location: Choose closest

3. **SSH into Server**:
   ```bash
   ssh root@your-server-ip
   ```

4. **Install Docker & Docker Compose**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

5. **Clone Your Repository**:
   ```bash
   git clone https://github.com/your-username/hair-similarity.git
   cd hair-similarity
   ```

6. **Set Up Environment Variables**:
   ```bash
   cp .env.example .env
   nano .env
   # Edit with your production values
   ```

7. **Start Services**:
   ```bash
   docker-compose up -d
   ```

8. **Set Up Nginx (Reverse Proxy)**:
   ```bash
   apt install nginx certbot python3-certbot-nginx
   # Configure nginx for your domain
   certbot --nginx -d yourdomain.com
   ```

---

## 📊 Cost Comparison

| Option | Monthly Cost | Free Tier | Difficulty | Best For |
|--------|-------------|-----------|------------|----------|
| **Render** | $14/month | 90 days free | ⭐ Easy | Most users |
| **Fly.io** | $0-10/month | Yes | ⭐⭐ Medium | Developers |
| **Railway** | $5-20/month | $5 credit | ⭐ Easy | Quick setup |
| **Hetzner VPS** | €4-5/month | No | ⭐⭐⭐ Hard | Advanced users |
| **DigitalOcean** | $12/month | $200 credit | ⭐⭐ Medium | Startups |

---

## 🎯 My Recommendation

**For you, I recommend Render** because:
1. ✅ **90 days FREE** - Test everything before paying
2. ✅ **Easiest setup** - No command line needed
3. ✅ **$14/month** after free trial - Very affordable
4. ✅ **Automatic HTTPS** - No SSL certificate setup
5. ✅ **Auto-deployments** - Push to GitHub = auto-deploy

---

## 🚀 Quick Start with Render (Recommended)

### 1. One-Time Setup (15 minutes)

1. Push code to GitHub
2. Sign up at render.com
3. Create PostgreSQL database
4. Create Web Service
5. Add environment variables
6. Deploy!

### 2. After Deployment

Your app will be live at: `https://your-app-name.onrender.com`

**Note**: Free tier services "spin down" after 15 minutes of inactivity. First request after spin-down takes ~30 seconds. Upgrade to paid plan to avoid this.

---

## 🔧 Post-Deployment Checklist

- [ ] Test your website URL
- [ ] Test database connection (check logs)
- [ ] Test Instagram API integration
- [ ] Test user registration/login
- [ ] Test image upload/search
- [ ] Set up custom domain (optional)
- [ ] Enable automatic backups
- [ ] Set up monitoring/alerts

---

## 💡 Cost Optimization Tips

1. **Use Free Tier First**: Test on Render's free tier for 90 days
2. **Monitor Usage**: Check Render dashboard for actual usage
3. **Optimize Images**: Compress images to reduce storage costs
4. **Database Cleanup**: Regularly clean old data
5. **CDN**: Use Cloudflare (free) for static assets

---

## 🆘 Need Help?

If you get stuck:
1. Check Render logs (Dashboard → Your Service → Logs)
2. Check database connection string format
3. Verify all environment variables are set
4. Check Instagram API credentials

---

## 📝 Next Steps

1. **Choose Render** (recommended)
2. Follow the Render setup steps above
3. Test your deployment
4. Share your live URL! 🎉

