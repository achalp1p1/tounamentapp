from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, send_file
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime, timedelta
import json
import configparser
from database.database_init import get_db_connection, init_database
import base64
from werkzeug.utils import secure_filename
import uuid
import shutil
import glob
import re
import io
from io import StringIO, BytesIO

app = Flask(__name__, template_folder='templates_db')
app.secret_key = 'your_secret_key_here'

# Initialize database on startup
init_database(drop_tables=False)

# Define upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'logo')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Add custom datetime filter
@app.template_filter('datetime')
def format_datetime(value, format='%Y-%m-%d'):
    if value:
        try:
            if isinstance(value, str):
                dt = datetime.strptime(value, '%Y-%m-%d')
            else:
                dt = value
            return dt.strftime('%d-%m-%y')
        except:
            return value
    return value

def get_image_base64():
    image_path = os.path.join('static', 'tt_facility.jpg')
    try:
        with open(image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{image_data}"
    except Exception as e:
        print(f"Error reading image: {e}")
        return None

@app.route('/')
def root():
    return redirect(url_for('login_db'))

@app.route('/logout_db')
def logout_db():
    session.clear()
    return redirect(url_for('login_db'))

@app.route('/db', methods=['GET', 'POST'])
def login_db():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        # Add your authentication logic here
        session['logged_in'] = True
        return redirect(url_for('dashboard_db'))
    
    image_data = get_image_base64()
    return render_template('login_db.html', image_data=image_data)

@app.route('/dashboard_db')
def dashboard_db():
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
    return render_template('dashboard_db.html', active_page='dashboard_db')

@app.route('/list_players_db')
def list_players_db():
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        print("Fetching players from database...")
        cursor.execute("""
            SELECT id, name, date_of_birth, gender, state, official_state_id 
            FROM players 
            ORDER BY name
        """)
        
        players = cursor.fetchall()
        print(f"Found {len(players)} players")
        
        if players:
            print("Sample player data:", players[0])
            
        return render_template('list_players_db.html', players=players)
        
    except mysql.connector.Error as e:
        print(f"Database error in list_players_db: {e}")
        return render_template('list_players_db.html', 
                             error="Error fetching players data", 
                             players=[])
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("Database connection closed.")

@app.route('/list_tournament_db')
def list_tournament_db():
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT t.*, 
                   GROUP_CONCAT(tc.category) as categories
            FROM tournaments t
            LEFT JOIN tournament_categories tc ON t.tournament_id = tc.tournament_id
            GROUP BY t.tournament_id
            ORDER BY t.start_date DESC
        """)
        
        tournaments = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('list_tournament_db.html', 
                             tournaments=tournaments)
        
    except Error as e:
        print(f"Error: {e}")
        return render_template('list_tournament_db.html', 
                             error="Error fetching tournaments data", 
                             tournaments=[])

def generate_player_id(dob):
    """Generate a unique player ID based on date of birth"""
    conn = None
    cursor = None
    try:
        # Get current count of players
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        count = cursor.fetchone()[0]
        
        # Format: 25-25-XXXX where XXXX is sequential
        next_id = str(count + 1).zfill(4)
        player_id = f"25-25-{next_id}"
        
        return player_id
    except Exception as e:
        print(f"Error generating player ID: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/player_registration_db', methods=['GET', 'POST'])
def player_registration_db():
    conn = None
    cursor = None
    
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    if request.method == 'POST':
        try:
            print("\n=== Starting Player Registration Process ===")
            
            # Get form data
            form_data = request.form.to_dict()
            files = request.files
            
            print("\nForm Data:")
            for key, value in form_data.items():
                print(f"{key}: {value}")
            
            print("\nFiles:")
            for key in files:
                print(f"{key}: {files[key].filename if files[key].filename else 'No file'}")
            
            # Validate required fields
            required_fields = ['name', 'date_of_birth', 'gender', 'phone_number']
            for field in required_fields:
                if not form_data.get(field):
                    print(f"\nMissing required field: {field}")
                    flash(f'Please fill in the {field.replace("_", " ")}', 'error')
                    return redirect(url_for('player_registration_db'))
            
            # Generate player ID
            player_id = generate_player_id(form_data['date_of_birth'])
            if not player_id:
                print("\nFailed to generate player ID")
                flash('Error generating player ID. Please try again.', 'error')
                return redirect(url_for('player_registration_db'))
                
            print(f"\nGenerated player ID: {player_id}")
            
            # Generate Official State ID only if state registration is checked and state is Delhi
            state_registration = form_data.get('state_registration') == 'on'
            state = form_data.get('state', '').strip()
            official_state_id = ''
            
            if state_registration:
                official_state_id = player_id.replace('-', '')
                if state == 'Delhi':
                    official_state_id = 'DL' + official_state_id
                print(f"Generated Official State ID: {official_state_id}")
            
            # Connect to database
            print("\nAttempting database connection...")
            conn = get_db_connection()
            if not conn:
                print("Failed to establish database connection")
                flash('Database connection failed. Please try again.', 'error')
                return redirect(url_for('player_registration_db'))
                
            cursor = conn.cursor(buffered=True)  # Use buffered cursor
            print("Database connection successful")
            
            # Convert boolean fields to 'Yes'/'No'
            state_registration = 'Yes' if form_data.get('state_registration') == 'on' else 'No'
            is_state_transfer = 'Yes' if form_data.get('is_state_transfer') == 'on' else 'No'
            
            # Insert player data
            insert_query = """
                INSERT INTO players (
                    id, name, date_of_birth, gender, phone_number, email,
                    address, state, ttfi_id, official_state_id, school_institution,
                    academy, district, upi_id, account_holder_name, account_number,
                    bank_name, branch_name, ifsc_code, state_registration,
                    is_state_transfer, photo_path, birth_certificate_path,
                    address_proof_path, payment_snapshot_path, transaction_id,
                    noc_certificate_path
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            insert_values = (
                player_id,
                form_data.get('name', '').strip(),
                form_data.get('date_of_birth', '').strip(),
                form_data.get('gender', '').strip(),
                form_data.get('phone_number', '').strip(),
                form_data.get('email', '').strip(),
                form_data.get('address', '').strip(),
                state,
                form_data.get('ttfi_id', '').strip(),
                official_state_id,  # Now using the generated official_state_id
                form_data.get('school_institution', '').strip(),
                form_data.get('academy', '').strip(),
                form_data.get('district', '').strip(),
                form_data.get('upi_id', '').strip(),
                form_data.get('account_holder_name', '').strip(),
                form_data.get('account_number', '').strip(),
                form_data.get('bank_name', '').strip(),
                form_data.get('branch_name', '').strip(),
                form_data.get('ifsc_code', '').strip(),
                state_registration,  # Using 'Yes'/'No' instead of boolean
                is_state_transfer,   # Using 'Yes'/'No' instead of boolean
                None,  # photo_path - will be updated after file upload
                None,  # birth_certificate_path - will be updated after file upload
                None,  # address_proof_path - will be updated after file upload
                None,  # payment_snapshot_path - will be updated after file upload
                form_data.get('transaction_id', '').strip(),
                None   # noc_certificate_path - will be updated after file upload
            )
            
            print("\nExecuting insert query:")
            print("Query:", insert_query)
            print("Values:", insert_values)
            
            cursor.execute(insert_query, insert_values)
            conn.commit()  # Commit after insert
            print("Player data inserted successfully")
            
            # Handle file uploads
            if player_id:
                upload_dir = os.path.join('static', 'uploads', 'players', player_id)
                os.makedirs(upload_dir, exist_ok=True)
                print(f"\nCreated upload directory: {upload_dir}")
                
                file_fields = {
                    'photo_path': 'photo_path',
                    'birth_certificate_path': 'birth_certificate_path',
                    'address_proof_path': 'address_proof_path',
                    'payment_snapshot_path': 'payment_snapshot_path',
                    'noc_certificate_path': 'noc_certificate_path'
                }
                
                file_paths = {}
                for db_field, form_field in file_fields.items():
                    print(f"\nProcessing file field {form_field}")
                    if form_field in files and files[form_field]:
                        file = files[form_field]
                        if file.filename:
                            filename = secure_filename(file.filename)
                            file_path = os.path.join(upload_dir, filename)
                            file.save(file_path)
                            file_paths[db_field] = os.path.join('uploads', 'players', player_id, filename)
                            print(f"Saved file {filename} for field {form_field}")
                
                if file_paths:
                    # Update file paths in database
                    update_query = "UPDATE players SET " + ", ".join(f"{field} = %s" for field in file_paths.keys()) + " WHERE id = %s"
                    update_values = list(file_paths.values()) + [player_id]
                    print("\nExecuting update query:")
                    print("Query:", update_query)
                    print("Values:", update_values)
                    cursor.execute(update_query, update_values)
                    conn.commit()  # Commit after update
                    print("File paths updated in database")
            
            # Verify the insert
            cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
            result = cursor.fetchone()
            if result:
                print(f"\nVerification: Player found in database with ID {player_id}")
                print("Player data:", result)
            else:
                print(f"\nVerification: Player NOT found in database with ID {player_id}")
            
            flash('Player registered successfully!', 'success')
            return redirect(url_for('list_players_db'))
            
        except Error as e:
            print(f"\nDatabase error: {e}")
            if conn:
                conn.rollback()
            flash('Error registering player. Please try again.', 'error')
            return redirect(url_for('player_registration_db'))
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            if conn:
                conn.rollback()
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('player_registration_db'))
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            print("\nDatabase connection cleanup completed")
            print("=== Player Registration Process Ended ===\n")
    
    # GET request - show registration form
    return render_template('player_registration_db.html', today_date=datetime.now().strftime('%Y-%m-%d'))

def generate_tournament_id():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current year's last 2 digits
        year = str(datetime.now().year)[-2:]
        
        # Get the current maximum ID for this year
        cursor.execute("""
            SELECT MAX(Tournament_ID) 
            FROM tournaments 
            WHERE Tournament_ID LIKE %s
        """, (f"{year}%",))
        
        max_id = cursor.fetchone()[0]
        
        if max_id:
            # Extract the sequence number and increment
            seq_num = int(max_id[2:]) + 1
        else:
            seq_num = 1
            
        # Format: "YYXXXX" where YY is year and XXXX is sequential number
        new_id = f"{year}{seq_num:04d}"
        
        cursor.close()
        conn.close()
        
        return new_id
        
    except Error as e:
        print(f"Error generating tournament ID: {e}")
        raise

@app.route('/create_tournament_db', methods=['GET', 'POST'])
def create_tournament_db():
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    if request.method == 'POST':
        try:
            form_data = request.form.to_dict()
            files = request.files.getlist('tournament_logo')  # Get all uploaded files
            
            # Generate tournament ID
            tournament_id = generate_tournament_id()
            
            # Handle logo uploads
            logo_filenames = []
            if files:
                # Create tournament directory
                tournament_dir = os.path.join('static', 'tournaments', tournament_id)
                os.makedirs(tournament_dir, exist_ok=True)
                
                for logo in files:
                    if logo and logo.filename:
                        # Secure the filename
                        filename = secure_filename(logo.filename)
                        # Save the file
                        logo_path = os.path.join(tournament_dir, f"logo_{filename}")
                        logo.save(logo_path)
                        # Store relative path for database
                        logo_filenames.append(f"tournaments/{tournament_id}/logo_{filename}")
            
            # Connect to database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert tournament data
            cursor.execute("""
                INSERT INTO tournaments (
                    tournament_id, name, venue, start_date, end_date, 
                    last_registration_date, total_prize, general_information,
                    tournament_logo_link, status, bank_account, upi_link
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                tournament_id,
                form_data.get('name', '').strip(),
                form_data.get('venue', '').strip(),
                form_data.get('start_date', '').strip(),
                form_data.get('end_date', '').strip(),
                form_data.get('last_registration_date', '').strip(),
                form_data.get('total_prize', '0').strip(),
                form_data.get('general_information', '').strip(),
                ','.join(logo_filenames) if logo_filenames else None,
                'Upcoming',  # Default status based on dates
                form_data.get('bank_account', '').strip(),
                form_data.get('upi_link', '').strip()
            ))
            
            # Handle categories
            # Categories are submitted as arrays with indices
            category_data = {}
            for key, value in form_data.items():
                if key.startswith('categories['):
                    # Extract index and field from key like categories[0][category]
                    parts = key.split('[')
                    index = parts[1].split(']')[0]
                    field = parts[2].split(']')[0]
                    
                    if index not in category_data:
                        category_data[index] = {}
                    category_data[index][field] = value

            # Insert categories
            for category_info in category_data.values():
                cursor.execute("""
                    INSERT INTO tournament_categories (
                        tournament_id, category, fee, first_prize,
                        second_prize, third_prize, format
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    tournament_id,
                    category_info.get('category', '').strip(),
                    category_info.get('fee', '0').strip(),
                    category_info.get('first_prize', '0').strip(),
                    category_info.get('second_prize', '0').strip(),
                    category_info.get('third_prize', '0').strip(),
                    category_info.get('format', '').strip()
                ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Tournament created successfully!', 'success')
            return redirect(url_for('list_tournament_db'))
            
        except Error as e:
            print(f"Error creating tournament: {e}")
            flash('Error creating tournament. Please try again.', 'error')
            return redirect(url_for('create_tournament_db'))
    
    # GET request - show creation form
    categories = get_categories_from_config()
    return render_template('tournament_creation_db.html', categories=categories)

@app.route('/tournament_db/<tournament_id>/edit', methods=['GET', 'POST'])
def edit_tournament_db(tournament_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            form_data = request.form.to_dict()
            files = request.files
            
            # Handle logo upload
            if 'tournament_logo' in files:
                logo = files['tournament_logo']
                if logo and logo.filename:
                    # Secure the filename
                    filename = secure_filename(logo.filename)
                    # Create tournament directory
                    tournament_dir = os.path.join('static', 'tournaments', tournament_id)
                    os.makedirs(tournament_dir, exist_ok=True)
                    # Save the file
                    logo_path = os.path.join(tournament_dir, f"logo_{filename}")
                    logo.save(logo_path)
                    
                    # Update logo filename in database
                    cursor.execute("""
                        UPDATE tournaments 
                        SET tournament_logo_link = %s 
                        WHERE tournament_id = %s
                    """, (f"logo_{filename}", tournament_id))
            
            # Handle empty values for decimal fields
            total_prize = form_data.get('total_prize', '').strip()
            if total_prize == '':
                total_prize = None
            else:
                try:
                    total_prize = float(total_prize)
                except ValueError:
                    total_prize = None
            
            # Update tournament data
            cursor.execute("""
                UPDATE tournaments SET
                    name = %s,
                    venue = %s,
                    start_date = %s,
                    end_date = %s,
                    last_registration_date = %s,
                    total_prize = %s,
                    general_information = %s,
                    bank_account = %s,
                    upi_link = %s,
                    payment_qr = %s
                WHERE tournament_id = %s
            """, (
                form_data.get('name', '').strip(),
                form_data.get('venue', '').strip(),
                form_data.get('start_date', '').strip() or None,
                form_data.get('end_date', '').strip() or None,
                form_data.get('last_registration_date', '').strip() or None,
                total_prize,
                form_data.get('general_information', '').strip(),
                form_data.get('bank_account', '').strip(),
                form_data.get('upi_link', '').strip(),
                form_data.get('payment_qr', '').strip(),
                tournament_id
            ))
            
            # Update categories
            cursor.execute("DELETE FROM tournament_categories WHERE tournament_id = %s", (tournament_id,))
            categories = request.form.getlist('categories[]')
            fees = request.form.getlist('fees[]')
            first_prizes = request.form.getlist('first_prizes[]')
            second_prizes = request.form.getlist('second_prizes[]')
            third_prizes = request.form.getlist('third_prizes[]')
            formats = request.form.getlist('formats[]')
            
            for i in range(len(categories)):
                # Handle empty values for numeric fields
                fee = fees[i].strip() if i < len(fees) else ''
                first_prize = first_prizes[i].strip() if i < len(first_prizes) else ''
                second_prize = second_prizes[i].strip() if i < len(second_prizes) else ''
                third_prize = third_prizes[i].strip() if i < len(third_prizes) else ''
                
                # Convert empty strings to None
                fee = float(fee) if fee != '' else None
                first_prize = float(first_prize) if first_prize != '' else None
                second_prize = float(second_prize) if second_prize != '' else None
                third_prize = float(third_prize) if third_prize != '' else None
                
                cursor.execute("""
                    INSERT INTO tournament_categories 
                    (tournament_id, category, fee, first_prize, second_prize, third_prize, format)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    tournament_id, 
                    categories[i],
                    fee,
                    first_prize,
                    second_prize,
                    third_prize,
                    formats[i] if i < len(formats) else None
                ))
            
            conn.commit()
            flash('Tournament updated successfully!', 'success')
            return redirect(url_for('list_tournament_db'))
            
        else:
            # GET request - fetch tournament data
            cursor.execute("""
                SELECT * FROM tournaments WHERE tournament_id = %s
            """, (tournament_id,))
            
            tournament = cursor.fetchone()
            
            if not tournament:
                flash('Tournament not found!', 'error')
                return redirect(url_for('list_tournament_db'))
            
            # Fetch tournament categories separately
            cursor.execute("""
                SELECT category, fee, first_prize, second_prize, third_prize, format
                FROM tournament_categories 
                WHERE tournament_id = %s
            """, (tournament_id,))
            
            tournament_categories = cursor.fetchall()
            
            # Get available categories from config
            available_categories = get_categories_from_config()
            
            return render_template('edit_tournament_db.html', 
                                 tournament=tournament,
                                 tournament_categories=tournament_categories,
                                 available_categories=available_categories)
    
    except Error as e:
        print(f"Error: {e}")
        flash('Error processing tournament. Please try again.', 'error')
        return redirect(url_for('list_tournament_db'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/tournament_db/<tournament_id>/info')
def tournament_info_db(tournament_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get tournament details
        cursor.execute("""
            SELECT t.*, 
                   GROUP_CONCAT(tc.category) as categories
            FROM tournaments t
            LEFT JOIN tournament_categories tc ON t.tournament_id = tc.tournament_id
            WHERE t.tournament_id = %s
            GROUP BY t.tournament_id
        """, (tournament_id,))
        
        tournament = cursor.fetchone()
        
        if not tournament:
            return "Tournament not found", 404
            
        # Get registrations for this tournament
        cursor.execute("""
            SELECT r.*, p.name
            FROM tournament_registrations r
            JOIN players p ON r.player_id = p.id
            WHERE r.tournament_id = %s
            ORDER BY r.registration_date DESC
        """, (tournament_id,))
        
        registrations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('tournament_details_db.html',
                             tournament=tournament,
                             registrations=registrations)
                             
    except Error as e:
        print(f"Error: {e}")
        return "Error fetching tournament details", 500

@app.route('/tournament_db/<tournament_id>/register', methods=['GET', 'POST'])
def tournament_register_db(tournament_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            data = request.get_json()
            player_id = data.get('player_id')
            category = data.get('category')
            
            # Check if player exists
            cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
            player = cursor.fetchone()
            
            if not player:
                return jsonify({'success': False, 'message': 'Player not found'})
                
            # Check if already registered
            cursor.execute("""
                SELECT * FROM tournament_registrations 
                WHERE tournament_id = %s AND player_id = %s AND category = %s
            """, (tournament_id, player_id, category))
            
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Player already registered in this category'})
                
            # Add registration
            cursor.execute("""
                INSERT INTO tournament_registrations 
                (tournament_id, player_id, category, registration_date, status)
                VALUES (%s, %s, %s, CURDATE(), 'Pending')
            """, (tournament_id, player_id, category))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'redirect_url': url_for('tournament_info_db', tournament_id=tournament_id)
            })
            
        # GET request - show registration form
        cursor.execute("""
            SELECT t.*, 
                   GROUP_CONCAT(tc.category) as categories
            FROM tournaments t
            LEFT JOIN tournament_categories tc ON t.tournament_id = tc.tournament_id
            WHERE t.tournament_id = %s
            GROUP BY t.tournament_id
        """, (tournament_id,))
        
        tournament = cursor.fetchone()
        
        if not tournament:
            return "Tournament not found", 404
            
        cursor.close()
        conn.close()
        
        return render_template('tournament_register_db.html',
                             tournament=tournament)
                             
    except Error as e:
        print(f"Error: {e}")
        return "Error processing registration", 500

@app.route('/search_players_db')
def search_players_db():
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        name = request.args.get('name', '')
        state = request.args.get('state', '')
        ttfi_id = request.args.get('ttfi_id', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Build dynamic query based on search parameters
        query = "SELECT * FROM players WHERE 1=1"
        params = []
        
        if name:
            query += " AND Name LIKE %s"
            params.append(f"%{name}%")
        
        if state:
            query += " AND State LIKE %s"
            params.append(f"%{state}%")
            
        if ttfi_id:
            query += " AND TTFI_ID LIKE %s"
            params.append(f"%{ttfi_id}%")
            
        query += " ORDER BY Name"
        
        cursor.execute(query, tuple(params))
        players = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('search_players_db.html',
                             players=players,
                             search_params={
                                 'name': name,
                                 'state': state,
                                 'ttfi_id': ttfi_id
                             })
                             
    except Error as e:
        print(f"Error: {e}")
        flash('Error searching players. Please try again.', 'error')
        return redirect(url_for('list_players_db'))

@app.route('/edit_player_db/<player_id>', methods=['GET', 'POST'])
def edit_player_db(player_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        if request.method == 'POST':
            # Get form data
            name = request.form.get('player_name')
            dob = request.form.get('dob')
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            email = request.form.get('email')
            address = request.form.get('address')
            state = request.form.get('state')
            district = request.form.get('district')
            ttfi_id = request.form.get('ttfi_id')
            institution = request.form.get('institution')
            academy = request.form.get('academy')
            upi_id = request.form.get('upi_id')
            
            print(f"Updating player {player_id} with name: {name}")
            
            # Update player data
            cursor.execute("""
                UPDATE players SET
                    name = %s,
                    date_of_birth = %s,
                    gender = %s,
                    phone_number = %s,
                    email = %s,
                    address = %s,
                    state = %s,
                    district = %s,
                    ttfi_id = %s,
                    school_institution = %s,
                    academy = %s,
                    upi_id = %s
                WHERE id = %s
            """, (name, dob, gender, phone, email, address, state, district, ttfi_id, institution, academy, upi_id, player_id))
            
            conn.commit()
            print("Player updated successfully")
            return redirect(url_for('list_players_db'))
            
        else:
            print(f"Fetching player data for ID: {player_id}")
            # Get player data for display
            cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
            player = cursor.fetchone()
            
            if player is None:
                print(f"Player not found with ID: {player_id}")
                return "Player not found", 404
                
            print("Player data found:", player)
                
            # Get states for dropdown
            cursor.execute("SELECT DISTINCT state FROM players WHERE state IS NOT NULL AND state != '' ORDER BY state")
            states = [row['state'] for row in cursor.fetchall()]
            
            return render_template('edit_player_db.html', player=player, states=states)
            
    except mysql.connector.Error as err:
        print(f"Database error in edit_player_db: {err}")
        return f"Database error occurred: {err}", 500
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("Database connection closed.")

@app.route('/delete_player_db/<player_id>', methods=['POST'])
def delete_player_db(player_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First delete from tournament_registrations
        cursor.execute("""
            DELETE FROM tournament_registrations
            WHERE Player_ID = %s
        """, (player_id,))
        
        # Then delete the player
        cursor.execute("""
            DELETE FROM players
            WHERE Player_ID = %s
        """, (player_id,))
        
        conn.commit()
        flash('Player deleted successfully!', 'success')
        
    except Error as e:
        print(f"Error: {e}")
        flash('Error deleting player. Please try again.', 'error')
        
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('list_players_db'))

@app.route('/delete_tournament_db/<tournament_id>', methods=['POST'])
def delete_tournament_db(tournament_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete from tournament_categories
        cursor.execute("""
            DELETE FROM tournament_categories
            WHERE Tournament_ID = %s
        """, (tournament_id,))
        
        # Delete from tournament_registrations
        cursor.execute("""
            DELETE FROM tournament_registrations
            WHERE Tournament_ID = %s
        """, (tournament_id,))
        
        # Delete the tournament
        cursor.execute("""
            DELETE FROM tournaments
            WHERE Tournament_ID = %s
        """, (tournament_id,))
        
        # Delete tournament directory with logos
        tournament_dir = os.path.join('static', 'tournaments', tournament_id)
        if os.path.exists(tournament_dir):
            shutil.rmtree(tournament_dir)
        
        conn.commit()
        flash('Tournament deleted successfully!', 'success')
        
    except Error as e:
        print(f"Error: {e}")
        flash('Error deleting tournament. Please try again.', 'error')
        
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('list_tournament_db'))

def get_categories_from_config():
    try:
        with open('config/categories_config.json', 'r') as f:
            config = json.load(f)
            categories = config.get('categories', [])
            return [category['name'] for category in categories]
    except Exception as e:
        print(f"Error reading categories config: {e}")
        return []

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

@app.route('/tournament_db/<tournament_id>/update_seeding', methods=['GET', 'POST'])
def tournament_update_seeding_db(tournament_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Get seeding data from form
            seeding_data = request.form.to_dict()
            
            # Update seeding for each registration
            for key, value in seeding_data.items():
                if key.startswith('seeding_'):
                    reg_id = key.split('_')[1]
                    cursor.execute("""
                        UPDATE tournament_registrations 
                        SET Seeding = %s 
                        WHERE Tournament_ID = %s AND Player_ID = %s
                    """, (value, tournament_id, reg_id))
            
            conn.commit()
            flash('Seeding updated successfully!', 'success')
            return redirect(url_for('tournament_info_db', tournament_id=tournament_id))
            
        else:
            # Get tournament details
            cursor.execute("""
                SELECT t.*, GROUP_CONCAT(tc.category) as categories
                FROM tournaments t
                LEFT JOIN tournament_categories tc ON t.tournament_id = tc.tournament_id
                WHERE t.tournament_id = %s
                GROUP BY t.tournament_id
            """, (tournament_id,))
            
            tournament = cursor.fetchone()
            
            if not tournament:
                flash('Tournament not found!', 'error')
                return redirect(url_for('list_tournament_db'))
            
            # Get registered players with their seeding
            cursor.execute("""
                SELECT p.*, tr.category, tr.registration_date, tr.Seeding
                FROM tournament_registrations tr
                JOIN players p ON tr.player_id = p.id
                WHERE tr.tournament_id = %s
                ORDER BY tr.category, tr.Seeding NULLS LAST, p.Name
            """, (tournament_id,))
            
            registrations = cursor.fetchall()
            
            # Get seeding ranges from config
            seeding_ranges = get_seeding_ranges()
            
            return render_template('tournament_update_format_db.html',
                                 tournament=tournament,
                                 registrations=registrations,
                                 seeding_ranges=seeding_ranges)
                                 
    except Error as e:
        print(f"Error: {e}")
        flash('Error updating seeding. Please try again.', 'error')
        return redirect(url_for('tournament_info_db', tournament_id=tournament_id))
        
    finally:
        cursor.close()
        conn.close()

def get_seeding_ranges():
    try:
        with open('config/seeding_ranges.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading seeding ranges: {e}")
        return {}

@app.route('/tournament_db/<tournament_id>/create_draw', methods=['GET', 'POST'])
def tournament_create_draw_db(tournament_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get tournament details
        cursor.execute("""
            SELECT t.*, GROUP_CONCAT(tc.category) as categories
            FROM tournaments t
            LEFT JOIN tournament_categories tc ON t.tournament_id = tc.tournament_id
            WHERE t.tournament_id = %s
            GROUP BY t.tournament_id
        """, (tournament_id,))
        
        tournament = cursor.fetchone()
        
        if not tournament:
            flash('Tournament not found!', 'error')
            return redirect(url_for('list_tournament_db'))
        
        # Get registered players with seeding
        cursor.execute("""
            SELECT p.*, tr.category, tr.registration_date, tr.seeding
            FROM tournament_registrations tr
            JOIN players p ON tr.player_id = p.id
            WHERE tr.tournament_id = %s
            ORDER BY tr.category, tr.seeding NULLS LAST, p.name
        """, (tournament_id,))
        
        registrations = cursor.fetchall()
        
        # Organize players by category
        players_by_category = {}
        for reg in registrations:
            category = reg['category']
            if category not in players_by_category:
                players_by_category[category] = []
            players_by_category[category].append(reg)
        
        cursor.close()
        conn.close()
        
        return render_template('tournament_create_draw_db.html',
                             tournament=tournament,
                             players_by_category=players_by_category)
        
    except Error as e:
        print(f"Error: {e}")
        flash('Error fetching tournament details. Please try again.', 'error')
        return redirect(url_for('list_tournament_db'))

@app.route('/save_tournament_draw_db', methods=['POST'])
def save_tournament_draw_db():
    if not session.get('logged_in'):
        return jsonify({'error': 'Not logged in'}), 401
        
    try:
        data = request.get_json()
        tournament_id = data.get('tournament_id')
        draw_data = data.get('draw_data', [])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clear existing draw data
        cursor.execute("""
            DELETE FROM tournament_draw
            WHERE Tournament_ID = %s
        """, (tournament_id,))
        
        # Insert new draw data
        for draw in draw_data:
            cursor.execute("""
                INSERT INTO tournament_draw (
                    Tournament_ID, Category, Round_Number,
                    Match_Number, Player1_ID, Player2_ID,
                    Winner_ID, Score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                tournament_id,
                draw['category'],
                draw['round'],
                draw['match'],
                draw['player1'],
                draw['player2'],
                draw.get('winner'),
                draw.get('score')
            ))
        
        conn.commit()
        return jsonify({'success': True})
        
    except Error as e:
        print(f"Error saving draw: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        cursor.close()
        conn.close()

@app.route('/tournament_db/<tournament_id>/get_category_players/<category>')
def get_category_players_db(tournament_id, category):
    if not session.get('logged_in'):
        return jsonify({'error': 'Not logged in'}), 401
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.*, tr.Seeding
            FROM tournament_registrations tr
            JOIN players p ON tr.Player_ID = p.Player_ID
            WHERE tr.Tournament_ID = %s AND tr.Category = %s
            ORDER BY tr.Seeding NULLS LAST, p.Name
        """, (tournament_id, category))
        
        players = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'players': [{
                'id': p['Player_ID'],
                'name': p['Name'],
                'seeding': p['Seeding']
            } for p in players]
        })
        
    except Error as e:
        print(f"Error fetching players: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_player_details_db/<player_id>')
def get_player_details_db(player_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, name, date_of_birth, state, district, school_institution
            FROM players
            WHERE id = %s
        """, (player_id,))
        
        player = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if player:
            return jsonify({'success': True, 'player': player})
        else:
            return jsonify({'success': False, 'message': 'Player not found'})
            
    except Error as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': 'Error fetching player details'})

if __name__ == '__main__':
    app.run(debug=True) 