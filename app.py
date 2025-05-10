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
                'General Information', 'Tournament Logo Link', 'Status'
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
            
            player_name = form_data.get('player_name', '').strip()
            date_of_birth = form_data.get('date_of_birth', '').strip()
            gender = form_data.get('gender', '').strip()
            phone = form_data.get('phone', '').strip()
            email = form_data.get('email', '').strip()
            address = form_data.get('address', '').strip()
            state = form_data.get('state', '').strip()
            ttfi_id = form_data.get('ttfi_id', '').strip()
            dstta_id = form_data.get('dstta_id', '').strip() if state == 'Delhi' else ''
            institution = form_data.get('institution', '').strip()
            academy = form_data.get('academy', '').strip()
            upi_id = form_data.get('upi_id', '').strip()

            print(f"Processed form data:")
            print(f"Name: {player_name}")
            print(f"DOB: {date_of_birth}")
            print(f"Gender: {gender}")
            print(f"Phone: {phone}")

            # Basic validation
            if not all([player_name, date_of_birth, gender, phone]):
                raise ValueError("All required fields must be filled out")

            if not phone.isdigit() or len(phone) != 10:
                raise ValueError("Please enter a valid 10-digit phone number")

            if not all(c.isalpha() or c.isspace() for c in player_name):
                raise ValueError("Name should only contain letters and spaces")

            # Generate Player ID
            current_year = str(datetime.now().year)[-2:]
            birth_year = str(datetime.strptime(date_of_birth, '%Y-%m-%d').year)[-2:]
            
            # Get the next sequence number
            sequence = 1
            id_prefix = f"{current_year}-{birth_year}-"
            
            if os.path.exists(PLAYERS_CSV):
                print("Reading existing players file for sequence number")
                with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if row.get('Player ID', '').startswith(id_prefix):
                            try:
                                current_sequence = int(row['Player ID'].split('-')[2])
                                sequence = max(sequence, current_sequence + 1)
                            except (IndexError, ValueError) as e:
                                print(f"Error parsing sequence number: {e}")
                                continue
            
            player_id = f"{current_year}-{birth_year}-{sequence:04d}"
            print(f"Generated Player ID: {player_id}")

            # Prepare player data
            fieldnames = [
                'Player ID',
                'Name',
                'Date of Birth',
                'Gender',
                'Phone Number',
                'Email ID',
                'Address',
                'State',
                'TTFI ID',
                'DSTTA ID',
                'School/Institution',
                'Academy',
                'UPI ID'
            ]

            player_data = {
                'Player ID': player_id,
                'Name': player_name,
                'Date of Birth': date_of_birth,
                'Gender': gender,
                'Phone Number': phone,
                'Email ID': email,
                'Address': address,
                'State': state,
                'TTFI ID': ttfi_id,
                'DSTTA ID': dstta_id,
                'School/Institution': institution,
                'Academy': academy,
                'UPI ID': upi_id
            }

            # Check if file exists and if player already exists
            player_exists = False
            if os.path.exists(PLAYERS_CSV):
                print("Checking for existing player")
                with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if (row['Name'].lower() == player_name.lower() and 
                            row['Phone Number'] == phone):
                            player_exists = True
                            player_data['Player ID'] = row['Player ID']
                            print(f"Found existing player with ID: {row['Player ID']}")
                            break

            if not player_exists:
                try:
                    # Write to CSV file
                    file_exists = os.path.exists(PLAYERS_CSV)
                    print(f"Writing new player to CSV. File exists: {file_exists}")
                    
                    mode = 'a' if file_exists else 'w'
                    print(f"Opening file in mode: {mode}")
                    
                    with open(PLAYERS_CSV, mode, newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=fieldnames)
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
            return render_template('players.html', 
                                 error=str(e),
                                 today_date=datetime.now().strftime('%Y-%m-%d'))

    # For GET request
    return render_template('players.html', today_date=datetime.now().strftime('%Y-%m-%d'))

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

        # Update seedings
        updated_count = 0
        for key, value in form_data.items():
            if key.startswith('seeding_'):
                index = int(key.split('_')[1])
                player_name = request.form.get(f'player_name_{index}')
                
                if player_name:
                    for player in all_players:
                        if (player['Player Name'] == player_name and 
                            player['Category'] == category):
                            player['Seeding'] = value if value.strip() else ''
                            updated_count += 1

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

