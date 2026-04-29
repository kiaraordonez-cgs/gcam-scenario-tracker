#!/usr/bin/env python3
"""
GCAM Scenario Tracker - Google Drive/Sheets Version
A Flask app that stores data in Google Sheets and files in Google Drive
"""

import os
import json
import difflib
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from werkzeug.utils import secure_filename
from lxml import etree
import gspread
from google.oauth2.service_account import Credentials

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

GOOGLE_SHEET_ID = '1n1dwcHThv_I19lWkuNhAK5rlscnyMGlM2x-VoR4R8rs'
GOOGLE_DRIVE_FOLDER_ID = '1RY61HJn1nWGsOlbjBE1lnbsEIH16TTfR'

ALLOWED_EXTENSIONS = {'xml'}

# =============================================================================
# Google API Setup
# =============================================================================

def get_google_sheets_client():
    """Initialize and return Google Sheets client"""
    import os
    import json
    import base64
    
    # Try base64 encoded env var first
    creds_base64 = os.environ.get('GOOGLE_CREDENTIALS_BASE64')
    if creds_base64:
        print("DEBUG: Using base64 encoded credentials")
        creds_json = base64.b64decode(creds_base64).decode('utf-8')
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        # Fallback to JSON env var
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
    import base64
    
    # Get credentials
    creds_base64 = os.environ.get('GOOGLE_CREDENTIALS_BASE64')
    
    if creds_base64:
        print("DEBUG: Using base64 for Drive API")
        creds_json = base64.b64decode(creds_base64).decode('utf-8')
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file('service-account.json', scopes=SCOPES)
    
    return build('drive', 'v3', credentials=creds)

# Initialize clients
try:
    gc = get_google_sheets_client()
    sheet = gc.open_by_key(GOOGLE_SHEET_ID)
    scenarios_sheet = sheet.worksheet('Scenarios')
    inputs_sheet = sheet.worksheet('InputFiles')
    junction_sheet = sheet.worksheet('ScenarioInputs')
    
    # FileStorage sheet for storing XML content
    try:
        file_storage_sheet = sheet.worksheet('FileStorage')
    except:
        # Create if doesn't exist
        file_storage_sheet = sheet.add_worksheet(title='FileStorage', rows=1000, cols=3)
        file_storage_sheet.append_row(['file_id', 'filename', 'content'])
    
    print("✓ Google Sheets connection successful")
except Exception as e:
    print(f"✗ Error initializing Google APIs: {e}")
    print("⚠ App will start but Google Sheets features will be unavailable")
    gc = None
    scenarios_sheet = None
    inputs_sheet = None
    junction_sheet = None
    file_storage_sheet = None

# =============================================================================
# Helper Functions - Google Sheets
# =============================================================================

def sheets_available():
    """Check if Google Sheets connection is available"""
    return scenarios_sheet is not None

# Simple in-memory cache to speed up page loads
_cache = {'data': None, 'timestamp': 0}
CACHE_TTL = 30  # seconds

def get_cached_data():
    """Get all sheet data with caching to reduce API calls"""
    import time
    now = time.time()
    if _cache['data'] and (now - _cache['timestamp']) < CACHE_TTL:
        return _cache['data']
    
    try:
        scenarios = scenarios_sheet.get_all_records()
        junctions = junction_sheet.get_all_records()
        inputs = inputs_sheet.get_all_records()
        _cache['data'] = {'scenarios': scenarios, 'junctions': junctions, 'inputs': inputs}
        _cache['timestamp'] = now
        return _cache['data']
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def invalidate_cache():
    """Clear cache after writes"""
    _cache['data'] = None
    _cache['timestamp'] = 0

