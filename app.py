#!/usr/bin/env python3
"""
GCAM Scenario Tracker - Google Drive/Sheets Version
A Flask app that stores data in Google Sheets and files in Google Drive
"""

import os
import json
import difflib
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from werkzeug.utils import secure_filename
from lxml import etree
import gspread
from google.oauth2.service_account import Credentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# =============================================================================
# Configuration
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-to-a-random-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Google Configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

GOOGLE_SHEET_ID = '1svIAFCtbWXFAgikFPRW8oMQTJbK-hOAKXehrYhP49ag'
GOOGLE_DRIVE_FOLDER_ID = '1JvhWQa2H3jXP8r6BtYEG6pGCCIZDMrDP'

ALLOWED_EXTENSIONS = {'xml'}

# =============================================================================
# Google API Setup
# =============================================================================

def get_google_sheets_client():
    """Initialize and return Google Sheets client"""
    import os
    import json
    
    # Try environment variable first, fall back to file
    creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('service-account.json', scopes=SCOPES)
    
    return gspread.authorize(creds)

def get_google_drive_client():
    """Initialize and return Google Drive client"""
    import os
    import json
    import tempfile
    
    gauth = GoogleAuth()
    
    # Try environment variable first
    creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if creds_json:
        # Write to temp file for PyDrive
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(creds_json)
            temp_path = f.name
        gauth.service_account_file = temp_path
    else:
        gauth.service_account_file = 'service-account.json'
    
    gauth.service_account_email = 'gcam-scenario-tracker-service@gcam-scenario-tracker.iam.gserviceaccount.com'
    gauth.ServiceAuth()
    return GoogleDrive(gauth)

# Initialize clients
try:
    gc = get_google_sheets_client()
    sheet = gc.open_by_key(GOOGLE_SHEET_ID)
    scenarios_sheet = sheet.worksheet('Scenarios')
    inputs_sheet = sheet.worksheet('InputFiles')
    junction_sheet = sheet.worksheet('ScenarioInputs')
    
    drive = get_google_drive_client()
except Exception as e:
    print(f"Error initializing Google APIs: {e}")
    gc = None
    drive = None

# =============================================================================
# Helper Functions - Google Sheets
# =============================================================================

def get_next_id(worksheet):
    """Get next available ID for a sheet"""
    values = worksheet.col_values(1)[1:]  # Skip header
    if not values:
        return 1
    return max([int(v) for v in values if v.isdigit()]) + 1

def find_row_by_id(worksheet, row_id):
    """Find row number by ID (returns row number, 1-indexed)"""
    try:
        cell = worksheet.find(str(row_id), in_column=1)
        return cell.row if cell else None
    except:
        return None

def find_row_by_value(worksheet, column, value):
    """Find first row where column matches value"""
    try:
        col_idx = worksheet.find(column).col
        col_values = worksheet.col_values(col_idx)
        for idx, val in enumerate(col_values[1:], start=2):  # Skip header
            if val == value:
                return idx
        return None
    except:
        return None

def get_all_scenarios():
    """Get all scenarios from Google Sheet"""
    try:
        records = scenarios_sheet.get_all_records()
        # Count input files for each scenario
        junction_records = junction_sheet.get_all_records()
        
        for record in records:
            record['input_count'] = sum(1 for j in junction_records if str(j.get('scenario_id')) == str(record.get('id')))
        
        return records
    except Exception as e:
        print(f"Error getting scenarios: {e}")
        return []

def get_all_input_files():
    """Get all input files from Google Sheet"""
    try:
        records = inputs_sheet.get_all_records()
        # Count scenarios for each input file
        junction_records = junction_sheet.get_all_records()
        
        for record in records:
            record['scenario_count'] = sum(1 for j in junction_records if str(j.get('input_file_id')) == str(record.get('id')))
        
        return records
    except Exception as e:
        print(f"Error getting input files: {e}")
        return []

def get_scenario_by_id(scenario_id):
    """Get scenario by ID"""
    try:
        records = scenarios_sheet.get_all_records()
        for record in records:
            if str(record.get('id')) == str(scenario_id):
                return record
        return None
    except Exception as e:
        print(f"Error getting scenario: {e}")
        return None

def get_input_by_id(input_id):
    """Get input file by ID"""
    try:
        records = inputs_sheet.get_all_records()
        for record in records:
            if str(record.get('id')) == str(input_id):
                return record
        return None
    except Exception as e:
        print(f"Error getting input file: {e}")
        return None

