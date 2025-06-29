from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import json
import configparser

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def load_db_config():
    """Load database configuration from properties file"""
    config = configparser.ConfigParser()
    config_path = os.path.join('config', 'database.properties')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Database configuration file not found at {config_path}")
    
    config.read(config_path)
    
    if 'database' not in config:
        raise KeyError("Database section not found in configuration file")
    
    db_config = {
        'host': config['database'].get('host', 'localhost'),
        'user': config['database'].get('user'),
        'password': config['database'].get('password'),
        'database': config['database'].get('database', 'tournament_db'),
        'port': config['database'].getint('port', 3306),
        'raise_on_warnings': config['database'].getboolean('raise_on_warnings', True),
        'auth_plugin': config['database'].get('auth_plugin', 'mysql_native_password'),
        'allow_local_infile': config['database'].getboolean('allow_local_infile', True)
    }
    
    # Validate required fields
    required_fields = ['user', 'password']
    missing_fields = [field for field in required_fields if not db_config.get(field)]
    if missing_fields:
        raise KeyError(f"Missing required database configuration fields: {', '.join(missing_fields)}")
    
    return db_config

def get_db_connection():
    """Get database connection using configuration from properties file"""
    try:
        # Load configuration
        db_config = load_db_config()
        
        # First try to connect to MySQL server without specifying database
        init_connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            port=db_config['port']
        )
        
        # Create database if it doesn't exist
        cursor = init_connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']}")
        cursor.close()
        init_connection.close()
        
        # Now connect with the database
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None
    except Exception as e:
        print(f"Error loading database configuration: {e}")
        return None

def check_tables_exist(cursor):
    """Check if all required tables exist"""
    cursor.execute("SHOW TABLES")
    existing_tables = {table[0].lower() for table in cursor.fetchall()}
    required_tables = {'tournaments', 'tournament_categories', 'players', 'tournament_registrations', 'tournament_draw'}
    missing_tables = required_tables - existing_tables
    return list(missing_tables)