def compute_duration(submitted_str, finished_str):
    """Compute duration between two datetime strings"""
    try:
        # Try various formats
        for fmt in ['%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M', '%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S']:
            try:
                t1 = datetime.strptime(submitted_str.strip(), fmt)
                t2 = datetime.strptime(finished_str.strip(), fmt)
                diff = t2 - t1
                total_minutes = int(diff.total_seconds() / 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                if hours > 0:
                    return f"{hours}h {minutes}m"
                return f"{minutes}m"
            except ValueError:
                continue
        return ''
    except:
        return ''

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
# Helper Functions - File Storage (in Sheets)
# =============================================================================

def upload_file_to_sheet(file_content, filename):
    """Store file content in Google Sheets and return file ID"""
    try:
        file_id = get_next_id(file_storage_sheet)
        file_storage_sheet.append_row([
            file_id,
            filename,
            file_content
        ])
        print(f"DEBUG: Stored file {filename} in Sheets, ID: {file_id}")
        return str(file_id)
    except Exception as e:
        print(f"Error storing file in Sheets: {e}")
        return None

def download_file_from_sheet(file_id):
    """Download file content from Google Sheets"""
    try:
        # Find row with matching file_id
        cell = file_storage_sheet.find(str(file_id), in_column=1)
        if cell:
            row_data = file_storage_sheet.row_values(cell.row)
            return row_data[2] if len(row_data) > 2 else None
        return None
    except Exception as e:
        print(f"Error downloading file from Sheets: {e}")
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
            
            # Extract folder location - everything between "input/" and the filename
            # Examples: 
            #   ../input/gcamdata/xml/file.xml → gcamdata/xml
            #   ../input/policyAI/file.xml → policyAI
            #   input/policyAI/file.xml → policyAI
            #   input/magicc/inputs/file.emk → magicc/inputs
            folder_location = ''
            if '/input/' in file_path:
                # Handle paths like ../input/xxx or /input/xxx
                parts = file_path.split('/input/', 1)
                if len(parts) > 1:
                    after_input = parts[1]
                    folder_parts = after_input.split('/')[:-1]  # Remove filename
                    folder_location = '/'.join(folder_parts)
            elif file_path.startswith('input/'):
                # Handle paths starting with input/
                after_input = file_path[6:]  # Remove 'input/'
                folder_parts = after_input.split('/')[:-1]  # Remove filename
                folder_location = '/'.join(folder_parts)
            
            result['input_files'].append({
                'file_name': file_name,
                'file_path': file_path,
                'folder_location': folder_location,
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

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    status = {
        'status': 'ok',
        'sheets_connected': sheets_available()
    }
    return jsonify(status)

@app.route('/')
def index():
    """Main dashboard"""
    if not sheets_available():
        flash('Google Sheets connection unavailable. Please try again in a moment.', 'warning')
        return render_template('index.html',
                             scenarios=[],
                             input_files=[],
                             projects=[])
    
    # Use cached data to reduce API calls (3 calls -> 0 on cache hit)
    cached = get_cached_data()
    if not cached:
        flash('Error loading data. Please refresh.', 'warning')
        return render_template('index.html', scenarios=[], input_files=[], projects=[])
    
    scenarios = cached['scenarios']
    junction_records = cached['junctions']
    input_files = cached['inputs']
    
    # Compute counts and durations
    for record in scenarios:
        record['input_count'] = sum(1 for j in junction_records if str(j.get('scenario_id')) == str(record.get('id')))
        # Compute duration if submitted and finished exist
        submitted = str(record.get('submitted', ''))
        finished = str(record.get('finished', ''))
        if submitted and finished:
            record['duration'] = compute_duration(submitted, finished)
        else:
            record['duration'] = ''
    
    for record in input_files:
        record['scenario_count'] = sum(1 for j in junction_records if str(j.get('input_file_id')) == str(record.get('id')))
    
    # Get unique projects for dropdown
    projects = sorted(set([s.get('project_name', '') for s in scenarios if s.get('project_name')]))
    
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
    uploaded_by = request.form.get('uploaded_by', '')  # Empty by default
    
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
        
        # Store in Google Sheets
        file_id = upload_file_to_sheet(file_content, filename)
        
        if not file_id:
            flash('Error storing file', 'error')
            return redirect(url_for('index'))
        
        # Parse configuration
        parsed = parse_configuration_xml(file_content)
        
        # Add scenario to sheet with UUID
        scenario_id = str(uuid.uuid4())[:8]  # Short unique ID (8 chars)
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
            len(parsed['input_files']),
            '',  # errors (col 13)
            '',  # submitted (col 14)
            '',  # finished (col 15)
            '',  # job_id (col 16)
            ''   # duration (col 17)
        ])
        
        # Process input files in batch to avoid rate limits
        # First, get all existing input file names in one call
        existing_files = {}
        try:
            all_inputs = inputs_sheet.get_all_records()
            for inp in all_inputs:
                existing_files[inp['file_name']] = inp['id']
        except:
            pass
        
        # Prepare batch data for new files and junctions
        new_files_to_add = []
        junctions_to_add = []
        next_input_id = get_next_id(inputs_sheet)
        
        for input_file in parsed['input_files']:
            # Check if exists
            if input_file['file_name'] in existing_files:
                input_id = existing_files[input_file['file_name']]
            else:
                # Prepare to add new
                input_id = next_input_id
                new_files_to_add.append([
                    input_id,
                    input_file['file_name'],
                    'Not analyzed',
                    'Not analyzed',
                    'Not analyzed',
                    '',  # policy_name
                    input_file.get('folder_location', ''),  # folder_location from config
                    '',  # description
                    '',  # additional_notes
                    'Auto-detected',
                    upload_date,
                    ''   # file_id
                ])
                existing_files[input_file['file_name']] = input_id
                next_input_id += 1
            
            # Prepare junction
            junctions_to_add.append([
                scenario_id,
                input_id,
                input_file['component_key']
            ])
        
        # Batch add new input files (single API call)
        if new_files_to_add:
            inputs_sheet.append_rows(new_files_to_add)
        
        # Batch add junctions (single API call)
        if junctions_to_add:
            junction_sheet.append_rows(junctions_to_add)
        
        flash(f'Successfully uploaded scenario "{parsed["scenario_name"]}" with {len(parsed["input_files"])} input files', 'success')
        invalidate_cache()
        
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
        
        # Parse input file (but don't store the content - just metadata)
        parsed = parse_input_file_xml(file_content)
        
        upload_date = datetime.now().isoformat()
        
        # Check if file already exists
        existing_row = find_row_by_value(inputs_sheet, 'file_name', filename)
        
        if existing_row:
            # Update existing record (no file storage)
            inputs_sheet.update_cell(existing_row, 3, parsed['regions'])
            inputs_sheet.update_cell(existing_row, 4, parsed['years'])
            inputs_sheet.update_cell(existing_row, 5, parsed['sectors'])
            inputs_sheet.update_cell(existing_row, 10, uploaded_by)
            inputs_sheet.update_cell(existing_row, 11, upload_date)
            # Leave file_id empty for input files
            flash(f'Updated input file metadata "{filename}" (file not stored)', 'success')
        else:
            # Create new record (no file storage)
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
                ''   # file_id (empty - not storing file)
            ])
            flash(f'Added input file metadata "{filename}" (file not stored)', 'success')
        
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/update_scenario/<scenario_id>', methods=['POST'])
def update_scenario(scenario_id):
    """Update scenario metadata"""
    try:
        row = find_row_by_value(scenarios_sheet, 'id', scenario_id)
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
        if 'uploaded_by' in data:
            scenarios_sheet.update_cell(row, 9, data['uploaded_by'])
        # New Zaratan columns (13-17)
        if 'errors' in data:
            scenarios_sheet.update_cell(row, 13, data['errors'])
        if 'submitted' in data:
            scenarios_sheet.update_cell(row, 14, data['submitted'])
            # Recompute duration if both submitted and finished exist
            try:
                row_data = scenarios_sheet.row_values(row)
                finished = row_data[14] if len(row_data) > 14 else ''
                if data['submitted'] and finished:
                    duration = compute_duration(data['submitted'], finished)
                    scenarios_sheet.update_cell(row, 17, duration)
            except: pass
        if 'finished' in data:
            scenarios_sheet.update_cell(row, 15, data['finished'])
            # Recompute duration
            try:
                row_data = scenarios_sheet.row_values(row)
                submitted = row_data[13] if len(row_data) > 13 else ''
                if submitted and data['finished']:
                    duration = compute_duration(submitted, data['finished'])
                    scenarios_sheet.update_cell(row, 17, duration)
            except: pass
        if 'job_id' in data:
            scenarios_sheet.update_cell(row, 16, data['job_id'])
        
        invalidate_cache()
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