@app.route('/create-draws')
def create_draws():
    return render_template('create_draws.html')

@app.route('/create-tournament', methods=['GET', 'POST'])
def create_tournament():
    if request.method == 'POST':
        try:
            # Generate unique tournament ID
            tournament_id = str(uuid.uuid4())
            
            # Get form data
            tournament_name = request.form.get('tournament_name')
            venue = request.form.get('venue')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            last_registration_date = request.form.get('last_registration_date')
            total_prize = request.form.get('total_prize')
            general_info = request.form.get('general_info')
            
            # Create tournament directory structure
            tournament_folder = os.path.join('static', 'tournaments', tournament_id)
            if not os.path.exists(tournament_folder):
                os.makedirs(tournament_folder)
            
            # Handle multiple tournament logos
            tournament_logos = request.files.getlist('tournament_logo')
            tournament_logo_links = []
            
            for idx, logo in enumerate(tournament_logos):
                if logo and logo.filename:
                    # Create a safe filename from tournament name
                    safe_tournament_name = "".join(c for c in tournament_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    filename = f"{safe_tournament_name}_logo_{idx+1}{os.path.splitext(logo.filename)[1]}"
                    logo_path = os.path.join(tournament_folder, filename)
                    logo.save(logo_path)
                    # Store the relative path for the database
                    logo_link = f"static/tournaments/{tournament_id}/{filename}"
                    tournament_logo_links.append(logo_link)
            
            # Join all logo links with a separator
            tournament_logo_links_str = '|'.join(tournament_logo_links)
            
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
                'Tournament Logo Link': tournament_logo_links_str,  # Store all logo links
                'Status': 'active'
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
    
    return render_template('tournament_creation.html')

@app.route('/list-tournament')
def list_tournament():
    tournaments = []
    categories_by_tid = {}
    tournament_categories = {}
    
    try:
        # Read tournaments
        with open('tournaments.csv', 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get('Status', '').lower() == 'active':
                    tournaments.append({
                        'Tournament Id': row['Tournament Id'],
                        'Tournament Name': row['Tournament Name'],
                        'Venue': row['Venue'],
                        'Start Date': row.get('Start Date', row.get('Tournament Date', '')),
                        'End Date': row.get('End Date', row.get('Tournament Date', '')),
                        'Last Registration Date': row['Last Registration Date'],
                        'Total Prize': row['Total Prize'],
                        'Categories': row['Categories'],
                        'Status': row['Status']
                    })
                    categories_by_tid[row['Tournament Id']] = []

        # Read tournament categories
        with open('tournament_categories.csv', 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                tournament_id = row.get('Tournament Id')
                if tournament_id in categories_by_tid:
                    if tournament_id not in tournament_categories:
                        tournament_categories[tournament_id] = []
                    tournament_categories[tournament_id].append({
                        'Tournament Name': row['Tournament Name'],
                        'Category': row['Category'],
                        'Fee': row['Fee'],
                        'First Prize': row['First Prize'],
                        'Second Prize': row['Second Prize'],
                        'Third Prize': row['Third Prize'],
                        'Format': row['Format']
                    })

        # Sort tournaments by start date
        tournaments.sort(key=lambda x: datetime.strptime(x['Start Date'], '%Y-%m-%d'))

        return render_template('list_tournament.html', 
                             tournaments=tournaments,
                             tournament_categories=tournament_categories)
    except Exception as e:
        return render_template('list_tournament.html', 
                             error=str(e),
                             tournaments=[],
                             tournament_categories={})

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

@app.route('/edit-tournament/<tournament_id>', methods=['GET', 'POST'])
def edit_tournament(tournament_id):
    if request.method == 'GET':
        # Get tournament details
        tournament = None
        with open('tournaments.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Tournament Id'] == tournament_id:
                    tournament = row
                    break
        
        if not tournament:
            return redirect(url_for('list_tournament'))
        
        # Get category details
        categories = []
        with open('tournament_categories.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Tournament Id'] == tournament_id:
                    categories.append(row)
        
        return render_template('edit_tournament.html', tournament=tournament, categories=categories)
    
    elif request.method == 'POST':
        try:
            # Get form data
            tournament_name = request.form.get('tournament_name')
            venue = request.form.get('venue')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            last_registration_date = request.form.get('last_registration_date')
            total_prize = request.form.get('total_prize')
            general_info = request.form.get('general_info')
            
            # Get the old tournament data for existing logo link
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
            
            # Handle tournament logo
            tournament_logo = request.files.get('tournament_logo')
            tournament_logo_link = old_tournament.get('Tournament Logo Link', '')
            if tournament_logo and tournament_logo.filename:
                # Create a safe filename from tournament name
                safe_tournament_name = "".join(c for c in tournament_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"{safe_tournament_name}_logo{os.path.splitext(tournament_logo.filename)[1]}"
                logo_path = os.path.join(tournament_folder, filename)
                tournament_logo.save(logo_path)
                # Store the relative path for the database
                tournament_logo_link = f"static/tournaments/{tournament_id}/{filename}"
            
            # Get category information
            categories = request.form.getlist('categories[]')
            fees = request.form.getlist('fees[]')
            first_prizes = request.form.getlist('first_prizes[]')
            second_prizes = request.form.getlist('second_prizes[]')
            third_prizes = request.form.getlist('third_prizes[]')
            formats = request.form.getlist('formats[]')
            
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
                            'Tournament Logo Link': tournament_logo_link,
                            'Status': 'active'
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
                    'Tournament Id': tournament_id,  # Use existing tournament ID
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
            
            return redirect(url_for('list_tournament'))
            
        except Exception as e:
            print(f"Error updating tournament: {str(e)}")
            return redirect(url_for('list_tournament'))

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

        # Read categories data
        categories = []
        girls_entries = {}  # Initialize empty dictionary for girls entries
        boys_entries = {}   # Initialize empty dictionary for boys entries
        
        # First, get all categories
        with open('tournament_categories.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Tournament Id'] == tournament_id:
                    categories.append(row)
                    # Initialize empty lists for entries
                    if 'Girls' in row['Category']:
                        girls_entries[row['Category']] = []
                    elif 'Boys' in row['Category']:
                        boys_entries[row['Category']] = []

        # Now get all registrations for this tournament
        registrations = []
        with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if (row['Tournament Id'] == tournament_id and 
                    row['Status'].lower() == 'active'):
                    registrations.append(row)

        # Get player details
        players = {}
        if os.path.exists(PLAYERS_CSV):
            with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    players[row['Player ID']] = row

        # Organize entries by category
        for reg in registrations:
            player = players.get(reg['Player ID'])
            if player:
                entry = {
                    'Name': player['Name'],
                    'Category': reg['Category'],
                    'Seeding': reg.get('Seeding', '')  # Get seeding value
                }
                
                # Add to appropriate category
                if reg['Category'] in girls_entries:
                    girls_entries[reg['Category']].append(entry)
                elif reg['Category'] in boys_entries:
                    boys_entries[reg['Category']].append(entry)

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
                             categories=categories,
                             girls_entries=girls_entries,
                             boys_entries=boys_entries)

    except Exception as e:
        print(f"Error in tournament_info route: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return "Error loading tournament details", 500

@app.route('/tournament/<tournament_id>/register', methods=['GET', 'POST'])
def tournament_register(tournament_id):
    try:
        # Get tournament details
        tournament = get_tournament(tournament_id)
        if not tournament:
            print(f"Tournament not found: {tournament_id}")
            return redirect(url_for('list_tournament'))

        # Get tournament categories
        tournament_categories = []
        try:
            with open('tournament_categories.csv', 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['Tournament Id'] == tournament_id:
                        tournament_categories.append(row['Category'])
        except Exception as e:
            print(f"Error reading tournament categories: {str(e)}")
            tournament_categories = []

        if request.method == 'POST':
            print("Processing POST request for tournament registration")
            
            # Get form data - required fields
            player_id = request.form.get('player_id', '').strip()
            player_name = request.form.get('player_name')
            dob = request.form.get('dob')
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            category = request.form.get('category')

            # Get form data - optional fields
            email = request.form.get('email', '').strip()
            address = request.form.get('address', '').strip()
            state = request.form.get('state', '').strip()
            ttfi_id = request.form.get('ttfi_id', '').strip()
            dstta_id = request.form.get('dstta_id', '').strip() if state == 'Delhi' else ''
            institution = request.form.get('institution', '').strip()
            academy = request.form.get('academy', '').strip()
            upi_id = request.form.get('upi_id', '').strip()

            print(f"Form data received: Name={player_name}, Player ID={player_id}")

            try:
                # Initialize tournament_registrations.csv if needed
                initialize_tournament_registrations_csv()

                # Check if this is a new player or selected from search
                if player_id and player_id.strip():
                    print(f"Using existing player with ID: {player_id}")
                    # Verify player exists
                    player_exists = False
                    with open('players_data.csv', 'r', newline='', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            if row['Player ID'] == player_id:
                                player_exists = True
                                break
                    
                    if not player_exists:
                        print(f"Error: Selected player ID {player_id} not found in database")
                        flash('Selected player not found in database', 'error')
                        return render_template('tournament_register.html',
                                            tournament=tournament,
                                            tournament_categories=tournament_categories,
                                            active_subpage='register')
                else:
                    print("Creating new player...")
                    # Generate new player ID
                    current_year = str(datetime.now().year)[-2:]
                    birth_year = str(datetime.strptime(dob, '%Y-%m-%d').year)[-2:]
                    
                    # Get the next sequence number
                    sequence = 1
                    id_prefix = f"{current_year}-{birth_year}-"
                    
                    if os.path.exists('players_data.csv'):
                        with open('players_data.csv', 'r', newline='', encoding='utf-8') as file:
                            reader = csv.DictReader(file)
                            for row in reader:
                                if row['Player ID'].startswith(id_prefix):
                                    try:
                                        current_sequence = int(row['Player ID'].split('-')[2])
                                        sequence = max(sequence, current_sequence + 1)
                                    except (IndexError, ValueError):
                                        continue
                    
                    player_id = f"{current_year}-{birth_year}-{sequence:04d}"
                    print(f"Generated new player ID: {player_id}")

                    # Define fieldnames for players_data.csv
                    player_fieldnames = [
                        'Player ID',
                        'Name',
                        'Date of Birth',
                        'Gender',
                        'Phone Number',
                        'Email ID',
                        'Address',
                        'State',
                        'TTFI ID',
                        'DSTTA ID',
                        'School/Institution',
                        'Academy',
                        'UPI ID'
                    ]

                    # Create players_data.csv if it doesn't exist
                    if not os.path.exists('players_data.csv'):
                        with open('players_data.csv', 'w', newline='', encoding='utf-8') as file:
                            writer = csv.DictWriter(file, fieldnames=player_fieldnames)
                            writer.writeheader()

                    # Add new player to players_data.csv
                    new_player_data = {
                        'Player ID': player_id,
                        'Name': player_name,
                        'Date of Birth': dob,
                        'Gender': gender,
                        'Phone Number': phone,
                        'Email ID': email,
                        'Address': address,
                        'State': state,
                        'TTFI ID': ttfi_id,
                        'DSTTA ID': dstta_id,
                        'School/Institution': institution,
                        'Academy': academy,
                        'UPI ID': upi_id
                    }

                    with open('players_data.csv', 'a', newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=player_fieldnames)
                        writer.writerow(new_player_data)
                        print(f"Added new player to players_data.csv: {new_player_data}")

                # Check for existing tournament registration
                registration_exists = False
                try:
                    with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            if (row['Tournament Id'] == tournament_id and 
                                row['Player ID'] == player_id and 
                                row['Category'] == category and 
                                row['Status'].lower() == 'active'):
                                registration_exists = True
                                break
                except Exception as e:
                    print(f"Error checking existing registration: {str(e)}")

                if registration_exists:
                    flash('Player already registered for this category', 'error')
                    return render_template('tournament_register.html',
                                        tournament=tournament,
                                        tournament_categories=tournament_categories,
                                        active_subpage='register')

                # Add tournament registration
                registration_data = {
                    'Tournament Id': tournament_id,
                    'Player ID': player_id,
                    'Registration Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Category': category,
                    'Status': 'Active',
                    'Seeding': ''
                }
                
                with open(TOURNAMENT_REGISTRATIONS_CSV, 'a', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=initialize_tournament_registrations_csv())
                    writer.writerow(registration_data)
                    print(f"Added tournament registration: {registration_data}")

                flash('Registration successful!', 'success')
                print("Registration process completed successfully")
                return render_template('tournament_register.html',
                                    tournament=tournament,
                                    tournament_categories=tournament_categories,
                                    active_subpage='register',
                                    success='Registration successful!')

            except Exception as e:
                print(f"Error in registration process: {str(e)}")
                flash(f'Error during registration: {str(e)}', 'error')
                return render_template('tournament_register.html',
                                    tournament=tournament,
                                    tournament_categories=tournament_categories,
                                    active_subpage='register')

        # GET request
        return render_template('tournament_register.html',
                            tournament=tournament,
                            tournament_categories=tournament_categories,
                            active_subpage='register')

    except Exception as e:
        print(f"Error in tournament_register: {str(e)}")
        return redirect(url_for('list_tournament'))

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

@app.route('/tournament/<tournament_id>/schedule')
def tournament_schedule(tournament_id):
    try:
        # Get tournament details
        tournament = get_tournament(tournament_id)
        if not tournament:
            return redirect(url_for('list_tournament'))

        return render_template('tournament_schedule.html',
                             tournament=tournament,
                             active_subpage='schedule')
    except Exception as e:
        print(f"Error in tournament_schedule: {str(e)}")
        return redirect(url_for('list_tournament'))

@app.route('/tournament/<tournament_id>/entries')
def tournament_entries(tournament_id):
    try:
        # Get tournament details
        tournament = get_tournament(tournament_id)
        if not tournament:
            return redirect(url_for('list_tournament'))

        # Get tournament categories
        girls_categories = []
        boys_categories = []
        try:
            with open('tournament_categories.csv', 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['Tournament Id'] == tournament_id:
                        if 'Girls' in row['Category']:
                            girls_categories.append(row['Category'])
                        elif 'Boys' in row['Category']:
                            boys_categories.append(row['Category'])
        except Exception as e:
            print(f"Error reading tournament categories: {str(e)}")

        # Initialize entries dictionaries
        girls_entries = {category: [] for category in girls_categories}
        boys_entries = {category: [] for category in boys_categories}
        
        try:
            # Get all registrations for this tournament
            registrations = []
            with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if (row['Tournament Id'] == tournament_id and 
                        row['Status'].lower() == 'active'):
                        registrations.append(row)

            # Get player details
            players = {}
            if os.path.exists(PLAYERS_CSV):
                with open(PLAYERS_CSV, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        players[row['Player ID']] = row

            # Organize entries by category
            for reg in registrations:
                player = players.get(reg['Player ID'])
                if player:
                    entry = {
                        'Name': player['Name'],
                        'Category': reg['Category'],
                        'Seeding': reg.get('Seeding', '')  # Get seeding value
                    }
                    
                    # Add to appropriate category
                    if reg['Category'] in girls_categories:
                        girls_entries[reg['Category']].append(entry)
                    elif reg['Category'] in boys_categories:
                        boys_entries[reg['Category']].append(entry)

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

        except Exception as e:
            print(f"Error processing entries: {str(e)}")

        return render_template('tournament_entries.html',
                             tournament=tournament,
                             girls_entries=girls_entries,
                             boys_entries=boys_entries,
                             active_subpage='entries')

    except Exception as e:
        print(f"Error in tournament_entries: {str(e)}")
        return redirect(url_for('list_tournament'))

@app.route('/tournament/<tournament_id>/results')
def tournament_results(tournament_id):
    try:
        # Get tournament details
        tournament = get_tournament(tournament_id)
        if not tournament:
            return redirect(url_for('list_tournament'))

        return render_template('tournament_results.html',
                             tournament=tournament,
                             active_subpage='results')
    except Exception as e:
        print(f"Error in tournament_results: {str(e)}")
        return redirect(url_for('list_tournament'))

@app.route('/tournament/<tournament_id>/update_seeding', methods=['GET', 'POST'])
def tournament_update_seeding(tournament_id):
    if request.method == 'POST':
        try:
            # Log received data
            category = request.form.get('category')
            player_ids = request.form.getlist('player_ids[]')
            seedings = request.form.getlist('seedings[]')
            
            print("\nReceived data:")
            print(f"Tournament ID: {tournament_id}")
            print(f"Category: {category}")
            print(f"Player IDs: {player_ids}")
            print(f"Seedings: {seedings}")

            # Read all registrations
            registrations = []
            with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                registrations = list(reader)
                print(f"\nTotal registrations read: {len(registrations)}")

            # Debug: Print a few sample registrations
            print("\nSample registrations:")
            for reg in registrations[:3]:
                print(reg)

            # Update seedings
            updates_made = 0
            for i, player_id in enumerate(player_ids):
                seeding = seedings[i]
                print(f"\nTrying to update player {player_id} with seeding {seeding}")
                
                for reg in registrations:
                    # Print exact values being compared
                    print(f"\nComparing:")
                    print(f"Tournament Ids: '{reg['Tournament Id']}' == '{tournament_id}' : {reg['Tournament Id'] == tournament_id}")
                    print(f"Player IDs: '{reg['Player ID']}' == '{player_id}' : {reg['Player ID'] == player_id}")
                    print(f"Categories: '{reg['Category']}' == '{category}' : {reg['Category'] == category}")
                    
                    if (reg['Tournament Id'] == tournament_id and 
                        reg['Player ID'] == player_id and 
                        reg['Category'] == category):
                        print(f"Match found! Updating seeding from {reg.get('Seeding', '')} to {seeding}")
                        reg['Seeding'] = seeding if seeding else ''
                        updates_made += 1
                        break  # Exit loop once update is made

            print(f"\nUpdates made: {updates_made}")

            if updates_made > 0:
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

            return render_template('tournament_update_seeding.html',
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
    with open(TOURNAMENT_REGISTRATIONS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if (row['Tournament Id'] == tournament_id and
                row['Category'] == category and
                row['Status'].lower() == 'active'):
                player_id = row['Player ID']
                seeding = row.get('Seeding', '')
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
                            players.append(player)
                            break
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
                    'Status': row['Status']
                }
    return None

@app.route('/get-players')
def get_players():
    try:
        search_name = request.args.get('name', '').lower().strip()
        print(f"Searching for name: '{search_name}'")
        
        players = []
        
        with open('players_data.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if search_name in row.get('Name', '').lower():
                    player = {
                        'Player_Id': row.get('Player ID', ''),
                        'Player_Name': row.get('Name', ''),
                        'Date_of_Birth': row.get('Date of Birth', ''),
                        'Gender': row.get('Gender', ''),
                        'Phone_Number': row.get('Phone Number', ''),
                        'Email': row.get('Email ID', ''),
                        'Address': row.get('Address', ''),
                        'State': row.get('State', ''),
                        'TTFI_ID': row.get('TTFI ID', ''),
                        'DSTTA_ID': row.get('DSTTA ID', ''),
                        'School_Institution': row.get('School/Institution', ''),
                        'Academy': row.get('Academy', ''),
                        'UPI_ID': row.get('UPI ID', '')
                    }
                    players.append(player)
                    if len(players) >= 10:  # Limit to 10 results
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

@app.route('/tournament/<tournament_id>/bulk_register', methods=['GET', 'POST'])
def tournament_bulk_register(tournament_id):
    if request.method == 'POST':
        if 'csvFile' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['csvFile']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            try:
                # Read the CSV file
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_data = list(csv.reader(stream))
                
                if len(csv_data) < 2:
                    flash('CSV file is empty or missing data', 'error')
                    return redirect(request.url)

                headers = csv_data[0]
                expected_headers = [
                    'Name', 'Date of Birth', 'Gender', 'Phone Number', 'Category',
                    'Email ID', 'Address', 'State', 'TTFI ID', 'DSTTA ID', 
                    'School/Institution', 'Academy', 'UPI ID'
                ]

                # Validate headers
                if len(headers) != len(expected_headers):
                    flash('Invalid CSV format: Incorrect number of columns', 'error')
                    return redirect(request.url)

                rows = csv_data[1:]
                validated_data = []
                
                # Validate each row
                for idx, row in enumerate(rows, start=1):
                    # Pad row with empty strings if it's shorter than headers
                    row = row + [''] * (len(headers) - len(row))
                    
                    row_data = {
                        'index': idx,
                        'data': row,
                        'errors': [],
                        'invalid_fields': set(),  # Add this to track which fields are invalid
                        'is_valid': True,
                        'registration_status': 'New',
                        'player_id': None
                    }

                    name = row[0].strip()
                    dob = row[1].strip()
                    phone = row[3].strip()

                    # Check if player exists based on name, DOB, and phone
                    if name and dob and phone:  # If all required fields are present
                        print(f"\nChecking for existing player:")
                        print(f"Name: '{name}'")
                        print(f"DOB: '{dob}'")
                        print(f"Phone: '{phone}'")
                        
                        player_id = get_player_id_from_players_data(name, dob, phone)
                        if player_id:
                            print(f"Found existing player with ID: {player_id}")
                            row_data['registration_status'] = 'Registered'
                            row_data['player_id'] = player_id
                        else:
                            print("No matching player found - will be registered as new")

                    # Validate mandatory fields
                    if not name:
                        row_data['errors'].append('Name is required')
                        row_data['invalid_fields'].add(0)  # 0 is the index for Name
                        row_data['is_valid'] = False

                    # Validate Date of Birth
                    try:
                        if not dob:
                            row_data['errors'].append('Date of Birth is required')
                            row_data['invalid_fields'].add(1)  # 1 is the index for DOB
                            row_data['is_valid'] = False
                        else:
                            datetime.strptime(dob, '%Y-%m-%d')
                    except ValueError:
                        row_data['errors'].append('Invalid date format (use YYYY-MM-DD)')
                        row_data['invalid_fields'].add(1)
                        row_data['is_valid'] = False

                    # Validate Gender
                    if not row[2].strip() or row[2].lower() not in ['male', 'female']:
                        row_data['errors'].append('Gender must be Male or Female')
                        row_data['invalid_fields'].add(2)  # 2 is the index for Gender
                        row_data['is_valid'] = False

                    # Validate Phone Number
                    if not phone or not phone.isdigit():
                        row_data['errors'].append('Phone number must be numeric')
                        row_data['invalid_fields'].add(3)  # 3 is the index for Phone
                        row_data['is_valid'] = False

                    # Validate Category
                    if not row[4].strip():
                        row_data['errors'].append('Category is required')
                        row_data['invalid_fields'].add(4)  # 4 is the index for Category
                        row_data['is_valid'] = False

                    validated_data.append(row_data)

                for row_data in validated_data:
                    row_data['invalid_fields'] = list(row_data['invalid_fields'])  # Convert set to list

                return render_template('tournament_bulk_register.html',
                                    tournament=get_tournament(tournament_id),
                                    csv_data={'headers': headers, 'rows': validated_data},
                                    show_table=True)

            except Exception as e:
                print(f"Error processing CSV: {str(e)}")
                app.logger.error(f"Error processing CSV: {str(e)}")
                flash(f'Error processing CSV file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload a CSV file.', 'error')
            return redirect(request.url)

    # GET request
    headers = [
        'Name', 'Date of Birth', 'Gender', 'Phone Number', 'Category',
        'Email ID', 'Address', 'State', 'TTFI ID', 'DSTTA ID',
        'School/Institution', 'Academy', 'UPI ID'
    ]
    empty_row = {
        'index': 1,
        'data': [''] * len(headers),
        'errors': [],
        'invalid_fields': list(range(5)),  # Mark first 5 as required/invalid by default
        'is_valid': False,
        'registration_status': 'New',
        'player_id': None
    }
    return render_template(
        'tournament_bulk_register.html',
        tournament=get_tournament(tournament_id),
        csv_data={'headers': headers, 'rows': [empty_row]},
        show_table=True
    )

@app.route('/tournament/<tournament_id>/bulk_register/download')
def download_bulk_template(tournament_id):
    try:
        # Create CSV content
        csv_content = (
            "Name,Date of Birth,Gender,Phone Number,Category,Email ID,Address,State,TTFI ID,DSTTA ID,School/Institution,Academy,UPI ID\n"
            "John Doe,2000-01-01,Male,9876543210,Under 11 Boys Singles,john.doe@email.com,123 Main Street,Delhi,TTFI123456,DSTTA789,ABC School,XYZ Academy,upi@bank"
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
            dstta_id = player_data[9].strip() if len(player_data) > 9 else ''
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
                        address, state, ttfi_id, dstta_id, institution, 
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

@app.route('/tournament/<tournament_id>/create_bracket')
def tournament_create_bracket(tournament_id):
    # Get tournament data
    tournament = get_tournament(tournament_id)
    if not tournament:
        return redirect(url_for('list_tournament'))
    
    # Get tournament categories specific to this tournament
    categories = get_tournament_categories(tournament_id)
    
    return render_template('tournament_create_bracket.html', 
                          tournament=tournament, 
                          tournament_id=tournament_id, 
                          categories=categories,
                          active_page='tournament',  # For main menu
                          active_subpage='create_bracket')  # For submenu

@app.route('/save_tournament_draw', methods=['POST'])
def save_tournament_draw():
    try:
        # Get data from the request
        data = request.json
        draw_data = data['drawData']
        tournament_id = data['tournamentId']
        category = data['category']
        
        # Create the CSV file if it doesn't exist
        file_exists = os.path.exists('Tournament_draw.csv')
        
        with open('Tournament_draw.csv', 'a', newline='', encoding='utf-8') as file:
            fieldnames = ['Rank', 'Seeding', 'TournamentId', 'Player Name', 'School/Institution', 'Category']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            # Write header if file doesn't exist
            if not file_exists:
                writer.writeheader()
            
            # First, remove any existing data for this tournament and category
            if file_exists:
                temp_rows = []
                with open('Tournament_draw.csv', 'r', newline='', encoding='utf-8') as read_file:
                    reader = csv.DictReader(read_file)
                    for row in reader:
                        # Keep rows that are not for this tournament and category
                        if not (row['TournamentId'] == tournament_id and row['Category'] == category):
                            temp_rows.append(row)
                
                # Rewrite the file with filtered rows
                with open('Tournament_draw.csv', 'w', newline='', encoding='utf-8') as write_file:
                    temp_writer = csv.DictWriter(write_file, fieldnames=fieldnames)
                    temp_writer.writeheader()
                    temp_writer.writerows(temp_rows)
                
                # Reopen the file for appending new rows
                file = open('Tournament_draw.csv', 'a', newline='', encoding='utf-8')
                writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            # Write the new draw data
            for row in draw_data:
                writer.writerow({
                    'Rank': row['rank'],
                    'Seeding': row['seeding'],
                    'TournamentId': row['tournamentId'],
                    'Player Name': row['name'],
                    'School/Institution': row['school'],
                    'Category': row['category']
                })
                
            file.close()
        
        return jsonify({'success': True, 'message': 'Draw saved successfully!'})
    
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
        
        return render_template('list_players.html', players=players, active_page='players')
    except Exception as e:
        print(f"Error in list_players: {e}")
        return render_template('list_players.html', players=[], error=str(e), active_page='players')

@app.route('/get_seeding_ranges')
def get_seeding_ranges():
    try:
        config_path = os.path.join('config', 'seeding_ranges.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                print(f"Loaded seeding ranges: {data}")
                return jsonify(data)
        else:
            print(f"Seeding ranges file not found at {config_path}")
            # Return default seeding ranges
            default_ranges = {
                "seeding_ranges": [
                    {"min": 1, "max": 2, "description": "Top Seeds"},
                    {"min": 3, "max": 5, "description": "Upper Seeds"},
                    {"min": 6, "max": 15, "description": "Mid Seeds"},
                    {"min": 16, "max": 31, "description": "Lower Seeds"},
                    {"min": 32, "max": 999, "description": "Unseeded"}
                ]
            }
            return jsonify(default_ranges)
    except Exception as e:
        print(f"Error loading seeding ranges: {str(e)}")
        # Return default seeding ranges
        default_ranges = {
            "seeding_ranges": [
                {"min": 1, "max": 2, "description": "Top Seeds"},
                {"min": 3, "max": 5, "description": "Upper Seeds"},
                {"min": 6, "max": 15, "description": "Mid Seeds"},
                {"min": 16, "max": 31, "description": "Lower Seeds"},
                {"min": 32, "max": 999, "description": "Unseeded"}
            ]
        }
        return jsonify(default_ranges)

if __name__ == '__main__':
    # Initialize CSV files if they don't exist
    initialize_tournament_registrations_csv()
    # Migrate existing CSV files if needed
    migrate_tournament_registrations_csv()
    # Ensure tournament directories exist
    ensure_tournament_directories()
    app.run(debug=True)