def init_database():
    """Initialize the database and create required tables if they don't exist"""
    connection = get_db_connection()
    if connection is None:
        return False

    try:
        cursor = connection.cursor()
        
        # Check which tables need to be created
        missing_tables = check_tables_exist(cursor)
        if not missing_tables:
            print("All database tables exist, skipping initialization")
            return True
        else:
            print(f"Missing tables that will be created: {', '.join(missing_tables)}")
        
        # Disable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            
        # Read SQL statements from file
        sql_file_path = os.path.join('config', 'table_schemas.sql')
        if not os.path.exists(sql_file_path):
            raise FileNotFoundError(f"SQL schema file not found at {sql_file_path}")
            
        with open(sql_file_path, 'r') as sql_file:
            # Read the entire file
            sql_content = sql_file.read()
            
            # Split into individual statements
            # This handles multi-line statements and ignores comments
            statements = []
            current_statement = []
            
            for line in sql_content.split('\n'):
                # Skip empty lines, comments, and SET statements (we handle them separately)
                line = line.strip()
                if not line or line.startswith('--') or line.startswith('SET'):
                    continue
                    
                current_statement.append(line)
                
                if line.endswith(';'):
                    # Statement is complete
                    statements.append(' '.join(current_statement))
                    current_statement = []
            
            # Execute each statement
            for statement in statements:
                if statement.strip():
                    try:
                        cursor.execute(statement)
                        print(f"Successfully executed: {statement[:100]}...")
                    except Error as e:
                        print(f"Error executing statement: {e}")
                        print(f"Statement was: {statement}")
                        # Continue with other statements
                        continue
        
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        
        connection.commit()
        print("Database initialized successfully")
        return True

    except Error as e:
        print(f"Error initializing database: {e}")
        return False
    except Exception as e:
        print(f"Error reading or executing SQL file: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/')
def index():
    try:
        connection = get_db_connection()
        if connection is None:
            return "Database connection error", 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, venue, start_date, end_date, status 
            FROM tournaments 
            WHERE status = 'active' 
            ORDER BY start_date DESC
        """)
        tournaments = cursor.fetchall()

        return render_template('index.html', tournaments=tournaments)

    except Error as e:
        print(f"Database error: {e}")
        return "Database error", 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/tournament/<tournament_id>/info')
def tournament_info(tournament_id):
    try:
        connection = get_db_connection()
        if connection is None:
            return "Database connection error", 500

        cursor = connection.cursor(dictionary=True)
        
        # Get tournament details
        cursor.execute("""
            SELECT * FROM tournaments WHERE id = %s
        """, (tournament_id,))
        tournament = cursor.fetchone()

        if not tournament:
            return "Tournament not found", 404

        # Calculate tournament status
        today = datetime.now().date()
        if today < tournament['start_date']:
            tournament_status = 'Upcoming'
        elif tournament['start_date'] <= today <= tournament['end_date']:
            tournament_status = 'In Progress'
        else:
            tournament_status = 'Completed'

        registration_open = today <= tournament['last_registration_date']

        # Get tournament registrations with player details
        cursor.execute("""
            SELECT 
                r.*, 
                p.name as player_name,
                p.school_institution
            FROM tournament_registrations r
            JOIN players p ON r.player_id = p.id
            WHERE r.tournament_id = %s
        """, (tournament_id,))
        registrations = cursor.fetchall()

        # Process registrations into categories
        girls_entries = {}
        boys_entries = {}
        
        girls_categories = ['u9', 'u11 Girls', 'u13 Girls', 'u15 Girls', 'u19 Girls', 'Women']
        boys_categories = ['u11 Boys', 'u13 Boys', 'u17 Boys', 'u19 Boys', 'Men']

        # Initialize categories from tournament categories
        categories = tournament['categories'].split(',')
        for category in categories:
            if category in girls_categories:
                girls_entries[category] = []
            elif category in boys_categories:
                boys_entries[category] = []

        # Process registrations
        for reg in registrations:
            entry = {
                'Name': reg['player_name'],
                'School/Institution': reg['school_institution'] or '',
                'Seeding': str(reg['seeding']) if reg['seeding'] else ''
            }
            
            category = reg['category']
            if category in girls_categories and category in girls_entries:
                girls_entries[category].append(entry)
            elif category in boys_categories and category in boys_entries:
                boys_entries[category].append(entry)

        # Sort entries by seeding
        def sort_by_seeding(entry):
            seeding = entry.get('Seeding', '')
            try:
                return (int(seeding) if seeding else 999999, entry['Name'])
            except ValueError:
                return (999999, entry['Name'])

        for category in girls_entries:
            girls_entries[category].sort(key=sort_by_seeding)
        for category in boys_entries:
            boys_entries[category].sort(key=sort_by_seeding)

        return render_template(
            'tournament_details.html',
            tournament=tournament,
            tournament_status=tournament_status,
            registration_open=registration_open,
            girls_entries=girls_entries,
            boys_entries=boys_entries
        )

    except Error as e:
        print(f"Database error: {e}")
        return "Database error", 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/tournament/<tournament_id>/update_seeding', methods=['POST'])
def tournament_update_seeding(tournament_id):
    if request.method == 'POST':
        try:
            connection = get_db_connection()
            if connection is None:
                return jsonify({'success': False, 'message': 'Database connection error'})

            cursor = connection.cursor()
            
            category = request.form.get('category')
            player_ids = request.form.getlist('player_ids[]')
            seedings = request.form.getlist('seedings[]')

            # Start a transaction
            connection.start_transaction()

            try:
                for player_id, seeding in zip(player_ids, seedings):
                    cursor.execute("""
                        UPDATE tournament_registrations 
                        SET seeding = %s 
                        WHERE tournament_id = %s 
                        AND player_id = %s 
                        AND category = %s
                    """, (
                        int(seeding) if seeding.strip() else None,
                        tournament_id,
                        player_id,
                        category
                    ))

                connection.commit()
                return jsonify({'success': True, 'message': 'Seedings updated successfully'})

            except Error as e:
                connection.rollback()
                return jsonify({'success': False, 'message': str(e)})

        except Error as e:
            print(f"Database error: {e}")
            return jsonify({'success': False, 'message': str(e)})

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

if __name__ == '__main__':
    # Initialize database before starting the app
    if init_database():
        app.run(debug=True)
    else:
        print("Failed to initialize database. Please check your database connection.") 