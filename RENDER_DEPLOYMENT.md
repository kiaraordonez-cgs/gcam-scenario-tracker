# GCAM Tracker - Render Deployment Guide

## Quick Deployment to Render.com

### Step 1: Push to GitHub

1. **Create a new GitHub repository**
   - Go to https://github.com/new
   - Name it `gcam-tracker` (or whatever you prefer)
   - Make it **Public** (easier for free tier)
   - Don't add README, .gitignore, or license (we have them)
   - Click "Create repository"

2. **Upload your code**
   
   **Option A - Upload via GitHub website** (Easiest):
   - On your new repo page, click "uploading an existing file"
   - Drag all files from this folder into the upload area
   - Make sure to include the hidden `.gitignore` file
   - Commit directly to main branch
   
   **Option B - Use Git** (if you have it installed):
   ```bash
   cd gcam-tracker-deploy
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/gcam-tracker.git
   git push -u origin main
   ```

### Step 2: Deploy on Render

1. **Connect GitHub to Render**
   - On the Render screen you're seeing, click **GitHub**
   - Authorize Render to access your GitHub repos
   - Find and select your `gcam-tracker` repository

2. **Configure the Web Service**
   
   Render should auto-detect the settings from `render.yaml`, but verify:
   
   - **Name**: `gcam-tracker` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: `Free`

3. **Deploy**
   - Click "Create Web Service"
   - Render will:
     - Install Python dependencies
     - Run the build script
     - Start your app with gunicorn
   
   Wait 2-3 minutes for first deployment.

4. **Access Your App**
   - You'll get a URL like: `https://gcam-tracker-abc123.onrender.com`
   - Open it in your browser
   - Start uploading XML files!

## Important Notes

### Free Tier Limitations
- **Sleeps after 15 min of inactivity** - first request after sleep takes ~30 seconds
- **750 hours/month** - enough for continuous use if it's your only service
- **Database resets on each deploy** - files in `uploads/` are also lost

### Data Persistence Solution

The free tier doesn't persist uploaded files or database between deploys. To fix this:

**Option 1 - Upgrade to Paid Tier** ($7/month)
- Persistent disk storage
- No sleeping
- Faster performance

**Option 2 - Use External Storage** (Free)
Add cloud storage for uploads:
- AWS S3 (free tier: 5GB)
- Google Cloud Storage (free tier: 5GB)
- Cloudinary (free tier: 10GB for images)

For database, use:
- Render's free PostgreSQL (90 days, then expires)
- ElephantSQL (free tier: 20MB PostgreSQL)

Let me know if you need help adding external storage!

### Environment Variables

If you need to change the secret key:

1. In Render dashboard, go to your service
2. Click "Environment" tab
3. Add: `SECRET_KEY` = `your-random-secret-key-here`
4. Service will auto-redeploy

### Custom Domain

To use your own domain (like gcam-tracker.youruniversity.edu):

1. In Render dashboard, go to "Settings"
2. Scroll to "Custom Domain"
3. Add your domain
4. Update DNS records as instructed by Render

## Troubleshooting

**Build fails**:
- Check the build logs in Render dashboard
- Usually it's a missing dependency - add to `requirements.txt`

**App starts but gives 500 error**:
- Check application logs in Render dashboard
- Often it's a database initialization issue
- The database is created automatically on first run

**Can't upload files**:
- Free tier has limited storage
- Check file size (max 50MB in app)
- Consider upgrading or adding external storage

**Uploads disappear**:
- This is expected on free tier
- Files are stored in ephemeral filesystem
- Use external storage (S3, etc.) for persistence

## Files Included

```
gcam-tracker-deploy/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies (includes gunicorn)
├── build.sh              # Render build script
├── render.yaml           # Render auto-configuration
├── .gitignore            # Files to exclude from Git
├── README.md             # Full documentation
├── RENDER_DEPLOYMENT.md  # This file
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── scenario_detail.html
│   ├── input_detail.html
│   └── compare.html
└── static/               # CSS and JavaScript
    ├── css/style.css
    └── js/script.js
```

## Next Steps After Deployment

1. **Test uploads** - Try uploading a configuration XML
2. **Share URL** - Send the Render URL to your team
3. **Set up backups** - Download database regularly if using free tier
4. **Monitor usage** - Check Render dashboard for activity

## Need Help?

- Render Docs: https://render.com/docs/web-services
- Render Discord: https://discord.gg/render
- GitHub Issues: Create an issue in your repo

Your app is ready to deploy! 🚀
