from database.database_init import get_db_connection, init_database
import mysql.connector
from mysql.connector import Error

def test_connection():
    print("Testing database connection...")
    
    try:
        connection = get_db_connection()
        if connection is None:
            print("Failed to establish database connection")
            return False
            
        cursor = connection.cursor()
        
        # Test basic query
        print("\nTesting basic query...")
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"Basic query result: {result}")
        
        # Test database existence
        print("\nChecking database existence...")
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall()]
        print(f"Available databases: {databases}")
        
        if 'tournament_db' not in databases:
            print("WARNING: tournament_db database does not exist!")
            return False
            
        # Test tables
        print("\nChecking tables in tournament_db...")
        cursor.execute("USE tournament_db")
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"Available tables: {tables}")
        
        if 'players' not in tables:
            print("WARNING: players table does not exist!")
            return False
            
        # Test players table structure
        print("\nChecking players table structure...")
        cursor.execute("DESCRIBE players")
        columns = cursor.fetchall()
        print("\nPlayers table columns:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
            
        return True
        
    except Error as e:
        print(f"MySQL Error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    print("=== Database Connection Test ===\n")
    
    # First, try to initialize the database
    print("Initializing database...")
    init_success = init_database()
    if not init_success:
        print("Failed to initialize database")
    else:
        print("Database initialized successfully")
    
    # Then test the connection
    print("\nTesting connection...")
    if test_connection():
        print("\nDatabase connection test PASSED!")
    else:
        print("\nDatabase connection test FAILED!") 