def get_input_files_for_scenario(scenario_id):
    """Get all input files linked to a scenario"""
    try:
        junction_records = junction_sheet.get_all_records()
        input_records = inputs_sheet.get_all_records()
        
        linked_input_ids = [j['input_file_id'] for j in junction_records if str(j['scenario_id']) == str(scenario_id)]
        
        result = []
        for input_rec in input_records:
            if str(input_rec['id']) in [str(i) for i in linked_input_ids]:
                # Find component key
                for j in junction_records:
                    if str(j['scenario_id']) == str(scenario_id) and str(j['input_file_id']) == str(input_rec['id']):
                        input_rec['component_key'] = j.get('component_key', '')
                        break
                result.append(input_rec)
        
        return result
    except Exception as e:
        print(f"Error getting input files for scenario: {e}")
        return []

def get_scenarios_for_input(input_id):
    """Get all scenarios using an input file"""
    try:
        junction_records = junction_sheet.get_all_records()
        scenario_records = scenarios_sheet.get_all_records()
        
        linked_scenario_ids = [j['scenario_id'] for j in junction_records if str(j['input_file_id']) == str(input_id)]
        
        result = []
        for scenario_rec in scenario_records:
            if str(scenario_rec['id']) in [str(s) for s in linked_scenario_ids]:
                # Find component key
                for j in junction_records:
                    if str(j['input_file_id']) == str(input_id) and str(j['scenario_id']) == str(scenario_rec['id']):
                        scenario_rec['component_key'] = j.get('component_key', '')
                        break
                result.append(scenario_rec)
        
        return result
    except Exception as e:
        print(f"Error getting scenarios for input: {e}")
        return []

# =============================================================================
# Helper Functions - Google Drive
# =============================================================================

def upload_to_drive(file_content, filename):
    """Upload file to Google Drive and return file ID"""
    try:
        file_metadata = {
            'title': filename,
            'parents': [{'id': GOOGLE_DRIVE_FOLDER_ID}]
        }
        
        gfile = drive.CreateFile(file_metadata)
        gfile.SetContentString(file_content)
        gfile.Upload()
        
        return gfile['id']
    except Exception as e:
        print(f"Error uploading to Drive: {e}")
        return None

def download_from_drive(file_id):
    """Download file content from Google Drive"""
    try:
        gfile = drive.CreateFile({'id': file_id})
        gfile.FetchMetadata()
        return gfile.GetContentString()
    except Exception as e:
        print(f"Error downloading from Drive: {e}")
        return None

# =============================================================================
# XML Parsing Functions
# =============================================================================

def parse_configuration_xml(xml_content):
    """Parse GCAM configuration XML from string content"""
    try:
        root = etree.fromstring(xml_content.encode())
    except:
        root = etree.fromstring(xml_content)
    
    result = {
        'scenario_name': None,
        'input_files': []
    }
    
    # Extract scenario name
    for val in root.findall('.//Strings/Value[@name="scenarioName"]'):
        if val.text:
            result['scenario_name'] = val.text.strip()
            break
    
    if not result['scenario_name']:
        result['scenario_name'] = 'Unnamed Scenario'
    
    # Extract input files
    for comp in root.findall('.//ScenarioComponents/Value'):
        file_path = comp.text.strip() if comp.text else None
        component_key = comp.get('name', '')
        
        if file_path:
            file_name = Path(file_path).name
            result['input_files'].append({
                'file_name': file_name,
                'file_path': file_path,
                'component_key': component_key
            })
    
    return result

def parse_input_file_xml(xml_content):
    """Parse GCAM input file XML from string content"""
    try:
        try:
            root = etree.fromstring(xml_content.encode())
        except:
            root = etree.fromstring(xml_content)
        
        result = {
            'regions': set(),
            'years': set(),
            'sectors': set()
        }
        
        # Extract regions
        for region in root.findall('.//region'):
            region_name = region.get('name')
            if region_name:
                result['regions'].add(region_name)
        
        # Extract years
        for constraint in root.findall('.//constraint'):
            year = constraint.get('year')
            if year:
                result['years'].add(year)
        
        # Extract sectors/policies
        for policy in root.findall('.//policy-portfolio-standard'):
            policy_name = policy.get('name', '')
            if policy_name:
                result['sectors'].add(policy_name)
        
        return {
            'regions': ', '.join(sorted(result['regions'])) if result['regions'] else 'All',
            'years': ', '.join(sorted(result['years'])) if result['years'] else 'N/A',
            'sectors': ', '.join(sorted(result['sectors'])) if result['sectors'] else 'N/A'
        }
    except Exception as e:
        print(f"Error parsing input XML: {e}")
        return {
            'regions': 'Parse Error',
            'years': 'Parse Error',
            'sectors': 'Parse Error'
        }

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =============================================================================
# Routes
# =============================================================================

