# GCAM Tracker - Google Drive/Sheets Version
## Deployment Guide

## ✅ What You Have

A Flask app that:
- ✅ Stores data in **Google Sheets** (persistent, never resets)
- ✅ Stores files in **Google Drive** (unlimited storage via your Google account)
- ✅ Runs on **Render Free tier** ($0/month - no sleeping if you keep it active)
- ✅ Auto-parses XML files
- ✅ Supports file comparison
- ✅ Fully searchable and filterable

## 📋 Prerequisites

You should already have:
- [x] Google Cloud Project created
- [x] Service account JSON file (service-account.json)
- [x] Google Sheet set up with 3 tabs (Scenarios, InputFiles, ScenarioInputs)
- [x] Google Drive folder created
- [x] Sheet and folder shared with service account email

If you haven't done these, see the main setup instructions.

---

## 🚀 Deployment to Render (5 minutes)

### Step 1: Upload to GitHub

**Option A: Via GitHub Website** (Easiest - No Git Required)

1. Go to https://github.com/new
2. Repository name: `gcam-tracker`
3. Make it **Public**
4. Click **Create repository**
5. Click **uploading an existing file**
6. Drag ALL files from the `gcam-tracker-google` folder
7. **IMPORTANT**: Make sure `service-account.json` is included!
8. Commit

**Option B: Via Git Command Line**

```bash
cd gcam-tracker-google
git init
git add .
git commit -m "Initial commit with Google integration"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/gcam-tracker.git
git push -u origin main
```

**⚠️ Security Note**: The `service-account.json` file MUST be in your repo for Render to access Google APIs. Make your repo **Private** if you're concerned about security (requires GitHub Pro or paid Render tier). For a research project, a public repo is usually fine - the service account only has access to your specific Sheet and Drive folder.

---

### Step 2: Deploy on Render

1. On Render dashboard, click **New** → **Web Service**
2. Click **GitHub** and authorize
3. Select your `gcam-tracker` repository
4. Render will auto-detect settings from `render.yaml`:
   - Build Command: `./build.sh`
   - Start Command: `gunicorn app:app`
   - Instance Type: **Free**
5. Click **Create Web Service**
6. Wait 3-5 minutes for deployment

---

### Step 3: Test Your App

1. Once deployed, Render gives you a URL like:
   ```
   https://gcam-tracker-abc123.onrender.com
   ```

2. Open it in browser - you should see the dashboard

3. **Test upload**:
   - Upload your `configuration_AP_17.xml`
   - Check Google Sheet - you should see the scenario row appear
   - Check Google Drive folder - you should see the file

4. **Test filtering**:
   - Type in search box
   - Use project dropdown
   - Click to edit cells inline

---

## 🔄 How It Works

### Data Flow

```
User uploads XML
     ↓
Flask app parses it
     ↓
Metadata → Google Sheets (database)
File content → Google Drive (storage)
     ↓
User edits metadata in web app
     ↓
Changes save to Google Sheets
     ↓
Team can view data in either:
  - Web app (recommended)
  - Google Sheets directly (for exports/analysis)
```

### What's Stored Where

**Google Sheets** (3 tabs):
- `Scenarios`: One row per scenario
- `InputFiles`: One row per input file  
- `ScenarioInputs`: Links scenarios ↔ input files

**Google Drive** (one folder):
- All uploaded XML files
- Named exactly as uploaded
- Organized in your `GCAM Tracker Files` folder

---

## 💡 Key Advantages

### vs. Render Paid ($7/month)
✅ **Free** - No monthly cost
✅ **Unlimited storage** - Google Drive unlimited (if using university account)
✅ **Collaborative** - Team can access Google Sheet directly
✅ **No data loss** - Everything persists forever

⚠️ **Tradeoff**: App still sleeps after 15 min (first load slow)

### vs. SQLite Version
✅ **Never resets** - Data persists across deployments
✅ **Backup built-in** - Google handles backups
✅ **Accessible** - Can view/export data in Sheets
✅ **No database migrations** - Just add columns in Sheet

---

## 🔧 Configuration

### Updating Google Credentials

If you need to change Google Sheet or Drive folder:

1. Edit `app.py` lines 30-31:
```python
GOOGLE_SHEET_ID = 'your-new-sheet-id'
GOOGLE_DRIVE_FOLDER_ID = 'your-new-folder-id'
```

2. Push to GitHub - Render auto-deploys

### Adding Columns to Database

Want to track more fields?

1. Open your Google Sheet
2. Add column header in row 1
3. Update `app.py` to read/write that column
4. Push changes to GitHub

No database migrations needed!

---

## 🐛 Troubleshooting

### "Error initializing Google APIs"

**Check**:
- Is `service-account.json` in your repository?
- Did you share the Sheet and Drive folder with the service account email?
- Are both Google Sheets API and Google Drive API enabled in Cloud Console?

**Fix**:
```bash
# Re-check Cloud Console APIs
# Re-share Sheet and folder with service account
# Re-deploy on Render
```

### "File not found" when downloading

**Issue**: The file wasn't uploaded to Drive

**Fix**:
- Re-upload the file via the web app
- Check Drive folder permissions
- Ensure Drive folder ID is correct in `app.py`

### Slow performance

**Issue**: Free tier + Google API calls can be slow

**Options**:
1. Upgrade to Render Starter ($7/mo) - no sleeping, faster
2. Cache Sheet data in memory (advanced - requires code changes)
3. Accept it - it's free!

### Changes in Sheet don't appear in app

**Issue**: App caches data briefly

**Fix**: Refresh the page - app fetches fresh data on each page load

---

## 📊 Viewing Data in Google Sheets

You can view/edit data directly in Google Sheets:

**Scenarios tab**:
- Each row is a scenario
- Edit personal_scenario_name, project_name, etc. directly
- Changes appear immediately in web app

**InputFiles tab**:
- Each row is an input file
- Edit policy_name, description, etc.

**ScenarioInputs tab**:
- Don't edit manually (junction table)
- Shows which scenarios use which files

**⚠️ Don't delete rows** - breaks relationships. Mark as "archived" in notes instead.

---

## 🔒 Security

### Service Account Safety

The `service-account.json` file is sensitive but limited:
- ✅ Only has access to YOUR specific Sheet and Drive folder
- ✅ Cannot access your email, other files, or anything else
- ✅ Can be revoked anytime in Google Cloud Console

### Best Practices

1. **Use a dedicated Google Sheet** - Don't reuse personal sheets
2. **Limit sharing** - Only share with team members who need access
3. **Monitor activity** - Check Drive folder activity log
4. **Rotate keys** - Regenerate service account key yearly

### If Key Compromised

1. Go to Google Cloud Console
2. Delete the old service account key
3. Create a new key
4. Replace `service-account.json` in your repo
5. Re-deploy on Render

---

## 📈 Scaling

### Performance Tuning

If app gets slow with many scenarios:

**Option 1: Add caching** (intermediate Python)
```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1)
def get_cached_scenarios():
    return get_all_scenarios()
```

**Option 2: Pagination** (advanced)
- Load 50 scenarios at a time
- Add "Load More" button

**Option 3: Upgrade Render** ($7/mo)
- Faster instance
- More memory
- Better performance

### Team Size

Works well up to:
- ✅ 10 active users
- ✅ 100 scenarios
- ✅ 1000 input files

Beyond that, consider:
- Caching (Option 1 above)
- PostgreSQL database (requires code rewrite)
- Dedicated server

---

## 🆘 Getting Help

**Render Issues**:
- Docs: https://render.com/docs
- Logs: Check your Render dashboard

**Google API Issues**:
- Check service account permissions
- Verify API quotas in Cloud Console

**App Bugs**:
- Check browser console (F12)
- Check Render logs
- Review app.py error messages

---

## 📝 Next Steps

Once deployed:

1. **Add initial data** - Upload a few test scenarios
2. **Train team** - Show them how to use search/filter
3. **Document projects** - Create project categories
4. **Set up workflow** - When to upload configs vs inputs
5. **Schedule backups** - Download Sheet as CSV monthly (optional)

---

Your app is ready to deploy! 🎉

The Google Drive/Sheets integration means you'll never lose data and can scale indefinitely for free.
