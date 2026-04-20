# Work Email Setup Checklist

## ✅ What You've Done
- [x] Created Google Sheet with work email
- [x] Created Google Drive folder with work email  
- [x] Shared both with service account (Editor access)
- [x] Provided new IDs

## 📋 What You Need to Do Now

### 1. Set Up Google Sheet Headers

Open your Sheet: https://docs.google.com/spreadsheets/d/1n1dwcHThv_I19lWkuNhAK5rlscnyMGlM2x-VoR4R8rs/edit

#### Tab 1: "Scenarios"
Make sure the first row has these exact headers (copy/paste):
```
id	scenario_name	personal_scenario_name	project_name	date_run	description	zaratan_link	additional_notes	uploaded_by	upload_date	config_file_id	num_input_files
```

#### Tab 2: "InputFiles"  
First row headers:
```
id	file_name	regions_modified	years_modified	sectors_modified	policy_name	folder_location	description	additional_notes	uploaded_by	upload_date	file_id
```

#### Tab 3: "ScenarioInputs"
First row headers:
```
scenario_id	input_file_id	component_key
```

**Tip:** Make sure there are NO extra spaces and headers are in row 1!

---

### 2. Update GitHub with New IDs

The `app.py` file has been updated with your new IDs:
- Sheet ID: `1n1dwcHThv_I19lWkuNhAK5rlscnyMGlM2x-VoR4R8rs`
- Folder ID: `1RY61HJn1nWGsOlbjBE1lnbsEIH16TTfR`

**Upload to GitHub:**
1. Go to: https://github.com/kiaraordonez-cgs/gcam-scenario-tracker
2. Click on `app.py`
3. Click pencil icon (edit)
4. Replace ALL content with the new `app.py` from the package
5. Commit changes

---

### 3. Verify Permissions

Double-check in your work email Google Sheet:

1. Click "Share" button
2. You should see:
   - Your work email (Owner)
   - `gcam-scenario-tracker-service@gcam-scenario-tracker.iam.gserviceaccount.com` (Editor)

Do the same for the Drive folder!

---

### 4. Wait for Render to Deploy

After you update `app.py` on GitHub:
- Render auto-deploys (~3 minutes)
- Watch the logs for errors
- Should see: "DEBUG: Using base64 encoded credentials" with NO errors

---

### 5. Test Upload

Once deployed:
1. Go to https://gcam-scenario-tracker.onrender.com
2. Upload `configuration_AP_17.xml`
3. Check your **WORK EMAIL** Google Sheet - data should appear!
4. Check your **WORK EMAIL** Drive folder - file should appear!

---

## 🎉 Result

After this:
- ✅ All data stored under WORK email (your university storage)
- ✅ Personal Gmail only provides backend service account
- ✅ You can share Sheet/folder with coworkers using work email
- ✅ If you leave, university keeps the data
- ✅ Service account is invisible to end users

---

## 🔧 Files to Update on GitHub

From the package:
1. **app.py** (new Sheet/Folder IDs) - REQUIRED
2. **templates/index.html** (UI updates) - Optional but recommended
3. **static/css/style.css** (UI updates) - Optional but recommended

Upload all 3 for the complete update (new IDs + new UI)!
