# GCAM Scenario Tracker

A web application for uploading, tracking, and comparing GCAM configuration files and input files.

## Features

### For Configuration Files
- Upload GCAM configuration XML files
- Automatically extracts:
  - Scenario name
  - List of all input files referenced
  - Upload metadata
- Editable fields:
  - Personal scenario name
  - Project name (dropdown with custom options)
  - Date run
  - Description
  - Zaratan output link
  - Additional notes

### For Input Files
- Upload GCAM input XML files
- Automatically extracts:
  - Regions modified (e.g., CA, TX, NY)
  - Years modified (e.g., 2030, 2035)
  - Sectors/policies modified
  - File name
- Editable fields:
  - Policy name
  - Folder location
  - Description
  - Additional notes
- Shows which scenarios use each input file

### Additional Features
- **Two linked tables**: Scenarios ↔ Input Files (many-to-many relationship)
- **Inline editing**: Click any editable cell to update it
- **Search and filter**: Search by name, filter by project
- **File comparison**: Select two input files to see a side-by-side diff
- **File downloads**: Download any uploaded XML file
- **Spreadsheet-like interface**: Familiar table view with sortable columns

## Quick Start (Local Development)

### Prerequisites
- Python 3.8 or higher
- pip

### Installation

1. **Extract the application files**
   ```bash
   cd gcam-tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Open in browser**
   Navigate to `http://localhost:5000`

That's it! The database will be created automatically on first run.

## Deployment Options

### Option 1: Free Cloud Hosting (Render.com)

Render offers free hosting for web apps. Perfect for small teams.

1. **Create a free account** at [render.com](https://render.com)

2. **Create a new Web Service**
   - Connect your GitHub repository (or upload files)
   - Choose "Python" environment
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

3. **Add gunicorn to requirements.txt**
   ```bash
   echo "gunicorn==21.2.0" >> requirements.txt
   ```

4. **Deploy**
   Render will automatically deploy your app and give you a URL like:
   `https://gcam-tracker-abc123.onrender.com`

**Note**: Free tier sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

### Option 2: Lab Server / University Server

If you have access to a Linux server:

1. **Install Python and dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn
   ```

2. **Run with gunicorn** (production server)
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

3. **Set up as a service** (optional - keeps it running)
   Create `/etc/systemd/system/gcam-tracker.service`:
   ```ini
   [Unit]
   Description=GCAM Tracker
   After=network.target

   [Service]
   User=your-username
   WorkingDirectory=/path/to/gcam-tracker
   ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Then:
   ```bash
   sudo systemctl enable gcam-tracker
   sudo systemctl start gcam-tracker
   ```

4. **Access from anywhere** (optional - set up nginx reverse proxy)
   This lets you access it via a friendly URL instead of IP:port

   Install nginx:
   ```bash
   sudo apt install nginx
   ```

   Create `/etc/nginx/sites-available/gcam-tracker`:
   ```nginx
   server {
       listen 80;
       server_name your-server-name.edu;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

   Enable:
   ```bash
   sudo ln -s /etc/nginx/sites-available/gcam-tracker /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Option 3: Heroku (Another Free Option)

1. **Install Heroku CLI**
   [Download here](https://devcli.heroku.com/install)

2. **Create a Procfile**
   ```bash
   echo "web: gunicorn app:app" > Procfile
   ```

3. **Add gunicorn**
   ```bash
   echo "gunicorn==21.2.0" >> requirements.txt
   ```

4. **Deploy**
   ```bash
   heroku login
   heroku create gcam-tracker
   git init
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```

Your app will be at `https://gcam-tracker.herokuapp.com`

## Usage Guide

### Uploading Configuration Files

1. Go to the dashboard
2. Under "Upload Configuration File", enter your name
3. Select the configuration XML file (e.g., `configuration_AP_17.xml`)
4. Click "Upload Configuration"

The app will:
- Parse the scenario name from `<Strings><Value name="scenarioName">`
- Extract all input files from `<ScenarioComponents>`
- Create a scenario row
- Create input file rows for each referenced file (if they don't exist)
- Link them together

### Uploading Input Files

1. Under "Upload Input File", enter your name
2. Select an input XML file (e.g., `coal_ceiling_tiered_phaseout_2030_2035_HA1.xml`)
3. Click "Upload Input File"

The app will:
- Parse regions from `<region name="...">`
- Parse years from `<constraint year="...">`
- Parse sectors/policies from element names
- Update the existing input file row with this metadata

### Editing Metadata

**For scenarios:**
- Click any cell in the "Personal Name", "Description", etc. columns
- Type your changes and press Enter or click away to save
- For "Project", select from dropdown or choose "+ Add New" to create a new project

**For input files:**
- Same process - click to edit, changes save automatically

### Comparing Files

1. In the Input Files table, check the boxes next to two files
2. Click "Compare Files" button
3. View side-by-side differences (if files have been uploaded)

### Searching and Filtering

- Use the search boxes to find scenarios or input files by name
- Use the "Project" dropdown to filter scenarios by project
- Click column headers to sort (browser feature)

## File Structure

```
gcam-tracker/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── gcam_tracker.db        # SQLite database (auto-created)
├── uploads/               # Uploaded files (auto-created)
│   ├── configs/          # Configuration XMLs
│   └── inputs/           # Input XMLs
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── scenario_detail.html
│   ├── input_detail.html
│   └── compare.html
└── static/               # CSS and JavaScript
    ├── css/
    │   └── style.css
    └── js/
        └── script.js
```

## Database Schema

**scenarios** table:
- id, scenario_name, personal_scenario_name, project_name
- date_run, description, zaratan_link, additional_notes
- uploaded_by, upload_date, config_file_path, num_input_files

**input_files** table:
- id, file_name, regions_modified, years_modified, sectors_modified
- policy_name, folder_location, description, additional_notes
- uploaded_by, upload_date, file_path

**scenario_inputs** (junction table):
- scenario_id, input_file_id, component_key

## Customization

### Adding Projects

Projects are added dynamically when you select "+ Add New" from the dropdown and enter a name. They're stored in the database and appear in the dropdown for all users.

### Changing the Secret Key

In `app.py`, line 13:
```python
app.config['SECRET_KEY'] = 'change-this-to-a-random-secret-key'
```

Generate a random key:
```python
import secrets
print(secrets.token_hex(32))
```

### Modifying Parsers

If your XML structure differs, edit these functions in `app.py`:
- `parse_configuration_xml()` - line 92
- `parse_input_file_xml()` - line 130

### Adding More Fields

1. Edit database schema in `init_db()` function
2. Add columns to HTML tables in templates
3. Update the `update_scenario()` or `update_input()` routes

## Troubleshooting

**Database locked error**
- SQLite has limited concurrent write support
- If multiple people upload at once, one may see this error
- Solution: Reload the page and try again
- For production with many users, switch to PostgreSQL

**File upload fails**
- Check file size (max 50MB by default)
- Ensure file is valid XML
- Check server logs for detailed error

**Changes don't save**
- Check browser console for errors (F12)
- Ensure JavaScript is enabled
- Try a different browser

**Can't access from other computers**
- Check firewall allows port 5000
- Use `0.0.0.0` instead of `127.0.0.1` when running
- For cloud deployment, use the provided URL

## Support

For issues specific to your GCAM XML format, edit the parser functions in `app.py`.

For deployment help, refer to the documentation for your chosen platform:
- Render: https://render.com/docs
- Heroku: https://devcenter.heroku.com/
- nginx: https://nginx.org/en/docs/

## License

This application was created for academic research use. Modify freely for your needs.
