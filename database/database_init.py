import mysql.connector
from mysql.connector import Error
import os
import json
import configparser

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

def load_table_config():
    """Load table configuration from JSON file"""
    config_path = os.path.join('config', 'table_config.json')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Table configuration file not found at {config_path}")
    
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    if 'required_tables' not in config:
        raise KeyError("required_tables section not found in table configuration file")
    
    return set(config['required_tables'])

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
    try:
        # Get required tables from config
        required_tables = load_table_config()
        
        # Get existing tables from database
        cursor.execute("SHOW TABLES")
        existing_tables = {table[0].lower() for table in cursor.fetchall()}
        
        # Find missing tables
        missing_tables = required_tables - existing_tables
        return list(missing_tables)
    except Exception as e:
        print(f"Error checking tables: {e}")
        return []

def init_database(drop_tables=False):
    """Initialize the database and create required tables if they don't exist"""
    print("Starting database initialization...")
    connection = get_db_connection()
    if connection is None:
        print("Failed to get database connection")
        return False

    try:
        cursor = connection.cursor()
        
        if drop_tables:
            # Drop all tables to ensure clean state
            print("Dropping existing tables...")
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            
            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            for table in tables:
                print(f"Dropping table {table[0]}")
                cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
            
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            print("All tables dropped successfully")
        
        # Read SQL statements from file
        sql_file_path = os.path.join('config', 'table_schemas.sql')
        if not os.path.exists(sql_file_path):
            raise FileNotFoundError(f"SQL schema file not found at {sql_file_path}")
            
        print(f"Reading SQL schema from {sql_file_path}")
        with open(sql_file_path, 'r') as sql_file:
            # Read the entire file
            sql_content = sql_file.read()
            
            # Split into individual statements
            # This handles multi-line statements and ignores comments
            statements = []
            current_statement = []
            
            for line in sql_content.split('\n'):
                # Skip empty lines and comments
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                    
                current_statement.append(line)
                
                if line.endswith(';'):
                    # Statement is complete
                    statements.append(' '.join(current_statement))
                    current_statement = []
            
            print(f"Found {len(statements)} SQL statements to execute")
            
            # Execute each statement
            for i, statement in enumerate(statements, 1):
                if statement.strip():
                    try:
                        cursor.execute(statement)
                        print(f"[{i}/{len(statements)}] Successfully executed: {statement[:100]}...")
                    except Error as e:
                        print(f"Error executing statement {i}: {e}")
                        print(f"Statement was: {statement}")
                        # Continue with other statements
                        continue
        
        # Verify tables were created
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("\nCreated tables:")
        for table in tables:
            print(f"- {table[0]}")
            cursor.execute(f"DESCRIBE {table[0]}")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  * {col[0]}: {col[1]}")
        
        connection.commit()
        print("\nDatabase initialization completed successfully")
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