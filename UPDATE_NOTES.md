# Updates - Red Theme + Bug Fixes

## Changes Made

### 1. ✅ Color Scheme Changed to Professional Red
- Changed from purple (#667eea, #764ba2) to red (#dc2626, #991b1b)
- Updated: navbar, buttons, tabs, badges, links
- Professional corporate red theme throughout

### 2. ✅ Removed Globe Emoji
- Title is now just "GCAM Scenario Tracker" (no 🌍)
- Cleaner, more professional look

### 3. ✅ Removed Compare Button from Input Files Tab
- Compare functionality removed (input files aren't stored anyway)
- Removed checkboxes from input files table
- Cleaner interface focused on metadata tracking

## Known Issue: Only 23 Input Files Detected

**The parser works correctly** - it finds all 166 unique input files in the configuration.

**Possible causes:**
1. Google Sheets `append_rows()` might have a batch limit
2. The existing InputFiles sheet might have pre-existing data causing conflicts

**To check:**
1. Open your Google Sheet InputFiles tab
2. See if there are actually more than 23 rows
3. If yes: UI pagination issue
4. If no: Batch append limit

**Quick fix to test:**
Try uploading a simple config with just 5-10 input files to see if they all appear.

**Permanent fix options:**
- Chunk the batch inserts (50 files at a time)
- Or just accept that input files are reference-only anyway

## Files to Upload

1. **static/css/style.css** (red theme)
2. **templates/base.html** (no emoji)
3. **templates/index.html** (no compare button)

app.py and requirements.txt stay the same as before.