@app.route('/scenario/<scenario_id>')
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
    
    # Note: Input files are not stored, only metadata
    # Comparison not available for input files
    diff_html = None
    
    return render_template('compare.html', 
                         file1=file1, 
                         file2=file2, 
                         diff_html=diff_html,
                         message="Input file contents are not stored. Only metadata is tracked.")

@app.route('/download/<path:file_type>/<file_id>')
def download_file(file_type, file_id):
    """Download a file from Google Sheets"""
    try:
        if file_type == 'config':
            scenario = get_scenario_by_id(file_id)
            if not scenario or not scenario.get('config_file_id'):
                flash('File not found', 'error')
                return redirect(url_for('index'))
            
            sheet_file_id = scenario['config_file_id']
            filename = f"{scenario['scenario_name']}.xml"
            
            # Download from Sheets
            content = download_file_from_sheet(sheet_file_id)
            
            if not content:
                flash('Error downloading file', 'error')
                return redirect(url_for('index'))
            
            # Return file
            return Response(
                content,
                mimetype='application/xml',
                headers={'Content-Disposition': f'attachment;filename={filename}'}
            )
        
        elif file_type == 'input':
            # Input files are not stored
            flash('Input files are not stored. Only metadata is tracked.', 'info')
            return redirect(url_for('index'))
        else:
            flash('Invalid file type', 'error')
            return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/migrate_folder_locations')