@app.route('/')
def index():
    """Main dashboard"""
    scenarios = get_all_scenarios()
    input_files = get_all_input_files()
    
    # Get unique projects for dropdown
    projects = list(set([s.get('project_name', '') for s in scenarios if s.get('project_name')]))
    projects.sort()
    
    return render_template('index.html',
                         scenarios=scenarios,
                         input_files=input_files,
                         projects=projects)

@app.route('/upload_config', methods=['POST'])
def upload_config():
    """Upload and parse configuration XML"""
    if 'config_file' not in request.files:
        flash('No file provided', 'error')
        return redirect(url_for('index'))
    
    file = request.files['config_file']
    uploaded_by = request.form.get('uploaded_by', 'Unknown')
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Only XML files allowed', 'error')
        return redirect(url_for('index'))
    
    try:
        # Read file content
        filename = secure_filename(file.filename)
        file_content = file.read().decode('utf-8')
        
        # Upload to Google Drive
        file_id = upload_to_drive(file_content, filename)
        
        if not file_id:
            flash('Error uploading file to Drive', 'error')
            return redirect(url_for('index'))
        
        # Parse configuration
        parsed = parse_configuration_xml(file_content)
        
        # Add scenario to sheet
        scenario_id = get_next_id(scenarios_sheet)
        upload_date = datetime.now().isoformat()
        
        scenarios_sheet.append_row([
            scenario_id,
            parsed['scenario_name'],
            '',  # personal_scenario_name
            '',  # project_name
            '',  # date_run
            '',  # description
            '',  # zaratan_link
            '',  # additional_notes
            uploaded_by,
            upload_date,
            file_id,
            len(parsed['input_files'])
        ])
        
        # Process input files
        for input_file in parsed['input_files']:
            # Check if input file already exists
            existing_row = find_row_by_value(inputs_sheet, 'file_name', input_file['file_name'])
            
            if existing_row:
                input_id = inputs_sheet.cell(existing_row, 1).value
            else:
                # Create new input file record
                input_id = get_next_id(inputs_sheet)
                inputs_sheet.append_row([
                    input_id,
                    input_file['file_name'],
                    'Not analyzed',
                    'Not analyzed',
                    'Not analyzed',
                    '',  # policy_name
                    '',  # folder_location
                    '',  # description
                    '',  # additional_notes
                    'Auto-detected',
                    upload_date,
                    ''   # file_id (will be filled when actual file uploaded)
                ])
            
            # Link scenario to input file
            junction_sheet.append_row([
                scenario_id,
                input_id,
                input_file['component_key']
            ])
        
        flash(f'Successfully uploaded scenario "{parsed["scenario_name"]}" with {len(parsed["input_files"])} input files', 'success')
        
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/upload_input', methods=['POST'])
def upload_input():
    """Upload input file XML"""
    if 'input_file' not in request.files:
        flash('No file provided', 'error')
        return redirect(url_for('index'))
    
    file = request.files['input_file']
    uploaded_by = request.form.get('uploaded_by', 'Unknown')
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Only XML files allowed', 'error')
        return redirect(url_for('index'))
    
    try:
        # Read file content
        filename = secure_filename(file.filename)
        file_content = file.read().decode('utf-8')
        
        # Upload to Google Drive
        file_id = upload_to_drive(file_content, filename)
        
        if not file_id:
            flash('Error uploading file to Drive', 'error')
            return redirect(url_for('index'))
        
        # Parse input file
        parsed = parse_input_file_xml(file_content)
        
        upload_date = datetime.now().isoformat()
        
        # Check if file already exists
        existing_row = find_row_by_value(inputs_sheet, 'file_name', filename)
        
        if existing_row:
            # Update existing record
            inputs_sheet.update_cell(existing_row, 3, parsed['regions'])
            inputs_sheet.update_cell(existing_row, 4, parsed['years'])
            inputs_sheet.update_cell(existing_row, 5, parsed['sectors'])
            inputs_sheet.update_cell(existing_row, 10, uploaded_by)
            inputs_sheet.update_cell(existing_row, 11, upload_date)
            inputs_sheet.update_cell(existing_row, 12, file_id)
            flash(f'Updated input file "{filename}"', 'success')
        else:
            # Create new record
            input_id = get_next_id(inputs_sheet)
            inputs_sheet.append_row([
                input_id,
                filename,
                parsed['regions'],
                parsed['years'],
                parsed['sectors'],
                '',  # policy_name
                '',  # folder_location
                '',  # description
                '',  # additional_notes
                uploaded_by,
                upload_date,
                file_id
            ])
            flash(f'Added new input file "{filename}"', 'success')
        
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/update_scenario/<int:scenario_id>', methods=['POST'])
def update_scenario(scenario_id):
    """Update scenario metadata"""
    try:
        row = find_row_by_id(scenarios_sheet, scenario_id)
        if not row:
            return jsonify({'status': 'error', 'message': 'Scenario not found'}), 404
        
        data = request.form
        
        # Update cells (columns match header order)
        if 'personal_scenario_name' in data:
            scenarios_sheet.update_cell(row, 3, data['personal_scenario_name'])
        if 'project_name' in data:
            scenarios_sheet.update_cell(row, 4, data['project_name'])
        if 'date_run' in data:
            scenarios_sheet.update_cell(row, 5, data['date_run'])
        if 'description' in data:
            scenarios_sheet.update_cell(row, 6, data['description'])
        if 'zaratan_link' in data:
            scenarios_sheet.update_cell(row, 7, data['zaratan_link'])
        if 'additional_notes' in data:
            scenarios_sheet.update_cell(row, 8, data['additional_notes'])
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/update_input/<int:input_id>', methods=['POST'])
def update_input(input_id):
    """Update input file metadata"""
    try:
        row = find_row_by_id(inputs_sheet, input_id)
        if not row:
            return jsonify({'status': 'error', 'message': 'Input file not found'}), 404
        
        data = request.form
        
        # Update cells
        if 'policy_name' in data:
            inputs_sheet.update_cell(row, 6, data['policy_name'])
        if 'folder_location' in data:
            inputs_sheet.update_cell(row, 7, data['folder_location'])
        if 'description' in data:
            inputs_sheet.update_cell(row, 8, data['description'])
        if 'additional_notes' in data:
            inputs_sheet.update_cell(row, 9, data['additional_notes'])
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/scenario/<int:scenario_id>')
def scenario_detail(scenario_id):
    """View scenario details"""
    scenario = get_scenario_by_id(scenario_id)
    
    if not scenario:
        flash('Scenario not found', 'error')
        return redirect(url_for('index'))
    
    input_files = get_input_files_for_scenario(scenario_id)
    
    return render_template('scenario_detail.html', scenario=scenario, input_files=input_files)

