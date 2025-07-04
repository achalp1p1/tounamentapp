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
init_database()

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
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM players 
            ORDER BY Name
        """)
        
        players = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('list_players_db.html', players=players)
        
    except Error as e:
        print(f"Error: {e}")
        return render_template('list_players_db.html', 
                             error="Error fetching players data", 
                             players=[])

@app.route('/list_tournament_db')
def list_tournament_db():
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT t.*, 
                   GROUP_CONCAT(tc.Category) as Categories
            FROM tournaments t
            LEFT JOIN tournament_categories tc ON t.Tournament_ID = tc.Tournament_ID
            GROUP BY t.Tournament_ID
            ORDER BY t.Start_Date DESC
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

def generate_player_id(date_of_birth):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the year from date_of_birth
        year = datetime.strptime(date_of_birth, '%Y-%m-%d').year
        year_code = str(year)[-2:]  # Last two digits of the year
        
        # Get the current maximum ID for this year
        cursor.execute("""
            SELECT MAX(Player_ID) 
            FROM players 
            WHERE Player_ID LIKE '25-25-%'
        """)
        
        max_id = cursor.fetchone()[0]
        
        if max_id:
            # Extract the sequence number and increment
            seq_num = int(max_id.split('-')[-1]) + 1
        else:
            seq_num = 1
            
        # Format: "25-25-XXXX" where XXXX is a sequential number
        new_id = f"25-25-{seq_num:04d}"
        
        cursor.close()
        conn.close()
        
        return new_id
        
    except Error as e:
        print(f"Error generating player ID: {e}")
        raise

@app.route('/player_registration_db', methods=['GET', 'POST'])
def player_registration_db():
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    if request.method == 'POST':
        try:
            # Get form data
            form_data = request.form.to_dict()
            files = request.files
            
            # Generate player ID
            player_id = generate_player_id(form_data['date_of_birth'])
            
            # Connect to database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert player data
            cursor.execute("""
                INSERT INTO players (
                    Player_ID, Name, Date_of_Birth, Gender, Phone, Email,
                    Address, State, TTFI_ID, Official_State_ID, Institution,
                    Academy, District, UPI_ID
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                player_id,
                form_data.get('player_name', '').strip(),
                form_data.get('date_of_birth', '').strip(),
                form_data.get('gender', '').strip(),
                form_data.get('phone', '').strip(),
                form_data.get('email', '').strip(),
                form_data.get('address', '').strip(),
                form_data.get('state', '').strip(),
                form_data.get('ttfi_id', '').strip(),
                form_data.get('official_state_id', '').strip(),
                form_data.get('institution', '').strip(),
                form_data.get('academy', '').strip(),
                form_data.get('district', '').strip(),
                form_data.get('upi_id', '').strip()
            ))
            
            # Handle file uploads if needed
            # TODO: Implement file upload handling
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Player registered successfully!', 'success')
            return redirect(url_for('list_players_db'))
            
        except Error as e:
            print(f"Error registering player: {e}")
            flash('Error registering player. Please try again.', 'error')
            return redirect(url_for('player_registration_db'))
    
    # GET request - show registration form
    return render_template('players_db.html')

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
            files = request.files
            
            # Generate tournament ID
            tournament_id = generate_tournament_id()
            
            # Handle logo upload
            logo_filename = None
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
                    logo_filename = f"logo_{filename}"
            
            # Connect to database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert tournament data
            cursor.execute("""
                INSERT INTO tournaments (
                    Tournament_ID, Name, Venue, Start_Date, End_Date, 
                    Last_Registration_Date, Total_Prize, General_Information,
                    Logo_Link, Status, Bank_Account, UPI_Link, Payment_QR
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                tournament_id,
                form_data.get('tournament_name', '').strip(),
                form_data.get('venue', '').strip(),
                form_data.get('start_date', '').strip(),
                form_data.get('end_date', '').strip(),
                form_data.get('last_registration_date', '').strip(),
                form_data.get('total_prize', '').strip(),
                form_data.get('general_information', '').strip(),
                logo_filename,
                'Active',  # Default status
                form_data.get('bank_account', '').strip(),
                form_data.get('upi_link', '').strip(),
                form_data.get('payment_qr', '').strip()
            ))
            
            # Handle categories
            categories = request.form.getlist('categories[]')
            for category in categories:
                cursor.execute("""
                    INSERT INTO tournament_categories (
                        Tournament_ID, Category
                    ) VALUES (%s, %s)
                """, (tournament_id, category))
            
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
    return render_template('tournament_creation_db.html')

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
                        SET Logo_Link = %s 
                        WHERE Tournament_ID = %s
                    """, (f"logo_{filename}", tournament_id))
            
            # Update tournament data
            cursor.execute("""
                UPDATE tournaments SET
                    Name = %s,
                    Venue = %s,
                    Start_Date = %s,
                    End_Date = %s,
                    Last_Registration_Date = %s,
                    Total_Prize = %s,
                    General_Information = %s,
                    Bank_Account = %s,
                    UPI_Link = %s,
                    Payment_QR = %s
                WHERE Tournament_ID = %s
            """, (
                form_data.get('tournament_name', '').strip(),
                form_data.get('venue', '').strip(),
                form_data.get('start_date', '').strip(),
                form_data.get('end_date', '').strip(),
                form_data.get('last_registration_date', '').strip(),
                form_data.get('total_prize', '').strip(),
                form_data.get('general_information', '').strip(),
                form_data.get('bank_account', '').strip(),
                form_data.get('upi_link', '').strip(),
                form_data.get('payment_qr', '').strip(),
                tournament_id
            ))
            
            # Update categories
            cursor.execute("DELETE FROM tournament_categories WHERE Tournament_ID = %s", (tournament_id,))
            categories = request.form.getlist('categories[]')
            for category in categories:
                cursor.execute("""
                    INSERT INTO tournament_categories (Tournament_ID, Category)
                    VALUES (%s, %s)
                """, (tournament_id, category))
            
            conn.commit()
            flash('Tournament updated successfully!', 'success')
            return redirect(url_for('list_tournament_db'))
            
        else:
            # GET request - fetch tournament data
            cursor.execute("""
                SELECT t.*, GROUP_CONCAT(tc.Category) as Categories
                FROM tournaments t
                LEFT JOIN tournament_categories tc ON t.Tournament_ID = tc.Tournament_ID
                WHERE t.Tournament_ID = %s
                GROUP BY t.Tournament_ID
            """, (tournament_id,))
            
            tournament = cursor.fetchone()
            
            if not tournament:
                flash('Tournament not found!', 'error')
                return redirect(url_for('list_tournament_db'))
            
            return render_template('edit_tournament_db.html', 
                                 tournament=tournament)
    
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
            SELECT t.*, GROUP_CONCAT(tc.Category) as Categories
            FROM tournaments t
            LEFT JOIN tournament_categories tc ON t.Tournament_ID = tc.Tournament_ID
            WHERE t.Tournament_ID = %s
            GROUP BY t.Tournament_ID
        """, (tournament_id,))
        
        tournament = cursor.fetchone()
        
        if not tournament:
            flash('Tournament not found!', 'error')
            return redirect(url_for('list_tournament_db'))
        
        # Get registered players
        cursor.execute("""
            SELECT p.*, tr.Category, tr.Registration_Date, tr.Status as Registration_Status
            FROM tournament_registrations tr
            JOIN players p ON tr.Player_ID = p.Player_ID
            WHERE tr.Tournament_ID = %s
            ORDER BY tr.Registration_Date
        """, (tournament_id,))
        
        registrations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('tournament_details_db.html',
                             tournament=tournament,
                             registrations=registrations)
        
    except Error as e:
        print(f"Error: {e}")
        flash('Error fetching tournament details. Please try again.', 'error')
        return redirect(url_for('list_tournament_db'))

@app.route('/tournament_db/<tournament_id>/register', methods=['GET', 'POST'])
def tournament_register_db(tournament_id):
    if not session.get('logged_in'):
        return redirect(url_for('login_db'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            player_id = request.form.get('player_id')
            category = request.form.get('category')
            
            # Check if already registered
            cursor.execute("""
                SELECT * FROM tournament_registrations
                WHERE Tournament_ID = %s AND Player_ID = %s AND Category = %s
            """, (tournament_id, player_id, category))
            
            if cursor.fetchone():
                flash('Player already registered in this category!', 'error')
                return redirect(url_for('tournament_register_db', tournament_id=tournament_id))
            
            # Register player
            cursor.execute("""
                INSERT INTO tournament_registrations (
                    Tournament_ID, Player_ID, Registration_Date, Category, Status
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                tournament_id,
                player_id,
                datetime.now().strftime('%Y-%m-%d'),
                category,
                'Pending'  # Default status
            ))
            
            conn.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('tournament_info_db', tournament_id=tournament_id))
            
        else:
            # GET request - show registration form
            # Get tournament details
            cursor.execute("""
                SELECT t.*, GROUP_CONCAT(tc.Category) as Categories
                FROM tournaments t
                LEFT JOIN tournament_categories tc ON t.Tournament_ID = tc.Tournament_ID
                WHERE t.Tournament_ID = %s
                GROUP BY t.Tournament_ID
            """, (tournament_id,))
            
            tournament = cursor.fetchone()
            
            # Get all players
            cursor.execute("SELECT * FROM players ORDER BY Name")
            players = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('tournament_register_db.html',
                                 tournament=tournament,
                                 players=players)
            
    except Error as e:
        print(f"Error: {e}")
        flash('Error processing registration. Please try again.', 'error')
        return redirect(url_for('list_tournament_db'))

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
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            form_data = request.form.to_dict()
            files = request.files
            
            # Update player data
            cursor.execute("""
                UPDATE players SET
                    Name = %s,
                    Date_of_Birth = %s,
                    Gender = %s,
                    Phone = %s,
                    Email = %s,
                    Address = %s,
                    State = %s,
                    TTFI_ID = %s,
                    Official_State_ID = %s,
                    Institution = %s,
                    Academy = %s,
                    District = %s,
                    UPI_ID = %s
                WHERE Player_ID = %s
            """, (
                form_data.get('player_name', '').strip(),
                form_data.get('date_of_birth', '').strip(),
                form_data.get('gender', '').strip(),
                form_data.get('phone', '').strip(),
                form_data.get('email', '').strip(),
                form_data.get('address', '').strip(),
                form_data.get('state', '').strip(),
                form_data.get('ttfi_id', '').strip(),
                form_data.get('official_state_id', '').strip(),
                form_data.get('institution', '').strip(),
                form_data.get('academy', '').strip(),
                form_data.get('district', '').strip(),
                form_data.get('upi_id', '').strip(),
                player_id
            ))
            
            # Handle file uploads if needed
            # TODO: Implement file upload handling
            
            conn.commit()
            flash('Player updated successfully!', 'success')
            return redirect(url_for('list_players_db'))
            
        else:
            # GET request - fetch player data
            cursor.execute("""
                SELECT * FROM players
                WHERE Player_ID = %s
            """, (player_id,))
            
            player = cursor.fetchone()
            
            if not player:
                flash('Player not found!', 'error')
                return redirect(url_for('list_players_db'))
            
            return render_template('edit_player_db.html',
                                 player=player)
                                 
    except Error as e:
        print(f"Error: {e}")
        flash('Error processing player data. Please try again.', 'error')
        return redirect(url_for('list_players_db'))
        
    finally:
        cursor.close()
        conn.close()

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
            return config.get('categories', [])
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
                SELECT t.*, GROUP_CONCAT(tc.Category) as Categories
                FROM tournaments t
                LEFT JOIN tournament_categories tc ON t.Tournament_ID = tc.Tournament_ID
                WHERE t.Tournament_ID = %s
                GROUP BY t.Tournament_ID
            """, (tournament_id,))
            
            tournament = cursor.fetchone()
            
            if not tournament:
                flash('Tournament not found!', 'error')
                return redirect(url_for('list_tournament_db'))
            
            # Get registered players with their seeding
            cursor.execute("""
                SELECT p.*, tr.Category, tr.Registration_Date, tr.Seeding
                FROM tournament_registrations tr
                JOIN players p ON tr.Player_ID = p.Player_ID
                WHERE tr.Tournament_ID = %s
                ORDER BY tr.Category, tr.Seeding NULLS LAST, p.Name
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
            SELECT t.*, GROUP_CONCAT(tc.Category) as Categories
            FROM tournaments t
            LEFT JOIN tournament_categories tc ON t.Tournament_ID = tc.Tournament_ID
            WHERE t.Tournament_ID = %s
            GROUP BY t.Tournament_ID
        """, (tournament_id,))
        
        tournament = cursor.fetchone()
        
        if not tournament:
            flash('Tournament not found!', 'error')
            return redirect(url_for('list_tournament_db'))
        
        # Get registered players with seeding
        cursor.execute("""
            SELECT p.*, tr.Category, tr.Registration_Date, tr.Seeding
            FROM tournament_registrations tr
            JOIN players p ON tr.Player_ID = p.Player_ID
            WHERE tr.Tournament_ID = %s
            ORDER BY tr.Category, tr.Seeding NULLS LAST, p.Name
        """, (tournament_id,))
        
        registrations = cursor.fetchall()
        
        # Group players by category
        players_by_category = {}
        for reg in registrations:
            category = reg['Category']
            if category not in players_by_category:
                players_by_category[category] = []
            players_by_category[category].append(reg)
        
        return render_template('tournament_update_format_db.html',
                             tournament=tournament,
                             players_by_category=players_by_category)
                             
    except Error as e:
        print(f"Error: {e}")
        flash('Error creating draw. Please try again.', 'error')
        return redirect(url_for('tournament_info_db', tournament_id=tournament_id))
        
    finally:
        cursor.close()
        conn.close()

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

if __name__ == '__main__':
    app.run(debug=True) 