def migrate_folder_locations():
    """One-time migration to populate folder_location for existing input files"""
    if not sheets_available():
        return jsonify({'error': 'Sheets not available'}), 503
    
    try:
        # Get all scenarios with their config files
        scenarios = scenarios_sheet.get_all_records()
        input_records = inputs_sheet.get_all_records()
        
        # Build a complete map of filename -> folder_location from all configs
        file_folder_map = {}
        
        for scenario in scenarios:
            config_file_id = scenario.get('config_file_id')
            if not config_file_id:
                continue
            
            # Get the config file content
            config_content = download_file_from_sheet(config_file_id)
            if not config_content:
                continue
            
            # Parse it
            try:
                parsed = parse_configuration_xml(config_content)
                
                # Add to map (later configs will override if same filename)
                for input_file in parsed['input_files']:
                    file_folder_map[input_file['file_name']] = input_file.get('folder_location', '')
            except Exception as e:
                print(f"Error parsing config for scenario {scenario.get('id')}: {e}")
                continue
        
        # Now update all input files using individual updates (slower but safer)
        updated_count = 0
        
        for i, input_rec in enumerate(input_records, start=2):  # Start at row 2 (after header)
            file_name = input_rec['file_name']
            if file_name in file_folder_map:
                folder_loc = file_folder_map[file_name]
                # Update column 7 (folder_location)
                try:
                    inputs_sheet.update_cell(i, 7, folder_loc)
                    updated_count += 1
                    
                    # Add small delay every 50 updates to avoid rate limits
                    if updated_count % 50 == 0:
                        print(f"Updated {updated_count} files, pausing briefly...")
                        import time
                        time.sleep(2)  # 2 second pause
                except Exception as e:
                    print(f"Error updating row {i}: {e}")
                    continue
        
        return jsonify({
            'status': 'success',
            'message': f'Updated folder locations for {updated_count} input files'
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Migration error: {error_details}")
        return jsonify({'error': str(e), 'details': error_details}), 500

@app.route('/test_compare')
def test_compare():
    """Test endpoint to verify routing works"""
    return jsonify({'status': 'ok', 'message': 'Comparison routing is working!'})

@app.route('/add_zaratan_columns')
def add_zaratan_columns():
    """One-time migration to add new Zaratan columns to Scenarios sheet"""
    if not sheets_available():
        return jsonify({'error': 'Sheets not available'}), 503
    try:
        headers = scenarios_sheet.row_values(1)
        new_cols = ['errors', 'submitted', 'finished', 'job_id', 'duration']
        added = []
        for col in new_cols:
            if col not in headers:
                next_col = len(headers) + 1
                scenarios_sheet.update_cell(1, next_col, col)
                headers.append(col)
                added.append(col)
        return jsonify({'status': 'success', 'added_columns': added, 'all_headers': headers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/compare_scenarios', strict_slashes=False)
def compare_scenarios():
    """Compare multiple scenarios and generate a report"""
    try:
        print("DEBUG: Compare scenarios route called")
        print(f"DEBUG: Request args: {request.args}")
        scenario_ids = request.args.get('ids', '').split(',')
        print(f"DEBUG: Scenario IDs: {scenario_ids}")
        
        if len(scenario_ids) < 2:
            flash('Please select at least 2 scenarios to compare', 'error')
            return redirect(url_for('index'))
        
        if not sheets_available():
            flash('Google Sheets connection unavailable', 'error')
            return redirect(url_for('index'))
        
        # Get all scenarios
        scenarios = []
        for scenario_id in scenario_ids:
            print(f"DEBUG: Getting scenario {scenario_id}")
            scenario = get_scenario_by_id(scenario_id)
            if scenario:
                # Get input files for this scenario
                input_files = get_input_files_for_scenario(scenario_id)
                scenario['input_file_names'] = set([f['file_name'] for f in input_files])
                scenarios.append(scenario)
                print(f"DEBUG: Found scenario with {len(input_files)} input files")
            else:
                print(f"DEBUG: Scenario {scenario_id} not found")
        
        if len(scenarios) < 2:
            flash('Could not find all selected scenarios', 'error')
            return redirect(url_for('index'))
        
        # Generate comparison report
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("GCAM SCENARIO COMPARISON REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Number of scenarios compared: {len(scenarios)}")
        report_lines.append("")
        
        # Section 1: Scenario Overview
        report_lines.append("-" * 80)
        report_lines.append("SCENARIO OVERVIEW")
        report_lines.append("-" * 80)
        for i, scenario in enumerate(scenarios, 1):
            report_lines.append(f"\n{i}. {scenario['scenario_name']}")
            report_lines.append(f"   ID: {scenario['id']}")
            if scenario.get('project_name'):
                report_lines.append(f"   Project: {scenario['project_name']}")
            if scenario.get('date_run'):
                report_lines.append(f"   Date Run: {scenario['date_run']}")
            report_lines.append(f"   Number of Input Files: {len(scenario['input_file_names'])}")
            if scenario.get('description'):
                report_lines.append(f"   Description: {scenario['description']}")
        
        report_lines.append("")
        
        # Section 2: Input Files Comparison - UNIQUE FILES FIRST
        report_lines.append("-" * 80)
        report_lines.append("INPUT FILES COMPARISON")
        report_lines.append("-" * 80)
        
        # Get all unique files across all scenarios
        all_files = set()
        for scenario in scenarios:
            all_files.update(scenario['input_file_names'])
        
        # Files shared by ALL scenarios
        shared_files = set.intersection(*[s['input_file_names'] for s in scenarios])
        
        report_lines.append(f"\nTotal unique input files across all scenarios: {len(all_files)}")
        report_lines.append(f"Files shared by ALL scenarios: {len(shared_files)}")
        
        # UNIQUE FILES FIRST (moved up)
        report_lines.append("\n" + "-" * 80)
        report_lines.append("UNIQUE FILES PER SCENARIO")
        report_lines.append("-" * 80)
        
        for scenario in scenarios:
            unique_files = scenario['input_file_names'] - shared_files
            other_files = set()
            for other in scenarios:
                if other['id'] != scenario['id']:
                    other_files.update(other['input_file_names'])
            
            truly_unique = scenario['input_file_names'] - other_files
            
            report_lines.append(f"\n{scenario['scenario_name']}:")
            report_lines.append(f"  Files NOT in common set: {len(unique_files)}")
            report_lines.append(f"  Files ONLY in this scenario: {len(truly_unique)}")
            
            if truly_unique:
                report_lines.append("  Unique files:")
                for file in sorted(truly_unique):
                    report_lines.append(f"    - {file}")
        
        # SHARED FILES AFTER (moved down)
        report_lines.append("\n" + "-" * 80)
        report_lines.append("SHARED FILES")
        report_lines.append("-" * 80)
        
        if shared_files:
            report_lines.append(f"\nFiles present in ALL {len(scenarios)} scenarios ({len(shared_files)} total):")
            for file in sorted(shared_files):
                report_lines.append(f"  - {file}")
        else:
            report_lines.append("\nNo files are shared by all scenarios.")
        
        # Section 3: File-by-File Matrix
        report_lines.append("\n" + "-" * 80)
        report_lines.append("FILE PRESENCE MATRIX")
        report_lines.append("-" * 80)
        report_lines.append("\nLegend: ✓ = Present, ✗ = Absent\n")
        
        # Create header
        header = "File Name".ljust(50)
        for i, scenario in enumerate(scenarios, 1):
            header += f"  S{i}"
        report_lines.append(header)
        report_lines.append("-" * len(header))
        
        # Add each file
        for file in sorted(all_files):
            line = file[:48].ljust(50)
            for scenario in scenarios:
                if file in scenario['input_file_names']:
                    line += "  ✓ "
                else:
                    line += "  ✗ "
            report_lines.append(line)
        
        # Section 4: Summary Statistics
        report_lines.append("\n" + "-" * 80)
        report_lines.append("SUMMARY STATISTICS")
        report_lines.append("-" * 80)
        
        for i, scenario in enumerate(scenarios, 1):
            overlap_counts = []
            for j, other in enumerate(scenarios, 1):
                if i != j:
                    overlap = len(scenario['input_file_names'] & other['input_file_names'])
                    total = len(scenario['input_file_names'] | other['input_file_names'])
                    if total > 0:
                        percentage = (overlap / total) * 100
                        overlap_counts.append(f"S{j}: {percentage:.1f}%")
            
            report_lines.append(f"\nS{i} ({scenario['scenario_name']}) overlap with others:")
            report_lines.append(f"  {', '.join(overlap_counts)}")
        
        report_lines.append("\n" + "=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)
        
        # =====================================================================
        # Generate XLSX comparison spreadsheet (2 sheets)
        # =====================================================================
        import io
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        wb = Workbook()
        
        # Build file -> folder map and file -> scenarios map
        file_folder_map = {}
        file_scenario_map = {}
        
        # Get folder info from input files sheet
        try:
            all_inputs = inputs_sheet.get_all_records()
            for inp in all_inputs:
                file_folder_map[inp.get('file_name', '')] = inp.get('folder_location', '')
        except:
            pass
        
        scenario_names_list = [s['scenario_name'] for s in scenarios]
        
        for scenario in scenarios:
            for file_name in scenario['input_file_names']:
                if file_name not in file_scenario_map:
                    file_scenario_map[file_name] = set()
                file_scenario_map[file_name].add(scenario['scenario_name'])
        
        # Sort files A-Z
        all_files_sorted = sorted(file_scenario_map.keys())
        
        # --- Sheet 1: Presence Matrix (like R script output) ---
        ws1 = wb.active
        ws1.title = "Presence Matrix"
        
        # Styles
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill("solid", fgColor="991B1B")  # Dark red
        present_fill = PatternFill("solid", fgColor="D1FAE5")  # Light green
        absent_fill = PatternFill("solid", fgColor="FEE2E2")   # Light red
        border = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='thin', color='D1D5DB')
        )
        center_align = Alignment(horizontal='center', vertical='center')
        
        # Headers
        headers = ["File Name", "Folder"] + scenario_names_list
        for col, header in enumerate(headers, 1):
            cell = ws1.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
        
        # Data rows
        for row_idx, file_name in enumerate(all_files_sorted, 2):
            folder = file_folder_map.get(file_name, '')
            present_in = file_scenario_map.get(file_name, set())
            
            # File name
            cell = ws1.cell(row=row_idx, column=1, value=file_name)
            cell.border = border
            
            # Folder
            cell = ws1.cell(row=row_idx, column=2, value=folder)
            cell.border = border
            
            # Scenario presence (1/0 with conditional formatting)
            for sc_idx, sc_name in enumerate(scenario_names_list, 3):
                is_present = sc_name in present_in
                cell = ws1.cell(row=row_idx, column=sc_idx, value=1 if is_present else 0)
                cell.alignment = center_align
                cell.border = border
                cell.fill = present_fill if is_present else absent_fill
                cell.font = Font(bold=True, color="065F46" if is_present else "991B1B")
        
        # Summary row at bottom
        summary_row = len(all_files_sorted) + 3
        ws1.cell(row=summary_row, column=1, value="TOTAL FILES").font = Font(bold=True)
        for sc_idx, sc_name in enumerate(scenario_names_list, 3):
            count = sum(1 for f in all_files_sorted if sc_name in file_scenario_map.get(f, set()))
            cell = ws1.cell(row=summary_row, column=sc_idx, value=count)
            cell.font = Font(bold=True)
            cell.alignment = center_align
        
        # Column widths
        ws1.column_dimensions['A'].width = 40
        ws1.column_dimensions['B'].width = 20
        for i in range(3, 3 + len(scenario_names_list)):
            from openpyxl.utils import get_column_letter
            ws1.column_dimensions[get_column_letter(i)].width = max(15, len(scenario_names_list[i-3]) + 4)
        
        # Freeze top row
        ws1.freeze_panes = 'A2'
        
        # --- Sheet 2: Summary (unique/shared with status) ---
        ws2 = wb.create_sheet("Summary")
        
        # Headers
        summary_headers = ["File Name", "Folder", "Status", "Present In"]
        for col, header in enumerate(summary_headers, 1):
            cell = ws2.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
        
        # Unique files first, then shared
        unique_fill = PatternFill("solid", fgColor="FEF3C7")  # Light yellow
        shared_fill = PatternFill("solid", fgColor="DBEAFE")   # Light blue
        
        current_row = 2
        total_scenarios = len(scenarios)
        
        # Unique files first
        for file_name in all_files_sorted:
            present_in = file_scenario_map.get(file_name, set())
            if len(present_in) < total_scenarios:
                folder = file_folder_map.get(file_name, '')
                
                if len(present_in) == 1:
                    status = f"Unique to {list(present_in)[0]}"
                else:
                    status = f"In {len(present_in)} of {total_scenarios} scenarios"
                
                present_str = "; ".join(sorted(present_in))
                
                ws2.cell(row=current_row, column=1, value=file_name).border = border
                ws2.cell(row=current_row, column=2, value=folder).border = border
                cell = ws2.cell(row=current_row, column=3, value=status)
                cell.border = border
                cell.fill = unique_fill
                ws2.cell(row=current_row, column=4, value=present_str).border = border
                current_row += 1
        
        # Separator row
        sep_cell = ws2.cell(row=current_row, column=1, value=f"--- SHARED FILES ({len(shared_files)} files in all {total_scenarios} scenarios) ---")
        sep_cell.font = Font(bold=True, color="1E40AF")
        current_row += 1
        
        # Shared files
        for file_name in sorted(shared_files):
            folder = file_folder_map.get(file_name, '')
            present_str = "; ".join(scenario_names_list)
            
            ws2.cell(row=current_row, column=1, value=file_name).border = border
            ws2.cell(row=current_row, column=2, value=folder).border = border
            cell = ws2.cell(row=current_row, column=3, value="Shared by all")
            cell.border = border
            cell.fill = shared_fill
            ws2.cell(row=current_row, column=4, value=present_str).border = border
            current_row += 1
        
        # Column widths
        ws2.column_dimensions['A'].width = 40
        ws2.column_dimensions['B'].width = 20
        ws2.column_dimensions['C'].width = 30
        ws2.column_dimensions['D'].width = 50
        ws2.freeze_panes = 'A2'
        
        # Save to buffer
        xlsx_buffer = io.BytesIO()
        wb.save(xlsx_buffer)
        xlsx_buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return Response(
            xlsx_buffer.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment;filename=scenario_comparison_{timestamp}.xlsx'}
        )
        
    except Exception as e:
        import traceback
        print(f"Comparison error: {traceback.format_exc()}")
        flash(f'Error comparing scenarios: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/delete_scenario/<scenario_id>', methods=['POST'])
def delete_scenario(scenario_id):
    """Delete a scenario and its junction records"""
    try:
        if not sheets_available():
            return jsonify({'success': False, 'error': 'Sheets unavailable'})
        
        # Find scenario row
        scenario_row = find_row_by_value(scenarios_sheet, 'id', scenario_id)
        
        if not scenario_row:
            return jsonify({'success': False, 'error': 'Scenario not found'})
        
        # Get config_file_id before deleting
        scenario_data = scenarios_sheet.row_values(scenario_row)
        config_file_id = scenario_data[10] if len(scenario_data) > 10 else None
        
        # Delete from FileStorage if config exists
        if config_file_id:
            try:
                file_row = find_row_by_value(file_storage_sheet, 'file_id', config_file_id)
                if file_row:
                    file_storage_sheet.delete_rows(file_row)
                    print(f"Deleted file {config_file_id} from storage")
            except Exception as e:
                print(f"Error deleting file from storage: {e}")
        
        # Delete scenario row
        scenarios_sheet.delete_rows(scenario_row)
        print(f"Deleted scenario row {scenario_row}")
        
        # Delete junction records - Get all and filter in Python to minimize API calls
        try:
            all_junctions = junction_sheet.get_all_records()
            rows_to_delete = []
            
            for idx, record in enumerate(all_junctions, start=2):  # Start at 2 (skip header)
                if str(record.get('scenario_id')) == str(scenario_id):
                    rows_to_delete.append(idx)
            
            # Delete in reverse order to maintain row numbers (but limit to avoid rate limit)
            deleted_count = 0
            for row_num in reversed(rows_to_delete[:10]):  # Only delete first 10 junctions to avoid rate limit
                junction_sheet.delete_rows(row_num)
                deleted_count += 1
            
            print(f"Deleted {deleted_count} junction records")
            
            # If there are more than 10, warn the user
            if len(rows_to_delete) > 10:
                return jsonify({
                    'success': True, 
                    'warning': f'Scenario deleted but some junction records remain (deleted {deleted_count} of {len(rows_to_delete)}). They won\'t affect the app.'
                })
                
        except Exception as e:
            print(f"Error deleting junctions: {e}")
            # Continue anyway - scenario is deleted
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error deleting scenario: {e}")
        invalidate_cache()
        return jsonify({'success': False, 'error': str(e)})

# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