@app.route('/input/<int:input_id>')
def input_detail(input_id):
    """View input file details"""
    input_file = get_input_by_id(input_id)
    
    if not input_file:
        flash('Input file not found', 'error')
        return redirect(url_for('index'))
    
    scenarios = get_scenarios_for_input(input_id)
    
    return render_template('input_detail.html', input_file=input_file, scenarios=scenarios)

@app.route('/compare/<int:id1>/<int:id2>')
def compare_inputs(id1, id2):
    """Compare two input files"""
    file1 = get_input_by_id(id1)
    file2 = get_input_by_id(id2)
    
    if not file1 or not file2:
        flash('One or both files not found', 'error')
        return redirect(url_for('index'))
    
    diff_html = None
    
    # Download and compare if both have file IDs
    if file1.get('file_id') and file2.get('file_id'):
        content1 = download_from_drive(file1['file_id'])
        content2 = download_from_drive(file2['file_id'])
        
        if content1 and content2:
            diff = difflib.HtmlDiff()
            diff_html = diff.make_file(
                content1.splitlines(),
                content2.splitlines(),
                file1['file_name'],
                file2['file_name']
            )
    
    return render_template('compare.html', file1=file1, file2=file2, diff_html=diff_html)

@app.route('/download/<path:file_type>/<int:file_id>')
def download_file(file_type, file_id):
    """Download a file from Google Drive"""
    try:
        if file_type == 'config':
            scenario = get_scenario_by_id(file_id)
            if not scenario or not scenario.get('config_file_id'):
                flash('File not found', 'error')
                return redirect(url_for('index'))
            
            drive_file_id = scenario['config_file_id']
            filename = f"{scenario['scenario_name']}.xml"
        
        elif file_type == 'input':
            input_file = get_input_by_id(file_id)
            if not input_file or not input_file.get('file_id'):
                flash('File not found', 'error')
                return redirect(url_for('index'))
            
            drive_file_id = input_file['file_id']
            filename = input_file['file_name']
        else:
            flash('Invalid file type', 'error')
            return redirect(url_for('index'))
        
        # Download from Drive
        content = download_from_drive(drive_file_id)
        
        if not content:
            flash('Error downloading file', 'error')
            return redirect(url_for('index'))
        
        # Return file
        return Response(
            content,
            mimetype='application/xml',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
