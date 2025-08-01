from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response, make_response, send_file
import csv
import os
import base64
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import uuid
import shutil
import glob
import re
import io
from io import StringIO, BytesIO
import json
import pandas as pd
import traceback

app = Flask(__name__)

# Define the function first
def ensure_tournament_directories():
    """Ensure the required directory structure exists for tournament files"""
    # Create static directory if it doesn't exist
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # Create tournaments directory if it doesn't exist
    tournaments_dir = os.path.join('static', 'tournaments')
    if not os.path.exists(tournaments_dir):
        os.makedirs(tournaments_dir)

# Then call the function
ensure_tournament_directories()

# Add this near the top of your app.py file, after app initialization
ensure_tournament_directories()

# Add custom datetime filter
@app.template_filter('datetime')
def format_datetime(value, format='%Y-%m-%d'):
    if value:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.strftime('%d-%m-%y')
        except:
            return value
    return value

# Define the CSV file paths with absolute paths
PLAYERS_CSV = os.path.join(os.getcwd(), 'players_data.csv')
print(f"Players CSV file path: {PLAYERS_CSV}")  # Debug print

TOURNAMENTS_CSV = 'tournaments.csv'
TOURNAMENT_REGISTRATIONS_CSV = 'tournament_registrations.csv'

# Add this if not already present
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'logo')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_image_base64():
    image_path = os.path.join('static', 'tt_facility.jpg')
    try:
        with open(image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{image_data}"
    except Exception as e:
        print(f"Error reading image: {e}")
        return None

def initialize_csv():
    # Initialize tournaments.csv if it doesn't exist
    if not os.path.exists('tournaments.csv'):
        with open('tournaments.csv', 'w', newline='', encoding='utf-8') as file:
            fieldnames = [
                'Tournament Id', 'Tournament Name', 'Categories', 'Venue',
                'Start Date', 'End Date', 'Last Registration Date', 'Total Prize',
                'General Information', 'Tournament Logo Link', 'Status',
                'Bank Account', 'UPI Link', 'Payment QR'
            ]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

def initialize_tournament_registrations_csv():
    """Initialize the tournament registrations CSV file with correct headers if it doesn't exist"""
    fieldnames = [
        'Tournament Id',  # Standardized field name
        'Player ID',      # Changed from 'Player Id' to match the code
        'Registration Date',
        'Category',
        'Status',
        'Seeding'
    ]
    
    if not os.path.exists(TOURNAMENT_REGISTRATIONS_CSV):
        with open(TOURNAMENT_REGISTRATIONS_CSV, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
    return fieldnames

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        # Add your authentication logic here
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    
    image_data = get_image_base64()
    return render_template('login.html', image_data=image_data)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', active_page='dashboard')

@app.route('/players', methods=['GET', 'POST'])
def player_registration():
    if request.method == 'POST':
        try:
            print("\n=== Starting Player Registration Process ===")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Players CSV path: {PLAYERS_CSV}")

            # Get form data
            form_data = request.form.to_dict()
            print(f"Received form data: {form_data}")

            # Get file data
            files = request.files
            print(f"Received files: {[f for f in files]}")

            player_name = form_data.get('player_name', '').strip()
            date_of_birth = form_data.get('date_of_birth', '').strip()
            gender = form_data.get('gender', '').strip()
            phone = form_data.get('phone', '').strip()
            email = form_data.get('email', '').strip()
            address = form_data.get('address', '').strip()
            state = form_data.get('state', '').strip()
            ttfi_id = form_data.get('ttfi_id', '').strip()
            official_state_id = form_data.get('official_state_id', '').strip()
            institution = form_data.get('institution', '').strip()
            academy = form_data.get('academy', '').strip()
            district = form_data.get('district', '').strip()
            
            # Bank details
            account_holder_name = form_data.get('account_holder_name', '').strip()
            account_number = form_data.get('account_number', '').strip()
            bank_name = form_data.get('bank_name', '').strip()
            branch_name = form_data.get('branch_name', '').strip()
            ifsc_code = form_data.get('ifsc_code', '').strip()
            upi_id = form_data.get('upi_id', '').strip()

            # Payment details
            payment_snapshot = request.files.get('payment_snapshot')
            transaction_id = form_data.get('transaction_id', '').strip()
            do_state_registration = form_data.get('do_state_registration') == 'on'
            is_state_transfer = form_data.get('is_state_transfer') == 'on'
            noc_certificate = request.files.get('noc_certificate')

            # Handle file uploads
            photo = request.files.get('photo')
            birth_certificate = request.files.get('birth_certificate')
            address_proof = request.files.get('address_proof')

            print("\nValidating form data...")
            # Basic validation
            if not all([player_name, date_of_birth, gender, phone]):
                raise ValueError("All required fields must be filled out")

            if not phone.isdigit() or len(phone) != 10:
                raise ValueError("Please enter a valid 10-digit phone number")

            if not all(c.isalpha() or c.isspace() for c in player_name):
                raise ValueError("Name should only contain letters and spaces")

            # Additional validation for state transfer
            if do_state_registration and is_state_transfer and not noc_certificate:
                raise ValueError("NOC certificate is required for state transfer")

            # Additional validation for state registration documents
            if do_state_registration:
                if not photo or not photo.filename:
                    raise ValueError("Photo is required for state registration")
                if not birth_certificate or not birth_certificate.filename:
                    raise ValueError("Birth Certificate is required for state registration")
                if not address_proof or not address_proof.filename:
                    raise ValueError("Address Proof is required for state registration")

            print("\nGenerating Player ID...")
            # Generate Player ID
            player_id = generate_new_player_id(date_of_birth)
            print(f"Generated Player ID: {player_id}")

            # Generate Official State ID only if state registration is checked
            official_state_id = ''
            if do_state_registration:
                official_state_id = player_id.replace('-', '')
                if state == 'Delhi':
                    official_state_id = 'DL' + official_state_id
                print(f"Generated Official State ID: {official_state_id}")

            print("\nCreating uploads directory...")
            # Create uploads directory if it doesn't exist
            uploads_dir = os.path.join('static', 'uploads', 'players', player_id)
            os.makedirs(uploads_dir, exist_ok=True)
            print(f"Created directory: {uploads_dir}")

            # Initialize file paths
            photo_path = ''
            birth_cert_path = ''
            address_proof_path = ''
            payment_snapshot_path = ''
            noc_certificate_path = ''

            print("\nSaving uploaded files...")
            # Save uploaded files if provided
            if photo and photo.filename:
                photo_path = os.path.join(uploads_dir, 'photo' + os.path.splitext(photo.filename)[1])
                photo.save(photo_path)
                photo_path = os.path.join('uploads', 'players', player_id, 'photo' + os.path.splitext(photo.filename)[1])
                print(f"Saved photo: {photo_path}")

            if birth_certificate and birth_certificate.filename:
                birth_cert_path = os.path.join(uploads_dir, 'birth_certificate' + os.path.splitext(birth_certificate.filename)[1])
                birth_certificate.save(birth_cert_path)
                birth_cert_path = os.path.join('uploads', 'players', player_id, 'birth_certificate' + os.path.splitext(birth_certificate.filename)[1])
                print(f"Saved birth certificate: {birth_cert_path}")

            if address_proof and address_proof.filename:
                address_proof_path = os.path.join(uploads_dir, 'address_proof' + os.path.splitext(address_proof.filename)[1])
                address_proof.save(address_proof_path)
                address_proof_path = os.path.join('uploads', 'players', player_id, 'address_proof' + os.path.splitext(address_proof.filename)[1])
                print(f"Saved address proof: {address_proof_path}")

            if payment_snapshot and payment_snapshot.filename:
                payment_snapshot_path = os.path.join(uploads_dir, 'payment_snapshot' + os.path.splitext(payment_snapshot.filename)[1])
                payment_snapshot.save(payment_snapshot_path)
                payment_snapshot_path = os.path.join('uploads', 'players', player_id, 'payment_snapshot' + os.path.splitext(payment_snapshot.filename)[1])
                print(f"Saved payment snapshot: {payment_snapshot_path}")

            if noc_certificate and noc_certificate.filename:
                noc_certificate_path = os.path.join(uploads_dir, 'noc_certificate' + os.path.splitext(noc_certificate.filename)[1])
                noc_certificate.save(noc_certificate_path)
                noc_certificate_path = os.path.join('uploads', 'players', player_id, 'noc_certificate' + os.path.splitext(noc_certificate.filename)[1])
                print(f"Saved NOC certificate: {noc_certificate_path}")

            player_data = {
                'Player ID': player_id,
                'Name': player_name,
                'Date of Birth': date_of_birth,
                'Gender': gender,
                'Phone Number': phone,
                'Email ID': email,
                'State': state,
                'District': district,
                'School/Institution': institution,
                'Academy': academy,
                'Address': address,
                'TTFI ID': ttfi_id,
                'Official State ID': official_state_id,
                'Photo Path': photo_path,
                'Birth Certificate Path': birth_cert_path,
                'Address Proof Path': address_proof_path,
                'Account Holder Name': account_holder_name,
                'Account Number': account_number,
                'Bank Name': bank_name,
                'Branch Name': branch_name,
                'IFSC Code': ifsc_code,
                'UPI ID': upi_id,
                'Payment Snapshot Path': payment_snapshot_path,
                'Transaction ID': transaction_id,
                'State Registration': 'Yes' if do_state_registration else 'No',
                'Is State Transfer': 'Yes' if is_state_transfer else 'No',
                'NOC Certificate Path': noc_certificate_path
            }

            print("\nChecking for existing player...")
            # Check if file exists and if player already exists
            player_exists = False
            if os.path.exists(PLAYERS_CSV):
                with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if (row['Name'].lower() == player_name.lower() and row['Phone Number'] == phone):
                            player_exists = True
                            player_data['Player ID'] = row['Player ID']
                            print(f"Found existing player with ID: {row['Player ID']}")
                            break

            if not player_exists:
                try:
                    print("\nWriting new player to CSV...")
                    # Write to CSV file
                    file_exists = os.path.exists(PLAYERS_CSV)
                    print(f"File exists: {file_exists}")

                    mode = 'a' if file_exists else 'w'
                    print(f"Opening file in mode: {mode}")

                    with open(PLAYERS_CSV, mode, newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=player_data.keys())
                        if not file_exists:
                            print("Writing CSV headers")
                            writer.writeheader()
                        print(f"Writing player data: {player_data}")
                        writer.writerow(player_data)
                        print("Successfully wrote player data to CSV")
                except Exception as e:
                    print(f"Error writing to CSV: {str(e)}")
                    raise

            print("=== Player Registration Process Completed ===\n")
            return render_template('registration_success.html', player_details=player_data)

        except Exception as e:
            print(f"Error in player registration: {str(e)}")
            print(traceback.format_exc())  # Add full traceback
            return render_template('players.html', error=str(e), today_date=datetime.now().strftime('%Y-%m-%d'))

    # For GET request
    return render_template('players.html', today_date=datetime.now().strftime('%Y-%m-%d'))

# Helper function to update seeding in a list of records
# records: list of dicts (player or registration records)
# seeding_map: dict mapping unique key (e.g., Player ID or (Name, Category)) to new seeding value
def update_seeding_in_records(records, seeding_map, key_func, seeding_field='Seeding'):
    """
    Update seeding in records using a mapping and a key function.
    Args:
        records: List of dicts (player or registration records)
        seeding_map: Dict mapping unique key to new seeding value
        key_func: Function(record) -> key used in seeding_map
        seeding_field: Field name for seeding (default 'Seeding')
    Returns:
        Number of updates made
    """
    updates_made = 0
    for rec in records:
        key = key_func(rec)
        if key in seeding_map:
            old_seeding = rec.get(seeding_field, '')
            new_seeding = seeding_map[key]
            if old_seeding != new_seeding:
                rec[seeding_field] = new_seeding
                updates_made += 1
    return updates_made

@app.route('/save-seeding', methods=['POST'])
def save_seeding():
    try:
        category = request.form.get('category')
        print(f"Saving seedings for category: {category}")  # Debug print

        # Read all players
        with open(PLAYERS_CSV, 'r', newline='') as file:
            reader = csv.DictReader(file)
            all_players = list(reader)
            fieldnames = reader.fieldnames
            if 'Seeding' not in fieldnames:
                fieldnames.append('Seeding')

        # Get all form data
        form_data = request.form.to_dict()
        print(f"Received form data: {form_data}")  # Debug print

        # Build seeding map: (player_name, category) -> seeding
        seeding_map = {}
        for key, value in form_data.items():
            if key.startswith('seeding_'):
                index = int(key.split('_')[1])
                player_name = request.form.get(f'player_name_{index}')
                if player_name:
                    seeding_map[(player_name, category)] = value.strip() if value.strip() else ''

        # Use helper to update seedings
        updated_count = update_seeding_in_records(
            all_players,
            seeding_map,
            key_func=lambda rec: (rec.get('Player Name'), rec.get('Category')),
            seeding_field='Seeding'
        )

        print(f"Updated seeding for {updated_count} players")  # Debug print

        # Write back to CSV
        with open(PLAYERS_CSV, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_players)

        return redirect(url_for('update_seeding',
                              category=category,
                              success='true',
                              message=f"Successfully updated seeding for {updated_count} players"))

    except Exception as e:
        print(f"Error in save_seeding: {e}")  # Debug print
        return redirect(url_for('update_seeding',
                              category=category,
                              success='false',
                              message=f"Error saving seeding: {str(e)}"))

def generate_tournament_id():
    # Get current year's last 2 digits
    current_year = str(datetime.now().year)[-2:]
    
    # Read existing tournaments to get the last used number
    last_number = 0
    try:
        with open('tournaments.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Tournament Id'].startswith(current_year):
                    try:
                        number = int(row['Tournament Id'][2:])
                        last_number = max(last_number, number)
                    except ValueError:
                        continue
    except FileNotFoundError:
        pass
    
    # Generate new number
    new_number = last_number + 1
    if new_number > 9999:
        raise ValueError("Maximum tournament limit reached for this year")
    
    # Format the tournament ID
    tournament_id = f"{current_year}{new_number:04d}"
    return tournament_id

@app.route('/create-tournament', methods=['GET', 'POST'])
def create_tournament():
    if request.method == 'POST':
        try:
            # Get category information first
            categories = request.form.getlist('categories[]')
            fees = request.form.getlist('fees[]')
            
            # Validate fees
            for i, fee in enumerate(fees):
                if not fee.strip():
                    category_name = categories[i] if i < len(categories) else f"Category #{i+1}"
                    flash(f'Fee is required for {category_name}', 'error')
                    return redirect(url_for('create_tournament'))
            
            # Generate tournament ID in the format YYXXXX
            tournament_id = generate_tournament_id()
            
            # Get form data
            tournament_name = request.form.get('tournament_name')
            venue = request.form.get('venue')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            last_registration_date = request.form.get('last_registration_date')
            total_prize = request.form.get('total_prize')
            general_info = request.form.get('general_info')
            bank_account = request.form.get('bank_account', '')
            upi_link = request.form.get('upi_link', '')
            payment_qr = ''  # Handle file upload if needed

            # Create tournament directory structure
            tournament_folder = os.path.join('static', 'tournaments', tournament_id)
            if not os.path.exists(tournament_folder):
                os.makedirs(tournament_folder)
            
            # Handle multiple tournament logos
            tournament_logos = request.files.getlist('tournament_logo')
            tournament_logo_links = []
            
            for logo in tournament_logos:
                if logo and logo.filename:
                    # Get the original filename and extension
                    original_filename = os.path.splitext(logo.filename)[0]
                    file_extension = os.path.splitext(logo.filename)[1]
                    # Create new filename with 'logo_' prefix
                    filename = f"logo_{original_filename}{file_extension}"
                    # Make the filename safe by removing any special characters
                    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                    logo_path = os.path.join(tournament_folder, safe_filename)
                    logo.save(logo_path)
                    # Store the relative path for the database
                    logo_link = f"static/tournaments/{tournament_id}/{safe_filename}"
                    tournament_logo_links.append(logo_link)
            
            # Join all logo links with a comma
            tournament_logo_links_str = ','.join(tournament_logo_links)
            
            # Get category information
            categories = request.form.getlist('categories[]')
            fees = request.form.getlist('fees[]')
            first_prizes = request.form.getlist('first_prizes[]')
            second_prizes = request.form.getlist('second_prizes[]')
            third_prizes = request.form.getlist('third_prizes[]')
            formats = request.form.getlist('formats[]')
            
            # Prepare tournament data
            tournament_data = {
                'Tournament Id': tournament_id,
                'Tournament Name': tournament_name,
                'Categories': ','.join(categories),
                'Venue': venue,
                'Start Date': start_date,
                'End Date': end_date,
                'Last Registration Date': last_registration_date,
                'Total Prize': total_prize,
                'General Information': general_info,
                'Tournament Logo Link': tournament_logo_links_str,
                'Status': 'active',
                'Bank Account': bank_account,
                'UPI Link': upi_link,
                'Payment QR': payment_qr
            }
            
            # Save tournament data
            with open('tournaments.csv', 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=tournament_data.keys())
                writer.writerow(tournament_data)
            
            # Save category data
            with open('tournament_categories.csv', 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['Tournament Id', 'Tournament Name', 'Category', 'Fee', 'First Prize', 'Second Prize', 'Third Prize', 'Format'])
                for i in range(len(categories)):
                    writer.writerow({
                        'Tournament Id': tournament_id,
                        'Tournament Name': tournament_name,
                        'Category': categories[i],
                        'Fee': fees[i],
                        'First Prize': first_prizes[i],
                        'Second Prize': second_prizes[i],
                        'Third Prize': third_prizes[i],
                        'Format': formats[i]
                    })
            
            flash('Tournament created successfully!', 'success')
            return redirect(url_for('tournament_info', tournament_id=tournament_id))
            
        except Exception as e:
            flash(f'Error creating tournament: {str(e)}', 'error')
            return redirect(url_for('create_tournament'))
    else:
        # Get categories from config
        categories = get_categories_from_config()
        print("Categories from config:", categories)  # Debug print
        return render_template('tournament_creation.html', 
                             categories=categories,
                             current_year=datetime.now().year)

@app.route('/list-tournament')
def list_tournament():
    search_query = request.args.get('search', '')
    statuses = request.args.getlist('status')
    # Set default filter if none selected
    if not statuses:
        statuses = ['upcoming', 'in-progress']
    try:
        # Read tournament data
        tournaments = []
        with open('tournaments.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip only if status is explicitly "inactive"
                if row.get('Status', '').lower() == 'inactive':
                    continue
                
                # Calculate tournament status
                start_date = datetime.strptime(row['Start Date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(row['End Date'], '%Y-%m-%d').date()
                today = datetime.now().date()
                
                if today < start_date:
                    row['status'] = 'upcoming'
                elif today >= start_date and today <= end_date:
                    row['status'] = 'in-progress'
                else:
                    row['status'] = 'completed'
                
                tournaments.append(row)
        
        # Filter tournaments based on search query
        if search_query:
            search_query = search_query.lower()
            tournaments = [t for t in tournaments if (
                search_query in t['Tournament Name'].lower() or
                search_query in t['Venue'].lower() or
                search_query in t['Categories'].lower()
            )]
        
        # Filter tournaments based on schedule
        if statuses:
            tournaments = [t for t in tournaments if t['status'] in statuses]

        # Read tournament categories
        tournament_categories = {}
        try:
            with open('tournament_categories.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tournament_id = row['Tournament Id']
                    if tournament_id not in tournament_categories:
                        tournament_categories[tournament_id] = []
                    tournament_categories[tournament_id].append(row)
        except FileNotFoundError:
            pass

        return render_template('list_tournament.html', 
                             tournaments=tournaments,
                             tournament_categories=tournament_categories,
                             search_query=search_query,
                             statuses=statuses,
                             current_date=datetime.now().strftime('%Y-%m-%d'))
    except Exception as e:
        return render_template('list_tournament.html', 
                             error=str(e),
                             search_query=search_query,
                             statuses=statuses,
                             current_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/delete-tournament/<tournament_id>', methods=['POST'])
def delete_tournament(tournament_id):
    try:
        # Read all tournaments
        tournaments = []
        with open('tournaments.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            tournaments = list(reader)

        # Find and mark the tournament as inactive
        tournament_found = False
        for tournament in tournaments:
            if tournament['Tournament Id'] == tournament_id:
                tournament['Status'] = 'inactive'
                tournament_found = True
                break
        
        # Write back all tournaments
        with open('tournaments.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tournaments)

        if tournament_found:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Tournament not found'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/tournament/<tournament_id>/edit', methods=['GET', 'POST'])
def edit_tournament(tournament_id):
    if request.method == 'POST':
        try:
            # Get form data
            tournament_name = request.form.get('tournament_name')
            venue = request.form.get('venue')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            last_registration_date = request.form.get('last_registration_date')
            total_prize = request.form.get('total_prize')
            general_info = request.form.get('general_info')
            bank_account = request.form.get('bank_account', '')
            upi_link = request.form.get('upi_link', '')

            # Get the old tournament data for existing logo links and QR
            old_tournament = None
            with open('tournaments.csv', 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['Tournament Id'] == tournament_id:
                        old_tournament = row
                        break

            # Create tournament directory if it doesn't exist
            tournament_folder = os.path.join('static', 'tournaments', tournament_id)
            if not os.path.exists(tournament_folder):
                os.makedirs(tournament_folder)
            
            # Get existing and deleted logos
            existing_logos = request.form.getlist('existing_logos[]')
            deleted_logos = request.form.getlist('deleted_logos[]')
            
            # Initialize logo links list with existing logos that weren't deleted
            tournament_logo_links = [logo for logo in existing_logos if logo not in deleted_logos]
            
            # Handle multiple tournament logos
            tournament_logos = request.files.getlist('tournament_logo')
            
            # Process new logo uploads
            for logo in tournament_logos:
                if logo and logo.filename:
                    # Get the original filename and extension
                    original_filename = os.path.splitext(logo.filename)[0]
                    file_extension = os.path.splitext(logo.filename)[1]
                    # Create new filename with 'logo_' prefix
                    filename = f"logo_{original_filename}{file_extension}"
                    # Make the filename safe by removing any special characters
                    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                    logo_path = os.path.join(tournament_folder, safe_filename)
                    logo.save(logo_path)
                    # Store the relative path for the database
                    logo_link = f"static/tournaments/{tournament_id}/{safe_filename}"
                    tournament_logo_links.append(logo_link)
            
            # Delete removed logo files from the filesystem
            for deleted_logo in deleted_logos:
                try:
                    logo_path = os.path.join('static', deleted_logo.replace('static/', ''))
                    if os.path.exists(logo_path):
                        os.remove(logo_path)
                except Exception as e:
                    print(f"Error deleting logo file {logo_path}: {str(e)}")
            
            # Join all logo links with a comma
            tournament_logo_links_str = ','.join(tournament_logo_links)
            
            # Get category information
            categories = request.form.getlist('categories[]')
            fees = request.form.getlist('fees[]')
            first_prizes = request.form.getlist('first_prizes[]')
            second_prizes = request.form.getlist('second_prizes[]')
            third_prizes = request.form.getlist('third_prizes[]')
            formats = request.form.getlist('formats[]')
            
            # Handle QR code upload and removal
            payment_qr = old_tournament.get('Payment QR', '') if old_tournament else ''
            if 'payment_qr' in request.files:
                qr_file = request.files['payment_qr']
                if qr_file and qr_file.filename:
                    qr_filename = secure_filename(qr_file.filename)
                    qr_path = os.path.join(tournament_folder, qr_filename)
                    qr_file.save(qr_path)
                    payment_qr = f'static/tournaments/{tournament_id}/{qr_filename}'
            # If user removed QR, handle that as well
            if request.form.get('remove_qr') == 'true':
                payment_qr = ''

            # Update tournaments.csv
            tournaments = []
            with open('tournaments.csv', 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['Tournament Id'] == tournament_id:
                        # Update existing tournament record
                        row.update({
                            'Tournament Name': tournament_name,
                            'Categories': ','.join(categories),
                            'Venue': venue,
                            'Start Date': start_date,
                            'End Date': end_date,
                            'Last Registration Date': last_registration_date,
                            'Total Prize': total_prize,
                            'General Information': general_info,
                            'Tournament Logo Link': tournament_logo_links_str,
                            'Status': 'active',
                            'Bank Account': bank_account,
                            'UPI Link': upi_link,
                            'Payment QR': payment_qr
                        })
                    tournaments.append(row)
            
            # Write back to tournaments.csv
            with open('tournaments.csv', 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(tournaments)
            
            # Update tournament_categories.csv
            categories_data = []
            with open('tournament_categories.csv', 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['Tournament Id'] != tournament_id:
                        categories_data.append(row)
            
            # Add updated categories
            for i in range(len(categories)):
                category_data = {
                    'Tournament Id': tournament_id,
                    'Tournament Name': tournament_name,
                    'Category': categories[i],
                    'Fee': fees[i],
                    'First Prize': first_prizes[i],
                    'Second Prize': second_prizes[i],
                    'Third Prize': third_prizes[i],
                    'Format': formats[i]
                }
                categories_data.append(category_data)
            
            # Write back to tournament_categories.csv
            with open('tournament_categories.csv', 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(categories_data)
            
            flash('Tournament updated successfully!', 'success')
            return redirect(url_for('tournament_info', tournament_id=tournament_id))
            
        except Exception as e:
            flash(f'Error updating tournament: {str(e)}', 'error')
            return redirect(url_for('edit_tournament', tournament_id=tournament_id))
    else:
        # Get tournament data
        tournament = get_tournament(tournament_id)
        if not tournament:
            return redirect(url_for('list_tournament'))
        
        # Get category names (for backward compatibility)
        categories = get_tournament_categories(tournament_id)
        
        # Get FULL tournament categories with all details
        full_categories = []
        try:
            with open('tournament_categories.csv', 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['Tournament Id'] == tournament_id:
                        full_categories.append(row)
        except Exception as e:
            print(f"Error reading full tournament categories: {e}")
        
        print("Full categories data:", full_categories)  # Debug print
        
        # Get all available categories from config
        all_categories = get_categories_from_config()
        
        return render_template('edit_tournament.html', 
                             tournament=tournament,
                             categories=categories,
                             full_categories=full_categories,  # Pass full category data
                             all_categories=all_categories,
                             current_year=datetime.now().year)

@app.route('/list-tournament-last2')
def list_tournament_last2():
    tournaments = []
    with open('tournaments.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        # Only active tournaments
        active_tournaments = [row for row in reader if row.get('Status', '').lower() == 'active']
        # Sort by Start Date descending (latest first)
        active_tournaments.sort(key=lambda x: x.get('Start Date', ''), reverse=True)
        # Get last 2
        tournaments = active_tournaments[:2]

    # Load all category rows for all tournaments
    categories_by_tid = {}
    if os.path.exists('tournament_categories.csv'):
        with open('tournament_categories.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                tid = row['Tournament Id']
                if tid not in categories_by_tid:
                    categories_by_tid[tid] = []
                categories_by_tid[tid].append(row)

    return render_template('list_tournament.html', tournaments=tournaments, categories_by_tid=categories_by_tid)

@app.route('/tournament/<tournament_id>/info')
def tournament_info(tournament_id):
    try:
        # Get current date
        today = datetime.now().date()
        print(f"=== Starting tournament_info route ===")
        print(f"Tournament ID: {tournament_id}")
        
        # Read tournament data
        tournament = None
        with open('tournaments.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Tournament Id'] == tournament_id:
                    tournament = row
                    break

        if not tournament:
            return "Tournament not found", 404

        # Calculate tournament status and registration status
        try:
            start_date = datetime.strptime(tournament['Start Date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(tournament['End Date'], '%Y-%m-%d').date()
            last_reg_date = datetime.strptime(tournament['Last Registration Date'], '%Y-%m-%d').date()
            
            if today < start_date:
                tournament_status = 'Upcoming'
            elif start_date <= today <= end_date:
                tournament_status = 'In Progress'
            else:
                tournament_status = 'Completed'
                
            # Check if registration is still open
            registration_open = today <= last_reg_date
            print(f"Registration open: {registration_open}")  # Debug print
            print(f"Today: {today}, Last registration date: {last_reg_date}")  # Debug print
        except Exception as e:
            print(f"Error parsing dates: {e}")
            tournament_status = 'Unknown'
            registration_open = False

        # Get categories for this tournament
        tournament_categories = []
        category_details = []  # New list to store category details
        with open('tournament_categories.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Tournament Id'] == tournament_id:
                    tournament_categories.append(row['Category'])
                    category_details.append(row)  # Store the complete category details

        print(f"Tournament categories: {tournament_categories}")

        # Initialize empty lists for entries
        girls_entries = {}
        boys_entries = {}

        # Define category mappings
        girls_categories = ['u9', 'u11 Girls', 'u13 Girls', 'u15 Girls', 'u19 Girls', 'Women', 'Veterans 39+ Women']
        boys_categories = ['u11 Boys', 'u13 Boys', 'u17 Boys', 'u19 Boys', 'Men', 'Veterans 39+ Men']

        # Initialize category dictionaries only for categories that exist in tournament_categories
        for category in girls_categories:
            if category in tournament_categories:
                girls_entries[category] = []
        for category in boys_categories:
            if category in tournament_categories:
                boys_entries[category] = []

        # Read registrations from tournament_registrations.csv (same as Step 2)
        print(f"Reading from tournament_registrations.csv for tournament {tournament_id}")
        if os.path.exists('tournament_registrations.csv'):
            with open('tournament_registrations.csv', 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for reg in reader:
                    if (reg['Tournament Id'] == tournament_id and 
                        reg['Status'].lower() == 'active'):
                        
                        # Get player details from players_data.csv
                        player_name = ""
                        school_institution = ""
                        with open('players_data.csv', 'r', newline='', encoding='utf-8') as pf:
                            preader = csv.DictReader(pf)
                            for prow in preader:
                                if prow['Player ID'] == reg['Player ID']:
                                    player_name = prow['Name']
                                    school_institution = prow.get('School/Institution', '')
                                    break
                        
                        entry = {
                            'Name': player_name,
                            'School/Institution': school_institution,
                            'Seeding': reg.get('Seeding', '')
                        }
                        
                        print(f"Found player: {player_name}, Category: {reg['Category']}, Seeding: '{reg.get('Seeding', '')}'")
                        
                        category = reg['Category']
                        if category in girls_categories and category in tournament_categories:
                            if category not in girls_entries:
                                girls_entries[category] = []
                            girls_entries[category].append(entry)
                        elif category in boys_categories and category in tournament_categories:
                            if category not in boys_entries:
                                boys_entries[category] = []
                            boys_entries[category].append(entry)

        # Sort entries in each category by seeding
        def sort_by_seeding(entry):
            seeding = entry.get('Seeding', '')
            try:
                return (int(seeding) if seeding else 999999, entry['Name'])
            except ValueError:
                return (999999, entry['Name'])

        # Sort each category's entries
        for category in girls_entries:
            girls_entries[category].sort(key=sort_by_seeding)
        for category in boys_entries:
            boys_entries[category].sort(key=sort_by_seeding)

        return render_template('tournament_details.html', 
                             tournament=tournament, 
                             categories=category_details,
                             girls_entries=girls_entries,
                             boys_entries=boys_entries,
                             tournament_status=tournament_status,
                             registration_open=registration_open,
                             current_date=datetime.now().strftime('%Y-%m-%d'))

    except Exception as e:
        print(f"Error in tournament_info route: {str(e)}")
        print(traceback.format_exc())
        return "Error loading tournament details", 500

@app.route('/tournament/<tournament_id>/register', methods=['POST'])
def register_player(tournament_id):
    try:
        print(f"=== Starting register_player route ===")
        print(f"Tournament ID: {tournament_id}")
        print(f"Form data: {request.form}")
        
        player_id = request.form.get('player_id')
        categories = request.form.getlist('categories')
        
        if not player_id or not categories:
            return "Missing required fields", 400

        # Get player details from players_data.csv
        player_details = None
        with open('players_data.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Player ID'] == player_id:
                    player_details = row
                    break
                    
        if not player_details:
            return "Player not found", 404

        # Check for existing registrations in the same categories
        existing_registrations = []
        if os.path.exists('tournament_registrations.csv'):
            with open('tournament_registrations.csv', 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if (row['Tournament Id'] == tournament_id and 
                        row['Player ID'] == player_id and 
                        row['Category'] in categories and
                        row['Status'].lower() == 'active'):
                        existing_registrations.append(row['Category'])

        if existing_registrations:
            error_message = f"Player is already registered in the following categories: {', '.join(existing_registrations)}"
            return redirect(url_for('tournament_info', 
                                  tournament_id=tournament_id, 
                                  tab='register', 
                                  error=error_message))

        # Add registrations for each category
        for category in categories:
            registration_data = {
                'Tournament Id': tournament_id,
                'Player ID': player_id,
                'Registration Date': datetime.now().strftime('%Y-%m-%d'),
                'Category': category,
                'Status': 'Active',
                'Seeding': ''  # Initialize with empty seeding
            }
            
            with open('tournament_registrations.csv', 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=registration_data.keys())
                writer.writerow(registration_data)

        # Redirect to the Entries tab with success message
        return redirect(url_for('tournament_info', 
                              tournament_id=tournament_id, 
                              tab='entries', 
                              message='Player has been successfully added to the tournament'))

    except Exception as e:
        print(f"Error in register_player route: {str(e)}")
        print(traceback.format_exc())
        return "Error registering player", 500

def get_tournament_categories(tournament_id):
    """Get categories specific to a tournament from the tournament_categories.csv file"""
    categories = []
    try:
        with open('tournament_categories.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Tournament Id'] == tournament_id:
                    categories.append(row['Category'])
    except Exception as e:
        print(f"Error reading tournament categories: {str(e)}")
        # Return empty list if there's an error
        return []
    
    # If no categories found for this tournament, return an empty list
    return categories

@app.route('/tournament/<tournament_id>/update_seeding', methods=['GET', 'POST'])
def tournament_update_seeding(tournament_id):
    if request.method == 'POST':
        try:
            category = request.form.get('category')
            player_ids = request.form.getlist('player_ids[]')
            seedings = request.form.getlist('seedings[]')
            print("\n=== Seeding Update Request ===")
            print(f"Tournament ID: {tournament_id}")
            print(f"Category: {category}")
            print(f"Number of players: {len(player_ids)}")
            print("\nPlayer IDs and Seedings:")
            for i, (pid, seed) in enumerate(zip(player_ids, seedings)):
                print(f"Player {i+1}: ID={pid}, Seeding={seed}")

            # Read all registrations
            registrations = []
            with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                registrations = list(reader)
                print(f"\nTotal registrations read: {len(registrations)}")
                print(f"CSV Headers: {fieldnames}")

            # Filter registrations for this specific tournament and category
            filtered_registrations = []
            for reg in registrations:
                if (reg['Tournament Id'] == tournament_id and 
                    reg['Category'] == category and
                    reg['Status'].lower() == 'active'):
                    filtered_registrations.append(reg)
                    print(f"✓ MATCHED: Added registration for Player ID '{reg.get('Player ID')}'")
                else:
                    print(f"✗ NO MATCH: Tournament Id match: {reg.get('Tournament Id') == tournament_id}, Category match: {reg.get('Category') == category}, Status active: {reg.get('Status', '').lower() == 'active'}")
            
            print(f"Filtered registrations for tournament {tournament_id}, category {category}: {len(filtered_registrations)}")
            
            # Debug: Show all filtered registrations
            print("Filtered registrations:")
            for reg in filtered_registrations:
                print(f"  Player ID: '{reg.get('Player ID')}', Seeding: '{reg.get('Seeding', '')}'")

            # Build seeding map: player_id -> seeding
            seeding_map = {pid: seed.strip() if seed.strip() else '' for pid, seed in zip(player_ids, seedings)}
            print(f"Seeding map: {seeding_map}")
            
            # Debug: Check if any player IDs in seeding_map exist in filtered_registrations
            for player_id in seeding_map.keys():
                found = any(reg.get('Player ID') == player_id for reg in filtered_registrations)
                print(f"Player ID '{player_id}' found in filtered registrations: {found}")

            # Use helper to update seedings on filtered registrations
            updates_made = update_seeding_in_records(
                filtered_registrations,
                seeding_map,
                key_func=lambda rec: rec.get('Player ID'),
                seeding_field='Seeding'
            )

            print(f"\nUpdates made: {updates_made}")

            if updates_made > 0:
                # Update the original registrations list with the changes from filtered_registrations
                for filtered_reg in filtered_registrations:
                    for i, reg in enumerate(registrations):
                        if (reg['Tournament Id'] == filtered_reg['Tournament Id'] and
                            reg['Category'] == filtered_reg['Category'] and
                            reg['Player ID'] == filtered_reg['Player ID']):
                            registrations[i] = filtered_reg
                            break
                
                # Write back to file
                with open(TOURNAMENT_REGISTRATIONS_CSV, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(registrations)
                print("Successfully wrote updates to file")
                return jsonify({'success': True, 'message': f'Updated {updates_made} records'})
            else:
                print("No matching records found to update")
                return jsonify({'success': False, 'message': 'No matching records found to update'})

        except Exception as e:
            print(f"Error updating seeding: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    else:
        try:
            tournament = get_tournament(tournament_id)
            if not tournament:
                return redirect(url_for('list_tournament'))

            # Get categories for this tournament
            categories = []
            try:
                with open('tournament_categories.csv', 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if row['Tournament Id'] == tournament_id:
                            categories.append(row['Category'])
                    categories.sort()
            except Exception as e:
                print(f"Error reading tournament categories: {str(e)}")

            return render_template('tournament_details.html',
                                tournament=tournament,
                                categories=categories,
                                active_subpage='update_seeding')
        except Exception as e:
            print(f"Error in tournament_update_seeding: {str(e)}")
            return redirect(url_for('list_tournament'))

@app.route('/tournament/<tournament_id>/get_category_players/<category>')
def get_category_players(tournament_id, category):
    # Get the requested fields
    fields = request.args.get('fields', 'basic')  # default to 'basic'
    players = []
    
    print(f"\n=== get_category_players called ===")
    print(f"Tournament ID: {tournament_id}")
    print(f"Category: {category}")
    print(f"Fields: {fields}")
    
    with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if (row['Tournament Id'] == tournament_id and
                row['Category'] == category and
                row['Status'].lower() == 'active'):
                player_id = row['Player ID']
                seeding = row.get('Seeding', '')
                print(f"Found registration: Player ID={player_id}, Seeding={seeding}")
                
                with open('players_data.csv', 'r', newline='', encoding='utf-8') as pf:
                    preader = csv.DictReader(pf)
                    for prow in preader:
                        if prow['Player ID'] == player_id:
                            player = {
                                'name': prow['Name'],
                                'player_id': player_id,
                                'seeding': seeding
                            }
                            if fields == 'full':
                                player['school'] = prow.get('School/Institution', '')
                                player['state'] = prow.get('State', '')
                                player['district'] = prow.get('District', '')
                                player['academy'] = prow.get('Academy', '')
                            players.append(player)
                            print(f"Added player: {prow['Name']}, Seeding: {seeding}")
                            break
    
    print(f"Total players returned: {len(players)}")
    print("Final player data:")
    for player in players:
        print(f"  {player['name']}: seeding = '{player['seeding']}'")
    
    return jsonify({'success': True, 'players': players})

# Helper function to get tournament details
def get_tournament(tournament_id):
    with open('tournaments.csv', 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['Tournament Id'] == tournament_id:
                return {
                    'Tournament Id': row['Tournament Id'],
                    'Tournament Name': row['Tournament Name'],
                    'Categories': row['Categories'],
                    'Venue': row['Venue'],
                    'Start Date': row['Start Date'],
                    'End Date': row['End Date'],
                    'Last Registration Date': row['Last Registration Date'],
                    'Total Prize': row['Total Prize'],
                    'General Information': row['General Information'],
                    'Tournament Logo Link': row.get('Tournament Logo Link', ''),
                    'Status': row['Status'],
                    'Bank Account': row.get('Bank Account', ''),
                    'UPI Link': row.get('UPI Link', ''),
                    'Payment QR': row.get('Payment QR', '')
                }
    return None

@app.route('/get-players')
def get_players():
    try:
        name = request.args.get('name', '').strip().lower()
        if not name:
            return jsonify([])
        
        players = []
        with open('players_data.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if name in row['Name'].lower():
                    players.append({
                        'Name': row['Name'],
                        'Player ID': row['Player ID'],
                        'Date of Birth': row['Date of Birth'],
                        'Gender': row['Gender'],
                        'State': row['State']
                    })
                    if len(players) >= 10:  # Limit results to 10 players
                        break
        
        return jsonify(players)
    except Exception as e:
        print(f"Error in get_players: {str(e)}")
        return jsonify([])

def generate_player_id(date_of_birth):
    try:
        # Get current year's last 2 digits (AA)
        current_year = str(datetime.now().year)[-2:]
        
        # Get birth year's last 2 digits (YY)
        dob = datetime.strptime(date_of_birth, '%Y-%m-%d')
        birth_year = str(dob.year)[-2:]
        
        # Create the prefix for the ID
        id_prefix = f"{current_year}-{birth_year}-"
        
        # Get the highest sequence number for this combination
        max_sequence = 0
        
        if os.path.exists(PLAYERS_CSV):
            with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if 'Player ID' in row and row['Player ID'].startswith(id_prefix):
                        try:
                            sequence = int(row['Player ID'].split('-')[-1])
                            max_sequence = max(max_sequence, sequence)
                        except ValueError:
                            continue
        
        # Generate new ID with next sequence number
        new_sequence = max_sequence + 1
        return f"{current_year}-{birth_year}-{new_sequence:04d}"  # Format with 4 leading zeros
        
    except Exception as e:
        print(f"Error generating player ID: {str(e)}")
        return None

def migrate_tournament_registrations_csv():
    try:
        if not os.path.exists(TOURNAMENT_REGISTRATIONS_CSV):
            initialize_tournament_registrations_csv()
            return

        # Read existing data
        rows = []
        with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='') as file:
            reader = csv.reader(file)
            headers = next(reader)
            rows.append(headers)
            for row in reader:
                rows.append(row)

        # Check if Seeding column exists
        if 'Seeding' not in headers:
            # Add Seeding column header
            headers.append('Seeding')
            rows[0] = headers
            
            # Add empty seeding value to all existing rows
            for i in range(1, len(rows)):
                rows[i].append('')

            # Write back to file
            with open(TOURNAMENT_REGISTRATIONS_CSV, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(rows)

    except Exception as e:
        print(f"Error migrating tournament registrations CSV: {str(e)}")

@app.route('/tournament/<tournament_id>/bulk_register/download')
def download_bulk_template(tournament_id):
    try:
        # Create CSV content
        csv_content = (
            "Name,Date of Birth,Gender,Phone Number,Category,Email ID,Address,State,TTFI ID,School/Institution,Academy,UPI ID\n"
            "John Doe,2000-01-01,Male,9876543210,Under 11 Boys Singles,john.doe@email.com,123 Main Street,Delhi,TTFI123456,ABC School,XYZ Academy,upi@bank"
        )
        
        # Create response
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=tournament_registration_template.csv'
        
        return response
        
    except Exception as e:
        app.logger.error(f"Error generating template: {str(e)}")
        flash('Error generating template file', 'error')
        return redirect(url_for('tournament_bulk_register', tournament_id=tournament_id))

@app.route('/tournament/<tournament_id>/bulk_register/submit', methods=['POST'])
def submit_bulk_registration(tournament_id):
    try:
        data = request.get_json()
        if not data or 'entries' not in data:
            return jsonify({'success': False, 'message': 'No data provided'})

        entries = data['entries']
        if not all(entry.get('is_valid', False) for entry in entries):
            return jsonify({
                'success': False,
                'message': 'Please correct all invalid entries before submitting'
            })

        skipped = []
        registered = []

        for entry in entries:
            player_data = entry['data']
            name = player_data[0].strip()
            dob = player_data[1].strip()
            gender = player_data[2].strip()
            phone = player_data[3].strip()
            category = player_data[4].strip()
            email = player_data[5].strip() if len(player_data) > 5 else ''
            address = player_data[6].strip() if len(player_data) > 6 else ''
            state = player_data[7].strip() if len(player_data) > 7 else ''
            ttfi_id = player_data[8].strip() if len(player_data) > 8 else ''
            official_state_id = player_data[9].strip() if len(player_data) > 9 else ''
            institution = player_data[10].strip() if len(player_data) > 10 else ''
            academy = player_data[11].strip() if len(player_data) > 11 else ''
            upi_id = player_data[12].strip() if len(player_data) > 12 else ''

            player_id = get_player_id_from_players_data(name, dob, phone)
            if not player_id:
                player_id = generate_new_player_id(dob)
                if not player_id:
                    skipped.append({'name': name, 'reason': 'Failed to generate Player ID'})
                    continue
                # Add to players_data.csv
                with open('players_data.csv', 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        player_id, name, dob, gender, phone, email, 
                        address, state, ttfi_id, official_state_id, institution, 
                        academy, upi_id
                    ])

            # Check if player is already registered for this tournament/category
            already_registered = False
            try:
                with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if (row['Tournament Id'] == tournament_id and 
                            row['Player ID'] == player_id and 
                            row['Category'] == category):
                            already_registered = True
                            break
            except FileNotFoundError:
                # If file doesn't exist, create it with headers
                with open(TOURNAMENT_REGISTRATIONS_CSV, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        'Tournament Id', 
                        'Player ID', 
                        'Registration Date',
                        'Category',
                        'Status',
                        'Seeding'
                    ])

            if already_registered:
                skipped.append({'name': name, 'reason': 'Already registered for this category'})
                continue

            # Register the player for the tournament
            with open(TOURNAMENT_REGISTRATIONS_CSV, 'a', newline='') as file:
                writer = csv.writer(file)
                registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([
                    tournament_id,
                    player_id,
                    registration_date,
                    category,
                    'Active',
                    ''
                ])
            registered.append({'name': name, 'player_id': player_id})

        summary = f"Registered: {len(registered)}. Skipped: {len(skipped)}."
        details = ""
        if skipped:
            details = " Skipped records: " + ", ".join([f"{r['name']} ({r['reason']})" for r in skipped])

        return jsonify({
            'success': True,
            'message': summary + details,
            'registered': registered,
            'skipped': skipped
        })

    except Exception as e:
        app.logger.error(f"Error in bulk registration: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing registrations: {str(e)}'
        })

def get_player_id_from_players_data(name, dob, phone):
    try:
        with open('players_data.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Debug print to check the actual values being compared
                print(f"\nComparing DB record:")
                print(f"Name: '{row['Name'].lower().strip()}' vs Input: '{name.lower().strip()}'")
                print(f"DOB: '{row['Date of Birth'].strip()}' vs Input: '{dob.strip()}'")
                print(f"Phone: '{row['Phone Number'].strip()}' vs Input: '{phone.strip()}'")
                
                # Case-insensitive name comparison and exact match for DOB and phone number
                if (row['Name'].lower().strip() == name.lower().strip() and 
                    row['Date of Birth'].strip() == dob.strip() and
                    row['Phone Number'].strip() == phone.strip()):
                    print(f"Match found! Player ID: {row['Player ID']}")
                    return row['Player ID']
                else:
                    # Print which fields didn't match
                    if row['Name'].lower().strip() != name.lower().strip():
                        print("Name did not match")
                    if row['Date of Birth'].strip() != dob.strip():
                        print("Date of Birth did not match")
                    if row['Phone Number'].strip() != phone.strip():
                        print("Phone number did not match")
    except Exception as e:
        print(f"Error reading players_data.csv: {str(e)}")
        app.logger.error(f"Error reading players_data.csv: {str(e)}")
    return None

def generate_new_player_id(dob):
    try:
        # Get current year's last two digits
        current_year = str(datetime.now().year)[-2:]
        # Get birth year's last two digits from DOB
        birth_year = str(datetime.strptime(dob, '%Y-%m-%d').year)[-2:]
        
        # Read existing player IDs to determine the next sequence number
        max_sequence = 0
        pattern = f"{current_year}-{birth_year}-"
        
        try:
            with open('players_data.csv', 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    player_id = row['Player ID']  # Changed from 'Player Id'
                    if player_id.startswith(pattern):
                        try:
                            sequence = int(player_id.split('-')[-1])
                            max_sequence = max(max_sequence, sequence)
                        except ValueError:
                            continue
        except FileNotFoundError:
            # If file doesn't exist, start with sequence 0
            pass
        
        # Generate new ID with incremented sequence
        new_sequence = str(max_sequence + 1).zfill(4)
        new_id = f"{current_year}-{birth_year}-{new_sequence}"
        print(f"Generated new player ID: {new_id}")  # Debug log
        return new_id

    except Exception as e:
        print(f"Error generating player ID: {str(e)}")  # Debug log
        app.logger.error(f"Error generating player ID: {str(e)}")
        return None

@app.route('/tournament/<tournament_id>/update_format')
def tournament_update_format(tournament_id):
    # You can render a template or just return a placeholder for now
    return f"Update Format page for tournament {tournament_id}"

@app.route('/tournament/<tournament_id>/create_draw')
def tournament_create_draw(tournament_id):
    # Get tournament data
    tournament = get_tournament(tournament_id)
    if not tournament:
        return redirect(url_for('list_tournament'))
    
    # Get tournament categories specific to this tournament
    categories = get_tournament_categories(tournament_id)
    
    return render_template('tournament_create_draw.html', 
                          tournament=tournament, 
                          tournament_id=tournament_id, 
                          categories=categories, 
                          active_page='tournament',  # For main menu
                          active_subpage='create_draw')  # For submenu

@app.route('/save_tournament_draw', methods=['POST'])
def save_tournament_draw():
    try:
        # Get data from the request
        data = request.json
        draw_data = data['drawData']
        tournament_id = data['tournamentId']
        category = data['category']
        
        print(f"\n=== Saving tournament draw ===")
        print(f"Tournament ID: {tournament_id}")
        print(f"Category: {category}")
        print(f"Number of players: {len(draw_data)}")
        
        # Read all registrations
        registrations = []
        with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            registrations = list(reader)
            print(f"Total registrations read: {len(registrations)}")

        # Update seeding for the specific category
        updates_made = 0
        for draw_row in draw_data:
            player_name = draw_row['name']
            new_seeding = draw_row['seeding']
            
            # Find the corresponding registration and update seeding
            for reg in registrations:
                if (reg['Tournament Id'] == tournament_id and 
                    reg['Category'] == category):
                    
                    # Get player name from players_data.csv
                    with open('players_data.csv', 'r', newline='', encoding='utf-8') as pf:
                        preader = csv.DictReader(pf)
                        for prow in preader:
                            if prow['Player ID'] == reg['Player ID']:
                                if prow['Name'] == player_name:
                                    old_seeding = reg.get('Seeding', '')
                                    reg['Seeding'] = new_seeding
                                    updates_made += 1
                                    print(f"Updated {player_name}: seeding from '{old_seeding}' to '{new_seeding}'")
                                break

        print(f"Updates made: {updates_made}")

        if updates_made > 0:
            # Write back to file
            with open(TOURNAMENT_REGISTRATIONS_CSV, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(registrations)
            print("Successfully wrote updates to tournament_registrations.csv")
            return jsonify({'success': True, 'message': f'Draw saved successfully! Updated {updates_made} records'})
        else:
            print("No matching records found to update")
            return jsonify({'success': False, 'message': 'No matching records found to update'})
    
    except Exception as e:
        print(f"Error saving tournament draw: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

@app.route('/list-players')
def list_players():
    try:
        players = []
        if os.path.exists(PLAYERS_CSV):
            with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                players = list(reader)
                # Sort players by name
                players.sort(key=lambda x: x['Name'].lower())
        
        return render_template('list_players.html', players=players, active_page='players')
    except Exception as e:
        print(f"Error in list_players: {e}")
        return render_template('list_players.html', players=[], error=str(e), active_page='players')

@app.route('/get_seeding_ranges')
def get_seeding_ranges():
    try:
        with open('config/seeding_ranges.json', 'r') as f:
            data = json.load(f)
        return jsonify({
            'success': True,
            'seeding_ranges': data['seeding_ranges']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/search-players')
def search_players():
    try:
        # Get search parameter
        player_name = request.args.get('player_name', '').strip().lower()
        
        # Check if search was performed
        search_performed = bool(player_name)
        
        # Initialize empty list for players
        players = []
        
        # Only proceed with search if the CSV file exists
        if os.path.exists(PLAYERS_CSV):
            with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                all_players = list(reader)
                
                # Filter players based on name
                if player_name:
                    filtered_players = [
                        p for p in all_players 
                        if player_name in p['Name'].lower()
                    ]
                    players = filtered_players
        
        return render_template(
            'search_players.html',
            players=players if search_performed else None,
            search_performed=search_performed
        )
        
    except Exception as e:
        print(f"Error during search: {e}")
        return render_template(
            'search_players.html',
            error=f"An error occurred while searching: {str(e)}",
            players=None,
            search_performed=False
        )

def get_categories_from_config():
    try:
        config_path = os.path.join('config', 'categories_config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
            categories = config.get('categories', [])
            print("Loaded categories:", categories)  # Debug print
            return categories
    except Exception as e:
        print(f"Error reading categories config: {e}")
        return []

def get_full_tournament_categories(tournament_id):
    """Get complete category details for a tournament including fees and prizes"""
    categories = []
    try:
        with open('tournament_categories.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Tournament Id'] == tournament_id:
                    categories.append(row)
    except Exception as e:
        print(f"Error reading tournament categories: {str(e)}")
        # Return empty list if there's an error
        return []
    
    # If no categories found for this tournament, return an empty list
    return categories

# Make the function available to templates
app.jinja_env.globals.update(get_full_tournament_categories=get_full_tournament_categories)

@app.route('/edit-player/<player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    if request.method == 'POST':
        try:
            print("\n=== Starting Player Edit Process ===")
            print(f"Player ID: {player_id}")
            print(f"Form data: {request.form}")
            print(f"Files received: {request.files}")
            
            # Get form data
            player_data = {
                'Player ID': player_id,
                'Name': request.form.get('player_name'),
                'Date of Birth': request.form.get('date_of_birth'),
                'Gender': request.form.get('gender'),
                'Phone Number': request.form.get('phone'),
                'Email ID': request.form.get('email'),
                'State': request.form.get('state'),
                'District': request.form.get('district'),
                'School/Institution': request.form.get('institution'),
                'Academy': request.form.get('academy'),
                'Address': request.form.get('address'),
                'TTFI ID': request.form.get('ttfi_id'),
                'Official State ID': request.form.get('official_state_id'),
                'UPI ID': request.form.get('upi_id'),
                'Account Holder Name': request.form.get('account_holder_name'),
                'Account Number': request.form.get('account_number'),
                'Bank Name': request.form.get('bank_name'),
                'Branch Name': request.form.get('branch_name'),
                'IFSC Code': request.form.get('ifsc_code'),
                'Transaction ID': request.form.get('transaction_id'),
                'State Registration': 'Yes' if request.form.get('do_state_registration') == 'on' else 'No'
            }

            print("\nForm data received:")
            print(f"Transaction ID: {player_data['Transaction ID']}")
            
            # Handle file uploads
            if 'photo' in request.files and request.files['photo'].filename:
                photo = request.files['photo']
                if photo and allowed_file(photo.filename, {'png', 'jpg', 'jpeg'}):
                    filename = secure_filename(photo.filename)
                    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', filename)
                    os.makedirs(os.path.dirname(photo_path), exist_ok=True)
                    photo.save(photo_path)
                    player_data['Photo Path'] = os.path.join('uploads', 'photos', filename)
                    print(f"Photo saved to: {player_data['Photo Path']}")

            if 'birth_certificate' in request.files and request.files['birth_certificate'].filename:
                birth_cert = request.files['birth_certificate']
                if birth_cert and allowed_file(birth_cert.filename, {'pdf', 'jpg', 'jpeg', 'png'}):
                    filename = secure_filename(birth_cert.filename)
                    cert_path = os.path.join(app.config['UPLOAD_FOLDER'], 'birth_certificates', filename)
                    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
                    birth_cert.save(cert_path)
                    player_data['Birth Certificate Path'] = os.path.join('uploads', 'birth_certificates', filename)
                    print(f"Birth certificate saved to: {player_data['Birth Certificate Path']}")

            if 'address_proof' in request.files and request.files['address_proof'].filename:
                address_proof = request.files['address_proof']
                if address_proof and allowed_file(address_proof.filename, {'pdf', 'jpg', 'jpeg', 'png'}):
                    filename = secure_filename(address_proof.filename)
                    proof_path = os.path.join(app.config['UPLOAD_FOLDER'], 'address_proofs', filename)
                    os.makedirs(os.path.dirname(proof_path), exist_ok=True)
                    address_proof.save(proof_path)
                    player_data['Address Proof Path'] = os.path.join('uploads', 'address_proofs', filename)
                    print(f"Address proof saved to: {player_data['Address Proof Path']}")

            if 'payment_snapshot' in request.files and request.files['payment_snapshot'].filename:
                payment_snap = request.files['payment_snapshot']
                if payment_snap and allowed_file(payment_snap.filename, {'jpg', 'jpeg', 'png'}):
                    filename = secure_filename(payment_snap.filename)
                    snap_path = os.path.join(app.config['UPLOAD_FOLDER'], 'payment_snapshots', filename)
                    os.makedirs(os.path.dirname(snap_path), exist_ok=True)
                    payment_snap.save(snap_path)
                    player_data['Payment Snapshot Path'] = os.path.join('uploads', 'payment_snapshots', filename)
                    print(f"Payment snapshot saved to: {player_data['Payment Snapshot Path']}")

            # Read existing players
            players = []
            with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                print(f"CSV Headers: {fieldnames}")
                for row in reader:
                    if row['Player ID'] == player_id:
                        print(f"\nFound existing player record:")
                        print(f"Existing Photo Path: {row.get('Photo Path', 'Not found')}")
                        print(f"Existing Birth Certificate Path: {row.get('Birth Certificate Path', 'Not found')}")
                        print(f"Existing Address Proof Path: {row.get('Address Proof Path', 'Not found')}")
                        print(f"Existing Payment Snapshot Path: {row.get('Payment Snapshot Path', 'Not found')}")
                        # Preserve existing file paths if no new files were uploaded
                        if 'Photo Path' not in player_data and 'Photo Path' in row:
                            player_data['Photo Path'] = row['Photo Path']
                            print(f"Preserved existing Photo Path: {player_data['Photo Path']}")
                        if 'Birth Certificate Path' not in player_data and 'Birth Certificate Path' in row:
                            player_data['Birth Certificate Path'] = row['Birth Certificate Path']
                            print(f"Preserved existing Birth Certificate Path: {player_data['Birth Certificate Path']}")
                        if 'Address Proof Path' not in player_data and 'Address Proof Path' in row:
                            player_data['Address Proof Path'] = row['Address Proof Path']
                            print(f"Preserved existing Address Proof Path: {player_data['Address Proof Path']}")
                        if 'Payment Snapshot Path' not in player_data and 'Payment Snapshot Path' in row:
                            player_data['Payment Snapshot Path'] = row['Payment Snapshot Path']
                            print(f"Preserved existing Payment Snapshot Path: {player_data['Payment Snapshot Path']}")
                        players.append(player_data)
                    else:
                        players.append(row)

            print("\nWriting updated data to CSV...")
            # Write back to CSV
            with open(PLAYERS_CSV, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(players)
            print("CSV update completed")

            flash('Player updated successfully!', 'success')
            return redirect(url_for('list_players'))

        except Exception as e:
            print(f"\nError in edit_player: {str(e)}")
            print(traceback.format_exc())
            flash(f'Error updating player: {str(e)}', 'error')
            return redirect(url_for('edit_player', player_id=player_id))

    else:
        # Get player data
        player = None
        with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Player ID'] == player_id:
                    player = row
                    break

        if not player:
            flash('Player not found', 'error')
            return redirect(url_for('list_players'))

        return render_template('edit_player.html', player=player)

@app.route('/delete-player/<player_id>', methods=['POST'])
def delete_player(player_id):
    try:
        # Read all players
        players = []
        with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['Player ID'] != player_id:
                    players.append(row)

        # Write back to CSV
        with open(PLAYERS_CSV, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(players)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/update-tournaments-csv')
def update_tournaments_csv():
    try:
        # Read existing tournaments
        tournaments = []
        with open('tournaments.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            tournaments = list(reader)

        # Ensure all tournaments have the new fields
        for tournament in tournaments:
            if 'Bank Account' not in tournament:
                tournament['Bank Account'] = ''
            if 'UPI Link' not in tournament:
                tournament['UPI Link'] = ''
            if 'Payment QR' not in tournament:
                tournament['Payment QR'] = ''

        # Write back to tournaments.csv
        with open('tournaments.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tournaments)

        return "Tournaments CSV updated successfully!"
    except Exception as e:
        return f"Error updating tournaments CSV: {str(e)}"

@app.route('/get_rankings')
def get_rankings():
    try:
        rankings = []
        players = []
        
        # Read players_data.csv to get Player ID to Official State ID mapping
        with open('players_data.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get('Official State ID'):  # Only include players with Official State ID
                    players.append({
                        'player_id': row['Player ID'],
                        'official_state_id': row['Official State ID']
                    })
        
        # Read Ranking.csv to get rankings
        with open('Ranking.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                rankings.append({
                    'official_state_id': row['Official State Id'],
                    'category': row['Category'],
                    'ranking': row['Ranking']
                })
        
        return jsonify({
            'success': True,
            'players': players,
            'rankings': rankings
        })
    except Exception as e:
        print(f"Error fetching rankings: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching rankings: {str(e)}'
        })

def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/update_player/<player_id>', methods=['POST'])
def update_player(player_id):
    if request.method == 'POST':
        try:
            print("\n=== Starting Player Edit Process ===")
            print(f"Player ID: {player_id}")
            print(f"Form data: {request.form}")
            print(f"Files received: {request.files}")
            
            # Get form data
            player_data = {
                'Player ID': player_id,
                'Name': request.form.get('player_name'),
                'Date of Birth': request.form.get('date_of_birth'),
                'Gender': request.form.get('gender'),
                'Phone Number': request.form.get('phone'),
                'Email ID': request.form.get('email'),
                'State': request.form.get('state'),
                'District': request.form.get('district'),
                'School/Institution': request.form.get('institution'),
                'Academy': request.form.get('academy'),
                'Address': request.form.get('address'),
                'TTFI ID': request.form.get('ttfi_id'),
                'Official State ID': request.form.get('official_state_id'),
                'UPI ID': request.form.get('upi_id'),
                'Account Holder Name': request.form.get('account_holder_name'),
                'Account Number': request.form.get('account_number'),
                'Bank Name': request.form.get('bank_name'),
                'Branch Name': request.form.get('branch_name'),
                'IFSC Code': request.form.get('ifsc_code'),
                'Transaction ID': request.form.get('transaction_id'),
                'State Registration': 'Yes' if request.form.get('do_state_registration') == 'on' else 'No'
            }

            print("\nForm data received:")
            print(f"Transaction ID: {player_data['Transaction ID']}")
            
            # Handle file uploads
            if 'photo' in request.files and request.files['photo'].filename:
                photo = request.files['photo']
                if photo and allowed_file(photo.filename, {'png', 'jpg', 'jpeg'}):
                    filename = secure_filename(photo.filename)
                    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', filename)
                    os.makedirs(os.path.dirname(photo_path), exist_ok=True)
                    photo.save(photo_path)
                    player_data['Photo Path'] = os.path.join('uploads', 'photos', filename)
                    print(f"Photo saved to: {player_data['Photo Path']}")

            if 'birth_certificate' in request.files and request.files['birth_certificate'].filename:
                birth_cert = request.files['birth_certificate']
                if birth_cert and allowed_file(birth_cert.filename, {'pdf', 'jpg', 'jpeg', 'png'}):
                    filename = secure_filename(birth_cert.filename)
                    cert_path = os.path.join(app.config['UPLOAD_FOLDER'], 'birth_certificates', filename)
                    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
                    birth_cert.save(cert_path)
                    player_data['Birth Certificate Path'] = os.path.join('uploads', 'birth_certificates', filename)
                    print(f"Birth certificate saved to: {player_data['Birth Certificate Path']}")

            if 'address_proof' in request.files and request.files['address_proof'].filename:
                address_proof = request.files['address_proof']
                if address_proof and allowed_file(address_proof.filename, {'pdf', 'jpg', 'jpeg', 'png'}):
                    filename = secure_filename(address_proof.filename)
                    proof_path = os.path.join(app.config['UPLOAD_FOLDER'], 'address_proofs', filename)
                    os.makedirs(os.path.dirname(proof_path), exist_ok=True)
                    address_proof.save(proof_path)
                    player_data['Address Proof Path'] = os.path.join('uploads', 'address_proofs', filename)
                    print(f"Address proof saved to: {player_data['Address Proof Path']}")

            if 'payment_snapshot' in request.files and request.files['payment_snapshot'].filename:
                payment_snap = request.files['payment_snapshot']
                if payment_snap and allowed_file(payment_snap.filename, {'jpg', 'jpeg', 'png'}):
                    filename = secure_filename(payment_snap.filename)
                    snap_path = os.path.join(app.config['UPLOAD_FOLDER'], 'payment_snapshots', filename)
                    os.makedirs(os.path.dirname(snap_path), exist_ok=True)
                    payment_snap.save(snap_path)
                    player_data['Payment Snapshot Path'] = os.path.join('uploads', 'payment_snapshots', filename)
                    print(f"Payment snapshot saved to: {player_data['Payment Snapshot Path']}")

            # Read existing players
            players = []
            with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                print(f"CSV Headers: {fieldnames}")
                for row in reader:
                    if row['Player ID'] == player_id:
                        print(f"\nFound existing player record:")
                        print(f"Existing Photo Path: {row.get('Photo Path', 'Not found')}")
                        print(f"Existing Birth Certificate Path: {row.get('Birth Certificate Path', 'Not found')}")
                        print(f"Existing Address Proof Path: {row.get('Address Proof Path', 'Not found')}")
                        print(f"Existing Payment Snapshot Path: {row.get('Payment Snapshot Path', 'Not found')}")
                        # Preserve existing file paths if no new files were uploaded
                        if 'Photo Path' not in player_data and 'Photo Path' in row:
                            player_data['Photo Path'] = row['Photo Path']
                            print(f"Preserved existing Photo Path: {player_data['Photo Path']}")
                        if 'Birth Certificate Path' not in player_data and 'Birth Certificate Path' in row:
                            player_data['Birth Certificate Path'] = row['Birth Certificate Path']
                            print(f"Preserved existing Birth Certificate Path: {player_data['Birth Certificate Path']}")
                        if 'Address Proof Path' not in player_data and 'Address Proof Path' in row:
                            player_data['Address Proof Path'] = row['Address Proof Path']
                            print(f"Preserved existing Address Proof Path: {player_data['Address Proof Path']}")
                        if 'Payment Snapshot Path' not in player_data and 'Payment Snapshot Path' in row:
                            player_data['Payment Snapshot Path'] = row['Payment Snapshot Path']
                            print(f"Preserved existing Payment Snapshot Path: {player_data['Payment Snapshot Path']}")
                        players.append(player_data)
                    else:
                        players.append(row)

            print("\nWriting updated data to CSV...")
            # Write back to CSV
            with open(PLAYERS_CSV, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(players)
            print("CSV update completed")

            flash('Player updated successfully!', 'success')
            return redirect(url_for('list_players'))

        except Exception as e:
            print(f"\nError in edit_player: {str(e)}")
            print(traceback.format_exc())
            flash(f'Error updating player: {str(e)}', 'error')
            return redirect(url_for('edit_player', player_id=player_id))

    else:
        # Get player data
        player = None
        with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Player ID'] == player_id:
                    player = row
                    break

        if not player:
            flash('Player not found', 'error')
            return redirect(url_for('list_players'))

        return render_template('edit_player.html', player=player)

if __name__ == '__main__':
    # Initialize CSV files if they don't exist
    initialize_tournament_registrations_csv()
    # Migrate existing CSV files if needed
    migrate_tournament_registrations_csv()
    # Ensure tournament directories exist
    ensure_tournament_directories()
    app.run(debug=True)